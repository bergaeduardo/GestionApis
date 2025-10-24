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
    envios_entregados = 0
    
    for registro in envios_pendientes:
        nro_pedido = registro[0]
        num_seguimiento = registro[1]
        talon_ped = registro[2] if len(registro) > 2 else None
        
        logger.info(f"Procesando pedido {nro_pedido} - Seguimiento: {num_seguimiento} - Talon: {talon_ped}")
        
        # Consultar estado del envío en la API
        estado_info = await consultar_estado_envio_api(num_seguimiento)
        
        if estado_info:
            estado = estado_info.get("estado")
            estado_id = estado_info.get("estadoId")
            fecha_estado = estado_info.get("fechaEstado")
            
            logger.info(f"Estado obtenido de API: {estado} (ID: {estado_id})")
            
            # Actualizar en la base de datos (pasando nro_pedido y talon_ped)
            if db.update_estado_envio(num_seguimiento, estado, estado_id, fecha_estado, nro_pedido, talon_ped):
                logger.info(f"✓ Pedido {nro_pedido} actualizado: {estado} (ID: {estado_id})")
                envios_actualizados += 1
                
                # Verificar si se actualizó también RO_T_ESTADO_PEDIDOS_ECOMMERCE
                if estado_id == 18:
                    if talon_ped:
                        logger.info(f"  → Tabla RO_T_ESTADO_PEDIDOS_ECOMMERCE actualizada (Pedido: {nro_pedido}, Talon: {talon_ped})")
                        envios_entregados += 1
                    else:
                        logger.warning(f"  → No se pudo actualizar RO_T_ESTADO_PEDIDOS_ECOMMERCE: falta TALON_PED")
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
    logger.info(f"Envíos entregados (tabla RO_T_ESTADO_PEDIDOS_ECOMMERCE actualizada): {envios_entregados}")
    logger.info(f"Con errores: {envios_con_error}")

async def sincronizar_entregados():
    """
    Sincroniza la tabla RO_T_ESTADO_PEDIDOS_ECOMMERCE con los registros que tienen estadoIdEnvio = 18
    pero que aún no están marcados como entregados en esa tabla.
    """
    db = AndreaniDB()
    
    logger.info("Buscando envíos con estadoIdEnvio = 18 para sincronizar...")
    
    # Consultar todos los registros con estado 18
    query = """
    SELECT NRO_PEDIDO, TALON_PED, fechaEstadoEnvio
    FROM SEIN_TABLA_TEMPORAL_SCRIPT
    WHERE IMP_ROT = 1 
      AND NUM_SEGUIMIENTO IS NOT NULL 
      AND estadoIdEnvio = '18'
    """
    
    registros_entregados = db.conexion.ejecutar_consulta(query)
    
    if not registros_entregados:
        logger.info("No se encontraron registros con estadoIdEnvio = 18 para sincronizar.")
        return
    
    logger.info(f"Se encontraron {len(registros_entregados)} registros con estado Entregado (18).")
    
    sincronizados = 0
    errores = 0
    
    for registro in registros_entregados:
        nro_pedido = registro[0]
        talon_ped = registro[1]
        fecha_entregado = registro[2]
        
        if not talon_ped:
            logger.warning(f"Registro sin TALON_PED: Pedido {nro_pedido}")
            continue
        
        try:
            # Limpiar valores
            nro_pedido_limpio = str(nro_pedido).strip()
            talon_ped_limpio = str(talon_ped).strip()
            
            # Convertir fecha si es necesario
            from datetime import datetime
            if isinstance(fecha_entregado, str):
                try:
                    fecha_dt = datetime.fromisoformat(fecha_entregado.replace('Z', '+00:00'))
                    fecha_formateada = fecha_dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    fecha_formateada = fecha_entregado
            else:
                # Si ya es datetime, convertir a string
                try:
                    fecha_formateada = fecha_entregado.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    fecha_formateada = str(fecha_entregado)
            
            # Verificar si ya está actualizado
            query_check = f"""
            SELECT ENTREGADO 
            FROM RO_T_ESTADO_PEDIDOS_ECOMMERCE
            WHERE LTRIM(RTRIM(NRO_PEDIDO)) = '{nro_pedido_limpio}' 
              AND TALON_PED = {talon_ped_limpio}
            """
            
            resultado_check = db.conexion.ejecutar_consulta(query_check)
            
            if resultado_check and len(resultado_check) > 0:
                entregado_actual = resultado_check[0][0]
                if entregado_actual == 1 or entregado_actual is True:
                    # Ya está marcado como entregado
                    continue
            
            # Actualizar
            from GestionAPI.Andreani.consultas import QRY_UPDATE_ENTREGADO
            if db.conexion.ejecutar_update(QRY_UPDATE_ENTREGADO, (fecha_formateada, nro_pedido_limpio, talon_ped_limpio)):
                logger.info(f"✓ Sincronizado - Pedido: {nro_pedido_limpio}, Talon: {talon_ped_limpio}")
                sincronizados += 1
            else:
                logger.warning(f"⚠ No se pudo actualizar - Pedido: {nro_pedido_limpio}, Talon: {talon_ped_limpio} (puede que no exista en la tabla)")
                
        except Exception as e:
            logger.error(f"✗ Error al sincronizar Pedido {nro_pedido}: {e}")
            errores += 1
    
    logger.info(f"\n=== Resumen de sincronización ===")
    logger.info(f"Total registros con estado 18: {len(registros_entregados)}")
    logger.info(f"Sincronizados exitosamente: {sincronizados}")
    logger.info(f"Con errores: {errores}")

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
    parser.add_argument(
        "--sincronizar",
        action="store_true",
        help="Sincronizar tabla RO_T_ESTADO_PEDIDOS_ECOMMERCE con registros que tienen estadoIdEnvio=18."
    )
    
    args = parser.parse_args()
    
    if args.sincronizar:
        # Modo de sincronización de entregados
        await sincronizar_entregados()
    elif args.actualizar:
        # Modo de actualización masiva
        await actualizar_estados_envios()
    elif args.numero_envio:
        # Modo de consulta individual con actualización en BD
        db = AndreaniDB()
        resultado = await consultar_estado_envio_api(args.numero_envio)
        
        if resultado:
            print("\nInformación del envío:")
            print(resultado)
            
            # Obtener el número de pedido y talon_ped desde la base de datos
            nro_pedido, talon_ped = db.get_pedido_by_seguimiento(args.numero_envio)
            
            # Guardar en la base de datos
            estado = resultado.get("estado")
            estado_id = resultado.get("estadoId")
            fecha_estado = resultado.get("fechaEstado")
            
            if db.update_estado_envio(args.numero_envio, estado, estado_id, fecha_estado, nro_pedido, talon_ped):
                print(f"\n✓ Estado actualizado en la base de datos para el envío {args.numero_envio}")
                if estado_id == 18 and nro_pedido and talon_ped:
                    print(f"✓ Tabla RO_T_ESTADO_PEDIDOS_ECOMMERCE también actualizada para el pedido {nro_pedido}, talon {talon_ped}")
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
