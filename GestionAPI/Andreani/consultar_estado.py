import asyncio
import argparse
import sys
import os
import logging
from datetime import datetime

# Agrega el directorio raíz del proyecto al sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from GestionAPI.Andreani.andreani_api import AndreaniAPI
from GestionAPI.common.credenciales import DATA_PROD
from GestionAPI.Andreani.db_operations_andreani import AndreaniDB

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('consultar_estado')

async def consultar_estado_envio_api(numero_envio: str):
    """
    Consulta el estado de un envío en la API de Andreani.

    Args:
        numero_envio (str): El número de envío a consultar.

    Returns:
        dict: La información del estado del envío o None si hay un error.
    """
    api = AndreaniAPI(
        base_url=DATA_PROD["url"],
        user=DATA_PROD["user"],
        password=DATA_PROD["passw"]
    )
    try:
        logger.info(f"Consultando API de Andreani para el envío: {numero_envio}")
        estado_envio = await api.consultar_estado_envio(numero_envio)

        if estado_envio:
            # Retornar solo los campos requeridos
            return {
                "estado": estado_envio.get("estado"),
                "estadoId": estado_envio.get("estadoId"),
                "fechaEstado": estado_envio.get("fechaEstado")
            }
    except Exception as e:
        logger.error(f"Ocurrió un error al consultar el estado del envío: {e}")
        return None

async def actualizar_estados_envios():
    """
    Consulta y actualiza los estados de envíos pendientes en la base de datos.
    
    Busca todos los registros con:
    - IMP_ROT = 1
    - NUM_SEGUIMIENTO IS NOT NULL
    - estadoIdEnvio <> 18 (o IS NULL)
    
    Para cada registro, consulta el estado en la API y actualiza la base de datos.
    """
    db = AndreaniDB()
    
    # Obtener envíos pendientes de actualización
    logger.info("Obteniendo envíos pendientes de actualización...")
    envios_pendientes = db.get_envios_pendientes()
    
    if not envios_pendientes:
        logger.info("No hay envíos pendientes para actualizar.")
        return
    
    logger.info(f"Se encontraron {len(envios_pendientes)} envíos pendientes.")
    
    # Procesar cada envío
    envios_actualizados = 0
    envios_con_error = 0
    
    for registro in envios_pendientes:
        nro_pedido = registro[0]
        num_seguimiento = registro[1]
        
        logger.info(f"Procesando pedido {nro_pedido} - Seguimiento: {num_seguimiento}")
        
        # Consultar estado del envío en la API
        estado_info = await consultar_estado_envio_api(num_seguimiento)
        
        if estado_info:
            estado = estado_info.get("estado")
            estado_id = estado_info.get("estadoId")
            fecha_estado = estado_info.get("fechaEstado")
            
            # Actualizar en la base de datos
            if db.update_estado_envio(num_seguimiento, estado, estado_id, fecha_estado):
                logger.info(f"✓ Pedido {nro_pedido} actualizado: {estado} (ID: {estado_id})")
                envios_actualizados += 1
            else:
                logger.error(f"✗ Error al actualizar pedido {nro_pedido} en la base de datos")
                envios_con_error += 1
        else:
            logger.warning(f"✗ No se pudo obtener información del envío {num_seguimiento} (Pedido: {nro_pedido})")
            envios_con_error += 1
        
        # Pequeña pausa entre llamadas a la API
        await asyncio.sleep(0.5)
    
    logger.info(f"\n=== Resumen de actualización ===")
    logger.info(f"Total envíos procesados: {len(envios_pendientes)}")
    logger.info(f"Actualizados exitosamente: {envios_actualizados}")
    logger.info(f"Con errores: {envios_con_error}")

async def main():
    """
    Función principal para ejecutar la consulta desde la línea de comandos.
    """
    parser = argparse.ArgumentParser(
        description="Consultar y actualizar estados de envíos de Andreani."
    )
    parser.add_argument(
        "--numero_envio",
        type=str,
        help="El número de envío específico a consultar (opcional)."
    )
    parser.add_argument(
        "--actualizar",
        action="store_true",
        help="Actualizar todos los estados de envíos pendientes en la base de datos."
    )
    
    args = parser.parse_args()
    
    if args.actualizar:
        # Modo de actualización masiva
        await actualizar_estados_envios()
    elif args.numero_envio:
        # Modo de consulta individual con actualización en BD
        db = AndreaniDB()
        resultado = await consultar_estado_envio_api(args.numero_envio)
        
        if resultado:
            print("\nInformación del envío:")
            print(resultado)
            
            # Guardar en la base de datos
            estado = resultado.get("estado")
            estado_id = resultado.get("estadoId")
            fecha_estado = resultado.get("fechaEstado")
            
            if db.update_estado_envio(args.numero_envio, estado, estado_id, fecha_estado):
                print(f"\n✓ Estado actualizado en la base de datos para el envío {args.numero_envio}")
            else:
                print(f"\n✗ No se pudo actualizar el estado en la base de datos")
        else:
            print("\nNo se pudo obtener información para el envío especificado.")
    else:
        # Si no se especifica ningún argumento, ejecutar actualización masiva por defecto
        print("Ejecutando actualización masiva de estados de envíos...")
        await actualizar_estados_envios()

if __name__ == "__main__":
    # Para ejecutar en Windows con asyncio
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())
