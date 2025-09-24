# Sistema de Impresión para GestionAPI

Este documento describe la configuración y uso del sistema de impresión implementado en el módulo `impresora.py`.

## Contenido
1. [Requisitos](#requisitos)
2. [Métodos de Impresión Disponibles](#métodos-de-impresión-disponibles)
3. [Instalación](#instalación)
4. [Uso](#uso)
5. [Configuración](#configuración)
6. [Solución de Problemas](#solución-de-problemas)

## Requisitos

### Para todos los métodos:
- Python 3.8 o superior
- pywin32 (`pip install pywin32`)

### Para el método Adobe Reader:
- Adobe Acrobat Reader DC instalado.

### Para el método Win32:
- Sistema operativo Windows.

### Para el método Ghostscript (Recomendado para servidores):
- Ghostscript instalado. Puedes descargarlo desde [ghostscript.com](https://www.ghostscript.com/releases/gsdnld.html).

## Métodos de Impresión Disponibles

### 1. Ghostscript (Método recomendado para servidor)
- **Método:** `ghost`
- Utiliza Ghostscript para procesar e imprimir archivos PDF directamente desde la línea de comandos.
- **Es el método más robusto y fiable para la impresión silenciosa en un entorno de servidor.**
- No abre ninguna interfaz gráfica.
- Requiere que Ghostscript esté instalado en el sistema.

### 2. Adobe Reader
- **Método:** `adobe`
- Utiliza Adobe Reader en segundo plano.
- **Nota:** Dependiendo de la versión y configuración de Adobe Reader, es posible que la aplicación se abra brevemente, por lo que no es ideal para un entorno de servidor desatendido.
- Alta compatibilidad con formatos PDF.

### 3. Win32 API
- **Método:** `win32`
- Utiliza la API nativa de Windows para la impresión.
- Es rápido y no tiene dependencias externas (más allá de `pywin32`).
- **Nota:** Puede fallar con errores de sistema operativo (`Uno de los dispositivos conectados al sistema no funciona`) si hay problemas con los drivers de la impresora o la configuración de Windows.

## Instalación

1. Instalar dependencias de Python:
```bash
pip install pywin32
```

2. Para el método **Ghostscript**:
   - Descargar e instalar la última versión de Ghostscript desde [su sitio web oficial](https://www.ghostscript.com/releases/gsdnld.html).
   - El script buscará automáticamente la instalación en las rutas estándar (`C:\Program Files\gs\...`).

3. Para el método **Adobe Reader**:
   - Instalar Adobe Acrobat Reader DC.
   - El script intentará localizar la instalación automáticamente.

## Uso

El uso no cambia. El `PrinterManager` seleccionará el método de impresión basado en la configuración.

```python
from GestionAPI.Andreani.impresora import PrinterManager

# El gestor de impresión se inicializa usando la configuración de printer_config.json
printer = PrinterManager()

# Imprimir un archivo
printer.switch_to_label_printer()
printer.print_file("etiqueta.pdf")
printer.restore_default_printer()
```

## Configuración

La forma recomendada de configurar el sistema es a través del archivo `config/printer_config.json`.

**Ejemplo de `config/printer_config.json`:**
```json
```json
{
    "printer": {
        "method": "pdftoprinter",
        "label_printer_path": "\\\\servidor\\nombre_impresora",
        "pdftoprinter_path": "C:\\path\t o\\PDFtoPrinter.exe",
        "margins": "0 0 0 0",
        "copies": 1
    }
}
```
```
- **method**: Puede ser `"ghost"`, `"win32"` o `"adobe"`. Se recomienda `"ghost"` para servidores.
- **label_printer_path**: La ruta de red o nombre exacto de la impresora de etiquetas.

## Solución de Problemas

### La impresión falla o abre una ventana

1.  **Se abre Adobe Reader:**
    - **Causa:** El método de impresión está configurado en `adobe`.
    - **Solución:** Cambia el método a `ghost` en `config/printer_config.json` y asegúrate de que Ghostscript esté instalado.

2.  **Error con el método `win32`:** `(31, 'ShellExecute', 'Uno de los dispositivos conectados al sistema no funciona.')`
    - **Causa:** Es un error a nivel del sistema operativo, probablemente relacionado con los drivers de la impresora o la conexión.
    - **Solución:** Intenta reinstalar los drivers de la impresora. La solución más fiable es cambiar al método `ghost`.

3.  **Error con el método `ghost`:** `GhostScript no encontrado.`
    - **Causa:** Ghostscript no está instalado o no se encuentra en las rutas estándar.
    - **Solución:** Instala Ghostscript desde su [sitio web oficial](https://www.ghostscript.com/releases/gsdnld.html).

4.  **"No se pudo cambiar a la impresora de etiquetas"**
    - **Causa:** El nombre o la ruta en `label_printer_path` no coincide exactamente con el nombre de la impresora en Windows.
    - **Solución:** Ve a `Panel de Control > Dispositivos e impresoras` y copia y pega el nombre exacto de la impresora en el archivo de configuración.
