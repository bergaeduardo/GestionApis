import logging
import os
from datetime import datetime

def setup_logger(name, log_path=None):
    """
    Configura un logger con handlers para archivo y consola.
    
    Args:
        name: Nombre del logger
        log_path: Ruta absoluta al archivo de log. Si es None, usa 'logs/app.log' relativo
    """
    # Si no se especifica ruta, usar la ruta relativa por defecto
    if log_path is None:
        log_dir = 'logs'
        log_file = 'logs/app.log'
    else:
        log_dir = os.path.dirname(log_path)
        log_file = log_path
    
    # Crear el directorio logs si no existe
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    # Configurar el logger principal
    logger = logging.getLogger(name)
    
    # Evitar duplicar handlers si el logger ya existe
    if logger.handlers:
        logger.handlers.clear()
        
    logger.setLevel(logging.DEBUG)
    
    # Crear el formato para los logs
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s - %(module)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler para archivo
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    
    # Handler para consola
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG)
    
    # Agregar handlers al logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger