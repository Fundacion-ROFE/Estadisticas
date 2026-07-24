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
                                                ├──► pestaña "SinCompletar" (bloques por
                                                │     ciudad, cursos apilados — encargados)
                                                ├──► pestaña "Historico" (snapshot semanal,
                                                │     marca de agua por semana ISO)
                                                ├──► pestaña "Semaforo" (semana pasada vs.
                                                │     actual POR ESTUDIANTE: verde/amarillo/
                                                │     rojo + tendencia Δ%)
                                                └──► pestaña "Balance" (resumen ciudad ×
                                                      materia, sin individuo — semáforo por
                                                      celda, para lectura rápida del monitor)
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
| Panel de Datos Supabase | [[panel-datos-etl]] | **MVP EN PRODUCCIÓN:** https://venerable-truffle-331f3c.netlify.app (URL corregida 2026-07-21) — Next.js estático sobre vistas de agregados Supabase; ETL diario n8n 9:45 (ahora 20 nodos, incluye `sync_emoflow_api`, `export_supabase_json`, `sync_supabase_to_sheets`) + `sociodemograficos-semanal` (lunes 6:00). **Auditoría de centralización 2026-07-21 — las 4 tareas pendientes ejecutadas:** retirados históricos 2023-2025 confirmado sin fuente recuperable (búsqueda cerrada), `sync_supabase_to_sheets`/`export_supabase_json` encadenados (con advertencia de consumidor no confirmado para el segundo), sociodemográficos JC diseñado en [[captura-sociodemografica-jc]] (no implementado, para el próximo año), migración Netlify→DigitalOcean sigue como próxima gran decisión de infra sin plan detallado. De paso: un bug de encoding propio (PowerShell mutilando tildes en nombres de nodos) encontrado y corregido. **2026-07-23: diccionario de datos canónico en [[supabase-estructura]]** (24 tablas, estados 🟢🟡🔴, tasas de match medidas, plan "única fuente de verdad") + análisis Emoflow↔resultados (asociación positiva robusta OR 2.36; retiro individual = hueco #1, no existe en Supabase). **Blindaje QA mismo día:** suite `test_integridad_supabase.py` (36/36 PASS tras aplicar la migración de seguridad — Samuel aprobó `006_seguridad_hardening`, 6/8 bloques aplicados, 2 descartados por romper funcionalidad real detectada antes de ejecutar), matriz de cobertura JC×MR, **vista nueva `v_persona_360`** (trazabilidad total por persona en una sola consulta), 16 casos discordantes de `postulantes_mr` documentados y en espera, y **`en_seguimiento_jc`** (alerta operativa de retiro pendiente de confirmar — el equipo borra del Sheet antes que de Q10; solo JC cohorte actual, 18 alertas reales de 777, **excluidas de "estudiante actual" en las 11 vistas + panel_riesgo + reporte_puntaje, sin tocar los números canónicos de Q10**, y mostradas aparte en **`v_retiro_probable_jc`** — 7 aprobaron antes de irse, 11 no — categoría separada de `cohorte_ingresos.retirados` oficial). **Corrección posterior mismo día:** 17/18 ya estaban confirmados en el pipeline oficial (`export_aprobacion.py`) que solo estaba desactualizado en Supabase (9:45 vs 12:04) — resincronizado (`cohorte_ingresos` JC ahora 760 activos/74 retirados, coincide con Seguimiento). Las 3 piezas de `en_seguimiento_jc` se mantienen como red de seguridad. **Barrido completo de las 24 fuentes del frontend** encontró 2 más sin ajustar (`v_emprendimiento_por_ciudad`, `cohorte_stats` vía `recompute_aggregates()`) — ya corregidas, 38/38 PASS. `Seguimiento` formalizada en `convenciones.md` como fuente esencial de la DB (759 vs 760 de Q10 fresco = evidencia de confiabilidad). **`007_retiros` aplicada (2026-07-23):** esquema de tabla individual de retiros listo (RLS+REVOKE verificado, 39/39 PASS) — tabla vacía, falta escribir `sync_retiros.py` para poblarla |
| Panel de Riesgo — mejora | [[panel-riesgo-mejora]] | **Fase 1 completada (2026-07-21):** `panel_riesgo_gui.py` ya lee la cohorte canónica de Supabase (verificado 777 JC / 283 MR / 9 cursos exacto). Fases 2-3 pendientes (tab "Decisiones" con botones de consulta, ficha ampliada) — se mantiene como GUI Tkinter (no panel web) por privacidad de PII |
| n8n: Automatización asistencia Zoom | [[zoom-asistencia]] | **Ya automatizado (workflow `asistencia-zoom-diario`, activo, 00:00 COT) — esta fila estaba desactualizada, corregida 2026-07-21.** `sync_asistencia_supabase.py` + `calcular_asistencia_promedio.py` corren solos a diario. Documentado en [[zoom-asistencia]]. |
| Postulantes MR → Supabase | [[postulantes-mr-supabase]] | **Fases 0-3 completadas + fusión de duplicados (2026-07-22):** tabla `postulantes_mr` cargada y depurada (5.351 → 5.315 filas tras fusionar 36/52 duplicados; 16 casos discordantes pendientes de revisión humana, ver `Downloads/postulantes_mr_disonancias_general.xlsx`). RLS sin anon verificado (401). Detector de typos por bloques confirmó el caso real Gina Gleisy. **Investigación MongoDB MR cerrada** ([[panel-datos-etl#Exploración de MongoDB]]): 99.9% redundante con `postulantes_mr`, solo 4 registros nuevos, no cargados. **Histórico Q10 MR 2023/2024 cerrado:** Q10 nunca trackeó cursos MR antes de 2025 — no falta ningún import. **Pendiente:** Fase 4 (n8n) y Fase 5 (búsqueda unificada) |
| Postulantes JC en Mongo → Supabase | [[panel-datos-etl#Auditoría Mongo JC]] | **Cargado (2026-07-22):** auditoría del Mongo `jovenes-creativos.User`/`Applicant` encontró 466 personas sin match en `participants` ni en el Sheet BD Seguimiento (463 tras excluir 3 admin) — a diferencia de MR (4 exclusivos, no cargado), aquí Samuel confirmó que el hallazgo era real e importante. Tabla `postulantes_jc` creada (RLS sin anon, columna `fuente` = mongo_user/mongo_applicant a pedido explícito) y cargada: 2.556 filas, 2.092 con match a `participants`, 464 exclusivas. Scripts: `extraer_mongo_jc_historico.py` + `cargar_mongo_jc_historico.py`. |
| Migración n8n → DigitalOcean | [[migracion-n8n-digitalocean]] | **Solo planificación (2026-07-22):** auditoría en vivo completa (12 workflows activos, credenciales sin fricción de OAuth, pero 35 nodos `executeCommand` con rutas Windows hardcoded + `git push` escondido en 7 scripts Python vía Windows Credential Manager). Decisión abierta: ¿reutilizar el droplet DigitalOcean ya existente de [[mr-website]] o uno nuevo? Sin fecha de ejecución — se espera que el sistema siga cambiando antes de arrancar. |

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
| [[plan-produccion-datos-2026-07-24]] | Plan ejecutable (Sonnet, agentes paralelos) para llevar DB + paneles + flujos a producción — incluye P0 de seguridad |
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
