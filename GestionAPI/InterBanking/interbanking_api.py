#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Cliente API para InterBanking
Maneja autenticación OAuth 2.0 (client_credentials) y consulta de saldos.
"""

import asyncio
import aiohttp
import logging
import time
from datetime import date as _date
from typing import Optional, Dict, Any, List

logger = logging.getLogger('interbanking_saldos')


class InterBankingAPIClient:
    """
    Cliente API para InterBanking.
    - Gestiona el ciclo de vida del token OAuth 2.0 (client_credentials).
    - Expone obtener_saldos() para consultar GET /accounts/balances.
    """

    def __init__(self, config: Dict[str, str]):
        """
        Args:
            config: diccionario INTERBANKING de credenciales.py
        """
        self._client_id = config['client_id']
        self._client_secret = config['client_secret']
        self._customer_id = config['customer_id']
        self._service_url = config['service_url']
        self._scope = config.get('scope', 'info-financiera')

        # Sandbox por defecto; producción cuando base_url_prod esté configurado
        if config.get('base_url_prod'):
            self._base_url = config['base_url_prod']
            self._token_url = config['token_url']
        else:
            self._base_url = config['base_url_sandbox']
            self._token_url = config['token_url_sandbox']

        self._session: Optional[aiohttp.ClientSession] = None
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0.0

    async def _get_session(self) -> aiohttp.ClientSession:
        if not self._session or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=90, connect=10, sock_read=60)
            connector = aiohttp.TCPConnector(limit=10, limit_per_host=2)
            self._session = aiohttp.ClientSession(timeout=timeout, connector=connector)
        return self._session

    async def _obtener_token(self) -> Optional[str]:
        """
        Solicita un token OAuth 2.0 usando client_credentials.
        Reutiliza el token mientras no haya expirado (buffer de 60 s).
        """
        if self._access_token and time.monotonic() < self._token_expires_at:
            return self._access_token

        payload = {
            'grant_type': 'client_credentials',
            'client_id': self._client_id,
            'client_secret': self._client_secret,
            'scope': self._scope,
        }
        # IBK requiere service_url como redirect_uri en el payload
        if self._service_url:
            payload['redirect_uri'] = self._service_url

        try:
            session = await self._get_session()
            async with session.post(self._token_url, data=payload) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.error(f"Error al obtener token IBK ({resp.status}): {text}")
                    return None
                data = await resp.json()
                self._access_token = data.get('access_token')
                expires_in = int(data.get('expires_in', 7200))
                self._token_expires_at = time.monotonic() + expires_in - 60
                logger.info(f"Token IBK obtenido. Expira en {expires_in}s.")
                return self._access_token
        except Exception as e:
            logger.error(f"Excepción al obtener token IBK: {e}")
            return None

    async def obtener_saldos(
        self,
        date_since: Optional[str] = None,
        date_until: Optional[str] = None,
        account_numbers: Optional[List[str]] = None,
        bank_numbers: Optional[List[str]] = None,
        currency: Optional[str] = None,
        account_type: Optional[str] = None,
        limit: int = 64,
        max_retries: int = 3,
    ) -> Optional[Dict[str, Any]]:
        """
        Llama a GET /accounts/balances.

        La API acepta hasta 180 días de historia en rangos de hasta 60 días por llamada.
        Usar sync_saldos_interbanking.py para rangos mayores (pagina automáticamente).

        Args:
            date_since: Fecha inicio yyyy-mm-dd (default: hoy - 7 días)
            date_until:  Fecha fin yyyy-mm-dd (default: hoy - 1 día)
            account_numbers: Lista de números de cuenta (opcional)
            bank_numbers:    Lista de códigos BCRA de banco (opcional)
            currency:        'ARS' | 'USD' (default: ARS)
            account_type:    'CC' | 'CA' (default: CC)
            limit:           Registros por página (default: 64, max recomendado: 64)
            max_retries:     Reintentos ante errores 5xx / timeout

        Returns:
            Dict con la respuesta JSON o None ante error.
        """
        token = await self._obtener_token()
        if not token:
            logger.error("No se pudo obtener token. Abortando consulta de saldos.")
            return None

        params: Dict[str, Any] = {'customer-id': self._customer_id, 'limit': str(limit)}
        if date_since:
            params['date-since'] = date_since
        if date_until:
            params['date-until'] = date_until
        if account_numbers:
            params['account-number'] = account_numbers
        if bank_numbers:
            params['bank-number'] = bank_numbers
        if currency:
            params['currency'] = currency
        if account_type:
            params['account-type'] = account_type

        url = f"{self._base_url}/accounts/balances"
        headers = {
            'Authorization': f'Bearer {token}',
            'client_id': self._client_id,   # apiKey requerido por IBK además del Bearer
            'Accept': 'application/json',
        }

        for intento in range(max_retries):
            try:
                session = await self._get_session()
                async with session.get(url, headers=headers, params=params) as resp:
                    if resp.status == 200:
                        return await resp.json()

                    if resp.status == 401:
                        # Token expirado prematuramente — forzar renovación
                        logger.warning("Token IBK rechazado (401). Forzando renovación.")
                        self._access_token = None
                        token = await self._obtener_token()
                        if not token:
                            return None
                        headers['Authorization'] = f'Bearer {token}'
                        continue

                    if resp.status == 400:
                        text = await resp.text()
                        logger.error(f"Parámetros inválidos en /accounts/balances (400): {text}")
                        return None

                    if resp.status == 404:
                        logger.warning("No se encontraron saldos (404).")
                        return None

                    if resp.status >= 500 and intento < max_retries - 1:
                        await asyncio.sleep(2 ** intento)
                        continue

                    text = await resp.text()
                    logger.error(f"Error HTTP {resp.status} en /accounts/balances: {text}")
                    return None

            except asyncio.TimeoutError:
                if intento < max_retries - 1:
                    await asyncio.sleep(2 ** intento)
                else:
                    logger.error(f"Timeout en /accounts/balances tras {max_retries} intentos.")
                    return None

            except aiohttp.ClientError as e:
                if intento < max_retries - 1:
                    await asyncio.sleep(2 ** intento)
                else:
                    logger.error(f"Error de conexión: {e}")
                    return None

            except Exception as e:
                logger.error(f"Error inesperado: {e}")
                return None

        return None

    def extraer_registros(self, respuesta: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Aplana la respuesta de /accounts/balances en una lista de registros
        listos para persistir en SQL Server.

        Cada registro representa una fila de historical_balances enriquecida
        con los datos de la cuenta y los saldos corrientes.

        Returns:
            Lista de dicts con las claves:
            fecha_operacion, nro_banco, nro_cuenta, tipo_cuenta, moneda,
            label_cuenta, nombre_cuenta, saldo_contable, saldo_operativo_inicial,
            saldo_operativo_actual, saldo_proyectado_24hs, saldo_proyectado_48hs,
            saldo_dia, total_debitos, total_creditos
        """
        registros = []
        accounts = respuesta.get('accounts', [])

        for account in accounts:
            balances = account.get('balances') or {}
            base = {
                'nro_banco': account.get('bank_number'),
                'nro_cuenta': account.get('account_number'),
                'tipo_cuenta': account.get('account_type'),
                'moneda': account.get('currency'),
                'label_cuenta': account.get('account_label'),
                'nombre_cuenta': account.get('account_name'),
                'saldo_contable': balances.get('countable_balance'),
                'saldo_operativo_inicial': balances.get('initial_operating_balance'),
                'saldo_operativo_actual': balances.get('current_operating_balance'),
                'saldo_proyectado_24hs': balances.get('projected_balance_24hs'),
                'saldo_proyectado_48hs': balances.get('projected_balance_48hs'),
            }

            # Registro intradiario: saldo actual del día en curso.
            # saldo_dia / débitos / créditos son datos de cierre; se actualiza
            # con cada ejecución (MERGE por clave) a medida que avanza el día.
            row_date = account.get('row_date') or account.get('origin')
            if row_date:
                try:
                    fecha_hoy = row_date.split('T')[0]
                except Exception:
                    fecha_hoy = str(_date.today())
            else:
                fecha_hoy = str(_date.today())

            registro_hoy = dict(base)
            registro_hoy['fecha_operacion'] = fecha_hoy
            registro_hoy['saldo_dia'] = None
            registro_hoy['total_debitos'] = None
            registro_hoy['total_creditos'] = None
            registros.append(registro_hoy)

            historical = account.get('historical_balances') or []
            for hb in historical:
                if not hb:
                    continue
                registro = dict(base)
                registro['fecha_operacion'] = hb.get('operation_date')
                registro['saldo_dia'] = hb.get('day_balance')
                registro['total_debitos'] = hb.get('total_debits')
                registro['total_creditos'] = hb.get('total_credits')
                registros.append(registro)

        return registros

    async def obtener_extractos(
        self,
        account_number: str,
        bank_number: str,
        date_since: str,
        date_until: str,
        account_type: str = 'CC',
        currency: str = 'ARS',
        page: int = 0,
        limit: int = 100,
        max_retries: int = 3,
    ) -> Optional[Dict[str, Any]]:
        """
        Llama a GET /accounts/{account-number}/statements.

        Historial máximo: 180 días en rangos de hasta 60 días por consulta.
        Soporta paginación: iterar incrementando `page` mientras haya más filas.

        Args:
            account_number: Número de cuenta bancaria.
            bank_number:    Código BCRA de 3 dígitos (ej: '007').
            date_since:     Fecha inicio yyyy-mm-dd (requerido por la API).
            date_until:     Fecha fin yyyy-mm-dd (requerido por la API).
            account_type:   'CC' | 'CA' (default: 'CC').
            currency:       'ARS' | 'USD' (default: 'ARS').
            page:           Página a solicitar (default: 0).
            limit:          Registros por página (default: 100).
            max_retries:    Reintentos ante errores 5xx / timeout.

        Returns:
            Dict con la respuesta JSON o None ante error.
        """
        token = await self._obtener_token()
        if not token:
            logger.error("No se pudo obtener token. Abortando consulta de extractos.")
            return None

        params: Dict[str, Any] = {
            'customer-id': self._customer_id,
            'bank-number': bank_number,
            'date-since': date_since,
            'date-until': date_until,
            'account-type': account_type,
            'currency': currency,
            'page': str(page),
            'limit': str(limit),
        }

        url = f"{self._base_url}/accounts/{account_number}/statements"
        headers = {
            'Authorization': f'Bearer {token}',
            'client_id': self._client_id,
            'Accept': 'application/json',
        }

        for intento in range(max_retries):
            try:
                session = await self._get_session()
                async with session.get(url, headers=headers, params=params) as resp:
                    if resp.status == 200:
                        return await resp.json()

                    if resp.status == 401:
                        logger.warning("Token IBK rechazado (401). Forzando renovación.")
                        self._access_token = None
                        token = await self._obtener_token()
                        if not token:
                            return None
                        headers['Authorization'] = f'Bearer {token}'
                        continue

                    if resp.status == 404:
                        logger.warning(
                            f"No se encontraron extractos para cuenta {account_number} "
                            f"banco {bank_number} (404)."
                        )
                        return None

                    if resp.status == 400:
                        text = await resp.text()
                        logger.error(
                            f"Parámetros inválidos en /accounts/{account_number}/statements "
                            f"(400): {text}"
                        )
                        return None

                    if resp.status >= 500 and intento < max_retries - 1:
                        await asyncio.sleep(2 ** intento)
                        continue

                    text = await resp.text()
                    logger.error(
                        f"Error HTTP {resp.status} en /accounts/{account_number}/statements: {text}"
                    )
                    return None

            except asyncio.TimeoutError:
                if intento < max_retries - 1:
                    await asyncio.sleep(2 ** intento)
                else:
                    logger.error(
                        f"Timeout en /accounts/{account_number}/statements "
                        f"tras {max_retries} intentos."
                    )
                    return None

            except aiohttp.ClientError as e:
                if intento < max_retries - 1:
                    await asyncio.sleep(2 ** intento)
                else:
                    logger.error(f"Error de conexión en extractos ({account_number}): {e}")
                    return None

            except Exception as e:
                logger.error(f"Error inesperado en extractos ({account_number}): {e}")
                return None

        return None

    def extraer_movimientos(
        self,
        respuesta: Dict[str, Any],
        bank_number: str,
        account_number: str,
        account_type: str,
        currency: str,
    ) -> List[Dict[str, Any]]:
        """
        Aplana la respuesta de /accounts/{account-number}/statements en una lista
        de movimientos individuales listos para persistir en SQL Server.

        Jerarquía: statements[] (por día) → movement_detail[] (por transacción).

        Returns:
            Lista de dicts con las claves:
            fecha_operacion, nro_banco, nro_cuenta, tipo_cuenta, moneda,
            nro_extracto, saldo_inicial, saldo_final, deb_total_dia, cred_total_dia,
            nro_correlativo, nro_comprobante, fecha_movimiento, fecha_valor,
            tipo_mov, importe, cod_operacion_ib, cod_operacion_banco,
            desc_operacion, desc_depositante, cuit_cliente, sucursal
        """
        movimientos = []
        statements = respuesta.get('statements') or []

        for statement in statements:
            if not statement:
                continue

            # Datos del encabezado diario (se repiten en cada movimiento del día)
            fecha_op = statement.get('operation_date')
            nro_extracto = statement.get('statement_number')
            saldo_inicial = statement.get('opening_balance')
            saldo_final = statement.get('ending_balance')
            deb_total = statement.get('debits_total_amount')
            cred_total = statement.get('credits_total_amount')

            for mov in (statement.get('movement_detail') or []):
                if not mov:
                    continue

                nro_correlativo = mov.get('correlative_number')
                if nro_correlativo is None:
                    logger.debug(
                        f"Movimiento sin correlativo en {account_number} / {fecha_op}, omitido."
                    )
                    continue

                movimientos.append({
                    'fecha_operacion':    fecha_op,
                    'nro_banco':          bank_number,
                    'nro_cuenta':         account_number,
                    'tipo_cuenta':        account_type,
                    'moneda':             currency,
                    'nro_extracto':       nro_extracto,
                    'saldo_inicial':      saldo_inicial,
                    'saldo_final':        saldo_final,
                    'deb_total_dia':      deb_total,
                    'cred_total_dia':     cred_total,
                    'nro_correlativo':    nro_correlativo,
                    'nro_comprobante':    mov.get('voucher_number'),
                    'fecha_movimiento':   mov.get('movement_date'),
                    'fecha_valor':        mov.get('value_date'),
                    'tipo_mov':           mov.get('debit_credit_type'),
                    'importe':            mov.get('amount'),
                    'cod_operacion_ib':   mov.get('operation_code_ib'),
                    'cod_operacion_banco': mov.get('operation_code_bank'),
                    'desc_operacion':     mov.get('code_description_bank'),
                    'desc_depositante':   mov.get('depositor_description'),
                    'cuit_cliente':       mov.get('customer_cuit'),
                    'sucursal':           mov.get('branch_office_activity'),
                })

        return movimientos

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
