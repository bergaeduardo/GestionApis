#!/usr/bin/env python3
"""
Script para marcar como procesados los comprobantes que ya existen en Solar
pero que quedaron pendientes en nuestra base de datos.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.db_operations import DatabaseOperations
from common.logger_config import setup_logger

# Configurar logger
logger = setup_logger(__name__, 'logs/actualizar_estados.log')

def actualizar_estados_procesados():
    """
    Actualiza el estado de comprobantes específicos que ya fueron procesados en Solar
    """
    
    # Lista de comprobantes que ya están procesados en Solar
    # AGREGAR AQUÍ LOS COMPROBANTES QUE YA ESTÁN PROCESADOS
    comprobantes_procesados = [
        # Ejemplo: 'A0021500000977', 'B0021500040374', 'B0021500040376'
        # COMPLETAR CON LOS COMPROBANTES REALES
    ]
    
    if not comprobantes_procesados:
        logger.warning("No hay comprobantes especificados para actualizar")
        print("IMPORTANTE: Debes especificar los comprobantes en la lista 'comprobantes_procesados'")
        return False
    
    try:
        db = DatabaseOperations()
        
        # Mostrar comprobantes que se van a actualizar
        print("Comprobantes que se marcarán como procesados:")
        for comp in comprobantes_procesados:
            print(f"  - {comp}")
        
        # Confirmar operación
        respuesta = input("\n¿Confirmas que estos comprobantes YA están procesados en Solar? (s/n): ").strip().lower()
        if respuesta != 's':
            print("Operación cancelada")
            return False
        
        # Crear string de comprobantes para SQL
        comprobantes_str = "('" + "', '".join(comprobantes_procesados) + "')"
        
        # Actualizar estados
        if db.actualizar_estado_sync(comprobantes_str):
            logger.info(f"Estados actualizados exitosamente para {len(comprobantes_procesados)} comprobantes")
            print(f"✅ {len(comprobantes_procesados)} comprobantes marcados como procesados")
            return True
        else:
            logger.error("Error al actualizar estados")
            print("❌ Error al actualizar estados")
            return False
            
    except Exception as e:
        logger.error(f"Error en actualización de estados: {str(e)}")
        print(f"❌ Error: {str(e)}")
        return False

def consultar_pendientes():
    """
    Consulta los comprobantes que están pendientes de sincronizar
    """
    try:
        db = DatabaseOperations()
        cursor = db.conectar()
        
        if cursor:
            cursor.execute("SELECT N_COMP, CONVERT(VARCHAR, FECHA_EMIS, 105) AS Fecha FROM EB_T_HistorialSincVentas_Solar WHERE ESTADO_SYNC = 0 ORDER BY FECHA_EMIS DESC")
            pendientes = cursor.fetchall()
            
            if pendientes:
                print(f"📋 Comprobantes pendientes de sincronizar ({len(pendientes)}):")
                print("=" * 50)
                for comp in pendientes[:20]:  # Mostrar solo los primeros 20
                    print(f"  {comp[0]} - {comp[1]}")
                
                if len(pendientes) > 20:
                    print(f"  ... y {len(pendientes) - 20} más")
                    
            else:
                print("✅ No hay comprobantes pendientes")
                
            cursor.close()
            db.connection.close()
            
    except Exception as e:
        logger.error(f"Error consultando pendientes: {str(e)}")
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    print("=== ACTUALIZADOR DE ESTADOS SOLAR ===")
    print("1. Consultar pendientes")
    print("2. Actualizar estados procesados")
    
    opcion = input("Selecciona una opción (1 o 2): ").strip()
    
    if opcion == "1":
        consultar_pendientes()
    elif opcion == "2":
        actualizar_estados_procesados()
    else:
        print("Opción no válida")