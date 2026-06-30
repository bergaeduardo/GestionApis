# Módulo HasarServicios - Conteo de Personas en Tiendas

## Descripción

Módulo de integración para sincronizar datos de conteo de personas (ingresos y merodeo) desde las APIs de HasarServicios hacia tablas SQL Server centralizadas. Permite analizar el comportamiento de clientes y mejorar la toma de decisiones comerciales y operativas.

Soporta dos granularidades de datos:
- **Diaria**: un registro por sucursal por día (APIs "Ingreso por día" y "Merodeo por dia")
- **Horaria**: un registro por sucursal por hora (APIs "IN x HORA" y "Merodeo MES X hora")

## Características

- **Arquitectura Asíncrona**: Procesamiento paralelo de múltiples sucursales y APIs usando `asyncio` y `aiohttp`
- **Multi-Base de Datos**: Soporte para almacenar datos en diferentes bases de datos según configuración
- **Gestión de Configuración**: Tabla SQL Server centralizada para vincular endpoints de API con sucursales
- **Operaciones MERGE**: Inserción y actualización atómica de datos (idempotencia)
- **Logging Centralizado**: Logs detallados en `HasarServicios/logs/app.log`
- **Manejo de Errores**: Reintentos automáticos con backoff exponencial, manejo de rate limiting (HTTP 429)
- **Testing Integrado**: Suite completa de tests para validación

## Estructura del Proyecto

```
HasarServicios/
├── __init__.py                  # Inicialización del módulo
├── api_hasar.py                 # Cliente API asíncrono (aiohttp)
├── consultas.py                 # Queries SQL (SELECT config, MERGE diario y horario)
├── db_operations_hasar.py       # Operaciones de base de datos multi-BD
├── sync_conteo_hasar.py         # Script principal de sincronización
├── test_hasar.py                # Suite de tests
├── logs/                        # Directorio de logs
│   └── app.log                  # Log principal
└── README.md                    # Este archivo
```

## Configuración Inicial

### 1. Crear Tablas en SQL Server

Ejecutar el script de creación base:

```bash
# Ubicación del script
GestionAPI/scripts/create_hasar_tables.sql
```

Si las tablas ya existen y se está migrando desde una versión anterior, ejecutar además:

```bash
# Script de migración: agrega soporte para datos horarios
GestionAPI/scripts/migrate_hasar_hora.sql
```

El script de migración es idempotente (se puede ejecutar múltiples veces sin efectos no deseados) y realiza:
- Agrega columna `FECHA_HORA DATETIME NULL` a `BI_T_INGRESOS_SUCURSALES`
- Reemplaza el índice único anterior por dos filtered unique indexes (uno para diarios, uno para horarios)

### 2. Verificar Credenciales

Las credenciales se configuran en `GestionAPI/common/credenciales.py`:

```python
POWER_BI_CONTROL = {
    'server': 'XL-APPS',
    'database': 'POWER_BI_CONTROL',
    'user': 'sa',
    'password': 'Axoft1988'
}

POWER_BI_CONTROL_FRANQUICIAS = {
    'server': 'XL-APPS',
    'database': 'POWER_BI_CONTROL_FRANQUICIAS',
    'user': 'sa',
    'password': 'Axoft1988'
}
```

### 3. Configurar Sucursales

Insertar configuraciones en la tabla `EB_BilcCamdata_pdv`:

| Campo | Descripción |
|-------|-------------|
| NUMERO_SUCURSAL | Número de sucursal (int) |
| NOMBRE_DASHBOARD | Nombre de la API (ver valores válidos abajo) |
| API | URL completa del endpoint de API |
| Token | Bearer token para autenticación |
| DATA_BASE | Nombre de la base de datos destino (`POWER_BI_CONTROL` o `POWER_BI_CONTROL_FRANQUICIAS`) |
| ACTIVO | 1 para activo, 0 para inactivo |

**Valores válidos para `NOMBRE_DASHBOARD`:**

| Valor | Tipo | Descripción |
|-------|------|-------------|
| `API - Ingreso por día` | Diaria | Ingresos totales del día |
| `API - Merodeo por dia` | Diaria | Merodeo total del día |
| `IN x HORA` | Horaria | Ingresos desglosados por hora |
| `Merodeo MES X hora` | Horaria | Merodeo desglosado por hora |

El sistema detecta automáticamente si una API es diaria u horaria según si el `NOMBRE_DASHBOARD` contiene `"x hora"`.

## Uso

### Ejecutar Tests

Antes de usar el módulo, ejecutar la suite de tests para validar configuración:

```bash
cd c:\Users\eduardo.berga\Desktop\Proyectos\GestionAPI
python GestionAPI\HasarServicios\test_hasar.py
```

Los tests verifican:
1. Conexión a bases de datos
2. Lectura de configuración de sucursales
3. Llamadas a APIs reales de HasarServicios
4. Inserción y actualización de datos

### Ejecutar Sincronización

Sincronizar datos de los últimos 30 días (excluyendo el día actual):

```bash
cd c:\Users\eduardo.berga\Desktop\Proyectos\GestionAPI
python GestionAPI\HasarServicios\sync_conteo_hasar.py
```

El script:
1. Lee configuración de sucursales activas desde `EB_BilcCamdata_pdv`
2. Procesa sucursales en paralelo
3. Por cada sucursal, separa las APIs en diarias y horarias
4. **APIs diarias**: combina Ingreso y Merodeo por fecha → guarda en `BI_T_INGRESOS_SUCURSALES` (FECHA_HORA = NULL)
5. **APIs horarias**: combina IN x HORA y Merodeo MES X hora por fecha+hora → guarda en `BI_T_INGRESOS_SUCURSALES` (FECHA_HORA = datetime completo)

### Revisar Logs

```bash
# Ver últimas líneas del log
Get-Content GestionAPI\HasarServicios\logs\app.log -Tail 50
```

El resumen del log diferencia registros diarios de horarios:

```
RESUMEN
Sucursales procesadas: 7 | Con errores: 0
Registros diarios actualizados: 189
Registros horarios actualizados: 4872
Duración: 95.3 segundos
```

## Arquitectura Técnica

### Flujo de Datos

```
┌─────────────────────┐
│ EB_BilcCamdata_pdv  │ ← Tabla de configuración
│ (sucursales activas)│
└──────────┬──────────┘
           │
           ↓
┌──────────────────────┐
│  sync_conteo_hasar   │ ← Script principal
│  (async main loop)   │
└──────────┬───────────┘
           │
    ┌──────┴──────┬──────────┐
    ↓             ↓          ↓
┌──────────┐ ┌──────────┐   ...   (sucursales en paralelo)
│Sucursal 3│ │Sucursal 6│
└────┬─────┘ └────┬─────┘
     │             │
  ┌──┴──┐       ┌──┴──┐
  ↓     ↓       ↓     ↓
Diarias Horarias ...        (APIs separadas por tipo)
  │     │
  │     ↓
  │  MERGE por (FECHA_HORA, NRO_SUCURS)
  │
  ↓
MERGE por (FECHA, NRO_SUCURS) donde FECHA_HORA IS NULL
  │
  ↓
┌─────────────────────────────┐
│ BI_T_INGRESOS_SUCURSALES    │
│ (POWER_BI_CONTROL o         │
│  POWER_BI_CONTROL_FRANQ.)   │
└─────────────────────────────┘
```

### Componentes Principales

#### 1. `api_hasar.py` - Cliente API Asíncrono

- Clase `HasarAPIClient` con `aiohttp.ClientSession`
- Métodos:
  - `obtener_datos()`: GET con Bearer token, validación de respuesta, manejo de rate limiting (429)
  - `extraer_datos()`: Parsea JSON a formato simple
  - `parsear_fecha()`: Convierte `"dd-mm-yyyy"` a datetime (APIs diarias)
  - `parsear_fecha_hora()`: Convierte `"dd-mm-yyyy H:MM AM/PM"` a datetime (APIs horarias)
- Reintentos automáticos con backoff exponencial para errores 5xx y rate limiting
- Timeouts: conexión 10s, lectura 120s
- Límites de conexión: 20 total, 3 por host

#### 2. `db_operations_hasar.py` - Operaciones de BD

- Clase `HasarDB` con soporte multi-base de datos
- Métodos:
  - `obtener_configuracion_sucursales()`: Lee `EB_BilcCamdata_pdv`
  - `upsert_ingresos()`: MERGE diario en `BI_T_INGRESOS_SUCURSALES` (clave: FECHA + NRO_SUCURS)
  - `upsert_ingresos_hora()`: MERGE horario en `BI_T_INGRESOS_SUCURSALES` (clave: FECHA_HORA + NRO_SUCURS)
  - `verificar_datos_guardados()`: Query para testing
- Conexiones dinámicas según campo `DATA_BASE`

#### 3. `sync_conteo_hasar.py` - Script Principal

- Función `async main()`:
  - Calcula rango de fechas (últimos 30 días excluyendo hoy)
  - Agrupa configuraciones por sucursal
  - Procesa sucursales en paralelo con `asyncio.gather()`
  - Consolida y loguea estadísticas diferenciando diarios de horarios
- Función `procesar_sucursal()`:
  - Separa APIs diarias (`NOMBRE_DASHBOARD` sin `"x hora"`) de horarias (con `"x hora"`)
  - Procesa cada grupo combinando Ingreso + Merodeo por fecha o fecha+hora
  - Ejecuta MERGE correspondiente para cada tipo

## Formato de Respuesta de API

### API - Ingreso por día (diaria)

```json
{
    "success": true,
    "report": {
        "name": "API - Ingreso por día",
        "data": {
            "series": [{"name": "IN", "data": [
                {"key": "06-04-2026", "value": 324}
            ]}]
        }
    }
}
```

### API - Merodeo por dia (diaria)

```json
{
    "success": true,
    "report": {
        "name": "API - Merodeo por dia",
        "data": {
            "series": [{"name": "MR", "data": [
                {"key": "06-04-2026", "value": 9334}
            ]}]
        }
    }
}
```

### IN x HORA (horaria)

```json
{
    "success": true,
    "report": {
        "name": "IN x HORA - Mes Actual",
        "data": {
            "series": [{"name": "IN", "data": [
                {"key": "01-06-2026 12:00 AM", "value": 0},
                {"key": "01-06-2026 1:00 AM",  "value": 0},
                {"key": "01-06-2026 1:00 PM",  "value": 47}
            ]}]
        }
    }
}
```

### Merodeo MES X hora (horaria)

```json
{
    "success": true,
    "report": {
        "name": "Merodeo MES X hora",
        "data": {
            "series": [{"name": "MR", "data": [
                {"key": "01-06-2026 12:00 AM", "value": 0},
                {"key": "01-06-2026 1:00 PM",  "value": 312}
            ]}]
        }
    }
}
```

## Esquema de Base de Datos

### Tabla: BI_T_INGRESOS_SUCURSALES

| Columna | Tipo | Descripción |
|---------|------|-------------|
| ID | INT IDENTITY | ID auto-incrementable |
| FECHA | DATE | Fecha del registro |
| FECHA_HORA | DATETIME (nullable) | Fecha y hora exacta — NULL para registros diarios, valor para horarios |
| NRO_SUCURS | INT | Número de sucursal |
| INGRESOS | INT | Cantidad de ingresos (personas que entraron) |
| MERODEO | INT (nullable) | Cantidad de merodeo (personas que pasaron frente al local) |
| CREATED_AT | DATETIME | Timestamp de creación/actualización |

**Índices:**

| Nombre | Columnas | Filtro | Descripción |
|--------|----------|--------|-------------|
| PK | ID | — | Primary key |
| UQ_BI_T_INGRESOS_DIARIO | FECHA, NRO_SUCURS | `WHERE FECHA_HORA IS NULL` | Un registro por día por sucursal |
| UQ_BI_T_INGRESOS_HORARIO | FECHA_HORA, NRO_SUCURS | `WHERE FECHA_HORA IS NOT NULL` | Un registro por hora por sucursal |
| IX_BI_T_INGRESOS_FECHA | FECHA DESC | — | Consultas por fecha |
| IX_BI_T_INGRESOS_SUCURSAL | NRO_SUCURS | — | Consultas por sucursal |

### Tabla: EB_BilcCamdata_pdv

Tabla de configuración. Primary Key: `(NUMERO_SUCURSAL, NOMBRE_DASHBOARD)`.

## Mantenimiento

### Activar/Desactivar Sucursales

```sql
-- Desactivar sucursal
UPDATE EB_BilcCamdata_pdv SET ACTIVO = 0 WHERE NUMERO_SUCURSAL = 6;

-- Activar sucursal
UPDATE EB_BilcCamdata_pdv SET ACTIVO = 1 WHERE NUMERO_SUCURSAL = 6;
```

### Consultar Datos Sincronizados

```sql
-- Datos diarios: últimos 30 días por sucursal
SELECT NRO_SUCURS, FECHA, INGRESOS, MERODEO, CREATED_AT
FROM BI_T_INGRESOS_SUCURSALES
WHERE FECHA_HORA IS NULL
  AND FECHA >= DATEADD(day, -30, GETDATE())
ORDER BY FECHA DESC, NRO_SUCURS;

-- Datos horarios: un día específico para una sucursal
SELECT FECHA_HORA, INGRESOS, MERODEO
FROM BI_T_INGRESOS_SUCURSALES
WHERE FECHA_HORA IS NOT NULL
  AND FECHA = '2026-06-29'
  AND NRO_SUCURS = 3
ORDER BY FECHA_HORA;

-- Estadísticas por sucursal (diarios)
SELECT
    NRO_SUCURS,
    COUNT(*) AS Total_Dias,
    MIN(FECHA) AS Fecha_Minima,
    MAX(FECHA) AS Fecha_Maxima,
    AVG(INGRESOS) AS Promedio_Ingresos,
    AVG(MERODEO) AS Promedio_Merodeo
FROM BI_T_INGRESOS_SUCURSALES
WHERE FECHA_HORA IS NULL
GROUP BY NRO_SUCURS
ORDER BY NRO_SUCURS;
```

## Troubleshooting

### Error: "No se pudo conectar a la base de datos"

- Verificar que el servidor XL-APPS esté accesible
- Validar credenciales en `common/credenciales.py`
- Verificar que las bases de datos POWER_BI_CONTROL existan

### Error: "No se encontraron sucursales activas"

- Ejecutar script SQL `create_hasar_tables.sql`
- Verificar que existan registros con `ACTIVO=1` en `EB_BilcCamdata_pdv`

### Error: "API retornó success=false"

- Verificar que el token Bearer sea válido
- Revisar que la URL del endpoint esté correcta
- Consultar logs en `HasarServicios/logs/app.log`

### Warning: "Rate limit (429)"

- El sistema reintenta automáticamente respetando el header `Retry-After`
- Si persiste, revisar la cantidad de sucursales activas procesándose en simultáneo

### Error: "Timeout después de N intentos"

- El timeout de lectura está configurado en 120 segundos
- Verificar conectividad de red a `blic.camdata.co`
- Las APIs horarias con rangos amplios pueden demorar más; considerar reducir el rango de días

### Las APIs horarias no se sincronizan

- Verificar que el `NOMBRE_DASHBOARD` en `EB_BilcCamdata_pdv` contenga la cadena `"x hora"` (sin distinguir mayúsculas)
- Ejemplos válidos: `"IN x HORA"`, `"Merodeo MES X hora"`

## Dependencias

- Python 3.7+
- aiohttp
- pyodbc
- datetime (stdlib)
- logging (stdlib)
- asyncio (stdlib)

## Autor

Eduardo Berga - Abril 2026

## Historial de Cambios

| Fecha | Descripción |
|-------|-------------|
| Abril 2026 | Versión inicial: sincronización diaria de ingresos y merodeo |
| Junio 2026 | Incorporación de APIs horarias (IN x HORA / Merodeo MES X hora), rango ampliado a 30 días, manejo de rate limiting y ajuste de timeouts |
