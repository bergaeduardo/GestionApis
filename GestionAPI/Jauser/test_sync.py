#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os

# Obtiene la ruta del directorio padre (la raíz del proyecto)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
# Añade la ruta de la raíz del proyecto a sys.path
sys.path.insert(0, project_root)

import logging
from GestionAPI.common.logger_config import setup_logger
from GestionAPI.Jauser.api_jauser import JauserAPI
from GestionAPI.Jauser.db_operations_jauser import JauserDB

# Configurar el logger
logger = setup_logger('test_jauser_sync')

def test_database_connection():
    """Prueba la conexión a la base de datos"""
    logger.info("=== TEST CONEXIÓN BASE DE DATOS ===")
    db = JauserDB()
    
    # Probar creación de tabla
    if db.create_stock_table():
        logger.info("✅ Tabla creada exitosamente")
    else:
        logger.error("❌ Error al crear tabla")
    
    # Probar inserción de datos de prueba
    test_data = [
        {"Piezas": "5", "Descripción": "TEST ITEM 1", "Código": "TEST001", "Model": "TEST MODEL"},
        {"Piezas": "3", "Descripción": "TEST ITEM 2", "Código": "TEST002", "Model": ""}
    ]
    
    if db.insert_stock_data(test_data, "NACIONAL"):
        logger.info("✅ Datos de prueba insertados")
    else:
        logger.error("❌ Error al insertar datos de prueba")
    
    # Verificar conteo
    count = db.get_stock_count()
    logger.info(f"📊 Total de registros en tabla: {count}")
    
    return True

def test_api_connection():
    """Prueba la conexión a la API de Jauser"""
    logger.info("=== TEST CONEXIÓN API JAUSER ===")
    api = JauserAPI()
    
    # Obtener token
    token = api.get_token()
    if token:
        logger.info("✅ Token obtenido exitosamente")
        
        # Probar obtener stock nacional
        stock_nacional = api.get_stock_nacional(token)
        if stock_nacional:
            logger.info(f"✅ Stock nacional obtenido: {len(stock_nacional)} items")
        else:
            logger.error("❌ Error al obtener stock nacional")
        
        # Probar obtener stock fiscal
        stock_fiscal = api.get_stock_fiscal(token)
        if stock_fiscal:
            logger.info(f"✅ Stock fiscal obtenido: {len(stock_fiscal)} items")
        else:
            logger.error("❌ Error al obtener stock fiscal")
        
        return True
    else:
        logger.error("❌ Error al obtener token")
        return False

def main():
    """Función principal de pruebas"""
    logger.info("🚀 Iniciando pruebas del módulo Jauser")
    
    # Test 1: Conexión a base de datos
    test_database_connection()
    
    # Test 2: Conexión a API
    test_api_connection()
    
    logger.info("✨ Pruebas finalizadas")

if __name__ == "__main__":
    main()
