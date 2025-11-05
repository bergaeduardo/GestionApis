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

# Ahora que agregamos el directorio raíz al path, podemos importar nuestros módulos
from GestionAPI.Andreani.impresora import PrinterManager

from GestionAPI.Andreani.andreani_api import AndreaniAPI
from GestionAPI.Andreani.db_operations_andreani import AndreaniDB
from GestionAPI.common.credenciales import DATA_PROD as DATA_PROD
from GestionAPI.common.logger_config import setup_logger

# Configuración del logger
logger = setup_logger('andreani_rotulos')

if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def process_orders_and_get_labels() -> None:
    """
    Función principal que maneja el proceso de obtención y generación de etiquetas.
    Consulta la base de datos por pedidos pendientes, crea las órdenes de envío
    y genera las etiquetas correspondientes.
    """
    # Configuración de credenciales
    base_url_qa = DATA_PROD["url"]
    user = DATA_PROD["user"]
    password = DATA_PROD["passw"]

    # Inicialización de la API
    try:
        api = AndreaniAPI(base_url_qa, user, password)
        logger.info("Conexión exitosa a la API de Andreani")
    except ValueError as e:
        logger.error(f"Error al inicializar la API de Andreani: {e}")
        return

    # Obtener datos de la base de datos
    try:
        andreani_db = AndreaniDB()
        logger.info("Conexión exitosa a la base de datos")
        
        # Lista para almacenar información de pedidos a imprimir
        orders_to_print = []
        
        # PASO 1: Verificar si hay pedidos con número de envío pero sin imprimir
        pedidos_sin_imprimir = andreani_db.get_pedidos_sin_imprimir()
        
        if pedidos_sin_imprimir:
            logger.info(f"Procesando {len(pedidos_sin_imprimir)} pedidos con envío creado pendientes de impresión")
            
            # Obtener etiquetas para pedidos que ya tienen número de envío
            for pedido_data in pedidos_sin_imprimir:
                nro_pedido = pedido_data[0].strip() if pedido_data[0] else None
                num_seguimiento = pedido_data[1].strip() if pedido_data[1] else None
                
                if nro_pedido and num_seguimiento:
                    # Obtener el número de agrupador desde Andreani usando el número de seguimiento
                    # Como no tenemos el agrupador guardado, necesitamos consultar a Andreani
                    # Por simplicidad, usaremos el número de seguimiento como referencia
                    orders_to_print.append({
                        "numeroPedido": nro_pedido,
                        "numeroEnvio": num_seguimiento,
                        "numeroAgrupador": num_seguimiento  # Usamos el número de envío para obtener la etiqueta
                    })
                    logger.info(f"Pedido sin imprimir agregado - Pedido: {nro_pedido}, Envío: {num_seguimiento}")
        
        # PASO 2: Procesar nuevos pedidos (sin número de envío)
        datos_db = andreani_db.get_data_from_sein()
        
        if datos_db:
            # Procesar los datos obtenidos
            json_string = datos_db[0][0]
            if json_string:
                orders_data = json.loads(json_string)
                orders = orders_data.get("data", [])
                
                if orders:
                    logger.info(f"Se encontraron {len(orders)} pedidos nuevos para procesar")
                    
                    # Lista para almacenar las tareas de creación de órdenes
                    create_order_tasks = []
                    
                    # Preparar las órdenes para el proceso
                    for order in orders:
                        # Ajustar el formato de 'postal' en 'origen' y 'destino'
                        if 'origen' in order and 'postal' in order['origen'] and isinstance(order['origen']['postal'], list):
                            order['origen']['postal'] = order['origen']['postal'][0]
                        if 'destino' in order and 'postal' in order['destino'] and isinstance(order['destino']['postal'], list):
                            order['destino']['postal'] = order['destino']['postal'][0]
                        
                        create_order_tasks.append(api.crear_orden_envio(order))

                    # Procesar todas las órdenes de envío
                    orders_results = await asyncio.gather(*create_order_tasks, return_exceptions=True)
                    
                    # Procesar los resultados y guardar número de envío inmediatamente
                    for order, result in zip(orders, orders_results):
                        if isinstance(result, Exception):
                            logger.error(f"Error al crear orden de envío: {result}")
                            continue
                        
                        if result is None:
                            logger.error(f"No se pudo crear la orden de envío para el pedido {order.get('idPedido')}, el resultado de la API fue nulo.")
                            continue
                            
                        numero_envio = result.get("numeroEnvio")
                        numero_agrupador = result.get("numeroAgrupador")
                        numero_pedido = order.get("idPedido", "No especificado")
                        
                        if numero_agrupador and numero_envio:
                            # IMPORTANTE: Guardar el número de envío inmediatamente después de crear la orden
                            if andreani_db.update_num_seguimiento(numero_pedido, numero_envio):
                                logger.info(f"Orden creada y NUM_SEGUIMIENTO guardado - Pedido: {numero_pedido}, Envío: {numero_envio}, Agrupador: {numero_agrupador}")
                                
                                orders_to_print.append({
                                    "numeroPedido": numero_pedido,
                                    "numeroEnvio": numero_envio,
                                    "numeroAgrupador": numero_agrupador
                                })
                            else:
                                logger.error(f"No se pudo guardar NUM_SEGUIMIENTO para el pedido {numero_pedido}")
            else:
                logger.debug("No hay datos JSON para procesar nuevos pedidos.")
        
        # PASO 3: Si no hay pedidos para imprimir, terminar
        if not orders_to_print:
            logger.info("No hay pedidos para imprimir en este momento")
            return
        
        logger.info(f"Total de pedidos a procesar para impresión: {len(orders_to_print)}")
        
        # PASO 4: Obtener etiquetas para todos los pedidos
        label_tasks = []
        for order_info in orders_to_print:
            label_tasks.append(api.obtener_etiquetas(order_info["numeroAgrupador"]))
        
        # Obtener todas las etiquetas
        labels_results = await asyncio.gather(*label_tasks, return_exceptions=True)

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
        printer_path = printer_config.get('label_printer_path', '\\\\192.168.0.64\\ZDesigner GC420t (EPL)') # Fallback to old hardcoded path
        
        os.environ['PRINTER_METHOD'] = printer_method  # Forzar el uso del método de impresión configurado
        
        logger.info(f"Usando método de impresión: {printer_method} y impresora: {printer_path}")
        
        printer_manager = PrinterManager(
            label_printer_path=printer_path,
            print_method=printer_method
        )
        
        try:
            # Cambiar a la impresora de etiquetas
            logger.info("Intentando cambiar a la impresora de etiquetas...")
            if not printer_manager.switch_to_label_printer():
                logger.error("No se pudo cambiar a la impresora de etiquetas - Verificar solución de problemas en README_IMPRESION.md")
                logger.info("Verificando impresoras disponibles...")
                printers = printer_manager.list_printers()
                logger.info("Impresoras instaladas en el sistema:")
                for printer in printers:
                    logger.info(f"- {printer['name']} ({printer['port']})")
                return
            
            # Procesar y guardar las etiquetas
            for order_info, label_result in zip(orders_to_print, labels_results):
                if isinstance(label_result, Exception):
                    logger.error(f"Error al obtener etiqueta para el pedido {order_info['numeroPedido']}: {label_result}")
                    continue

                try:
                    # Crear un directorio temporal dedicado si no existe
                    temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp")
                    if not os.path.exists(temp_dir):
                        os.makedirs(temp_dir)
                    
                    # Crear nombre de archivo único para cada etiqueta
                    filename = f"etiqueta_{order_info['numeroPedido']}.pdf"
                    filepath = os.path.join(temp_dir, filename)
                    
                    # Asegurarse de que el archivo anterior se elimine si existe
                    if os.path.exists(filepath):
                        try:
                            os.remove(filepath)
                        except Exception as e:
                            logger.warning(f"No se pudo eliminar el archivo temporal existente: {e}")
                    
                    with open(filepath, "wb") as etiqueta_file:
                        etiqueta_file.write(label_result)
                    logger.info(f"Etiqueta guardada como '{filepath}' para el pedido {order_info['numeroPedido']}")
                    
                    # Imprimir la etiqueta
                    if printer_manager.print_file(filepath):
                        logger.info(f"Etiqueta enviada a imprimir para el pedido {order_info['numeroPedido']}")
                        # Marcar como impreso (IMP_ROT = 1)
                        andreani_db.update_imp_rot(order_info['numeroPedido'])
                    else:
                        logger.error(f"Error al imprimir la etiqueta para el pedido {order_info['numeroPedido']}")
                        
                    # Dar tiempo a Adobe Reader para procesar el archivo
                    import time
                    time.sleep(5)  # Esperar 5 segundos
                    
                    # Opcionalmente, eliminar el archivo PDF después de imprimir
                    try:
                        os.remove(filepath)
                        logger.debug(f"Archivo temporal {filename} eliminado")
                    except Exception as e:
                        logger.warning(f"No se pudo eliminar el archivo temporal {filename}: {e}")
                    
                except Exception as e:
                    logger.error(f"Error al procesar la etiqueta para el pedido {order_info['numeroPedido']}: {e}")
        
        except Exception as e:
            logger.error(f"Error en el proceso de impresión: {e}")
        
        finally:
            # Restaurar la impresora predeterminada
            if not printer_manager.restore_default_printer():
                logger.warning("No se pudo restaurar la impresora predeterminada")

    except Exception as e:
        logger.error(f"Error general en el proceso: {e}")

if __name__ == "__main__":
    logger.info("Iniciando proceso de sincronización de rótulos Andreani")
    asyncio.run(process_orders_and_get_labels())
    logger.info("Proceso de sincronización de rótulos Andreani finalizado")