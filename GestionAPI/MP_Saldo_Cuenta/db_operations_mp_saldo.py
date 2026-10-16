#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Operaciones de base de datos para el módulo MP_Saldo_Cuenta.
Guarda cada snapshot de saldo en la tabla MP_T_SALDO_CUENTA (LAKER_SA, XL-TANGO).

Script de creación de tabla (ejecutar una sola vez en SQL Server):

    CREATE TABLE MP_T_SALDO_CUENTA (
        ID                   INT IDENTITY(1,1) PRIMARY KEY,
        TIMESTAMP_CONSULTA   DATETIME2        NOT NULL,
        USER_ID              BIGINT           NOT NULL,
        CURRENCY_ID          VARCHAR(10)      NOT NULL,
        AVAILABLE_BALANCE    DECIMAL(18, 2)   NOT NULL,
        UNAVAILABLE_BALANCE  DECIMAL(18, 2)   NULL,
        TOTAL_AMOUNT         DECIMAL(18, 2)   NOT NULL,
        FUENTE               VARCHAR(200)     NOT NULL,
        FECHA_CORTE_REPORTE  DATETIME2        NULL,
        CREATED_AT           DATETIME2        NOT NULL DEFAULT GETDATE()
    );
"""

import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, project_root)

import logging
import pyodbc
from typing import Dict, Any, Optional

from GestionAPI.common.credenciales import CENTRAL_LAKERS

logger = logging.getLogger("mp_saldo_cuenta")

TABLE_NAME = "MP_T_SALDO_CUENTA"
CONNECTION_TIMEOUT = 10  # segundos

INSERT_SQL = f"""
INSERT INTO {TABLE_NAME} (
    TIMESTAMP_CONSULTA,
    USER_ID,
    CURRENCY_ID,
    AVAILABLE_BALANCE,
    UNAVAILABLE_BALANCE,
    TOTAL_AMOUNT,
    FUENTE,
    FECHA_CORTE_REPORTE
) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
"""


class MercadoPagoSaldoDB:
    """Guarda snapshots de saldo de Mercado Pago en SQL Server."""

    def __init__(self):
        self._config = CENTRAL_LAKERS

    def _conectar(self) -> Optional[pyodbc.Connection]:
        """Abre conexión pyodbc con timeout explícito para no quedarse colgado."""
        conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={self._config['server']};"
            f"DATABASE={self._config['database']};"
            f"UID={self._config['user']};"
            f"PWD={self._config['password']};"
            f"Connection Timeout={CONNECTION_TIMEOUT};"
        )
        try:
            conn = pyodbc.connect(conn_str)
            conn.timeout = 30  # query execution timeout (segundos)
            return conn
        except pyodbc.Error as e:
            logger.error(f"Error de conexión a SQL Server ({self._config['server']}): {e}")
            return None

    def insertar_saldo(self, saldo: Dict[str, Any]) -> bool:
        """
        Inserta un snapshot de saldo en MP_T_SALDO_CUENTA.

        Args:
            saldo (dict): Resultado de consultar_saldo() con campos timestamp, user_id,
                          currency_id, available_balance, unavailable_balance,
                          total_amount, fuente, fecha_corte_reporte (opcional).

        Returns:
            bool: True si el INSERT fue exitoso.
        """
        params = (
            saldo.get("timestamp"),
            saldo.get("user_id"),
            saldo.get("currency_id", "ARS"),
            saldo.get("available_balance"),
            saldo.get("unavailable_balance"),      # puede ser None
            saldo.get("total_amount"),
            saldo.get("fuente", ""),
            saldo.get("fecha_corte_reporte"),       # puede ser None
        )

        conn = self._conectar()
        if not conn:
            logger.error("No se pudo conectar a la base de datos.")
            return False

        cursor = conn.cursor()
        try:
            cursor.execute(INSERT_SQL, params)
            conn.commit()
            logger.info(
                f"Saldo guardado en BD: user_id={saldo.get('user_id')} | "
                f"available={saldo.get('available_balance')} ARS | "
                f"fuente={saldo.get('fuente')}"
            )
            return True
        except Exception as e:
            logger.error(f"Error al insertar saldo en {TABLE_NAME}: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()

    def ultimo_saldo(self) -> Optional[Dict[str, Any]]:
        """
        Devuelve el último saldo registrado en la tabla.

        Returns:
            dict con los campos del último registro, o None si la tabla está vacía.
        """
        sql = f"""
SELECT TOP 1
    TIMESTAMP_CONSULTA, USER_ID, CURRENCY_ID,
    AVAILABLE_BALANCE, UNAVAILABLE_BALANCE, TOTAL_AMOUNT,
    FUENTE, FECHA_CORTE_REPORTE, CREATED_AT
FROM {TABLE_NAME}
ORDER BY ID DESC
"""
        conn = self._conectar()
        if not conn:
            return None

        cursor = conn.cursor()
        try:
            cursor.execute(sql)
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "timestamp": str(row[0]),
                "user_id": row[1],
                "currency_id": row[2],
                "available_balance": float(row[3]) if row[3] is not None else None,
                "unavailable_balance": float(row[4]) if row[4] is not None else None,
                "total_amount": float(row[5]) if row[5] is not None else None,
                "fuente": row[6],
                "fecha_corte_reporte": str(row[7]) if row[7] else None,
                "created_at": str(row[8]),
            }
        except Exception as e:
            logger.error(f"Error al consultar {TABLE_NAME}: {e}")
            return None
        finally:
            cursor.close()
            conn.close()
