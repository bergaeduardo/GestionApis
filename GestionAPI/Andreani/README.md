# 📦 Sistema de Gestión de Rótulos Andreani

Sistema integral para automatizar el proceso de generación, descarga e impresión de etiquetas de envío mediante la API de Andreani.

## 🚀 Características Principales

- 🔑 **Autenticación automática** con la API de Andreani
- 📍 **Gestión completa de envíos**: creación, consulta y rastreo
- 🏷️ **Descarga e impresión automática** de etiquetas PDF
- �️ **Sistema de impresión robusto** con múltiples métodos
- � **Actualización automática** de estados de envío
- �️ **Herramientas de diagnóstico** integradas

## � Estructura del Proyecto

### Scripts Principales
- **`sync_rotulos_andreani.py`** - Script principal para generar e imprimir rótulos
- **`consultar_estado.py`** - Actualización de estados de envío
- **`andreani_api.py`** - Cliente para la API de Andreani
- **`db_operations_andreani.py`** - Operaciones de base de datos
- **`impresora.py`** - Sistema de impresión multiplataforma

### Herramientas de Diagnóstico
- **`test_rapido.py`** - Verificación rápida del sistema de impresión

### Configuración
- **`config/printer_config.json`** - Configuración de impresión
- **`credenciales.py`** - Credenciales de API (crear manualmente)

## ⚙️ Instalación y Configuración

### 1. Prerrequisitos

#### Software Requerido
- **Python 3.8+**
- **PDFtoPrinter** - Para impresión de PDFs
- **Acceso a base de datos** CENTRAL_LAKERS
- **Impresora de etiquetas** configurada en red

#### Dependencias Python
```bash
pip install aiohttp pyodbc pywin32
```

### 2. Configuración de Credenciales

Crear archivo `credenciales.py`:
```python
DATA_PROD = {
    "url": "https://api.andreani.com",
    "user": "tu_usuario",
    "passw": "tu_contraseña"
}

DATA_QA = {
    "url": "https://apisqa.andreani.com", 
    "user": "tu_usuario_qa",
    "passw": "tu_contraseña_qa"
}
```

### 3. Configuración de Impresión

El archivo `config/printer_config.json` debe contener:
```json
{
    "printer": {
        "method": "pdftoprinter",
        "label_printer_path": "\\\\servidor\\nombre_impresora",
        "copies": 1,
        "adobe_reader_path": "C:\\Program Files (x86)\\Adobe\\Acrobat Reader DC\\Reader\\AcroRd32.exe"
    }
}
```

### 4. Configuración de Windows Defender

⚠️ **IMPORTANTE**: Agregar exclusión en Windows Defender para PDFtoPrinter.exe:

1. Abrir **Windows + I** → **Actualización y seguridad** → **Seguridad de Windows**
2. Ir a **Protección contra virus y amenazas** → **Administrar configuración**  
3. En **Exclusiones** → **Agregar o quitar exclusiones**
4. **Agregar exclusión** → **Archivo** → Seleccionar `C:\Program Files\PDFtoPrinter\PDFtoPrinter.exe`

## 🖨️ Sistema de Impresión

### Métodos Disponibles

#### 1. PDFtoPrinter (Recomendado)
- **Método**: `pdftoprinter`
- Impresión directa sin abrir aplicaciones
- Robusto y eficiente para entornos de servidor
- Requiere exclusión en Windows Defender

#### 2. Adobe Reader  
- **Método**: `adobe`
- Compatible con todos los formatos PDF
- Puede abrir ventanas temporalmente

#### 3. Win32 API
- **Método**: `win32`
- API nativa de Windows
- Rápido pero puede fallar con problemas de drivers

#### 4. Ghostscript
- **Método**: `ghost`  
- Ideal para servidores Linux/Windows
- Requiere instalación de Ghostscript

### Configuración de Impresora

Para configurar la impresora de etiquetas:
1. Verificar nombre exacto en **Panel de Control** → **Dispositivos e impresoras**
2. Actualizar `label_printer_path` en `config/printer_config.json`
3. Para impresoras de red usar formato: `\\\\servidor\\nombre_impresora`

## 🚀 Uso del Sistema

### Ejecutar Generación de Rótulos
```bash
# Activar entorno virtual
env\Scripts\activate

# Ejecutar script principal
python sync_rotulos_andreani.py
```

### Verificar Sistema de Impresión
```bash
# Diagnóstico rápido (recomendado)
python test_rapido.py
```

### Actualizar Estados de Envío
```bash
# Actualización masiva
python consultar_estado.py --actualizar

# Consulta individual  
python consultar_estado.py --numero_envio <numero>
```

## 🔧 Solución de Problemas

### Errores Comunes

#### "ERROR DE IMPRESION"
**Causa**: Windows Defender bloquea PDFtoPrinter  
**Solución**: Agregar exclusión en Windows Defender (ver sección de configuración)

#### "No se pudo cambiar a la impresora de etiquetas"
**Causa**: Nombre de impresora incorrecto  
**Solución**: Verificar nombre exacto en Windows y actualizar configuración

#### Timeouts en impresión
**Causa**: Impresora ocupada o sin papel  
**Solución**: Verificar estado físico de la impresora y conexión de red

#### Error de conexión a base de datos
**Causa**: Credenciales incorrectas o servidor no disponible  
**Solución**: Verificar configuración en `credenciales.py` y conectividad

### Herramientas de Diagnóstico

#### Verificación Rápida
```bash
python test_rapido.py
```
Verifica:
- ✅ Estado de PDFtoPrinter
- ✅ Conectividad con impresora
- ✅ Funcionamiento general del sistema

#### Logs del Sistema
- **Ubicación**: `logs/app.log`
- **Contiene**: Detalles de errores, tiempos de ejecución, estados de impresión

## 📊 Flujo de Trabajo

### 1. Generación de Rótulos
1. **Consulta base de datos** → Obtiene pedidos pendientes
2. **API Andreani** → Crea órdenes de envío  
3. **Descarga PDFs** → Obtiene etiquetas generadas
4. **Impresión** → Envía a impresora de etiquetas
5. **Actualización BD** → Marca como impreso (`IMP_ROT = 1`)

### 2. Seguimiento de Estados  
1. **Consulta envíos** → Pedidos con seguimiento activo
2. **API Andreani** → Obtiene estado actualizado
3. **Actualización BD** → Guarda nuevo estado y fecha

## 📋 Campos de Base de Datos

### Tabla: SEIN_TABLA_TEMPORAL_SCRIPT
- **`IMP_ROT`** - Flag de impresión (0/1)
- **`NUM_SEGUIMIENTO`** - Número de tracking de Andreani  
- **`estadoEnvio`** - Descripción del estado
- **`estadoIdEnvio`** - ID numérico del estado
- **`fechaEstadoEnvio`** - Timestamp último estado

## 🤝 Contribución

1. Fork del proyecto
2. Crear rama de características (`git checkout -b feature/NuevaCaracteristica`)
3. Commit cambios (`git commit -m 'Add: Nueva característica'`)  
4. Push a la rama (`git push origin feature/NuevaCaracteristica`)
5. Crear Pull Request

## 📬 Soporte

Para soporte técnico, contactar al departamento de TI.

## 🙏 Agradecimientos

Proyecto inspirado en el excelente trabajo de **Yamila Navas** en [API-ANDREANI](https://github.com/Yamila-Navas/API-ANDREANI).

---

**Versión del Sistema**: 2.0  
**Última actualización**: Noviembre 2025
