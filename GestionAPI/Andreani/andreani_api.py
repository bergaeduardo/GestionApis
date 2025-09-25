import asyncio
import aiohttp
from requests.auth import HTTPBasicAuth


class AndreaniAPI:
    def __init__(self, base_url, user, password):
        self.base_url = base_url
        self.user = user
        self.password = password
        self.token = None
        self._auth_lock = asyncio.Lock() # Agregamos un Lock

    async def _ensure_token(self):
        """Asegura que el token esté disponible antes de continuar."""
        async with self._auth_lock:
            if not self.token:
                await self._get_auth_token()

    async def _get_auth_token(self):
        """Obtiene el token de autenticación de forma asíncrona."""
        login_url = f"{self.base_url}/login"
        async with aiohttp.ClientSession() as session:
            async with session.get(
                login_url, auth=aiohttp.BasicAuth(self.user, self.password)
            ) as response:
                if response.status == 200:
                    self.token = response.headers.get("x-authorization-token")
                    return self.token
                else:
                    text = await response.text()
                    print(f"Error {response.status}: {text}")
                    return None

    async def _make_request(self, method, url, headers=None, params=None, json_data=None):
        """Realiza una solicitud a la API de forma asíncrona y maneja los errores."""
        await self._ensure_token()  # Aseguramos que el token esté disponible
        headers = headers or {}
        if self.token:
            headers["x-authorization-token"] = self.token
        
        if method == "POST" and json_data is not None:
            headers["Content-Type"] = "application/json"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method, url, headers=headers, params=params, json=json_data
                ) as response:
                    if response.status >= 400:
                        error_body = await response.text()
                        print(f"Error en la solicitud a {url}: {response.status} {response.reason}. Respuesta: {error_body}")
                        return None

                    if response.status == 204:
                        return None
                    
                    content_type = response.headers.get("Content-Type", "")
                    if "application/json" in content_type:
                        return await response.json()
                    else:
                        return await response.read()
        except aiohttp.ClientError as e:
            print(f"Error de cliente AIOHTTP al intentar conectar a {url}: {e}")
            return None
        except Exception as e:
            print(f"Error no manejado en _make_request para {url}: {e}")
            return None


    async def buscar_sucursales(self, parametros):
        """Busca sucursales según los parámetros proporcionados de forma asíncrona."""
        url = f"{self.base_url}/v2/sucursales"
        return await self._make_request("GET", url, params=parametros)

    async def obtener_cotizacion(self, parametros):
        """Obtiene la cotización de envío de forma asíncrona."""
        url = f"{self.base_url}/v1/tarifas"
        return await self._make_request("GET", url, params=parametros)

    async def crear_orden_envio(self, data):
        """Crea una orden de envío de forma asíncrona."""
        url = f"{self.base_url}/v2/ordenes-de-envio"

        response = await self._make_request("POST", url, json_data=data)

        if response:
            resultado = {}
            if response.get("bultos") and response["bultos"][0].get("numeroDeEnvio"):
                resultado["numeroEnvio"] = response["bultos"][0]["numeroDeEnvio"]
            if response.get("agrupadorDeBultos"):
                resultado["numeroAgrupador"] = response["agrupadorDeBultos"]
            return resultado

    async def consultar_estado_orden(self, numeroEnvio):
        """Consulta el estado de una orden de envío de forma asíncrona."""
        url = f"{self.base_url}/v2/ordenes-de-envio/{numeroEnvio}"
        response = await self._make_request("GET", url)

        if response:
            estado = response.get("estado")
            return estado
        else:
            return None

    async def obtener_etiquetas(self, numeroAgrupador):
        """Obtiene las etiquetas de envío de forma asíncrona."""
        url = f"{self.base_url}/v2/ordenes-de-envio/{numeroAgrupador}/etiquetas"
        return await self._make_request("GET", url)

    async def consultar_estado_envio(self, numeroEnvio):
        """Consulta el estado de un envío de forma asíncrona."""
        url = f"{self.base_url}/v2/envios/{numeroEnvio}"
        return await self._make_request("GET", url)

    async def obtener_envios(self, params):
        """Obtiene envíos según los parámetros de forma asíncrona."""
        url = f"{self.base_url}/v2/envios"
        return await self._make_request("GET", url, params=params)

    async def obtener_multimedia_envio(self, numeroEnvio):
        """Obtiene información multimedia del envío de forma asíncrona."""
        url = f"{self.base_url}/v1/envios/{numeroEnvio}/multimedia"
        return await self._make_request("GET", url)

    async def obtener_remito_digitalizado(self, numeroEnvio):
        """Obtiene el remito digitalizado del envío de forma asíncrona."""
        url = f"{self.base_url}/v1/envios/{numeroEnvio}/remito"
        return await self._make_request("GET", url)

    async def obtener_trazas_envio(self, numeroEnvio):
        """Obtiene las trazas del envío de forma asíncrona."""
        url = f"{self.base_url}/v2/envios/{numeroEnvio}/trazas"
        return await self._make_request("GET", url)

    async def obtener_localidades_por_codigo_postal(self, codigo_postal):
        """Obtiene localidades filtradas por código postal de forma asíncrona."""
        url = f"{self.base_url}/v1/localidades"
        response = await self._make_request("GET", url)

        if response:
            localidades_filtradas = [
                localidad
                for localidad in response
                if codigo_postal in localidad["codigosPostales"]
            ]
            return localidades_filtradas
        else:
            return []