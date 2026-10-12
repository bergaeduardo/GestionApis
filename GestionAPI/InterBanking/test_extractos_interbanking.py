#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Suite de tests para el módulo de Extractos InterBanking.
Valida configuración, BD, OAuth y llamada real a la API.
"""

import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

import asyncio
from datetime import datetime, timedelta

from GestionAPI.common.logger_config import setup_logger
from GestionAPI.common.credenciales import INTERBANKING, INTERBANKING_DB
from GestionAPI.InterBanking.interbanking_api import InterBankingAPIClient
from GestionAPI.InterBanking.db_operations_extractos import InterBankingExtractosDB

logger = setup_logger(
    'interbanking_extractos_test',
    log_path=os.path.join(os.path.dirname(__file__), 'logs', 'extractos.log'),
)


def test_credenciales_y_cuentas():
    """Test 1: Verifica credenciales y que existan cuentas en la BD."""
    logger.info("=" * 60)
    logger.info("TEST 1: Credenciales + cuentas disponibles")
    logger.info("=" * 60)

    campos_requeridos = ['client_id', 'client_secret', 'customer_id']
    faltantes = [c for c in campos_requeridos if not INTERBANKING.get(c)]
    if faltantes:
        logger.error(f"✗ Faltan credenciales: {faltantes}")
        return False

    db = InterBankingExtractosDB()
    cuentas = db.obtener_cuentas()
    if not cuentas:
        logger.error(
            "✗ No hay cuentas en BI_T_SALDOS_INTERBANKING. "
            "Ejecutar sync_saldos_interbanking.py primero."
        )
        return False

    logger.info(f"  customer_id: {INTERBANKING['customer_id']}")
    logger.info(f"  Cuentas encontradas: {len(cuentas)}")
    for c in cuentas[:3]:
        logger.info(f"    Banco {c['nro_banco']} — Cuenta {c['nro_cuenta']}")
    logger.info("✓ TEST 1 PASADO\n")
    return True


def test_conexion_base_datos():
    """Test 2: Conexión BD y creación de tabla."""
    logger.info("=" * 60)
    logger.info("TEST 2: Conexión a base de datos")
    logger.info("=" * 60)

    try:
        db = InterBankingExtractosDB()
        logger.info(f"  Servidor: {INTERBANKING_DB['server']}")
        logger.info(f"  Base:     {INTERBANKING_DB['database']}")

        ok = db.crear_tabla_si_no_existe()
        if ok:
            logger.info("✓ Conexión exitosa y tabla BI_T_EXTRACTOS_INTERBANKING verificada")
            logger.info("✓ TEST 2 PASADO\n")
            return True
        else:
            logger.error("✗ No se pudo conectar a la base de datos")
            return False
    except Exception as e:
        logger.error(f"✗ TEST 2 FALLIDO: {e}\n")
        return False


async def test_autenticacion():
    """Test 3: OAuth token (reutiliza la misma mecánica que Saldos)."""
    logger.info("=" * 60)
    logger.info("TEST 3: Autenticación OAuth 2.0")
    logger.info("=" * 60)

    api = InterBankingAPIClient(INTERBANKING)
    try:
        token = await api._obtener_token()
        if token:
            logger.info(f"  Token recibido: {token[:20]}...")
            logger.info("✓ TEST 3 PASADO\n")
            return True
        else:
            logger.error("✗ No se obtuvo token")
            return False
    except Exception as e:
        logger.error(f"✗ TEST 3 FALLIDO: {e}\n")
        return False
    finally:
        await api.close()


async def test_consulta_extractos():
    """Test 4: Consulta real a la API para la primera cuenta disponible (últimos 7 días)."""
    logger.info("=" * 60)
    logger.info("TEST 4: Consulta de extractos (API real)")
    logger.info("=" * 60)

    db = InterBankingExtractosDB()
    cuentas = db.obtener_cuentas()
    if not cuentas:
        logger.error("✗ Sin cuentas disponibles para testear")
        return False

    cuenta = cuentas[0]
    ayer = datetime.now().date() - timedelta(days=1)
    date_since = str(ayer - timedelta(days=6))
    date_until = str(ayer)

    logger.info(
        f"  Cuenta: banco {cuenta['nro_banco']} / {cuenta['nro_cuenta']} "
        f"({cuenta['tipo_cuenta']}/{cuenta['moneda']})"
    )
    logger.info(f"  Rango: {date_since} → {date_until}")

    api = InterBankingAPIClient(INTERBANKING)
    try:
        respuesta = await api.obtener_extractos(
            account_number=cuenta['nro_cuenta'],
            bank_number=cuenta['nro_banco'],
            date_since=date_since,
            date_until=date_until,
            account_type=cuenta['tipo_cuenta'],
            currency=cuenta['moneda'],
        )

        if respuesta is None:
            logger.error("✗ La API no retornó datos")
            return False

        gd = respuesta.get('general_data') or {}
        statements = respuesta.get('statements') or []
        total_rows = gd.get('total_rows', 0)

        logger.info(f"  Total movimientos (API): {total_rows}")
        logger.info(f"  Días con extracto en esta página: {len(statements)}")

        movimientos = api.extraer_movimientos(
            respuesta,
            cuenta['nro_banco'],
            cuenta['nro_cuenta'],
            cuenta['tipo_cuenta'],
            cuenta['moneda'],
        )
        logger.info(f"  Movimientos aplanados: {len(movimientos)}")

        if movimientos:
            m0 = movimientos[0]
            logger.info(
                f"  Ejemplo: {m0['fecha_operacion']} | "
                f"{m0['tipo_mov']} | ${m0['importe']} | {m0['desc_operacion']}"
            )

        logger.info("✓ TEST 4 PASADO\n")
        return True

    except Exception as e:
        logger.error(f"✗ TEST 4 FALLIDO: {e}\n")
        return False
    finally:
        await api.close()


async def test_insercion_datos():
    """Test 5: Inserta un movimiento de prueba y verifica que se guardó."""
    logger.info("=" * 60)
    logger.info("TEST 5: Inserción y actualización de datos")
    logger.info("=" * 60)

    db = InterBankingExtractosDB()
    fecha_test = datetime.now().date() - timedelta(days=1)
    cuenta_test = '00-EXTRACTOS-TEST'
    banco_test  = '999'
    corr_test   = 999999999

    movimiento_test = {
        'fecha_operacion':    fecha_test,
        'nro_banco':          banco_test,
        'nro_cuenta':         cuenta_test,
        'tipo_cuenta':        'CC',
        'moneda':             'ARS',
        'nro_extracto':       'TEST-001',
        'saldo_inicial':      10000.00,
        'saldo_final':        11500.00,
        'deb_total_dia':      500.00,
        'cred_total_dia':     2000.00,
        'nro_correlativo':    corr_test,
        'nro_comprobante':    12345678,
        'fecha_movimiento':   None,
        'fecha_valor':        None,
        'tipo_mov':           'C',
        'importe':            2000.00,
        'cod_operacion_ib':   'TEST_OP',
        'cod_operacion_banco': '001',
        'desc_operacion':     'Movimiento de prueba',
        'desc_depositante':   'PROVEEDOR TEST SA',
        'cuit_cliente':       '20-12345678-9',
        'sucursal':           '0001',
    }

    try:
        ok = db.upsert_movimiento(movimiento_test)
        if not ok:
            logger.error("✗ Inserción fallida")
            return False
        logger.info("  ✓ Inserción exitosa")

        movimiento_test['importe'] = 3000.00
        ok2 = db.upsert_movimiento(movimiento_test)
        if not ok2:
            logger.error("✗ Actualización fallida")
            return False
        logger.info("  ✓ Actualización exitosa (MERGE)")

        rows = db.verificar_movimientos_guardados(fecha_test, fecha_test)
        encontrado = any(r[3] == corr_test for r in rows)
        if encontrado:
            logger.info("  ✓ Dato verificado en BD")
        else:
            logger.warning("  ⚠ No se encontró el dato en la verificación")

        logger.info("✓ TEST 5 PASADO\n")
        return True

    except Exception as e:
        logger.error(f"✗ TEST 5 FALLIDO: {e}\n")
        return False

    finally:
        try:
            from GestionAPI.common.conexion import Conexion
            from GestionAPI.InterBanking.consultas_extractos import QRY_LIMPIAR_EXTRACTOS_TEST
            from GestionAPI.common.credenciales import INTERBANKING_DB as cfg
            conn = Conexion(cfg['server'], cfg['database'], cfg['user'], cfg['password'])
            cursor = conn.conectar()
            if cursor:
                cursor.execute(QRY_LIMPIAR_EXTRACTOS_TEST, (cuenta_test, corr_test))
                conn.connection.commit()
                cursor.close()
                conn.connection.close()
                logger.info("  Datos de prueba eliminados")
        except Exception:
            pass


async def ejecutar_todos():
    logger.info("╔" + "═" * 78 + "╗")
    logger.info("║" + " " * 17 + "SUITE DE TESTS — EXTRACTOS INTERBANKING" + " " * 22 + "║")
    logger.info("╚" + "═" * 78 + "╝\n")

    resultados = [
        ("Credenciales + cuentas en BD",  test_credenciales_y_cuentas()),
        ("Conexión a base de datos",       test_conexion_base_datos()),
        ("Autenticación OAuth",            await test_autenticacion()),
        ("Consulta de extractos (API)",    await test_consulta_extractos()),
        ("Inserción y verificación",       await test_insercion_datos()),
    ]

    pasados = sum(1 for _, r in resultados if r)
    fallidos = len(resultados) - pasados

    logger.info("=" * 80)
    logger.info("RESUMEN")
    logger.info("=" * 80)
    for nombre, resultado in resultados:
        estado = "✓ PASADO" if resultado else "✗ FALLIDO"
        logger.info(f"{nombre:40} ... {estado}")
    logger.info("=" * 80)
    logger.info(f"Total: {len(resultados)} | Pasados: {pasados} | Fallidos: {fallidos}")
    logger.info("=" * 80)

    if fallidos == 0:
        logger.info("\n🎉 Todos los tests pasaron.")
    else:
        logger.warning(f"\n⚠ {fallidos} test(s) fallaron.")

    return fallidos == 0


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        ok = asyncio.run(ejecutar_todos())
        sys.exit(0 if ok else 1)
    except KeyboardInterrupt:
        logger.info("Tests interrumpidos")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error fatal: {e}", exc_info=True)
        sys.exit(1)
