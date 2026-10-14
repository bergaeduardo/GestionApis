#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Operaciones de base de datos para el módulo de Movimientos InterBanking.
Maneja la escritura de movimientos en BI_T_MOVIMIENTOS_INTERBANKING.
"""

import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

import logging
from typing import Dict, List, Any
from datetime import datetime

from GestionAPI.common.conexion import Conexion
from GestionAPI.common.credenciales import INTERBANKING_DB
from GestionAPI.InterBanking.consultas_movimientos import (
    QRY_CREATE_TABLE_MOVIMIENTOS,
    QRY_MIGRATE_ID_TO_BIGINT,
    QRY_MERGE_MOVIMIENTO_DIA,
    QRY_OBTENER_CUENTAS,
    QRY_VERIFICAR_MOVIMIENTOS,
    QRY_LIMPIAR_MOVIMIENTOS_TEST,
)

logger = logging.getLogger(__name__)


class InterBankingMovimientosDB:
    """
    Operaciones de base de datos para Movimientos InterBanking.
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
        """Crea BI_T_MOVIMIENTOS_INTERBANKING si no existe y aplica migraciones."""
        try:
            conexion = self._get_connection()
            cursor = conexion.conectar()
            if cursor:
                cursor.execute(QRY_CREATE_TABLE_MOVIMIENTOS)
                conexion.connection.commit()
                # Migración: INT → BIGINT en ID_MOVIMIENTO (IDs reales superan INT max)
                cursor.execute(QRY_MIGRATE_ID_TO_BIGINT)
                conexion.connection.commit()
                cursor.close()
                conexion.connection.close()
                logger.info("Tabla BI_T_MOVIMIENTOS_INTERBANKING verificada/creada.")
                return True
            return False
        except Exception as e:
            logger.error(f"Error al crear/migrar tabla de movimientos: {e}")
            return False

    def obtener_cuentas(self) -> List[Dict[str, str]]:
        """
        Retorna la lista de cuentas conocidas desde BI_T_SALDOS_INTERBANKING.
        Cada elemento: {'nro_banco', 'nro_cuenta', 'tipo_cuenta', 'moneda'}.
        """
        try:
            conexion = self._get_connection()
            cursor = conexion.conectar()
            if not cursor:
                logger.error("No se pudo conectar para obtener cuentas.")
                return []
            cursor.execute(QRY_OBTENER_CUENTAS)
            rows = cursor.fetchall()
            cursor.close()
            conexion.connection.close()
            return [
                {
                    'nro_banco':   str(r[0]),
                    'nro_cuenta':  str(r[1]),
                    'tipo_cuenta': str(r[2]) if r[2] else 'CC',
                    'moneda':      str(r[3]) if r[3] else 'ARS',
                }
                for r in rows
            ]
        except Exception as e:
            logger.error(f"Error al obtener cuentas: {e}")
            return []

    def upsert_movimiento(self, mov: Dict[str, Any]) -> bool:
        """
        Inserta o actualiza un movimiento individual.
        Clave única: (NRO_BANCO, NRO_CUENTA, TIPO_CUENTA, MONEDA, TIPO_MOVIMIENTO, ID_MOVIMIENTO).

        Returns:
            True si la operación fue exitosa, False en caso de error.
        """
        id_movimiento = mov.get('id_movimiento')
        if id_movimiento is None:
            logger.debug(
                f"Movimiento sin id_movimiento, omitido: {mov.get('nro_cuenta')}"
            )
            return False

        def _parse_dt(val):
            if not val:
                return None
            if isinstance(val, str):
                try:
                    return datetime.fromisoformat(val.replace('Z', ''))
                except ValueError:
                    return None
            return val

        params = (
            mov.get('nro_banco'),
            mov.get('nro_cuenta'),
            mov.get('tipo_cuenta'),
            mov.get('moneda'),
            mov.get('tipo_movimiento'),
            id_movimiento,
            _parse_dt(mov.get('fecha_proceso')),
            mov.get('tipo_deb_cred'),
            mov.get('importe'),
            mov.get('nro_comprobante'),
            mov.get('cod_operacion_ib'),
            mov.get('cod_operacion_banco'),
            mov.get('desc_operacion_ib'),
            mov.get('desc_operacion_banco'),
            mov.get('cbu_cuenta'),
            mov.get('cod_depositante'),
            mov.get('desc_depositante'),
            mov.get('cuit_cliente'),
            mov.get('cod_agrupamiento_ib'),
            mov.get('sucursal'),
        )

        try:
            conexion = self._get_connection()
            cursor = conexion.conectar()
            if cursor:
                cursor.execute(QRY_MERGE_MOVIMIENTO_DIA, params)
                conexion.connection.commit()
                cursor.close()
                conexion.connection.close()
                return True
            return False
        except Exception as e:
            logger.error(
                f"Error en upsert_movimiento "
                f"({mov.get('nro_cuenta')} / {mov.get('tipo_movimiento')} / id:{id_movimiento}): {e}"
            )
            return False

    def upsert_movimientos_batch(self, movimientos: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Persiste una lista de movimientos usando upsert individual.

        Returns:
            dict con 'ok' y 'error' (contadores).
        """
        stats = {'ok': 0, 'error': 0}
        for mov in movimientos:
            if self.upsert_movimiento(mov):
                stats['ok'] += 1
            else:
                stats['error'] += 1
        return stats

    def verificar_movimientos_guardados(
        self, nro_banco: str, nro_cuenta: str, tipo_movimiento: str
    ) -> List:
        """Retorna movimientos guardados para una cuenta y tipo (para testing)."""
        try:
            conexion = self._get_connection()
            cursor = conexion.conectar()
            if cursor:
                cursor.execute(QRY_VERIFICAR_MOVIMIENTOS, (nro_banco, nro_cuenta, tipo_movimiento))
                resultados = cursor.fetchall()
                cursor.close()
                conexion.connection.close()
                return resultados
            return []
        except Exception as e:
            logger.error(f"Error al verificar movimientos: {e}")
            return []
