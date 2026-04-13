#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script principal de sincronización para HasarServicios
Obtiene datos de conteo de personas (ingresos y merodeo) desde APIs de HasarServicios
y los sincroniza con tablas SQL Server en múltiples bases de datos.
"""

import sys
import os

# Obtiene la ruta del directorio padre (la raíz del proyecto)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
# Añade la ruta de la raíz del proyecto a sys.path
sys.path.insert(0, project_root)

import asyncio
from datetime import datetime, timedelta
from collections import defaultdict
from typing import List, Dict, Any

from GestionAPI.common.logger_config import setup_logger
from GestionAPI.HasarServicios.db_operations_hasar import HasarDB
from GestionAPI.HasarServicios.api_hasar import HasarAPIClient

# Configurar logger específico para este módulo
logger = setup_logger('hasar_conteo', log_path=os.path.join(os.path.dirname(__file__), 'logs', 'app.log'))


async def procesar_sucursal(
    api_client: HasarAPIClient, 
    db: HasarDB, 
    nro_sucursal: int, 
    configs_sucursal: List[Dict[str, Any]],
    fecha_inicio: datetime,
    fecha_fin: datetime
) -> Dict[str, Any]:
    """
    Procesa todas las APIs de una sucursal de forma concurrente.
    
    Args:
        api_client: Cliente API configurado
        db: Instancia de HasarDB
        nro_sucursal: Número de sucursal a procesar
        configs_sucursal: Lista de configuraciones de APIs para esta sucursal
        fecha_inicio: Fecha inicial del rango a sincronizar
        fecha_fin: Fecha final del rango a sincronizar
        
    Returns:
        Dict con estadísticas del procesamiento
    """
    estadisticas = {
        'sucursal': nro_sucursal,
        'apis_procesadas': 0,
        'apis_fallidas': 0,
        'registros_guardados': 0,
        'errores': []
    }
    
    # Determinar la base de datos destino (todas las APIs de la sucursal usan la misma BD)
    database_name = configs_sucursal[0]['DATA_BASE']
    
    # Llamar todas las APIs de la sucursal en paralelo
    tareas_api = []
    for config in configs_sucursal:
        tarea = api_client.obtener_datos(config['API'], config['Token'])
        tareas_api.append((config['NOMBRE_DASHBOARD'], tarea))
    
    # Esperar a que todas las APIs respondan
    resultados_apis = {}
    for nombre_dashboard, tarea in tareas_api:
        try:
            respuesta = await tarea
            if respuesta:
                resultados_apis[nombre_dashboard] = respuesta
                estadisticas['apis_procesadas'] += 1
            else:
                estadisticas['apis_fallidas'] += 1
                estadisticas['errores'].append(f"API {nombre_dashboard}: sin datos")
        except Exception as e:
            logger.error(f"Error al procesar API '{nombre_dashboard}' de sucursal {nro_sucursal}: {e}")
            estadisticas['apis_fallidas'] += 1
            estadisticas['errores'].append(f"API {nombre_dashboard}: {str(e)}")
    
    # Si no se obtuvieron datos de ninguna API, terminar
    if not resultados_apis:
        return estadisticas
    
    # Combinar datos de ambas APIs (Ingreso y Merodeo) por fecha
    datos_por_fecha = defaultdict(lambda: {'ingresos': None, 'merodeo': None})
    
    for nombre_dashboard, respuesta in resultados_apis.items():
        datos_extraidos = api_client.extraer_datos(respuesta)
        
        es_ingreso = 'ingreso' in nombre_dashboard.lower()
        es_merodeo = 'merodeo' in nombre_dashboard.lower()
        
        for item in datos_extraidos:
            fecha_obj = api_client.parsear_fecha(item['fecha'])
            
            if not fecha_obj:
                continue
            
            # Filtrar por rango de fechas solicitado
            if not (fecha_inicio <= fecha_obj <= fecha_fin):
                continue
            
            fecha_key = fecha_obj.date()
            
            if es_ingreso:
                datos_por_fecha[fecha_key]['ingresos'] = item['valor']
            elif es_merodeo:
                datos_por_fecha[fecha_key]['merodeo'] = item['valor']
    
    # Guardar datos combinados en la base de datos
    for fecha, valores in datos_por_fecha.items():
        try:
            exito = db.upsert_ingresos(
                database_name=database_name,
                fecha=fecha,
                nro_sucurs=nro_sucursal,
                ingresos=valores['ingresos'],
                merodeo=valores['merodeo']
            )
            
            if exito:
                estadisticas['registros_guardados'] += 1
                
        except Exception as e:
            logger.error(f"Error al guardar datos de sucursal {nro_sucursal}, fecha {fecha}: {e}")
            estadisticas['errores'].append(f"Fecha {fecha}: {str(e)}")
    
    return estadisticas


async def main():
    """
    Función principal de sincronización.
    Procesa todas las sucursales activas en paralelo.
    """
    logger.info("=" * 80)
    logger.info("SINCRONIZACIÓN HASARSERVICIOS - CONTEO DE PERSONAS")
    logger.info("=" * 80)
    
    inicio_proceso = datetime.now()
    
    try:
        # Inicializar componentes
        db = HasarDB()
        api_client = HasarAPIClient()
        
        # Obtener estadísticas de configuración
        stats_config = db.obtener_estadisticas_config()
        
        # Obtener configuración de sucursales activas
        configuraciones = db.obtener_configuracion_sucursales()
        
        if not configuraciones:
            logger.error("No hay sucursales activas configuradas")
            return
        
        # Calcular rango de fechas: últimos 5 días excluyendo el día actual
        fecha_fin = datetime.now().date() - timedelta(days=1)  # Ayer
        fecha_inicio = fecha_fin - timedelta(days=4)  # 5 días atrás desde ayer
        
        # Agrupar configuraciones por sucursal
        configs_por_sucursal = defaultdict(list)
        for config in configuraciones:
            configs_por_sucursal[config['NUMERO_SUCURSAL']].append(config)
        
        # Procesar todas las sucursales en paralelo
        tareas_sucursales = []
        for nro_sucursal, configs in configs_por_sucursal.items():
            tarea = procesar_sucursal(
                api_client=api_client,
                db=db,
                nro_sucursal=nro_sucursal,
                configs_sucursal=configs,
                fecha_inicio=datetime.combine(fecha_inicio, datetime.min.time()),
                fecha_fin=datetime.combine(fecha_fin, datetime.max.time())
            )
            tareas_sucursales.append(tarea)
        
        # Esperar a que todas las sucursales se procesen
        resultados = await asyncio.gather(*tareas_sucursales, return_exceptions=True)
        
        # Consolidar estadísticas
        total_apis_procesadas = 0
        total_apis_fallidas = 0
        total_registros_guardados = 0
        sucursales_exitosas = 0
        sucursales_con_errores = 0
        
        for resultado in resultados:
            if isinstance(resultado, Exception):
                logger.error(f"Error en procesamiento de sucursal: {resultado}")
                sucursales_con_errores += 1
            elif isinstance(resultado, dict):
                total_apis_procesadas += resultado.get('apis_procesadas', 0)
                total_apis_fallidas += resultado.get('apis_fallidas', 0)
                total_registros_guardados += resultado.get('registros_guardados', 0)
                
                if resultado.get('registros_guardados', 0) > 0:
                    sucursales_exitosas += 1
                if resultado.get('errores'):
                    sucursales_con_errores += 1
        
        # Cerrar sesión HTTP
        await api_client.close()
        
        # Resumen final
        duracion = datetime.now() - inicio_proceso
        logger.info("=" * 80)
        logger.info("RESUMEN")
        logger.info("=" * 80)
        logger.info(f"Sucursales procesadas: {sucursales_exitosas} | Con errores: {sucursales_con_errores}")
        logger.info(f"Registros actualizados: {total_registros_guardados}")
        logger.info(f"Duración: {duracion.total_seconds():.1f} segundos")
        logger.info("=" * 80)
        
        if total_registros_guardados > 0:
            logger.info("✓ Sincronización completada exitosamente")
        else:
            logger.warning("⚠ No se guardaron registros")
        
    except Exception as e:
        logger.error(f"Error crítico en proceso de sincronización: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    """
    Punto de entrada del script.
    Ejecuta la función principal de forma asíncrona.
    """
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Sincronización interrumpida por el usuario")
    except Exception as e:
        logger.error(f"Error fatal: {e}", exc_info=True)
        sys.exit(1)
