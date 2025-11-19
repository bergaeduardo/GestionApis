import asyncio
import logging
import sys
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

# Agregar el directorio raíz del proyecto al path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from GestionAPI.common.logger_config import setup_logger
from GestionAPI.common.credenciales import WELIVERY
from GestionAPI.Welivery.welivery_api import WeliveryAPI
from GestionAPI.Welivery.db_operations_welivery import WeliveryDB

# Importar módulo de impresión de etiquetas
try:
    from GestionAPI.Welivery.sync_etiquetas_welivery import process_and_print_labels
    PRINT_ENABLED = True
except ImportError as e:
    logger_temp = logging.getLogger('welivery_sync')
    logger_temp.warning(f"No se pudo importar módulo de impresión de etiquetas: {e}")
    PRINT_ENABLED = False

# Configurar logger específico para Welivery con ruta absoluta
welivery_log_path = os.path.join(os.path.dirname(__file__), 'logs', 'app.log')
logger = setup_logger('welivery_sync', welivery_log_path)

class WeliverySync:
    """
    Clase principal para sincronizar estados de envío con Welivery.
    Maneja la creación de envíos y actualización de estados.
    """
    
    def __init__(self):
        """Inicializa el sincronizador de Welivery."""
        self.api = WeliveryAPI(
            base_url=WELIVERY['url'],
            user=WELIVERY['user'],
            password=WELIVERY['password']
        )
        self.db = WeliveryDB()
        self.stats = {
            'envios_creados': 0,
            'estados_actualizados': 0,
            'entregados_marcados': 0,
            'errores': 0
        }

    async def crear_envios_pendientes(self) -> Dict[str, int]:
        """
        Crea envíos para pedidos que no tienen número de seguimiento.
        
        Returns:
            Dict[str, int]: Estadísticas de la operación
        """
        logger.info("=== INICIANDO CREACIÓN DE ENVÍOS PENDIENTES ===")
        
        # Resetear estadísticas
        self.stats = {
            'envios_creados': 0,
            'estados_actualizados': 0,
            'entregados_marcados': 0,
            'errores': 0
        }
        
        try:
            # Obtener pedidos pendientes de envío
            pedidos = self.db.get_pedidos_pendientes_envio()
            
            if not pedidos:
                logger.info("No hay pedidos pendientes de envío")
                return self.stats
            
            logger.info(f"Procesando {len(pedidos)} pedidos pendientes de envío")
            
            for pedido in pedidos:
                nro_pedido, order_id_tienda, talon_ped = pedido
                
                try:
                    # Usar ORDER_ID_TIENDA como número de seguimiento
                    if order_id_tienda:
                        num_seguimiento = str(order_id_tienda).strip()
                        
                        # Actualizar número de seguimiento en la base de datos
                        if self.db.update_numero_seguimiento(str(nro_pedido), str(talon_ped), num_seguimiento):
                            self.stats['envios_creados'] += 1
                            logger.info(f"Envío creado exitosamente para pedido {nro_pedido} - NUM_SEGUIMIENTO: {num_seguimiento}")
                        else:
                            self.stats['errores'] += 1
                            logger.error(f"Error al crear envío para pedido {nro_pedido}")
                    else:
                        self.stats['errores'] += 1
                        logger.warning(f"Pedido {nro_pedido} no tiene ORDER_ID_TIENDA")
                        
                except Exception as e:
                    self.stats['errores'] += 1
                    logger.error(f"Error procesando pedido {nro_pedido}: {e}")
            
            logger.info(f"Creación de envíos completada: {self.stats['envios_creados']} creados, {self.stats['errores']} errores")
            return self.stats
            
        except Exception as e:
            logger.error(f"Error general en creación de envíos: {e}")
            self.stats['errores'] += 1
            return self.stats

    async def actualizar_estados_entrega(self) -> Dict[str, int]:
        """
        Actualiza estados de envíos consultando la API de Welivery.
        
        Returns:
            Dict[str, int]: Estadísticas de la operación
        """
        logger.info("=== INICIANDO ACTUALIZACIÓN DE ESTADOS ===")
        
        try:
            # Obtener pedidos pendientes de entrega
            pedidos = self.db.get_pedidos_pendientes_entrega()
            
            if not pedidos:
                logger.info("No hay pedidos pendientes de actualización de estado")
                return self.stats
            
            logger.info(f"Consultando estado de {len(pedidos)} pedidos en Welivery")
            
            # Extraer números de seguimiento
            tracking_numbers = [str(pedido[1]) for pedido in pedidos if pedido[1]]
            
            if not tracking_numbers:
                logger.warning("No hay números de seguimiento válidos")
                return self.stats
            
            # Consultar estados en lotes para mejor rendimiento
            status_results = await self.api.get_multiple_delivery_status(tracking_numbers)
            
            # Preparar actualizaciones
            updates = []
            
            for pedido in pedidos:
                nro_pedido, num_seguimiento, talon_ped = pedido
                num_seguimiento_str = str(num_seguimiento)
                
                if num_seguimiento_str in status_results:
                    status_data = status_results[num_seguimiento_str]
                    
                    if status_data:
                        status = status_data.get('Status', 'INDEFINIDO')
                        estado_texto, estado_id = self.api.map_status_to_code(status)
                        
                        # Obtener fecha del estado más reciente del historial
                        fecha_estado = self._get_latest_status_date(status_data)
                        
                        updates.append({
                            'nro_pedido': str(nro_pedido),
                            'talon_ped': str(talon_ped),
                            'num_seguimiento': num_seguimiento_str,
                            'estado_texto': estado_texto,
                            'estado_id': estado_id,
                            'fecha_estado': fecha_estado
                        })
            
            # Procesar actualizaciones masivas
            if updates:
                bulk_stats = self.db.process_bulk_status_update(updates)
                
                # Actualizar estadísticas
                self.stats['estados_actualizados'] += bulk_stats['exitosos']
                self.stats['entregados_marcados'] += bulk_stats['entregados']
                self.stats['errores'] += bulk_stats['errores']
                
                logger.info(f"Actualización completada: {bulk_stats['exitosos']} estados actualizados, "
                           f"{bulk_stats['entregados']} marcados como entregados")
            else:
                logger.info("No hay actualizaciones para procesar")
            
            return self.stats
            
        except Exception as e:
            logger.error(f"Error general en actualización de estados: {e}")
            self.stats['errores'] += 1
            return self.stats

    def _get_latest_status_date(self, status_data: Dict[str, Any]) -> Optional[datetime]:
        """
        Obtiene la fecha del estado más reciente del historial.
        
        Args:
            status_data (Dict): Datos del estado del envío
            
        Returns:
            datetime: Fecha del estado más reciente o None
        """
        try:
            history = status_data.get('status_history', [])
            if history and len(history) > 0:
                # El historial debería estar ordenado, tomar el último
                latest_entry = history[-1]
                date_str = latest_entry.get('date_time', '')
                
                if date_str:
                    # Parsear fecha en formato "2025-09-11 17:38:22"
                    return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            
            return datetime.now()
            
        except Exception as e:
            logger.warning(f"Error al parsear fecha del historial: {e}")
            return datetime.now()

    async def sincronizar_completo(self) -> Dict[str, int]:
        """
        Ejecuta un ciclo completo de sincronización.
        
        Returns:
            Dict[str, int]: Estadísticas consolidadas de toda la operación
        """
        logger.info("=== INICIANDO SINCRONIZACIÓN COMPLETA DE WELIVERY ===")
        
        total_stats = {
            'envios_creados': 0,
            'estados_actualizados': 0,
            'entregados_marcados': 0,
            'errores': 0
        }
        
        try:
            # Paso 1: Crear envíos pendientes
            logger.info("Paso 1: Creando envíos pendientes...")
            stats1 = await self.crear_envios_pendientes()
            
            # Agregar estadísticas
            for key in total_stats:
                total_stats[key] += stats1.get(key, 0)
            
            # Paso 1.5: Imprimir etiquetas de los envíos recién creados
            if stats1.get('envios_creados', 0) > 0 and PRINT_ENABLED:
                logger.info("Paso 1.5: Imprimiendo etiquetas de envíos recién creados...")
                try:
                    await process_and_print_labels()
                    logger.info("Proceso de impresión de etiquetas completado")
                except Exception as e:
                    logger.error(f"Error durante la impresión de etiquetas: {e}")
                    total_stats['errores'] += 1
            elif not PRINT_ENABLED:
                logger.warning("Módulo de impresión no disponible, saltando impresión de etiquetas")
            else:
                logger.info("No hay etiquetas nuevas para imprimir")
            
            # Breve pausa entre operaciones
            await asyncio.sleep(2)
            
            # Paso 2: Actualizar estados de entrega
            logger.info("Paso 2: Actualizando estados de entrega...")
            stats2 = await self.actualizar_estados_entrega()
            
            # Agregar estadísticas
            for key in total_stats:
                total_stats[key] += stats2.get(key, 0)
            
            logger.info("=== SINCRONIZACIÓN COMPLETA FINALIZADA ===")
            logger.info(f"Resumen: {total_stats['envios_creados']} envíos creados, "
                       f"{total_stats['estados_actualizados']} estados actualizados, "
                       f"{total_stats['entregados_marcados']} entregados marcados, "
                       f"{total_stats['errores']} errores")
            
            return total_stats
            
        except Exception as e:
            logger.error(f"Error en sincronización completa: {e}")
            total_stats['errores'] += 1
            return total_stats

    async def consultar_envio_especifico(self, num_seguimiento: str) -> Optional[Dict[str, Any]]:
        """
        Consulta el estado de un envío específico.
        
        Args:
            num_seguimiento (str): Número de seguimiento del envío
            
        Returns:
            Dict[str, Any]: Información del estado del envío
        """
        logger.info(f"Consultando envío específico: {num_seguimiento}")
        
        try:
            # Consultar en la API
            status_data = await self.api.get_delivery_status(num_seguimiento)
            
            if status_data:
                status = status_data.get('Status', 'INDEFINIDO')
                estado_texto, estado_id = self.api.map_status_to_code(status)
                
                result = {
                    'num_seguimiento': num_seguimiento,
                    'estado_api': status,
                    'estado_texto': estado_texto,
                    'estado_id': estado_id,
                    'datos_completos': status_data
                }
                
                # Buscar en BD local
                pedido_local = self.db.get_pedido_by_seguimiento(num_seguimiento)
                if pedido_local:
                    result['pedido_local'] = {
                        'nro_pedido': pedido_local[0],
                        'talon_ped': pedido_local[2],
                        'estado_actual': pedido_local[3],
                        'estado_id_actual': pedido_local[4]
                    }
                
                logger.info(f"Consulta completada para {num_seguimiento}: {status}")
                return result
            else:
                logger.warning(f"No se encontró información para {num_seguimiento}")
                return None
                
        except Exception as e:
            logger.error(f"Error consultando envío {num_seguimiento}: {e}")
            return None

    async def close(self):
        """Cierra las conexiones y libera recursos."""
        try:
            await self.api.close()
            self.db.close_connection()
            logger.info("Recursos liberados correctamente")
        except Exception as e:
            logger.error(f"Error liberando recursos: {e}")

# Función principal para ejecución independiente
async def main():
    """Función principal para ejecutar la sincronización."""
    sync = None
    
    try:
        sync = WeliverySync()
        
        # Ejecutar sincronización completa
        stats = await sync.sincronizar_completo()
        print(f"Sincronización finalizada: {stats}")
        
    except KeyboardInterrupt:
        logger.info("Proceso interrumpido por el usuario")
    except Exception as e:
        logger.error(f"Error en proceso principal: {e}")
    finally:
        if sync:
            await sync.close()
            
        # Dar tiempo para que se cierren todas las conexiones
        await asyncio.sleep(0.1)

if __name__ == "__main__":
    # Ejecutar con manejo limpio del event loop
    try:
        asyncio.run(main())
    except RuntimeError as e:
        if "Event loop is closed" not in str(e):
            raise