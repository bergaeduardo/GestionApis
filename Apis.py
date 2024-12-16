import requests
import json
from credenciales import API_SOLAR

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

    # payload_ventas = {
    #     "IdCliente": "000040",
    #     "Comprobantes": [
    #         {
    #             "Fecha": "26-03-2021",
    #             "Hora": "18:15:00",
    #             "IdComprobante": "02",
    #             "PtoVenta": "0001",
    #             "NroComprobante": "00000356",
    #             "Detalles": [
    #                 {
    #                     "DescripcionItem": "Jean varon talle 44",
    #                     "Cantidad": "1",
    #                     "ImporteNeto": "2000.00",
    #                     "Importelmpuestos": "420.00"
    #                 },
    #                 {
    #                     "DescripcionItem": "Medias mujer largas",
    #                     "Cantidad": "3",
    #                     "ImporteNeto": "1500.00",
    #                     "Importelmpuestos": "315.00"
    #                 }
    #             ],
    #             "Pagos": [
    #                 {
    #                     "MedioPago": "EFECTIVO",
    #                     "Importe": "4235.00"
    #                 }
    #             ]
    #         }
    #     ]
    # }

    # Realizar la solicitud de envío de ventas
    response_ventas = requests.post(url_ventas, headers=headers_ventas, data=json.dumps(payload_ventas))

    if response_ventas.status_code == 201:
        print("Ventas informadas correctamente:", response_ventas.text)
        return True
    else:
        print("Error al informar ventas, código de estado:", response_ventas.status_code, response_ventas.text)
        return False

# # # obtener token
# token = obtenerToken_Solar()
# # # print('Mytoken: ', token)

# # # informar ventas
# ventas = {
#       "IdCliente":"000040",
#       "Comprobantes":[
#          {
#             "Fecha":"28-11-2024",
#             "Hora":"12:17:00",
#             "IdComprobante":"006",
#             "PtoVenta":"0001",
#             "NroComprobante":"021500030562",
#             "Detalles":[
#                {
#                   "DescripcionItem":"XT4SDC29C0212",
#                   "Cantidad":"1",
#                   "ImporteNeto":"70991.73",
#                   "ImporteImpuestos":"14908.27"
#                }
#             ],
#             "Pagos":[
#                {
#                   "MedioPago":"DEBITO",
#                   "Importe":"85900.00"
#                }
#             ]
#          }
#       ]
#    }

# informarVentas_Solar(token, ventas)