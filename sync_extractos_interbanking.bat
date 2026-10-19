@echo off
:: Tarea programada — Sincronización diaria de extractos InterBanking
:: Ejecutar: mes anterior completo + mes en curso + purga de históricos
:: %~dp0 resuelve el directorio del bat sin importar la ubicación.

setlocal

set PYTHON="%~dp0env\Scripts\python.exe"
set SCRIPT="%~dp0GestionAPI\InterBanking\sync_extractos_interbanking.py"
set LOG_DIR="%~dp0GestionAPI\InterBanking\logs"

if not exist %LOG_DIR% mkdir %LOG_DIR%

%PYTHON% %SCRIPT% --dos-meses --purgar >> "%~dp0GestionAPI\InterBanking\logs\extractos_cron.log" 2>&1

if %ERRORLEVEL% neq 0 (
    echo [%DATE% %TIME%] ERROR: sync_extractos_interbanking.py falló con código %ERRORLEVEL%
    exit /b %ERRORLEVEL%
)

endlocal
