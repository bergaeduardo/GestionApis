import requests
import json
from GestionAPI.common.credenciales import API_SOLAR

def obtenerToken_Solar():
    reqUrl = "https://conectados.fortinmaure.com.ar/SolutionsRE_BackEnd/api/autenticacion/obtenerTokenAcceso"

    headersList = {
    "Content-Type": "application/json" 
    }

    payload = json.dumps({ 
    "usuario": API_SOLAR["usuario"], 
    "clave": API_SOLAR["clave"] 
    } )

    response = requests.request("POST", reqUrl, data=payload,  headers=headersList)
    data = json.loads(response.content.decode('utf-8-sig'))
    # print (data.get('token'))
    return data.get('token')

def informarVentas_Solar(token, ventas):
    url_ventas = "https://conectados.fortinmaure.com.ar/SolutionsRE_BackEnd/api/monitoring/informarVentas"
    headers_ventas = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload_ventas = ventas

    # Realizar la solicitud de envío de ventas
    response_ventas = requests.post(url_ventas, headers=headers_ventas, data=json.dumps(payload_ventas))

    if response_ventas.status_code == 201:
        print("Ventas informadas correctamente:", response_ventas.text)
        return True
    else:
        print("Error al informar ventas, código de estado:", response_ventas.status_code, response_ventas.text)
        return False
