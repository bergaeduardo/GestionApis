"""
Script de prueba para el módulo de impresión de etiquetas Welivery.
Este script permite probar la funcionalidad de descarga e impresión de etiquetas
sin necesidad de ejecutar el proceso completo.
"""

import asyncio
import sys
import os
import logging

# Configuración de rutas
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from GestionAPI.Welivery.welivery_api import WeliveryAPI
from GestionAPI.Welivery.db_operations_welivery import WeliveryDB
from GestionAPI.common.credenciales import WELIVERY
from GestionAPI.common.logger_config import setup_logger

# Configuración del logger
logger = setup_logger('welivery_test_etiquetas')

async def test_get_label_url(tracking_number: str):
    """
    Prueba la obtención de la URL de etiqueta para un número de seguimiento.
    
    Args:
        tracking_number (str): Número de seguimiento a probar
    """
    logger.info("=" * 80)
    logger.info(f"PRUEBA: Obtener URL de etiqueta para seguimiento {tracking_number}")
    logger.info("=" * 80)
    
    base_url = WELIVERY["url"]
    user = WELIVERY["user"]
    password = WELIVERY["password"]
    
    try:
        api = WeliveryAPI(base_url, user, password)
        logger.info("Conexión exitosa a la API de Welivery")
        
        # Obtener URL de etiqueta
        label_url = await api.get_label_url(tracking_number)
        
        if label_url:
            logger.info(f"✓ URL de etiqueta obtenida exitosamente:")
            logger.info(f"  {label_url}")
            return label_url
        else:
            logger.error(f"✗ No se pudo obtener la URL de etiqueta")
            return None
            
    except Exception as e:
        logger.error(f"Error en la prueba: {e}", exc_info=True)
        return None
    finally:
        await api.close()

async def test_download_label(tracking_number: str, output_path: str = None):
    """
    Prueba la descarga de una etiqueta.
    
    Args:
        tracking_number (str): Número de seguimiento a probar
        output_path (str, optional): Ruta donde guardar el PDF
    """
    logger.info("=" * 80)
    logger.info(f"PRUEBA: Descargar etiqueta para seguimiento {tracking_number}")
    logger.info("=" * 80)
    
    if output_path is None:
        # Crear directorio temporal si no existe
        temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp")
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        output_path = os.path.join(temp_dir, f"test_etiqueta_{tracking_number}.pdf")
    
    base_url = WELIVERY["url"]
    user = WELIVERY["user"]
    password = WELIVERY["password"]
    
    try:
        api = WeliveryAPI(base_url, user, password)
        logger.info("Conexión exitosa a la API de Welivery")
        
        # Descargar etiqueta
        success = await api.download_label(tracking_number, output_path)
        
        if success:
            logger.info(f"✓ Etiqueta descargada exitosamente en:")
            logger.info(f"  {output_path}")
            
            # Verificar tamaño del archivo
            file_size = os.path.getsize(output_path)
            logger.info(f"  Tamaño: {file_size} bytes")
            
            return output_path
        else:
            logger.error(f"✗ No se pudo descargar la etiqueta")
            return None
            
    except Exception as e:
        logger.error(f"Error en la prueba: {e}", exc_info=True)
        return None
    finally:
        await api.close()

def test_get_pedidos_sin_imprimir():
    """
    Prueba la obtención de pedidos pendientes de impresión desde la base de datos.
    """
    logger.info("=" * 80)
    logger.info("PRUEBA: Obtener pedidos pendientes de impresión")
    logger.info("=" * 80)
    
    try:
        db = WeliveryDB()
        logger.info("Conexión exitosa a la base de datos")
        
        pedidos = db.get_pedidos_sin_imprimir()
        
        if pedidos:
            logger.info(f"✓ Se encontraron {len(pedidos)} pedidos pendientes de impresión:")
            for i, pedido in enumerate(pedidos[:10], 1):  # Mostrar solo los primeros 10
                nro_pedido = pedido[0].strip() if pedido[0] else "N/A"
                num_seguimiento = pedido[1].strip() if pedido[1] else "N/A"
                talon_ped = str(pedido[2]) if pedido[2] else "N/A"
                logger.info(f"  {i}. Pedido: {nro_pedido}, Seguimiento: {num_seguimiento}, Talón: {talon_ped}")
            
            if len(pedidos) > 10:
                logger.info(f"  ... y {len(pedidos) - 10} más")
            
            return pedidos
        else:
            logger.info("No se encontraron pedidos pendientes de impresión")
            return []
            
    except Exception as e:
        logger.error(f"Error en la prueba: {e}", exc_info=True)
        return None

def test_update_imp_rot(nro_pedido: str, talon_ped: str = '99'):
    """
    Prueba la actualización del campo IMP_ROT.
    
    Args:
        nro_pedido (str): Número de pedido
        talon_ped (str): Talón del pedido
    """
    logger.info("=" * 80)
    logger.info(f"PRUEBA: Actualizar IMP_ROT para pedido {nro_pedido}")
    logger.info("=" * 80)
    
    try:
        db = WeliveryDB()
        logger.info("Conexión exitosa a la base de datos")
        
        success = db.update_imp_rot(nro_pedido, talon_ped)
        
        if success:
            logger.info(f"✓ Campo IMP_ROT actualizado exitosamente para pedido {nro_pedido}")
            return True
        else:
            logger.error(f"✗ No se pudo actualizar IMP_ROT para pedido {nro_pedido}")
            return False
            
    except Exception as e:
        logger.error(f"Error en la prueba: {e}", exc_info=True)
        return False

async def run_all_tests():
    """
    Ejecuta todas las pruebas disponibles.
    """
    logger.info("\n" + "=" * 80)
    logger.info("INICIANDO SUITE DE PRUEBAS DE IMPRESIÓN DE ETIQUETAS WELIVERY")
    logger.info("=" * 80 + "\n")
    
    # Prueba 1: Obtener pedidos sin imprimir
    logger.info("\n[PRUEBA 1/4] Obtener pedidos sin imprimir")
    pedidos = test_get_pedidos_sin_imprimir()
    
    if pedidos and len(pedidos) > 0:
        # Usar el primer pedido para las siguientes pruebas
        primer_pedido = pedidos[0]
        nro_pedido = primer_pedido[0].strip() if primer_pedido[0] else None
        num_seguimiento = primer_pedido[1].strip() if primer_pedido[1] else None
        
        if num_seguimiento:
            # Prueba 2: Obtener URL de etiqueta
            logger.info("\n[PRUEBA 2/4] Obtener URL de etiqueta")
            label_url = await test_get_label_url(num_seguimiento)
            
            if label_url:
                # Prueba 3: Descargar etiqueta
                logger.info("\n[PRUEBA 3/4] Descargar etiqueta")
                file_path = await test_download_label(num_seguimiento)
                
                if file_path:
                    logger.info(f"\n✓ Etiqueta descargada en: {file_path}")
                    logger.info("  Puedes abrir este archivo para verificar la etiqueta")
        else:
            logger.warning("El primer pedido no tiene número de seguimiento, saltando pruebas de API")
    else:
        logger.warning("No hay pedidos para probar, considera usar un número de seguimiento específico")
    
    # Prueba 4: Información de configuración
    logger.info("\n[PRUEBA 4/4] Verificar configuración de impresora")
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'printer_config.json')
    if os.path.exists(config_path):
        import json
        with open(config_path, 'r') as f:
            config = json.load(f)
            logger.info("✓ Configuración de impresora cargada:")
            logger.info(f"  Método: {config.get('printer', {}).get('method', 'N/A')}")
            logger.info(f"  Impresora: {config.get('printer', {}).get('label_printer_path', 'N/A')}")
    else:
        logger.warning("✗ No se encontró archivo de configuración printer_config.json")
    
    logger.info("\n" + "=" * 80)
    logger.info("SUITE DE PRUEBAS COMPLETADA")
    logger.info("=" * 80 + "\n")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Pruebas para el módulo de impresión de etiquetas Welivery')
    parser.add_argument('--tracking', type=str, help='Número de seguimiento para probar')
    parser.add_argument('--pedido', type=str, help='Número de pedido para probar update_imp_rot')
    parser.add_argument('--all', action='store_true', help='Ejecutar todas las pruebas')
    
    args = parser.parse_args()
    
    if args.all:
        asyncio.run(run_all_tests())
    elif args.tracking:
        asyncio.run(test_download_label(args.tracking))
    elif args.pedido:
        test_update_imp_rot(args.pedido)
    else:
        # Por defecto, ejecutar todas las pruebas
        asyncio.run(run_all_tests())
