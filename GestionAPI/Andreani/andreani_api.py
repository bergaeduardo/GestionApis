import requests
from requests.auth import HTTPBasicAuth
# from credenciales import DATA_QA # Lo importamos donde lo usamos


class AndreaniAPI:
    def __init__(self, base_url, user, password):
        self.base_url = base_url
        self.user = user
        self.password = password
        self.token = self._get_auth_token()

        if not self.token:
            raise ValueError("No se pudo obtener el token de autorización.")
    
    def _get_auth_token(self):
        """Obtiene el token de autenticación."""
        login_url = f"{self.base_url}/login"
        response = requests.get(login_url, auth=HTTPBasicAuth(self.user, self.password))

        if response.status_code == 200:
            return response.headers.get('x-authorization-token')
        else:
            print(f"Error {response.status_code}: {response.text}")
            return None
    
    def _make_request(self, method, url, headers=None, params=None, json=None):
        """Realiza una solicitud a la API y maneja los errores."""
        headers = headers or {}
        if self.token:
             headers['x-authorization-token'] = self.token
        
        try:
            response = requests.request(method, url, headers=headers, params=params, json=json)
            response.raise_for_status()  # Lanza una excepción para errores HTTP
            
            if response.status_code == 204:
                return None  # No hay contenido en la respuesta
            
            try:
                return response.json()
            except requests.exceptions.JSONDecodeError:
                return response.content
        except requests.exceptions.RequestException as e:
            print(f"Error en la solicitud: {e}")
            if response:
                print(f"Detalles: {response.status_code} - {response.text}")
            return None
        
    def buscar_sucursales(self, parametros):
        """Busca sucursales según los parámetros proporcionados."""
        url = f"{self.base_url}/v2/sucursales"
        return self._make_request("GET", url, params=parametros)
    
    def obtener_cotizacion(self, parametros):
        """Obtiene la cotización de envío."""
        url = f"{self.base_url}/v1/tarifas"
        return self._make_request("GET", url, params=parametros)
    
    def crear_orden_envio(self, data):
        """Crea una orden de envío."""
        url = f'{self.base_url}/v2/ordenes-de-envio'
        
        response = self._make_request("POST", url, json=data)
        
        if response:
            resultado = {}
            
            if response.get('bultos') and response['bultos'][0].get("numeroDeEnvio"):
              resultado["numeroEnvio"] = response["bultos"][0]["numeroDeEnvio"]
            if response.get('agrupadorDeBultos'):
              resultado["numeroAgrupador"] = response["agrupadorDeBultos"]
            
            if response.get("sucursalDeDistribucion"):
                sucursalDistribucion = response["sucursalDeDistribucion"].get("descripcion", "N/A")
            else:
                sucursalDistribucion = 'N/A'
            
            etiquetas = response.get('bultos')[0].get("linking") if response.get('bultos') and response['bultos'][0].get("linking") else 'N/A'

            print("Orden de envío creada con éxito.")
            print("Número de envío:", resultado.get("numeroEnvio", "N/A"))
            print("Número de agrupador de bultos:", resultado.get("numeroAgrupador", "N/A"))
            print("Sucursal de distribución:", sucursalDistribucion)
           
            return resultado
    
    def consultar_estado_orden(self, numeroEnvio):
        """Consulta el estado de una orden de envío."""
        url = f"{self.base_url}/v2/ordenes-de-envio/{numeroEnvio}"
        response = self._make_request("GET", url)
        
        if response:
          estado = response.get("estado")
          return estado
        else:
            return None
    
    def obtener_etiquetas(self, numeroAgrupador):
        """Obtiene las etiquetas de envío."""
        url = f"{self.base_url}/v2/ordenes-de-envio/{numeroAgrupador}/etiquetas"
        return self._make_request("GET", url)
    
    def consultar_estado_envio(self, numeroEnvio):
        """Consulta el estado de un envío."""
        url = f'{self.base_url}/v2/envios/{numeroEnvio}'
        return self._make_request("GET", url)

    def obtener_envios(self, params):
        """Obtiene envíos según los parámetros."""
        url = f'{self.base_url}/v2/envios'
        return self._make_request("GET", url, params=params)
    
    def obtener_multimedia_envio(self, numeroEnvio):
        """Obtiene información multimedia del envío"""
        url = f'{self.base_url}/v1/envios/{numeroEnvio}/multimedia'
        return self._make_request("GET", url)
    
    def obtener_remito_digitalizado(self, numeroEnvio):
        """Obtiene el remito digitalizado del envío"""
        url = f'{self.base_url}/v1/envios/{numeroEnvio}/remito'
        return self._make_request("GET", url)
        
    def obtener_trazas_envio(self, numeroEnvio):
        """Obtiene las trazas del envío"""
        url = f'{self.base_url}/v2/envios/{numeroEnvio}/trazas'
        return self._make_request("GET", url)
    
    def obtener_localidades_por_codigo_postal(self, codigo_postal):
        """Obtiene localidades filtradas por código postal."""
        url = f"{self.base_url}/v1/localidades"
        response = self._make_request("GET", url)

        if response:
            localidades_filtradas = [
                localidad
                for localidad in response
                if codigo_postal in localidad["codigosPostales"]
            ]
            return localidades_filtradas
        else:
             return []