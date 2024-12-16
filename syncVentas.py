from conexion import Conexion
from credenciales import LOCALES_LAKERS
import Apis
from consultas import qry_ventasEnc,qry_ventasDetalle

# Crear una instancia de la clase Conexion
conexion = Conexion(server=LOCALES_LAKERS['server'], database=LOCALES_LAKERS['database'], user=LOCALES_LAKERS['user'], password=LOCALES_LAKERS['password'])

"""     Ventas Encabezados """
# Obtener ventas pendientes de sincronizar (Solo encabezados)
ventasEnc = conexion.ejecutar_consulta(qry_ventasEnc)

if not ventasEnc:
    print("No hay ventas pendientes de sincronizar")
    exit()
else:
    print("Hay {} ventas pendientes de sincronizar".format(len(ventasEnc)))

    # obtener token
    token = Apis.obtenerToken_Solar()
    resultadoSync = False
    if token:
        # Convertir los resultados en una lista de diccionarios
        columnas_ventasEnc = conexion.obtener_nombres_columnas(qry_ventasEnc)
        resultados_ventasEnc = [dict(zip(columnas_ventasEnc, fila)) for fila in ventasEnc]
        # print(resultados_ventasEnc)


        """     Ventas Detalle """
        # Ejecutar la consulta y obtener los resultados
        lista_ventasDetalle = conexion.ejecutar_consulta(qry_ventasDetalle)
        # Obtener los nombres de las columnas para la consulta ventasDetalle
        columnas_ventasDetalle = conexion.obtener_nombres_columnas(qry_ventasDetalle)
        dict_VentasDetalle = [dict(zip(columnas_ventasDetalle, fila)) for fila in lista_ventasDetalle]
        
        # Armar estructura de detalle
        DetalleVentas = []
        for detalle in dict_VentasDetalle:
            comprobante_encontrado = False
            for registro in DetalleVentas:
                if registro['Comprobante'] == detalle['Comprobante']:
                    comprobante_encontrado = True
                    registro['Detalle'].append({
                        "DescripcionItem": detalle['Detalle.CodArticulo'],
                        "Cantidad": str(detalle['Detalle.Cantidad']),
                        "ImporteNeto": str(detalle['Detalle.Importe']),
                        "ImporteImpuestos": str(detalle['Detalle.IVA'])
                    })
                    break

            if not comprobante_encontrado:
                DetalleVentas.append({
                    'Comprobante': detalle['Comprobante'],
                    'Detalle': [{
                        "DescripcionItem": detalle['Detalle.CodArticulo'],
                        "Cantidad": str(detalle['Detalle.Cantidad']),
                        "ImporteNeto": str(detalle['Detalle.Importe']),
                        "ImporteImpuestos": str(detalle['Detalle.IVA'])
                    }]
                })

        # print('DetalleVentas',DetalleVentas)

        # Armar estructura de Json
        data = []
        data.append({
            "IdCliente": "000040", 
            "Comprobantes": []
        })
        comprobante = []
        listComp = []    

        for EncVentas in resultados_ventasEnc:
            # Encontrar el detalle del comprobante específico 
            comprobante_buscar = EncVentas['NroComprobante']
            # print(comprobante_buscar)
            detalle_variable = next((item["Detalle"] for item in DetalleVentas if item["Comprobante"] == comprobante_buscar), None) 
            # print(detalle_variable)
            
            registro = {
                "Fecha": EncVentas['Fecha'],
                "Hora": EncVentas['Hora'],
                "IdComprobante": EncVentas['IdComprobante'],
                "PtoVenta": EncVentas['PtoVenta'],
                "NroComprobante": EncVentas['NroComprobante'][-12:],
                "Detalles": detalle_variable,
                "Pagos": [{ 
                    "MedioPago": EncVentas['MedioPago'], 
                    "Importe": str(EncVentas['Importe'])
                }]
            }
            
            comprobante.append(registro)
            listComp.append(EncVentas['NroComprobante'])

        # Agregar cada nuevo comprobante a la lista existente en "Comprobantes"
        data[0]["Comprobantes"].extend(comprobante)

        # Convertir la lista de comprobantes en un string separado por comas y encerrado entre paréntesis
        comprobantes_str = "('" + "', '".join(listComp) + "')"

        # Imprimir el string de comprobantes
        print(comprobantes_str)


        # informar ventas
        resultadoSync = Apis.informarVentas_Solar(token, data[0])
        if resultadoSync:
            print("Información de ventas sincronizada con Solar")
            # Actualizar estado en el historial
            actEstado = conexion.actEstadoSync(comprobantes_str)
            if actEstado:
                print("Estado actualizado en la base de datos")
            else:
                print("Error al actualizar estado en la base de datos")
        else:
            print("Error al informar ventas con Solar")

    else:
        print("Error al obtener token para sincronizar información de ventas con Solar")
        exit()
    


    