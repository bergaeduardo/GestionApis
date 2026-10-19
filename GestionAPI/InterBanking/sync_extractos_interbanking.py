#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script principal de sincronización — InterBanking Extractos.
Obtiene los movimientos bancarios desde GET /accounts/{account-number}/statements
y los persiste en BI_T_EXTRACTOS_INTERBANKING (SQL Server).

Rango por defecto: mes anterior completo.
La API limita a 60 días por consulta y 180 días de historia.
Cada cuenta requiere una llamada separada; se paginan automáticamente.

Uso típico:
    python sync_extractos_interbanking.py
    python sync_extractos_interbanking.py --mes 2026-08
    python sync_extractos_interbanking.py --desde 2026-09-01 --hasta 2026-09-15
"""

import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

import asyncio
import argparse
from calendar import monthrange
from datetime import datetime, date, timedelta
from typing import Dict

from GestionAPI.common.logger_config import setup_logger
from GestionAPI.common.credenciales import INTERBANKING
from GestionAPI.InterBanking.db_operations_extractos import InterBankingExtractosDB
from GestionAPI.InterBanking.interbanking_api import InterBankingAPIClient

logger = setup_logger(
    'interbanking_extractos',
    log_path=os.path.join(os.path.dirname(__file__), 'logs', 'extractos.log'),
)

LIMITE_POR_PAGINA = 100


async def sincronizar_cuenta(
    api_client: InterBankingAPIClient,
    db: InterBankingExtractosDB,
    cuenta: dict,
    date_since: str,
    date_until: str,
) -> Dict[str, int]:
    """
    Sincroniza todos los movimientos de una cuenta en el rango dado.
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
        respuesta = await api_client.obtener_extractos(
            account_number=nro_cuenta,
            bank_number=nro_banco,
            date_since=date_since,
            date_until=date_until,
            account_type=tipo,
            currency=moneda,
            page=pagina,
            limit=LIMITE_POR_PAGINA,
        )

        if not respuesta:
            if pagina == 0:
                logger.warning(
                    f"  Sin respuesta para banco {nro_banco} / cuenta {nro_cuenta}."
                )
            break

        movimientos = api_client.extraer_movimientos(
            respuesta, nro_banco, nro_cuenta, tipo, moneda
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


async def main(ranges: list, purgar: bool = False):
    """
    Sincroniza extractos para uno o más rangos de fecha.

    Args:
        ranges: lista de tuplas (date_since, date_until) en formato 'YYYY-MM-DD'.
        purgar: si True, elimina registros anteriores al mes anterior tras la sync.
    """
    logger.info("=" * 80)
    logger.info("SINCRONIZACIÓN INTERBANKING — EXTRACTOS")
    for ds, du in ranges:
        logger.info(f"Rango: {ds}  →  {du}")
    logger.info("=" * 80)

    inicio_proceso = datetime.now()

    api_client = InterBankingAPIClient(INTERBANKING)
    db = InterBankingExtractosDB()

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

        for rango_idx, (date_since, date_until) in enumerate(ranges, 1):
            logger.info(f"\n--- Rango {rango_idx}/{len(ranges)}: {date_since} → {date_until} ---")
            for i, cuenta in enumerate(cuentas, 1):
                logger.info(
                    f"\n[{i}/{len(cuentas)}] Banco {cuenta['nro_banco']} — "
                    f"Cuenta {cuenta['nro_cuenta']}"
                )
                stats = await sincronizar_cuenta(api_client, db, cuenta, date_since, date_until)
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
        logger.info(f"Cuentas procesadas:  {len(cuentas)}")
        logger.info(f"Movimientos guardados / actualizados: {total_ok}")
        logger.info(f"Con error:           {total_error}")
        logger.info(f"Duración:            {duracion.total_seconds():.1f} segundos")
        logger.info("=" * 80)

        if total_error == 0:
            logger.info("✓ Sincronización de extractos completada exitosamente")
        else:
            logger.warning(f"⚠ Sincronización completada con {total_error} errores")

        if purgar:
            logger.info("\n--- Purgando registros históricos ---")
            corte = _primer_dia_mes_anterior()
            db.purgar_historicos(corte)

    except Exception as e:
        logger.error(f"Error crítico en sincronización de extractos: {e}", exc_info=True)
        raise
    finally:
        await api_client.close()


def _primer_dia_mes_anterior() -> date:
    """Retorna el primer día del mes anterior."""
    hoy = date.today()
    primer_dia_actual = hoy.replace(day=1)
    ultimo_dia_ant = primer_dia_actual - timedelta(days=1)
    return ultimo_dia_ant.replace(day=1)


def _mes_anterior() -> tuple:
    """Retorna (date_since, date_until) del mes calendario anterior."""
    primer = _primer_dia_mes_anterior()
    hoy = date.today()
    primer_dia_actual = hoy.replace(day=1)
    ultimo_dia_ant = primer_dia_actual - timedelta(days=1)
    return str(primer), str(ultimo_dia_ant)


def _dos_meses() -> list:
    """
    Retorna dos rangos: mes anterior completo + mes en curso hasta hoy.
    Siempre se generan rangos separados para respetar el límite de 60 días de la API.
    """
    hoy = date.today()
    primer_dia_actual = hoy.replace(day=1)
    ultimo_dia_ant = primer_dia_actual - timedelta(days=1)
    primer_dia_ant = ultimo_dia_ant.replace(day=1)
    return [
        (str(primer_dia_ant), str(ultimo_dia_ant)),   # mes anterior completo
        (str(primer_dia_actual), str(hoy)),            # mes en curso hasta hoy
    ]


def _parse_args():
    parser = argparse.ArgumentParser(description="Sincronización de extractos InterBanking")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '--dos-meses', action='store_true', default=False,
        help='Sincroniza mes anterior completo + mes en curso hasta hoy (recomendado para cron)'
    )
    group.add_argument(
        '--mes', type=str, default=None,
        help='Mes a procesar en formato YYYY-MM (default: mes anterior)'
    )
    group.add_argument(
        '--desde', type=str, default=None,
        help='Fecha inicio yyyy-mm-dd (requiere --hasta)'
    )
    parser.add_argument(
        '--hasta', type=str, default=None,
        help='Fecha fin yyyy-mm-dd (usado junto a --desde)'
    )
    parser.add_argument(
        '--purgar', action='store_true', default=False,
        help='Elimina registros anteriores al mes anterior tras la sincronización'
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()

    if args.dos_meses:
        ranges = _dos_meses()
    elif args.desde:
        date_since = args.desde
        date_until = args.hasta or str(date.today() - timedelta(days=1))
        ranges = [(date_since, date_until)]
    elif args.mes:
        try:
            año, mes = map(int, args.mes.split('-'))
            _, ultimo_dia = monthrange(año, mes)
            date_since = f"{año:04d}-{mes:02d}-01"
            date_until = f"{año:04d}-{mes:02d}-{ultimo_dia:02d}"
            ranges = [(date_since, date_until)]
        except ValueError:
            print("Error: --mes debe tener formato YYYY-MM (ej: 2026-09)")
            sys.exit(1)
    else:
        date_since, date_until = _mes_anterior()
        ranges = [(date_since, date_until)]

    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        asyncio.run(main(ranges, purgar=args.purgar))
    except KeyboardInterrupt:
        logger.info("Sincronización interrumpida por el usuario")
    except Exception as e:
        logger.error(f"Error fatal: {e}", exc_info=True)
        sys.exit(1)
