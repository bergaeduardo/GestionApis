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
logger = setup_logger('sync_stock_jauser')

def main():
    logger.info("Iniciando sincronización de stock de Jauser...")

    # Inicializar la API y la DB
    api = JauserAPI()
    db = JauserDB()

    try:
        # 1. Obtener token de autenticación
        token = api.get_token()
        if not token:
            logger.error("No se pudo obtener el token de autenticación.")
            return
        logger.info("Token de autenticación obtenido exitosamente.")

        # 2. Consultar stock Nacional
        stock_nacional = api.get_stock_nacional(token)
        if stock_nacional is None:
            logger.error("No se pudo obtener el stock nacional.")
            return
        logger.info(f"Stock nacional obtenido: {len(stock_nacional)} items.")

        # 3. Consultar stock Fiscal
        stock_fiscal = api.get_stock_fiscal(token)
        if stock_fiscal is None:
            logger.error("No se pudo obtener el stock fiscal.")
            return
        logger.info(f"Stock fiscal obtenido: {len(stock_fiscal)} items.")

        # Combinar los stocks si es necesario o procesarlos por separado
        # Por ahora, vamos a procesar ambos sets de datos.
        all_stock_items = stock_nacional + stock_fiscal # O manejar por separado según necesites
        logger.info(f"Total de items de stock a procesar: {len(all_stock_items)}.")

        # 4. Eliminar datos existentes en la tabla
        db.clear_stock_table()
        logger.info("Datos de stock existentes eliminados de la tabla.")

        # 5. Almacenar los nuevos datos
        db.insert_stock_data(all_stock_items)
        logger.info("Nuevos datos de stock insertados en la tabla.")

        logger.info("Sincronización de stock de Jauser finalizada exitosamente.")

    except Exception as e:
        logger.error(f"Ocurrió un error durante la sincronización: {e}")

if __name__ == "__main__":
    main()