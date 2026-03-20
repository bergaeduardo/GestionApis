import sys
import os

# Obtiene la ruta del directorio padre (la raíz del proyecto)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
# Añade la ruta de la raíz del proyecto a sys.path
sys.path.insert(0, project_root)

from GestionAPI.common.conexion import Conexion
from GestionAPI.common.credenciales import LOCALES_LAKERS
from GestionAPI.Solar import Apis
from GestionAPI.Solar.consultas import qry_ventasEnc,qry_ventasDetalle

import json

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
                    
                    # Validar datos antes de agregar
                    cantidad = detalle.get('Detalle.Cantidad', 0) or 0
                    importe = detalle.get('Detalle.Importe', 0) or 0
                    iva = detalle.get('Detalle.IVA', 0) or 0
                    
                    # Filtrar items con ImporteNeto = 0 para evitar error 422
                    if importe <= 0:
                        print(f"ADVERTENCIA: Item filtrado por ImporteNeto = {importe} - Comprobante: {detalle.get('Comprobante')}")
                        continue
                    
                    # Log para debug si hay otros problemas
                    if not cantidad:
                        print(f"ADVERTENCIA: Cantidad = 0 pero ImporteNeto válido - Cantidad: {cantidad}, Importe: {importe}, Comprobante: {detalle.get('Comprobante')}")
                    
                    registro['Detalle'].append({
                        "DescripcionItem": detalle.get('Detalle.CodArticulo', ''),
                        "Cantidad": str(cantidad),
                        "ImporteNeto": str(importe),
                        "ImporteImpuestos": str(iva)
                    })
                    break

            if not comprobante_encontrado:
                # Validar datos antes de crear nuevo registro
                cantidad = detalle.get('Detalle.Cantidad', 0) or 0
                importe = detalle.get('Detalle.Importe', 0) or 0
                iva = detalle.get('Detalle.IVA', 0) or 0
                
                # Filtrar items con ImporteNeto = 0 para evitar error 422
                if importe <= 0:
                    print(f"ADVERTENCIA: Item filtrado por ImporteNeto = {importe} - Comprobante: {detalle.get('Comprobante')}")
                    continue
                
                # Log para debug si hay otros problemas
                if not cantidad:
                    print(f"ADVERTENCIA: Cantidad = 0 pero ImporteNeto válido - Cantidad: {cantidad}, Importe: {importe}, Comprobante: {detalle.get('Comprobante')}")
                
                DetalleVentas.append({
                    'Comprobante': detalle['Comprobante'],
                    'Detalle': [{
                        "DescripcionItem": detalle.get('Detalle.CodArticulo', ''),
                        "Cantidad": str(cantidad),
                        "ImporteNeto": str(importe),
                        "ImporteImpuestos": str(iva)
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
        # comprobante.append({
        #     "Fecha": "26-03-2021", 
        #     "Hora": "18:15:00", 
        #     "IdComprobante": "02", 
        #     "PtoVenta": "0001", 
        #     "NroComprobante": "", 
        #     "Detalles": [], 
        #     "Pagos": []
        # })
    

        for EncVentas in resultados_ventasEnc:
            # Encontrar el detalle del comprobante específico 
            comprobante_buscar = EncVentas['NroComprobante']
            # print(comprobante_buscar)
            detalle_variable = next((item["Detalle"] for item in DetalleVentas if item["Comprobante"] == comprobante_buscar), None) 
            # print(detalle_variable)
            
            # Calcular Importe dinámicamente como suma de ImporteNeto + ImporteImpuestos
            # Solo si el comprobante tiene detalles válidos (ImporteNeto > 0)
            importe_calculado = 0.0
            detalle_valido = False
            
            if detalle_variable and len(detalle_variable) > 0:
                for detalle_item in detalle_variable:
                    importe_neto = float(detalle_item.get('ImporteNeto', 0) or 0)
                    importe_impuestos = float(detalle_item.get('ImporteImpuestos', 0) or 0)
                    if importe_neto > 0:  # Solo procesar items con ImporteNeto válido
                        importe_calculado += importe_neto + importe_impuestos
                        detalle_valido = True
                
                if detalle_valido:
                    print(f"Comprobante {comprobante_buscar}: Importe calculado = {importe_calculado}")
                else:
                    print(f"ADVERTENCIA: Comprobante {comprobante_buscar}: Sin detalles válidos - se omitirá")
                    continue  # Saltar este comprobante si no tiene detalles válidos
            else:
                print(f"ADVERTENCIA: No se encontraron detalles para comprobante {comprobante_buscar}")
                continue  # Saltar este comprobante si no tiene detalles
            
            registro = {
                "Fecha": EncVentas['Fecha'],
                "Hora": EncVentas['Hora'],
                "IdComprobante": EncVentas['IdComprobante'],
                "PtoVenta": EncVentas['PtoVenta'],
                "NroComprobante": EncVentas['NroComprobante'][-12:],
                "Detalles": detalle_variable,
                "Pagos": [{ 
                    "MedioPago": EncVentas['MedioPago'], 
                    "Importe": str(round(importe_calculado, 2))
                }]
            }
            
            # Reemplazar el valor en "Comprobantes" de la variable "data" 
            data[0]["Comprobantes"] = [registro]

            # informar ventas
            resultadoSync = Apis.informarVentas_Solar(token, data[0])
            if resultadoSync:
                print("Información de ventas sincronizada con Solar")
                # Actualizar estado en el historial
                actEstado = conexion.actEstadoSync(EncVentas['NroComprobante'])
                if actEstado:
                    print("Estado actualizado en la base de datos")
                else:
                    print("Error al actualizar estado en la base de datos")
            else:
                print("Error al informar ventas con Solar")


            

        # # Agregar cada nuevo comprobante a la lista existente en "Comprobantes"
        # data[0]["Comprobantes"].extend(comprobante)



        #     if resultadoSync:
        #         # print("Información de ventas sincronizada con Solar")
        #         # data = json.dumps(data)
        #         print(data[0])
        #     else:
        #         # print("Error al sincronizar información de ventas con Solar")
        #         data = json.dumps(data)
        #         # print(data[0])
        # else:
        #     print("Error al obtener token para sincronizar información de ventas con Solar")
    else:
        print("Error al obtener token para sincronizar información de ventas con Solar")
        exit()
    


    