import requests
from requests.auth import HTTPBasicAuth
from credenciales import DATA_QA


#----------------------------------------------------------------------------------GENERAR EL TOKEN

# Configuración
base_url_qa = DATA_QA["url"] # NO MODIFICAR (es la URL de QA)
user = DATA_QA["user"] # Mantener en un lugar seguro
passw = DATA_QA["passw"] # Mantener en un lugar seguro

#autenticacion:
def get_auth_token(base_url, username, password):
    login_url = f"{base_url}/login"
    response = requests.get(login_url, auth=HTTPBasicAuth(username, password))
    
    # Verificar si la petición fue exitosa
    if response.status_code == 200:
        return response.headers.get('x-authorization-token')
    else:
        print(f"Error {response.status_code}: {response.text}")
        return None


token = get_auth_token(base_url_qa, user, passw)
if token:
    print("Token obtenido")
else:
    print("No se obtuvo el token")

#----------------------------------------------------------------------------------------SUCURSALES
# comprador consulta sucursales disponibles para retirar

def buscar_sucursales(base_url, parametros):

    response = requests.get(f"{base_url}/v2/sucursales", params=parametros)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error {response.status_code}: {response.text}")
        return None


parametros_sucursales = {
    'localidad': 'Cordoba'
}

# sucursales = buscar_sucursales(base_url_qa, parametros_sucursales)

# if sucursales:
#     print("Cotización obtenida:", sucursales)


respuesta_esperada = {
        "id": 10055,
        "codigo": "SFN",
        "numero": "55",
        "descripcion": "SANTA FE (CENTRO)",
        "canal": "B2C",
        "direccion": {
            "calle": "25 de Mayo",
            "numero": "3340",
            "provincia": "Santa Fe",
            "localidad": "Santa Fe",
            "region": "Litoral",
            "pais": "Argentina",
            "codigoPostal": "3000"
        },
        "coordenadas": {
            "latitud": "-31.637650",
            "longitud": "-60.703000"
        },
        "horarioDeAtencion": "Lunes a Viernes de 08:00 a 18:00 - Sábados de 08:00 a 13:00",
        "datosAdicionales": {
            "seHaceAtencionAlCliente": True,
            "conBuzonInteligente": False,
            "tipo": "SUCURSAL"
        },
        "telefonos": [
            "0810-122-1111"
        ],
        "codigosPostalesAtendidos": [
            "2469",
            "3000",
            "3001",
            "3002",
            "3003",
            "3004",
            "3005",
            "3006",
            "3007",
            "3008",
            "3014",
            "3018",
            "3020",
            "3021",
        ]
    }


#-----------------------------------------------------------------------------------------COTIZADOR
# comprador cotiza el envio del paquete

#llamada a la api andreani: cotizacion
def obtener_cotizacion(token, base_url, parametros):
    headers = {
        'x-authorization-token': token,
    }
    
    response = requests.get(f"{base_url}/v1/tarifas", headers=headers, params=parametros)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error {response.status_code}: {response.text}")
        return None


parametros_cotizacion = {
    'cpDestino': '3432',    # Reemplaza con el valor real
    'contrato': '400021942',           # Reemplaza con el valor real
    'cliente': '0012008402',             # Reemplaza con el valor real
    'bultos[0][volumen]': '1000',   # Reemplaza con el valor real en cm3
}

# cotizacion = obtener_cotizacion(token, base_url_qa, parametros_cotizacion)

# if cotizacion:
#     print("Cotización obtenida:", cotizacion)


#-----------------------------------------------------------------------DATOS PARA LA ORDEN DE ENVIO


# Define los datos para la orden de envío
data = {
    "contrato": "400021942",#o
    "idPedido": "",
    "valorACobrar": 6000.00,
    "origen": {
        "postal": {
            "codigoPostal": "1644",#o
            "calle": "Uruguay",#o
            "numero": "4415",#o
            "localidad": "Béccar",#o
            "region": "Buenos Aires",
            "pais": "Argentina",#o
            "componentesDeDireccion": [
                {
                    "meta": "",
                    "contenido": ""
                }
            ]
        }
    },
    "destino": {
        "postal": {
            "codigoPostal": "3432",#o
            "calle": "Constitución  1293",#o
            "numero": "1293",#o
            "localidad": "Bella Vista",#o
            "region": "AR-B",
            "pais": "Argentina",
            "componentesDeDireccion": [
                {
                    "meta": "",
                    "contenido": ""
                },
                {
                    "meta": "",
                    "contenido": ""
                }
            ]
        }
    },
    "remitente": {
        "nombreCompleto": "Lakers Corp",
        "email": "xlshop@xl.com.ar",
        "documentoTipo": "DNI",
        "documentoNumero": "41322399",
        "telefonos": [
            {
                "tipo": 1,
                "numero": "153715896"
            }
        ]
    },
    "destinatario": [
        {
            "nombreCompleto": "Ramiro Orozco",
            "email": "ramiro.orozco@xl.com.ar",
            "documentoTipo": "CUIT",
            "documentoNumero": "30234567890",
            "telefonos": [
                {
                    "tipo": 2,
                    "numero": "153111231"
                }
            ]
        }
    ],
    "remito": {
        "numeroRemito": "123456789012R",
    },
    "bultos": [
        {
            "kilos": 2,
            "volumenCm": 5000,
            "valorDeclaradoSinImpuestos": 1200,
            "valorDeclaradoConImpuestos": 1452,
            "referencias": [
                {
                    "meta": "detalle",
                    "contenido": "Secador de pelo"
                },
                {
                    "meta": "idCliente",
                    "contenido": "10000"
                },
                {
                    "meta": "observaciones",
                    "contenido": "color negro"
                }
            ]
        }
    ]
}




#--------------------------------------------------------------------------CREAR UNA ORDEN DE ENVIO


def crear_orden_envio(url, token, data):
    headers = {'x-authorization-token': token}
    url = f'{base_url_qa}/v2/ordenes-de-envio'
    
    # solicitud POST para crear la orden de envío:
    response = requests.post(url, json=data, headers=headers)
    
    #numero de andrani y agrupador de bultos:
    resultado = {}
    
    if response.status_code == 200:
        print("Orden de envío creada con éxito.")
        resultado["numeroEnvio"] = response.json().get("bultos")[0].get("numeroDeEnvio")
        resultado["numeroAgrupador"] = response.json().get('agrupadorDeBultos')
        sucursalDistribucion = response.json().get("sucursalDeDistribucion")["descripcion"]
        etiquetas = response.json().get("bultos")[0].get("linking")
        
        print("Número de envío:", resultado["numeroEnvio"])
        print("Número de agrupador de bultos:", resultado["numeroAgrupador"])
        print("Sucursal de distribución:", sucursalDistribucion)
        
    
    elif response.status_code == 202:
        print("La solicitud fue aceptada.")
        resultado["numeroEnvio"] = response.json().get("bultos")[0].get("numeroDeEnvio")
        resultado["numeroAgrupador"] = response.json().get('agrupadorDeBultos')
        sucursalDistribucion = response.json().get("sucursalDeDistribucion")["descripcion"]
        etiquetas = response.json().get("bultos")[0].get("linking")
        
        print("Número de envío:", resultado["numeroEnvio"])
        print("Número de agrupador:", resultado["numeroAgrupador"])
        print("Sucursal de distribución:", sucursalDistribucion)
        
    else:
        print("Error al crear la orden de envío.")
        print("Código de estado:", response.status_code)
        print("Respuesta:", response.text)
    
    return resultado


#llamo a la funcion:
resultado = crear_orden_envio(base_url_qa, token, data)

# Ahora puedes usar resultado en otras partes de tu programa
if resultado.get("numeroEnvio"):
    numeroEnvio = resultado["numeroEnvio"]

if resultado.get("numeroAgrupador"):
    numeroAgrupador = resultado["numeroAgrupador"]
    

#--------------------------------------------------------------------------------ESTADO DE UNA ORDEN


def consultar_estado_orden(numeroEnvio, token, url):

    url = f"{url}/v2/ordenes-de-envio/{numeroEnvio}"

    headers = {'x-authorization-token': token}

    # solicitud GET para consultar el estado de la orden
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        estado = data.get("estado")
        return estado
    else:
        print("Error al consultar el estado de la orden.")
        print("Código de estado:", response.status_code)
        print("Respuesta:", response.text)
        return None

#llamo a la funcion
estado = consultar_estado_orden(numeroEnvio, token, base_url_qa)

if estado:
    print(f"El estado de la orden con número de Andreani {numeroEnvio} es: {estado}")
    
#--------------------------------------------------------------------------------ETIQUETAS-ANDREANI

import requests

def obtener_etiquetas(numeroAgrupador, token, url):

    url = f"{url}/v2/ordenes-de-envio/{numeroAgrupador}/etiquetas"

    headers = {'x-authorization-token': token}

    # solicitud GET para obtener las etiquetas
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        print("Etiquetas obtenidas con éxito.")
        etiqueta = response.content  # Contenido de la etiqueta
        
        return etiqueta
    else:
        print("Error al obtener etiquetas.")
        print("Código de estado:", response.status_code)
        print("Respuesta:", response.text)



etiqueta = obtener_etiquetas(numeroAgrupador, token, base_url_qa)
# Guarda la etiqueta en un archivo local
with open("etiqueta_andreani.pdf", "wb") as etiqueta_file:
    etiqueta_file.write(etiqueta)

print("Etiqueta guardada como 'etiqueta_andreani.pdf'")


print('########################################################################################')
#----------------------------------------------------------------------------------ESTADO DEL ENVIO

def consultar_estado_envio(numeroEnvio, token, url):
   
    url = f'{url}/v2/envios/{numeroEnvio}'

    headers = {'x-authorization-token': token}

    # solicitud GET a la API:
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        print('La respuesta fue exitosa')
        
        data = response.json()
        print(data)
        
        return data

    else:
        print('Error en la petición')
        print('Código de estado: ', response.status_code)
        print('Respuesta: ', response.text)
    
    
'''respuesta_esperada = {
    'numeroDeTracking': '360000044179430',
    'contrato': '300006611',
    'ciclo': 'Distribution',
    'estado': 'Pendiente',
    'estadoId': 21,
    'fechaEstado': '2021-03-09T11:59:04',
    'sucursalDeDistribucion': {
      'nomenclatura': 'MONSERRAT',
      'descripcion': 'Monserrat',
      'id': 12
    },
    'fechaCreacion': '2021-03-10T11:18:01',
    'destino': {
      'Postal': {
        'localidad': 'C.A.B.A.',
        'pais': 'Argentina',
        'direccion': 'AV J MANUEL DE ROSAS 380',
        'codigoPostal': '1002'
      }
    },
    'remitente': {},
    'destinatario': {
      'nombreYApellido': 'Juana Gonzalez',
      'tipoYNumeroDeDocumento': 'PAS783297632',
      'eMail': 'destinatario@andreani.com'
    },
    'bultos': [
      {
        'kilos': 0.005,
        'valorDeclaradoConImpuestos': 1452,
        'IdDeProducto': '123456789',
        'volumen': 0.000005
      }
    ],
    'idDeProducto': '123456789',
    'referencias': [
      '360000044179430',
      '2',
      'B',
      '123456789'
    ]
  }'''

consultar_estado_envio(numeroEnvio, token, base_url_qa)


#-----------------------------------------------------------------------------------OBTENER UN ENVIO



url = f'https://apisqa.andreani.com/v2/envios'

headers = {
    'x-authorization-token': token
}
params = {
    "contrato": "400021942"
}

#solicitud de la api:
response = requests.get(url, headers=headers, params=params)

if response == 200:
    print('La respuesta fue exitosa')
    
    data = response.json()
    print(data)

else:
    print('Error en la peticion')
    print('Codigo de estado: ', response.status_code)
    print('Respuesta: ', response.text)

respuesta_esperada = {
    "numeroDeTracking": "360000277619810",
    "contrato": "400006968",
    "ciclo": "Ciclo de Rendición",
    "estado": "Rendido",
    "estadoId": 24,
    "fechaEstado": "2021-12-16T15:01:44",
    "servicio": "LI Retiro",
    "sucursalDeDistribucion": {},
    "fechaCreacion": "2021-11-19T16:14:26",
    "destino": {
        "Postal": {
            "localidad": "SANTA FE",
            "region": "Santa Fe",
            "pais": "Argentina",
            "direccion": "Santiago del estero piso 1 B 2917",
            "codigoPostal": "3000"
        }
    },
    "remitente": {
        "nombreYApellido": "PORTSAID"
    },
    "destinatario": {
        "nombreYApellido": "Ana Laura, Mansilla",
        "tipoYNumeroDeDocumento": "31139666",
        "eMail": "analauramansilla8@gmail.com"
    },
    "bultos": [{
        "kilos": 0.002,
        "valorDeclaradoConImpuestos": 500,
        "IdDeProducto": "dsd949216-01",
        "volumen": 0.005
    }],
    "idDeProducto": "dsd949216-01",
    "referencias": [
        "dsd949216-01",
        "360000277619810",
        "0100163640"
    ]
}





#--------------------------------------------------------------------------------ARCHIVOS MULTIMEDIA


url = f'https://apisqa.andreani.com/v1/envios/{numeroEnvio}/multimedia'

headers = {
    'x-authorization-token': token

}


#solicitud de la api:
response = requests.get(url, headers=headers)

if response == 200:
    print('La respuesta fue exitosa')
    
    data = response.json()
    print('--------------------------------------------------------------')
    print(data)
    print('--------------------------------------------------------------')

    

else:
    print('Error en la peticion')
    print('Codigo de estado: ', response.status_code)
    print('Respuesta: ', response.text)

respuesta_esperada = {
     "numeroDeEnvio": "360000036137650",
     "multimedia": [
       {
         "meta": "constanciaelectronica",
         "contenido": "link"
       }
     ]
   } 



#-------------------------------------------------------------------------------REMITO DIGITALIZADO


url = F'https://apisqa.andreani.com/v1/envios/{numeroEnvio}/remito'


headers = {
    'x-authorization-token': token

}


#solicitud de la api:
response = requests.get(url, headers=headers)

if response == 200:
    print('La respuesta fue exitosa')
    
    data = response.json()
    print('--------------------------------------------------------------')
    print(data)
    print('--------------------------------------------------------------')

    

else:
    print('Error en la peticion')
    print('Codigo de estado: ', response.status_code)
    print('Respuesta: ', response.text)


respuesta_esperada = {
    "numeroDeEnvio": "5000988946",
    "multimedia": [
        {
            "meta": "remito",
            "cotenido": "http://naogetfile/getfile/download/remito/5000988946/tif"
        }
    ]
}



#---------------------------------------------------------------------------------TRAZAS DE EL ENVIO


url = f'https://apisqa.andreani.com/v2/envios/{numeroEnvio}/trazas'

headers = {
    'x-authorization-token': token

}


#solicitud de la api:
response = requests.get(url, headers=headers)

if response == 200:
    print('La respuesta fue exitosa')
    
    data = response.json()
    print('--------------------------------------------------------------')
    print(data)
    print('--------------------------------------------------------------')

    

else:
    print('Error en la peticion')
    print('Codigo de estado: ', response.status_code)
    print('Respuesta: ', response.text)


respuesta_esperada = {
   'eventos': [
     {
       'Fecha': '2021-03-09T11:08:03',
       'Estado': 'Pendiente de ingreso',
       'EstadoId': 1,
       'Traduccion': 'ENVIO INGRESADO AL SISTEMA',
       'Sucursal': 'Sucursal Genérica',
       'SucursalId': 999,
       'Ciclo': 'Distribution'
     },
     {
       'Fecha': '2021-03-09T11:08:09',
       'Estado': 'Ingreso al circuito operativo',
       'EstadoId': 5,
       'Traduccion': 'ENVIO INGRESADO AL SISTEMA',
       'Sucursal': 'Monserrat',
       'SucursalId': 12,
       'Ciclo': 'Distribution'
     },
     {
       'Fecha': '2021-03-09T11:53:55',
       'Estado': 'En distribución',
       'EstadoId': 6,
       'Traduccion': 'ENVIO CON SALIDA A REPARTO',
       'Sucursal': 'Monserrat',
       'SucursalId': 12,
       'Ciclo': 'Distribution'
     },
     {
       'Fecha': '2021-03-09T11:59:04',
       'Estado': 'Visita', 
       'EstadoId': 11,  
       'Motivo': 'No se encuentra el titular',
       'MotivoId': 36, 
       'Traduccion': 'No se encuentra el titular',
       'Sucursal': 'Monserrat', 
       'SucursalId': 12,  
       'Ciclo': 'Distribution'
     }
   ]
}




