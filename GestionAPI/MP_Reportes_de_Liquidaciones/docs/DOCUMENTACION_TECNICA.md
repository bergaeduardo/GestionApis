# Documentación Técnica — MP_Reportes_de_Liquidaciones

> **Última actualización:** 24 de abril de 2026  
> **Autor:** Eduardo Berga  
> **Base de código:** `GestionAPI/MP_Reportes_de_Liquidaciones/`

---

## 1. Panorama General

Este módulo sincroniza automáticamente los **Reportes de Liquidaciones de Mercado Pago** hacia SQL Server. Opera de forma completamente asíncrona (`asyncio` + `aiohttp`) y cubre el ciclo completo: configurar la cuenta MP → solicitar generación del reporte → hacer polling hasta que esté disponible → descargar el CSV → transformar con Pandas → hacer upsert en la tabla `MP_T_REPORTE_DE_LIQUIDACIONES` de `LAKER_SA`.

### Flujo de datos completo

```
API Mercado Pago
  │
  ├─ 1. PUT /v1/account/release_report/config  → asegurar encabezados en inglés
  ├─ 2. GET /v1/account/release_report/list    → snapshot de IDs previos
  ├─ 3. POST /v1/account/release_report        → solicitar reporte (últimos 5 días)
  ├─ 4. GET /v1/account/release_report/list    → polling hasta que aparezca un ID nuevo
  └─ 5. GET /v1/account/release_report/{file_name} → descarga CSV binario
         │
         ▼
  sync_liquidaciones_mp.py  (orquestador asyncio)
         │
         ├─ pd.read_csv()            → carga en memoria
         ├─ rename columns           → CSV_KEY → COLUMNA_DB  (ver consultas.py)
         ├─ type coercion            → DECIMAL / INT / DATETIME / BOOL
         └─ MercadoPagoDB.upsert_liquidaciones()
                  │
                  └─ MERGE INTO MP_T_REPORTE_DE_LIQUIDACIONES (LAKER_SA @ XL-TANGO)
```

---

## 2. Estructura de Archivos

```
MP_Reportes_de_Liquidaciones/
├── sync_liquidaciones_mp.py   ← Orquestador principal. Punto de entrada único.
├── api_mp.py                  ← Cliente API async (MercadoPagoAPIClient)
├── db_operations_mp.py        ← Capa de datos (MercadoPagoDB), construye y ejecuta el MERGE
├── consultas.py               ← Constantes: TABLE_NAME, MERGE_KEY_COLUMNS, CSV_TO_DB_COLUMNS,
│                                 listas de tipos (DECIMAL_COLUMNS, INT_COLUMNS, etc.)
├── test_mp.py                 ← CLI de pruebas manuales (ver sección 6)
├── run_sync.bat               ← Script de ejecución para Tarea Programada de Windows
├── docs/
│   └── DOCUMENTACION_TECNICA.md  ← Este archivo
├── logs/
│   └── app.log                ← Log del proceso (rotación manual)
└── temp/                      ← CSV descargados temporalmente (se eliminan al finalizar)
```

---

## 3. Componentes Principales

### 3.1 `sync_liquidaciones_mp.py` — Orquestador

Punto de entrada. Ejecuta `asyncio.run(main())` con la política `WindowsSelectorEventLoopPolicy` para compatibilidad Windows.

**Pasos internos de `main()`:**

1. Inicializa `MercadoPagoAPIClient(access_token)` y `MercadoPagoDB()`.
2. Llama a `client.asegurar_configuracion_en_ingles()` — si falla, continúa con fallback de encabezados en español (`SPANISH_TO_KEY`).
3. Toma snapshot de IDs previos con `obtener_lista_reportes()`.
4. Calcula el rango de fechas con `_calcular_rango_fechas()` (últimos 5 días, alineado a medianoche Argentina UTC-3).
5. Crea el reporte (`crear_reporte()`).
6. Hace polling con `esperar_reporte_disponible(ids_previos, max_espera_seg=1200, intervalo_seg=15)`.
7. Descarga el CSV binario con `descargar_reporte(file_name)`.
8. Guarda temporalmente en `temp/`, procesa con Pandas, ejecuta upsert.
9. Elimina el archivo temporal.

**Función clave de timezone:**
```python
# _calcular_rango_fechas() — medianoche Argentina = 03:00 UTC
# Si ahora UTC < 03:00 → "ayer" en Argentina
if ahora_utc.hour < 3:
    hoy_ar_en_utc = ahora_utc.replace(hour=3, ...) - timedelta(days=1)
else:
    hoy_ar_en_utc = ahora_utc.replace(hour=3, ...)
```

**Fallback de columnas en español:**  
El dict `SPANISH_TO_KEY` en `sync_liquidaciones_mp.py` mapea ~55 encabezados en español a los KEY ingleses. Se usa solo si `asegurar_configuracion_en_ingles()` retorna `False`.

---

### 3.2 `api_mp.py` — `MercadoPagoAPIClient`

Cliente asíncrono sobre `aiohttp`. Reutiliza una sola `ClientSession` durante toda la ejecución (lazy init en `_get_session()`).

| Método | Endpoint MP | Descripción |
|---|---|---|
| `consultar_configuracion()` | GET `/v1/account/release_report/config` | Estado actual de config |
| `actualizar_configuracion(config)` | PUT `/v1/account/release_report/config` | Cambiar `report_translation` |
| `asegurar_configuracion_en_ingles()` | PUT (condicional) | Idempotente: solo actualiza si ya no está en inglés |
| `crear_reporte(begin, end)` | POST `/v1/account/release_report` | Solicita generación async (202 Accepted) |
| `obtener_lista_reportes()` | GET `/v1/account/release_report/list` | Lista todos los reportes |
| `esperar_reporte_disponible(ids_previos)` | polling lista | Espera hasta 20 min, intervalo 15 s |
| `descargar_reporte(file_name)` | GET `/v1/account/release_report/{file_name}` | Descarga CSV binario |
| `close()` | — | Cierra `ClientSession` explícitamente |

**Autenticación:** Bearer token en el header `Authorization` de la sesión.  
**Reintentos:** `_get`, `_post`, `_put` implementan backoff exponencial (`2^intento` segundos) con hasta 3 reintentos automáticos. Los errores `401` y `404` no reintentan.

---

### 3.3 `db_operations_mp.py` — `MercadoPagoDB`

Usa `GestionAPI.common.conexion.Conexion` con `CENTRAL_LAKERS` (servidor `XL-TANGO`, base `LAKER_SA`).

**Método central: `upsert_liquidaciones(df: pd.DataFrame) → dict`**

1. Filtra columnas del DataFrame contra `CSV_TO_DB_COLUMNS.values()`.
2. Llama a `_build_merge_query(db_columns)` que genera dinámicamente la sentencia T-SQL `MERGE`.
3. Itera fila por fila ejecutando `cursor.execute(merge_query, params)`.
4. Hace `commit()` al final del lote; `rollback()` ante error crítico.
5. Retorna `{"insertados": int, "actualizados_aprox": int, "errores": int}`.

**Clave del MERGE (unicidad):**
```python
MERGE_KEY_COLUMNS = ["FECHA_LIQUIDACION", "SOURCE_ID", "RECORD_TYPE", "DESCRIPTION"]
```
La condición ON usa `ISNULL(target.col, '') = ISNULL(source.col, '')` para manejar NULLs correctamente.

---

### 3.4 `consultas.py` — Constantes y mapeos

Archivo de sólo constantes. No contiene lógica de negocio.

```python
TABLE_NAME = "MP_T_REPORTE_DE_LIQUIDACIONES"
MERGE_KEY_COLUMNS = ["FECHA_LIQUIDACION", "SOURCE_ID", "RECORD_TYPE", "DESCRIPTION"]

CSV_TO_DB_COLUMNS = {
    "DATE":          "FECHA_LIQUIDACION",
    "SOURCE_ID":     "SOURCE_ID",
    "RECORD_TYPE":   "RECORD_TYPE",
    # ... ~55 columnas más
}

DECIMAL_COLUMNS = {"NET_CREDIT_AMOUNT", "NET_DEBIT_AMOUNT", ...}  # 12 columnas
INT_COLUMNS     = {"INSTALLMENTS", "ORDER_ID", "SHIPPING_ID", "PACK_ID"}
DATETIME_COLUMNS = {"DATE", "TRANSACTION_APPROVAL_DATE"}
BOOL_COLUMNS    = {"IS_RELEASED"}
```

**Al agregar una columna nueva al reporte MP:** se debe actualizar este archivo (el mapeo y el set de tipos), y re-ejecutar `create_mp_table.sql` o aplicar un `ALTER TABLE` manual.

---

## 4. Base de Datos SQL Server

### Servidor y base de datos

| Parámetro | Valor |
|---|---|
| Servidor | `XL-TANGO` |
| Base de datos | `LAKER_SA` |
| Credenciales | `CENTRAL_LAKERS` en `GestionAPI/common/credenciales.py` |
| Driver | `ODBC Driver 17 for SQL Server` |

### Tabla: `dbo.MP_T_REPORTE_DE_LIQUIDACIONES`

Script de creación: [`GestionAPI/scripts/create_mp_table.sql`](../../scripts/create_mp_table.sql)

#### Grupos de columnas

| Grupo | Columnas clave |
|---|---|
| **PK / Auditoría** | `ID` (IDENTITY), `CREATED_AT` (DEFAULT GETDATE()) |
| **Clave MERGE** | `FECHA_LIQUIDACION`, `SOURCE_ID`, `RECORD_TYPE`, `DESCRIPTION` |
| **Referencia externa** | `EXTERNAL_REFERENCE` |
| **Montos** (DECIMAL 17,2) | `NET_CREDIT_AMOUNT`, `NET_DEBIT_AMOUNT`, `GROSS_AMOUNT`, `MP_FEE_AMOUNT`, `BALANCE_AMOUNT`, y 7 más |
| **Pago** | `INSTALLMENTS`, `PAYMENT_METHOD`, `PAYMENT_METHOD_TYPE`, `CURRENCY`, `FRANCHISE`, `LAST_FOUR_DIGITS` |
| **Impuestos** | `TAX_DETAIL`, `TAXES_DISAGGREGATED` (VARCHAR MAX, JSON) |
| **Punto de venta físico** | `POS_ID`, `POS_NAME`, `STORE_ID`, `STORE_NAME`, `POI_ID` |
| **Orden / Envío** | `ORDER_ID`, `SHIPPING_ID`, `PACK_ID`, `SHIPMENT_MODE` |
| **Producto / Vendedor** | `ITEM_ID`, `PRODUCT_SKU`, `BUSINESS_UNIT`, `SUB_UNIT` |
| **Pagador** | `PAYER_NAME`, `PAYER_ID_TYPE`, `PAYER_ID_NUMBER` |
| **Extra (JSON)** | `METADATA`, `OPERATION_TAGS` (VARCHAR MAX) |

#### Constraints e índices

```sql
-- Clave primaria
CONSTRAINT PK_MP_T_REPORTE_DE_LIQUIDACIONES PRIMARY KEY (ID)

-- Unicidad del registro de negocio
CONSTRAINT UQ_MP_LIQUIDACIONES_KEY UNIQUE (FECHA_LIQUIDACION, SOURCE_ID, RECORD_TYPE, DESCRIPTION)

-- Índices para consultas frecuentes
IX_MP_LIQ_FECHA      ON (FECHA_LIQUIDACION DESC)
IX_MP_LIQ_SOURCE_ID  ON (SOURCE_ID)
IX_MP_LIQ_RECORD_TYPE ON (RECORD_TYPE)
```

> **Nota:** La constraint `UQ_MP_LIQUIDACIONES_KEY` es la garantía de base de datos que refuerza la misma unicidad que el `MERGE` aplica en la aplicación.

---

## 5. Credenciales y Configuración

### Mercado Pago

Definida en `GestionAPI/common/credenciales.py`:

```python
MERCADOPAGO = {
    "access_token": "APP_USR-..."   # Token de producción
}
```

Se instancia directamente en `sync_liquidaciones_mp.py`:
```python
from GestionAPI.common.credenciales import MERCADOPAGO
client = MercadoPagoAPIClient(MERCADOPAGO["access_token"])
```

### Base de datos

```python
CENTRAL_LAKERS = {
    'server': 'XL-TANGO',
    'database': 'LAKER_SA',
    'user': 'sa',
    'password': '...'
}
```

---

## 6. Flujos de Trabajo para Desarrolladores

### 6.1 Ejecución normal (producción)

```bat
REM Desde la raíz del proyecto
call env\Scripts\activate.bat
python "GestionAPI\MP_Reportes_de_Liquidaciones\sync_liquidaciones_mp.py"
```

O usando el `.bat` incluido (diseñado para Tarea Programada de Windows):
```bat
GestionAPI\MP_Reportes_de_Liquidaciones\run_sync.bat
```

El `.bat` cambia el directorio a la raíz del proyecto (`cd /d "%~dp0..\.."`) antes de activar el entorno virtual, lo que es necesario para que las importaciones con `sys.path.insert(0, project_root)` funcionen correctamente.

### 6.2 Pruebas manuales con `test_mp.py`

```bat
cd GestionAPI\MP_Reportes_de_Liquidaciones

REM Ver configuración actual de la cuenta en MP
python test_mp.py config

REM Listar todos los reportes generados (guarda en logs/lista_reportes.log)
python test_mp.py lista

REM Consultar un reporte específico por ID
python test_mp.py buscar 884331221

REM Descargar CSV de un reporte específico
python test_mp.py descargar release-report-144448334-24-04-2026.csv

REM Crear un reporte nuevo para los últimos 5 días
python test_mp.py crear
```

> **Importante:** `python test_mp.py lista` escribe el resultado completo en `logs/lista_reportes.log`. No solo en consola.

### 6.3 Instalación del entorno

```bash
python -m venv env
env\Scripts\activate.bat
pip install -r requirements.txt
```

Dependencias principales usadas por este módulo: `aiohttp`, `pyodbc`, `pandas`, `pip-system-certs`.

### 6.4 Crear/recrear la tabla en SQL Server

```bat
REM Conectarse a XL-TANGO y ejecutar:
sqlcmd -S XL-TANGO -d LAKER_SA -i "GestionAPI\scripts\create_mp_table.sql"
```

> **Atención:** El script incluye `DROP TABLE IF EXISTS`. En producción, usar `ALTER TABLE` para agregar columnas nuevas en lugar de recrear.

---

## 7. Patrones Específicos del Módulo

### 7.1 Patrón de importación (obligatorio en todos los scripts)

Todos los archivos que no están en la raíz insertan la raíz del proyecto en `sys.path` antes de cualquier import del proyecto:

```python
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, project_root)

from GestionAPI.common.credenciales import MERCADOPAGO
from GestionAPI.MP_Reportes_de_Liquidaciones.api_mp import MercadoPagoAPIClient
```

### 7.2 Logger por módulo

El logger se llama siempre `"mp_liquidaciones"` en todos los archivos del módulo, y escribe en `logs/app.log` con ruta absoluta:

```python
logger = setup_logger(
    "mp_liquidaciones",
    log_path=os.path.join(_module_dir, "logs", "app.log"),
)
```

Formato del log: `[YYYY-MM-DD HH:MM:SS] LEVEL - modulo:linea - mensaje`

### 7.3 Sesión HTTP reutilizable

`MercadoPagoAPIClient` mantiene **una sola** `aiohttp.ClientSession` durante toda la ejecución. Se cierra explícitamente con `await client.close()` en el bloque `finally` del orquestador.

```python
finally:
    await client.close()
```

### 7.4 Estrategia de polling por snapshot de IDs

MP no garantiza que el reporte más reciente de la lista sea el que acabamos de crear. En lugar de comparar timestamps, se toma un **snapshot de IDs previos** antes de llamar a `crear_reporte()`, y se busca el primer ID nuevo con `file_name` no nulo:

```python
ids_previos = {r.get("id") for r in await client.obtener_lista_reportes()}
await client.crear_reporte(begin_date, end_date)
file_name = await client.esperar_reporte_disponible(ids_previos)
```

### 7.5 Construcción dinámica del MERGE

`_build_merge_query()` genera la sentencia MERGE en tiempo de ejecución basándose en las columnas presentes en el DataFrame. Esto hace que el código sea tolerante a reportes con columnas faltantes (MP puede omitir columnas vacías en el CSV).

### 7.6 Coerción de tipos antes del upsert

En `sync_liquidaciones_mp.py`, antes del upsert, se aplica coerción explícita:

```python
# Decimales: reemplazar comas, convertir a float
for col in DECIMAL_COLUMNS:
    df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", "."), errors="coerce")

# Enteros: pd.to_numeric con downcast
for col in INT_COLUMNS:
    df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

# Datetimes: pd.to_datetime con utc=True
for col in DATETIME_COLUMNS:
    df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)

# Booleanos: mapeo "true"/"false" → 1/0
for col in BOOL_COLUMNS:
    df[col] = df[col].map({"true": 1, "false": 0, True: 1, False: 0})
```

---

## 8. Dependencias Externas

| Dependencia | Versión | Uso |
|---|---|---|
| `aiohttp` | 3.10.11 | Cliente HTTP async para API de MP |
| `pyodbc` | 5.2.0 | Conexión a SQL Server (ODBC Driver 17) |
| `pandas` | (transitive) | Procesamiento del CSV descargado |
| `pip-system-certs` | 4.0 | Certificados SSL del sistema corporativo |
| `asyncio` (stdlib) | — | Event loop async; política `WindowsSelectorEventLoopPolicy` |

---

## 9. Puntos de Integración

| Sistema externo | Protocolo | Credencial usada |
|---|---|---|
| Mercado Pago API | HTTPS / Bearer token | `MERCADOPAGO["access_token"]` |
| SQL Server `LAKER_SA` @ `XL-TANGO` | pyodbc / ODBC 17 | `CENTRAL_LAKERS` |

---

## 10. Consideraciones Operativas

- **Rango de 5 días:** El reporte cubre `begin_date` hasta `end_date` (ambos alineados a medianoche Argentina). Esto significa que siempre incluye el día de ayer como último día.
- **Tiempo de generación MP:** Puede demorar entre 1 y 20 minutos. El script espera hasta 20 minutos (`max_espera_seg=1200`), verificando cada 15 segundos.
- **Archivo temporal:** El CSV se guarda en `temp/` con el `file_name` de MP y se elimina al terminar, tanto en éxito como en error.
- **Idempotencia:** El `MERGE` garantiza que ejecutar el script dos veces en el mismo día no duplica registros; actualiza los existentes.
- **ODBC Driver:** La clase `Conexion` (en `common/`) usa `ODBC Driver 17 for SQL Server`. La clase `DatabaseConnection` (usada por Solar) usa `ODBC Driver 13`. Este módulo usa `Conexion`, por lo que requiere el driver 17.
