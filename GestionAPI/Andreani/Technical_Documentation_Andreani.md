# Documento Técnico del Proyecto Andreani

## 1. Arquitectura del Sistema

### 1.1. Descripción General
El proyecto Andreani es un sistema de backend diseñado para automatizar el proceso de generación e impresión de rótulos de envío. Su función principal es consultar una base de datos en busca de pedidos pendientes, comunicarse con la API de Andreani para crear las órdenes de envío correspondientes, descargar las etiquetas (rótulos) en formato PDF y enviarlas a una impresora específica.

El sistema está diseñado como un conjunto de módulos de Python que operan de forma secuencial y asíncrona, orquestados por un script principal. No sigue un patrón de arquitectura tradicional como MVC, sino que se estructura como una **arquitectura orientada a componentes o servicios**, donde cada módulo tiene una responsabilidad bien definida.

### 1.2. Diagrama de Componentes (Descripción Textual)

```
+-------------------------+      +--------------------------+      +-----------------------------+
|                         |      |                          |      |                             |
|   Base de Datos         |----->|  db_operations_andreani  |<---->|  sync_rotulos_andreani.py   |
| (CENTRAL_LAKERS)        |      |  (Capa de Acceso a Datos)  |      |  (Orquestador Principal)    |
|  SEIN_TABLA_TEMPORAL    |      |                          |      |                             |
|      _SCRIPT            |      |                          |      |                             |
+-------------------------+      +--------------------------+      +-----------------------------+
       ^                                     ^                                   |
       |                                     |                                   |
       |                         +-----------v-----------+       +---------------v-----------------+
       |                         |                       |       |                                 |
       +-------------------------|  consultar_estado.py  |<------|  andreani_api.py                |
                                 |  (Actualización de    |       |  (Cliente Asíncrono de API)     |
                                 |   Estados de Envío)   |       |                                 |
                                 +-----------------------+       +---------------------------------+
                                                                                |
                                                                                v
+-------------------------+      +-------------------------+      +-----------------------------+
|                         |      |                         |      |                             |
|   Impresora de Rótulos  |<-----|  impresora.py           |<-----|  API Externa de Andreani    |
|  (ZDesigner, etc.)      |      |  (Gestor de Impresión)  |      |  (Endpoints REST)           |
|                         |      |                         |      |                             |
+-------------------------+      +-------------------------+      +-----------------------------+

```

### 1.3. Flujo de Datos

#### Flujo de Generación de Rótulos
1.  El script `sync_rotulos_andreani.py` se ejecuta.
2.  Se conecta a la base de datos a través de `db_operations_andreani.py` y obtiene los pedidos pendientes de la tabla `SEIN_TABLA_TEMPORAL_SCRIPT`.
3.  Para cada pedido, invoca de forma asíncrona al cliente `andreani_api.py` para crear una orden de envío en la API de Andreani.
4.  Con el `numeroAgrupador` obtenido, vuelve a llamar a la API para descargar la etiqueta en formato PDF.
5.  El script guarda el PDF en un directorio temporal.
6.  Utiliza el módulo `impresora.py` para gestionar la cola de impresión de Windows, seleccionar la impresora de rótulos y enviar el archivo PDF para su impresión.
7.  Si la impresión es exitosa, actualiza el estado del pedido en la base de datos a través de `db_operations_andreani.py` (campo `IMP_ROT = 1` y `NUM_SEGUIMIENTO`).
8.  Finalmente, el gestor de impresión restaura la impresora predeterminada del sistema.

#### Flujo de Actualización de Estados de Envío
1.  El script `consultar_estado.py` se ejecuta (manual o programado).
2.  Se conecta a la base de datos y consulta los registros en `SEIN_TABLA_TEMPORAL_SCRIPT` que cumplan: `IMP_ROT = 1`, `NUM_SEGUIMIENTO IS NOT NULL` y `estadoIdEnvio <> 18` (o `IS NULL`).
3.  Para cada registro obtenido, realiza una consulta asíncrona a la API de Andreani para obtener el estado actualizado del envío.
4.  Extrae los campos `estado`, `estadoId` y `fechaEstado` de la respuesta de la API.
5.  Actualiza la base de datos con estos valores en los campos `estadoEnvio`, `estadoIdEnvio` y `fechaEstadoEnvio`.
6.  Genera un reporte con el resumen de envíos actualizados y errores encontrados.

### 1.4. Tecnologías y Patrones
*   **Lenguaje:** Python 3
*   **Librerías Principales:**
    *   `aiohttp`: Para realizar llamadas asíncronas a la API de Andreani, mejorando el rendimiento al procesar múltiples pedidos.
    *   `pyodbc`: Para la conexión y ejecución de consultas a la base de datos SQL Server.
    *   `pywin32`: Para interactuar con la API de Windows, específicamente para la gestión de impresoras.
*   **Patrones:**
    *   **Asincronía:** El uso de `asyncio` y `aiohttp` es fundamental para procesar pedidos en paralelo sin bloquear el hilo principal.
    *   **Abstracción de Componentes:** Cada módulo (`andreani_api`, `db_operations_andreani`, `impresora`) encapsula una funcionalidad específica, facilitando su mantenimiento y reutilización.
    *   **Inyección de Dependencias (Ligera):** La configuración (credenciales, rutas de impresora) se gestiona en archivos externos (`credenciales.py`, `config/printer_config.json`) y se pasa a las clases correspondientes durante la inicialización.

## 2. Especificación Técnica / Diseño Detallado

### 2.1. Módulos Principales

#### `sync_rotulos_andreani.py`
*   **Responsabilidad:** Orquestar todo el proceso. Es el punto de entrada de la lógica de negocio.
*   **Clase/Función Principal:** `process_orders_and_get_labels()` (función asíncrona).
*   **Lógica Clave:**
    1.  Inicializa `AndreaniAPI` y `AndreaniDB`.
    2.  Llama a `get_data_from_sein()` para obtener los datos.
    3.  Procesa el JSON y crea tareas asíncronas para `api.crear_orden_envio()`.
    4.  Recopila los resultados y crea nuevas tareas para `api.obtener_etiquetas()`.
    5.  Configura e inicializa el `PrinterManager` desde `impresora.py`.
    6.  Itera sobre las etiquetas descargadas, las guarda como PDF y las imprime usando `printer_manager.print_file()`.
    7.  Llama a `andreani_db.update_imp_rot()` para marcar el pedido como impreso.

#### `andreani_api.py`
*   **Responsabilidad:** Encapsular toda la comunicación con la API de Andreani.
*   **Clase Principal:** `AndreaniAPI`.
*   **Métodos Clave:**
    *   `_get_auth_token()`: Obtiene y almacena el token de autorización.
    *   `_make_request()`: Método base para realizar todas las peticiones `GET`/`POST` asíncronas.
    *   `crear_orden_envio(data)`: Envía los datos de un pedido para crear una orden.
    *   `obtener_etiquetas(numeroAgrupador)`: Descarga el contenido binario (PDF) de una etiqueta.
    *   Otros métodos para consultar estado, sucursales, etc.

#### `db_operations_andreani.py`
*   **Responsabilidad:** Gestionar las operaciones de lectura y escritura en la base de datos.
*   **Clase Principal:** `AndreaniDB`.
*   **Estructuras de Datos:**
    *   **Tabla de Origen:** `SEIN_TABLA_TEMPORAL_SCRIPT`. Contiene información de pedidos y estados de envío.
    *   **Campos de Control:**
        *   `IMP_ROT`: Flag (`bit` o `int`) que se establece a `1` cuando un rótulo ha sido impreso.
        *   `NUM_SEGUIMIENTO`: Almacena el número de seguimiento de Andreani.
        *   `estadoEnvio`: Descripción textual del estado del envío (ej: "Entregado").
        *   `estadoIdEnvio`: ID numérico del estado del envío (ej: 18 para "Entregado").
        *   `fechaEstadoEnvio`: Fecha y hora del último estado conocido.
*   **Métodos Clave:**
    *   `get_data_from_sein()`: Ejecuta la consulta `QRY_GET_DATA_FROM_SEIN` para obtener los pedidos pendientes de impresión.
    *   `update_imp_rot(nro_pedido, numero_envio)`: Ejecuta `QRY_UPDATE_IMP_ROT` para actualizar el estado de impresión y el número de seguimiento.
    *   `get_envios_pendientes()`: Ejecuta `QRY_GET_ENVIOS_PENDIENTES` para obtener envíos que requieren actualización de estado.
    *   `update_estado_envio(num_seguimiento, estado, estado_id, fecha_estado)`: Ejecuta `QRY_UPDATE_ESTADO_ENVIO` para actualizar los campos de estado del envío.

#### `consultar_estado.py`
*   **Responsabilidad:** Consultar y actualizar el estado de los envíos desde la API de Andreani.
*   **Función Principal:** `actualizar_estados_envios()` (función asíncrona).
*   **Modos de Operación:**
    1.  **Actualización Masiva:** Procesa todos los envíos pendientes de actualización en la base de datos.
    2.  **Consulta Individual:** Consulta el estado de un envío específico por su número de seguimiento y actualiza la base de datos.
*   **Lógica Clave:**
    1.  Obtiene los envíos pendientes con `AndreaniDB.get_envios_pendientes()`.
    2.  Para cada envío, llama a `consultar_estado_envio_api()` que usa `andreani_api.consultar_estado_envio()`.
    3.  Actualiza los campos de estado en la base de datos con `update_estado_envio()`.
    4.  Genera un reporte con estadísticas del proceso.
*   **Uso desde línea de comandos:**
    *   `python consultar_estado.py --actualizar`: Actualiza todos los envíos pendientes.
    *   `python consultar_estado.py --numero_envio <numero>`: Consulta y actualiza un envío específico.
    *   `python consultar_estado.py`: Ejecuta actualización masiva por defecto.

#### `impresora.py`
*   **Responsabilidad:** Abstraer la complejidad de la impresión de archivos PDF en Windows.
*   **Clase Principal:** `PrinterManager`.
*   **Lógica Clave:**
    *   Permite cambiar la impresora predeterminada del sistema a una impresora de etiquetas específica y luego restaurarla.
    *   Implementa múltiples estrategias de impresión (`Win32`, `Ghostscript`, `Adobe`, `PDFtoPrinter`) para máxima compatibilidad. La estrategia se elige desde un archivo de configuración.
    *   Proporciona un método simple `print_file(path)` que utiliza la estrategia seleccionada.

## 3. Manual de Instalación y Configuración

### 3.1. Prerrequisitos
*   Python 3.8+
*   Acceso a la base de datos `CENTRAL_LAKERS`.
*   Credenciales para la API de Andreani (QA o Producción).
*   Una impresora de rótulos instalada en un servidor de impresión o localmente.

### 3.2. Entorno de Desarrollo
1.  **Clonar el repositorio.**
2.  **Crear un entorno virtual:**
    ```bash
    python -m venv env
    env\Scripts\activate
    ```
3.  **Instalar dependencias:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Configurar Credenciales:**
    *   Asegurarse de que el archivo `GestionAPI/common/credenciales.py` exista y contenga los diccionarios `CENTRAL_LAKERS` (para la BD) y `DATA_QA` o `DATA_PROD` (para la API).
5.  **Configurar Impresora:**
    *   Crear el archivo `GestionAPI/Andreani/config/printer_config.json`.
    *   Añadir la configuración de la impresora. Se recomienda **Ghostscript** para entornos de servidor.
        ```json
        {
            "printer": {
                "method": "ghost",
                "label_printer_path": "\\servidor\impresora_etiquetas"
            }
        }
        ```
    *   Asegurarse de que el software requerido por el método (`Ghostscript`, `Adobe Reader`) esté instalado en la máquina que ejecutará el script.

### 3.3. Entorno de Producción
La configuración es idéntica a la de desarrollo, pero se deben tomar las siguientes precauciones:
*   Las credenciales en `credenciales.py` deben apuntar a los **entornos de producción** de la base de datos y la API de Andreani.
*   El script `sync_rotulos_andreani.py` debe ser ejecutado por un **programador de tareas** (como el Programador de Tareas de Windows) con la frecuencia deseada.
*   El script `consultar_estado.py` también debe programarse para ejecutarse periódicamente y mantener actualizados los estados de envío.
*   La cuenta de usuario que ejecuta la tarea programada debe tener **permisos para cambiar la impresora predeterminada** y acceder a las rutas de red de las impresoras.

## 4. Plan de Pruebas (QA)

### 4.1. Pruebas Existentes
El archivo `test_andreani.py` contiene pruebas unitarias básicas de "humo" (smoke tests) para verificar la conectividad.
*   `test_api_connection`: Valida que la clase `AndreaniAPI` pueda inicializarse y obtener un token de autenticación de la API.
*   `test_db_connection`: Valida que la clase `AndreaniDB` pueda establecer una conexión con la base de datos.

### 4.2. Casos de Prueba Manuales

#### Pruebas de Generación de Rótulos
*   **Caso 1: Flujo Completo Exitoso**
    *   **Descripción:** Verificar que un pedido nuevo en la BD se procesa, se imprime y se marca como impreso.
    *   **Pasos:**
        1. Insertar un registro válido en `SEIN_TABLA_TEMPORAL_SCRIPT`.
        2. Ejecutar `sync_rotulos_andreani.py`.
    *   **Criterio de Aceptación:**
        * Se imprime una etiqueta física en la impresora correcta.
        * El campo `IMP_ROT` del pedido se actualiza a `1`.
        * El campo `NUM_SEGUIMIENTO` se guarda correctamente.
        * Los logs muestran un proceso exitoso.

*   **Caso 2: Error de Conexión con la API**
    *   **Descripción:** Simular un fallo en la API de Andreani.
    *   **Pasos:** Modificar temporalmente las credenciales de la API para que fallen.
    *   **Criterio de Aceptación:** El script debe registrar el error y no debe actualizar el pedido en la BD como impreso.

*   **Caso 3: Impresora no disponible**
    *   **Descripción:** Simular un fallo en la impresora.
    *   **Pasos:** Desconectar la impresora o usar una ruta incorrecta en `printer_config.json`.
    *   **Criterio de Aceptación:** El script debe registrar el error de impresión y no debe actualizar el pedido en la BD.

#### Pruebas de Actualización de Estados
*   **Caso 4: Actualización Masiva de Estados**
    *   **Descripción:** Verificar que el sistema actualice correctamente múltiples estados de envío.
    *   **Pasos:**
        1. Asegurarse de tener varios registros con `IMP_ROT = 1`, `NUM_SEGUIMIENTO` válido y `estadoIdEnvio <> 18`.
        2. Ejecutar `python consultar_estado.py --actualizar`.
    *   **Criterio de Aceptación:**
        * Los campos `estadoEnvio`, `estadoIdEnvio` y `fechaEstadoEnvio` se actualizan correctamente.
        * El reporte final muestra el número correcto de envíos actualizados.
        * Los logs muestran información detallada de cada actualización.

*   **Caso 5: Consulta Individual de Estado**
    *   **Descripción:** Verificar que se pueda consultar y actualizar un envío específico.
    *   **Pasos:**
        1. Obtener un `NUM_SEGUIMIENTO` válido de la base de datos.
        2. Ejecutar `python consultar_estado.py --numero_envio <NUM_SEGUIMIENTO>`.
    *   **Criterio de Aceptación:**
        * Se muestra la información del estado en consola.
        * El registro en la base de datos se actualiza con el estado actual.
        * El log confirma la actualización exitosa.

*   **Caso 6: Envíos ya Entregados**
    *   **Descripción:** Verificar que no se consulten envíos ya entregados (`estadoIdEnvio = 18`).
    *   **Pasos:**
        1. Marcar algunos registros con `estadoIdEnvio = 18`.
        2. Ejecutar `python consultar_estado.py --actualizar`.
    *   **Criterio de Aceptación:**
        * Los envíos con `estadoIdEnvio = 18` no son procesados.
        * Solo se actualizan los envíos pendientes.

### 4.3. Estrategia de Pruebas Futuras
*   **Mocking:** Extender las pruebas unitarias para mockear las respuestas de la API de Andreani y la base de datos. Esto permitiría probar la lógica de `sync_rotulos_andreani.py` de forma aislada y sin depender de servicios externos.
*   **Pruebas de Regresión:** Crear pruebas que validen el formato de los datos enviados a la API de Andreani para detectar cambios inesperados.
*   **Pruebas de Impresión:** Crear un script de prueba específico para `impresora.py` que intente imprimir un PDF de prueba con cada uno de los métodos (`ghost`, `adobe`, `win32`) para validar la configuración del entorno.

## 5. Documentación de APIs (Cliente Interno)

Esta sección documenta los métodos de la clase `AndreaniAPI` que actúa como cliente para la API REST externa de Andreani.

---
**Método:** `async def crear_orden_envio(self, data: dict)`
*   **Descripción:** Crea una nueva orden de envío.
*   **Endpoint Andreani:** `POST /v2/ordenes-de-envio`
*   **Parámetros:**
    *   `data` (dict): Un diccionario con la estructura completa de la orden de envío (ver ejemplo abajo).
*   **Respuesta:** Un diccionario con `numeroEnvio` y `numeroAgrupador` si es exitoso, o `None` si falla.
*   **Ejemplo de `data`:**
    ```json
    {
        "contrato": "400021942",
        "origen": { "postal": { ... } },
        "destino": { "postal": { ... } },
        "remitente": { ... },
        "destinatario": [ { ... } ],
        "bultos": [ { ... } ]
    }
    ```

---
**Método:** `async def obtener_etiquetas(self, numeroAgrupador: str)`
*   **Descripción:** Obtiene el contenido binario (PDF) de las etiquetas para un grupo de bultos.
*   **Endpoint Andreani:** `GET /v2/ordenes-de-envio/{numeroAgrupador}/etiquetas`
*   **Parámetros:**
    *   `numeroAgrupador` (str): El identificador del agrupador de bultos.
*   **Respuesta:** `bytes` con el contenido del archivo PDF, o `None` si falla.

---
**Método:** `async def consultar_estado_orden(self, numeroEnvio: str)`
*   **Descripción:** Consulta el estado de una orden de envío ya creada.
*   **Endpoint Andreani:** `GET /v2/ordenes-de-envio/{numeroEnvio}`
*   **Parámetros:**
    *   `numeroEnvio` (str): El número de envío de Andreani.
*   **Respuesta:** Un `string` con el estado de la orden (ej: "Pendiente"), o `None`.

---
**Método:** `async def consultar_estado_envio(self, numeroEnvio: str)`
*   **Descripción:** Realiza el seguimiento (tracking) de un envío.
*   **Endpoint Andreani:** `GET /v2/envios/{numeroEnvio}`
*   **Parámetros:**
    *   `numeroEnvio` (str): El número de envío de Andreani.
*   **Respuesta:** Un `dict` con la información completa del tracking, incluyendo:
    *   `estado` (str): Descripción textual del estado (ej: "Entregado", "En Tránsito").
    *   `estadoId` (int): ID numérico del estado (ej: 18 para "Entregado").
    *   `fechaEstado` (str): Fecha y hora del estado en formato ISO 8601.
    *   Otros campos adicionales con información del destinatario, dirección, etc.
    *   Retorna `None` si falla la consulta.

---
*(Otros métodos como `buscar_sucursales`, `obtener_cotizacion`, etc., siguen un patrón similar.)*

## 6. Consultas SQL del Proyecto

Esta sección documenta las consultas SQL utilizadas en el módulo, definidas en `consultas.py`:

---
**Consulta:** `QRY_GET_DATA_FROM_SEIN`
*   **Descripción:** Obtiene los pedidos pendientes de procesamiento desde la tabla `SEIN_TABLA_TEMPORAL_SCRIPT`.
*   **Filtro:** `IMP_ROT = 0` (pedidos no procesados).
*   **Formato de Salida:** JSON con la estructura requerida por la API de Andreani.

---
**Consulta:** `QRY_UPDATE_IMP_ROT`
*   **Descripción:** Actualiza el estado de impresión de un pedido y almacena el número de seguimiento.
*   **Parámetros:**
    *   `NUM_SEGUIMIENTO`: Número de seguimiento de Andreani.
    *   `NRO_PEDIDO`: Número de pedido interno.
*   **Operación:** `UPDATE SEIN_TABLA_TEMPORAL_SCRIPT SET IMP_ROT = 1, NUM_SEGUIMIENTO = ? WHERE NRO_PEDIDO = ? AND IMP_ROT = 0`

---
**Consulta:** `QRY_GET_ENVIOS_PENDIENTES`
*   **Descripción:** Obtiene los envíos que requieren actualización de estado.
*   **Filtros:**
    *   `IMP_ROT = 1`: Ya fueron procesados y tienen rótulo.
    *   `NUM_SEGUIMIENTO IS NOT NULL`: Tienen número de seguimiento válido.
    *   `estadoIdEnvio <> 18 OR estadoIdEnvio IS NULL`: No están entregados o no tienen estado.
*   **Campos Retornados:** `NRO_PEDIDO`, `NUM_SEGUIMIENTO`.

---
**Consulta:** `QRY_UPDATE_ESTADO_ENVIO`
*   **Descripción:** Actualiza los campos de estado de un envío.
*   **Parámetros:**
    *   `estadoEnvio`: Descripción textual del estado.
    *   `estadoIdEnvio`: ID numérico del estado.
    *   `fechaEstadoEnvio`: Fecha y hora del estado.
    *   `NUM_SEGUIMIENTO`: Número de seguimiento para identificar el registro.
*   **Operación:** `UPDATE SEIN_TABLA_TEMPORAL_SCRIPT SET estadoEnvio = ?, estadoIdEnvio = ?, fechaEstadoEnvio = ? WHERE NUM_SEGUIMIENTO = ?`

## 7. Estados de Envío de Andreani

Los principales estados de envío manejados por el sistema son:

| Estado ID | Descripción | Significado |
|-----------|-------------|-------------|
| 1 | Pendiente | El envío fue creado pero aún no fue despachado |
| 5 | En Tránsito | El envío está en camino al destino |
| 7 | En Distribución | El envío está en el centro de distribución local |
| 18 | Entregado | El envío fue entregado exitosamente (estado final) |
| 20 | Devuelto | El envío fue devuelto al remitente |
| 99 | Incidente | Hubo un problema con el envío |

**Nota:** El estado ID 18 (Entregado) es considerado un estado final, por lo que los envíos con este estado no son consultados en las actualizaciones automáticas.
