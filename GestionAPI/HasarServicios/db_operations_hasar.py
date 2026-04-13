#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Operaciones de base de datos para el módulo HasarServicios
Maneja la lectura de configuración y escritura de datos de conteo de personas
"""

import sys
import os

# Obtiene la ruta del directorio padre (la raíz del proyecto)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
# Añade la ruta de la raíz del proyecto a sys.path
sys.path.insert(0, project_root)

import logging
from datetime import datetime
from GestionAPI.common.conexion import Conexion
from GestionAPI.common.credenciales import POWER_BI_CONTROL, POWER_BI_CONTROL_FRANQUICIAS
from GestionAPI.HasarServicios.consultas import (
    QRY_OBTENER_CONFIG, 
    QRY_CONTAR_TOTAL,
    QRY_MERGE_INGRESOS,
    QRY_VERIFICAR_DATOS
)

logger = logging.getLogger(__name__)

class HasarDB:
    """
    Clase para manejar operaciones de base de datos del módulo HasarServicios.
    Soporta conexiones dinámicas a múltiples bases de datos.
    """
    
    def __init__(self):
        """
        Inicializa configuraciones de bases de datos disponibles.
        """
        self.db_configs = {
            'POWER_BI_CONTROL': POWER_BI_CONTROL,
            'POWER_BI_CONTROL_FRANQUICIAS': POWER_BI_CONTROL_FRANQUICIAS
        }
        # Conexión por defecto para leer la configuración
        self.config_db = 'POWER_BI_CONTROL'
    
    def _get_connection(self, database_name):
        """
        Obtiene una conexión a la base de datos especificada.
        
        Args:
            database_name (str): Nombre de la base de datos (debe existir en db_configs)
            
        Returns:
            Conexion: Objeto de conexión a la base de datos
        """
        if database_name not in self.db_configs:
            logger.error(f"Base de datos '{database_name}' no configurada")
            return None
        
        config = self.db_configs[database_name]
        return Conexion(
            server=config['server'],
            database=config['database'],
            user=config['user'],
            password=config['password']
        )
    
    def obtener_configuracion_sucursales(self):
        """
        Obtiene la configuración de sucursales activas desde la tabla EB_BilcCamdata_pdv.
        
        Returns:
            list: Lista de diccionarios con la configuración de cada endpoint activo.
                  Cada diccionario contiene: NUMERO_SUCURSAL, NOMBRE_DASHBOARD, API, Token, DATA_BASE, ACTIVO
        """
        try:
            conexion = self._get_connection(self.config_db)
            if not conexion:
                return []
            
            resultados = conexion.ejecutar_consulta(QRY_OBTENER_CONFIG)
            
            if not resultados:
                return []
            
            # Convertir resultados a lista de diccionarios
            configuraciones = []
            for row in resultados:
                config = {
                    'NUMERO_SUCURSAL': row[0],
                    'NOMBRE_DASHBOARD': row[1],
                    'API': row[2],
                    'Token': row[3],
                    'DATA_BASE': row[4],
                    'ACTIVO': row[5]
                }
                configuraciones.append(config)
            
            return configuraciones
            
        except Exception as e:
            logger.error(f"Error al obtener configuración de sucursales: {e}")
            return []
    
    def obtener_estadisticas_config(self):
        """
        Obtiene estadísticas sobre registros activos e inactivos para logging.
        
        Returns:
            dict: Diccionario con contadores (Activos, Inactivos, Total)
        """
        try:
            conexion = self._get_connection(self.config_db)
            if not conexion:
                return {'Activos': 0, 'Inactivos': 0, 'Total': 0}
            
            resultados = conexion.ejecutar_consulta(QRY_CONTAR_TOTAL)
            
            if resultados and len(resultados) > 0:
                row = resultados[0]
                return {
                    'Activos': row[0] or 0,
                    'Inactivos': row[1] or 0,
                    'Total': row[2] or 0
                }
            
            return {'Activos': 0, 'Inactivos': 0, 'Total': 0}
            
        except Exception as e:
            logger.error(f"Error al obtener estadísticas: {e}")
            return {'Activos': 0, 'Inactivos': 0, 'Total': 0}
    
    def upsert_ingresos(self, database_name, fecha, nro_sucurs, ingresos=None, merodeo=None):
        """
        Inserta o actualiza un registro en la tabla BI_T_INGRESOS_SUCURSALES.
        Usa MERGE SQL para atomicidad: si existe el registro (por FECHA + NRO_SUCURS), 
        se actualiza; si no existe, se inserta.
        
        Args:
            database_name (str): Nombre de la base de datos donde insertar
            fecha (datetime.date): Fecha del registro
            nro_sucurs (int): Número de sucursal
            ingresos (int, optional): Cantidad de ingresos. Si es None, se usa 0
            merodeo (int, optional): Cantidad de merodeo. Si es None, se mantiene NULL
            
        Returns:
            bool: True si la operación fue exitosa, False en caso contrario
        """
        try:
            conexion = self._get_connection(database_name)
            if not conexion:
                logger.error(f"No se pudo conectar a la base de datos '{database_name}'")
                return False
            
            # Preparar valores (convertir None a 0 para INGRESOS, mantener NULL para MERODEO)
            ingresos_val = ingresos if ingresos is not None else 0
            merodeo_val = merodeo  # Puede ser None
            
            # Ejecutar MERGE con parámetros
            params = (fecha, nro_sucurs, ingresos_val, merodeo_val)
            cursor = conexion.conectar()
            
            if cursor:
                cursor.execute(QRY_MERGE_INGRESOS, params)
                conexion.connection.commit()
                cursor.close()
                conexion.connection.close()
                
                return True
            else:
                logger.error(f"No se pudo obtener cursor para {database_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error al guardar datos en {database_name}: {e}")
            return False
    
    def verificar_datos_guardados(self, database_name, fecha_inicio, fecha_fin):
        """
        Verifica los datos guardados en un rango de fechas (útil para testing).
        
        Args:
            database_name (str): Nombre de la base de datos
            fecha_inicio (datetime.date): Fecha inicial del rango
            fecha_fin (datetime.date): Fecha final del rango
            
        Returns:
            list: Lista de tuplas con los datos encontrados
        """
        try:
            conexion = self._get_connection(database_name)
            if not conexion:
                return []
            
            cursor = conexion.conectar()
            if cursor:
                cursor.execute(QRY_VERIFICAR_DATOS, (fecha_inicio, fecha_fin))
                resultados = cursor.fetchall()
                cursor.close()
                conexion.connection.close()
                return resultados
            
            return []
            
        except Exception as e:
            logger.error(f"Error al verificar datos en {database_name}: {e}")
            return []
