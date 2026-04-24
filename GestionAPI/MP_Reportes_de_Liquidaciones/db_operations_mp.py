#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Operaciones de base de datos para el módulo MP-Reportes_de_Liquidaciones.
Maneja el upsert (MERGE) de registros en la tabla MP_T_REPORTE_DE_LIQUIDACIONES.
"""

import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, project_root)

import logging
import pandas as pd
from typing import Optional

from GestionAPI.common.conexion import Conexion
from GestionAPI.common.credenciales import CENTRAL_LAKERS
from GestionAPI.MP_Reportes_de_Liquidaciones.consultas import (
    TABLE_NAME,
    MERGE_KEY_COLUMNS,
    CSV_TO_DB_COLUMNS,
)

logger = logging.getLogger("mp_liquidaciones")


class MercadoPagoDB:
    """
    Clase para manejar las operaciones de base de datos del módulo MP-Reportes_de_Liquidaciones.
    Utiliza la base LAKER_SA en el servidor XL-TANGO.
    """

    def __init__(self):
        self._config = CENTRAL_LAKERS

    def _get_connection(self) -> Conexion:
        return Conexion(
            server=self._config["server"],
            database=self._config["database"],
            user=self._config["user"],
            password=self._config["password"],
        )

    def _build_merge_query(self, db_columns: list) -> str:
        """
        Construye dinámicamente la sentencia MERGE T-SQL para las columnas presentes en el DataFrame.

        Args:
            db_columns (list): Lista de nombres de columnas DB a incluir en el MERGE.

        Returns:
            str: Sentencia MERGE parametrizada con placeholders '?'.
        """
        # Columnas non-key para UPDATE
        non_key_cols = [c for c in db_columns if c not in MERGE_KEY_COLUMNS]

        placeholders = ", ".join(["?" for _ in db_columns])
        source_alias = ", ".join(db_columns)

        # Condición ON: manejo de NULL con ISNULL para las 4 claves
        on_conditions = " AND ".join(
            [
                f"ISNULL(target.{c}, '') = ISNULL(source.{c}, '')"
                for c in MERGE_KEY_COLUMNS
                if c in db_columns
            ]
        )

        # SET del UPDATE
        update_set = ",\n        ".join(
            [f"target.{c} = source.{c}" for c in non_key_cols]
        )

        # Columnas y valores del INSERT
        insert_cols = ", ".join(db_columns)
        insert_vals = ", ".join([f"source.{c}" for c in db_columns])

        query = f"""
MERGE INTO {TABLE_NAME} AS target
USING (
    SELECT {placeholders}
) AS source ({source_alias})
ON (
    {on_conditions}
)
WHEN MATCHED THEN
    UPDATE SET
        {update_set},
        CREATED_AT = GETDATE()
WHEN NOT MATCHED THEN
    INSERT ({insert_cols}, CREATED_AT)
    VALUES ({insert_vals}, GETDATE());
"""
        return query

    def upsert_liquidaciones(self, df: pd.DataFrame) -> dict:
        """
        Inserta o actualiza los registros del DataFrame en MP_T_REPORTE_DE_LIQUIDACIONES.
        Para cada fila ejecuta un MERGE: si la clave (FECHA_LIQUIDACION, SOURCE_ID,
        RECORD_TYPE, DESCRIPTION) ya existe, actualiza; si no, inserta.

        Args:
            df (pd.DataFrame): DataFrame con columnas en nombres de DB (ya renombradas).

        Returns:
            dict: {"insertados": int, "actualizados_aprox": int, "errores": int}
        """
        if df.empty:
            logger.warning("DataFrame vacío. No hay registros para procesar.")
            return {"insertados": 0, "actualizados_aprox": 0, "errores": 0}

        # Filtrar solo las columnas que existen en el CSV_TO_DB_COLUMNS (columnas DB válidas)
        columnas_db_validas = list(CSV_TO_DB_COLUMNS.values())
        df_cols = [c for c in df.columns if c in columnas_db_validas]

        if not df_cols:
            logger.error("El DataFrame no tiene columnas reconocibles para el MERGE.")
            return {"insertados": 0, "actualizados_aprox": 0, "errores": 0}

        merge_query = self._build_merge_query(df_cols)
        df_subset = df[df_cols]

        stats = {"insertados": 0, "actualizados_aprox": 0, "errores": 0}

        conexion = self._get_connection()
        cursor = conexion.conectar()
        if not cursor:
            logger.error("No se pudo obtener cursor para la base de datos.")
            return stats

        try:
            for idx, row in df_subset.iterrows():
                params = [
                    None if (pd.isna(v) if not isinstance(v, str) else v == "") else v
                    for v in row.tolist()
                ]
                try:
                    cursor.execute(merge_query, params)
                    stats["insertados"] += 1  # aproximado (MERGE no diferencia fácilmente)
                except Exception as e:
                    logger.error(f"Error en MERGE fila {idx}: {e}")
                    stats["errores"] += 1

            conexion.connection.commit()
            logger.info(
                f"MERGE completado. Filas procesadas: {stats['insertados']} | "
                f"Errores: {stats['errores']}"
            )
        except Exception as e:
            logger.error(f"Error crítico durante el proceso de upsert: {e}")
            if conexion.connection:
                conexion.connection.rollback()
        finally:
            cursor.close()
            conexion.connection.close()

        return stats
