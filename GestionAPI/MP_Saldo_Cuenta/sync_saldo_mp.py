#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script principal de sincronización para MP_Saldo_Cuenta.

Flujo:
  1. Consultar el saldo de la cuenta de Mercado Pago via API.
  2. Insertar el resultado en la tabla MP_T_SALDO_CUENTA (LAKER_SA, XL-TANGO).
  3. Loguear el resultado en logs/app.log.

Uso:
    python sync_saldo_mp.py

Diseñado para ejecutarse periódicamente (Task Scheduler de Windows, cron, etc.)
"""

import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, project_root)

import asyncio

from GestionAPI.common.logger_config import setup_logger
from GestionAPI.common.credenciales import MERCADOPAGO
from GestionAPI.MP_Saldo_Cuenta.api_mp_saldo import consultar_saldo
from GestionAPI.MP_Saldo_Cuenta.db_operations_mp_saldo import MercadoPagoSaldoDB

_module_dir = os.path.dirname(__file__)
logger = setup_logger(
    "mp_saldo_cuenta",
    log_path=os.path.join(_module_dir, "logs", "app.log"),
)


async def main():
    logger.info("=== Inicio sync saldo Mercado Pago ===")

    # 1. Consultar saldo via API
    saldo = await consultar_saldo(MERCADOPAGO["access_token"])
    if saldo is None:
        logger.error("No se pudo obtener el saldo. Proceso abortado.")
        sys.exit(1)

    logger.info(
        f"Saldo obtenido: available={saldo.get('available_balance')} ARS | "
        f"fuente={saldo.get('fuente')}"
    )

    # 2. Guardar en base de datos
    db = MercadoPagoSaldoDB()
    ok = db.insertar_saldo(saldo)
    if not ok:
        logger.error("Error al guardar el saldo en la base de datos.")
        sys.exit(1)

    logger.info("=== Sync completado exitosamente ===")


if __name__ == "__main__":
    asyncio.run(main())
