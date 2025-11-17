"""
Módulo Welivery - Gestión de envíos y seguimiento

Este módulo proporciona funcionalidad completa para integrar con la API de Welivery,
permitiendo:

- Crear envíos para pedidos pendientes
- Consultar estados de envío
- Actualizar información en base de datos local
- Manejar estados de entrega y completado

Clases principales:
- WeliveryAPI: Cliente API asíncrono para consultas de estado
- WeliveryDB: Operaciones de base de datos
- WeliverySync: Sincronizador principal

Uso básico:
    from GestionAPI.Welivery.sync_welivery import WeliverySync
    
    sync = WeliverySync()
    await sync.sincronizar_completo()
"""

from .welivery_api import WeliveryAPI
from .db_operations_welivery import WeliveryDB
from .sync_welivery import WeliverySync

__version__ = "1.0.0"
__author__ = "GestionAPI Team"

# Exportar clases principales
__all__ = [
    'WeliveryAPI',
    'WeliveryDB', 
    'WeliverySync'
]