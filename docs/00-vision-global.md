# Visión Global — Fundación ROFÉ / Jóvenes creaTIvos

> Home de Obsidian y punto de entrada para Claude Code.
> **Leer esto primero** antes de cualquier tarea nueva.
> Conexiones: [[convenciones]] · [[mapa-codigo]] · [CLAUDE.md](../CLAUDE.md)

---

## Flujo general del sistema

```
Telegram bot              Schedule 4h (automático)
    │  /actualizar q10        │
    └──────────┬──────────────┘
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
    │ + tools/course_config.json        │
    │   (JC / MR / Stand-by)           │
    ▼                                   ▼
docs/dashboard/data.json        docs/avance/data.json
  { JC top-level,                (solo cursos manuales JC)
    mr: {...},
    stand: {...} }
    │                                   │
    └──────────────┬────────────────────┘
                   │ git push
                   ▼
           GitHub Pages
    fundacion-rofe.github.io/Estadisticas/dashboard/
                   │
    ┌──────────────┼──────────────┬──────────────┐
    ▼              ▼              ▼               ▼
Tab 1 Q10    Tab 2 Avance   Tab 3 Comp.   Tab 4 Admin
(solo JC)    (solo JC)     (JC vs JC)   (JC+MR+Stand)

+ docs/mujeres-rofe/ → lee data.mr del mismo JSON
```

```
(solo local, nunca GitHub)
Google Sheets h2test   ──┐
                          ├──► panel_riesgo_gui.py
Google Sheets Avance   ──┘     4 tabs interactivos (PII):
                               🎓 JC  |  ⚠ Atención  |  💡 MR  |  ⚙ Admin
                               ↑ KPIs clickeables → tabla dinámica
                               Admin guarda → tools/course_config.json
```

---

## Stack

| Componente | Detalle |
|---|---|
| Orquestador | n8n 2.8.4 self-hosted, local en PC Samuel (EstudiantesJC) |
| Arranque | Task Scheduler → `iniciar_n8n.bat` al iniciar sesión (automático) |
| Tunnel | Cloudflare Tunnel (`cloudflared`) — expone n8n al webhook de Telegram |
| Identidad | Google Workspace — Service Account por proceso |
| Dashboard | GitHub Pages → `fundacion-rofe.github.io/Estadisticas/dashboard/` |
| Red | Proxy corporativo con SSL MITM — ver [[convenciones#SSL corporativo]] |

---

## Procesos completados

| Proceso | Nota | Completado | Estado |
|---|---|---|---|
| Consolidación Q10 | [[q10-consolidacion]] | 2026-06-25 | Schedule 4h + Telegram activos · 1,145 estudiantes 2026 · 4,553 total DB |
| Dashboard web | [[dashboard-web]] | 2026-06-26 | GitHub Pages live · 4 tabs (JC/Avance/Comp/Admin) · panel MR · separación JC/MR en Python |
| Panel de riesgo GUI | [[dashboard-web]] | 2026-06-26 | 4 tabs interactivos · KPIs clickeables · vistas dinámicas JC y MR · Tab Admin con course_config.json |

---

## Procesos en progreso

| Proceso | Nota | Bloqueado por |
|---|---|---|
| Asistencia Zoom | [[zoom-asistencia]] | Confirmar cómo se captura Email/ID en sesiones reales |
| Pseudonimizador | [[pseudonimizador]] | App completa lista (HTML único, 3 tabs) · Pendiente push a GitHub Pages y prueba con equipo |

---

## Procesos identificados (pendientes)

| Proceso | Por qué importa |
|---|---|
| Creación reuniones Meet | 2 asistentes lo hacen manualmente hoy |

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
- **Trigger dual (Telegram + Schedule):** patrón establecido en Q10 — Schedule para actualizaciones automáticas silenciosas, Telegram para forzar actualización on-demand. Reutilizable en otros procesos.
- **Arranque automático vía Task Scheduler:** tarea "Iniciar n8n ROFE" registrada en Windows — corre `iniciar_n8n.bat` al iniciar sesión de EstudiantesJC. No requiere intervención manual.
- **JSON sin PII:** toda salida pública es JSON agregado. Datos individuales solo en `tools/`.

---

## Próxima gran decisión

Una vez completados 3-4 procesos, evaluar si conviene un workflow maestro n8n que orqueste sub-flujos o mantenerlos independientes. No tomar antes de tener visión completa.
