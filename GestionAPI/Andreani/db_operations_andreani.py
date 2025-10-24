import logging
from GestionAPI.common.conexion import Conexion
from GestionAPI.common.credenciales import CENTRAL_LAKERS
from GestionAPI.Andreani.consultas import (
    QRY_GET_DATA_FROM_SEIN, 
    QRY_UPDATE_IMP_ROT, 
    QRY_GET_ENVIOS_PENDIENTES, 
    QRY_UPDATE_ESTADO_ENVIO, 
    QRY_UPDATE_ENTREGADO,
    QRY_GET_PEDIDO_BY_SEGUIMIENTO
)

logger = logging.getLogger('andreani_rotulos')

class AndreaniDB:
    def __init__(self):
        self.db_config = CENTRAL_LAKERS
        self.conexion = Conexion(
            server=self.db_config['server'],
            database=self.db_config['database'],
            user=self.db_config['user'],
            password=self.db_config['password']
        )

    def get_data_from_sein(self):
        """
        Obtiene los datos de la tabla SEIN_TABLA_TEMPORAL_SCRIPT.
        """
        try:
            # Ejecutar la consulta
            resultados = self.conexion.ejecutar_consulta(QRY_GET_DATA_FROM_SEIN)
            
            if resultados:
                logger.info("Datos obtenidos correctamente desde SEIN_TABLA_TEMPORAL_SCRIPT.")
                return resultados
            else:
                logger.info("No se encontraron datos en SEIN_TABLA_TEMPORAL_SCRIPT.")
                return None
        except Exception as e:
            logger.error(f"Error al obtener datos de SEIN_TABLA_TEMPORAL_SCRIPT: {e}")
            return None

    def update_imp_rot(self, nro_pedido, numero_envio):
        """
        Actualiza el campo IMP_ROT a 1 y el NUM_SEGUIMIENTO para un pedido específico.
        """
        # Agregar un caracter vacio por delante para evitar errores de SQL Server
        nro_pedido = f" {nro_pedido}"
        try:
            # La consulta ahora espera (numero_envio, nro_pedido)
            if self.conexion.ejecutar_update(QRY_UPDATE_IMP_ROT, (numero_envio, nro_pedido)):
                logger.info(f"IMP_ROT y NUM_SEGUIMIENTO actualizados para el pedido {nro_pedido}.")
                return True
            else:
                logger.error(f"Fallo al ejecutar el update de IMP_ROT y NUM_SEGUIMIENTO para el pedido {nro_pedido}.")
                return False
        except Exception as e:
            logger.error(f"Error al actualizar IMP_ROT y NUM_SEGUIMIENTO para el pedido {nro_pedido}: {e}")
            return False

    def get_envios_pendientes(self):
        """
        Obtiene los envíos con IMP_ROT=1, NUM_SEGUIMIENTO IS NOT NULL y estadoIdEnvio <> 18.
        """
        try:
            resultados = self.conexion.ejecutar_consulta(QRY_GET_ENVIOS_PENDIENTES)
            
            if resultados:
                logger.info(f"Se encontraron {len(resultados)} envíos pendientes de actualización.")
                return resultados
            else:
                logger.info("No se encontraron envíos pendientes de actualización.")
                return []
        except Exception as e:
            logger.error(f"Error al obtener envíos pendientes: {e}")
            return []

    def update_estado_envio(self, num_seguimiento, estado, estado_id, fecha_estado, nro_pedido=None, talon_ped=None):
        """
        Actualiza el estado del envío en la tabla SEIN_TABLA_TEMPORAL_SCRIPT.
        Si el estado es 18 (Entregado), también actualiza la tabla RO_T_ESTADO_PEDIDOS_ECOMMERCE.
        """
        try:
            if self.conexion.ejecutar_update(QRY_UPDATE_ESTADO_ENVIO, (estado, estado_id, fecha_estado, num_seguimiento)):
                logger.info(f"Estado del envío actualizado para el seguimiento {num_seguimiento}.")
                
                # Si el estado es 18 (Entregado), actualizar también RO_T_ESTADO_PEDIDOS_ECOMMERCE
                if estado_id == 18 and nro_pedido and talon_ped:
                    try:
                        # Limpiar los valores (quitar espacios)
                        nro_pedido_limpio = str(nro_pedido).strip()
                        talon_ped_limpio = str(talon_ped).strip()
                        
                        # Convertir fecha de formato ISO 8601 a formato SQL Server
                        from datetime import datetime
                        if isinstance(fecha_estado, str):
                            try:
                                fecha_dt = datetime.fromisoformat(fecha_estado.replace('Z', '+00:00'))
                                fecha_formateada = fecha_dt.strftime('%Y-%m-%d %H:%M:%S')
                            except:
                                fecha_formateada = fecha_estado
                                logger.warning(f"No se pudo convertir la fecha, usando valor original: {fecha_estado}")
                        else:
                            fecha_formateada = fecha_estado
                        
                        # Ejecutar el UPDATE
                        if self.conexion.ejecutar_update(QRY_UPDATE_ENTREGADO, (fecha_formateada, nro_pedido_limpio, talon_ped_limpio)):
                            logger.info(f"Tabla RO_T_ESTADO_PEDIDOS_ECOMMERCE actualizada para el pedido {nro_pedido_limpio}, talon {talon_ped_limpio}.")
                        else:
                            logger.warning(f"No se pudo actualizar RO_T_ESTADO_PEDIDOS_ECOMMERCE para el pedido {nro_pedido_limpio}, talon {talon_ped_limpio}.")
                    except Exception as e:
                        logger.error(f"Error al actualizar RO_T_ESTADO_PEDIDOS_ECOMMERCE para el pedido {nro_pedido}, talon {talon_ped}: {e}")
                elif estado_id == 18 and not talon_ped:
                    logger.warning(f"No se puede actualizar RO_T_ESTADO_PEDIDOS_ECOMMERCE: falta TALON_PED para el pedido {nro_pedido}")
                
                return True
            else:
                logger.error(f"Fallo al actualizar el estado del envío para el seguimiento {num_seguimiento}.")
                return False
        except Exception as e:
            logger.error(f"Error al actualizar el estado del envío para el seguimiento {num_seguimiento}: {e}")
            return False

    def get_pedido_by_seguimiento(self, num_seguimiento):
        """
        Obtiene el número de pedido y TALON_PED a partir del número de seguimiento.
        Retorna una tupla (nro_pedido, talon_ped).
        """
        try:
            resultados = self.conexion.ejecutar_consulta(
                QRY_GET_PEDIDO_BY_SEGUIMIENTO.replace('?', f"'{num_seguimiento}'")
            )
            
            if resultados and len(resultados) > 0:
                nro_pedido = resultados[0][0]
                talon_ped = resultados[0][1] if len(resultados[0]) > 1 else None
                logger.info(f"Datos encontrados - Pedido: {nro_pedido}, Talon: {talon_ped} para seguimiento {num_seguimiento}")
                return (nro_pedido, talon_ped)
            else:
                logger.warning(f"No se encontró información para el seguimiento {num_seguimiento}")
                return (None, None)
        except Exception as e:
            logger.error(f"Error al obtener información para el seguimiento {num_seguimiento}: {e}")
            return (None, None)