#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script principal de sincronización para MP_Saldo_Demanda.

Genera un reporte bajo demanda en la API de Mercado Pago (ayer 00:00 → ahora),
espera a que esté disponible (1-5 min) y persiste:
  - MP_T_SALDO_DEMANDA         : 1 fila resumen con el saldo final
  - MP_T_SALDO_DEMANDA_DETALLE : 1 fila por cada movimiento del reporte (para validación)

Uso:
    python sync_saldo_demanda.py

Tiempo de ejecución estimado: 2-5 minutos.
"""

import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, project_root)

import asyncio

from GestionAPI.common.logger_config import setup_logger
from GestionAPI.common.credenciales import MERCADOPAGO
from GestionAPI.MP_Saldo_Demanda.api_mp_demanda import MercadoPagoDemandaClient
from GestionAPI.MP_Saldo_Demanda.db_mp_demanda import MercadoPagoDemandaDB

_module_dir = os.path.dirname(__file__)
logger = setup_logger(
    "mp_saldo_demanda",
    log_path=os.path.join(_module_dir, "logs", "app.log"),
)


async def main():
    logger.info("=== Inicio sync saldo Mercado Pago (demanda) ===")
    logger.info("Generando reporte bajo demanda. Esto puede tardar 2-5 minutos...")

    client = MercadoPagoDemandaClient(MERCADOPAGO["access_token"])
    db = MercadoPagoDemandaDB()

    try:
        resultado = await client.get_resultado_completo()
        if resultado is None:
            logger.error("No se pudo obtener el reporte. Proceso abortado.")
            sys.exit(1)

        saldo = resultado["saldo"]
        filas = resultado["filas"]
        file_name = resultado["file_name"]

        logger.info(
            f"Reporte procesado: {len(filas)} filas | "
            f"available={saldo.get('available_balance')} ARS | "
            f"período={saldo.get('begin_date')} → {saldo.get('end_date')}"
        )

        # Guardar resumen
        ok_resumen = db.insertar_saldo(saldo)
        if not ok_resumen:
            logger.error("Error al guardar el resumen en la base de datos.")
            sys.exit(1)

        # Guardar detalle (todas las filas del CSV)
        stats = db.insertar_detalle(
            filas=filas,
            sync_timestamp=saldo["timestamp"],
            user_id=saldo["user_id"],
            file_name=file_name,
        )
        logger.info(f"Detalle: {stats['insertados']} filas insertadas | {stats['errores']} errores")

    finally:
        await client.close()

    logger.info("=== Sync demanda completado exitosamente ===")


if __name__ == "__main__":
    asyncio.run(main())
