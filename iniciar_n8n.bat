@echo off
chcp 65001 >nul

echo.
echo ==========================================
echo   n8n - Bot Q10 Fundacion ROFE
echo ==========================================
echo.

:: Ruta a cloudflared (instalado via winget)
set "CF_EXE=%LOCALAPPDATA%\Microsoft\WinGet\Packages\Cloudflare.cloudflared_Microsoft.Winget.Source_8wekyb3d8bbwe\cloudflared.exe"
set "CF_LOG=%TEMP%\cloudflared_n8n.log"

:: Leer variables del .env de q10-consolidacion (TELEGRAM_BOT_TOKEN, N8N_API_KEY, etc.)
set "ENV_FILE=%~dp0scripts\q10-consolidacion\.env"
for /f "usebackq tokens=1,* delims==" %%A in ("%ENV_FILE%") do (
    if not "%%A"=="" (
        echo %%A | findstr /b "#" >nul 2>&1 || set "%%A=%%B"
    )
)

:: NODES_EXCLUDE=[] re-habilita executeCommand (desactivado por defecto en n8n 2.x)
set "NODES_EXCLUDE=[]"
:: Necesario para redes con proxy corporativo que intercepta HTTPS
set "NODE_TLS_REJECT_UNAUTHORIZED=0"

echo [1/4] Iniciando Cloudflare Tunnel...
del /f /q "%CF_LOG%" >nul 2>&1
start /B "" "%CF_EXE%" tunnel --url http://localhost:5678 --no-autoupdate > "%CF_LOG%" 2>&1

:: Esperar hasta 20s a que cloudflared publique la URL HTTPS
set "CF_URL="
set /a intentos=0
:esperar_url
timeout /t 2 /nobreak >nul
set /a intentos+=1
for /f "tokens=*" %%L in ('findstr /i "trycloudflare.com" "%CF_LOG%" 2^>nul') do (
    for /f "tokens=3" %%U in ("%%L") do set "CF_URL=%%U"
)
if defined CF_URL goto :url_ok
if %intentos% LSS 10 goto :esperar_url
echo ERROR: No se obtuvo URL de Cloudflare en 20 segundos.
echo Verifica que cloudflared este instalado y que haya conexion a internet.
pause
exit /b 1

:url_ok
echo   URL Cloudflare: %CF_URL%
set "WEBHOOK_URL=%CF_URL%"
echo.

echo [2/4] Iniciando n8n con WEBHOOK_URL=%CF_URL%...
echo   Editor local:  http://localhost:5678
echo   Editor remoto: %CF_URL%
echo.

start /B "" "C:\nvm4w\nodejs\n8n.cmd" start

:: Esperar a que n8n este listo (healthcheck)
echo [3/4] Esperando que n8n este listo...
set /a espera=0
:esperar_n8n
timeout /t 3 /nobreak >nul
set /a espera+=1
curl -s http://localhost:5678/healthz >nul 2>&1
if %errorlevel% EQU 0 goto :n8n_ok
if %espera% LSS 15 goto :esperar_n8n
echo AVISO: n8n tardo mas de lo esperado. Continuando de todas formas.
:n8n_ok
echo   n8n listo.

:: Activar el workflow y registrar el webhook con Telegram
echo [4/4] Activando workflow y registrando webhook con Telegram...
timeout /t 3 /nobreak >nul
curl -s -X POST "http://localhost:5678/api/v1/workflows/Rblg81qifVshsRae/activate" ^
     -H "X-N8N-API-KEY: %N8N_API_KEY%" ^
     -H "Content-Type: application/json" >nul 2>&1
echo   Workflow activado. Bot Telegram escuchando.
echo.
echo ==========================================
echo   Sistema activo. No cerrar esta ventana.
echo   Ctrl+C para detener todo.
echo ==========================================
echo.

:loop
timeout /t 60 /nobreak >nul
curl -s http://localhost:5678/healthz >nul 2>&1
if %errorlevel% NEQ 0 (
    echo AVISO: n8n no responde. Reinicia el script.
    pause
    exit /b 1
)
goto :loop
