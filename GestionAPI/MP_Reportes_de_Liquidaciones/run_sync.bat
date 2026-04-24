@echo off
:: =============================================================
:: run_sync.bat
:: Inicia el entorno virtual y ejecuta el script de sincronización
:: del Reporte de Liquidaciones de Mercado Pago.
:: =============================================================

:: Moverse a la raíz del proyecto (2 niveles arriba del .bat)
cd /d "%~dp0..\.."

echo [%DATE% %TIME%] Iniciando sincronizacion MP - Reporte de Liquidaciones...

:: Activar entorno virtual
call env\Scripts\activate.bat

:: Ejecutar el script de sincronización
python "GestionAPI\MP_Reportes_de_Liquidaciones\sync_liquidaciones_mp.py"

:: Capturar el código de salida
set EXIT_CODE=%ERRORLEVEL%

if %EXIT_CODE% NEQ 0 (
    echo [%DATE% %TIME%] ERROR: El script termino con codigo %EXIT_CODE%.
) else (
    echo [%DATE% %TIME%] Sincronizacion finalizada exitosamente.
)

exit /b %EXIT_CODE%
