"""
Módulo para sincronizar e imprimir etiquetas de Welivery.
Este script obtiene pedidos pendientes de impresión, descarga las etiquetas
desde la API de Welivery y las envía a imprimir.
"""

import asyncio
import platform
import json
import sys
import os
import logging
from typing import List, Dict, Optional, Tuple

# Configuración de rutas
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

# Importaciones de módulos del proyecto
from GestionAPI.Welivery.impresora import PrinterManager
from GestionAPI.Welivery.welivery_api import WeliveryAPI
from GestionAPI.Welivery.db_operations_welivery import WeliveryDB
from GestionAPI.common.credenciales import WELIVERY
from GestionAPI.common.logger_config import setup_logger

# Configuración del logger
logger = setup_logger('welivery_etiquetas')

if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def process_and_print_labels() -> None:
    """
    Función principal que maneja el proceso de descarga e impresión de etiquetas.
    Consulta la base de datos por pedidos pendientes de impresión,
    descarga las etiquetas desde Welivery y las envía a imprimir.
    """
    # Configuración de credenciales
    base_url = WELIVERY["url"]
    user = WELIVERY["user"]
    password = WELIVERY["password"]

    # Inicialización de la API
    try:
        api = WeliveryAPI(base_url, user, password)
        logger.info("Conexión exitosa a la API de Welivery")
    except Exception as e:
        logger.error(f"Error al inicializar la API de Welivery: {e}")
        return

    # Obtener datos de la base de datos
    try:
        welivery_db = WeliveryDB()
        logger.info("Conexión exitosa a la base de datos")
        
        # Lista para almacenar información de pedidos a imprimir
        orders_to_print = []
        
        # Obtener pedidos pendientes de impresión
        pedidos_sin_imprimir = welivery_db.get_pedidos_sin_imprimir()
        
        if not pedidos_sin_imprimir:
            logger.info("No hay pedidos pendientes de impresión en este momento")
            return
        
        logger.info(f"Se encontraron {len(pedidos_sin_imprimir)} pedidos para procesar")
        
        # Procesar pedidos pendientes
        for pedido_data in pedidos_sin_imprimir:
            nro_pedido = pedido_data[0].strip() if pedido_data[0] else None
            num_seguimiento = pedido_data[1].strip() if pedido_data[1] else None
            talon_ped = str(pedido_data[2]) if pedido_data[2] else '99'
            
            if nro_pedido and num_seguimiento:
                orders_to_print.append({
                    "numeroPedido": nro_pedido,
                    "numeroSeguimiento": num_seguimiento,
                    "talonPed": talon_ped
                })
                logger.info(f"Pedido agregado - Pedido: {nro_pedido}, Seguimiento: {num_seguimiento}")
        
        if not orders_to_print:
            logger.info("No hay pedidos válidos para procesar")
            return
        
        logger.info(f"Total de pedidos a procesar para impresión: {len(orders_to_print)}")
        
        # Cargar configuración de impresora desde printer_config.json
        config_path = os.path.join(os.path.dirname(__file__), 'config', 'printer_config.json')
        printer_config = {}
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    printer_config = json.load(f).get('printer', {})
            except Exception as e:
                logger.error(f"Error al cargar printer_config.json: {e}")

        printer_method = printer_config.get('method', 'win32')
        printer_path = printer_config.get('label_printer_path', '\\\\PC-PEDIDOS-02\\ZDesigner GC420t (EPL)')
        
        os.environ['PRINTER_METHOD'] = printer_method
        
        logger.info(f"Usando método de impresión: {printer_method} y impresora: {printer_path}")
        
        printer_manager = PrinterManager(
            label_printer_path=printer_path,
            print_method=printer_method
        )
        
        try:
            # Cambiar a la impresora de etiquetas
            logger.info("Intentando cambiar a la impresora de etiquetas...")
            if not printer_manager.switch_to_label_printer():
                logger.error("No se pudo cambiar a la impresora de etiquetas")
                logger.info("Verificando impresoras disponibles...")
                printers = printer_manager.list_printers()
                logger.info("Impresoras instaladas en el sistema:")
                for printer in printers:
                    logger.info(f"- {printer['name']} ({printer['port']})")
                return
            
            # Crear directorio temporal si no existe
            temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp")
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)
                logger.info(f"Directorio temporal creado: {temp_dir}")
            
            # Procesar cada pedido
            for order_info in orders_to_print:
                try:
                    nro_pedido = order_info['numeroPedido']
                    num_seguimiento = order_info['numeroSeguimiento']
                    talon_ped = order_info['talonPed']
                    
                    logger.info(f"Procesando pedido {nro_pedido} - Seguimiento: {num_seguimiento}")
                    
                    # Crear nombre de archivo único para cada etiqueta
                    filename = f"etiqueta_welivery_{nro_pedido}.pdf"
                    filepath = os.path.join(temp_dir, filename)
                    
                    # Eliminar archivo anterior si existe
                    if os.path.exists(filepath):
                        try:
                            os.remove(filepath)
                            logger.debug(f"Archivo anterior eliminado: {filepath}")
                        except Exception as e:
                            logger.warning(f"No se pudo eliminar el archivo temporal existente: {e}")
                    
                    # Descargar la etiqueta
                    logger.info(f"Descargando etiqueta para pedido {nro_pedido}...")
                    download_success = await api.download_label(num_seguimiento, filepath)
                    
                    if not download_success:
                        logger.error(f"No se pudo descargar la etiqueta para el pedido {nro_pedido}")
                        continue
                    
                    # Verificar que el archivo PDF se haya guardado correctamente
                    if not os.path.exists(filepath):
                        logger.error(f"ERROR CRÍTICO: El archivo de etiqueta no se pudo guardar en {filepath}")
                        continue
                    
                    file_size = os.path.getsize(filepath)
                    if file_size == 0:
                        logger.error(f"ERROR CRÍTICO: El archivo de etiqueta está vacío (0 bytes) - Pedido: {nro_pedido}")
                        continue
                    
                    logger.info(f"Etiqueta descargada correctamente - Tamaño: {file_size} bytes")
                    
                    # Imprimir la etiqueta
                    try:
                        logger.info(f"Iniciando impresión de etiqueta - Pedido: {nro_pedido}")
                        logger.debug(f"Método: {printer_method}, Impresora: {printer_path}")
                        
                        print_result = printer_manager.print_file(filepath)
                        
                        if print_result:
                            logger.info(f"[OK] Etiqueta enviada a imprimir correctamente - Pedido: {nro_pedido}")
                            # Marcar como impreso (IMP_ROT = 1)
                            if welivery_db.update_imp_rot(nro_pedido, talon_ped):
                                logger.info(f"[OK] Base de datos actualizada (IMP_ROT=1) - Pedido: {nro_pedido}")
                            else:
                                logger.error(f"[ERROR] No se pudo actualizar IMP_ROT en la base de datos - Pedido: {nro_pedido}")
                        else:
                            logger.error(
                                f"[ERROR] ERROR DE IMPRESION - Pedido: {nro_pedido}\n"
                                f"  - Archivo: {filepath}\n"
                                f"  - Tamaño: {file_size} bytes\n"
                                f"  - Método de impresión: {printer_method}\n"
                                f"  - Impresora: {printer_path}\n"
                                f"  - Verificar: Conectividad de red, estado de la impresora, permisos de archivo"
                            )
                    except Exception as print_error:
                        logger.error(
                            f"[ERROR] EXCEPCION AL IMPRIMIR - Pedido: {nro_pedido}\n"
                            f"  - Error: {type(print_error).__name__}: {str(print_error)}\n"
                            f"  - Archivo: {filepath}\n"
                            f"  - Método: {printer_method}\n"
                            f"  - Impresora: {printer_path}",
                            exc_info=True
                        )
                    
                    # Dar tiempo al sistema para procesar el archivo
                    import time
                    time.sleep(3)
                    
                    # Opcionalmente, eliminar el archivo PDF después de imprimir
                    try:
                        os.remove(filepath)
                        logger.debug(f"Archivo temporal {filename} eliminado")
                    except Exception as e:
                        logger.warning(f"No se pudo eliminar el archivo temporal {filename}: {e}")
                    
                except Exception as e:
                    logger.error(f"Error al procesar el pedido {order_info.get('numeroPedido', 'desconocido')}: {e}", exc_info=True)
        
        except Exception as e:
            logger.error(f"Error en el proceso de impresión: {e}", exc_info=True)
        
        finally:
            # Restaurar la impresora predeterminada
            if not printer_manager.restore_default_printer():
                logger.warning("No se pudo restaurar la impresora predeterminada")
            
            # Cerrar sesión de API
            await api.close()

    except Exception as e:
        logger.error(f"Error general en el proceso: {e}", exc_info=True)

if __name__ == "__main__":
    logger.info("=" * 80)
    logger.info("Iniciando proceso de sincronización de etiquetas Welivery")
    logger.info("=" * 80)
    asyncio.run(process_and_print_labels())
    logger.info("=" * 80)
    logger.info("Proceso de sincronización de etiquetas Welivery finalizado")
    logger.info("=" * 80)
