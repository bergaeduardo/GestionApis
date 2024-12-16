# Sistema de Sincronización de Ventas

Un sistema robusto basado en Python para sincronizar datos de ventas entre una base de datos SQL Server local y la plataforma Solar API.

## Descripción General

Este sistema automatiza el proceso de sincronización de datos de ventas mediante:
1. Obtención de datos de ventas desde una base de datos SQL Server local
2. Procesamiento y formateo de datos según las especificaciones de Solar API
3. Autenticación con Solar API
4. Transmisión segura de información de ventas

## Características

- **Autenticación Automatizada**: Autenticación segura basada en tokens con Solar API
- **Procesamiento de Datos de Ventas**: Manejo integral de registros de ventas incluyendo:
  - Detalles de transacciones
  - Información a nivel de artículos
  - Procesamiento de pagos
  - Cálculos de impuestos
- **Integración con Base de Datos**: Conexión directa a SQL Server con manejo robusto de errores
- **Configuración Flexible**: Fácilmente configurable para diferentes entornos

## Componentes del Sistema

### 1. Integración API (`Apis.py`)
- Maneja toda la comunicación con Solar API
- Gestiona tokens de autenticación
- Procesa la transmisión de datos de ventas

### 2. Conexión a Base de Datos (`conexion.py`)
- Gestiona conexiones a la base de datos SQL Server
- Ejecuta consultas con manejo de errores
- Procesa conjuntos de resultados
- Actualiza estado de sincronización

### 3. Consultas SQL (`consultas.py`)
- Contiene todas las consultas SQL para recuperación de datos
- Maneja agregación compleja de datos de ventas
- Gestiona detalles y cálculos de transacciones

## Requisitos Técnicos

- Python 3.x
- Paquetes Python requeridos:
  - `requests`: Para comunicación API
  - `pyodbc`: Para conectividad con SQL Server
- SQL Server con ODBC Driver 17
- Credenciales válidas de Solar API

## Configuración

1. **Configuración de Base de Datos**
   - Configurar detalles de conexión al servidor
   - Establecer permisos apropiados de base de datos
   - Asegurar que ODBC Driver 17 esté instalado

2. **Configuración de API**
   - Configurar credenciales de Solar API
   - Configurar endpoints de API
   - Instalar certificados SSL requeridos

## Configuración de Certificado SSL

Para el manejo adecuado del certificado SSL:

1. Descargar el certificado desde `https://conectados.fortinmaure.com.ar`
2. Instalar el certificado en su sistema
3. Ejecutar el siguiente comando en su entorno virtual:
   ```bash
   python -m pip install pip-system-certs
   ```

## Flujo de Datos

1. **Autenticación**
   - El sistema solicita token de autenticación a Solar API
   - El token se almacena para solicitudes posteriores

2. **Obtención de Datos de Ventas**
   - El sistema consulta la base de datos local para ventas pendientes
   - Los datos se procesan y formatean según especificaciones de API

3. **Transmisión de Datos**
   - Los datos de ventas formateados se envían a Solar API
   - El sistema maneja la respuesta y actualiza el estado de sincronización

4. **Actualización de Estado**
   - Los registros sincronizados exitosamente se marcan en la base de datos
   - El sistema mantiene un registro de auditoría de sincronización

## Manejo de Errores

El sistema incluye manejo integral de errores para:
- Problemas de conexión a base de datos
- Fallos en comunicación API
- Errores de validación de datos
- Problemas de certificados SSL

## Seguridad

- Gestión segura de credenciales
- Autenticación API basada en tokens
- Transmisión encriptada de datos
- Seguridad en conexión a base de datos

## Mejores Prácticas

- Monitoreo regular de logs de sincronización
- Validación periódica de credenciales API
- Mantenimiento y optimización de base de datos
- Gestión de renovación de certificados SSL

## Soporte

Para soporte técnico o consultas:
1. Verificar validez del certificado SSL
2. Verificar conectividad de base de datos
3. Confirmar accesibilidad del endpoint API
4. Revisar logs de sincronización
