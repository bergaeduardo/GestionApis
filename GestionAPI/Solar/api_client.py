import requests
import json
import logging
from urllib3.exceptions import InsecureRequestWarning
import certifi

# Configurar el logger
logger = logging.getLogger('solar_sync')

# Suprimir advertencias de certificados no verificados
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

class SolarApiClient:
    def __init__(self, base_url="https://conectados.fortinmaure.com.ar/SolutionsRE_BackEnd/api"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.verify = certifi.where()

    def obtener_token(self, credentials):
        try:
            url = f"{self.base_url}/autenticacion/obtenerTokenAcceso"
            headers = {"Content-Type": "application/json"}
            payload = {
                "usuario": credentials["usuario"],
                "clave": credentials["clave"]
            }

            response = self.session.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            token = data.get('token')
            
            if token:
                logger.info("Token obtenido exitosamente")
                return token
            else:
                logger.error("No se pudo obtener el token de acceso")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Error en la solicitud de token: {str(e)}")
            return None

    def informar_ventas(self, token, ventas):
        try:
            url = f"{self.base_url}/monitoring/informarVentas"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }

            response = self.session.post(url, json=ventas, headers=headers)
            
            if response.status_code == 201:
                logger.info("Ventas informadas exitosamente")
                return True
            else:
                logger.error(f"Error al informar ventas: {response.status_code} - {response.text}")
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Error en la solicitud de informar ventas: {str(e)}")
            return False