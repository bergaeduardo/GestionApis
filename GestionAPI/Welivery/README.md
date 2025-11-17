# 📦 Sistema de Gestión de Envíos Welivery

## 🎯 Descripción

Sistema de integración con la API de Welivery para automatizar la gestión de envíos y seguimiento de pedidos. Proporciona sincronización bidireccional entre la base de datos interna y la plataforma Welivery.

## ✨ Características Principales

- 🔄 **Sincronización automática** de estados de envío
- 📊 **Consultas masivas** optimizadas con procesamiento asíncrono
- 🛡️ **Manejo robusto de errores** con reintentos automáticos
- 📝 **Logging detallado** para auditoría y debugging
- 🧪 **Suite de tests** completa con alta cobertura
- ⚡ **Alto rendimiento** con conexiones HTTP reutilizables

## 🏗️ Arquitectura

```
┌─────────────────┐    HTTP/REST     ┌─────────────────┐
│   WeliveryAPI   │◄─────────────────►│  API Welivery   │
│    (Client)     │                  │   (External)    │
└─────────────────┘                  └─────────────────┘
         ▲
         │ Interface
         ▼
┌─────────────────┐    SQL/ODBC      ┌─────────────────┐
│  WeliverySync   │◄─────────────────►│   SQL Server    │
│ (Orchestrator)  │                  │   (Database)    │
└─────────────────┘                  └─────────────────┘
         ▲
         │ Data Access
         ▼
┌─────────────────┐
│  WeliveryDB     │
│ (Repository)    │
└─────────────────┘
```

## 🚀 Inicio Rápido

### Prerrequisitos

```bash
# Python 3.8+
python --version

# Dependencias
pip install aiohttp pyodbc
```

### Configuración

1. **Configurar credenciales** en `../common/credenciales.py`:
```python
WELIVERY = {
    "url": "https://sistema.welivery.com.ar/api/delivery/status",
    "user": "tu_usuario",
    "password": "tu_password"
}
```

2. **Verificar conectividad**:
```bash
python test_welivery.py
```

3. **Ejecutar sincronización**:
```bash
python sync_welivery.py
```

## 📋 Uso

### Sincronización Manual

```python
from sync_welivery import WeliverySync
import asyncio

async def sync_example():
    sync = WeliverySync()
    try:
        # Sincronización completa
        stats = await sync.sincronizacion_completa()
        print(f"Estados actualizados: {stats['estados_actualizados']}")
    finally:
        await sync.close()

asyncio.run(sync_example())
```

### Consulta Individual

```python
from welivery_api import WeliveryAPI

async def query_example():
    api = WeliveryAPI(
        base_url="https://sistema.welivery.com.ar/api/delivery/status",
        user="usuario", 
        password="password"
    )
    
    try:
        status = await api.get_delivery_status("1344301085663-01")
        print(f"Estado: {status['Status']}")
    finally:
        await api.close()
```

## 🧪 Testing

### Ejecutar todos los tests
```bash
python test_welivery.py
```

### Tests específicos
```bash
# Solo tests de API
python -m unittest test_welivery.TestWeliveryAPI -v

# Solo tests de BD
python -m unittest test_welivery.TestWeliveryDB -v
```

## 📊 Monitoreo

### Logs del Sistema
```bash
# Ver logs en tiempo real
tail -f logs/welivery.log

# Buscar errores
grep ERROR logs/welivery.log
```

### Métricas Clave
- **Estados actualizados/hora**: Meta 100+
- **Tiempo de respuesta API**: < 2 segundos
- **Tasa de errores**: < 2%

## 📚 Documentación Completa

Para información técnica detallada, consultar:

📖 **[DOCUMENTACION_TECNICA.md](DOCUMENTACION_TECNICA.md)**

Incluye:
- Arquitectura del sistema
- Diseño técnico detallado  
- Manual de instalación completo
- Plan de pruebas (QA)
- Documentación de APIs
- Stored Procedures y triggers
- Jobs programados y métricas

## 🔧 Estructura del Módulo

```
Welivery/
├── __init__.py                 # Módulo Python
├── consultas.py               # Consultas SQL optimizadas  
├── welivery_api.py           # Cliente API asíncrono
├── db_operations_welivery.py # Operaciones de base de datos
├── sync_welivery.py          # Sincronizador principal
├── test_welivery.py         # Suite de pruebas unitarias
├── README.md                # Documentación básica (este archivo)
├── DOCUMENTACION_TECNICA.md # Documentación técnica completa
└── logs/                   # Directorio de logs
```

## Funcionalidades Principales

### 1. Creación de Envíos
- Busca pedidos pendientes sin número de seguimiento
- Usa `ORDER_ID_TIENDA` como número de seguimiento
- Actualiza `NUM_SEGUIMIENTO` en `SEIN_TABLA_TEMPORAL_SCRIPT`

### 2. Consulta de Estados
- Consulta la API de Welivery para obtener estados de envío
- Maneja múltiples consultas asíncronamente
- Mapea estados de texto a códigos numéricos

### 3. Actualización de Base de Datos
- Actualiza `estadoEnvio`, `estadoIdEnvio` y `fechaEstadoEnvio`
- Marca pedidos como entregados en `RO_T_ESTADO_PEDIDOS_ECOMMERCE`
- Procesamiento masivo de actualizaciones

## Configuración

### Credenciales
Las credenciales se configuran en `GestionAPI/common/credenciales.py`:

```python
WELIVERY = {
    "url": "https://sistema.welivery.com.ar",
    "user": "tu_usuario_welivery",
    "password": "tu_contraseña_welivery"
}
```

### Base de Datos
Utiliza la configuración `CENTRAL_LAKERS` para conectarse a SQL Server.

## Uso

### Sincronización Completa
```python
from GestionAPI.Welivery.sync_welivery import WeliverySync
import asyncio

async def ejecutar_sincronizacion():
    sync = WeliverySync()
    try:
        stats = await sync.sincronizar_completo()
        print(f"Resultados: {stats}")
    finally:
        await sync.close()

asyncio.run(ejecutar_sincronizacion())
```

### Consulta de Envío Específico
```python
async def consultar_envio():
    sync = WeliverySync()
    try:
        resultado = await sync.consultar_envio_especifico("1560401410870-01")
        print(f"Estado: {resultado}")
    finally:
        await sync.close()
```

### Solo Creación de Envíos
```python
async def crear_envios():
    sync = WeliverySync()
    try:
        stats = await sync.crear_envios_pendientes()
        print(f"Envíos creados: {stats['envios_creados']}")
    finally:
        await sync.close()
```

## API de Welivery

### Endpoint Principal
- **URL**: `https://sistema.welivery.com.ar/api/delivery_status`
- **Método**: GET
- **Autenticación**: Basic Auth
- **Parámetro**: `id` (número de seguimiento)

### Respuesta Típica
```json
{
    "status": "OK",
    "data": {
        "Status": "COMPLETADO",
        "welivery_id": "19205607",
        "external_id": "1560401410870-01",
        "status_history": [
            {
                "date_time": "2025-09-11 17:38:22",
                "estado": "COMPLETADO"
            }
        ]
    }
}
```

## Mapeo de Estados

| Estado Welivery | Código | Descripción |
|----------------|--------|-------------|
| PENDIENTE | 0 | Envío creado, pendiente |
| EN CURSO | 2 | En tránsito |
| COMPLETADO | 3 | Entregado exitosamente |
| CANCELADO | 4 | Envío cancelado |
| INGRESO A DEPOSITO | 7 | En depósito |
| REPETIDO | 9 | Reintento de entrega |
| PREPARADO | 10 | Listo para envío |
| REGRESADO | 19 | Devuelto al origen |
| INDEFINIDO | 98 | Estado no reconocido |

## Base de Datos

### Tablas Involucradas

#### SEIN_TABLA_TEMPORAL_SCRIPT
- `NRO_PEDIDO`: Número de pedido
- `NUM_SEGUIMIENTO`: Número de seguimiento (se actualiza)
- `TALON_PED`: Talón del pedido
- `METODO_ENVIO`: Filtro por 'FLEX'
- `estadoEnvio`: Estado en texto (se actualiza)
- `estadoIdEnvio`: ID del estado (se actualiza)
- `fechaEstadoEnvio`: Fecha del estado (se actualiza)

#### RO_T_ESTADO_PEDIDOS_ECOMMERCE
- `NRO_PEDIDO`: Número de pedido
- `TALON_PED`: Talón del pedido
- `ENTREGADO`: Flag de entrega (se actualiza a 1)
- `FECHA_ENTREGADO`: Fecha de entrega (se actualiza)

### Consultas Principales

#### Pedidos Pendientes de Envío
```sql
SELECT A.NRO_PEDIDO, B.ORDER_ID_TIENDA, A.TALON_PED 
FROM SEIN_TABLA_TEMPORAL_SCRIPT AS A
LEFT JOIN GVA21 AS B ON B.NRO_PEDIDO=A.NRO_PEDIDO AND B.TALON_PED=A.TALON_PED
WHERE A.TALON_PED = '99'
AND A.METODO_ENVIO = 'FLEX'
AND A.NUM_SEGUIMIENTO IS NULL
```

#### Pedidos Pendientes de Entrega
```sql
SELECT NRO_PEDIDO, NUM_SEGUIMIENTO, TALON_PED 
FROM SEIN_TABLA_TEMPORAL_SCRIPT
WHERE TALON_PED = '99'
AND METODO_ENVIO = 'FLEX'
AND NUM_SEGUIMIENTO IS NOT NULL
AND (estadoIdEnvio NOT IN('3','4','19','23') OR estadoIdEnvio IS NULL)
```

## Logging

El módulo utiliza el sistema de logging configurado en `common/logger_config.py`. Los logs se guardan en:
- Archivo: `logs/app.log`
- Consola: Output directo

### Niveles de Log
- **INFO**: Operaciones normales y estadísticas
- **WARNING**: Situaciones no críticas
- **ERROR**: Errores que requieren atención
- **DEBUG**: Información detallada para desarrollo

## Pruebas

### Ejecutar Pruebas Unitarias
```bash
cd GestionAPI/Welivery
python test_welivery.py
```

### Pruebas Manuales
```bash
# Probar API
python test_welivery.py manual_api

# Probar base de datos
python test_welivery.py manual_db

# Probar sincronización
python test_welivery.py manual_sync
```

## Ejecución Directa

Para ejecutar el módulo directamente:

```bash
cd GestionAPI/Welivery
python sync_welivery.py
```

## Manejo de Errores

El módulo incluye manejo robusto de errores:

- **Timeouts**: 30 segundos para consultas API
- **Reconexión**: Manejo automático de conexiones DB
- **Validación**: Verificación de datos antes de actualizar
- **Logging**: Registro detallado de todos los errores

## Consideraciones de Performance

- **Consultas Asíncronas**: Múltiples consultas API en paralelo
- **Procesamiento por Lotes**: Actualizaciones masivas de BD
- **Connection Pooling**: Reutilización de conexiones
- **Rate Limiting**: Control de velocidad de consultas

## Monitoreo y Estadísticas

Cada ejecución proporciona estadísticas detalladas:

```python
{
    'envios_creados': 15,
    'estados_actualizados': 42,
    'entregados_marcados': 8,
    'errores': 2
}
```

## 🐛 Resolución de Problemas

### Errores Comunes

#### Error de Autenticación
```
Error 401: Unauthorized
```
**Solución**: Verificar credenciales en `../common/credenciales.py`

#### Timeout de Conexión
```
Error: TimeoutError
```
**Solución**: Revisar conectividad de red y estado de API Welivery

#### Error de Base de Datos
```
Error: pyodbc.Error
```
**Solución**: Verificar conexión SQL Server y permisos

### Debug Avanzado

```python
# Habilitar logging detallado
import logging
logging.getLogger('welivery_api').setLevel(logging.DEBUG)
```

## 🔒 Seguridad

- ✅ **Autenticación HTTP Basic** con credenciales protegidas
- ✅ **Timeouts configurables** para prevenir DoS
- ✅ **Validación de entrada** en todos los parámetros
- ✅ **Logs sanitizados** sin exposición de credenciales

## 🤝 Contribución

1. Fork del proyecto
2. Crear rama de características (`git checkout -b feature/nueva-funcionalidad`)
3. Commit cambios (`git commit -m 'Add: Nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crear Pull Request

### Estándares de Código
- Seguir PEP 8 para Python
- Documentar todas las funciones públicas
- Incluir tests para nueva funcionalidad
- Mantener cobertura de tests > 80%

## 📞 Soporte

- 🐛 **Issues**: Crear issue en sistema de gestión
- 📧 **Email**: equipo-desarrollo@empresa.com
- 📱 **Slack**: #welivery-integration

---

**Última actualización**: Diciembre 2024  
**Versión**: 1.0  
**Estado**: Producción ✅

## 📚 Documentación Adicional

Para información técnica detallada, consultar:
- [`DOCUMENTACION_TECNICA.md`](./DOCUMENTACION_TECNICA.md) - Arquitectura completa y especificaciones
- [`ejemplo_delivery_status.json`](./ejemplo_delivery_status.json) - Ejemplo de respuesta API

1. **Error de Autenticación**
   - Verificar credenciales en `credenciales.py`
   - Confirmar acceso a la API de Welivery

2. **Conexión a Base de Datos**
   - Verificar configuración `CENTRAL_LAKERS`
   - Confirmar conectividad al servidor SQL

3. **Números de Seguimiento Faltantes**
   - Verificar que exista `ORDER_ID_TIENDA` en GVA21
   - Confirmar filtros de consulta

4. **Estados No Actualizados**
   - Verificar respuesta de API Welivery
   - Confirmar mapeo de estados

## Mantenimiento

### Actualización de Estados
Para agregar nuevos estados, modificar el método `map_status_to_code` en `welivery_api.py`.

### Nuevas Consultas
Agregar consultas SQL en `consultas.py` y métodos correspondientes en `db_operations_welivery.py`.

### Logging Adicional
Configurar logging específico modificando `setup_logger` si es necesario.

## Versiones

- **1.0.0**: Implementación inicial completa

## Contacto

Para soporte o consultas sobre este módulo, contactar al equipo de desarrollo de GestionAPI.