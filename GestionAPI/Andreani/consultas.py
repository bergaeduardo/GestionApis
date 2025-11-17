#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Consultas SQL para el módulo Andreani

QRY_GET_DATA_FROM_SEIN = """
SELECT CAST((
SELECT 
    '400007367' AS contrato,
    LTRIM(RTRIM(T_OUTER.NRO_PEDIDO)) AS idPedido,
    0 AS valorACobrar,
    JSON_QUERY((
        SELECT
            '1644' AS codigoPostal,
            'Uruguay' AS calle,
            '4415' AS numero,
            'Béccar' AS localidad,
            '' AS region,
            'Argentina' AS pais,
            JSON_QUERY('[{"meta": "", "contenido": ""}]') AS componentesDeDireccion
        FOR JSON PATH, ROOT('postal')
    )) AS origen,
	JSON_QUERY((
		SELECT
			LTRIM(RTRIM(T_OUTER.CODIGO_POSTAL_ENTREGA)) AS codigoPostal,
			-- Calle: todo antes del último espacio
			CASE 
				WHEN CHARINDEX(' ', REVERSE(LTRIM(RTRIM(T_OUTER.DIRECCION_ENTREGA)))) > 0
				THEN LEFT(
						LTRIM(RTRIM(T_OUTER.DIRECCION_ENTREGA)),
						LEN(LTRIM(RTRIM(T_OUTER.DIRECCION_ENTREGA))) 
						- CHARINDEX(' ', REVERSE(LTRIM(RTRIM(T_OUTER.DIRECCION_ENTREGA))))
					 )
				ELSE '' -- o la dirección completa si no hay espacio
			END AS calle,
			-- Número: todo después del último espacio
			CASE 
				WHEN CHARINDEX(' ', REVERSE(LTRIM(RTRIM(T_OUTER.DIRECCION_ENTREGA)))) > 0
				THEN RIGHT(
						LTRIM(RTRIM(T_OUTER.DIRECCION_ENTREGA)),
						CHARINDEX(' ', REVERSE(LTRIM(RTRIM(T_OUTER.DIRECCION_ENTREGA)))) - 1
					 )
				ELSE LTRIM(RTRIM(T_OUTER.DIRECCION_ENTREGA)) -- toda la dirección si no hay espacio
			END AS numero,
			LTRIM(RTRIM(T_OUTER.LOCALIDAD_ENTREGA)) AS localidad,
			LTRIM(RTRIM(T_OUTER.PROVINCIA)) AS region,
			'Argentina' AS pais,
			JSON_QUERY('[{"meta": "", "contenido": ""}, {"meta": "", "contenido": ""}]') AS componentesDeDireccion
		FOR JSON PATH, ROOT('postal')
	)) AS destino,
    JSON_QUERY((
        SELECT
            'Lakers Corp' AS nombreCompleto,
            'xlshop@xl.com.ar' AS email,
            'DNI' AS documentoTipo,
            '41322399' AS documentoNumero,
            JSON_QUERY('[{"tipo": 1, "numero": "153715896"}]') AS telefonos
        FOR JSON PATH, WITHOUT_ARRAY_WRAPPER
    )) AS remitente,
    JSON_QUERY((
        SELECT
            T1.NOMBRE_CLIENTE AS nombreCompleto,
            T1.E_MAIL AS email,
            'CUIT' AS documentoTipo,
            T1.N_CUIT AS documentoNumero,
            JSON_QUERY(
                (
                    SELECT
                        2 AS tipo,
                        LTRIM(RTRIM(T1.TELEFONO1_ENTREGA)) AS numero
                    FOR JSON PATH
                )
            ) AS telefonos
        FROM
            SEIN_TABLA_TEMPORAL_SCRIPT AS T1
        WHERE
            T1.NRO_PEDIDO = T_OUTER.NRO_PEDIDO
        FOR JSON PATH
    )) AS destinatario,
    JSON_QUERY((
    SELECT 2 AS kilos,
           5000 AS volumenCm,
           0 AS valorDeclaradoSinImpuestos,
           0 AS valorDeclaradoConImpuestos,
           JSON_QUERY((
               SELECT [meta], [contenido]
               FROM (
                   SELECT 'detalle' AS [meta], '' AS [contenido]
                   UNION ALL
                   SELECT 'idCliente' AS [meta], LTRIM(RTRIM(T_OUTER.NRO_PEDIDO)) AS [contenido]
                   UNION ALL
                   SELECT 'observaciones' AS [meta], '' AS [contenido]
               ) AS ReferenciasSub
               FOR JSON PATH
           )) AS referencias
    FOR JSON PATH
	)) AS bultos
FROM
    SEIN_TABLA_TEMPORAL_SCRIPT AS T_OUTER
WHERE
    T_OUTER.IMP_ROT = 0
    AND T_OUTER.NUM_SEGUIMIENTO IS NULL
    AND T_OUTER.TALON_PED IN('80','99','102')
    AND T_OUTER.METODO_ENVIO = 'DOMICILIO'
FOR JSON PATH, ROOT('data')
) AS NTEXT);
"""

QRY_UPDATE_NUM_SEGUIMIENTO = """
UPDATE SEIN_TABLA_TEMPORAL_SCRIPT SET NUM_SEGUIMIENTO = ? WHERE NRO_PEDIDO = ? AND NUM_SEGUIMIENTO IS NULL
"""

QRY_UPDATE_IMP_ROT = """
UPDATE SEIN_TABLA_TEMPORAL_SCRIPT SET IMP_ROT = 1 WHERE NRO_PEDIDO = ? AND NUM_SEGUIMIENTO IS NOT NULL
"""

QRY_GET_PEDIDOS_SIN_IMPRIMIR = """
SELECT NRO_PEDIDO, NUM_SEGUIMIENTO
FROM SEIN_TABLA_TEMPORAL_SCRIPT
WHERE NUM_SEGUIMIENTO IS NOT NULL 
  AND IMP_ROT = 0
  AND TALON_PED IN('80','99','102')
  AND METODO_ENVIO = 'DOMICILIO'
"""

QRY_GET_ENVIOS_PENDIENTES = """
SELECT NRO_PEDIDO, NUM_SEGUIMIENTO, TALON_PED
FROM SEIN_TABLA_TEMPORAL_SCRIPT
WHERE IMP_ROT = 1 
  AND NUM_SEGUIMIENTO IS NOT NULL 
  AND (estadoIdEnvio not in('14','18','20') OR estadoIdEnvio IS NULL)
  AND estadoEnvio <> 'RESCATADO'
"""

QRY_UPDATE_ESTADO_ENVIO = """
UPDATE SEIN_TABLA_TEMPORAL_SCRIPT 
SET estadoEnvio = ?, estadoIdEnvio = ?, fechaEstadoEnvio = ?
WHERE NUM_SEGUIMIENTO = ?
"""

QRY_UPDATE_ENTREGADO = """
UPDATE RO_T_ESTADO_PEDIDOS_ECOMMERCE 
SET ENTREGADO = 1, FECHA_ENTREGADO = ?
WHERE LTRIM(RTRIM(NRO_PEDIDO)) = ? AND TALON_PED = CAST(? AS INT)
"""

QRY_GET_PEDIDO_BY_SEGUIMIENTO = """
SELECT NRO_PEDIDO, TALON_PED
FROM SEIN_TABLA_TEMPORAL_SCRIPT
WHERE NUM_SEGUIMIENTO = ?
"""