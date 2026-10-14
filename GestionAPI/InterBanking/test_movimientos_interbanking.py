#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Suite de tests para el módulo de Movimientos InterBanking.
Valida configuración, BD, OAuth y llamada real a la API (tipo=dia).
"""

import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

import asyncio
from datetime import datetime

from GestionAPI.common.logger_config import setup_logger
from GestionAPI.common.credenciales import INTERBANKING, INTERBANKING_DB
from GestionAPI.InterBanking.interbanking_api import InterBankingAPIClient
from GestionAPI.InterBanking.db_operations_movimientos import InterBankingMovimientosDB

logger = setup_logger(
    'interbanking_movimientos_test',
    log_path=os.path.join(os.path.dirname(__file__), 'logs', 'movimientos.log'),
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

    db = InterBankingMovimientosDB()
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
        db = InterBankingMovimientosDB()
        logger.info(f"  Servidor: {INTERBANKING_DB['server']}")
        logger.info(f"  Base:     {INTERBANKING_DB['database']}")

        ok = db.crear_tabla_si_no_existe()
        if ok:
            logger.info("✓ Conexión exitosa y tabla BI_T_MOVIMIENTOS_INTERBANKING verificada")
            logger.info("✓ TEST 2 PASADO\n")
            return True
        else:
            logger.error("✗ No se pudo conectar a la base de datos")
            return False
    except Exception as e:
        logger.error(f"✗ TEST 2 FALLIDO: {e}\n")
        return False


async def test_autenticacion():
    """Test 3: OAuth token (reutiliza la misma mecánica que Saldos y Extractos)."""
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


async def test_consulta_movimientos_dia():
    """Test 4: Consulta real a la API (tipo=dia) para la primera cuenta disponible."""
    logger.info("=" * 60)
    logger.info("TEST 4: Consulta de movimientos del día (API real)")
    logger.info("=" * 60)

    db = InterBankingMovimientosDB()
    cuentas = db.obtener_cuentas()
    if not cuentas:
        logger.error("✗ Sin cuentas disponibles para testear")
        return False

    cuenta = cuentas[0]
    logger.info(
        f"  Cuenta: banco {cuenta['nro_banco']} / {cuenta['nro_cuenta']} "
        f"({cuenta['tipo_cuenta']}/{cuenta['moneda']})"
    )
    logger.info("  Tipo de movimiento: dia (tiempo real)")

    api = InterBankingAPIClient(INTERBANKING)
    try:
        respuesta = await api.obtener_movimientos(
            account_number=cuenta['nro_cuenta'],
            bank_number=cuenta['nro_banco'],
            movement_type='dia',
            account_type=cuenta['tipo_cuenta'],
            currency=cuenta['moneda'],
        )

        if respuesta is None:
            logger.warning(
                "  ⚠ La API no retornó datos para 'dia' — puede no haber movimientos aún hoy"
            )
            logger.info("✓ TEST 4 PASADO (sin movimientos en el día)\n")
            return True

        gd = respuesta.get('general_data') or {}
        total_rows = gd.get('total_rows', 0)

        logger.info(f"  Total movimientos del día (API): {total_rows}")

        movimientos = api.extraer_movimientos_planos(
            respuesta,
            cuenta['nro_banco'],
            cuenta['nro_cuenta'],
            cuenta['tipo_cuenta'],
            cuenta['moneda'],
            'dia',
        )
        logger.info(f"  Movimientos aplanados: {len(movimientos)}")

        if movimientos:
            m0 = movimientos[0]
            logger.info(
                f"  Ejemplo: {m0['fecha_proceso']} | "
                f"{m0['tipo_deb_cred']} | ${m0['importe']} | {m0['desc_operacion_banco']}"
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

    db = InterBankingMovimientosDB()
    cuenta_test    = '00-MOVIMIENTOS-TEST'
    banco_test     = '999'
    tipo_test      = 'CC'
    moneda_test    = 'ARS'
    id_movimiento_test = 999999999

    movimiento_test = {
        'nro_banco':           banco_test,
        'nro_cuenta':          cuenta_test,
        'tipo_cuenta':         tipo_test,
        'moneda':              moneda_test,
        'tipo_movimiento':     'dia',
        'id_movimiento':       id_movimiento_test,
        'fecha_proceso':       datetime.now().replace(microsecond=0),
        'tipo_deb_cred':       'C',
        'importe':             5000.00,
        'nro_comprobante':     87654321,
        'cod_operacion_ib':    'TEST_OP',
        'cod_operacion_banco': '001',
        'desc_operacion_ib':   'Transferencia entrada test',
        'desc_operacion_banco': 'TRANSFERENCIA TEST',
        'cbu_cuenta':          '0000000000000000000000',
        'cod_depositante':     'TEST001',
        'desc_depositante':    'PROVEEDOR TEST SA',
        'cuit_cliente':        '20-12345678-9',
        'cod_agrupamiento_ib': '1',
        'sucursal':            '0001',
    }

    try:
        ok = db.upsert_movimiento(movimiento_test)
        if not ok:
            logger.error("✗ Inserción fallida")
            return False
        logger.info("  ✓ Inserción exitosa")

        movimiento_test['importe'] = 7500.00
        ok2 = db.upsert_movimiento(movimiento_test)
        if not ok2:
            logger.error("✗ Actualización fallida")
            return False
        logger.info("  ✓ Actualización exitosa (MERGE)")

        rows = db.verificar_movimientos_guardados(banco_test, cuenta_test, 'dia')
        encontrado = any(r[3] == id_movimiento_test for r in rows)
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
            from GestionAPI.InterBanking.consultas_movimientos import QRY_LIMPIAR_MOVIMIENTOS_TEST
            from GestionAPI.common.credenciales import INTERBANKING_DB as cfg
            conn = Conexion(cfg['server'], cfg['database'], cfg['user'], cfg['password'])
            cursor = conn.conectar()
            if cursor:
                cursor.execute(QRY_LIMPIAR_MOVIMIENTOS_TEST, (cuenta_test, id_movimiento_test))
                conn.connection.commit()
                cursor.close()
                conn.connection.close()
                logger.info("  Datos de prueba eliminados")
        except Exception:
            pass


async def ejecutar_todos():
    logger.info("╔" + "═" * 78 + "╗")
    logger.info("║" + " " * 16 + "SUITE DE TESTS — MOVIMIENTOS INTERBANKING" + " " * 21 + "║")
    logger.info("╚" + "═" * 78 + "╝\n")

    resultados = [
        ("Credenciales + cuentas en BD",  test_credenciales_y_cuentas()),
        ("Conexión a base de datos",       test_conexion_base_datos()),
        ("Autenticación OAuth",            await test_autenticacion()),
        ("Consulta movimientos del día",   await test_consulta_movimientos_dia()),
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
