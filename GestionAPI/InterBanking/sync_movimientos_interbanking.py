#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script principal de sincronización — InterBanking Movimientos.
Obtiene movimientos desde GET /accounts/{account-number}/movements/{movement-type}
y los persiste en BI_T_MOVIMIENTOS_INTERBANKING (SQL Server).

Tipos disponibles:
    dia       → movimientos del día en curso (tiempo real, sin rango de fechas)
    diferidos → movimientos programados con fecha futura
    anteriores→ movimientos históricos (requiere --desde / --hasta)

Uso típico:
    python sync_movimientos_interbanking.py
    python sync_movimientos_interbanking.py --tipo diferidos
    python sync_movimientos_interbanking.py --tipo anteriores --desde 2026-10-01 --hasta 2026-10-13
"""

import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

import asyncio
import argparse
from datetime import datetime, date, timedelta
from typing import Dict, Optional

from GestionAPI.common.logger_config import setup_logger
from GestionAPI.common.credenciales import INTERBANKING
from GestionAPI.InterBanking.db_operations_movimientos import InterBankingMovimientosDB
from GestionAPI.InterBanking.interbanking_api import InterBankingAPIClient

logger = setup_logger(
    'interbanking_movimientos',
    log_path=os.path.join(os.path.dirname(__file__), 'logs', 'movimientos.log'),
)

LIMITE_POR_PAGINA = 100


async def sincronizar_cuenta(
    api_client: InterBankingAPIClient,
    db: InterBankingMovimientosDB,
    cuenta: dict,
    movement_type: str,
    date_since: Optional[str],
    date_until: Optional[str],
) -> Dict[str, int]:
    """
    Sincroniza todos los movimientos de una cuenta para el tipo dado.
    Itera páginas hasta agotar total_rows.

    Returns:
        dict con 'ok' y 'error'.
    """
    nro_banco  = cuenta['nro_banco']
    nro_cuenta = cuenta['nro_cuenta']
    tipo       = cuenta['tipo_cuenta']
    moneda     = cuenta['moneda']

    stats = {'ok': 0, 'error': 0}
    pagina = 0

    while True:
        respuesta = await api_client.obtener_movimientos(
            account_number=nro_cuenta,
            bank_number=nro_banco,
            movement_type=movement_type,
            account_type=tipo,
            currency=moneda,
            date_since=date_since,
            date_until=date_until,
            page=pagina,
            limit=LIMITE_POR_PAGINA,
        )

        if not respuesta:
            if pagina == 0:
                logger.info(
                    f"  Sin movimientos ({movement_type}) para banco {nro_banco} / cuenta {nro_cuenta}."
                )
            break

        movimientos = api_client.extraer_movimientos_planos(
            respuesta, nro_banco, nro_cuenta, tipo, moneda, movement_type
        )

        if movimientos:
            parcial = db.upsert_movimientos_batch(movimientos)
            stats['ok']    += parcial['ok']
            stats['error'] += parcial['error']

        # Verificar si hay más páginas
        gd = respuesta.get('general_data') or {}
        total_rows = gd.get('total_rows', 0) or 0
        limit_resp  = gd.get('limit', LIMITE_POR_PAGINA) or LIMITE_POR_PAGINA
        registros_hasta_ahora = (pagina + 1) * limit_resp

        if registros_hasta_ahora >= total_rows or not movimientos:
            break

        pagina += 1

    return stats


async def main(movement_type: str, date_since: Optional[str], date_until: Optional[str]):
    logger.info("=" * 80)
    logger.info("SINCRONIZACIÓN INTERBANKING — MOVIMIENTOS")
    logger.info(f"Tipo: {movement_type}")
    if date_since:
        logger.info(f"Rango: {date_since}  →  {date_until or 'sin límite'}")
    logger.info("=" * 80)

    inicio_proceso = datetime.now()

    api_client = InterBankingAPIClient(INTERBANKING)
    db = InterBankingMovimientosDB()

    try:
        db.crear_tabla_si_no_existe()

        cuentas = db.obtener_cuentas()
        if not cuentas:
            logger.error(
                "No se encontraron cuentas en BI_T_SALDOS_INTERBANKING. "
                "Ejecutar sync_saldos_interbanking.py primero."
            )
            return

        logger.info(f"Cuentas a procesar: {len(cuentas)}")
        for c in cuentas:
            logger.info(f"  Banco {c['nro_banco']} — Cuenta {c['nro_cuenta']} ({c['tipo_cuenta']}/{c['moneda']})")

        total_ok = 0
        total_error = 0

        for i, cuenta in enumerate(cuentas, 1):
            logger.info(
                f"\n[{i}/{len(cuentas)}] Banco {cuenta['nro_banco']} — "
                f"Cuenta {cuenta['nro_cuenta']}"
            )
            stats = await sincronizar_cuenta(
                api_client, db, cuenta, movement_type, date_since, date_until
            )
            logger.info(
                f"  Movimientos guardados: {stats['ok']} | "
                f"Errores: {stats['error']}"
            )
            total_ok    += stats['ok']
            total_error += stats['error']

        duracion = datetime.now() - inicio_proceso
        logger.info("\n" + "=" * 80)
        logger.info("RESUMEN")
        logger.info("=" * 80)
        logger.info(f"Tipo de movimiento: {movement_type}")
        logger.info(f"Cuentas procesadas:            {len(cuentas)}")
        logger.info(f"Movimientos guardados / actlz: {total_ok}")
        logger.info(f"Con error:                     {total_error}")
        logger.info(f"Duración:                      {duracion.total_seconds():.1f} segundos")
        logger.info("=" * 80)

        if total_error == 0:
            logger.info("✓ Sincronización de movimientos completada exitosamente")
        else:
            logger.warning(f"⚠ Sincronización completada con {total_error} errores")

    except Exception as e:
        logger.error(f"Error crítico en sincronización de movimientos: {e}", exc_info=True)
        raise
    finally:
        await api_client.close()


def _parse_args():
    parser = argparse.ArgumentParser(description="Sincronización de movimientos InterBanking")
    parser.add_argument(
        '--tipo',
        type=str,
        default='dia',
        choices=['dia', 'diferidos', 'anteriores'],
        help="Tipo de movimiento: dia (default), diferidos, anteriores",
    )
    parser.add_argument(
        '--desde', type=str, default=None,
        help='Fecha inicio yyyy-mm-dd (requerido para --tipo anteriores)'
    )
    parser.add_argument(
        '--hasta', type=str, default=None,
        help='Fecha fin yyyy-mm-dd (requerido para --tipo anteriores)'
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()

    date_since = None
    date_until = None

    if args.tipo == 'anteriores':
        if not args.desde:
            ayer = date.today() - timedelta(days=1)
            date_since = str(ayer - timedelta(days=6))
            date_until = str(ayer)
        else:
            date_since = args.desde
            date_until = args.hasta or str(date.today() - timedelta(days=1))
    elif args.desde:
        # Permite --desde / --hasta para cualquier tipo
        date_since = args.desde
        date_until = args.hasta

    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        asyncio.run(main(args.tipo, date_since, date_until))
    except KeyboardInterrupt:
        logger.info("Sincronización interrumpida por el usuario")
    except Exception as e:
        logger.error(f"Error fatal: {e}", exc_info=True)
        sys.exit(1)
