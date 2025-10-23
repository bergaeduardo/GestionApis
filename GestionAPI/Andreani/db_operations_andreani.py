import logging
from GestionAPI.common.conexion import Conexion
from GestionAPI.common.credenciales import CENTRAL_LAKERS
from GestionAPI.Andreani.consultas import QRY_GET_DATA_FROM_SEIN, QRY_UPDATE_IMP_ROT, QRY_GET_ENVIOS_PENDIENTES, QRY_UPDATE_ESTADO_ENVIO

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

    def update_estado_envio(self, num_seguimiento, estado, estado_id, fecha_estado):
        """
        Actualiza el estado del envío en la tabla SEIN_TABLA_TEMPORAL_SCRIPT.
        """
        try:
            if self.conexion.ejecutar_update(QRY_UPDATE_ESTADO_ENVIO, (estado, estado_id, fecha_estado, num_seguimiento)):
                logger.info(f"Estado del envío actualizado para el seguimiento {num_seguimiento}.")
                return True
            else:
                logger.error(f"Fallo al actualizar el estado del envío para el seguimiento {num_seguimiento}.")
                return False
        except Exception as e:
            logger.error(f"Error al actualizar el estado del envío para el seguimiento {num_seguimiento}: {e}")
            return False