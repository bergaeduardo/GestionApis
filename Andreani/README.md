# 📦 Integración con la API de Andreani

Este proyecto proporciona una interfaz robusta y fácil de usar para interactuar con la API de Andreani, permitiéndote gestionar tus envíos de manera eficiente. Con este código, podrás:

*   🔑 Autenticarte y obtener un token de acceso.
*   📍 Buscar sucursales cercanas.
*   💰 Obtener cotizaciones para tus envíos.
*   🚚 Crear órdenes de envío.
*   📊 Consultar el estado de tus órdenes.
*   🏷️ Descargar etiquetas de envío.
*   ℹ️ Consultar el estado de un envío específico.
*   🖼️ Obtener información multimedia de tus envíos.
*   🧾 Descargar remitos digitalizados.
*   ⏳ Rastrear las trazas de tus envíos.

## 🚀 Empezando

### 🛠️ Pre requisitos

Asegúrate de tener instalado lo siguiente antes de comenzar:

*   🐍 **Python 3.6+:**  Necesitarás Python en tu sistema.
*   📦 **`requests`:** Instala la librería con `pip install requests`.
*   🔑 **Credenciales:** Crea un archivo `credenciales.py` con tus credenciales de la API de Andreani:

    ```python
    DATA_QA = {
        "url": "https://apisqa.andreani.com",
        "user": "tu_usuario",
        "passw": "tu_contraseña"
    }
    ```

    **Importante:** Reemplaza `"tu_usuario"` y `"tu_contraseña"` con tus credenciales reales. ¡Guarda este archivo en un lugar seguro!

### ⚙️ Configuración

1.  **Clone (o descarga) el repositorio:**

    ```bash
    git clone <URL_del_repositorio>
    cd <nombre_del_repositorio>
    ```
2.  **Crea `credenciales.py`:**

    En la misma carpeta que `andreani_api.py` y `main.py`, crea el archivo `credenciales.py` con tus credenciales (ver prerrequisitos).
3.  **Instala dependencias:**

    ```bash
    pip install requests
    ```

### 🎬 Uso

1.  **Ejecuta el script:**

    ```bash
    python main.py
    ```

    El script ejecutará una serie de pruebas y mostrará los resultados en la consola.

## 🗂️ Estructura del Código

El proyecto está organizado en los siguientes archivos:

*   **`andreani_api.py`:**
    *   Contiene la clase `AndreaniAPI`, que encapsula todas las interacciones con la API de Andreani.
    *   Incluye métodos para autenticación, consulta de sucursales, cotizaciones, creación de órdenes, etc.
    *   Gestiona errores HTTP y devuelve los datos en formato JSON o contenido de la respuesta (PDF).
*   **`main.py`:**
    *   Importa y utiliza la clase `AndreaniAPI` para realizar operaciones en la API de Andreani.
    *   Incluye ejemplos de uso de cada una de las funcionalidades.
*   **`credenciales.py`:**
    *   Contiene las credenciales de acceso a la API (este archivo debes crearlo tú).

## 🙏 Agradecimiento

Este proyecto ha sido inspirado y se ha apoyado en el excelente trabajo realizado por **Yamila Navas** en su repositorio [API-ANDREANI](https://github.com/Yamila-Navas/API-ANDREANI). ¡Muchas gracias por tu valiosa contribución!

## 🤝 Contribución
1. Haz un Fork del proyecto
2. Crea tu rama de características (git checkout -b feature/AmazingFeature)
3. Realiza tus cambios y haz commit (git commit -m 'Add: AmazingFeature')
4. Push a la rama (git push origin feature/AmazingFeature)
5. Abre un Pull Request

## 📬 Contacto
Para soporte técnico, contactar al departamento de TI.
Email: tu.email@ejemplo.com
LinkedIn: [Tu perfil](URL)
Twitter: [@tuusuario](URL)

¡Gracias por pasar!