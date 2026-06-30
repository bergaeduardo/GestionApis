"""
Consultas SQL para el módulo HasarServicios
Contiene las queries para obtener configuración y sincronizar datos de conteo de personas
"""

# Query para obtener configuración de sucursales activas desde la tabla de configuración
QRY_OBTENER_CONFIG = """
SELECT 
    NUMERO_SUCURSAL,
    NOMBRE_DASHBOARD,
    API,
    Token,
    DATA_BASE,
    ACTIVO
FROM EB_BilcCamdata_pdv
WHERE ACTIVO = 1
ORDER BY NUMERO_SUCURSAL, NOMBRE_DASHBOARD
"""

# Query para obtener el total de registros (activos e inactivos) para logging
QRY_CONTAR_TOTAL = """
SELECT 
    SUM(CASE WHEN ACTIVO = 1 THEN 1 ELSE 0 END) AS Activos,
    SUM(CASE WHEN ACTIVO = 0 THEN 1 ELSE 0 END) AS Inactivos,
    COUNT(*) AS Total
FROM EB_BilcCamdata_pdv
"""

# Template de MERGE para insertar o actualizar datos diarios en BI_T_INGRESOS_SUCURSALES
# La condición AND target.FECHA_HORA IS NULL es necesaria para no colisionar con
# registros horarios del mismo día y sucursal.
QRY_MERGE_INGRESOS = """
MERGE INTO BI_T_INGRESOS_SUCURSALES AS target
USING (
    SELECT
        ? AS FECHA,
        ? AS NRO_SUCURS,
        ? AS INGRESOS,
        ? AS MERODEO
) AS source
ON target.FECHA = source.FECHA AND target.NRO_SUCURS = source.NRO_SUCURS AND target.FECHA_HORA IS NULL
WHEN MATCHED THEN
    UPDATE SET
        INGRESOS = source.INGRESOS,
        MERODEO = source.MERODEO,
        CREATED_AT = GETDATE()
WHEN NOT MATCHED THEN
    INSERT (FECHA, NRO_SUCURS, INGRESOS, MERODEO, CREATED_AT)
    VALUES (source.FECHA, source.NRO_SUCURS, source.INGRESOS, source.MERODEO, GETDATE());
"""

# Template de MERGE para insertar o actualizar datos HORARIOS en BI_T_INGRESOS_SUCURSALES
# Clave única: (FECHA_HORA, NRO_SUCURS)
QRY_MERGE_INGRESOS_HORA = """
MERGE INTO BI_T_INGRESOS_SUCURSALES AS target
USING (
    SELECT
        ? AS FECHA,
        ? AS FECHA_HORA,
        ? AS NRO_SUCURS,
        ? AS INGRESOS,
        ? AS MERODEO
) AS source
ON target.FECHA_HORA = source.FECHA_HORA AND target.NRO_SUCURS = source.NRO_SUCURS
WHEN MATCHED THEN
    UPDATE SET
        INGRESOS = source.INGRESOS,
        MERODEO = source.MERODEO,
        CREATED_AT = GETDATE()
WHEN NOT MATCHED THEN
    INSERT (FECHA, FECHA_HORA, NRO_SUCURS, INGRESOS, MERODEO, CREATED_AT)
    VALUES (source.FECHA, source.FECHA_HORA, source.NRO_SUCURS, source.INGRESOS, source.MERODEO, GETDATE());
"""

# Query para verificar datos existentes en un rango de fechas (útil para testing)
QRY_VERIFICAR_DATOS = """
SELECT 
    FECHA,
    NRO_SUCURS,
    INGRESOS,
    MERODEO,
    CREATED_AT
FROM BI_T_INGRESOS_SUCURSALES
WHERE FECHA >= ? AND FECHA <= ?
ORDER BY FECHA DESC, NRO_SUCURS
"""

# Query para limpiar datos de prueba (solo para testing)
QRY_LIMPIAR_DATOS_TEST = """
DELETE FROM BI_T_INGRESOS_SUCURSALES
WHERE NRO_SUCURS = ? AND FECHA >= ?
"""
