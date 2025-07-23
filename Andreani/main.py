from andreani_api import AndreaniAPI
from config.credenciales import DATA_QA  # Asegúrate de tener este archivo

if __name__ == '__main__':
    # Configuración de credenciales:
    base_url_qa = DATA_QA["url"]
    user = DATA_QA["user"]
    password = DATA_QA["passw"]
    
    # Inicialización de la API:
    try:
        api = AndreaniAPI(base_url_qa, user, password)
        print("Conexión exitosa a la API de Andreani.")
    except ValueError as e:
        print(f"Error al inicializar la API: {e}")
        exit()

    # # Ejemplo de uso:
    
    # # 1. Buscar Sucursales
    # parametros_sucursales = {'localidad': 'Cordoba'}
    # sucursales = api.buscar_sucursales(parametros_sucursales)
    # if sucursales:
    #     print("\nSucursales encontradas:", sucursales)
    
    # # 2. Obtener Cotización
    # parametros_cotizacion = {
    #     'cpDestino': '3432',
    #     'contrato': '400021942',
    #     'cliente': '0012008402',
    #     'bultos[0][volumen]': '1000',
    # }
    # cotizacion = api.obtener_cotizacion(parametros_cotizacion)
    # if cotizacion:
    #   print("\nCotización obtenida:", cotizacion)
    
    # # 3. Crear Orden de Envío
    # data = {
    #     "contrato": "400021942",
    #     "idPedido": "",
    #     "valorACobrar": 6000.00,
    #     "origen": {
    #         "postal": {
    #             "codigoPostal": "1644",
    #             "calle": "Uruguay",
    #             "numero": "4415",
    #             "localidad": "Béccar",
    #             "region": "Buenos Aires",
    #             "pais": "Argentina",
    #             "componentesDeDireccion": [
    #                 {"meta": "", "contenido": ""}
    #             ]
    #         }
    #     },
    #     "destino": {
    #         "postal": {
    #             "codigoPostal": "3432",
    #             "calle": "Constitución  1293",
    #             "numero": "1293",
    #             "localidad": "Bella Vista",
    #             "region": "AR-B",
    #             "pais": "Argentina",
    #             "componentesDeDireccion": [
    #                 {"meta": "", "contenido": ""},
    #                 {"meta": "", "contenido": ""}
    #             ]
    #         }
    #     },
    #     "remitente": {
    #         "nombreCompleto": "Lakers Corp",
    #         "email": "xlshop@xl.com.ar",
    #         "documentoTipo": "DNI",
    #         "documentoNumero": "41322399",
    #         "telefonos": [{"tipo": 1, "numero": "153715896"}]
    #     },
    #     "destinatario": [
    #         {
    #             "nombreCompleto": "Ramiro Orozco",
    #             "email": "ramiro.orozco@xl.com.ar",
    #             "documentoTipo": "CUIT",
    #             "documentoNumero": "30234567890",
    #             "telefonos": [{"tipo": 2, "numero": "153111231"}]
    #         }
    #     ],
    #     "remito": {"numeroRemito": "123456789012R"},
    #     "bultos": [
    #         {
    #             "kilos": 2,
    #             "volumenCm": 5000,
    #             "valorDeclaradoSinImpuestos": 1200,
    #             "valorDeclaradoConImpuestos": 1452,
    #             "referencias": [
    #                 {"meta": "detalle", "contenido": "Secador de pelo"},
    #                 {"meta": "idCliente", "contenido": "10000"},
    #                 {"meta": "observaciones", "contenido": "color negro"}
    #             ]
    #         }
    #     ]
    # }
    
    # resultado_orden = api.crear_orden_envio(data)
    # if resultado_orden:
    #   numeroEnvio = resultado_orden.get("numeroEnvio")
    #   numeroAgrupador = resultado_orden.get("numeroAgrupador")
      
    #   # 4. Consultar Estado de la Orden
    #   if numeroEnvio:
    #     estado_orden = api.consultar_estado_orden(numeroEnvio)
    #     if estado_orden:
    #         print(f"\nEstado de la orden {numeroEnvio}: {estado_orden}")
      
    #   # 5. Obtener Etiquetas
    #   if numeroAgrupador:
    #       etiqueta = api.obtener_etiquetas(numeroAgrupador)
    #       if etiqueta:
    #           with open("etiqueta_andreani.pdf", "wb") as etiqueta_file:
    #             etiqueta_file.write(etiqueta)
    #             print("\nEtiqueta guardada como 'etiqueta_andreani.pdf'")
    
    #       # 6. Consultar Estado de Envío
    #       estado_envio = api.consultar_estado_envio(numeroEnvio)
    #       if estado_envio:
    #           print("\nEstado del envío:", estado_envio)
    
    # # 7. Obtener Envios por contrato
    # params = {
    # "contrato": "400021942"
    # }
    # envios_contrato = api.obtener_envios(params)
    # if envios_contrato:
    #     print("\nEnvios por contrato:", envios_contrato)
    
    # # 8. Obtener info multimedia del envio
    # if numeroEnvio:
    #     multimedia_envio = api.obtener_multimedia_envio(numeroEnvio)
    #     if multimedia_envio:
    #         print("\nInfo multimedia del envio:", multimedia_envio)
        
    #     # 9. Obtener remito digitalizado del envio
    #     remito_digitalizado = api.obtener_remito_digitalizado(numeroEnvio)
    #     if remito_digitalizado:
    #       print("\nRemito digitalizado del envio:", remito_digitalizado)
    
    #     # 10. Obtener trazas del envio
    #     trazas_envio = api.obtener_trazas_envio(numeroEnvio)
    #     if trazas_envio:
    #         print("\nTrazas del envio:", trazas_envio)

     # 11. Obtener Localidades por código postal
    codigo_postal_buscado = "1644"  # Reemplaza con el código postal que deseas buscar
    localidades = api.obtener_localidades_por_codigo_postal(codigo_postal_buscado)

    if localidades:
        print(f"\nLocalidades encontradas para el código postal {codigo_postal_buscado}:")
        for localidad in localidades:
          print(f"Localidad: {localidad['localidad']}")