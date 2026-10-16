#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Cliente API asíncrono para consultar el saldo disponible de una cuenta de Mercado Pago Argentina.

Estrategia con fallback automático:
    1. Intenta el endpoint directo de balance (requiere scope mp-account):
       GET /users/{user_id}/mercadopago_account/balance
    2. Si recibe 403, cae al fallback:
       Descarga el reporte de liquidaciones más reciente y extrae el último BALANCE_AMOUNT.
"""

import asyncio
import aiohttp
import csv
import io
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

logger = logging.getLogger("mp_saldo_cuenta")

MP_BASE_URL = "https://api.mercadopago.com"


class MercadoPagoSaldoClient:
    """
    Consulta el saldo disponible de una cuenta de Mercado Pago mediante la API oficial.
    Usa Bearer token para autenticación y aiohttp para las llamadas HTTP.
    """

    def __init__(self, access_token: str):
        self._access_token = access_token
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if not self._session or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=60)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    "Authorization": f"Bearer {self._access_token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
        return self._session

    async def _get_json(self, endpoint: str, max_retries: int = 3) -> Optional[Any]:
        """GET que espera respuesta JSON. Devuelve None en error."""
        url = f"{MP_BASE_URL}{endpoint}"
        for intento in range(max_retries):
            try:
                session = await self._get_session()
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.json()
                    if response.status in (401, 403, 404):
                        text = await response.text()
                        logger.warning(f"HTTP {response.status} en {url}: {text}")
                        return {"_status": response.status}
                    if response.status >= 500 and intento < max_retries - 1:
                        await asyncio.sleep(2 ** intento)
                        continue
                    text = await response.text()
                    logger.error(f"Error HTTP {response.status} en GET {url}: {text}")
                    return None
            except asyncio.TimeoutError:
                if intento < max_retries - 1:
                    await asyncio.sleep(2 ** intento)
                    continue
                logger.error(f"Timeout en GET {url}")
                return None
            except aiohttp.ClientError as e:
                if intento < max_retries - 1:
                    await asyncio.sleep(2 ** intento)
                    continue
                logger.error(f"Error de conexión en GET {url}: {e}")
                return None
        return None

    async def _get_bytes(self, url: str) -> Optional[bytes]:
        """GET que descarga contenido binario (CSV)."""
        try:
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.read()
                text = await response.text()
                logger.error(f"Error HTTP {response.status} descargando {url}: {text}")
                return None
        except Exception as e:
            logger.error(f"Error descargando {url}: {e}")
            return None

    # ------------------------------------------------------------------
    # Método directo (requiere scope mp-account)
    # ------------------------------------------------------------------

    async def _saldo_directo(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Intenta obtener el saldo via endpoint directo.
        Devuelve el dict de saldo, None si falla, o {"_forbidden": True} si es 403.
        """
        datos = await self._get_json(f"/users/{user_id}/mercadopago_account/balance")
        if datos is None:
            return None
        if datos.get("_status") == 403:
            return {"_forbidden": True}
        return datos

    # ------------------------------------------------------------------
    # Fallback: extraer BALANCE_AMOUNT del reporte de liquidaciones más reciente
    # ------------------------------------------------------------------

    async def _lista_reportes(self) -> List[Dict[str, Any]]:
        resultado = await self._get_json("/v1/account/release_report/list")
        if isinstance(resultado, list):
            return resultado
        return []

    async def _saldo_desde_reporte(self) -> Optional[Dict[str, Any]]:
        """
        Descarga el reporte de liquidaciones más reciente y extrae el último BALANCE_AMOUNT.
        """
        lista = await self._lista_reportes()
        if not lista:
            logger.error("No hay reportes de liquidaciones disponibles para usar como fallback.")
            return None

        # El reporte más reciente es el primero de la lista (MP los devuelve en orden descendente)
        # Filtramos los que tienen file_name disponible
        disponibles = [r for r in lista if r.get("file_name")]
        if not disponibles:
            logger.error("Ningún reporte tiene file_name disponible.")
            return None

        reporte = disponibles[0]
        file_name = reporte["file_name"]
        fecha_reporte = reporte.get("end_date", "desconocida")
        logger.info(f"Fallback: usando reporte '{file_name}' (hasta {fecha_reporte})")

        url = f"{MP_BASE_URL}/v1/account/release_report/{file_name}"
        contenido = await self._get_bytes(url)
        if not contenido:
            return None

        # Parsear el CSV — MP puede usar ";" como separador y encabezados en español
        texto = contenido.decode("utf-8-sig", errors="replace")

        # Detectar separador: si la primera línea tiene ";" asumimos punto y coma
        primera_linea = texto.split("\n")[0]
        separador = ";" if primera_linea.count(";") > primera_linea.count(",") else ","

        reader = csv.DictReader(io.StringIO(texto), delimiter=separador)

        # Leer todas las filas primero para inspeccionar encabezados
        filas = list(reader)
        if not filas:
            logger.error("El reporte CSV está vacío.")
            return None

        columnas_reales = list(filas[0].keys())
        logger.info(f"Columnas en el reporte: {columnas_reales}")

        # Posibles nombres del campo saldo (inglés y español)
        CANDIDATOS_BALANCE = [
            "BALANCE_AMOUNT",       # inglés (report_translation=en)
            "SALDO",                # español genérico
            "MONTO_SALDO",
            "SALDO_DISPONIBLE",
            "Balance amount",
            "Saldo",
        ]

        columna_balance = next(
            (c for c in CANDIDATOS_BALANCE if c in columnas_reales), None
        )

        if columna_balance is None:
            logger.error(
                f"No se encontró columna de saldo. Columnas disponibles: {columnas_reales}"
            )
            return None

        # Excluir filas totalizadoras (RECORD_TYPE='total' o DESCRIPTION vacía)
        # que MP incluye al final del CSV con BALANCE_AMOUNT=0
        TIPOS_TOTAL = {"total", "totals", "subtotal", ""}
        filas_movimiento = [
            f for f in filas
            if (f.get("RECORD_TYPE") or "").strip().lower() not in TIPOS_TOTAL
            and (f.get("DESCRIPTION") or "").strip() != ""
        ]
        if not filas_movimiento:
            logger.warning("No se encontraron filas de movimiento. Usando todas las filas.")
            filas_movimiento = filas

        logger.info(f"Filas de movimiento (sin totalizadores): {len(filas_movimiento)} de {len(filas)} totales")

        ultimo_balance = None
        for fila in filas_movimiento:
            valor = fila.get(columna_balance, "").strip()
            if valor:
                try:
                    ultimo_balance = float(valor.replace(",", "."))
                except ValueError:
                    pass

        if ultimo_balance is None:
            logger.error(f"La columna '{columna_balance}' existe pero no tiene valores numéricos.")
            return None

        logger.info(f"BALANCE_AMOUNT final (último movimiento): {ultimo_balance}")

        return {
            "available_balance": ultimo_balance,
            "unavailable_balance": None,   # No disponible via reporte
            "total_amount": ultimo_balance,
            "currency_id": "ARS",
            "fuente": f"reporte:{file_name}",
            "fecha_corte_reporte": fecha_reporte,
        }

    # ------------------------------------------------------------------
    # Método principal
    # ------------------------------------------------------------------

    async def get_saldo_json(self) -> Optional[Dict[str, Any]]:
        """
        Consulta el saldo disponible de la cuenta y devuelve el resultado en formato JSON.

        Intenta primero el endpoint directo (scope mp-account). Si recibe 403,
        usa el fallback de reporte de liquidaciones.

        Returns:
            Dict con:
                - timestamp (str): Momento de la consulta en ISO 8601 UTC.
                - user_id (int): ID de la cuenta consultada.
                - currency_id (str): Moneda (ej. "ARS").
                - available_balance (float): Saldo disponible para usar.
                - unavailable_balance (float|None): Saldo pendiente (None si viene del fallback).
                - total_amount (float): Saldo total.
                - fuente (str): "api_directa" o "reporte:<file_name>".
            Devuelve None si todas las estrategias fallan.
        """
        datos_usuario = await self._get_json("/users/me")
        if not datos_usuario or "_status" in datos_usuario:
            logger.error("No se pudo obtener el user_id desde /users/me")
            return None

        user_id = datos_usuario["id"]

        # Intento 1: endpoint directo
        saldo = await self._saldo_directo(user_id)

        if saldo and not saldo.get("_forbidden"):
            return {
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "user_id": user_id,
                "currency_id": saldo.get("currency_id", "ARS"),
                "available_balance": saldo.get("available_balance", 0.0),
                "unavailable_balance": saldo.get("unavailable_balance", 0.0),
                "total_amount": saldo.get("total_amount", 0.0),
                "fuente": "api_directa",
            }

        # Intento 2: fallback via reporte
        if saldo and saldo.get("_forbidden"):
            logger.info("Endpoint directo devolvió 403. Usando fallback de reporte.")

        saldo_fallback = await self._saldo_desde_reporte()
        if saldo_fallback is None:
            return None

        return {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "user_id": user_id,
            **saldo_fallback,
        }

    async def close(self):
        """Cierra la sesión HTTP de forma explícita."""
        if self._session and not self._session.closed:
            await self._session.close()


async def consultar_saldo(access_token: str) -> Optional[Dict[str, Any]]:
    """
    Función de conveniencia para consultar el saldo sin gestionar el cliente manualmente.

    Args:
        access_token (str): Token de acceso de la cuenta de Mercado Pago.

    Returns:
        Dict con el saldo o None si falla.
    """
    client = MercadoPagoSaldoClient(access_token)
    try:
        return await client.get_saldo_json()
    finally:
        await client.close()
