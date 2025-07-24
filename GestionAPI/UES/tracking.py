import requests
from requests.auth import HTTPBasicAuth
import json

# # Configuración
# BASE_URL = "https://sge.ues.com.uy:9443/ues_commerce/get_eventos_tracking"
# CREDENTIALS = ('tu_usuario', 'tu_contraseña')  # Reemplaza con tus credenciales

# # Función para obtener eventos de tracking
# def obtener_eventos_tracking(data):
#     headers = {
#         'Content-Type': 'application/json',
#         'User-Agent': 'Mozilla/5.0'
#     }
#     response = requests.post(BASE_URL, auth=HTTPBasicAuth(*CREDENTIALS), headers=headers, data=json.dumps(data))
#     return response.json()

# # Ejemplo de datos para obtener eventos de tracking
# tracking_data = {
#     "Cliente": "47756",
#     "Tocken": "Gene71c0-47756",
#     "ref_pedido": "1485400503746-01",
# }

# # Obtener eventos de tracking
# respuesta_eventos = obtener_eventos_tracking(tracking_data)
# print("Respuesta de eventos de tracking:", respuesta_eventos)



reqUrl = "https://sge.ues.com.uy:9443/ues_commerce/get_eventos_tracking"

headersList = {
 "Content-Type": "application/json",
 "User-Agent": "Mozilla/5.0" 
}

payload = json.dumps({
  "Cliente": "47756",
  "Tocken": "Gene71c0-47756",
  "ref_pedido": "1485400503746-01"
})

response = requests.request("GET", reqUrl, data=payload,  headers=headersList)

print(response.text)
