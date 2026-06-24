# Visión Global de Automatizaciones

> Mapa de todo lo que se ha automatizado, lo que está en progreso, y lo pendiente.
> Se actualiza cada vez que se completa o inicia un proceso nuevo.
> Punto de entrada para entender el estado del proyecto completo de un vistazo.

## Stack general
- **Orquestador:** n8n 2.8.4 (self-hosted, corriendo localmente en el PC de Samuel / EstudiantesJC)
- **Tunnel externo:** Cloudflare Tunnel (`cloudflared`) — expone n8n al webhook de Telegram sin ngrok
- **Identidad/Datos:** Google Workspace (Sheets, Drive) — Service Account por proceso
- **Asistente de desarrollo:** Claude Code + Claude API para tareas puntuales dentro de flujos
- **Red:** proxy/firewall corporativo con interceptación SSL — ver [[convenciones#SSL corporativo]]

## Procesos completados

| Proceso | Nota | Completado | Resultado |
|---|---|---|---|
| Consolidación Q10 | [[q10-consolidacion]] | 2026-06-24 | 8,818 filas · H1Test + h2test operativas · bot Telegram activo |

## Procesos en progreso

| Proceso | Nota | Prioridad | Notas rápidas |
|---|---|---|---|
| Asistencia Zoom | [[zoom-asistencia]] | Alta | Bloqueado — pendiente confirmar captura de Email/ID en sesiones |

## Procesos identificados (pendientes de iniciar)

| Proceso | Descripción breve | Por qué importa |
|---|---|---|
| Dashboard web Q10 | Script Python genera JSON desde h2test → commit a GitHub → GitHub Pages muestra estadísticas | En construcción — ver [[q10-consolidacion#Conexión h2test → Dashboard web]] |
| Creación de reuniones Meet | Hoy lo hacen manualmente 2 asistentes | Ahorro de tiempo humano directo |

## Patrones recurrentes detectados

- **SSL corporativo:** todos los procesos que hagan HTTP desde Python o n8n en esta red necesitan el mismo fix. Ver [[convenciones#SSL corporativo]].
- **Trigger Telegram + n8n local:** patrón establecido en Q10, reutilizable para otros procesos bajo demanda.

## Próxima gran decisión
Una vez completados 3-4 procesos individuales, evaluar unificación: ¿conviene un
workflow maestro en n8n que orqueste sub-flujos, o mantenerlos independientes?
Decisión pendiente — no tomar todavía, falta visión suficiente del entorno completo.
