# Módulo HasarServicios - Conteo de Personas en Tiendas

## Descripción

Módulo de integración para sincronizar datos de conteo de personas (ingresos y merodeo) desde las APIs de HasarServicios hacia tablas SQL Server centralizadas. Permite analizar el comportamiento de clientes y mejorar la toma de decisiones comerciales y operativas.

## Características

- **Arquitectura Asíncrona**: Procesamiento paralelo de múltiples sucursales y APIs usando `asyncio` y `aiohttp`
- **Multi-Base de Datos**: Soporte para almacenar datos en diferentes bases de datos según configuración
- **Gestión de Configuración**: Tabla SQL Server centralizada para vincular endpoints de API con sucursales
- **Operaciones MERGE**: Inserción y actualización atómica de datos (idempotencia)
- **Logging Centralizado**: Logs detallados en `HasarServicios/logs/app.log`
- **Manejo de Errores**: Reintentos automáticos con backoff exponencial
- **Testing Integrado**: Suite completa de tests para validación

## Estructura del Proyecto

```
HasarServicios/
├── __init__.py                  # Inicialización del módulo
├── api_hasar.py                 # Cliente API asíncrono (aiohttp)
├── consultas.py                 # Queries SQL (SELECT config, MERGE datos)
├── db_operations_hasar.py       # Operaciones de base de datos multi-BD
├── sync_conteo_hasar.py         # Script principal de sincronización
├── test_hasar.py                # Suite de tests
├── logs/                        # Directorio de logs
│   └── app.log                  # Log principal
└── README.md                    # Este archivo
```

## Configuración Inicial

### 1. Crear Tablas en SQL Server

Ejecutar el script SQL para crear las tablas necesarias:

```bash
# Ubicación del script
GestionAPI/scripts/create_hasar_tables.sql
```

Este script crea:
- **EB_BilcCamdata_pdv**: Tabla de configuración con endpoints de API por sucursal
- **BI_T_INGRESOS_SUCURSALES**: Tabla de almacenamiento de datos (en múltiples BDs)

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
| NOMBRE_DASHBOARD | Nombre descriptivo de la API ("API - Ingreso por día" o "API - Merodeo por dia") |
| API | URL completa del endpoint de API |
| Token | Bearer token para autenticación |
| DATA_BASE | Nombre de la base de datos destino ('POWER_BI_CONTROL' o 'POWER_BI_CONTROL_FRANQUICIAS') |
| ACTIVO | 1 para activo, 0 para inactivo |

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

Sincronizar datos de los últimos 5 días (excluyendo el día actual):

```bash
cd c:\Users\eduardo.berga\Desktop\Proyectos\GestionAPI
python GestionAPI\HasarServicios\sync_conteo_hasar.py
```

El script:
1. Lee configuración de sucursales activas desde `EB_BilcCamdata_pdv`
2. Procesa sucursales en paralelo
3. Por cada sucursal, consulta APIs de "Ingreso" y "Merodeo" concurrentemente
4. Combina resultados de ambas APIs por fecha
5. Guarda/actualiza datos en `BI_T_INGRESOS_SUCURSALES` de la BD correspondiente

### Revisar Logs

Los logs se guardan en `HasarServicios/logs/app.log`:

```bash
# Ver últimas líneas del log
Get-Content GestionAPI\HasarServicios\logs\app.log -Tail 50
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
           ├─────────────────────┬─────────────────────┐
           ↓                     ↓                     ↓
    ┌─────────────┐       ┌─────────────┐       ┌─────────────┐
    │ Sucursal 3  │       │ Sucursal 6  │  ...  │ Sucursal N  │
    │ (paralelo)  │       │ (paralelo)  │       │ (paralelo)  │
    └─────┬───────┘       └─────┬───────┘       └─────┬───────┘
          │                     │                     │
    ┌─────┴─────┐         ┌─────┴─────┐         ┌─────┴─────┐
    ↓           ↓         ↓           ↓         ↓           ↓
┌────────┐  ┌────────┐  ...                              ┌────────┐
│ API    │  │ API    │                                   │ API    │
│Ingreso │  │Merodeo │                                   │Merodeo │
└───┬────┘  └────┬───┘                                   └────┬───┘
    │            │                                            │
    └────────┬───┘                                            │
             │                                                │
             ↓                                                ↓
    ┌────────────────┐                              ┌────────────────┐
    │ Combinar datos │                              │ Combinar datos │
    │   por fecha    │                              │   por fecha    │
    └────────┬───────┘                              └────────┬───────┘
             │                                                │
             ↓                                                ↓
┌─────────────────────────────┐              ┌─────────────────────────────┐
│ BI_T_INGRESOS_SUCURSALES    │              │ BI_T_INGRESOS_SUCURSALES    │
│ (POWER_BI_CONTROL)          │              │ (POWER_BI_CONTROL_FRANQ.)   │
│ MERGE por FECHA+NRO_SUCURS  │              │ MERGE por FECHA+NRO_SUCURS  │
└─────────────────────────────┘              └─────────────────────────────┘
```

### Componentes Principales

#### 1. `api_hasar.py` - Cliente API Asíncrono

- Clase `HasarAPIClient` con `aiohttp.ClientSession`
- Métodos:
  - `obtener_datos()`: GET con Bearer token, validación de respuesta
  - `extraer_datos()`: Parsea JSON a formato simple
  - `parsear_fecha()`: Convierte "dd-mm-yyyy" a datetime
- Reintentos automáticos con backoff exponencial
- Límites de conexión: 50 total, 10 por host

#### 2. `db_operations_hasar.py` - Operaciones de BD

- Clase `HasarDB` con soporte multi-base de datos
- Métodos:
  - `obtener_configuracion_sucursales()`: Lee EB_BilcCamdata_pdv
  - `upsert_ingresos()`: MERGE en BI_T_INGRESOS_SUCURSALES
  - `verificar_datos_guardados()`: Query para testing
- Conexiones dinámicas según campo DATA_BASE

#### 3. `sync_conteo_hasar.py` - Script Principal

- Función `async main()`:
  - Calcula rango de fechas (últimos 5 días excluyendo hoy)
  - Agrupa configuraciones por sucursal
  - Procesa sucursales en paralelo con `asyncio.gather()`
  - Consolida estadísticas y logging de resumen
- Función `procesar_sucursal()`:
  - Llama APIs de Ingreso y Merodeo concurrentemente
  - Combina resultados en memoria por fecha
  - Ejecuta MERGE único por fecha con ambos valores

## Formato de Respuesta de API

### API - Ingreso por día

```json
{
    "success": true,
    "report": {
        "name": "API - Ingreso por día",
        "timezone": "America/Argentina/Buenos_Aires",
        "data": {
            "series": [{
                "name": "IN",
                "data": [
                    {"key": "06-04-2026", "value": 324},
                    {"key": "07-04-2026", "value": 346}
                ]
            }]
        }
    }
}
```

### API - Merodeo por dia

```json
{
    "success": true,
    "report": {
        "name": "API - Merodeo por dia",
        "data": {
            "series": [{
                "name": "MR",
                "data": [
                    {"key": "06-04-2026", "value": 9334},
                    {"key": "07-04-2026", "value": 9934}
                ]
            }]
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
| NRO_SUCURS | INT | Número de sucursal |
| INGRESOS | INT | Cantidad de ingresos (personas que entraron) |
| MERODEO | INT (nullable) | Cantidad de merodeo (personas que pasaron frente al local) |
| CREATED_AT | DATETIME | Timestamp de creación/actualización |

**Índices**:
- Primary Key: ID
- Unique: (FECHA, NRO_SUCURS) - Previene duplicados
- Nonclustered: FECHA DESC, NRO_SUCURS

## Mantenimiento

### Activar/Desactivar Sucursales

```sql
-- Desactivar sucursal
UPDATE EB_BilcCamdata_pdv 
SET ACTIVO = 0 
WHERE NUMERO_SUCURSAL = 6;

-- Activar sucursal
UPDATE EB_BilcCamdata_pdv 
SET ACTIVO = 1 
WHERE NUMERO_SUCURSAL = 6;
```

### Consultar Datos Sincronizados

```sql
-- Últimos 5 días de todas las sucursales
SELECT 
    NRO_SUCURS,
    FECHA,
    INGRESOS,
    MERODEO,
    CREATED_AT
FROM BI_T_INGRESOS_SUCURSALES
WHERE FECHA >= DATEADD(day, -5, GETDATE())
ORDER BY FECHA DESC, NRO_SUCURS;

-- Estadísticas por sucursal
SELECT 
    NRO_SUCURS,
    COUNT(*) AS Total_Registros,
    MIN(FECHA) AS Fecha_Minima,
    MAX(FECHA) AS Fecha_Maxima,
    AVG(INGRESOS) AS Promedio_Ingresos,
    AVG(MERODEO) AS Promedio_Merodeo
FROM BI_T_INGRESOS_SUCURSALES
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
- Verificar que existan registros con ACTIVO=1 en EB_BilcCamdata_pdv

### Error: "API retornó success=false"

- Verificar que el token Bearer sea válido
- Revisar que la URL del endpoint esté correcta
- Consultar logs en `HasarServicios/logs/app.log`

### Error: "Timeout al consultar la API"

- El timeout está configurado en 30 segundos
- Verificar conectividad de red a blic.camdata.co
- Revisar si el servidor de API está respondiendo

## Dependencias

- Python 3.7+
- aiohttp
- pyodbc
- datetime (stdlib)
- logging (stdlib)
- asyncio (stdlib)

## Autor

Eduardo Berga - Abril 2026

## Notas Adicionales

- El script sincroniza los **últimos 5 días excluyendo el día actual**
- Los datos se actualizan de forma idempotente (ejecutar múltiples veces no duplica registros)
- El procesamiento es asíncrono y paralelo para maximizar throughput
- Los logs incluyen estadísticas detalladas de cada ejecución
