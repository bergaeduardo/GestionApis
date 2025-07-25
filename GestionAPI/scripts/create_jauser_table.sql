-- Script SQL para crear la tabla de stock de Jauser
-- Ejecutar este script en tu base de datos SQL Server

USE [nombre_de_tu_base_de_datos]
GO

-- Crear tabla de stock de Jauser
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='jauser_stock' AND xtype='U')
BEGIN
    CREATE TABLE jauser_stock (
        id INT IDENTITY(1,1) PRIMARY KEY,
        piezas VARCHAR(50),
        descripcion VARCHAR(255),
        codigo VARCHAR(100),
        model VARCHAR(255),
        tipo_deposito VARCHAR(20), -- 'NACIONAL' o 'FISCAL'
        fecha_actualizacion DATETIME DEFAULT GETDATE()
    );
    
    -- Crear índices para mejorar el rendimiento
    CREATE INDEX idx_jauser_stock_codigo ON jauser_stock(codigo);
    CREATE INDEX idx_jauser_stock_tipo ON jauser_stock(tipo_deposito);
    CREATE INDEX idx_jauser_stock_fecha ON jauser_stock(fecha_actualizacion);
END
GO

-- Verificar la creación de la tabla
SELECT 
    TABLE_NAME,
    COLUMN_NAME,
    DATA_TYPE,
    IS_NULLABLE,
    COLUMN_DEFAULT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'jauser_stock'
ORDER BY ORDINAL_POSITION
GO

-- Ejemplo de inserción de datos
/*
INSERT INTO jauser_stock (piezas, descripcion, codigo, model, tipo_deposito)
VALUES 
    ('1', 'OT3SLI08C0501', 'OT3SLI08C0501', '', 'NACIONAL'),
    ('1', 'NADIA BAUL', 'XC4WBA03C1001', 'CARTERAS DE CUERO', 'FISCAL');
*/
