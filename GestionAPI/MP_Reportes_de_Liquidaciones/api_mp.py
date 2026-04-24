#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Cliente API asíncrono para Mercado Pago - Reporte de Liquidaciones.
Maneja la creación, consulta, espera y descarga de reportes mediante la API oficial de MP.
"""

import asyncio
import aiohttp
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger("mp_liquidaciones")

MP_BASE_URL = "https://api.mercadopago.com"


class MercadoPagoAPIClient:
    """
    Cliente API asíncrono para interactuar con los endpoints de Reportes de Liquidaciones de Mercado Pago.
    Usa Bearer token para autenticación y aiohttp para las llamadas HTTP.
    """

    def __init__(self, access_token: str):
        """
        Args:
            access_token (str): Token de acceso de la cuenta de Mercado Pago.
        """
        self._access_token = access_token
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Obtiene o reutiliza la sesión HTTP con configuración optimizada."""
        if not self._session or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=60)
            connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers={
                    "Authorization": f"Bearer {self._access_token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
        return self._session

    async def _get(
        self, endpoint: str, max_retries: int = 3, **kwargs
    ) -> Optional[Any]:
        """
        Ejecuta un GET con reintentos y backoff exponencial.

        Returns:
            Respuesta deserializada (dict o list) o None en caso de error.
        """
        url = f"{MP_BASE_URL}{endpoint}"
        for intento in range(max_retries):
            try:
                session = await self._get_session()
                async with session.get(url, **kwargs) as response:
                    if response.status == 200:
                        content_type = response.headers.get("Content-Type", "")
                        if "json" in content_type:
                            return await response.json()
                        return await response.read()  # CSV binario
                    if response.status == 401:
                        logger.error("Error de autenticación (401). Verificar access_token.")
                        return None
                    if response.status == 404:
                        logger.error(f"Recurso no encontrado (404): {url}")
                        return None
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
                logger.error(f"Timeout en GET {url} después de {max_retries} intentos.")
                return None
            except aiohttp.ClientError as e:
                if intento < max_retries - 1:
                    await asyncio.sleep(2 ** intento)
                    continue
                logger.error(f"Error de conexión en GET {url}: {e}")
                return None
        return None

    async def _post(
        self, endpoint: str, payload: Dict[str, Any], max_retries: int = 3
    ) -> Optional[Dict[str, Any]]:
        """
        Ejecuta un POST con reintentos y backoff exponencial.

        Returns:
            Respuesta JSON deserializada o None en caso de error.
        """
        url = f"{MP_BASE_URL}{endpoint}"
        for intento in range(max_retries):
            try:
                session = await self._get_session()
                async with session.post(url, json=payload) as response:
                    if response.status in (200, 201, 202):  # 202 = Accepted (creación asíncrona)
                        return await response.json()
                    if response.status == 401:
                        logger.error("Error de autenticación (401). Verificar access_token.")
                        return None
                    if response.status >= 500 and intento < max_retries - 1:
                        await asyncio.sleep(2 ** intento)
                        continue
                    text = await response.text()
                    logger.error(f"Error HTTP {response.status} en POST {url}: {text}")
                    return None
            except asyncio.TimeoutError:
                if intento < max_retries - 1:
                    await asyncio.sleep(2 ** intento)
                    continue
                logger.error(f"Timeout en POST {url} después de {max_retries} intentos.")
                return None
            except aiohttp.ClientError as e:
                if intento < max_retries - 1:
                    await asyncio.sleep(2 ** intento)
                    continue
                logger.error(f"Error de conexión en POST {url}: {e}")
                return None
        return None

    async def _put(
        self, endpoint: str, payload: Dict[str, Any], max_retries: int = 3
    ) -> Optional[Dict[str, Any]]:
        """Ejecuta un PUT con reintentos."""
        url = f"{MP_BASE_URL}{endpoint}"
        for intento in range(max_retries):
            try:
                session = await self._get_session()
                async with session.put(url, json=payload) as response:
                    if response.status == 200:
                        return await response.json()
                    if response.status == 401:
                        logger.error("Error de autenticación (401). Verificar access_token.")
                        return None
                    if response.status >= 500 and intento < max_retries - 1:
                        await asyncio.sleep(2 ** intento)
                        continue
                    text = await response.text()
                    logger.error(f"Error HTTP {response.status} en PUT {url}: {text}")
                    return None
            except asyncio.TimeoutError:
                if intento < max_retries - 1:
                    await asyncio.sleep(2 ** intento)
                    continue
                logger.error(f"Timeout en PUT {url} después de {max_retries} intentos.")
                return None
            except aiohttp.ClientError as e:
                if intento < max_retries - 1:
                    await asyncio.sleep(2 ** intento)
                    continue
                logger.error(f"Error de conexión en PUT {url}: {e}")
                return None
        return None

    # ------------------------------------------------------------------
    # Métodos de configuración
    # ------------------------------------------------------------------

    async def consultar_configuracion(self) -> Optional[Dict[str, Any]]:
        """
        Consulta la configuración actual del reporte de liquidaciones.

        Returns:
            Dict con la configuración actual o None en caso de error.
        """
        return await self._get("/v1/account/release_report/config")

    async def actualizar_configuracion(self, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Actualiza la configuración del reporte de liquidaciones.
        Útil para asegurar que los encabezados del CSV estén en inglés (KEY names).

        Args:
            config (Dict): Campos de configuración a actualizar.

        Returns:
            Dict con la configuración actualizada o None en caso de error.
        """
        return await self._put("/v1/account/release_report/config", config)

    async def asegurar_configuracion_en_ingles(self) -> bool:
        """
        Configura el reporte para que los encabezados del CSV usen los KEY names en inglés.
        Esto simplifica el mapeo posterior en Pandas.

        Returns:
            bool: True si la configuración fue exitosa.
        """
        config_actual = await self.consultar_configuracion()
        if config_actual and config_actual.get("report_translation") == "en":
            logger.info("Configuración del reporte ya usa encabezados en inglés.")
            return True

        resultado = await self.actualizar_configuracion({"report_translation": "en"})
        if resultado:
            logger.info("Configuración actualizada: report_translation = 'en'")
            return True

        logger.warning(
            "No se pudo actualizar la configuración del reporte. "
            "Se intentará procesar el CSV con encabezados en español."
        )
        return False

    # ------------------------------------------------------------------
    # Métodos de creación y consulta de reportes
    # ------------------------------------------------------------------

    async def crear_reporte(self, begin_date: str, end_date: str) -> Optional[Dict[str, Any]]:
        """
        Solicita la creación de un Reporte de Liquidaciones para el rango de fechas indicado.

        Args:
            begin_date (str): Fecha de inicio en formato ISO 8601 UTC. Ej: "2026-04-19T00:00:00Z"
            end_date (str): Fecha de fin en formato ISO 8601 UTC. Ej: "2026-04-25T00:00:00Z"

        Returns:
            Dict con los datos del reporte creado (incluye 'file_name' y 'status') o None.
        """
        payload = {
            "begin_date": begin_date,
            "end_date": end_date,
        }
        logger.info(f"Creando reporte de liquidaciones: {begin_date} → {end_date}")
        respuesta = await self._post("/v1/account/release_report", payload)
        if respuesta:
            logger.info(
                f"Reporte creado. file_name='{respuesta.get('file_name')}' "
                f"status='{respuesta.get('status')}'"
            )
        return respuesta

    async def obtener_lista_reportes(self) -> List[Dict[str, Any]]:
        """
        Obtiene la lista de todos los reportes de liquidaciones generados.

        Returns:
            Lista de dicts con info de cada reporte (file_name, status, begin_date, end_date, etc.)
        """
        resultado = await self._get("/v1/account/release_report/list")
        if isinstance(resultado, list):
            return resultado
        return []

    async def esperar_reporte_disponible(
        self, ids_previos: set, max_espera_seg: int = 1200, intervalo_seg: int = 15
    ) -> Optional[str]:
        """
        Espera hasta que aparezca un reporte NUEVO en la lista (id no presente antes de la
        creación) con file_name disponible.

        Estrategia por snapshot: se compara la lista actual contra los IDs conocidos antes
        de llamar a crear_reporte. El primer reporte nuevo con file_name es el nuestro.
        Esto es más robusto que comparar timestamps y compatible con todas las versiones de Python.

        Args:
            ids_previos (set): Conjunto de IDs de reportes que existían ANTES de crear el nuevo.
            max_espera_seg (int): Tiempo máximo de espera en segundos (default: 1200 = 20 min).
            intervalo_seg (int): Intervalo entre consultas en segundos (default: 15).

        Returns:
            str: file_name del reporte nuevo cuando esté disponible, o None si se superó el tiempo.
        """
        logger.info(
            f"Esperando reporte nuevo en la lista "
            f"(IDs previos conocidos: {len(ids_previos)})..."
        )
        transcurrido = 0
        while transcurrido < max_espera_seg:
            lista = await self.obtener_lista_reportes()
            for reporte in lista:
                report_id = reporte.get("id")
                file_name = reporte.get("file_name")
                # Buscar un reporte cuyo id NO existía antes de la creación y ya tiene file_name
                if report_id not in ids_previos and file_name:
                    logger.info(
                        f"Reporte nuevo disponible. file_name='{file_name}' "
                        f"id={report_id} status={reporte.get('status')}"
                    )
                    return file_name

            logger.info(
                f"Reporte nuevo aún no disponible. Esperando {intervalo_seg}s... "
                f"({transcurrido}/{max_espera_seg}s)"
            )
            await asyncio.sleep(intervalo_seg)
            transcurrido += intervalo_seg

        logger.error(
            f"El reporte nuevo no estuvo disponible en {max_espera_seg} segundos."
        )
        return None

    async def descargar_reporte(self, file_name: str) -> Optional[bytes]:
        """
        Descarga el contenido binario (CSV) del reporte indicado.

        Args:
            file_name (str): Nombre del archivo del reporte (obtenido de crear_reporte).

        Returns:
            bytes: Contenido del CSV o None en caso de error.
        """
        logger.info(f"Descargando reporte: {file_name}")
        # El endpoint de descarga devuelve el CSV directamente (no JSON)
        session = await self._get_session()
        url = f"{MP_BASE_URL}/v1/account/release_report/{file_name}"
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    contenido = await response.read()
                    logger.info(
                        f"Reporte descargado exitosamente. Tamaño: {len(contenido)} bytes."
                    )
                    return contenido
                if response.status == 401:
                    logger.error("Error de autenticación (401) al descargar reporte.")
                    return None
                text = await response.text()
                logger.error(
                    f"Error HTTP {response.status} al descargar '{file_name}': {text}"
                )
                return None
        except asyncio.TimeoutError:
            logger.error(f"Timeout al descargar el reporte '{file_name}'.")
            return None
        except aiohttp.ClientError as e:
            logger.error(f"Error de conexión al descargar '{file_name}': {e}")
            return None

    async def close(self):
        """Cierra la sesión HTTP de forma explícita."""
        if self._session and not self._session.closed:
            await self._session.close()
