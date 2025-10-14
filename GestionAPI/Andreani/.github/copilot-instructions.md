# Copilot Instructions - Sistema de Integración Andreani

## Arquitectura del Proyecto

Este es un sistema de automatización para **rótulos de envío de Andreani** que sigue una arquitectura orientada a componentes con **flujo asíncrono**. El sistema consulta pedidos pendientes en SQL Server, crea órdenes en la API de Andreani, descarga etiquetas PDF y las imprime automáticamente.

### Componentes Principales

- **`sync_rotulos_andreani.py`**: Orquestador principal del proceso completo
- **`andreani_api.py`**: Cliente asíncrono para API de Andreani con manejo de tokens automático
- **`db_operations_andreani.py`**: Capa de acceso a datos para tabla `SEIN_TABLA_TEMPORAL_SCRIPT`
- **`impresora.py`**: Gestor de impresoras Windows con múltiples métodos de impresión
- **`consultas.py`**: Consultas SQL complejas que generan JSON estructurado

## Patrones Específicos del Proyecto

### 1. Gestión de Rutas y Módulos
```python
# Patrón común en todos los archivos principales
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)
from GestionAPI.Andreani.module import Class
from GestionAPI.common.credenciales import DATA_QA as DATA_PROD
```

### 2. API Asíncrona con Token Automático
- `AndreaniAPI` usa `aiohttp` con `_ensure_token()` y `asyncio.Lock()` para thread safety
- Todos los métodos de API son `async` y manejan errores HTTP automáticamente
- Usa `DATA_QA as DATA_PROD` para flexibilidad entre ambientes

### 3. Consultas SQL Complejas con JSON
Las consultas en `consultas.py` generan JSON directamente en SQL Server:
```sql
-- Patrón: Campos anidados con JSON_QUERY y FOR JSON PATH
JSON_QUERY((SELECT codigoPostal, calle, numero FROM ... FOR JSON PATH, ROOT('postal'))) AS origen
```

### 4. Gestión de Impresoras Windows
`PrinterManager` soporta múltiples métodos según `config/printer_config.json`:
- `"pdftoprinter"` (recomendado): Usa PDFtoPrinter.exe
- `"win32"`: API nativa de Windows
- `"adobe"`: Integración con Adobe Reader

## Flujo de Trabajo Típico

1. **Consultar datos**: `AndreaniDB.get_data_from_sein()` obtiene pedidos pendientes
2. **Crear orden**: `AndreaniAPI.crear_orden_envio()` retorna `numeroAgrupador`
3. **Obtener etiqueta**: `AndreaniAPI.obtener_etiquetas()` descarga PDF
4. **Imprimir**: `PrinterManager.print_pdf()` envía a impresora de rótulos
5. **Actualizar estado**: `AndreaniDB.update_imp_rot()` marca como procesado

## Configuración y Credenciales

- **Credenciales**: `GestionAPI.common.credenciales` (DATA_QA, CENTRAL_LAKERS)
- **Config impresora**: `config/printer_config.json` define método y path de impresora
- **Logging**: Usar `setup_logger('andreani_rotulos')` de `GestionAPI.common.logger_config`

## Windows-Specific

- **Async Policy**: Todos los archivos principales usan `WindowsSelectorEventLoopPolicy()`
- **Impresión**: Sistema diseñado para impresoras de etiquetas ZDesigner vía red UNC
- **Paths**: Usar rutas absolutas y manejar paths UNC para impresoras de red

## Testing y Debugging

- **Tests**: `test_andreani.py` usa `unittest.IsolatedAsyncioTestCase` para async
- **Debug**: `debug_andreani_batch.py` para pruebas de lotes de órdenes
- **API legacy**: `api.py` contiene implementación síncrona de respaldo

## Convenciones de Código

- **Async/await**: Todo el flujo principal es asíncrono
- **Logging**: Usar logger específico `'andreani_rotulos'` con niveles apropiados
- **Error handling**: Métodos devuelven `None` en error, logs detallados
- **JSON handling**: Preferir `await response.json()` sobre parseo manual
- **DB queries**: Usar parámetros SQL para prevenir inyección

## Archivos Clave para Entender

- `Technical_Documentation_Andreani.md`: Documentación arquitectural completa
- `sync_rotulos_andreani.py`: Ejemplo completo del flujo principal
- `config/printer_config.json`: Configuración de impresión
- `consultas.py`: Estructura de datos y queries SQL/JSON