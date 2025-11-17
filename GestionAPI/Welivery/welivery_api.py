import asyncio
import aiohttp
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger('welivery_api')

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
                        
                        logger.debug(f"Request to {url} with params: {params}")
                        logger.debug(f"Response status: {response.status}")
                        
                        if response.status == 200:
                            data = await response.json()
                            logger.debug(f"Response data: {data}")
                            return data
                        elif response.status == 401:
                            logger.error("Error de autenticación: credenciales inválidas")
                            return None
                        elif response.status == 404:
                            logger.warning(f"Número de seguimiento no encontrado: {params.get('Id', 'N/A')}")
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
        endpoint = ""
        params = {"Id": tracking_number}
        
        logger.info(f"Consultando estado de envío para: {tracking_number}")
        
        response = await self._make_request("GET", endpoint, params)
        
        if response and response.get("status") == "OK":
            data = response.get("data", {})
            status = data.get("Status", "")
            logger.info(f"Estado obtenido para {tracking_number}: {status}")
            return data
        else:
            logger.warning(f"No se pudo obtener estado para {tracking_number}")
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
        
        logger.info(f"Consultando estado para {len(tracking_numbers)} envíos")
        
        # Crear tareas asíncronas para cada consulta
        tasks = []
        for tracking_number in tracking_numbers:
            task = asyncio.create_task(self.get_delivery_status(tracking_number))
            tasks.append((tracking_number, task))
        
        # Ejecutar todas las consultas concurrentemente
        results = {}
        completed_tasks = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
        
        for (tracking_number, _), result in zip(tasks, completed_tasks):
            if isinstance(result, Exception):
                logger.error(f"Error al consultar {tracking_number}: {result}")
                results[tracking_number] = None
            else:
                results[tracking_number] = result
        
        logger.info(f"Consultas completadas: {len([r for r in results.values() if r is not None])}/{len(tracking_numbers)} exitosas")
        
        return results

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
            logger.info("Cliente API de Welivery cerrado")
        except Exception as e:
            logger.error(f"Error cerrando cliente Welivery: {e}")
        finally:
            # Siempre asegurar que los atributos se reinicien
            self._session = None