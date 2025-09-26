import sys
import os
import logging

# Añadir la raíz del proyecto a sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from GestionAPI.common.logger_config import setup_logger
from GestionAPI.common.db_operations import DatabaseConnection
from GestionAPI.Solar.api_client import SolarApiClient
from GestionAPI.common.credenciales import LOCALES_LAKERS, API_SOLAR

def test_api_connection(logger):
    """
    Prueba la conexión con la API de Solar obteniendo un token.
    """
    logger.info("Iniciando prueba de conexión a la API de Solar...")
    try:
        api_client = SolarApiClient()
        token = api_client.obtener_token(API_SOLAR)
        if token:
            logger.info("Conexión con la API de Solar exitosa. Token obtenido.")
            return True
        else:
            logger.error("Fallo al conectar con la API de Solar. No se pudo obtener el token.")
            return False
    except Exception as e:
        logger.error(f"Error inesperado durante la prueba de conexión a la API: {e}", exc_info=True)
        return False

def test_db_connection(logger):
    """
    Prueba la conexión con la base de datos.
    """
    logger.info("Iniciando prueba de conexión a la base de datos...")
    try:
        db = DatabaseConnection(
            server=LOCALES_LAKERS['server'],
            database=LOCALES_LAKERS['database'],
            user=LOCALES_LAKERS['user'],
            password=LOCALES_LAKERS['password']
        )
        cursor = db.conectar()
        if cursor:
            logger.info("Conexión con la base de datos exitosa.")
            cursor.close()
            db.connection.close()
            return True
        else:
            logger.error("Fallo al conectar con la base de datos.")
            return False
    except Exception as e:
        logger.error(f"Error inesperado durante la prueba de conexión a la base de datos: {e}", exc_info=True)
        return False

def main():
    """
    Función principal para ejecutar las pruebas de conexión.
    """
    logger = setup_logger('solar_connection_test')
    
    logger.info("=============================================")
    logger.info("     INICIANDO PRUEBAS DE CONEXIÓN SOLAR     ")
    logger.info("=============================================")
    
    api_success = test_api_connection(logger)
    db_success = test_db_connection(logger)
    
    logger.info("=============================================")
    logger.info("            RESUMEN DE LAS PRUEBAS           ")
    logger.info("=============================================")
    logger.info(f"Conexión API: {'ÉXITO' if api_success else 'FALLO'}")
    logger.info(f"Conexión BD:  {'ÉXITO' if db_success else 'FALLO'}")
    logger.info("=============================================")

if __name__ == "__main__":
    main()
