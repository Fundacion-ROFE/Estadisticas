# Watchdog: detecta ejecuciones de n8n "colgadas" (conexion muerta tras suspend/resume,
# vease docs/procesos/mapa-codigo.md / memoria project_n8n_suspend_resume) sin depender
# del evento Power-Troubleshooter Id=1 -- ese evento no se disparo la noche del 24-jul
# pese a que el mismo cuelgue ocurrio, dejando el auto-heal existente ciego.
# Revisa ejecuciones "running" hace mas de 20 min -> si hay, reinicia n8n via iniciar_n8n.bat.

$envFile = "C:\Users\EstudiantesJC\downloads\admin-usable\scripts\q10-consolidacion\.env"
$apiKey = $null
foreach ($line in Get-Content $envFile) {
    if ($line -match '^N8N_API_KEY=(.+)$') { $apiKey = $Matches[1].Trim() }
}
if (-not $apiKey) { exit 0 }

$logPath = "C:\Users\EstudiantesJC\downloads\admin-usable\tools\watchdog_n8n.log"

try {
    $resp = Invoke-RestMethod -Uri "http://localhost:5678/api/v1/executions?status=running&limit=20" `
        -Headers @{ "X-N8N-API-KEY" = $apiKey } -TimeoutSec 15
} catch {
    "$(Get-Date -Format o) - n8n no responde a la API (posible caida total)" | Out-File -Append $logPath
    exit 0
}

$ahora = Get-Date
$colgadas = @($resp.data | Where-Object {
    $inicio = [datetime]$_.startedAt
    ($ahora - $inicio).TotalMinutes -gt 20
})

if ($colgadas.Count -gt 0) {
    "$(Get-Date -Format o) - $($colgadas.Count) ejecucion(es) colgada(s) (>20 min): reiniciando n8n" | Out-File -Append $logPath
    Start-Process -FilePath "C:\Users\EstudiantesJC\downloads\admin-usable\iniciar_n8n.bat"
}
