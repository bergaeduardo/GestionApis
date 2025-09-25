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
|                         |      |                          |      |                             |
+-------------------------+      +--------------------------+      +-----------------------------+
                                                                                |
                                                                                |
                                              +---------------------------------v---------------------------------+
                                              |                                                                   |
                                              |  andreani_api.py (Cliente Asíncrono de API)                       |
                                              |                                                                   |
                                              +---------------------------------^---------------------------------+
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
1.  El script `sync_rotulos_andreani.py` se ejecuta.
2.  Se conecta a la base de datos a través de `db_operations_andreani.py` y obtiene los pedidos pendientes de la tabla `SEIN_TABLA_TEMPORAL_SCRIPT`.
3.  Para cada pedido, invoca de forma asíncrona al cliente `andreani_api.py` para crear una orden de envío en la API de Andreani.
4.  Con el `numeroAgrupador` obtenido, vuelve a llamar a la API para descargar la etiqueta en formato PDF.
5.  El script guarda el PDF en un directorio temporal.
6.  Utiliza el módulo `impresora.py` para gestionar la cola de impresión de Windows, seleccionar la impresora de rótulos y enviar el archivo PDF para su impresión.
7.  Si la impresión es exitosa, actualiza el estado del pedido en la base de datos a través de `db_operations_andreani.py`.
8.  Finalmente, el gestor de impresión restaura la impresora predeterminada del sistema.

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
    *   **Tabla de Origen:** `SEIN_TABLA_TEMPORAL_SCRIPT`. Se espera que contenga una columna con un JSON que representa los pedidos a procesar.
    *   **Campo de Actualización:** `IMP_ROT`. Un flag (probablemente `bit` o `int`) que se establece a `1` cuando un rótulo ha sido impreso.
*   **Métodos Clave:**
    *   `get_data_from_sein()`: Ejecuta la consulta `QRY_GET_DATA_FROM_SEIN` para obtener los pedidos.
    *   `update_imp_rot(nro_pedido)`: Ejecuta `QRY_UPDATE_IMP_ROT` para actualizar el estado de impresión.

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
*   La cuenta de usuario que ejecuta la tarea programada debe tener **permisos para cambiar la impresora predeterminada** y acceder a las rutas de red de las impresoras.

## 4. Plan de Pruebas (QA)

### 4.1. Pruebas Existentes
El archivo `test_andreani.py` contiene pruebas unitarias básicas de "humo" (smoke tests) para verificar la conectividad.
*   `test_api_connection`: Valida que la clase `AndreaniAPI` pueda inicializarse y obtener un token de autenticación de la API.
*   `test_db_connection`: Valida que la clase `AndreaniDB` pueda establecer una conexión con la base de datos.

### 4.2. Casos de Prueba Manuales
*   **Caso 1: Flujo Completo Exitoso**
    *   **Descripción:** Verificar que un pedido nuevo en la BD se procesa, se imprime y se marca como impreso.
    *   **Pasos:**
        1. Insertar un registro válido en `SEIN_TABLA_TEMPORAL_SCRIPT`.
        2. Ejecutar `sync_rotulos_andreani.py`.
    *   **Criterio de Aceptación:**
        * Se imprime una etiqueta física en la impresora correcta.
        * El campo `IMP_ROT` del pedido se actualiza a `1`.
        * Los logs muestran un proceso exitoso.

*   **Caso 2: Error de Conexión con la API**
    *   **Descripción:** Simular un fallo en la API de Andreani.
    *   **Pasos:** Modificar temporalmente las credenciales de la API para que fallen.
    *   **Criterio de Aceptación:** El script debe registrar el error y no debe actualizar el pedido en la BD como impreso.

*   **Caso 3: Impresora no disponible**
    *   **Descripción:** Simular un fallo en la impresora.
    *   **Pasos:** Desconectar la impresora o usar una ruta incorrecta en `printer_config.json`.
    *   **Criterio de Aceptación:** El script debe registrar el error de impresión y no debe actualizar el pedido en la BD.

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
*   **Respuesta:** Un `dict` con la información completa del tracking, o `None`.

---
*(Otros métodos como `buscar_sucursales`, `obtener_cotizacion`, etc., siguen un patrón similar.)*
