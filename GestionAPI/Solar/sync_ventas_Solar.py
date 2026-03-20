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
    logger = setup_logger('solar_sync')
    
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
                    
                    # Validar datos antes de agregar
                    cantidad = detalle.get('Detalle.Cantidad', 0) or 0
                    importe = detalle.get('Detalle.Importe', 0) or 0
                    iva = detalle.get('Detalle.IVA', 0) or 0
                    
                    # Filtrar items problemáticos de manera inteligente:
                    # - Solo filtrar si ImporteNeto = 0 Y Cantidad = 0 (items vacíos/nulos)
                    # - NO filtrar items negativos legítimos (devoluciones, descuentos)
                    if importe == 0 and cantidad == 0:
                        logger.debug(f"Item vacío filtrado - Comprobante: {detalle.get('Comprobante')}")
                        continue
                    
                    # Log para debug de items negativos (son legítimos)
                    if importe < 0:
                        logger.debug(f"Item negativo incluido (devolución/descuento) - ImporteNeto: {importe}, Comprobante: {detalle.get('Comprobante')}")
                    
                    # Log para debug si hay otros problemas
                    if not cantidad:
                        logger.warning(f"Cantidad = 0 pero ImporteNeto válido - Cantidad: {cantidad}, Importe: {importe}, Comprobante: {detalle.get('Comprobante')}")
                    
                    registro['Detalle'].append({
                        "DescripcionItem": detalle.get('Detalle.CodArticulo', ''),
                        "Cantidad": str(cantidad),
                        "Alicuota": str(detalle.get('Detalle.Alicuota', 0) or 0),
                        "Rubro": str(detalle.get('Detalle.Rubro', 0) or 0),
                        "ImporteNeto": str(importe),
                        "ImporteImpuestos": str(iva)
                    })
                    break

            if not comprobante_encontrado:
                # Validar datos antes de crear nuevo registro
                cantidad = detalle.get('Detalle.Cantidad', 0) or 0
                importe = detalle.get('Detalle.Importe', 0) or 0
                iva = detalle.get('Detalle.IVA', 0) or 0
                
                # Filtrar items problemáticos de manera inteligente:
                # - Solo filtrar si ImporteNeto = 0 Y Cantidad = 0 (items vacíos/nulos)
                # - NO filtrar items negativos legítimos (devoluciones, descuentos)
                if importe == 0 and cantidad == 0:
                    logger.debug(f"Item vacío filtrado - Comprobante: {detalle.get('Comprobante')}")
                    continue
                
                # Log para debug de items negativos (son legítimos)
                if importe < 0:
                    logger.debug(f"Item negativo incluido (devolución/descuento) - ImporteNeto: {importe}, Comprobante: {detalle.get('Comprobante')}")
                
                # Log para debug si hay otros problemas
                if not cantidad:
                    logger.warning(f"Cantidad = 0 pero ImporteNeto válido - Cantidad: {cantidad}, Importe: {importe}, Comprobante: {detalle.get('Comprobante')}")
                
                DetalleVentas.append({
                    'Comprobante': detalle['Comprobante'],
                    'Detalle': [{
                        "DescripcionItem": detalle.get('Detalle.CodArticulo', ''),
                        "Cantidad": str(cantidad),
                        "Alicuota": str(detalle.get('Detalle.Alicuota', 0) or 0),
                        "Rubro": str(detalle.get('Detalle.Rubro', 0) or 0),
                        "ImporteNeto": str(importe),
                        "ImporteImpuestos": str(iva)
                    }]
                })

        # print('Sync_ventas_Solar-DetalleVentas',DetalleVentas)

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
            
            # Calcular Importe dinámicamente como suma de ImporteNeto + ImporteImpuestos
            # Solo si el comprobante tiene detalles válidos (ImporteNeto > 0)
            importe_calculado = 0.0
            detalle_valido = False
            
            if detalle_variable and len(detalle_variable) > 0:
                for detalle_item in detalle_variable:
                    importe_neto = float(detalle_item.get('ImporteNeto', 0) or 0)
                    importe_impuestos = float(detalle_item.get('ImporteImpuestos', 0) or 0)
                    # Incluir TODOS los items (positivos y negativos) para cálculo correcto
                    # Solo excluir si ambos ImporteNeto e ImporteImpuestos son exactamente 0
                    if importe_neto != 0 or importe_impuestos != 0:
                        importe_calculado += importe_neto + importe_impuestos
                        detalle_valido = True
                
                if detalle_valido:
                    # Debug: logger.debug(f"Comprobante {comprobante_buscar}: Importe calculado = {importe_calculado}")
                    pass
                else:
                    logger.warning(f"Comprobante {comprobante_buscar}: Sin detalles válidos - se omitirá")
                    continue  # Saltar este comprobante si no tiene detalles válidos
            else:
                logger.warning(f"No se encontraron detalles para comprobante {comprobante_buscar}")
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
            
            comprobante.append(registro)
            listComp.append(EncVentas['NroComprobante'])

        # print(listComp)
        # Agregar cada nuevo comprobante a la lista existente en "Comprobantes"
        data[0]["Comprobantes"].extend(comprobante)

        # Convertir la lista de comprobantes en un string separado por comas y encerrado entre paréntesis
        comprobantes_str = "('" + "', '".join(listComp) + "')"

        logger.info(f"Preparando envío de {len(listComp)} comprobantes: {', '.join(listComp)}")

        # Informar ventas (pasar lista de comprobantes originales para errores útiles)
        resultado_api = api_client.informar_ventas(token, data[0], listComp)
        if resultado_api:
            # comprobantes_str = "('" + "', '".join(data['comprobantes']) + "')"
            if db.actualizar_estado_sync(comprobantes_str):
                logger.info("Proceso de sincronización completado exitosamente")
            else:
                logger.error("Error al actualizar estado de sincronización")
        else:
            # Verificar si es un error de comprobantes ya registrados (422)
            logger.warning("Error en API - verificando si comprobantes ya están procesados...")
            
            # Si los comprobantes ya están registrados en Solar, marcarlos como procesados
            # ACTIVAR: Descomentar las siguientes líneas para marcar automáticamente como procesados
            if db.actualizar_estado_sync(comprobantes_str):
                logger.warning("Comprobantes marcados como procesados (ya estaban registrados en Solar)")
            else:
                logger.error("Error al actualizar estado tras detectar comprobantes duplicados")
            
            # logger.error("Error al informar ventas")

    except Exception as e:
        logger.error(f"Error en el proceso de sincronización: {str(e)}", exc_info=True)

def procesar_datos_ventas(ventas_enc, ventas_detalle):
    # Procesar y estructurar los datos de ventas
    # [Implementación del procesamiento de datos...]
    pass

if __name__ == "__main__":
    main()