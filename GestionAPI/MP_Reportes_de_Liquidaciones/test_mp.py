#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de pruebas manuales para la API de Mercado Pago - Reporte de Liquidaciones.

Uso:
    python test_mp.py <accion> [parametro]

Acciones disponibles:
    config          Consultar configuración actual del reporte
    lista           Consultar lista de todos los reportes generados
    buscar <id>     Consultar el estado de un reporte específico por id
    descargar <file_name>
                    Descargar el CSV de un reporte y guardarlo en temp/
    crear           Crear un reporte para los últimos 5 días (sin el día actual)

Ejemplos:
    python test_mp.py config
    python test_mp.py lista
    python test_mp.py buscar 884331221
    python test_mp.py descargar release-report-144448334-24-04-2026.csv
    python test_mp.py crear
"""

import sys
import os
import asyncio
import json
import logging

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, project_root)

from datetime import datetime, timedelta, timezone
from GestionAPI.common.credenciales import MERCADOPAGO
from GestionAPI.MP_Reportes_de_Liquidaciones.api_mp import MercadoPagoAPIClient

TEMP_DIR = os.path.join(os.path.dirname(__file__), "temp")
LOGS_DIR = os.path.join(os.path.dirname(__file__), "logs")


def _get_test_logger(nombre_archivo: str) -> logging.Logger:
    """Crea un logger que escribe en consola y en un archivo de log."""
    os.makedirs(LOGS_DIR, exist_ok=True)
    ruta_log = os.path.join(LOGS_DIR, nombre_archivo)

    logger = logging.getLogger(f"test_mp.{nombre_archivo}")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    fmt = logging.Formatter("%(message)s")

    # Handler a consola
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # Handler a archivo (sobrescribe cada vez)
    fh = logging.FileHandler(ruta_log, mode="w", encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger, ruta_log


def _print_json(data):
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))


def _log_json(log: logging.Logger, data):
    log.info(json.dumps(data, indent=2, ensure_ascii=False, default=str))


async def accion_config(client: MercadoPagoAPIClient):
    """Consultar configuración actual del reporte."""
    print("\n--- CONSULTAR CONFIGURACIÓN ---")
    resultado = await client.consultar_configuracion()
    if resultado:
        _print_json(resultado)
    else:
        print("ERROR: No se pudo obtener la configuración.")


async def accion_lista(client: MercadoPagoAPIClient):
    """Consultar lista de todos los reportes generados y guarda el resultado en logs/lista_reportes.log."""
    log, ruta_log = _get_test_logger("lista_reportes.log")
    log.info("\n--- CONSULTAR LISTA DE REPORTES ---")
    lista = await client.obtener_lista_reportes()
    if lista:
        log.info(f"Total reportes encontrados: {len(lista)}\n")
        for r in lista:
            log.info(
                f"  id={r.get('id')} | status={r.get('status', ''):<10} | "
                f"file_name={r.get('file_name')} | "
                f"begin={r.get('begin_date','')[:10]} end={r.get('end_date','')[:10]}"
            )
        log.info("\n--- JSON COMPLETO ---")
        _log_json(log, lista)
        print(f"\nResultado completo guardado en: {ruta_log}")
    else:
        log.info("No se encontraron reportes o hubo un error.")
        print(f"Log guardado en: {ruta_log}")


async def accion_buscar(client: MercadoPagoAPIClient, report_id: int):
    """Buscar un reporte específico por id en la lista."""
    print(f"\n--- BUSCAR REPORTE id={report_id} ---")
    lista = await client.obtener_lista_reportes()
    encontrado = None
    for r in lista:
        if r.get("id") == report_id:
            encontrado = r
            break
    if encontrado:
        _print_json(encontrado)
    else:
        print(f"No se encontró ningún reporte con id={report_id}.")
        print(f"IDs disponibles: {[r.get('id') for r in lista]}")


async def accion_descargar(client: MercadoPagoAPIClient, file_name: str):
    """Descargar el CSV de un reporte y guardarlo en temp/."""
    print(f"\n--- DESCARGAR REPORTE: {file_name} ---")
    contenido = await client.descargar_reporte(file_name)
    if contenido:
        os.makedirs(TEMP_DIR, exist_ok=True)
        ruta = os.path.join(TEMP_DIR, file_name)
        with open(ruta, "wb") as f:
            f.write(contenido)
        print(f"CSV guardado en: {ruta}")
        print(f"Tamaño: {len(contenido)} bytes")
        # Mostrar primeras líneas
        print("\nPrimeras 5 líneas del CSV:")
        lineas = contenido.decode("utf-8-sig", errors="replace").splitlines()
        for linea in lineas[:5]:
            print(" ", linea[:120])
    else:
        print("ERROR: No se pudo descargar el reporte.")


async def accion_crear(client: MercadoPagoAPIClient):
    """Crear un reporte para los últimos 5 días sin incluir el día actual (alineado UTC-3)."""
    print("\n--- CREAR REPORTE ---")
    ahora_utc = datetime.now(tz=timezone.utc)
    # Medianoche Argentina = 03:00 UTC
    if ahora_utc.hour < 3:
        hoy_ar_en_utc = ahora_utc.replace(hour=3, minute=0, second=0, microsecond=0) - timedelta(days=1)
    else:
        hoy_ar_en_utc = ahora_utc.replace(hour=3, minute=0, second=0, microsecond=0)
    end_date = hoy_ar_en_utc
    begin_date = hoy_ar_en_utc - timedelta(days=5)
    begin_str = begin_date.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_str = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"Rango: {begin_str} → {end_str}")
    resultado = await client.crear_reporte(begin_str, end_str)
    if resultado:
        _print_json(resultado)
        generation_date = resultado.get("generation_date")
        print(f"\njob_id={resultado.get('id')} | generation_date={generation_date}")
        print("Nota: el job_id NO es el id del reporte en la lista. Use 'python test_mp.py lista' para verificar.")
    else:
        print("ERROR: No se pudo crear el reporte.")


async def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(0)

    accion = args[0].lower()
    client = MercadoPagoAPIClient(access_token=MERCADOPAGO["access_token"])

    try:
        if accion == "config":
            await accion_config(client)

        elif accion == "lista":
            await accion_lista(client)

        elif accion == "buscar":
            if len(args) < 2:
                print("ERROR: Indicar el id del reporte. Ej: python test_mp.py buscar 884331221")
                sys.exit(1)
            await accion_buscar(client, int(args[1]))

        elif accion == "descargar":
            if len(args) < 2:
                print("ERROR: Indicar el file_name. Ej: python test_mp.py descargar release-report-xxx.csv")
                sys.exit(1)
            await accion_descargar(client, args[1])

        elif accion == "crear":
            await accion_crear(client)

        else:
            print(f"Acción desconocida: '{accion}'")
            print(__doc__)
            sys.exit(1)

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
