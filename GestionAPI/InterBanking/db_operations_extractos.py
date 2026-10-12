#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Operaciones de base de datos para el módulo de Extractos InterBanking.
Maneja la escritura de movimientos en BI_T_EXTRACTOS_INTERBANKING.
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
from GestionAPI.InterBanking.consultas_extractos import (
    QRY_CREATE_TABLE_EXTRACTOS,
    QRY_MERGE_MOVIMIENTO,
    QRY_OBTENER_CUENTAS,
    QRY_VERIFICAR_EXTRACTOS,
    QRY_LIMPIAR_EXTRACTOS_TEST,
)

logger = logging.getLogger(__name__)


class InterBankingExtractosDB:
    """
    Operaciones de base de datos para Extractos InterBanking.
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
        """Crea BI_T_EXTRACTOS_INTERBANKING si no existe."""
        try:
            conexion = self._get_connection()
            cursor = conexion.conectar()
            if cursor:
                cursor.execute(QRY_CREATE_TABLE_EXTRACTOS)
                conexion.connection.commit()
                cursor.close()
                conexion.connection.close()
                logger.info("Tabla BI_T_EXTRACTOS_INTERBANKING verificada/creada.")
                return True
            return False
        except Exception as e:
            logger.error(f"Error al crear tabla de extractos: {e}")
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
        Clave única: (NRO_BANCO, NRO_CUENTA, FECHA_OPERACION, NRO_CORRELATIVO).

        Returns:
            True si la operación fue exitosa, False en caso de error.
        """
        fecha = mov.get('fecha_operacion')
        nro_correlativo = mov.get('nro_correlativo')

        if not fecha or nro_correlativo is None:
            logger.debug(
                f"Movimiento sin fecha o correlativo, omitido: "
                f"{mov.get('nro_cuenta')} / {fecha}"
            )
            return False

        if isinstance(fecha, str):
            try:
                fecha = datetime.fromisoformat(fecha.split('T')[0]).date()
            except ValueError:
                logger.error(f"Fecha inválida en extracto: {fecha}")
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
            fecha,
            mov.get('nro_banco'),
            mov.get('nro_cuenta'),
            mov.get('tipo_cuenta'),
            mov.get('moneda'),
            mov.get('nro_extracto'),
            mov.get('saldo_inicial'),
            mov.get('saldo_final'),
            mov.get('deb_total_dia'),
            mov.get('cred_total_dia'),
            nro_correlativo,
            mov.get('nro_comprobante'),
            _parse_dt(mov.get('fecha_movimiento')),
            _parse_dt(mov.get('fecha_valor')),
            mov.get('tipo_mov'),
            mov.get('importe'),
            mov.get('cod_operacion_ib'),
            mov.get('cod_operacion_banco'),
            mov.get('desc_operacion'),
            mov.get('desc_depositante'),
            mov.get('cuit_cliente'),
            mov.get('sucursal'),
        )

        try:
            conexion = self._get_connection()
            cursor = conexion.conectar()
            if cursor:
                cursor.execute(QRY_MERGE_MOVIMIENTO, params)
                conexion.connection.commit()
                cursor.close()
                conexion.connection.close()
                return True
            return False
        except Exception as e:
            logger.error(
                f"Error en upsert_movimiento "
                f"({mov.get('nro_cuenta')} / {fecha} / corr:{nro_correlativo}): {e}"
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

    def verificar_movimientos_guardados(self, fecha_inicio, fecha_fin) -> List:
        """Retorna movimientos guardados en el rango (para testing)."""
        try:
            conexion = self._get_connection()
            cursor = conexion.conectar()
            if cursor:
                cursor.execute(QRY_VERIFICAR_EXTRACTOS, (fecha_inicio, fecha_fin))
                resultados = cursor.fetchall()
                cursor.close()
                conexion.connection.close()
                return resultados
            return []
        except Exception as e:
            logger.error(f"Error al verificar extractos: {e}")
            return []
