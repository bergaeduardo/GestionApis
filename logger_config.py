import logging
import os
from datetime import datetime

def setup_logger():
    # Crear el directorio logs si no existe
    if not os.path.exists('logs'):
        os.makedirs('logs')
        
    # Configurar el logger principal
    logger = logging.getLogger('solar_sync')
    logger.setLevel(logging.INFO)
    
    # Crear el formato para los logs
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s - %(module)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler para archivo
    file_handler = logging.FileHandler('logs/app.log')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    
    # Handler para consola
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    
    # Agregar handlers al logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger