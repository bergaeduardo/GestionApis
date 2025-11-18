import asyncio
import aiohttp
import logging
import os
from typing import Optional, Dict, Any

# Usar el logger configurado por el módulo padre
logger = logging.getLogger('welivery_sync')

class WeliveryAPI:
    """
    Cliente API para interactuar con la API de Welivery de forma asíncrona.
    Maneja autenticación básica y consultas de estado de envío.
    """
    
    def __init__(self, base_url: str, user: str, password: str):
        """
        Inicializa el cliente API de Welivery.
        
        Args:
            base_url (str): URL base de la API de Welivery
            user (str): Usuario para autenticación
            password (str): Contraseña para autenticación
        """
        self.base_url = base_url
        self.user = user
        self.password = password
        self._session = None

    async def _get_session(self):
        """Obtiene o crea una sesión HTTP reutilizable."""
        if not hasattr(self, '_session') or self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                auth=aiohttp.BasicAuth(self.user, self.password)
            )
        return self._session

    async def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """
        Realiza una solicitud a la API de Welivery de forma asíncrona.
        
        Args:
            method (str): Método HTTP (GET, POST, etc.)
            endpoint (str): Endpoint de la API
            params (Dict, optional): Parámetros para la consulta
            
        Returns:
            Dict[str, Any]: Respuesta de la API o None en caso de error
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            session = await self._get_session()
            
            async with session.request(
                method=method,
                url=url,
                params=params
            ) as response:
                        
                        if response.status == 200:
                            data = await response.json()
                            return data
                        elif response.status == 401:
                            logger.error("Error de autenticación: credenciales inválidas")
                            return None
                        elif response.status == 404:
                            # No loguear, es normal que algunos envíos no existan
                            return None
                        elif response.status == 400:
                            # No loguear, es normal que algunos envíos no tengan acceso
                            return None
                        else:
                            text = await response.text()
                            logger.error(f"Error {response.status}: {text}")
                            return None
                            
        except asyncio.TimeoutError:
            logger.error(f"Timeout al consultar la API de Welivery: {url}")
            return None
        except aiohttp.ClientError as e:
            logger.error(f"Error de cliente al consultar Welivery: {e}")
            return None
        except Exception as e:
            logger.error(f"Error inesperado al consultar Welivery: {e}")
            return None

    async def get_delivery_status(self, tracking_number: str) -> Optional[Dict[str, Any]]:
        """
        Consulta el estado de un envío por número de seguimiento.
        
        Args:
            tracking_number (str): Número de seguimiento del envío
            
        Returns:
            Dict[str, Any]: Información del estado del envío o None en caso de error
        """
        endpoint = "/api/delivery_status"
        params = {"Id": tracking_number}
        
        response = await self._make_request("GET", endpoint, params)
        
        if response and response.get("status") in ["OK", "Ok"]:
            data = response.get("data", {})
            return data
        else:
            return None

    async def get_multiple_delivery_status(self, tracking_numbers: list) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        Consulta el estado de múltiples envíos de forma asíncrona.
        
        Args:
            tracking_numbers (list): Lista de números de seguimiento
            
        Returns:
            Dict[str, Optional[Dict[str, Any]]]: Diccionario con el estado de cada envío
        """
        if not tracking_numbers:
            return {}
        
        # Crear tareas asíncronas para cada consulta
        tasks = []
        for tracking_number in tracking_numbers:
            task = asyncio.create_task(self.get_delivery_status(tracking_number))
            tasks.append((tracking_number, task))
        
        # Ejecutar todas las consultas concurrentemente
        results = {}
        completed_tasks = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
        
        successful_count = 0
        for (tracking_number, _), result in zip(tasks, completed_tasks):
            if isinstance(result, Exception):
                results[tracking_number] = None
            else:
                results[tracking_number] = result
                if result is not None:
                    successful_count += 1
        
        logger.info(f"Consultas API completadas: {successful_count}/{len(tracking_numbers)} exitosas")
        
        return results

    async def get_label_url(self, tracking_number: str) -> Optional[str]:
        """
        Obtiene la URL de descarga de la etiqueta de un envío.
        
        Args:
            tracking_number (str): Número de seguimiento del envío
            
        Returns:
            Optional[str]: URL completa de la etiqueta o None en caso de error
        """
        endpoint = "/api/delivery_get"
        params = {"Id": tracking_number}
        
        try:
            response = await self._make_request("GET", endpoint, params)
            
            if response and response.get("status") in ["OK", "Ok"]:
                data = response.get("data", {})
                label_url = data.get("LabelUrl", "")
                
                if label_url:
                    # Limpiar las barras invertidas
                    label_url = label_url.replace("\\", "")
                    
                    # Concatenar con la URL base
                    full_url = f"{self.base_url}{label_url}"
                    
                    logger.info(f"URL de etiqueta obtenida para seguimiento {tracking_number}: {full_url}")
                    return full_url
                else:
                    logger.warning(f"No se encontró LabelUrl para el seguimiento {tracking_number}")
                    return None
            else:
                logger.warning(f"No se pudo obtener información de etiqueta para el seguimiento {tracking_number}")
                return None
                
        except Exception as e:
            logger.error(f"Error al obtener URL de etiqueta para {tracking_number}: {e}")
            return None

    async def download_label(self, tracking_number: str, file_path: str) -> bool:
        """
        Descarga la etiqueta de un envío y la guarda en un archivo.
        
        Args:
            tracking_number (str): Número de seguimiento del envío
            file_path (str): Ruta donde guardar el archivo PDF
            
        Returns:
            bool: True si la descarga fue exitosa, False en caso contrario
        """
        try:
            # Obtener la URL de la etiqueta
            label_url = await self.get_label_url(tracking_number)
            
            if not label_url:
                logger.error(f"No se pudo obtener la URL de etiqueta para {tracking_number}")
                return False
            
            # Descargar el archivo PDF
            session = await self._get_session()
            
            async with session.get(label_url) as response:
                if response.status == 200:
                    content = await response.read()
                    
                    # Guardar el archivo
                    with open(file_path, 'wb') as f:
                        f.write(content)
                    
                    logger.info(f"Etiqueta descargada exitosamente: {file_path}")
                    return True
                else:
                    logger.error(f"Error al descargar etiqueta: HTTP {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error al descargar etiqueta para {tracking_number}: {e}")
            return False

    def map_status_to_code(self, status: str) -> tuple:
        """
        Mapea el estado de texto de Welivery a código numérico.
        
        Args:
            status (str): Estado de texto de Welivery
            
        Returns:
            tuple: (estado_texto, codigo_numerico)
        """
        status_mapping = {
            "PENDIENTE": ("PENDIENTE", 0),
            "EN CURSO": ("EN CURSO", 2),
            "NO COMPLETADO": ("NO COMPLETADO", 2),
            "COMPLETADO": ("COMPLETADO", 3),
            "CANCELADO": ("CANCELADO", 4),
            "INGRESO A DEPOSITO": ("INGRESO A DEPOSITO", 7),
            "REPETIDO": ("REPETIDO", 9),
            "PREPARADO": ("PREPARADO", 10),
            "PRIMER VISITA": ("PRIMER VISITA", 11),
            "SEGUNDA VISITA": ("SEGUNDA VISITA", 12),
            "DEBE REGRESAR": ("DEBE REGRESAR", 13),
            "ASIGNADO": ("ASIGNADO", 15),
            "REGRESADO": ("REGRESADO", 19),
            "NO RETIRADO": ("NO RETIRADO", 20),
            "RETIRADO": ("RETIRADO", 21),
            "SINIESTRO": ("SINIESTRO", 23),
            "INDEFINIDO": ("INDEFINIDO", 98),
            "SIN PROCESAR": ("SIN PROCESAR", 99)
        }
        
        return status_mapping.get(status.upper(), ("INDEFINIDO", 98))

    async def close(self):
        """
        Cierra el cliente API y libera recursos.
        """
        try:
            if hasattr(self, '_session') and self._session and not self._session.closed:
                await self._session.close()
        except Exception as e:
            logger.error(f"Error cerrando cliente Welivery: {e}")
        finally:
            # Siempre asegurar que los atributos se reinicien
            self._session = None