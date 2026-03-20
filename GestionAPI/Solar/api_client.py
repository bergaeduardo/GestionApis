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
        # Desactivar verificación SSL temporalmente para pruebas
        self.session.verify = False

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

    def informar_ventas(self, token, ventas, comprobantes_originales=None):
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
                try:
                    error_detail = response.json()
                    
                    # Procesar mensajes de Solar para mostrar de forma más clara
                    if 'Mensajes' in error_detail and isinstance(error_detail['Mensajes'], list):
                        # Agrupar mensajes únicos para evitar duplicados
                        mensajes_unicos = {}
                        comprobantes_duplicados = set()
                        
                        for msg in error_detail['Mensajes']:
                            mensaje = msg.get('mensaje', '')
                            if 'YA ESTA REGISTRADO' in mensaje:
                                # Extraer número de comprobante del mensaje
                                import re
                                # Buscar pattern: "EL COMPROBANTE FACB 0001-21500040 YA ESTA REGISTRADO"
                                match = re.search(r'COMPROBANTE\s+(FAC[AB]|NCR[AB])\s+(\d{4}-\d{8})', mensaje)
                                if match:
                                    comprobantes_duplicados.add(match.group(2))
                                else:
                                    # Fallback: buscar cualquier patrón XXXX-XXXXXXXX en el mensaje
                                    fallback_match = re.search(r'(\d{4}-\d{8})', mensaje)
                                    if fallback_match:
                                        comprobantes_duplicados.add(fallback_match.group(1))
                            
                            if mensaje not in mensajes_unicos:
                                mensajes_unicos[mensaje] = 1
                            else:
                                mensajes_unicos[mensaje] += 1
                        
                        if comprobantes_duplicados:
                            # Mostrar directamente los comprobantes originales del lote actual
                            if comprobantes_originales:
                                logger.error(f"Error al informar ventas: {response.status_code} - COMPROBANTES YA REGISTRADOS: {', '.join(comprobantes_originales)}")
                            else:
                                logger.error(f"Error al informar ventas: {response.status_code} - COMPROBANTES YA REGISTRADOS: {', '.join(comprobantes_duplicados)}")
                        
                        # Log mensajes únicos con su cantidad (solo para mensajes no repetitivos)
                        for mensaje, cantidad in mensajes_unicos.items():
                            if cantidad == 1:  # Solo mostrar mensajes únicos, no los repetitivos
                                # Convertir mensaje individual para mostrar comprobante original
                                mensaje_convertido = mensaje
                                if comprobantes_originales and 'YA ESTA REGISTRADO' in mensaje:
                                    # Para el primer comprobante original como referencia
                                    if len(comprobantes_originales) > 0:
                                        mensaje_convertido = f"EL COMPROBANTE {comprobantes_originales[0]} YA ESTA REGISTRADO"
                                logger.warning(f"Error detalle: {mensaje_convertido}")
                    else:
                        logger.error(f"Error al informar ventas: {response.status_code} - {error_detail}")
                        
                except Exception as e:
                    error_detail = response.text
                    logger.error(f"Error al informar ventas: {response.status_code} - {error_detail}")
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Error en la solicitud de informar ventas: {str(e)}")
            return False