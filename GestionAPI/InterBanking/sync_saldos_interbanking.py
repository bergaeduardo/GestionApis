#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script principal de sincronización — InterBanking Saldos.
Obtiene saldos diarios históricos desde GET /accounts/balances
y los persiste en BI_T_SALDOS_INTERBANKING (SQL Server).

Uso típico:
    python sync_saldos_interbanking.py
    python sync_saldos_interbanking.py --days 30
    python sync_saldos_interbanking.py --desde 2024-01-01 --hasta 2024-01-31
"""

import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

import asyncio
import argparse
from datetime import datetime, timedelta

from GestionAPI.common.logger_config import setup_logger
from GestionAPI.common.credenciales import INTERBANKING
from GestionAPI.InterBanking.db_operations_interbanking import InterBankingDB
from GestionAPI.InterBanking.interbanking_api import InterBankingAPIClient

logger = setup_logger(
    'interbanking_saldos',
    log_path=os.path.join(os.path.dirname(__file__), 'logs', 'app.log'),
)

# Días de historia a sincronizar cuando no se especifica rango explícito
DIAS_POR_DEFECTO = 7


async def main(date_since: str, date_until: str):
    logger.info("=" * 80)
    logger.info("SINCRONIZACIÓN INTERBANKING — SALDOS DIARIOS")
    logger.info(f"Rango: {date_since}  →  {date_until}")
    logger.info("=" * 80)

    inicio_proceso = datetime.now()

    api_client = InterBankingAPIClient(INTERBANKING)
    db = InterBankingDB()

    try:
        # Garantizar que la tabla existe
        db.crear_tabla_si_no_existe()

        # Consultar saldos
        logger.info("Consultando /accounts/balances...")
        respuesta = await api_client.obtener_saldos(
            date_since=date_since,
            date_until=date_until,
        )

        if not respuesta:
            logger.error("La API no retornó datos. Abortando.")
            return

        # Extrae y aplana los registros
        registros = api_client.extraer_registros(respuesta)
        total_obtenidos = len(registros)
        logger.info(f"Registros obtenidos de la API: {total_obtenidos}")

        if not registros:
            logger.warning("No hay registros para persistir.")
            return

        # Mostrar resumen de cuentas encontradas
        cuentas = {(r['nro_banco'], r['nro_cuenta']) for r in registros}
        logger.info(f"Cuentas involucradas: {len(cuentas)}")
        for banco, cuenta in sorted(cuentas):
            logger.info(f"  Banco {banco} — Cuenta {cuenta}")

        # Persistir en SQL Server
        logger.info("Guardando en BI_T_SALDOS_INTERBANKING...")
        stats = db.upsert_saldos_batch(registros)

        # Resumen final
        duracion = datetime.now() - inicio_proceso
        logger.info("=" * 80)
        logger.info("RESUMEN")
        logger.info("=" * 80)
        logger.info(f"Registros procesados: {total_obtenidos}")
        logger.info(f"  Guardados / actualizados: {stats['ok']}")
        logger.info(f"  Sin histórico (omitidos): {stats.get('sin_historico', 0)}")
        logger.info(f"  Con error:                {stats['error']}")
        logger.info(f"Duración: {duracion.total_seconds():.1f} segundos")
        logger.info("=" * 80)

        if stats['error'] == 0:
            logger.info("✓ Sincronización completada exitosamente")
        else:
            logger.warning(f"⚠ Sincronización completada con {stats['error']} errores")

    except Exception as e:
        logger.error(f"Error crítico en sincronización: {e}", exc_info=True)
        raise
    finally:
        await api_client.close()


def _parse_args():
    parser = argparse.ArgumentParser(description="Sincronización de saldos InterBanking")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '--days', type=int, default=None,
        help=f'Días de historia hacia atrás desde ayer (default: {DIAS_POR_DEFECTO})'
    )
    group.add_argument(
        '--desde', type=str, default=None,
        help='Fecha inicio yyyy-mm-dd (requiere --hasta)'
    )
    parser.add_argument(
        '--hasta', type=str, default=None,
        help='Fecha fin yyyy-mm-dd (usado junto a --desde)'
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()

    hoy  = datetime.now().date()
    ayer = hoy - timedelta(days=1)

    if args.desde:
        date_since = args.desde
        date_until = args.hasta or str(ayer)
    else:
        dias = args.days if args.days is not None else DIAS_POR_DEFECTO
        # La API es T-1: date_until = ayer (datos confirmados del día anterior)
        date_since = str(ayer - timedelta(days=dias - 1))
        date_until = str(ayer)

    # Python 3.8 en Windows usa ProactorEventLoop que arroja RuntimeError al cerrar.
    # SelectorEventLoopPolicy evita ese ruido sin afectar el comportamiento.
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        asyncio.run(main(date_since, date_until))
    except KeyboardInterrupt:
        logger.info("Sincronización interrumpida por el usuario")
    except Exception as e:
        logger.error(f"Error fatal: {e}", exc_info=True)
        sys.exit(1)
