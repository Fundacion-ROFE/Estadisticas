@echo off
chcp 65001 >nul

echo.
echo ==========================================
echo   n8n - Fundacion ROFE / Jovenes creaTIvos
echo ==========================================
echo.

:: ---------------------------------------------------------------------------
:: Tunel: ngrok con DOMINIO FIJO (reemplazo de cloudflared desde 2026-07).
:: El tunel se llama "n8n" y esta definido en %LOCALAPPDATA%\ngrok\ngrok.yml:
::     tunnels:
::       n8n:
::         proto: http
::         addr: 5678
::         domain: ergonomic-absinthe-refract.ngrok-free.dev
:: Al ser fijo, WEBHOOK_URL ya no se descubre parseando logs: es constante.
:: Eso hace PERMANENTE el webhook de Zoom (antes cambiaba en cada arranque).
:: ---------------------------------------------------------------------------
set "NGROK_EXE=%LOCALAPPDATA%\Microsoft\WinGet\Links\ngrok.exe"
set "NGROK_TUNNEL=n8n"
set "WEBHOOK_URL=https://ergonomic-absinthe-refract.ngrok-free.dev"

:: Leer variables del .env de q10-consolidacion (TELEGRAM_BOT_TOKEN, N8N_API_KEY, etc.)
set "ENV_FILE=%~dp0scripts\q10-consolidacion\.env"
for /f "usebackq tokens=1,* delims==" %%A in ("%ENV_FILE%") do (
    if not "%%A"=="" (
        echo %%A | findstr /b "#" >nul 2>&1 || set "%%A=%%B"
    )
)

:: Leer variables del .env de zoom-asistencia (ZOOM_WEBHOOK_SECRET_TOKEN, etc.)
set "ENV_FILE_ZOOM=%~dp0scripts\zoom-asistencia\.env"
for /f "usebackq tokens=1,* delims==" %%A in ("%ENV_FILE_ZOOM%") do (
    if not "%%A"=="" (
        echo %%A | findstr /b "#" >nul 2>&1 || set "%%A=%%B"
    )
)

:: NODES_EXCLUDE=[] re-habilita executeCommand (desactivado por defecto en n8n 2.x)
set "NODES_EXCLUDE=[]"
:: Necesario para redes con proxy corporativo que intercepta HTTPS
set "NODE_TLS_REJECT_UNAUTHORIZED=0"
:: Desactiva telemetria de PostHog (us.i.posthog.com bloqueado en red corporativa)
set "N8N_DIAGNOSTICS_ENABLED=false"
:: Sin esto n8n usa America/New_York en los Schedule Triggers
set "GENERIC_TIMEZONE=America/Bogota"
:: Git 100% desatendido: nunca colgarse esperando un prompt de credencial
:: (executeCommand con git push heredaria este entorno como hijo de n8n)
set "GCM_INTERACTIVE=never"
set "GIT_TERMINAL_PROMPT=0"

echo [1/4] Iniciando tunel ngrok (dominio fijo)...
tasklist /FI "IMAGENAME eq ngrok.exe" /NH 2>nul | findstr /i "ngrok" >nul 2>&1
if %errorlevel% EQU 0 (
    echo   ngrok ya estaba corriendo. Se reutiliza.
) else (
    start /B "" "%NGROK_EXE%" start %NGROK_TUNNEL%
    timeout /t 5 /nobreak >nul
    echo   ngrok iniciado.
)
echo   URL publica: %WEBHOOK_URL%
echo.

echo [2/4] Iniciando n8n...
echo   Editor local:  http://localhost:5678
echo   Editor remoto: %WEBHOOK_URL%
echo.

:: Matar instancia anterior de n8n (para que la nueva herede el entorno correcto)
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"name='node.exe'\" | Where-Object { $_.CommandLine -like '*n8n*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
timeout /t 3 /nobreak >nul

start /B "" "C:\nvm4w\nodejs\n8n.cmd" start

:: Esperar a que n8n este listo (healthcheck). Arranque tipico: 60-70 s.
echo [3/4] Esperando que n8n este listo (puede tardar ~70s)...
set /a espera=0
:esperar_n8n
timeout /t 5 /nobreak >nul
set /a espera+=1
curl -s http://localhost:5678/healthz >nul 2>&1
if %errorlevel% EQU 0 goto :n8n_ok
if %espera% LSS 24 goto :esperar_n8n
echo AVISO: n8n tardo mas de 120s. Continuando de todas formas.
:n8n_ok
echo   n8n listo.

:: Activar el workflow del bot y registrar el webhook con Telegram
echo [4/4] Activando workflow del bot Q10...
timeout /t 3 /nobreak >nul
curl -s -X POST "http://localhost:5678/api/v1/workflows/Rblg81qifVshsRae/activate" ^
     -H "X-N8N-API-KEY: %N8N_API_KEY%" ^
     -H "Content-Type: application/json" -d "{}" >nul 2>&1
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
    echo [%time%] AVISO: n8n no responde. Reinicia el script.
    pause
    exit /b 1
)

:: Vigilar el tunel. Al ser dominio fijo, basta con relanzarlo: la URL no cambia,
:: asi que el webhook de Zoom y el de Telegram siguen siendo validos.
tasklist /FI "IMAGENAME eq ngrok.exe" /NH 2>nul | findstr /i "ngrok" >nul 2>&1
if %errorlevel% NEQ 0 (
    echo [%time%] ngrok caido. Relanzando ^(misma URL: %WEBHOOK_URL%^)...
    start /B "" "%NGROK_EXE%" start %NGROK_TUNNEL%
    timeout /t 5 /nobreak >nul
    echo [%time%] Tunel restablecido.
)

curl -s "http://localhost:5678/api/v1/workflows/Rblg81qifVshsRae" -H "X-N8N-API-KEY: %N8N_API_KEY%" -o "%TEMP%\wf_check.json" 2>nul
findstr /i "active" "%TEMP%\wf_check.json" | findstr "false" >nul 2>&1
if %errorlevel% EQU 0 (
    echo [%time%] Workflow inactivo. Reactivando...
    curl -s -X POST "http://localhost:5678/api/v1/workflows/Rblg81qifVshsRae/activate" -H "X-N8N-API-KEY: %N8N_API_KEY%" -H "Content-Type: application/json" -d "{}" >nul 2>&1
    echo [%time%] Workflow reactivado.
)

goto :loop
