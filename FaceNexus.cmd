@echo off
setlocal EnableExtensions
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
set "PY=%ROOT%\.venv\Scripts\python.exe"
set "VAULT=V:\FaceNexus"

if not exist "%PY%" (
    echo Falta el entorno virtual .venv. Prepara el entorno en el repositorio.
    echo Carpeta: "%ROOT%"
    pause
    exit /b 1
)
if not exist "%VAULT%\" (
    echo No esta montado V:\FaceNexus. Monta el volumen VeraCrypt y vuelve a abrir FaceNexus.
    pause
    exit /b 1
)

cd /d "%ROOT%"
"%PY%" -m scripts.operator_ui --vault "%VAULT%" %*
set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
    echo FaceNexus termino con error %ERR%.
    pause
)
exit /b %ERR%
