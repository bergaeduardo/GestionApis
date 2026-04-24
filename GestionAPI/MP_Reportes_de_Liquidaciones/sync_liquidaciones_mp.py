#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script principal de sincronización para MP_Reportes_de_Liquidaciones.

Flujo:
  1. Configurar el reporte para usar encabezados en inglés (KEY names).
  2. Solicitar la creación del reporte para los últimos 5 días.
  3. Esperar (polling) hasta que el reporte esté disponible.
  4. Descargar el CSV y guardarlo temporalmente en temp/.
  5. Procesar el CSV con Pandas (renombrar columnas, limpiar tipos).
  6. Hacer upsert en la tabla MP_T_REPORTE_DE_LIQUIDACIONES en SQL Server.
  7. Eliminar el archivo temporal.

Proceso asíncrono mediante asyncio.
"""

import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, project_root)

import asyncio
import io
from datetime import datetime, timedelta, timezone

import pandas as pd

from GestionAPI.common.logger_config import setup_logger
from GestionAPI.common.credenciales import MERCADOPAGO
from GestionAPI.MP_Reportes_de_Liquidaciones.api_mp import MercadoPagoAPIClient
from GestionAPI.MP_Reportes_de_Liquidaciones.db_operations_mp import MercadoPagoDB
from GestionAPI.MP_Reportes_de_Liquidaciones.consultas import (
    CSV_TO_DB_COLUMNS,
    DECIMAL_COLUMNS,
    INT_COLUMNS,
    DATETIME_COLUMNS,
    BOOL_COLUMNS,
)

_module_dir = os.path.dirname(__file__)
# Logger con ruta al logs/ dentro del mismo módulo
logger = setup_logger(
    "mp_liquidaciones",
    log_path=os.path.join(_module_dir, "logs", "app.log"),
)

TEMP_DIR = os.path.join(_module_dir, "temp")

# Encabezados en español → KEY inglés (fallback si report_translation != 'en')
SPANISH_TO_KEY = {
    "Fecha de liquidación": "DATE",
    "ID de operación en Mercado Pago": "SOURCE_ID",
    "Código de referencia": "EXTERNAL_REFERENCE",
    "Tipo de registro": "RECORD_TYPE",
    "Descripción": "DESCRIPTION",
    "Monto neto acreditado": "NET_CREDIT_AMOUNT",
    "Monto neto debitado": "NET_DEBIT_AMOUNT",
    "Monto recibido por compras por split": "SELLER_AMOUNT",
    "Monto bruto de la operación": "GROSS_AMOUNT",
    "Datos extra": "METADATA",
    "Comisión de Mercado Pago": "MP_FEE_AMOUNT",
    "Comisión por ofrecer cuotas sin interés": "FINANCING_FEE_AMOUNT",
    "Costo de envío": "SHIPPING_FEE_AMOUNT",
    "Impuestos cobrados por retenciones IIBB": "TAXES_AMOUNT",
    "Cupón de descuento": "COUPON_AMOUNT",
    "Cuotas": "INSTALLMENTS",
    "Medio de pago": "PAYMENT_METHOD",
    "Tipo de medio de pago": "PAYMENT_METHOD_TYPE",
    "Detalle de impuestos": "TAX_DETAIL",
    "Impuesto descontado del valor bruto": "TAX_AMOUNT_TELCO",
    "Fecha de aprobación": "TRANSACTION_APPROVAL_DATE",
    "ID de caja": "POS_ID",
    "Nombre de caja": "POS_NAME",
    "ID de caja definido por el usuario": "EXTERNAL_POS_ID",
    "ID de sucursal": "STORE_ID",
    "Nombre de sucursal": "STORE_NAME",
    "ID de sucursal definido por el usuario": "EXTERNAL_STORE_ID",
    "ID de la orden": "ORDER_ID",
    "ID de envío": "SHIPPING_ID",
    "Modo de envío": "SHIPMENT_MODE",
    "ID del paquete": "PACK_ID",
    "Desglose de impuestos": "TAXES_DISAGGREGATED",
    "Costo por ofrecer descuento": "EFFECTIVE_COUPON_AMOUNT",
    "Número de serie del lector": "POI_ID",
    "Tarjeta de tu comprador": "CARD_INITIAL_NUMBER",
    "Etiquetas de la operación": "OPERATION_TAGS",
    "Identificador de producto": "ITEM_ID",
    "Nombre de quien hace el pago": "PAYER_NAME",
    "Tipo de identificación del pagador": "PAYER_ID_TYPE",
    "Número de identificación del pagador": "PAYER_ID_NUMBER",
    "Canal de venta": "BUSINESS_UNIT",
    "Plataforma de cobro": "SUB_UNIT",
    "Saldo": "BALANCE_AMOUNT",
    "Cuenta de destino del retiro": "PAYOUT_BANK_ACCOUNT_NUMBER",
    "Código de producto SKU": "PRODUCT_SKU",
    "Detalle de la venta": "SALE_DETAIL",
    "Moneda": "CURRENCY",
    "Bandera": "FRANCHISE",
    "Últimos 4 dígitos": "LAST_FOUR_DIGITS",
    "ID de la solicitud": "ORDER_MP",
    "Billetera virtual": "POI_WALLET_NAME",
    "ID de intento de operación": "TRANSACTION_INTENT_ID",
    "Banco de origen": "POI_BANK_NAME",
    "ID de la compra": "PURCHASE_ID",
    "Liberado": "IS_RELEASED",
    "ID de asociación de envíos": "SHIPPING_ORDER_ID",
    "Nombre del emisor": "ISSUER_NAME",
}


def _calcular_rango_fechas() -> tuple:
    """
    Calcula el rango de fechas para los últimos 5 días alineado con la medianoche de Argentina (UTC-3).

    La API de Mercado Pago (Argentina) opera en UTC-3. Para que los límites de fecha
    coincidan exactamente con medianoche local, los timestamps deben enviarse en múltiplos
    de 03:00 UTC (= 00:00 Argentina).

    Ejemplo (si hoy Argentina es 24/04):
        - end_date  = 2026-04-24T03:00:00Z  (= 00:00 del 24/04 Argentina = inicio de hoy)
        - begin_date = 2026-04-19T03:00:00Z  (= 00:00 del 19/04 Argentina)
        → cubre exactamente los 5 días: 19, 20, 21, 22 y 23 de abril en Argentina.

    Returns:
        Tuple (begin_date_str, end_date_str) en formato ISO 8601 UTC.
    """
    ahora_utc = datetime.now(tz=timezone.utc)

    # Calcular la medianoche de HOY en Argentina (UTC-3 = UTC+03:00:00 en offset inverso)
    # Medianoche Argentina = 03:00 UTC del mismo día calendario UTC
    # Si aún no llegamos a las 03:00 UTC, seguimos siendo "ayer" en Argentina
    if ahora_utc.hour < 3:
        hoy_ar_en_utc = ahora_utc.replace(hour=3, minute=0, second=0, microsecond=0) - timedelta(days=1)
    else:
        hoy_ar_en_utc = ahora_utc.replace(hour=3, minute=0, second=0, microsecond=0)

    # end = 02:59:59Z del día actual = 23:59:59 de AYER en Argentina
    # Usando el último segundo del día anterior evitamos ambigüedad en cómo MP interpreta el límite.
    end_date = hoy_ar_en_utc - timedelta(seconds=1)      # = 2026-04-24T02:59:59Z = 23:59:59 AR ayer
    begin_date = hoy_ar_en_utc - timedelta(days=5)       # = 5 días atrás desde medianoche AR hoy

    return (
        begin_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
        end_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )


def _guardar_csv_temporal(contenido: bytes, file_name: str) -> str:
    """
    Guarda el contenido binario del CSV en el directorio temp/.

    Returns:
        str: Ruta absoluta del archivo guardado.
    """
    os.makedirs(TEMP_DIR, exist_ok=True)
    ruta = os.path.join(TEMP_DIR, file_name)
    with open(ruta, "wb") as f:
        f.write(contenido)
    logger.info(f"CSV temporal guardado en: {ruta}")
    return ruta


def _leer_csv(ruta: str) -> pd.DataFrame:
    """
    Lee el archivo CSV del reporte de MP y devuelve un DataFrame con columnas renombradas a sus KEY DB names.

    Args:
        ruta (str): Ruta al archivo CSV.

    Returns:
        pd.DataFrame con columnas nombradas según CSV_TO_DB_COLUMNS.
    """
    # Intentar detectar el separador (MP puede usar ; o ,)
    with open(ruta, "r", encoding="utf-8-sig") as f:
        primera_linea = f.readline()

    separador = ";" if primera_linea.count(";") > primera_linea.count(",") else ","

    df = pd.read_csv(ruta, sep=separador, encoding="utf-8-sig", dtype=str)
    logger.info(f"CSV leído: {len(df)} filas, {len(df.columns)} columnas. Separador: '{separador}'")

    # Normalizar encabezados: quitar espacios extra
    df.columns = [c.strip() for c in df.columns]

    # Si los encabezados están en español, traducirlos a KEY inglés
    if df.columns[0] not in CSV_TO_DB_COLUMNS:
        df.rename(columns=SPANISH_TO_KEY, inplace=True)
        logger.info("Encabezados traducidos de español a KEY inglés.")

    # Renombrar de KEY CSV → columna DB
    df.rename(columns=CSV_TO_DB_COLUMNS, inplace=True)

    return df


def _limpiar_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica conversiones de tipos y limpieza de datos al DataFrame.

    - Reemplaza cadenas vacías y 'nan' por None (NULL en DB).
    - Convierte columnas decimales, enteras, datetime y booleanas.

    Args:
        df (pd.DataFrame): DataFrame crudo con columnas renombradas.

    Returns:
        pd.DataFrame limpio listo para el upsert.
    """
    # Reemplazar cadenas vacías y 'nan' por NaN
    df.replace({"": None, "nan": None, "NaN": None, "None": None}, inplace=True)

    # Columnas DB a KEY para la conversión de tipos
    db_to_csv_key = {v: k for k, v in CSV_TO_DB_COLUMNS.items()}

    # Convertir decimales
    for col in df.columns:
        csv_key = db_to_csv_key.get(col, col)
        if csv_key in DECIMAL_COLUMNS:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        elif csv_key in INT_COLUMNS:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            df[col] = df[col].where(df[col].notna(), other=None)
        elif csv_key in DATETIME_COLUMNS or col in ("FECHA_LIQUIDACION", "TRANSACTION_APPROVAL_DATE"):
            df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)
            # Convertir a timezone-naive para compatibilidad con pyodbc / SQL Server
            if hasattr(df[col], "dt") and hasattr(df[col].dt, "tz"):
                df[col] = df[col].dt.tz_localize(None) if df[col].dt.tz is None else df[col].dt.tz_convert(None)
        elif csv_key in BOOL_COLUMNS or col == "IS_RELEASED":
            df[col] = df[col].map(
                lambda x: True if str(x).strip().lower() in ("true", "1", "yes") 
                          else (False if str(x).strip().lower() in ("false", "0", "no") else None)
            )

    logger.info(f"DataFrame limpiado. Total filas: {len(df)}")
    return df


async def main():
    """
    Función principal de sincronización del reporte de liquidaciones de Mercado Pago.
    """
    logger.info("=" * 80)
    logger.info("SINCRONIZACIÓN MP - REPORTE DE LIQUIDACIONES")
    logger.info("=" * 80)

    inicio_proceso = datetime.now()
    api_client = MercadoPagoAPIClient(access_token=MERCADOPAGO["access_token"])
    ruta_temp = None

    try:
        # 1. Calcular rango de fechas (últimos 5 días sin incluir el día actual)
        begin_date, end_date = _calcular_rango_fechas()
        logger.info(f"Rango de fechas: {begin_date} → {end_date}")

        # 3. Obtener snapshot de IDs de reportes ya existentes (antes de crear el nuevo)
        reportes_previos = await api_client.obtener_lista_reportes()
        ids_previos = {r.get("id") for r in reportes_previos if r.get("id") is not None}
        logger.info(f"Reportes existentes antes de crear: {len(ids_previos)}")

        # 4. Crear el reporte
        reporte_info = await api_client.crear_reporte(begin_date, end_date)
        if not reporte_info:
            logger.error("No se pudo crear el reporte. Abortando sincronización.")
            return

        report_id = reporte_info.get("id")
        status = reporte_info.get("status", "")
        file_name = reporte_info.get("file_name")  # Null en respuesta 202 (creación async)

        logger.info(
            f"Reporte solicitado. job_id={report_id} | status='{status}' | file_name='{file_name}'"
        )

        # 5. Si el reporte no está listo inmediatamente, esperar con polling (máx. 20 min)
        # Se busca un reporte NUEVO (id no presente antes de la creación) con file_name disponible.
        if status != "ready" or not file_name:
            file_name = await api_client.esperar_reporte_disponible(
                ids_previos, max_espera_seg=1200
            )
            if not file_name:
                logger.error("El reporte no estuvo disponible en el tiempo de espera (20 min). Abortando.")
                return

        # 5. Descargar el CSV
        contenido_csv = await api_client.descargar_reporte(file_name)
        if not contenido_csv:
            logger.error("No se pudo descargar el reporte. Abortando sincronización.")
            return

        # 6. Guardar CSV en temp/
        ruta_temp = _guardar_csv_temporal(contenido_csv, file_name)

        # 7. Leer con Pandas
        df = _leer_csv(ruta_temp)
        if df.empty:
            logger.warning("El reporte descargado no contiene datos.")
            return

        # 8. Limpiar y convertir tipos
        df = _limpiar_dataframe(df)

        # 9. Upsert en SQL Server
        db = MercadoPagoDB()
        stats = db.upsert_liquidaciones(df)

        # Resumen final
        duracion = datetime.now() - inicio_proceso
        logger.info("=" * 80)
        logger.info("RESUMEN")
        logger.info("=" * 80)
        logger.info(f"Filas procesadas: {stats['insertados']} | Errores: {stats['errores']}")
        logger.info(f"Duración total: {duracion.total_seconds():.1f} segundos")
        logger.info("=" * 80)

        if stats["errores"] == 0:
            logger.info("Sincronización completada exitosamente.")
        else:
            logger.warning(
                f"Sincronización completada con {stats['errores']} errores. Revisar logs."
            )

    except Exception as e:
        logger.error(f"Error crítico en el proceso de sincronización: {e}", exc_info=True)
        raise

    finally:
        await api_client.close()
        # Eliminar CSV temporal
        if ruta_temp and os.path.exists(ruta_temp):
            try:
                os.remove(ruta_temp)
                logger.info(f"Archivo temporal eliminado: {ruta_temp}")
            except OSError as e:
                logger.warning(f"No se pudo eliminar el archivo temporal '{ruta_temp}': {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Sincronización interrumpida por el usuario.")
    except Exception as e:
        logger.error(f"Error fatal: {e}", exc_info=True)
        sys.exit(1)
