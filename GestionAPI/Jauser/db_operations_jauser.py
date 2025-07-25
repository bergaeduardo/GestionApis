#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os

# Obtiene la ruta del directorio padre (la raíz del proyecto)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
# Añade la ruta de la raíz del proyecto a sys.path
sys.path.insert(0, project_root)

import logging
from GestionAPI.common.conexion import Conexion
from GestionAPI.common.credenciales import CENTRAL_TASKY

logger = logging.getLogger(__name__)

class JauserDB:
    def __init__(self):
        self.db_config = CENTRAL_TASKY
        self.conexion = Conexion(
            server=self.db_config['server'],
            database=self.db_config['database'],
            user=self.db_config['user'],
            password=self.db_config['password']
        )
    
    def create_stock_table(self):
        """Crea la tabla de stock si no existe"""
        sql_create_table = """
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='jauser_stock' AND xtype='U')
        BEGIN
            CREATE TABLE jauser_stock (
                id INT IDENTITY(1,1) PRIMARY KEY,
                piezas VARCHAR(50),
                descripcion VARCHAR(255),
                codigo VARCHAR(100),
                model VARCHAR(255),
                tipo_deposito VARCHAR(20), -- 'NACIONAL' o 'FISCAL'
                fecha_actualizacion DATETIME DEFAULT GETDATE()
            );
            
            CREATE INDEX idx_jauser_stock_codigo ON jauser_stock(codigo);
            CREATE INDEX idx_jauser_stock_tipo ON jauser_stock(tipo_deposito);
        END
        """
        
        try:
            cursor = self.conexion.conectar()
            if cursor:
                cursor.execute(sql_create_table)
                self.conexion.connection.commit()
                logger.info("Tabla jauser_stock creada exitosamente")
                cursor.close()
                self.conexion.connection.close()
                return True
        except Exception as e:
            logger.error(f"Error al crear tabla: {e}")
            return False
    
    def clear_stock_table(self):
        """Elimina todos los datos existentes de la tabla de stock"""
        try:
            cursor = self.conexion.conectar()
            if cursor:
                sql = "TRUNCATE TABLE jauser_stock"
                cursor.execute(sql)
                self.conexion.connection.commit()
                cursor.close()
                self.conexion.connection.close()
                logger.info("Datos de stock eliminados exitosamente")
                return True
        except Exception as e:
            logger.error(f"Error al limpiar tabla: {e}")
            return False
    
    def insert_stock_data(self, stock_items, tipo_deposito):
        """Inserta los nuevos datos de stock en la tabla"""
        try:
            cursor = self.conexion.conectar()
            if cursor:
                sql_insert = """
                INSERT INTO jauser_stock (piezas, descripcion, codigo, model, tipo_deposito)
                VALUES (?, ?, ?, ?, ?)
                """
                
                for item in stock_items:
                    cursor.execute(sql_insert, (
                        item.get('Piezas', ''),
                        item.get('Descripción', ''),
                        item.get('Código', ''),
                        item.get('Model', ''),
                        tipo_deposito
                    ))
                
                self.conexion.connection.commit()
                cursor.close()
                self.conexion.connection.close()
                logger.info(f"{len(stock_items)} items de stock {tipo_deposito} insertados exitosamente")
                return True
        except Exception as e:
            logger.error(f"Error al insertar datos: {e}")
            return False
    
    def get_stock_count(self, tipo_deposito=None):
        """Obtiene el conteo de registros en la tabla de stock"""
        try:
            if tipo_deposito:
                sql = "SELECT COUNT(*) FROM jauser_stock WHERE tipo_deposito = ?"
                result = self.conexion.ejecutar_consulta(sql)
            else:
                sql = "SELECT COUNT(*) FROM jauser_stock"
                result = self.conexion.ejecutar_consulta(sql)
            
            return result[0][0] if result else 0
        except Exception as e:
            logger.error(f"Error al obtener conteo: {e}")
            return 0
