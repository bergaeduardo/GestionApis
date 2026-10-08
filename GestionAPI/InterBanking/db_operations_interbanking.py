#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Operaciones de base de datos para el módulo InterBanking.
Maneja la escritura de saldos bancarios en BI_T_SALDOS_INTERBANKING.
"""

import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from GestionAPI.common.conexion import Conexion
from GestionAPI.common.credenciales import INTERBANKING_DB
from GestionAPI.InterBanking.consultas import (
    QRY_CREATE_TABLE,
    QRY_MERGE_SALDO,
    QRY_VERIFICAR_SALDOS,
    QRY_LIMPIAR_DATOS_TEST,
)

logger = logging.getLogger(__name__)


class InterBankingDB:
    """
    Operaciones de base de datos para InterBanking.
    Apunta siempre a INTERBANKING_DB (configurable en credenciales.py).
    """

    def __init__(self):
        self._db_config = INTERBANKING_DB

    def _get_connection(self) -> Conexion:
        return Conexion(
            server=self._db_config['server'],
            database=self._db_config['database'],
            user=self._db_config['user'],
            password=self._db_config['password'],
        )

    def crear_tabla_si_no_existe(self) -> bool:
        """Crea BI_T_SALDOS_INTERBANKING si no existe."""
        try:
            conexion = self._get_connection()
            cursor = conexion.conectar()
            if cursor:
                cursor.execute(QRY_CREATE_TABLE)
                conexion.connection.commit()
                cursor.close()
                conexion.connection.close()
                logger.info("Tabla BI_T_SALDOS_INTERBANKING verificada/creada.")
                return True
            return False
        except Exception as e:
            logger.error(f"Error al crear tabla: {e}")
            return False

    def upsert_saldo(self, registro: Dict[str, Any]) -> bool:
        """
        Inserta o actualiza un registro de saldo diario.
        Clave única: (FECHA_OPERACION, NRO_BANCO, NRO_CUENTA).

        Args:
            registro: dict con campos del saldo (ver interbanking_api.extraer_registros)

        Returns:
            True si la operación fue exitosa.
        """
        fecha = registro.get('fecha_operacion')
        if not fecha:
            logger.debug(f"Cuenta sin histórico en el período, omitida: {registro.get('nro_cuenta')}")
            return None  # None = omitido (sin histórico), no es un error

        # Normalizar fecha a objeto date si viene como string
        if isinstance(fecha, str):
            try:
                fecha = datetime.fromisoformat(fecha.split('T')[0]).date()
            except ValueError:
                logger.error(f"Fecha inválida: {fecha}")
                return False

        params = (
            fecha,
            registro.get('nro_banco'),
            registro.get('nro_cuenta'),
            registro.get('tipo_cuenta'),
            registro.get('moneda'),
            registro.get('label_cuenta'),
            registro.get('nombre_cuenta'),
            registro.get('saldo_contable'),
            registro.get('saldo_operativo_inicial'),
            registro.get('saldo_operativo_actual'),
            registro.get('saldo_proyectado_24hs'),
            registro.get('saldo_proyectado_48hs'),
            registro.get('saldo_dia'),
            registro.get('total_debitos'),
            registro.get('total_creditos'),
        )

        try:
            conexion = self._get_connection()
            cursor = conexion.conectar()
            if cursor:
                cursor.execute(QRY_MERGE_SALDO, params)
                conexion.connection.commit()
                cursor.close()
                conexion.connection.close()
                return True
            return False
        except Exception as e:
            logger.error(f"Error en upsert_saldo ({registro.get('nro_cuenta')} / {fecha}): {e}")
            return False

    def upsert_saldos_batch(self, registros: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Persiste una lista de registros usando upsert individual.

        Returns:
            dict con 'ok' y 'error' (contadores).
        """
        stats = {'ok': 0, 'error': 0, 'sin_historico': 0}
        for reg in registros:
            resultado = self.upsert_saldo(reg)
            if resultado is True:
                stats['ok'] += 1
            elif resultado is None:
                stats['sin_historico'] += 1
            else:
                stats['error'] += 1
        return stats

    def verificar_saldos_guardados(
        self, fecha_inicio, fecha_fin
    ) -> List:
        """Retorna registros guardados en el rango de fechas (para testing)."""
        try:
            conexion = self._get_connection()
            cursor = conexion.conectar()
            if cursor:
                cursor.execute(QRY_VERIFICAR_SALDOS, (fecha_inicio, fecha_fin))
                resultados = cursor.fetchall()
                cursor.close()
                conexion.connection.close()
                return resultados
            return []
        except Exception as e:
            logger.error(f"Error al verificar saldos: {e}")
            return []
