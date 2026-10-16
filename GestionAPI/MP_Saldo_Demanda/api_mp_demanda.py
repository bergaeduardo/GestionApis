#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Cliente API asíncrono para consultar el saldo de Mercado Pago mediante reporte bajo demanda.

Flujo:
  1. Toma snapshot de reportes existentes (para identificar el nuevo).
  2. Solicita la generación de un nuevo reporte para el período: ayer 00:00 → ahora.
  3. Espera (polling) hasta que el nuevo reporte esté disponible.
  4. Descarga el CSV y extrae el último BALANCE_AMOUNT.
  5. Devuelve el resultado en formato JSON.

Tiempo de espera típico: 1-5 minutos.
"""

import asyncio
import aiohttp
import csv
import io
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List, Set

logger = logging.getLogger("mp_saldo_demanda")

MP_BASE_URL = "https://api.mercadopago.com"
POLL_INTERVALO_SEG = 20
POLL_MAX_SEG = 1200  # 20 minutos máximo de espera


class MercadoPagoDemandaClient:
    """
    Genera un reporte de liquidaciones bajo demanda y extrae el saldo actual de la cuenta.
    """

    def __init__(self, access_token: str):
        self._access_token = access_token
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if not self._session or self._session.closed:
            # Timeouts explícitos: connect=10s, lectura de socket=25s, total=35s
            # Evita colgarse en conexiones lentas o respuestas incompletas
            timeout = aiohttp.ClientTimeout(total=90, connect=10, sock_read=75)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    "Authorization": f"Bearer {self._access_token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
        return self._session

    async def _get_json(self, endpoint: str, max_retries: int = 2) -> Optional[Any]:
        url = f"{MP_BASE_URL}{endpoint}"
        for intento in range(max_retries):
            try:
                session = await self._get_session()
                async with session.get(url) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    text = await resp.text()
                    logger.error(f"GET {url} → HTTP {resp.status}: {text}")
                    return None
            except (asyncio.TimeoutError, aiohttp.ClientError) as e:
                logger.warning(f"GET {url} intento {intento+1}/{max_retries} falló: {e}")
                if intento < max_retries - 1:
                    await asyncio.sleep(3)
                    continue
                logger.error(f"GET {url} agotó reintentos.")
                return None
        return None

    async def _post_json(self, endpoint: str, payload: Dict) -> Optional[Any]:
        url = f"{MP_BASE_URL}{endpoint}"
        try:
            session = await self._get_session()
            async with session.post(url, json=payload) as resp:
                if resp.status in (200, 201, 202):
                    return await resp.json()
                text = await resp.text()
                logger.error(f"POST {url} → HTTP {resp.status}: {text}")
                return None
        except (asyncio.TimeoutError, aiohttp.ClientError) as e:
            logger.error(f"POST {url} error: {e}")
            return None

    async def _get_bytes(self, url: str) -> Optional[bytes]:
        try:
            session = await self._get_session()
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.read()
                text = await resp.text()
                logger.error(f"GET (bytes) {url} → HTTP {resp.status}: {text}")
                return None
        except (asyncio.TimeoutError, aiohttp.ClientError) as e:
            logger.error(f"Error descargando {url}: {e}")
            return None

    # ------------------------------------------------------------------

    async def _ids_reportes_existentes(self) -> Set[Any]:
        """
        Devuelve el conjunto de IDs de reportes ya existentes.
        Se llama UNA sola vez antes de crear el nuevo reporte.
        """
        lista = await self._get_json("/v1/account/release_report/list")
        if isinstance(lista, list):
            ids = {r.get("id") for r in lista if r.get("id")}
            logger.info(f"Snapshot: {len(ids)} reportes existentes antes de crear el nuevo.")
            return ids
        return set()

    async def _crear_reporte(self, begin_date: str, end_date: str) -> Optional[Any]:
        """Solicita la creación del reporte. Devuelve el dict de respuesta (con 'id') o None."""
        payload = {"begin_date": begin_date, "end_date": end_date}
        logger.info(f"Solicitando reporte: {begin_date} → {end_date}")
        return await self._post_json("/v1/account/release_report", payload)

    async def _esperar_nuevo_reporte(self, ids_previos: Set, reporte_id: Any) -> Optional[str]:
        """
        Espera hasta que aparezca un reporte con ID nuevo y file_name disponible.

        Estrategia (snapshot): el reporte NO aparece en la lista mientras se genera.
        Solo aparece cuando está listo. Buscamos cualquier ID que no existía en el
        snapshot previo y que ya tenga file_name — ese es el nuestro.

        El tiempo se mide con monotonic() para contar tiempo real (no solo sleep).
        """
        inicio = time.monotonic()

        while True:
            transcurrido = int(time.monotonic() - inicio)
            if transcurrido >= POLL_MAX_SEG:
                break

            lista = await self._get_json("/v1/account/release_report/list")

            if lista is None:
                logger.warning(f"[{transcurrido}s] Lista no disponible (timeout/error). Reintentando...")
            elif isinstance(lista, list):
                for r in lista:
                    r_id = r.get("id")
                    file_name = r.get("file_name") or ""
                    if r_id not in ids_previos and file_name:
                        logger.info(f"[{transcurrido}s] Reporte disponible (id={r_id}): {file_name}")
                        return file_name
                # Reporte aún no apareció en la lista — sigue generándose
                logger.info(f"[{transcurrido}s] Reporte {reporte_id} aún en generación. Esperando...")

            await asyncio.sleep(POLL_INTERVALO_SEG)

        elapsed = int(time.monotonic() - inicio)
        logger.error(f"Timeout: el reporte {reporte_id} no estuvo disponible en {elapsed}s (límite {POLL_MAX_SEG}s).")
        return None

    async def _eliminar_reporte(self, file_name: str) -> None:
        """Elimina el reporte de MP para no acumular reportes generados bajo demanda."""
        url = f"{MP_BASE_URL}/v1/account/release_report/{file_name}"
        try:
            session = await self._get_session()
            async with session.delete(url) as resp:
                if resp.status in (200, 204):
                    logger.info(f"Reporte eliminado de MP: {file_name}")
                else:
                    text = await resp.text()
                    logger.warning(f"No se pudo eliminar el reporte {file_name}: HTTP {resp.status} — {text}")
        except (asyncio.TimeoutError, aiohttp.ClientError) as e:
            logger.warning(f"Error al intentar eliminar reporte {file_name}: {e}")

    async def _descargar_filas_csv(self, file_name: str) -> Optional[List[Dict]]:
        """Descarga el CSV y devuelve todas las filas como lista de dicts."""
        url = f"{MP_BASE_URL}/v1/account/release_report/{file_name}"
        contenido = await self._get_bytes(url)
        if not contenido:
            return None

        texto = contenido.decode("utf-8-sig", errors="replace")
        primera_linea = texto.split("\n")[0]
        sep = ";" if primera_linea.count(";") > primera_linea.count(",") else ","

        filas = list(csv.DictReader(io.StringIO(texto), delimiter=sep))
        if not filas:
            logger.error("El CSV del reporte está vacío.")
            return None

        logger.info(f"Reporte descargado: {len(filas)} filas | columnas: {list(filas[0].keys())}")
        return filas

    def _balance_desde_filas(self, filas: List[Dict]) -> Optional[float]:
        """
        Extrae el último BALANCE_AMOUNT de las filas de movimiento real.
        Excluye filas totalizadoras (RECORD_TYPE='total' o DESCRIPTION vacía/nula)
        que el CSV de MP incluye al final y siempre tienen BALANCE_AMOUNT=0.
        """
        candidatos = ["BALANCE_AMOUNT", "SALDO", "MONTO_SALDO", "SALDO_DISPONIBLE"]
        col = next((c for c in candidatos if c in filas[0]), None)
        if not col:
            logger.error(f"No se encontró columna de saldo. Columnas: {list(filas[0].keys())}")
            return None

        # Filtrar filas totalizadoras: RECORD_TYPE in ('total', '') o DESCRIPTION vacía
        TIPOS_TOTAL = {"total", "totals", "subtotal", ""}
        filas_movimiento = [
            f for f in filas
            if (f.get("RECORD_TYPE") or "").strip().lower() not in TIPOS_TOTAL
            and (f.get("DESCRIPTION") or "").strip() != ""
        ]

        if not filas_movimiento:
            logger.warning("No se encontraron filas de movimiento sin totalizadores. Usando todas.")
            filas_movimiento = filas

        logger.info(f"Filas de movimiento (sin totalizadores): {len(filas_movimiento)} de {len(filas)} totales")

        ultimo = None
        for fila in filas_movimiento:
            valor = (fila.get(col) or "").strip()
            if valor:
                try:
                    ultimo = float(valor.replace(",", "."))
                except ValueError:
                    pass

        if ultimo is None:
            logger.error(f"La columna '{col}' no tiene valores numéricos en filas de movimiento.")
        else:
            logger.info(f"BALANCE_AMOUNT final (último movimiento): {ultimo}")
        return ultimo

    # ------------------------------------------------------------------

    async def get_resultado_completo(self) -> Optional[Dict[str, Any]]:
        """
        Genera un reporte bajo demanda (ayer 00:00 → ahora) y devuelve el saldo
        más todas las filas del CSV para persistencia y validación.

        Returns:
            Dict con:
                - saldo: resumen (timestamp, user_id, available_balance, etc.)
                - filas: lista de dicts con todas las filas del CSV
                - file_name: nombre del reporte generado
            O None si falla.
        """
        ahora = datetime.now(timezone.utc)
        ayer_inicio = (ahora - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        begin_date = ayer_inicio.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_date = ahora.strftime("%Y-%m-%dT%H:%M:%SZ")

        datos_usuario = await self._get_json("/users/me")
        if not datos_usuario or "id" not in datos_usuario:
            logger.error("No se pudo obtener el user_id.")
            return None
        user_id = datos_usuario["id"]

        # Snapshot de IDs existentes ANTES de crear el nuevo reporte
        ids_previos = await self._ids_reportes_existentes()

        resp_creacion = await self._crear_reporte(begin_date, end_date)
        if not resp_creacion:
            return None

        reporte_id = resp_creacion.get("id")
        if not reporte_id:
            logger.error(f"La respuesta de creación no incluye 'id': {resp_creacion}")
            return None

        logger.info(
            f"Reporte creado con id={reporte_id}. "
            f"Esperando generación (máx. {POLL_MAX_SEG}s, polling cada {POLL_INTERVALO_SEG}s)..."
        )
        file_name = await self._esperar_nuevo_reporte(ids_previos, reporte_id)
        if not file_name:
            return None

        filas = await self._descargar_filas_csv(file_name)
        if not filas:
            return None

        balance = self._balance_desde_filas(filas)
        if balance is None:
            return None

        saldo = {
            "timestamp": ahora.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "user_id": user_id,
            "currency_id": "ARS",
            "available_balance": balance,
            "total_amount": balance,
            "fuente": f"demanda:{file_name}",
            "begin_date": begin_date,
            "end_date": end_date,
        }

        return {"saldo": saldo, "filas": filas, "file_name": file_name}

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
