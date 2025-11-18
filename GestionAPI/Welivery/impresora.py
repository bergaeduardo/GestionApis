"""
Módulo para gestionar impresoras en Windows.
Este módulo proporciona una interfaz para manejar la configuración de impresoras,
especialmente útil para la impresión de etiquetas y rotulación.
"""

import win32print
import win32api
import win32ui
import logging
import subprocess
import os
import json
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Union
from pathlib import Path

logger = logging.getLogger(__name__)

class PrintMethod(Enum):
    """Enumeration of available printing methods"""
    WIN32 = "win32"
    ADOBE = "adobe"
    GHOST = "ghost"
    PDFTOPRINTER = "pdftoprinter"

class PrinterError(Exception):
    """Custom exception for printer-related errors"""
    pass

class BasePrinter(ABC):
    """Abstract base class for printer implementations"""
    
    @abstractmethod
    def print_file(self, file_path: Union[str, Path], copies: int = 1) -> bool:
        """Print a file using the specific implementation"""
        pass

class Win32Printer(BasePrinter):
    """Implementation of printing using win32api"""
    
    def print_file(self, file_path: Union[str, Path], copies: int = 1) -> bool:
        try:
            file_path = str(Path(file_path).resolve())
            
            if not os.path.exists(file_path):
                logger.error(f"Win32Printer: El archivo no existe - {file_path}")
                return False
            
            printer_name = win32print.GetDefaultPrinter()
            logger.debug(f"Win32Printer: Imprimiendo en {printer_name}")
            
            # Inicializar objeto de impresión
            win32api.ShellExecute(
                0,                  # Handle parent (0 = desktop)
                "printto",          # Operación
                file_path,          # Archivo a imprimir
                '"%s"' % printer_name,  # Impresora
                ".",                # Directorio de trabajo
                0                   # Mostrar la ventana (0 = oculta)
            )
            
            logger.info(f"Archivo {file_path} enviado a imprimir usando Win32API")
            return True
            
        except win32api.error as e:
            logger.error(f"Win32API error al imprimir: Código {e.winerror} - {e.strerror}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Error inesperado al imprimir usando Win32API: {type(e).__name__}: {e}", exc_info=True)
            return False

class GhostPrinter(BasePrinter):
    """Implementation of printing using GhostScript"""
    
    def __init__(self):
        self._gsprint_path = self._find_gsprint()
    
    def _find_gsprint(self) -> str:
        """Find GSPrint installation"""
        common_paths = [
            r"C:\Program Files\gs\gs*\bin\gswin64c.exe",
            r"C:\Program Files (x86)\gs\gs*\bin\gswin32c.exe"
        ]
        
        # Buscar gsprint en las rutas comunes
        import glob
        for path_pattern in common_paths:
            matches = glob.glob(path_pattern)
            if matches:
                # Tomar la versión más reciente
                return sorted(matches)[-1]
                
        raise PrinterError(
            "GhostScript no encontrado. Por favor instálalo desde:\n"
            "https://www.ghostscript.com/releases/gsdnld.html"
        )
    
    def print_file(self, file_path: Union[str, Path], copies: int = 1) -> bool:
        try:
            file_path = str(Path(file_path).resolve())
            printer_name = win32print.GetDefaultPrinter()
            
            command = [
                self._gsprint_path,
                "-dPDFFitPage",
                "-dNOPAUSE",
                "-dBATCH",
                "-dNOPROMPT",
                f"-sDEVICE=mswinpr2",
                f"-sOutputFile=%printer%{printer_name}",
                file_path,
                "-c",
                "quit"
            ]
            
            logger.debug(f"Imprimiendo con GhostScript: {' '.join(command)}")
            
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            if result.returncode == 0:
                logger.info(f"Archivo {file_path} enviado a imprimir usando GhostScript")
                return True
            else:
                logger.error(f"Error al imprimir usando GhostScript: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error al imprimir usando GhostScript: {e}")
            return False

class PDFtoPrinterPrinter(BasePrinter):
    """Implementation of printing using PDFtoPrinter"""

    def __init__(self):
        self._pdftoprinter_path = self._find_pdftoprinter()

    def _find_pdftoprinter(self) -> str:
        """Find PDFtoPrinter installation"""
        common_paths = [
            r"C:\Program Files\PDFtoPrinter\PDFtoPrinter.exe",
            r"C:\Program Files (x86)\PDFtoPrinter\PDFtoPrinter.exe",
        ]
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        from shutil import which
        if which("PDFtoPrinter.exe"):
            return "PDFtoPrinter.exe"

        raise PrinterError("PDFtoPrinter.exe no encontrado en rutas comunes o en el PATH.")


    def print_file(self, file_path: Union[str, Path], copies: int = 1) -> bool:
        try:
            file_path = str(Path(file_path).resolve())
            printer_name = win32print.GetDefaultPrinter()

            command = [
                self._pdftoprinter_path,
                file_path,
                "-printer",
                printer_name
            ]
            if copies > 1:
                command.append("-copies")
                command.append(str(copies))

            logger.debug(f"Imprimiendo con PDFtoPrinter: {' '.join(command)}")

            # Configuración mejorada para manejar SmartScreen y timeouts
            import time
            max_attempts = 3
            base_timeout = 30
            
            for attempt in range(max_attempts):
                try:
                    # Incrementar timeout en cada intento
                    timeout = base_timeout * (attempt + 1)
                    logger.debug(f"Intento {attempt + 1}/{max_attempts} con timeout de {timeout}s")
                    
                    result = subprocess.run(
                        command,
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    break  # Si llegamos aquí, el comando se ejecutó sin timeout
                    
                except subprocess.TimeoutExpired:
                    if attempt < max_attempts - 1:
                        logger.warning(f"Timeout en intento {attempt + 1}, reintentando...")
                        time.sleep(2)  # Pausa entre intentos
                        continue
                    else:
                        logger.error(f"PDFtoPrinter timeout después de {max_attempts} intentos")
                        logger.error("POSIBLE CAUSA: Windows Defender SmartScreen bloqueando PDFtoPrinter")
                        logger.error("SOLUCIÓN: Ejecutar configurar_defender.py como administrador")
                        return False

            if result.returncode == 0:
                logger.info(f"Archivo {file_path} enviado a imprimir usando PDFtoPrinter")
                if result.stdout:
                    logger.debug(f"PDFtoPrinter stdout: {result.stdout}")
                return True
            else:
                error_msg = f"Error al imprimir usando PDFtoPrinter - ReturnCode: {result.returncode}"
                if result.stdout:
                    error_msg += f"\nStdout: {result.stdout.strip()}"
                if result.stderr:
                    error_msg += f"\nStderr: {result.stderr.strip()}"
                    
                # Detectar error específico de SmartScreen
                if "no se reconoce" in result.stderr.lower() or "access denied" in result.stderr.lower():
                    error_msg += "\n⚠️  POSIBLE BLOQUEO DE WINDOWS DEFENDER SMARTSCREEN"
                    error_msg += "\n🔧 SOLUCIÓN: Ejecutar configurar_defender.py como administrador"
                    
                logger.error(error_msg)
                return False
                
        except FileNotFoundError as e:
            logger.error(f"PDFtoPrinter.exe no encontrado o archivo PDF no existe: {e}")
            return False
        except Exception as e:
            logger.error(f"Error inesperado al imprimir con PDFtoPrinter: {type(e).__name__}: {e}", exc_info=True)
            return False

class AdobePrinter(BasePrinter):
    """Implementation of printing using Adobe Reader"""
    
    def __init__(self):
        self._adobe_path = self._find_adobe_reader()
    
    def _find_adobe_reader(self) -> str:
        """Find Adobe Reader installation path"""
        # 1. Primero buscar en la variable de entorno
        adobe_path = os.environ.get('ADOBE_READER_PATH')
        if adobe_path and os.path.exists(adobe_path):
            return adobe_path

        # 2. Buscar en configuración si existe
        config_path = os.path.join(os.path.dirname(__file__), 'config', 'printer_config.json')
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    adobe_path = config.get('printer', {}).get('adobe_reader_path')
                    if adobe_path and os.path.exists(adobe_path):
                        return adobe_path
            except Exception as e:
                logger.warning(f"Error al leer configuración de Adobe Reader: {e}")

        # 3. Buscar en rutas comunes
        common_paths = [
            r"C:\Program Files (x86)\Adobe\Acrobat Reader DC\Reader\AcroRd32.exe",
            r"C:\Program Files\Adobe\Acrobat Reader DC\Reader\AcroRd32.exe",
            r"C:\Program Files\Adobe\Acrobat Reader\Reader\AcroRd32.exe",
            r"C:\Program Files (x86)\Adobe\Acrobat Reader\Reader\AcroRd32.exe",
            # Buscar en todas las versiones posibles de Adobe Reader
            *[f"C:\Program Files (x86)\Adobe\Reader\{v}\Reader\AcroRd32.exe" for v in range(8, 13)],
            *[f"C:\Program Files\Adobe\Reader\{v}\Reader\AcroRd32.exe" for v in range(8, 13)]
        ]
        
        # 4. Buscar en el registro de Windows si las rutas anteriores fallan
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\AcroRd32.exe") as key:
                path = winreg.QueryValue(key, None)
                if path and os.path.exists(path):
                    return path
        except Exception:
            pass

        # 5. Buscar en las rutas comunes
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        raise PrinterError(
            "Adobe Reader no encontrado. Por favor, especifica la ruta correcta usando:\n"
            "1. Variable de entorno ADOBE_READER_PATH\n"
            "2. Archivo de configuración config/printer_config.json\n"
            "3. O asegúrate de que Adobe Reader esté instalado en una de las rutas estándar"
        )
    
    def print_file(self, file_path: Union[str, Path], copies: int = 1) -> bool:
        try:
            # Verificaciones previas
            file_path = str(Path(file_path).resolve())
            if not os.path.exists(file_path):
                logger.error(f"AdobePrinter: El archivo no existe: {file_path}")
                return False
            
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                logger.error(f"AdobePrinter: El archivo está vacío (0 bytes): {file_path}")
                return False
                
            logger.debug(f"AdobePrinter: Archivo validado - {file_path} ({file_size} bytes)")
                
            # Verificar que la impresora predeterminada esté configurada
            current_printer = win32print.GetDefaultPrinter()
            if not current_printer:
                logger.error("AdobePrinter: No hay impresora predeterminada configurada")
                return False
                
            logger.debug(f"AdobePrinter: Impresora actual: {current_printer}")
            
            # Pausa de 2 segundos antes de imprimir
            import time
            time.sleep(2)

            # Parámetros optimizados para impresión silenciosa
            command = [
                self._adobe_path,
                "/s",    # Modo silencioso
                "/h",    # Ocultar la aplicación
                "/t",    # Imprimir a una impresora específica
                file_path,
                current_printer # Imprimir a la impresora especificada
            ]
            
            logger.debug(f"AdobePrinter: Ejecutando comando: {' '.join(command)}")
            
            # Ejecutar Adobe Reader de forma silenciosa en segundo plano
            process = subprocess.Popen(
                command,
                creationflags=subprocess.CREATE_NO_WINDOW,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            logger.info(f"Archivo {file_path} enviado a imprimir usando Adobe Reader (PID: {process.pid}).")
            logger.warning("Los errores de impresión de Adobe Reader no se capturarán directamente en este modo.")
            return True
                
        except FileNotFoundError as e:
            logger.error(f"AdobePrinter: Adobe Reader no encontrado o archivo no existe: {e}", exc_info=True)
            return False
        except subprocess.CalledProcessError as e:
            logger.error(f"AdobePrinter: Error al ejecutar Adobe Reader - ReturnCode: {e.returncode}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"AdobePrinter: Error inesperado - {type(e).__name__}: {e}", exc_info=True)
            return False

class PrinterManager:
    """
    Clase para gestionar la configuración de impresoras en Windows.
    
    Esta clase proporciona métodos para cambiar entre impresoras,
    guardar y restaurar la configuración de impresora predeterminada,
    y obtener información sobre las impresoras del sistema.
    """
    
    def __init__(self, label_printer_path: Optional[str] = None, 
                 print_method: Union[str, PrintMethod] = None):
        """
        Inicializa el gestor de impresoras. 
        
        Args:
            label_printer_path (str, optional): Ruta de la impresora de etiquetas.
                Si se proporciona, anula la configuración del archivo JSON.
            print_method (Union[str, PrintMethod], optional): Método de impresión a utilizar.
                Si se proporciona, anula la configuración del archivo JSON.
        """
        # 1. Cargar configuración desde el archivo JSON
        config_path = os.path.join(os.path.dirname(__file__), 'config', 'printer_config.json')
        config_method = None
        config_label_printer = None

        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f).get('printer', {})
                    config_method = config.get('method')
                    config_label_printer = config.get('label_printer_path')
            except Exception as e:
                logger.warning(f"Error al leer el archivo de configuración {config_path}: {e}")

        # 2. Determinar la configuración final, dando prioridad a los argumentos del constructor
        final_print_method = print_method or config_method or PrintMethod.ADOBE
        self._label_printer = label_printer_path or config_label_printer
        self._original_printer = None

        # 3. Configurar el método de impresión
        if isinstance(final_print_method, str):
            try:
                self._print_method = PrintMethod(final_print_method.lower())
            except ValueError:
                logger.warning(f"Método de impresión '{final_print_method}' no válido. Usando Adobe.")
                self._print_method = PrintMethod.ADOBE
        else:
            self._print_method = final_print_method
            
        # 4. Inicializar el printer específico
        try:
            if self._print_method == PrintMethod.WIN32:
                self._printer = Win32Printer()
            elif self._print_method == PrintMethod.GHOST:
                self._printer = GhostPrinter()
            elif self._print_method == PrintMethod.PDFTOPRINTER:
                self._printer = PDFtoPrinterPrinter()
            else: # Incluye ADOBE y cualquier otro caso por defecto
                self._printer = AdobePrinter()
        except PrinterError as e:
            logger.error(f"Error al inicializar el método de impresión {self._print_method.value}: {e}")
            logger.info("Cambiando al método alternativo de impresión")
            
            # Intentar método alternativo (simple fallback)
            self._print_method = (PrintMethod.ADOBE if self._print_method != PrintMethod.ADOBE 
                                else PrintMethod.WIN32)
            try:
                self._printer = (AdobePrinter() if self._print_method == PrintMethod.ADOBE 
                               else Win32Printer())
            except PrinterError as inner_e:
                logger.error(f"Error al inicializar el método alternativo: {inner_e}")
                raise e # Relanzar la excepción original
    
    @property
    def current_printer(self) -> str:
        """
        Obtiene el nombre de la impresora actualmente establecida como predeterminada.
        
        Returns:
            str: Nombre de la impresora predeterminada actual.
        """
        return win32print.GetDefaultPrinter()
    
    @property
    def label_printer(self) -> Optional[str]:
        """
        Obtiene la ruta de la impresora de etiquetas configurada.
        
        Returns:
            Optional[str]: Ruta de la impresora de etiquetas o None si no está configurada.
        """
        return self._label_printer
    
    def set_label_printer(self, printer_path: str) -> None:
        """
        Establece la ruta de la impresora de etiquetas. 
        
        Args:
            printer_path (str): Ruta completa de la impresora de etiquetas.
                Ejemplo: "\\\\192.168.0.64\\ZDesigner GC420t (EPL)"
        """
        self._label_printer = printer_path
        logger.info(f"Impresora de etiquetas configurada: {printer_path}")
    
    def switch_to_label_printer(self) -> bool:
        """
        Cambia la impresora predeterminada a la impresora de etiquetas.
        
        Returns:
            bool: True si el cambio fue exitoso, False en caso contrario.
        
        Raises:
            ValueError: Si no se ha configurado una impresora de etiquetas.
        """
        if not self._label_printer:
            raise ValueError("No se ha configurado una impresora de etiquetas")
        
        try:
            # Verificar si la impresora existe en el sistema
            printers = self.list_printers()
            printer_names = [p['name'] for p in printers]
            logger.debug(f"Impresoras disponibles: {printer_names}")
            
            if self._label_printer not in printer_names:
                logger.error(f"La impresora {self._label_printer} no está instalada en el sistema")
                logger.info("Impresoras disponibles:")
                for printer in printers:
                    logger.info(f"- {printer['name']} ({printer['port']})")
                return False
                
            # Verificar si podemos abrir la impresora
            try:
                hprinter = win32print.OpenPrinter(self._label_printer)
                win32print.ClosePrinter(hprinter)
            except Exception as e:
                logger.exception(f"No se puede acceder a la impresora: {self._label_printer}")
                return False
            
            # Guardar la impresora actual
            try:
                self._original_printer = win32print.GetDefaultPrinter()
                logger.debug(f"Impresora original: {self._original_printer}")
            except Exception as e:
                logger.warning(f"No se pudo obtener la impresora predeterminada actual: {e}")
                self._original_printer = None
            
            # Intentar cambiar la impresora
            try:
                win32print.SetDefaultPrinter(self._label_printer)
                current = win32print.GetDefaultPrinter()
                if current == self._label_printer:
                    logger.info(f"Cambiado exitosamente a impresora de etiquetas: {self._label_printer}")
                    return True
                else:
                    logger.error(f"La impresora no se cambió correctamente. Se intentó establecer: {self._label_printer}, pero la actual es: {current}")
                    return False
            except Exception as e:
                logger.exception(f"Error al establecer la impresora predeterminada: {self._label_printer}. Verifica que tienes permisos de administrador o los permisos necesarios para cambiar la impresora")
                return False
                
        except Exception as e:
            logger.exception(f"Error inesperado al cambiar la impresora a: {self._label_printer}")
            return False
    
    def restore_default_printer(self) -> bool:
        """
        Restaura la impresora predeterminada original.
        
        Returns:
            bool: True si la restauración fue exitosa, False en caso contrario.
        """
        if not self._original_printer:
            logger.warning("No hay impresora original para restaurar")
            return False
        
        try:
            win32print.SetDefaultPrinter(self._original_printer)
            logger.info(f"Restaurada impresora predeterminada: {self._original_printer}")
            self._original_printer = None
            return True
        except Exception as e:
            logger.error(f"Error al restaurar impresora predeterminada: {e}")
            return False
    
    def print_file(self, file_path: Union[str, Path], copies: int = 1) -> bool:
        """
        Imprime un archivo usando el método de impresión configurado.
        
        Args:
            file_path (Union[str, Path]): Ruta al archivo a imprimir
            copies (int, optional): Número de copias a imprimir. Por defecto 1.
            
        Returns:
            bool: True si la impresión fue exitosa, False en caso contrario.
        """
        return self._printer.print_file(file_path, copies)
    
    @staticmethod
    def list_printers() -> list:
        """
        Obtiene una lista de todas las impresoras instaladas en el sistema.
        
        Returns:
            list: Lista de diccionarios con información de las impresoras.
                Cada diccionario contiene:
                - name: Nombre de la impresora
                - port: Puerto de la impresora
                - description: Descripción de la impresora
        """
        printer_info = []
        
        try:
            for printer in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | 
                                                 win32print.PRINTER_ENUM_CONNECTIONS):
                info = {
                    'name': printer[2] if len(printer) > 2 else 'Desconocido',
                    'port': printer[1] if len(printer) > 1 else 'Desconocido',
                    'description': printer[4] if len(printer) > 4 else 'Sin descripción'
                }
                printer_info.append(info)
                logger.debug(f"Impresora encontrada: {info}")
            return printer_info
        except Exception as e:
            logger.error(f"Error al listar impresoras: {e}")
            return []

# Para mantener compatibilidad con el código existente
def rotuladora():
    """
    Función heredada para mantener compatibilidad con código existente.
    Cambia a la impresora de etiquetas y retorna la impresora original.
    
    Returns:
        str: Nombre de la impresora original
    """
    printer_manager = PrinterManager("\\pc-pedidos-02\\ZDesigner GC420t (EPL)")
    printer_manager.switch_to_label_printer()
    return printer_manager.current_printer

def predet(currentprinter):
    """
    Función heredada para mantener compatibilidad con código existente.
    Restaura la impresora predeterminada.
    
    Args:
        currentprinter (str): Nombre de la impresora a restaurar
    """
    win32print.SetDefaultPrinter(currentprinter)

def mensaje():
    """
    Función heredada para mantener compatibilidad con código existente.
    Retorna un mensaje con la impresora actual.
    
    Returns:
        str: Mensaje con el nombre de la impresora actual
    """
    return 'Impresora: ' + win32print.GetDefaultPrinter()