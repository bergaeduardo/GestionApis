# Documentación Técnica - Proyecto Solar

## 1. Arquitectura del Sistema

El sistema de sincronización de Solar es un proceso en batch diseñado para leer información de ventas desde una base de datos local, procesarla y enviarla a una API REST externa.

### 1.1. Diagrama de Componentes y Flujo de Datos

El flujo de trabajo sigue una arquitectura de 3 capas:

1.  **Capa de Datos (Origen):**
    *   **Tecnología:** Microsoft SQL Server.
    *   **Función:** Almacena los datos de ventas en tablas como `EB_T_HistorialSincVentas_Solar` y otras relacionadas (`CTA02`, `CTA03`, etc.).

2.  **Capa de Aplicación (Lógica de Negocio):**
    *   **Tecnología:** Python 3.
    *   **Función:** El script `sync_ventas_Solar.py` actúa como orquestador. Se conecta a la base de datos, extrae las ventas pendientes, las transforma en un formato JSON específico y las envía a la API externa.
    *   **Componentes Clave:**
        *   `sync_ventas_Solar.py`: Script principal que ejecuta el proceso.
        *   `api_client.py`: Clase `SolarApiClient` que gestiona la comunicación con la API REST (autenticación y envío de datos).
        *   `db_operations.py`: Clase `DatabaseConnection` que maneja la conexión y ejecución de consultas en la base de datos.
        *   `consultas.py`: Almacena las complejas consultas SQL para obtener los datos de ventas.
        *   `credenciales.py`: Archivo central para configurar los accesos a la BD y la API.

3.  **Capa Externa (Destino):**
    *   **Tecnología:** API REST.
    *   **URL Base:** `https://conectados.fortinmaure.com.ar/SolutionsRE_BackEnd/api`
    *   **Función:** Recibe los datos de ventas procesados por la aplicación Python.

### 1.2. Patrones Utilizados

*   **Sincronización de Datos en Batch:** El proceso no es en tiempo real. Se ejecuta como una tarea programada o manual que procesa un lote de registros pendientes (`ESTADO_SYNC = 0`).
*   **Repository/Gateway:** Las clases `DatabaseConnection` y `SolarApiClient` actúan como gateways, aislando la lógica de negocio del acceso directo a la base de datos y a la API.

---

## 2. Especificación Técnica / Diseño Detallado

### 2.1. Lógica de Negocio

El proceso sigue los siguientes pasos:

1.  **Inicio:** Se ejecuta el script `sync_ventas_Solar.py`.
2.  **Conexión a BD:** Se establece una conexión con la base de datos MS SQL Server utilizando las credenciales de `LOCALES_LAKERS`.
3.  **Extracción de Datos:**
    *   Se ejecuta `qry_ventasEnc` para obtener los encabezados de las ventas con `ESTADO_SYNC = 0`.
    *   Si no hay ventas, el script finaliza.
    *   Se ejecuta `qry_ventasDetalle` para obtener todas las líneas de detalle de las ventas de los últimos 5 días.
4.  **Autenticación API:** Se obtiene un token de acceso de la API de Solar (`/autenticacion/obtenerTokenAcceso`) usando las credenciales de `API_SOLAR`. Si falla, el proceso se detiene.
5.  **Transformación de Datos:**
    *   Los resultados de las consultas SQL se convierten en diccionarios de Python.
    *   Los detalles de venta se agrupan bajo su correspondiente número de comprobante.
    *   Se construye la estructura final del payload JSON, que contiene un `IdCliente` fijo ("000040") y una lista de `Comprobantes`.
6.  **Envío de Datos:** El payload JSON se envía al endpoint `/monitoring/informarVentas` de la API.
7.  **Actualización de Estado:** Si el envío a la API es exitoso (HTTP 201), se ejecuta una consulta `UPDATE` en la tabla `EB_T_HistorialSincVentas_Solar` para cambiar `ESTADO_SYNC` a 1 en los registros procesados, evitando que se vuelvan a enviar.

### 2.2. Estructuras de Datos

#### Payload JSON para `informarVentas`

```json
{
  "IdCliente": "000040",
  "Comprobantes": [
    {
      "Fecha": "dd-mm-yyyy",
      "Hora": "hh:mm:ss",
      "IdComprobante": "string",
      "PtoVenta": "string",
      "NroComprobante": "string (últimos 12 caracteres)",
      "Detalles": [
        {
          "DescripcionItem": "string (Código de Artículo)",
          "Cantidad": "string",
          "Alicuota": "string",
          "Rubro": "string",
          "ImporteNeto": "string",
          "ImporteImpuestos": "string"
        }
      ],
      "Pagos": [
        {
          "MedioPago": "string",
          "Importe": "string"
        }
      ]
    }
  ]
}
```

---

## 3. Manual de Instalación y Configuración

### 3.1. Requisitos Previos

*   Python 3.x
*   Acceso a la base de datos MS SQL Server.
*   Credenciales para la API de Solar.

### 3.2. Pasos de Instalación

1.  **Clonar el Repositorio:**
    ```bash
    git clone <URL_DEL_REPOSITORIO>
    cd GestionAPI
    ```

2.  **Crear Entorno Virtual (Recomendado):**
    ```bash
    python -m venv env
    source env/bin/activate  # En Windows: env\Scripts\activate
    ```

3.  **Instalar Dependencias:**
    ```bash
    pip install -r requirements.txt
    ```
    Las dependencias clave incluyen: `requests`, `pyodbc`.

### 3.3. Configuración

1.  Navega al archivo `GestionAPI/common/credenciales.py`.
2.  Modifica los diccionarios con los valores correctos para los entornos de desarrollo, testing o producción:
    *   `LOCALES_LAKERS`: Configura las credenciales de la base de datos.
        ```python
        LOCALES_LAKERS = {
            "server": "TU_SERVIDOR_SQL",
            "database": "TU_BASE_DE_DATOS",
            "user": "TU_USUARIO_BD",
            "password": "TU_PASSWORD_BD"
        }
        ```
    *   `API_SOLAR`: Configura las credenciales para la API.
        ```python
        API_SOLAR = {
            "usuario": "TU_USUARIO_API",
            "clave": "TU_CLAVE_API"
        }
        ```

### 3.4. Ejecución

*   **Para ejecutar el proceso de sincronización:**
    ```bash
    python GestionAPI/Solar/sync_ventas_Solar.py
    ```
*   **Para ejecutar las pruebas de conexión:**
    ```bash
    python GestionAPI/Solar/test_conexion_solar.py
    ```

---

## 4. Plan de Pruebas (QA)

### 4.1. Pruebas Existentes

El proyecto incluye un script de "smoke test" (`test_conexion_solar.py`) que verifica la conectividad básica:
*   `test_api_connection`: Intenta obtener un token de la API para validar las credenciales y la conexión.
*   `test_db_connection`: Intenta establecer una conexión con la base de datos para validar la configuración y el acceso.

### 4.2. Casos de Prueba Recomendados

| ID  | Escenario                               | Pasos a Seguir                                                                                             | Resultado Esperado                                                                                              |
| --- | --------------------------------------- | ---------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| 1   | **Éxito - Venta simple**                | 1. Asegurar que hay una venta con `ESTADO_SYNC = 0`.<br>2. Ejecutar `sync_ventas_Solar.py`.                 | 1. El script se ejecuta sin errores.<br>2. La API devuelve HTTP 201.<br>3. `ESTADO_SYNC` se actualiza a 1.      |
| 2   | **Éxito - Sin ventas pendientes**       | 1. Asegurar que no hay ventas con `ESTADO_SYNC = 0`.<br>2. Ejecutar el script.                              | El script muestra el mensaje "No hay ventas pendientes de sincronizar" y finaliza limpiamente.                  |
| 3   | **Fallo - Credenciales API incorrectas**| 1. Modificar `API_SOLAR` con una clave incorrecta.<br>2. Ejecutar el script.                                | 1. El script registra "No se pudo obtener el token de acceso".<br>2. El script finaliza.<br>3. `ESTADO_SYNC` no cambia. |
| 4   | **Fallo - Conexión a BD incorrecta**    | 1. Modificar `LOCALES_LAKERS` con un servidor incorrecto.<br>2. Ejecutar el script.                         | El script registra un error de conexión a la base de datos y finaliza.                                          |
| 5   | **Fallo - API de ventas no disponible** | 1. (Simulado) Modificar la URL de `informarVentas` a un endpoint inválido.<br>2. Ejecutar el script.         | 1. El script registra "Error al informar ventas".<br>2. El script finaliza.<br>3. `ESTADO_SYNC` no cambia.      |

---

## 5. Documentación de APIs (Externa)

Esta sección describe la API de Solar consumida por este sistema.

### Endpoint: `POST /autenticacion/obtenerTokenAcceso`

*   **Descripción:** Autentica al cliente y devuelve un token de acceso tipo Bearer.
*   **URL:** `https://conectados.fortinmaure.com.ar/SolutionsRE_BackEnd/api/autenticacion/obtenerTokenAcceso`
*   **Request Body:**
    ```json
    {
      "usuario": "string",
      "clave": "string"
    }
    ```
*   **Success Response (200 OK):**
    ```json
    {
      "token": "ey..."
    }
    ```

### Endpoint: `POST /monitoring/informarVentas`

*   **Descripción:** Recibe y procesa un lote de comprobantes de venta.
*   **URL:** `https://conectados.fortinmaure.com.ar/SolutionsRE_BackEnd/api/monitoring/informarVentas`
*   **Headers:**
    *   `Authorization`: `Bearer <TOKEN>`
    *   `Content-Type`: `application/json`
*   **Request Body:** Ver estructura detallada en la sección 2.2.
*   **Success Response (201 Created):** El servidor responde con un cuerpo de respuesta que confirma la recepción, pero la condición principal de éxito es el código de estado.
*   **Error Response (4xx, 5xx):** El servidor puede devolver varios códigos de error si el token es inválido, el formato del JSON es incorrecto o hay un problema en el servidor.
