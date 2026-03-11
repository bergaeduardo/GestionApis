#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Consulta y actualización de estados de envío Andreani — Pedidos desde Sucursal.

Trabaja con los registros de la tabla EB_ENVIOS_WEB_DESDE_SUC.
Las funciones que operan sobre SEIN_TABLA_TEMPORAL_SCRIPT se mantienen en
consultar_estado.py.

Uso:
    # Actualización masiva (por defecto si no se pasa argumento):
    python consultar_estado_suc.py

    # Actualización masiva explícita:
    python consultar_estado_suc.py --actualizar

    # Consulta y actualización de un envío individual:
    python consultar_estado_suc.py --numero_envio <NUM_SEGUIMIENTO>
"""

import asyncio
import argparse
import sys
import os
import logging

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from GestionAPI.Andreani.andreani_api import AndreaniAPI
from GestionAPI.common.credenciales import DATA_PROD
from GestionAPI.Andreani.db_operations_andreani import AndreaniSucDB

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('consultar_estado_suc')


async def consultar_estado_envio_api(numero_envio: str):
    """
    Consulta el estado de un envío en la API de Andreani.

    Args:
        numero_envio: El número de seguimiento a consultar.

    Returns:
        dict con 'estado', 'estadoId' y 'fechaEstado', o None si hay error.
    """
    api = AndreaniAPI(
        base_url=DATA_PROD["url"],
        user=DATA_PROD["user"],
        password=DATA_PROD["passw"]
    )
    try:
        logger.info(f"Consultando API de Andreani para el envío: {numero_envio}")
        estado_envio = await api.consultar_estado_envio(numero_envio)

        if estado_envio:
            return {
                "estado": estado_envio.get("estado"),
                "estadoId": estado_envio.get("estadoId"),
                "fechaEstado": estado_envio.get("fechaEstado")
            }
    except Exception as e:
        logger.error(f"Ocurrió un error al consultar el estado del envío: {e}")

    return None


async def actualizar_estados_envios():
    """
    Consulta y actualiza los estados de envíos pendientes en EB_ENVIOS_WEB_DESDE_SUC.

    Busca todos los registros con:
    - IMP_ROT = 1
    - NUM_SEGUIMIENTO IS NOT NULL
    - estadoIdEnvio NOT IN ('14','18','20') o IS NULL
    - estadoEnvio <> 'RESCATADO'

    Para cada registro consulta el estado en la API y actualiza la base de datos.
    """
    db = AndreaniSucDB()

    logger.info("Obteniendo envíos desde sucursal pendientes de actualización...")
    envios_pendientes = db.get_envios_pendientes()

    if not envios_pendientes:
        logger.info("No hay envíos pendientes para actualizar.")
        return

    logger.info(f"Se encontraron {len(envios_pendientes)} envíos pendientes.")

    envios_actualizados = 0
    envios_con_error = 0

    for registro in envios_pendientes:
        nro_pedido = registro[0]
        num_seguimiento = registro[1]

        logger.info(f"Procesando pedido {nro_pedido} — Seguimiento: {num_seguimiento}")

        estado_info = await consultar_estado_envio_api(num_seguimiento)

        if estado_info:
            estado = estado_info.get("estado")
            estado_id = estado_info.get("estadoId")
            fecha_estado = estado_info.get("fechaEstado")

            logger.info(f"Estado obtenido de API: {estado} (ID: {estado_id})")

            if db.update_estado_envio(num_seguimiento, estado, estado_id, fecha_estado):
                logger.info(f"✓ Pedido {nro_pedido} actualizado: {estado} (ID: {estado_id})")
                envios_actualizados += 1
            else:
                logger.error(f"✗ Error al actualizar pedido {nro_pedido} en la base de datos")
                envios_con_error += 1
        else:
            logger.warning(
                f"✗ No se pudo obtener información del envío {num_seguimiento} "
                f"(Pedido: {nro_pedido})"
            )
            envios_con_error += 1

        # Pequeña pausa entre llamadas a la API
        await asyncio.sleep(0.5)

    logger.info("=== Resumen de actualización ===")
    logger.info(f"Total envíos procesados: {len(envios_pendientes)}")
    logger.info(f"Actualizados exitosamente: {envios_actualizados}")
    logger.info(f"Con errores: {envios_con_error}")


async def main():
    """Función principal para ejecutar la consulta desde la línea de comandos."""
    parser = argparse.ArgumentParser(
        description="Consultar y actualizar estados de envíos Andreani desde sucursal."
    )
    parser.add_argument(
        "--numero_envio",
        type=str,
        help="Número de seguimiento específico a consultar (opcional)."
    )
    parser.add_argument(
        "--actualizar",
        action="store_true",
        help="Actualizar todos los estados de envíos pendientes en la base de datos."
    )

    args = parser.parse_args()

    if args.actualizar:
        await actualizar_estados_envios()
    elif args.numero_envio:
        db = AndreaniSucDB()
        resultado = await consultar_estado_envio_api(args.numero_envio)

        if resultado:
            print("\nInformación del envío:")
            print(resultado)

            nro_pedido, _ = db.get_pedido_by_seguimiento(args.numero_envio)

            estado = resultado.get("estado")
            estado_id = resultado.get("estadoId")
            fecha_estado = resultado.get("fechaEstado")

            if db.update_estado_envio(args.numero_envio, estado, estado_id, fecha_estado):
                print(
                    f"\n✓ Estado actualizado en la base de datos "
                    f"para el envío {args.numero_envio}"
                )
            else:
                print("\n✗ No se pudo actualizar el estado en la base de datos")
        else:
            print("\nNo se pudo obtener información para el envío especificado.")
    else:
        # Por defecto ejecutar actualización masiva
        print("Ejecutando actualización masiva de estados de envíos desde sucursal...")
        await actualizar_estados_envios()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(main())
