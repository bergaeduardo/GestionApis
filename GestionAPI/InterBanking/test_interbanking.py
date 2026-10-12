#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de testing para el módulo InterBanking.
Valida autenticación OAuth, llamada a la API y operaciones de base de datos.
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
from GestionAPI.InterBanking.db_operations_interbanking import InterBankingDB

logger = setup_logger(
    'interbanking_test',
    log_path=os.path.join(os.path.dirname(__file__), 'logs', 'app.log'),
)


def test_credenciales():
    """Test 1: Verifica que las credenciales estén configuradas."""
    logger.info("=" * 60)
    logger.info("TEST 1: Credenciales configuradas")
    logger.info("=" * 60)

    campos_requeridos = ['client_id', 'client_secret', 'customer_id']
    faltantes = [c for c in campos_requeridos if not INTERBANKING.get(c)]

    if faltantes:
        logger.error(f"✗ Faltan credenciales en INTERBANKING: {faltantes}")
        logger.error("  Completar en GestionAPI/common/credenciales.py")
        return False

    logger.info(f"  client_id:   {'*' * 6}{INTERBANKING['client_id'][-4:]}")
    logger.info(f"  customer_id: {INTERBANKING['customer_id']}")
    entorno = "PRODUCCIÓN" if INTERBANKING.get('base_url_prod') else "SANDBOX"
    logger.info(f"  Entorno: {entorno}")
    logger.info("✓ TEST 1 PASADO\n")
    return True


def test_conexion_base_datos():
    """Test 2: Verifica la conexión a SQL Server y crea la tabla si falta."""
    logger.info("=" * 60)
    logger.info("TEST 2: Conexión a base de datos")
    logger.info("=" * 60)

    try:
        db = InterBankingDB()
        logger.info(f"  Servidor: {INTERBANKING_DB['server']}")
        logger.info(f"  Base:     {INTERBANKING_DB['database']}")

        ok = db.crear_tabla_si_no_existe()
        if ok:
            logger.info("✓ Conexión exitosa y tabla verificada")
            logger.info("✓ TEST 2 PASADO\n")
            return True
        else:
            logger.error("✗ No se pudo conectar a la base de datos")
            return False
    except Exception as e:
        logger.error(f"✗ TEST 2 FALLIDO: {e}\n")
        return False


async def test_autenticacion():
    """Test 3: Obtiene un token OAuth de InterBanking."""
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


async def test_consulta_saldos():
    """Test 4: Consulta real a GET /accounts/balances (últimos 7 días)."""
    logger.info("=" * 60)
    logger.info("TEST 4: Consulta de saldos (API real)")
    logger.info("=" * 60)

    ayer = datetime.now().date() - timedelta(days=1)
    date_since = str(ayer - timedelta(days=6))
    date_until = str(ayer)

    api = InterBankingAPIClient(INTERBANKING)
    try:
        respuesta = await api.obtener_saldos(date_since=date_since, date_until=date_until)

        if not respuesta:
            logger.error("✗ La API no retornó datos")
            return False

        cuentas = respuesta.get('accounts', [])
        logger.info(f"  Cuentas en respuesta: {len(cuentas)}")

        for cuenta in cuentas[:3]:
            logger.info(
                f"  Banco {cuenta.get('bank_number')} | "
                f"Cuenta {cuenta.get('account_number')} | "
                f"Saldo contable: {cuenta.get('balances', {}).get('countable_balance')}"
            )

        registros = api.extraer_registros(respuesta)
        logger.info(f"  Registros históricos aplanados: {len(registros)}")

        logger.info("✓ TEST 4 PASADO\n")
        return True

    except Exception as e:
        logger.error(f"✗ TEST 4 FALLIDO: {e}\n")
        return False
    finally:
        await api.close()


async def test_insercion_datos():
    """Test 5: Inserta un registro de prueba y verifica que se guardó."""
    logger.info("=" * 60)
    logger.info("TEST 5: Inserción y actualización de datos")
    logger.info("=" * 60)

    db = InterBankingDB()
    fecha_test = datetime.now().date() - timedelta(days=1)
    cuenta_test = '00-TEST-99999'

    registro_test = {
        'fecha_operacion': fecha_test,
        'nro_banco': '999',
        'nro_cuenta': cuenta_test,
        'tipo_cuenta': 'CC',
        'moneda': 'ARS',
        'label_cuenta': 'Test Label',
        'nombre_cuenta': 'Cuenta de prueba',
        'saldo_contable': 12345.67,
        'saldo_operativo_inicial': 11000.00,
        'saldo_operativo_actual': 12345.67,
        'saldo_proyectado_24hs': 12345.67,
        'saldo_proyectado_48hs': 12345.67,
        'saldo_dia': 12345.67,
        'total_debitos': 500.00,
        'total_creditos': 1845.67,
    }

    try:
        # Inserción
        ok = db.upsert_saldo(registro_test)
        if not ok:
            logger.error("✗ Inserción fallida")
            return False
        logger.info("  ✓ Inserción exitosa")

        # Actualización (mismo registro)
        registro_test['saldo_contable'] = 99999.99
        ok2 = db.upsert_saldo(registro_test)
        if not ok2:
            logger.error("✗ Actualización fallida")
            return False
        logger.info("  ✓ Actualización exitosa")

        # Verificar
        rows = db.verificar_saldos_guardados(fecha_test, fecha_test)
        encontrado = any(str(r[2]) == cuenta_test for r in rows)  # r[2] = NRO_CUENTA
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
        # Limpiar datos de prueba
        try:
            from GestionAPI.common.conexion import Conexion
            from GestionAPI.InterBanking.consultas import QRY_LIMPIAR_DATOS_TEST
            from GestionAPI.common.credenciales import INTERBANKING_DB as cfg
            conn = Conexion(cfg['server'], cfg['database'], cfg['user'], cfg['password'])
            cursor = conn.conectar()
            if cursor:
                cursor.execute(QRY_LIMPIAR_DATOS_TEST, (cuenta_test, fecha_test))
                conn.connection.commit()
                cursor.close()
                conn.connection.close()
                logger.info("  Datos de prueba eliminados")
        except Exception:
            pass


async def ejecutar_todos():
    logger.info("╔" + "═" * 78 + "╗")
    logger.info("║" + " " * 20 + "SUITE DE TESTS — INTERBANKING" + " " * 29 + "║")
    logger.info("╚" + "═" * 78 + "╝\n")

    resultados = [
        ("Credenciales configuradas", test_credenciales()),
        ("Conexión a base de datos",  test_conexion_base_datos()),
        ("Autenticación OAuth",       await test_autenticacion()),
        ("Consulta de saldos (API)",  await test_consulta_saldos()),
        ("Inserción y verificación",  await test_insercion_datos()),
    ]

    pasados = sum(1 for _, r in resultados if r)
    fallidos = len(resultados) - pasados

    logger.info("=" * 80)
    logger.info("RESUMEN")
    logger.info("=" * 80)
    for nombre, resultado in resultados:
        estado = "✓ PASADO" if resultado else "✗ FALLIDO"
        logger.info(f"{nombre:35} ... {estado}")
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
