import logging
import sys
import os
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any

# Agregar el directorio padre al path para importaciones
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.conexion import Conexion
from common.credenciales import CENTRAL_LAKERS
from consultas import (
    QRY_GET_PEDIDOS_PENDIENTES,
    QRY_GET_PEDIDOS_PENDIENTES_ENTREGA,
    QRY_UPDATE_NUM_SEGUIMIENTO,
    QRY_UPDATE_ESTADO_ENVIO,
    QRY_UPDATE_ENTREGADO,
    QRY_CHECK_PEDIDO_ECOMMERCE,
    QRY_GET_PEDIDO_BY_SEGUIMIENTO
)

# Usar el logger configurado por el módulo padre
logger = logging.getLogger('welivery_sync')

class WeliveryDB:
    """
    Clase para manejar todas las operaciones de base de datos relacionadas con Welivery.
    Interactúa con las tablas SEIN_TABLA_TEMPORAL_SCRIPT y RO_T_ESTADO_PEDIDOS_ECOMMERCE.
    """
    
    def __init__(self):
        """Inicializa la conexión a la base de datos."""
        self.db_config = CENTRAL_LAKERS
        self.conexion = Conexion(
            server=self.db_config['server'],
            database=self.db_config['database'],
            user=self.db_config['user'],
            password=self.db_config['password']
        )

    def get_pedidos_pendientes_envio(self) -> Optional[List[Tuple]]:
        """
        Obtiene pedidos pendientes de envío (sin número de seguimiento).
        
        Returns:
            List[Tuple]: Lista de tuplas con (NRO_PEDIDO, ORDER_ID_TIENDA, TALON_PED)
        """
        try:
            resultados = self.conexion.ejecutar_consulta(QRY_GET_PEDIDOS_PENDIENTES)
            
            if resultados:
                logger.info(f"Se encontraron {len(resultados)} pedidos pendientes de envío")
                return resultados
            else:
                logger.info("No se encontraron pedidos pendientes de envío")
                return []
                
        except Exception as e:
            logger.error(f"Error al obtener pedidos pendientes de envío: {e}")
            return None

    def get_pedidos_pendientes_entrega(self) -> Optional[List[Tuple]]:
        """
        Obtiene pedidos pendientes de entrega (con número de seguimiento pero sin estado final).
        
        Returns:
            List[Tuple]: Lista de tuplas con (NRO_PEDIDO, NUM_SEGUIMIENTO, TALON_PED)
        """
        try:
            resultados = self.conexion.ejecutar_consulta(QRY_GET_PEDIDOS_PENDIENTES_ENTREGA)
            
            if resultados:
                logger.info(f"Se encontraron {len(resultados)} pedidos pendientes de entrega")
                return resultados
            else:
                logger.info("No se encontraron pedidos pendientes de entrega")
                return []
                
        except Exception as e:
            logger.error(f"Error al obtener pedidos pendientes de entrega: {e}")
            return None

    def update_numero_seguimiento(self, nro_pedido: str, talon_ped: str, num_seguimiento: str) -> bool:
        """
        Actualiza el número de seguimiento para un pedido específico.
        
        Args:
            nro_pedido (str): Número de pedido
            talon_ped (str): Talón del pedido
            num_seguimiento (str): Número de seguimiento a asignar
            
        Returns:
            bool: True si la actualización fue exitosa
        """
        try:
            # Agregar espacio al inicio del número de pedido para evitar errores de SQL Server
            nro_pedido_formatted = f" {nro_pedido.strip()}"
            
            params = [num_seguimiento, nro_pedido_formatted, talon_ped]
            result = self.conexion.ejecutar_update(QRY_UPDATE_NUM_SEGUIMIENTO, params)
            
            if result:
                logger.info(f"Número de seguimiento {num_seguimiento} actualizado para pedido {nro_pedido}")
                return True
            else:
                logger.warning(f"No se pudo actualizar número de seguimiento para pedido {nro_pedido}")
                return False
                
        except Exception as e:
            logger.error(f"Error al actualizar número de seguimiento para pedido {nro_pedido}: {e}")
            return False

    def update_estado_envio(self, nro_pedido: str, talon_ped: str, estado_texto: str, 
                          estado_id: int, fecha_estado: datetime = None) -> bool:
        """
        Actualiza el estado de envío para un pedido específico.
        
        Args:
            nro_pedido (str): Número de pedido
            talon_ped (str): Talón del pedido
            estado_texto (str): Estado en texto
            estado_id (int): ID del estado
            fecha_estado (datetime, optional): Fecha del estado, si no se proporciona usa la actual
            
        Returns:
            bool: True si la actualización fue exitosa
        """
        try:
            if fecha_estado is None:
                fecha_estado = datetime.now()
            
            # Agregar espacio al inicio del número de pedido para evitar errores de SQL Server
            nro_pedido_formatted = f" {nro_pedido.strip()}"
            
            params = [estado_texto, estado_id, fecha_estado, nro_pedido_formatted, talon_ped]
            result = self.conexion.ejecutar_update(QRY_UPDATE_ESTADO_ENVIO, params)
            
            if result:
                logger.info(f"Estado {estado_texto} ({estado_id}) actualizado para pedido {nro_pedido}")
                return True
            else:
                logger.warning(f"No se pudo actualizar estado para pedido {nro_pedido}")
                return False
                
        except Exception as e:
            logger.error(f"Error al actualizar estado para pedido {nro_pedido}: {e}")
            return False

    def update_entregado(self, nro_pedido: str, talon_ped: str, fecha_entrega: datetime = None) -> bool:
        """
        Actualiza el estado de entregado en la tabla RO_T_ESTADO_PEDIDOS_ECOMMERCE.
        
        Args:
            nro_pedido (str): Número de pedido
            talon_ped (str): Talón del pedido
            fecha_entrega (datetime, optional): Fecha de entrega, si no se proporciona usa la actual
            
        Returns:
            bool: True si la actualización fue exitosa
        """
        try:
            # Verificar si el pedido existe en la tabla de ecommerce
            if not self._check_pedido_exists_in_ecommerce(nro_pedido, talon_ped):
                logger.debug(f"Pedido {nro_pedido} no existe en RO_T_ESTADO_PEDIDOS_ECOMMERCE - no requiere actualización")
                return False
            
            if fecha_entrega is None:
                fecha_entrega = datetime.now()
            
            # Agregar espacio al inicio del número de pedido para evitar errores de SQL Server
            nro_pedido_formatted = f" {nro_pedido.strip()}"
            
            params = [fecha_entrega, nro_pedido_formatted, talon_ped]
            result = self.conexion.ejecutar_update(QRY_UPDATE_ENTREGADO, params)
            
            if result:
                logger.info(f"Pedido {nro_pedido} marcado como entregado en ecommerce")
                return True
            else:
                logger.warning(f"No se pudo marcar como entregado el pedido {nro_pedido}")
                return False
                
        except Exception as e:
            logger.error(f"Error al marcar como entregado el pedido {nro_pedido}: {e}")
            return False

    def _check_pedido_exists_in_ecommerce(self, nro_pedido: str, talon_ped: str) -> bool:
        """
        Verifica si un pedido existe en la tabla RO_T_ESTADO_PEDIDOS_ECOMMERCE.
        
        Args:
            nro_pedido (str): Número de pedido
            talon_ped (str): Talón del pedido
            
        Returns:
            bool: True si el pedido existe
        """
        try:
            # Agregar espacio al inicio del número de pedido para evitar errores de SQL Server
            nro_pedido_formatted = f" {nro_pedido.strip()}"
            
            params = [nro_pedido_formatted, talon_ped]
            resultado = self.conexion.ejecutar_consulta_con_parametros(QRY_CHECK_PEDIDO_ECOMMERCE, params)
            
            if resultado and len(resultado) > 0:
                count = resultado[0][0]
                return count > 0
            else:
                return False
                
        except Exception as e:
            logger.error(f"Error al verificar existencia del pedido {nro_pedido}: {e}")
            return False

    def get_pedido_by_seguimiento(self, num_seguimiento: str) -> Optional[Tuple]:
        """
        Obtiene información de un pedido por número de seguimiento.
        
        Args:
            num_seguimiento (str): Número de seguimiento
            
        Returns:
            Tuple: Información del pedido (NRO_PEDIDO, NUM_SEGUIMIENTO, TALON_PED, estadoEnvio, estadoIdEnvio)
        """
        try:
            params = [num_seguimiento]
            resultados = self.conexion.ejecutar_consulta_con_parametros(QRY_GET_PEDIDO_BY_SEGUIMIENTO, params)
            
            if resultados and len(resultados) > 0:
                logger.info(f"Pedido encontrado para seguimiento {num_seguimiento}")
                return resultados[0]
            else:
                logger.warning(f"No se encontró pedido para seguimiento {num_seguimiento}")
                return None
                
        except Exception as e:
            logger.error(f"Error al buscar pedido por seguimiento {num_seguimiento}: {e}")
            return None

    def process_bulk_status_update(self, status_updates: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Procesa actualizaciones masivas de estados.
        
        Args:
            status_updates (List[Dict]): Lista de diccionarios con información de actualizaciones
            Formato esperado: [
                {
                    'nro_pedido': str,
                    'talon_ped': str,
                    'num_seguimiento': str,
                    'estado_texto': str,
                    'estado_id': int,
                    'fecha_estado': datetime (opcional)
                }
            ]
            
        Returns:
            Dict[str, int]: Estadísticas de la operación
        """
        stats = {
            'procesados': 0,
            'exitosos': 0,
            'errores': 0,
            'entregados': 0
        }
        
        logger.info(f"Iniciando procesamiento masivo de {len(status_updates)} actualizaciones")
        
        for update in status_updates:
            stats['procesados'] += 1
            
            try:
                nro_pedido = update['nro_pedido']
                talon_ped = update['talon_ped']
                estado_texto = update['estado_texto']
                estado_id = update['estado_id']
                fecha_estado = update.get('fecha_estado')
                
                # Actualizar estado en SEIN_TABLA_TEMPORAL_SCRIPT
                if self.update_estado_envio(nro_pedido, talon_ped, estado_texto, estado_id, fecha_estado):
                    stats['exitosos'] += 1
                    
                    # Si el estado es COMPLETADO (3), intentar actualizar la tabla de ecommerce
                    if estado_id == 3:
                        # Verificar PRIMERO si el pedido existe en ecommerce
                        if self._check_pedido_exists_in_ecommerce(nro_pedido, talon_ped):
                            if self.update_entregado(nro_pedido, talon_ped, fecha_estado):
                                stats['entregados'] += 1
                                logger.info(f"Pedido {nro_pedido} marcado como entregado en ecommerce")
                            else:
                                logger.warning(f"Error técnico al marcar como entregado: {nro_pedido}")
                        else:
                            logger.info(f"Pedido {nro_pedido} no requiere actualización en ecommerce (no existe en esa tabla)")
                            # No contamos esto como error, es una situación normal
                else:
                    stats['errores'] += 1
                    
            except Exception as e:
                logger.error(f"Error procesando actualización: {e}")
                stats['errores'] += 1
        
        logger.info(f"Procesamiento masivo completado: {stats}")
        return stats

    def close_connection(self):
        """Cierra la conexión a la base de datos."""
        try:
            if self.conexion:
                # Aquí podrías agregar lógica para cerrar la conexión si tu clase Conexion lo soporta
                logger.info("Conexión a base de datos cerrada")
        except Exception as e:
            logger.error(f"Error al cerrar conexión: {e}")