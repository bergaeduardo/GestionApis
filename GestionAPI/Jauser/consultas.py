#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Consultas SQL para el módulo Jauser

# Consulta para verificar la estructura de la tabla
QRY_VERIFICAR_TABLA = """
SELECT 
    COLUMN_NAME,
    DATA_TYPE,
    IS_NULLABLE,
    COLUMN_DEFAULT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'jauser_stock'
ORDER BY ORDINAL_POSITION
"""

# Consulta para obtener todo el stock
QRY_OBTENER_STOCK = """
SELECT 
    piezas,
    descripcion,
    codigo,
    model,
    tipo_deposito,
    fecha_actualizacion
FROM jauser_stock
ORDER BY tipo_deposito, codigo
"""

# Consulta para obtener stock por tipo de depósito
QRY_OBTENER_STOCK_POR_TIPO = """
SELECT 
    piezas,
    descripcion,
    codigo,
    model,
    fecha_actualizacion
FROM jauser_stock
WHERE tipo_deposito = ?
ORDER BY codigo
"""

# Consulta para buscar stock por código
QRY_BUSCAR_POR_CODIGO = """
SELECT 
    piezas,
    descripcion,
    codigo,
    model,
    tipo_deposito,
    fecha_actualizacion
FROM jauser_stock
WHERE codigo LIKE ?
ORDER BY tipo_deposito
"""
