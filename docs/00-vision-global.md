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
+ docs/retirados/   → botón "Retirados ↗" en el dashboard

Rama Retirados (mismo pipeline n8n, Fase 4):
q10_to_sheets.py --grupo retirados ──► reporte "Estudiantes cancelados"
    ▼ pestaña Retirados (cruda, Sheet h2test)
retirados_headless.py ──► pestaña Retirados-complete (bloques por Tipo)
    ▼ export_retirados.py
docs/retirados/data.json (solo agregados) ──► panel público de retirados
```

```
(solo local, nunca GitHub)
Google Sheets h2test          ──┐
Google Sheets Avance          ──┤
Pestaña Retirados             ──┼──► panel_riesgo_gui.py
Supabase asistencia_promedio ──┘     5 tabs interactivos (PII):
                                     🎓 JC | 💡 MR | ⚙ Admin | 🔀 Diferencias | 🚪 Retirados
                                     ↑ KPIs clickeables → tabla dinámica
                                     Admin guarda → tools/course_config.json
                                     ✓ Columna "Asistencia %" en 5 vistas

Google Sheets h2test (avance < 100, solo JC)  ──┐
BD Seguimiento Monitorias (Grupo = ciudad)    ──┼──► exportar_sin_completar.py
                                                └──► Sheet privado "SinCompletar"
                                                     (bloques horizontales por ciudad,
                                                      cursos apilados — para encargados)
```

---

## Stack

| Componente | Detalle |
|---|---|
| Orquestador | n8n 2.8.4 self-hosted, local en PC Samuel (EstudiantesJC) |
| Arranque | Task Scheduler → `iniciar_n8n.bat` al iniciar sesión (automático) |
| Tunnel | **ngrok — dominio estático fijo** `ergonomic-absinthe-refract.ngrok-free.dev` (2026-07-06, reemplaza el `cloudflared` efímero que rotaba). Ver [[reference-ngrok-tunel-fijo]]. Expone n8n a los webhooks de Telegram y Zoom |
| Identidad | Google Workspace — Service Account por proceso |
| Dashboard | GitHub Pages → `fundacion-rofe.github.io/Estadisticas/dashboard/` |
| Red | Proxy corporativo con SSL MITM — ver [[convenciones#SSL corporativo]] |

---

## Procesos completados

| Proceso | Nota | Completado | Estado |
|---|---|---|---|
| Consolidación Q10 | [[q10-consolidacion]] | 2026-06-25 | Schedule 4h + Telegram activos · 1,145 estudiantes 2026 · 4,553 total DB |
| Dashboard web | [[dashboard-web]] | 2026-06-26 | GitHub Pages live · panel MR · separación JC/MR en Python · **panel Aprobación por curso** (cohorte completa habilitados + inhabilitados, aprobado = avance ≥ 100, 2026-07-07) · **tabs 1–3 rediseñados sobre la cohorte de aprobación** + tendencia con snapshots diarios (2026-07-07, pedido del supervisor) · marca de agua cursos finalizados en export_stats (2026-07-06, hoy solo alimenta Admin) · **Refactorización 2026: Fases 1–3 completadas** — Fase 1 (Tab 1 solo-JC + exclusión de pruebas) y Fase 2 (Comparativo solo-JC + panel MR sobre cohorte) el 2026-07-08; **Fase 3** (panel Retirados filtrado a 2026 con etapa de retiro vía ledger + funnel de retención en Tendencia) el 2026-07-09 |
| Panel de riesgo GUI | [[dashboard-web]] | 2026-06-26 | 5 tabs interactivos · KPIs clickeables · vistas dinámicas JC y MR · Tab Admin con course_config.json · Tab Retirados |
| Retirados Q10 | [[q10-consolidacion]] | 2026-07-02 | Fase 4 del pipeline · reporte Estudiantes cancelados → Retirados/Retirados-complete → panel público · histórico 353 · **panel filtrado a cohorte 2026: 82 retirados únicos + etapa de retiro** (2026-07-09) |
| Pseudonimizador | [[pseudonimizador]] | 2026-06-30 | GitHub Pages live · 3 tabs · Web Worker para 22 MB / 44 pestañas · Pendiente demo con equipo |
| Actualización BD MR | [[mr-actualizacion-datos]] | 2026-07-08 | Form MR2024 → pestaña General de BD-Mujeres ROFÉ · cruce por cédula · col `Fecha Actualización` · n8n diario 9:30 am COT (`LgkDbNPERYgKMrYj`) · backfill: 286 filas actualizadas + 24 nuevas (naranja, revisar) |
| Asistencia Zoom (cálculo + panel) | [[zoom-asistencia]] | 2026-07-13 | **COMPLETADO:** webhook Zoom → ZOOM-ASISTANCE (704 registros) → `calcular_asistencia_promedio.py` → Supabase `asistencia_promedio` (490 estudiantes) → Panel de riesgo muestra "Asistencia %" en 5 vistas. RLS policies + documentación del flujo listos. Automatización n8n diaria 00:00 pendiente de configurar en dashboard n8n. |

---

## Procesos en progreso

| Proceso | Nota | Bloqueado por |
|---|---|---|
| Website Mujeres ROFÉ | [[mr-website]] | **Documentación inicial lista (2026-07-07).** Código en repo independiente (`Downloads\Mujeres-Rofe-Website`, back Express+Mongo / front Angular 15, deploy droplet DigitalOcean vía Actions). Bloqueado por: definir alcance de los cambios solicitados + clonar repos remotos (copia local sin `.git`) |
| Panel de Datos Supabase | [[panel-datos-etl]] | **MVP EN PRODUCCIÓN (2026-07-10):** https://classy-pasca-eecdd6.netlify.app — Next.js estático (repo dedicado `panel-datos-rofe`) sobre vistas de agregados Supabase; ETL diario n8n 9:45; sociodemográficos de BD monitorias (775); **cuadre 9/9 exacto vs dashboard canónico** (activos y aprobados por curso). Pendiente menor: verificar 1ª corrida automática n8n, retirados en Supabase, campo programa JC/MR, renombrar sitio Netlify |
| n8n: Automatización asistencia Zoom | [[zoom-asistencia]] | Script `calcular_asistencia_promedio.py` funcional. Pendiente: agregar Cron job en n8n para ejecutar diariamente a las 00:00 (después de que Zoom envíe eventos). Documentado en [[asistencia-zoom-flujo]]. |

---

## Procesos identificados (pendientes)

| Proceso | Por qué importa |
|---|---|
| Creación reuniones Meet | 2 asistentes lo hacen manualmente hoy |
| Grabaciones Zoom → YouTube | [[zoom-youtube]] — subida manual hoy; documentado y viable, reusa la app Zoom S2S de [[zoom-asistencia]] (2026-07-03) |

---

## Archivos clave

| Archivo | Propósito |
|---|---|
| [CLAUDE.md](../CLAUDE.md) | Instrucciones para Claude Code |
| [[convenciones]] | Estándares técnicos (SSL, Q10, n8n, Sheets) |
| [[prioridades-automatizacion-ia]] | Priorización de las 7 áreas pedidas por dirección (2026-07-10) + argumento BD central |
| [[mapa-codigo]] | Índice esquemático de todos los scripts |
| [[bd-seguimiento-monitorias]] | Arquitectura interna de la BD manual de 35 pestañas (hub `Seguimiento` + hojas-ciudad) |
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
- **Marca de agua (high-water mark):** cuando una fuente solo trae registros "activos" (Q10 archiva a los retirados), rastrear el máximo histórico por entidad en un JSON de estado monótono para no perder cifras de cohortes ya terminadas. Ver [[dashboard-web#Cursos finalizados — marca de agua (inscritos → finalizados)]].

---

## Próxima gran decisión

Una vez completados 3-4 procesos, evaluar si conviene un workflow maestro n8n que orqueste sub-flujos o mantenerlos independientes. No tomar antes de tener visión completa.
