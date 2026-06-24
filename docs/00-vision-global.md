# Visión Global — Fundación ROFÉ / Jóvenes creaTIvos

> Home de Obsidian y punto de entrada para Claude Code.
> **Leer esto primero** antes de cualquier tarea nueva.
> Conexiones: [[convenciones]] · [[mapa-codigo]] · [CLAUDE.md](../CLAUDE.md)

---

## Flujo general del sistema

```
Telegram bot
    │  /actualizar h2test
    ▼
n8n (local, PC Samuel)
    │  ejecuta
    ▼
q10_to_sheets.py ──► Q10 (site6.q10.com) ──► Excel/xlsx
    │                 Login 7 pasos AJAX
    │  escribe (activos solamente)
    ▼
Google Sheets H1Test (datos crudos planos)
    │
    │ organizador_headless.py
    │  - ordena por curso
    │  - bloques horizontales
    │  - Observaciones + Estadisticas
    ▼
Google Sheets h2test            Google Sheets (Avance — manual)
    │                                   │
    │ export_stats.py                   │ export_avance.py
    ▼                                   ▼
docs/dashboard/data.json        docs/avance/data.json
    │                                   │
    └──────────────┬────────────────────┘
                   │ git push
                   ▼
           GitHub Pages
    fundacion-rofe.github.io/Estadisticas/dashboard/
                   │
    ┌──────────────┼─────────────────┐
    ▼              ▼                 ▼
Tab 1 Q10    Tab 2 Avance    Tab 3 Comparativo
```

```
(solo local, nunca GitHub)
Google Sheets h2test   ──┐
                          ├──► panel_riesgo.py ──► consola + tools/reportes/*.csv
Google Sheets (Avance) ──┘     cruce por email
```

---

## Stack

| Componente | Detalle |
|---|---|
| Orquestador | n8n 2.8.4 self-hosted, local en PC Samuel (EstudiantesJC) |
| Tunnel | Cloudflare Tunnel (`cloudflared`) — expone n8n al webhook de Telegram |
| Identidad | Google Workspace — Service Account por proceso |
| Dashboard | GitHub Pages → `fundacion-rofe.github.io/Estadisticas/dashboard/` |
| Red | Proxy corporativo con SSL MITM — ver [[convenciones#SSL corporativo]] |

---

## Procesos completados

| Proceso | Nota | Completado | Estado |
|---|---|---|---|
| Consolidación Q10 | [[q10-consolidacion]] | 2026-06-24 | Bot Telegram activo · 8,845 filas · h2test operativa |
| Dashboard web | [[dashboard-web]] | 2026-06-24 | GitHub Pages live · 3 tabs · export_stats + export_avance funcionando |

---

## Procesos en progreso

| Proceso | Nota | Bloqueado por |
|---|---|---|
| Asistencia Zoom | [[zoom-asistencia]] | Confirmar cómo se captura Email/ID en sesiones reales |

---

## Procesos identificados (pendientes)

| Proceso | Por qué importa |
|---|---|
| Creación reuniones Meet | 2 asistentes lo hacen manualmente hoy |
| Panel de riesgo real | `panel_riesgo.py` listo — pendiente validar con datos reales y corregir apuntador a pestaña Avance |

---

## Archivos clave

| Archivo | Propósito |
|---|---|
| [CLAUDE.md](../CLAUDE.md) | Instrucciones para Claude Code |
| [[convenciones]] | Estándares técnicos (SSL, Q10, n8n, Sheets) |
| [[mapa-codigo]] | Índice esquemático de todos los scripts |
| [claude_sessions.md](../claude_sessions.md) | Bitácora cronológica de sesiones |
| [[plantillas/plantilla-proceso]] | Plantilla para notas nuevas de proceso |

---

## Runbooks para operadores

| Runbook | Para quién |
|---|---|
| [q10-actualizar](../runbooks/q10-actualizar.md) | Equipo no técnico — actualizar H1Test vía bot Telegram |

---

## Patrones recurrentes detectados

- **SSL corporativo:** aplica a Python, n8n y git. Ver [[convenciones#SSL corporativo]].
- **Doble encabezado en Sheets:** h2test y pestaña Avance usan el mismo patrón (fila 1 = nombres fusionados, fila 2 = sub-headers). Ver [[convenciones#Doble encabezado en Google Sheets]].
- **Trigger Telegram + n8n local:** patrón establecido en Q10, reutilizable para otros procesos.
- **JSON sin PII:** toda salida pública es JSON agregado. Datos individuales solo en `tools/`.

---

## Próxima gran decisión

Una vez completados 3-4 procesos, evaluar si conviene un workflow maestro n8n que orqueste sub-flujos o mantenerlos independientes. No tomar antes de tener visión completa.
