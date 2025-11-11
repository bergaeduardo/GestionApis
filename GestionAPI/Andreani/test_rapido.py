#!/usr/bin/env python3
"""
DIAGNÓSTICO RÁPIDO - SIN VENTANAS DE AYUDA
==========================================

Este script hace un diagnóstico rápido sin mostrar ventanas de PDFtoPrinter.
Perfecto para verificar que todo funcione después de configurar Windows Defender.
"""

import os
import sys
import time
import subprocess
from pathlib import Path

def quick_test():
    """Diagnóstico súper rápido sin ventanas"""
    print("🚀 DIAGNÓSTICO RÁPIDO DE IMPRESIÓN")
    print("=" * 35)
    
    # 1. Verificar PDFtoPrinter
    pdftoprinter_path = r"C:\Program Files\PDFtoPrinter\PDFtoPrinter.exe"
    
    if not os.path.exists(pdftoprinter_path):
        print("❌ PDFtoPrinter no encontrado")
        return False
    
    print("✅ PDFtoPrinter encontrado")
    
    # 2. Verificar impresora de red
    try:
        import win32print
        printer_name = r"\\PC-PEDIDOS-02\ZDesigner GC420t (EPL)"
        hprinter = win32print.OpenPrinter(printer_name)
        printer_info = win32print.GetPrinter(hprinter, 2)
        win32print.ClosePrinter(hprinter)
        
        print(f"✅ Impresora accesible: {printer_name}")
        print(f"📊 Estado: {printer_info['Status']}, Jobs: {printer_info['cJobs']}")
        
    except Exception as e:
        print(f"❌ Error accediendo a impresora: {e}")
        return False
    
    # 3. Prueba rápida de PDFtoPrinter (sin ventanas)
    print("⏳ Probando PDFtoPrinter (modo silencioso)...")
    
    try:
        # Crear PDF mínimo
        temp_dir = Path(__file__).parent / "temp"
        temp_dir.mkdir(exist_ok=True)
        test_pdf = temp_dir / "test_quick.pdf"
        
        # PDF ultra-minimal
        minimal_pdf = b"""%PDF-1.0
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 100]>>endobj
xref 0 4
0000000000 65535 f 
0000000010 00000 n 
0000000053 00000 n 
0000000100 00000 n 
trailer<</Size 4/Root 1 0 R>>
startxref 159
%%EOF"""
        
        with open(test_pdf, "wb") as f:
            f.write(minimal_pdf)
        
        # Probar impresión real (modo silencioso)
        command = [
            pdftoprinter_path,
            str(test_pdf),
            "-printer", printer_name,
            "/s"  # Modo silencioso si está disponible
        ]
        
        start_time = time.time()
        result = subprocess.run(command, 
                              capture_output=True, 
                              text=True, 
                              timeout=30,
                              creationflags=subprocess.CREATE_NO_WINDOW)
        
        elapsed_time = time.time() - start_time
        
        # Limpiar archivo temporal
        test_pdf.unlink()
        
        print(f"⏱️  Tiempo: {elapsed_time:.1f}s")
        print(f"📊 Return code: {result.returncode}")
        
        if result.returncode == 0:
            print("✅ PRUEBA DE IMPRESIÓN EXITOSA")
            return True
        else:
            print("⚠️  Error en impresión")
            if result.stderr:
                print(f"❌ Error: {result.stderr[:100]}")
            return False
            
    except subprocess.TimeoutExpired:
        print("⏰ Timeout en impresión")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("📍 Diagnóstico después de configurar Windows Defender")
    print("🎯 Objetivo: Verificar que todo funcione sin ventanas molestas\n")
    
    success = quick_test()
    
    print("\n" + "=" * 35)
    if success:
        print("🎉 ¡TODO FUNCIONANDO!")
        print("✅ Puedes ejecutar sync_rotulos_andreani.py")
        print("💡 El sistema de impresión está listo")
    else:
        print("❌ PROBLEMAS DETECTADOS")
        print("🔧 Revisa la configuración o ejecuta diagnostico_impresion.py")
    
    print("\n💭 Nota: Para problemas persistentes:")
    print("   • Verificar estado físico de la impresora")
    print("   • Revisar conexión de red")
    print("   • Consultar logs en logs/app.log")

if __name__ == "__main__":
    main()