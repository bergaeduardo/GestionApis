#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Cliente API para HasarServicios
Maneja consultas asíncronas a las APIs de conteo de personas de HasarServicios
"""

import asyncio
import aiohttp
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger('hasar_conteo')

class HasarAPIClient:
    """
    Cliente API asíncrono para interactuar con las APIs de HasarServicios.
    Maneja autenticación con Bearer token y consultas de datos de conteo de personas.
    """
    
    def __init__(self):
        """
        Inicializa el cliente API de HasarServicios.
        Las URLs y tokens se pasan dinámicamente en cada llamada desde la configuración de BD.
        """
        self._session = None
    
    async def _get_session(self):
        """
        Obtiene o crea una sesión HTTP reutilizable con configuración optimizada.
        
        Returns:
            aiohttp.ClientSession: Sesión HTTP configurada
        """
        if not self._session or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            # Límites de conexión para prevenir saturación
            connector = aiohttp.TCPConnector(limit=50, limit_per_host=10)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector
            )
        return self._session
    
    async def obtener_datos(self, url: str, token: str, max_retries: int = 3) -> Optional[Dict[str, Any]]:
        """
        Obtiene datos de una API de HasarServicios con reintentos.
        
        Args:
            url (str): URL completa del endpoint de API
            token (str): Bearer token para autenticación
            max_retries (int): Número máximo de reintentos en caso de error (default: 3)
            
        Returns:
            Dict[str, Any]: Respuesta de la API con estructura:
                {
                    "success": true,
                    "report": {
                        "name": "API - Ingreso por día",
                        "data": {
                            "series": [{
                                "data": [{"key": "06-04-2026", "value": 324}, ...]
                            }]
                        }
                    }
                }
            None en caso de error o fallo de validación
        """
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        for intento in range(max_retries):
            try:
                session = await self._get_session()
                
                async with session.get(url, headers=headers) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        
                        # Validar estructura de respuesta
                        if not self._validar_respuesta(data):
                            logger.error(f"Respuesta inválida de API: {url}")
                            return None
                        
                        return data
                    
                    elif response.status == 401:
                        logger.error(f"Error de autenticación (401) para {url}: token inválido")
                        return None  # No reintentar en errores de autenticación
                    
                    elif response.status == 404:
                        logger.error(f"Endpoint no encontrado (404): {url}")
                        return None  # No reintentar en endpoints no encontrados
                    
                    elif response.status >= 500:
                        # Error del servidor, reintentar
                        if intento < max_retries - 1:
                            await asyncio.sleep(2 ** intento)  # Backoff exponencial
                            continue
                        else:
                            logger.error(f"Error del servidor ({response.status}) después de {max_retries} intentos: {url}")
                            return None
                    
                    else:
                        text = await response.text()
                        logger.error(f"Error HTTP {response.status}: {text}")
                        return None
            
            except asyncio.TimeoutError:
                if intento < max_retries - 1:
                    await asyncio.sleep(2 ** intento)
                    continue
                else:
                    logger.error(f"Timeout después de {max_retries} intentos: {url}")
                    return None
            
            except aiohttp.ClientError as e:
                if intento < max_retries - 1:
                    await asyncio.sleep(2 ** intento)
                    continue
                else:
                    logger.error(f"Error de conexión: {e}")
                    return None
            
            except Exception as e:
                logger.error(f"Error inesperado al consultar API: {e}")
                return None
        
        return None
    
    def _validar_respuesta(self, data: Dict[str, Any]) -> bool:
        """
        Valida que la respuesta de la API tenga la estructura esperada.
        
        Args:
            data (Dict): Datos JSON de la respuesta
            
        Returns:
            bool: True si la estructura es válida, False en caso contrario
        """
        try:
            # Verificar campo "success"
            if not data.get('success', False):
                logger.error(f"API retornó success=false")
                return False
            
            # Verificar estructura básica
            if 'report' not in data:
                logger.error("Falta campo 'report' en respuesta")
                return False
            
            report = data['report']
            
            if 'data' not in report:
                logger.error("Falta campo 'data' en report")
                return False
            
            if 'series' not in report['data']:
                logger.error("Falta campo 'series' en data")
                return False
            
            series = report['data']['series']
            
            if not isinstance(series, list) or len(series) == 0:
                logger.error("Campo 'series' vacío o no es lista")
                return False
            
            # Verificar que la primera serie tenga campo 'data'
            if 'data' not in series[0]:
                logger.error("Falta campo 'data' en primera serie")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error al validar respuesta: {e}")
            return False
    
    def extraer_datos(self, respuesta: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extrae los datos de conteo de la respuesta de la API.
        
        Args:
            respuesta (Dict): Respuesta completa de la API
            
        Returns:
            List[Dict]: Lista de diccionarios con formato:
                [{"fecha": "06-04-2026", "valor": 324}, ...]
        """
        try:
            series_data = respuesta['report']['data']['series'][0]['data']
            
            datos_extraidos = []
            for item in series_data:
                datos_extraidos.append({
                    'fecha': item['key'],
                    'valor': item['value']
                })
            
            return datos_extraidos
            
        except Exception as e:
            logger.error(f"Error al extraer datos de respuesta: {e}")
            return []
    
    def parsear_fecha(self, fecha_str: str) -> Optional[datetime]:
        """
        Parsea una fecha en formato "dd-mm-yyyy" a objeto datetime.
        
        Args:
            fecha_str (str): Fecha en formato "dd-mm-yyyy" (ej: "06-04-2026")
            
        Returns:
            datetime: Objeto datetime o None si hay error
        """
        try:
            return datetime.strptime(fecha_str, "%d-%m-%Y")
        except ValueError as e:
            logger.error(f"Error al parsear fecha '{fecha_str}': {e}")
            return None
    
    async def close(self):
        """
        Cierra la sesión HTTP de forma explícita.
        Debe llamarse al finalizar el uso del cliente.
        """
        if self._session and not self._session.closed:
            await self._session.close()
