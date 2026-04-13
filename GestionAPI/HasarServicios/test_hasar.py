#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de testing para el módulo HasarServicios
Valida conexiones, consultas API y operaciones de base de datos
"""

import sys
import os

# Obtiene la ruta del directorio padre (la raíz del proyecto)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
# Añade la ruta de la raíz del proyecto a sys.path
sys.path.insert(0, project_root)

import asyncio
from datetime import datetime, timedelta

from GestionAPI.common.logger_config import setup_logger
from GestionAPI.HasarServicios.db_operations_hasar import HasarDB
from GestionAPI.HasarServicios.api_hasar import HasarAPIClient

# Configurar logger para tests
logger = setup_logger('hasar_test', log_path=os.path.join(os.path.dirname(__file__), 'logs', 'app.log'))


def test_conexion_base_datos():
    """
    Test 1: Verifica la conexión a las bases de datos configuradas.
    """
    logger.info("=" * 60)
    logger.info("TEST 1: Conexión a bases de datos")
    logger.info("=" * 60)
    
    try:
        db = HasarDB()
        
        # Test conexión a POWER_BI_CONTROL
        logger.info("Probando conexión a POWER_BI_CONTROL...")
        conexion = db._get_connection('POWER_BI_CONTROL')
        
        if conexion:
            logger.info("✓ Conexión a POWER_BI_CONTROL exitosa")
        else:
            logger.error("✗ No se pudo conectar a POWER_BI_CONTROL")
            return False
        
        # Test conexión a POWER_BI_CONTROL_FRANQUICIAS
        logger.info("Probando conexión a POWER_BI_CONTROL_FRANQUICIAS...")
        conexion2 = db._get_connection('POWER_BI_CONTROL_FRANQUICIAS')
        
        if conexion2:
            logger.info("✓ Conexión a POWER_BI_CONTROL_FRANQUICIAS exitosa")
        else:
            logger.error("✗ No se pudo conectar a POWER_BI_CONTROL_FRANQUICIAS")
            return False
        
        logger.info("✓ TEST 1 PASADO: Todas las conexiones exitosas\n")
        return True
        
    except Exception as e:
        logger.error(f"✗ TEST 1 FALLIDO: Error en conexión: {e}\n")
        return False


def test_lectura_configuracion():
    """
    Test 2: Verifica la lectura de la tabla de configuración EB_BilcCamdata_pdv.
    """
    logger.info("=" * 60)
    logger.info("TEST 2: Lectura de configuración de sucursales")
    logger.info("=" * 60)
    
    try:
        db = HasarDB()
        
        # Obtener estadísticas
        stats = db.obtener_estadisticas_config()
        logger.info(f"Estadísticas de configuración:")
        logger.info(f"  - Activos: {stats['Activos']}")
        logger.info(f"  - Inactivos: {stats['Inactivos']}")
        logger.info(f"  - Total: {stats['Total']}")
        
        # Obtener configuración activa
        configuraciones = db.obtener_configuracion_sucursales()
        
        if not configuraciones:
            logger.warning("⚠ No se encontraron sucursales activas")
            logger.warning("  Asegúrate de haber ejecutado el script SQL create_hasar_tables.sql\n")
            return False
        
        logger.info(f"\nSe encontraron {len(configuraciones)} configuraciones activas:")
        for config in configuraciones:
            logger.info(f"  - Sucursal {config['NUMERO_SUCURSAL']}: {config['NOMBRE_DASHBOARD']}")
            logger.info(f"    API: {config['API'][:50]}...")
            logger.info(f"    BD Destino: {config['DATA_BASE']}")
        
        logger.info("\n✓ TEST 2 PASADO: Configuración leída correctamente\n")
        return True
        
    except Exception as e:
        logger.error(f"✗ TEST 2 FALLIDO: Error al leer configuración: {e}\n")
        return False


async def test_llamada_api():
    """
    Test 3: Verifica la llamada a una API real de HasarServicios (asíncrono).
    """
    logger.info("=" * 60)
    logger.info("TEST 3: Llamada a API de HasarServicios")
    logger.info("=" * 60)
    
    try:
        db = HasarDB()
        api_client = HasarAPIClient()
        
        # Obtener primera configuración activa para probar
        configuraciones = db.obtener_configuracion_sucursales()
        
        if not configuraciones:
            logger.warning("⚠ No hay configuraciones activas para probar API\n")
            return False
        
        config_test = configuraciones[0]
        logger.info(f"Probando API: {config_test['NOMBRE_DASHBOARD']}")
        logger.info(f"Sucursal: {config_test['NUMERO_SUCURSAL']}")
        logger.info(f"URL: {config_test['API'][:60]}...")
        
        # Llamar a la API
        respuesta = await api_client.obtener_datos(config_test['API'], config_test['Token'])
        
        if not respuesta:
            logger.error("✗ La API no retornó datos")
            await api_client.close()
            return False
        
        logger.info(f"✓ API respondió exitosamente")
        logger.info(f"  - Success: {respuesta.get('success')}")
        logger.info(f"  - Report name: {respuesta.get('report', {}).get('name')}")
        
        # Extraer y mostrar algunos datos
        datos = api_client.extraer_datos(respuesta)
        logger.info(f"  - Registros obtenidos: {len(datos)}")
        
        if datos:
            logger.info(f"  - Ejemplo primer registro:")
            logger.info(f"    Fecha: {datos[0]['fecha']}, Valor: {datos[0]['valor']}")
        
        await api_client.close()
        logger.info("\n✓ TEST 3 PASADO: API respondió correctamente\n")
        return True
        
    except Exception as e:
        logger.error(f"✗ TEST 3 FALLIDO: Error al llamar API: {e}\n")
        return False


async def test_insercion_datos():
    """
    Test 4: Verifica la inserción/actualización de datos en la tabla BI_T_INGRESOS_SUCURSALES.
    """
    logger.info("=" * 60)
    logger.info("TEST 4: Inserción y actualización de datos")
    logger.info("=" * 60)
    
    try:
        db = HasarDB()
        
        # Datos de prueba
        fecha_test = datetime.now().date() - timedelta(days=1)
        nro_sucursal_test = 9999  # Sucursal ficticia para testing
        database_test = 'POWER_BI_CONTROL'
        
        logger.info(f"Insertando datos de prueba:")
        logger.info(f"  - BD: {database_test}")
        logger.info(f"  - Fecha: {fecha_test}")
        logger.info(f"  - Sucursal: {nro_sucursal_test}")
        logger.info(f"  - Ingresos: 100, Merodeo: 500")
        
        # Primera inserción
        exito = db.upsert_ingresos(
            database_name=database_test,
            fecha=fecha_test,
            nro_sucurs=nro_sucursal_test,
            ingresos=100,
            merodeo=500
        )
        
        if not exito:
            logger.error("✗ No se pudo insertar datos iniciales")
            return False
        
        logger.info("✓ Primera inserción exitosa")
        
        # Actualización (mismo registro, valores diferentes)
        logger.info(f"Actualizando registro con nuevos valores:")
        logger.info(f"  - Ingresos: 200, Merodeo: 1000")
        
        exito2 = db.upsert_ingresos(
            database_name=database_test,
            fecha=fecha_test,
            nro_sucurs=nro_sucursal_test,
            ingresos=200,
            merodeo=1000
        )
        
        if not exito2:
            logger.error("✗ No se pudo actualizar datos")
            return False
        
        logger.info("✓ Actualización exitosa")
        
        # Verificar datos guardados
        logger.info("Verificando datos guardados...")
        datos_verificados = db.verificar_datos_guardados(
            database_test,
            fecha_test,
            fecha_test
        )
        
        if datos_verificados:
            for row in datos_verificados:
                if row[1] == nro_sucursal_test:  # NRO_SUCURS
                    logger.info(f"  - Fecha: {row[0]}, Sucursal: {row[1]}")
                    logger.info(f"  - Ingresos: {row[2]}, Merodeo: {row[3]}")
                    
                    if row[2] == 200 and row[3] == 1000:
                        logger.info("✓ Datos verificados correctamente (actualización aplicada)")
                    else:
                        logger.warning("⚠ Datos no coinciden con lo esperado")
        
        # Limpiar datos de prueba
        logger.info("Limpiando datos de prueba...")
        from GestionAPI.HasarServicios.consultas import QRY_LIMPIAR_DATOS_TEST
        conexion = db._get_connection(database_test)
        if conexion:
            cursor = conexion.conectar()
            if cursor:
                cursor.execute(QRY_LIMPIAR_DATOS_TEST, (nro_sucursal_test, fecha_test))
                conexion.connection.commit()
                cursor.close()
                conexion.connection.close()
                logger.info("✓ Datos de prueba eliminados")
        
        logger.info("\n✓ TEST 4 PASADO: Inserción y actualización funcionan correctamente\n")
        return True
        
    except Exception as e:
        logger.error(f"✗ TEST 4 FALLIDO: Error en inserción/actualización: {e}\n")
        return False


async def ejecutar_todos_los_tests():
    """
    Ejecuta todos los tests secuencialmente.
    """
    logger.info("╔" + "═" * 78 + "╗")
    logger.info("║" + " " * 20 + "SUITE DE TESTS - HASARSERVICIOS" + " " * 27 + "║")
    logger.info("╚" + "═" * 78 + "╝\n")
    
    resultados = []
    
    # Test 1: Conexión a BD (síncrono)
    resultados.append(("Conexión a BD", test_conexion_base_datos()))
    
    # Test 2: Lectura de configuración (síncrono)
    resultados.append(("Lectura de configuración", test_lectura_configuracion()))
    
    # Test 3: Llamada a API (asíncrono)
    resultados.append(("Llamada a API", await test_llamada_api()))
    
    # Test 4: Inserción de datos (asíncrono)
    resultados.append(("Inserción de datos", await test_insercion_datos()))
    
    # Resumen
    logger.info("=" * 80)
    logger.info("RESUMEN DE TESTS")
    logger.info("=" * 80)
    
    total = len(resultados)
    pasados = sum(1 for _, resultado in resultados if resultado)
    fallidos = total - pasados
    
    for nombre, resultado in resultados:
        estado = "✓ PASADO" if resultado else "✗ FALLIDO"
        logger.info(f"{nombre:30} ... {estado}")
    
    logger.info("=" * 80)
    logger.info(f"Total: {total} tests | Pasados: {pasados} | Fallidos: {fallidos}")
    logger.info("=" * 80)
    
    if fallidos == 0:
        logger.info("\n🎉 ¡Todos los tests pasaron exitosamente!")
    else:
        logger.warning(f"\n⚠️ {fallidos} test(s) fallaron. Revisa los logs para más detalles.")
    
    return fallidos == 0


if __name__ == "__main__":
    """
    Punto de entrada del script de tests.
    Ejecuta todos los tests de forma asíncrona.
    """
    try:
        exito = asyncio.run(ejecutar_todos_los_tests())
        sys.exit(0 if exito else 1)
    except KeyboardInterrupt:
        logger.info("\nTests interrumpidos por el usuario")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error fatal en tests: {e}", exc_info=True)
        sys.exit(1)
