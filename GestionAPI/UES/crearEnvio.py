import requests
from requests.auth import HTTPBasicAuth
import json

# Configuración
BASE_URL = "https://sge.ues.com.uy:9443/ues_commerce"
CREDENTIALS = ('XL_EXT', 'XL_EXT_11032')  # Reemplaza con tus credenciales

# Función para crear un envío
def crear_envio(data):
    url = f"{BASE_URL}/UES_InsertEnvio"
    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.post(url, auth=HTTPBasicAuth(*CREDENTIALS), headers=headers, data=json.dumps(data))
    return response.json()

# Función para consultar el estado de una solicitud de envío
def consultar_estado_envio(tracking_number):
    url = f"{BASE_URL}/GetStatus?tracking={tracking_number}"
    response = requests.get(url, auth=HTTPBasicAuth(*CREDENTIALS))
    return response.json()

# Ejemplo de datos para crear un envío
envio_data = {
    "Cliente": "47756",
    "Tocken": "Gene71c0-47756",
    "CentroCliente": "F",
    "NroPedido": "B0021500031051",
    "TP": "",
    "Entrega": "TEST54321",
    "Transporte": "",
    "FechaCrea": "2022-04-15",
    "PExp": "",
    "TipoMaterial": "",
    "TipoServicio": "12176",
    "PickUp": "",
    "Cbtos": "1",
    "CantTotal": "1",
    "PesoTotal": "2.3",
    "UMP": "Kg",
    "ValorMonetario": "600",
    "FecEntrega": "",
    "VentanaHoraria": "",
    "Destinatario": "JOHN DOE",
    "Calle": "CALLE NAPO 1138, POR EL COLISEO CERRADO DE IQUITOS",
    "Nro": "1138",
    "BIS": "",
    "NroDeApto": "",
    "BarrioLocalidad": "Colonia Palma",
    "Departamento": "Artigas",
    "Localidad": "",
    "CodPo": "55000",
    "Latitud": "-30.5802926",
    "Longitud": "-57.6815647",
    "Soc": "",
    "Observaciones": "No hay",
    "TelefonoContacto": "099xxxxxxx",
    "EmailRecibe": "jdoe@email.com",
    "MontoCobrar": "",
    "Comentarios": "CreacionTestingUES",
    "Cantidad": "",
    "UM": "",
    "Guia": "json",
    "Zpl": "1",
    "levante": {
        "levante_direccion_id": "",
        "levante_tipo": 2,
        "levante_fecha": "2024-06-21",
        "levante_calle": "Burgues",
        "levante_numero_puerta": "2825",
        "levante_departamento": "Montevideo",
        "levante_localidad": "Reducto",
        "levante_latitud": "",
        "levante_longitud": "",
        "levante_observaciones": "Ejemplo de observación"
    }
}

# Crear un envío
respuesta_creacion = crear_envio(envio_data)
print("Respuesta de creación de envío:", respuesta_creacion)

# Consultar el estado de la solicitud de envío
if 'trackingNumber' in respuesta_creacion:
    tracking_number = respuesta_creacion['trackingNumber']
    respuesta_consulta = consultar_estado_envio(tracking_number)
    print("Respuesta de consulta de estado de envío:", respuesta_consulta)
else:
    print("No se pudo obtener el trackingNumber de la respuesta de creación de envío.")
