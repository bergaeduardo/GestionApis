#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de prueba manual para consultar el saldo disponible de Mercado Pago.

Uso:
    python test_mp_saldo.py            → muestra el saldo actual
    python test_mp_saldo.py --debug    → saldo + últimos movimientos del reporte
"""

import sys
import os
import asyncio
import json
import csv
import io
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s [%(name)s] %(message)s",
    stream=sys.stdout,
)

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, project_root)

from GestionAPI.common.credenciales import MERCADOPAGO
from GestionAPI.MP_Saldo_Cuenta.api_mp_saldo import MercadoPagoSaldoClient, consultar_saldo

CAMPOS_EXTRACTO = ["DATE", "RECORD_TYPE", "DESCRIPTION", "NET_CREDIT_AMOUNT", "NET_DEBIT_AMOUNT", "BALANCE_AMOUNT"]
FILAS_A_MOSTRAR = 15


async def mostrar_extracto(client: MercadoPagoSaldoClient):
    """Descarga el último reporte y muestra las últimas N filas como mini-extracto."""
    lista = await client._lista_reportes()
    disponibles = [r for r in lista if r.get("file_name")]
    if not disponibles:
        print("No hay reportes disponibles.")
        return

    reporte = disponibles[0]
    file_name = reporte["file_name"]
    fecha_inicio = reporte.get("begin_date", "?")
    fecha_fin = reporte.get("end_date", "?")

    print(f"\n{'='*70}")
    print(f"  Reporte: {file_name}")
    print(f"  Período: {fecha_inicio}  →  {fecha_fin}")
    print(f"{'='*70}")

    import aiohttp
    url = f"https://api.mercadopago.com/v1/account/release_report/{file_name}"
    contenido = await client._get_bytes(url)
    if not contenido:
        print("No se pudo descargar el reporte.")
        return

    texto = contenido.decode("utf-8-sig", errors="replace")
    primera_linea = texto.split("\n")[0]
    sep = ";" if primera_linea.count(";") > primera_linea.count(",") else ","

    filas = list(csv.DictReader(io.StringIO(texto), delimiter=sep))
    ultimas = filas[-FILAS_A_MOSTRAR:]

    # Anchos de columna
    anchos = {c: len(c) for c in CAMPOS_EXTRACTO}
    for fila in ultimas:
        for c in CAMPOS_EXTRACTO:
            anchos[c] = max(anchos[c], len(str(fila.get(c, "") or "")))

    # Encabezado
    header = "  ".join(c.ljust(anchos[c]) for c in CAMPOS_EXTRACTO)
    sep_line = "  ".join("-" * anchos[c] for c in CAMPOS_EXTRACTO)
    print(header)
    print(sep_line)

    for fila in ultimas:
        linea = "  ".join(str(fila.get(c, "") or "").ljust(anchos[c]) for c in CAMPOS_EXTRACTO)
        print(linea)

    print(f"\n  → Mostrando últimas {len(ultimas)} filas de {len(filas)} totales.")
    if filas:
        ultimo_balance = filas[-1].get("BALANCE_AMOUNT", "N/A")
        print(f"  → BALANCE_AMOUNT final del reporte: {ultimo_balance} ARS")
    print()


async def main():
    debug = "--debug" in sys.argv
    access_token = MERCADOPAGO["access_token"]

    print("Consultando saldo de Mercado Pago...")
    client = MercadoPagoSaldoClient(access_token)

    try:
        resultado = await client.get_saldo_json()

        if resultado is None:
            print("ERROR: No se pudo obtener el saldo. Revisar logs y access_token.")
            sys.exit(1)

        print("\n--- Saldo actual ---")
        print(json.dumps(resultado, indent=2, ensure_ascii=False))

        if debug:
            await mostrar_extracto(client)

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
