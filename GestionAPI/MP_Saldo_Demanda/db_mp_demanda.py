#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Operaciones de base de datos para el módulo MP_Saldo_Demanda.
Tablas:
  - MP_T_SALDO_DEMANDA         : resumen (1 fila por ejecución)
  - MP_T_SALDO_DEMANDA_DETALLE : todas las filas del CSV (N filas por ejecución)

Scripts de creación (ejecutar una sola vez en LAKER_SA, XL-TANGO):

    CREATE TABLE MP_T_SALDO_DEMANDA (
        ID                  INT IDENTITY(1,1) PRIMARY KEY,
        TIMESTAMP_CONSULTA  DATETIME2       NOT NULL,
        USER_ID             BIGINT          NOT NULL,
        CURRENCY_ID         VARCHAR(10)     NOT NULL,
        AVAILABLE_BALANCE   DECIMAL(18, 2)  NOT NULL,
        TOTAL_AMOUNT        DECIMAL(18, 2)  NOT NULL,
        FUENTE              VARCHAR(300)    NOT NULL,
        BEGIN_DATE          DATETIME2       NOT NULL,
        END_DATE            DATETIME2       NOT NULL,
        CREATED_AT          DATETIME2       NOT NULL DEFAULT GETDATE()
    );

    CREATE TABLE MP_T_SALDO_DEMANDA_DETALLE (
        ID                      INT IDENTITY(1,1) PRIMARY KEY,
        SYNC_TIMESTAMP          DATETIME2       NOT NULL,
        USER_ID                 BIGINT          NOT NULL,
        FILE_NAME               VARCHAR(300)    NOT NULL,
        FECHA_MOVIMIENTO        DATETIME2       NULL,
        SOURCE_ID               VARCHAR(100)    NULL,
        EXTERNAL_REFERENCE      VARCHAR(200)    NULL,
        RECORD_TYPE             VARCHAR(100)    NULL,
        DESCRIPTION             VARCHAR(500)    NULL,
        NET_CREDIT_AMOUNT       DECIMAL(18, 2)  NULL,
        NET_DEBIT_AMOUNT        DECIMAL(18, 2)  NULL,
        GROSS_AMOUNT            DECIMAL(18, 2)  NULL,
        MP_FEE_AMOUNT           DECIMAL(18, 2)  NULL,
        BALANCE_AMOUNT          DECIMAL(18, 2)  NULL,
        CURRENCY                VARCHAR(10)     NULL,
        PAYMENT_METHOD          VARCHAR(100)    NULL,
        CREATED_AT              DATETIME2       NOT NULL DEFAULT GETDATE()
    );
"""

import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, project_root)

import logging
import re
import pyodbc
from datetime import datetime
from typing import Dict, Any, List, Optional

from GestionAPI.common.credenciales import CENTRAL_LAKERS

logger = logging.getLogger("mp_saldo_demanda")

TABLE_NAME = "MP_T_SALDO_DEMANDA"
CONNECTION_TIMEOUT = 10

INSERT_SQL = f"""
INSERT INTO {TABLE_NAME} (
    TIMESTAMP_CONSULTA,
    USER_ID,
    CURRENCY_ID,
    AVAILABLE_BALANCE,
    TOTAL_AMOUNT,
    FUENTE,
    BEGIN_DATE,
    END_DATE
) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
"""


class MercadoPagoDemandaDB:
    """Persiste snapshots de saldo (demanda) en SQL Server."""

    def __init__(self):
        self._config = CENTRAL_LAKERS

    def _conectar(self) -> Optional[pyodbc.Connection]:
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
            conn.timeout = 30  # query execution timeout (segundos); 0 = sin límite
            return conn
        except pyodbc.Error as e:
            logger.error(f"Error de conexión a {self._config['server']}: {e}")
            return None

    def insertar_saldo(self, saldo: Dict[str, Any]) -> bool:
        """
        Inserta un snapshot en MP_T_SALDO_DEMANDA.

        Args:
            saldo: resultado de consultar_saldo_demanda() con los campos del reporte.

        Returns:
            True si el INSERT fue exitoso.
        """
        params = (
            saldo.get("timestamp"),
            saldo.get("user_id"),
            saldo.get("currency_id", "ARS"),
            saldo.get("available_balance"),
            saldo.get("total_amount"),
            saldo.get("fuente", ""),
            saldo.get("begin_date"),
            saldo.get("end_date"),
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
                f"Saldo guardado: user_id={saldo.get('user_id')} | "
                f"available={saldo.get('available_balance')} ARS | "
                f"período={saldo.get('begin_date')} → {saldo.get('end_date')}"
            )
            return True
        except Exception as e:
            logger.error(f"Error al insertar en {TABLE_NAME}: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()

    def insertar_detalle(self, filas: List[Dict], sync_timestamp: str, user_id: int, file_name: str) -> Dict[str, int]:
        """
        Inserta todas las filas del CSV en MP_T_SALDO_DEMANDA_DETALLE.

        Args:
            filas: lista de dicts del CSV (una por movimiento).
            sync_timestamp: timestamp del sync al que pertenecen.
            user_id: ID del usuario MP.
            file_name: nombre del archivo de reporte origen.

        Returns:
            Dict con {"insertados": int, "errores": int}
        """
        INSERT_DETALLE = """
INSERT INTO MP_T_SALDO_DEMANDA_DETALLE (
    SYNC_TIMESTAMP, USER_ID, FILE_NAME,
    FECHA_MOVIMIENTO, SOURCE_ID, EXTERNAL_REFERENCE,
    RECORD_TYPE, DESCRIPTION,
    NET_CREDIT_AMOUNT, NET_DEBIT_AMOUNT, GROSS_AMOUNT,
    MP_FEE_AMOUNT, BALANCE_AMOUNT, CURRENCY, PAYMENT_METHOD
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

        def _decimal(val):
            v = str(val or "").strip()
            if not v:
                return None
            try:
                return float(v.replace(",", "."))
            except ValueError:
                return None

        def _str(val, maxlen=None):
            s = str(val or "").strip() or None
            if s and maxlen:
                s = s[:maxlen]
            return s

        def _dt(val):
            """Convierte string ISO 8601 del CSV de MP a datetime Python (sin timezone)."""
            s = str(val or "").strip()
            if not s:
                return None
            # Eliminar offset de timezone (+HH:MM o -HH:MM) para compatibilidad con DATETIME2
            s = re.sub(r"[+-]\d{2}:\d{2}$", "", s)
            s = s.replace("T", " ")
            for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
                try:
                    return datetime.strptime(s, fmt)
                except ValueError:
                    continue
            return None

        conn = self._conectar()
        if not conn:
            logger.error("No se pudo conectar a la base de datos.")
            return {"insertados": 0, "errores": len(filas)}

        params_list = []
        for fila in filas:
            params_list.append((
                sync_timestamp,
                user_id,
                file_name,
                _dt(fila.get("DATE")),
                _str(fila.get("SOURCE_ID"), 100),
                _str(fila.get("EXTERNAL_REFERENCE"), 200),
                _str(fila.get("RECORD_TYPE"), 100),
                _str(fila.get("DESCRIPTION"), 500),
                _decimal(fila.get("NET_CREDIT_AMOUNT")),
                _decimal(fila.get("NET_DEBIT_AMOUNT")),
                _decimal(fila.get("GROSS_AMOUNT")),
                _decimal(fila.get("MP_FEE_AMOUNT")),
                _decimal(fila.get("BALANCE_AMOUNT")),
                _str(fila.get("CURRENCY"), 10),
                _str(fila.get("PAYMENT_METHOD"), 100),
            ))

        MAX_REINTENTOS = 3
        stats = {"insertados": 0, "errores": 0}

        for intento in range(1, MAX_REINTENTOS + 1):
            cursor = conn.cursor()
            try:
                cursor.executemany(INSERT_DETALLE, params_list)
                conn.commit()
                stats["insertados"] = len(params_list)
                logger.info(f"Detalle guardado: {stats['insertados']} filas | intento {intento}/{MAX_REINTENTOS}")
                cursor.close()
                break
            except Exception as e:
                conn.rollback()
                cursor.close()
                logger.warning(f"Intento {intento}/{MAX_REINTENTOS} fallido: {e}")
                if intento < MAX_REINTENTOS:
                    import time as _time
                    _time.sleep(5 * intento)  # backoff: 5s, 10s
                else:
                    logger.error(f"Detalle NO guardado tras {MAX_REINTENTOS} intentos. Rollback total.")
                    stats["errores"] = len(params_list)

        conn.close()

        return stats
