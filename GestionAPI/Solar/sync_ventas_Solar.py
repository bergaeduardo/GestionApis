import sys
import os

# Obtiene la ruta del directorio padre (la raíz del proyecto)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
# Añade la ruta de la raíz del proyecto a sys.path
sys.path.insert(0, project_root)
import logging
from GestionAPI.common.logger_config import setup_logger
from GestionAPI.common.db_operations import DatabaseConnection
from GestionAPI.Solar.api_client import SolarApiClient
from GestionAPI.common.credenciales import LOCALES_LAKERS, API_SOLAR
from GestionAPI.Solar.consultas import qry_ventasEnc, qry_ventasDetalle

def main():
    # Configurar el logger
    logger = setup_logger()
    
    try:
        # Inicializar conexión a la base de datos
        db = DatabaseConnection(
            server=LOCALES_LAKERS['server'],
            database=LOCALES_LAKERS['database'],
            user=LOCALES_LAKERS['user'],
            password=LOCALES_LAKERS['password']
        )

        # Obtener ventas pendientes
        ventas_enc = db.ejecutar_consulta(qry_ventasEnc)
        if not ventas_enc:
            logger.info("No hay ventas pendientes de sincronizar")
            return

        logger.info(f"Se encontraron {len(ventas_enc)} ventas pendientes de sincronizar")

        # Inicializar cliente API
        api_client = SolarApiClient()
        token = api_client.obtener_token(API_SOLAR)
        
        if not token:
            logger.error("No se pudo obtener el token de acceso")
            return

# Convertir los resultados en una lista de diccionarios
        columnas_ventasEnc = db.obtener_nombres_columnas(qry_ventasEnc)
        resultados_ventasEnc = [dict(zip(columnas_ventasEnc, fila)) for fila in ventas_enc]
        # print(resultados_ventasEnc)


        """     Ventas Detalle """
        # Ejecutar la consulta y obtener los resultados
        lista_ventasDetalle = db.ejecutar_consulta(qry_ventasDetalle)
        # Obtener los nombres de las columnas para la consulta ventasDetalle
        columnas_ventasDetalle = db.obtener_nombres_columnas(qry_ventasDetalle)
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

        # print(listComp)
        # Agregar cada nuevo comprobante a la lista existente en "Comprobantes"
        data[0]["Comprobantes"].extend(comprobante)

        # Convertir la lista de comprobantes en un string separado por comas y encerrado entre paréntesis
        comprobantes_str = "('" + "', '".join(listComp) + "')"

        # Imprimir el string de comprobantes
        # print(comprobantes_str)
        
        # Informar ventas
        if api_client.informar_ventas(token, data[0]):
            # comprobantes_str = "('" + "', '".join(data['comprobantes']) + "')"
            if db.actualizar_estado_sync(comprobantes_str):
                logger.info("Proceso de sincronización completado exitosamente")
            else:
                logger.error("Error al actualizar estado de sincronización")
        else:
            logger.error("Error al informar ventas")

    except Exception as e:
        logger.error(f"Error en el proceso de sincronización: {str(e)}", exc_info=True)

def procesar_datos_ventas(ventas_enc, ventas_detalle):
    # Procesar y estructurar los datos de ventas
    # [Implementación del procesamiento de datos...]
    pass

if __name__ == "__main__":
    main()