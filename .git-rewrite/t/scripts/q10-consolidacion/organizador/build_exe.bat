@echo off
echo ===================================================
echo Compilando OrganizadorQ10 de forma robusta...
echo ===================================================

:: 1. Intentar instalar PyInstaller de forma explícita en el entorno del usuario
python -m pip install --user pyinstaller

:: 2. Ubicar dinámicamente el ejecutable de PyInstaller en la carpeta de Scripts del usuario
:: Esto evita depender enteramente del comando "python -m PyInstaller" si este falla.
SET "PY_SCRIPTS_PATH=%APPDATA%\Python\Python314\Scripts"

if exist "%PY_SCRIPTS_PATH%\pyinstaller.exe" (
    echo [INFO] Detectado PyInstaller en la ruta local de usuario.
    "%PY_SCRIPTS_PATH%\pyinstaller.exe" --clean --onefile --windowed --name "OrganizadorQ10" --add-data "../credenciales_service_account.json;." organizador_q10.py
) else (
    echo [INFO] Intentando compilación directa mediante módulo...
    python -m PyInstaller --clean --onefile --windowed --name "OrganizadorQ10" --add-data "../credenciales_service_account.json;." organizador_q10.py
)

echo ===================================================
echo Proceso finalizado localmente. Verifique sus carpetas.
echo ===================================================
pause