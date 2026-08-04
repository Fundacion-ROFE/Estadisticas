# Archivo — documentos históricos

Documentos de **fases de planeación ya ejecutadas** o **incidentes resueltos**. Se conservan por
trazabilidad de decisiones, pero **no reflejan el estado actual** del sistema. Para el estado vivo
ver `docs/00-vision-global.md` y `docs/procesos/`.

Archivados el 2026-07-21 (limpieza de mantenimiento):

| Archivo | Qué era | Por qué se archivó |
|---|---|---|
| `PLAN-DATOS-ANALISIS-PROFUNDO.md` | Plan inicial del panel de datos (9-jul) | Panel ya en producción (Netlify + Supabase) |
| `ARQUITECTURA-VISUAL.md` | Diagrama ejecutivo del plan de datos | Superado por la implementación real |
| `CLAUDE-CODE-PROMPTS-POR-FASE.md` | Prompts de arranque por fase | Ya usados |
| `MATRIZ-DECISIONES-PENDIENTES.md` | Decisiones previas a Fase 0 | Decisiones ya tomadas |
| `PROXIMOS-PASOS-SESION-2.md` | Plan de la sesión 2 | Sesión ya pasó |
| `prompt-arbol-progreso.md` | Prompt del proyecto "Árbol ROFÉ" (carpeta aparte) | No pertenece a este repo activo |
| `plan-agentes-automatizacion.md` | Plan de agentes/herramientas | Ejecutado |
| `plan-ejecucion-sonnet.md` | Versión del plan para ejecutar con Sonnet | Ejecutado |
| `ANALISIS-SHEETS-VS-SUPABASE.md` | Benchmark de la decisión de backend | Decisión tomada: ganó Supabase |
| `SECURITY-INCIDENT.md` | Incidente de la clave Supabase (14-jul) | Resuelto (historia purgada) |

Archivados el 2026-07-29 (unificación de planes de manejo de DB, varios redactados con Fable,
otros con Sonnet — reemplazados por `docs/procesos/plan-maestro-2026-07-29.md`):

| Archivo | Qué era | Por qué se archivó |
|---|---|---|
| `plan-maestro-2026-07-28.md` | Fusión previa de producción+testing+auditoría (28-jul) | Superado por `plan-maestro-2026-07-29.md`, que además absorbe lo pendiente que quedó fuera |
| `plan-produccion-datos-2026-07-24.md` | Plan de producción DB/paneles/flujos para Sonnet (24-jul) | P0/Olas 0-2 ejecutadas y verificadas; lo pendiente (Olas 3-4, reglas de mantenibilidad) pasó a `plan-maestro-2026-07-29.md` §4/P3 y §4/P6 |
| `plan-testing-produccion-2026-07-29.md` | Plan de testing pre-corte miércoles (27-jul) | Bloques 1/2/4 cerrados y verificados; Bloque 3 (preguntas doradas) y la decisión de credencial Lina/Astrid pasaron a `plan-maestro-2026-07-29.md` §5/§2 |
| `plan-accion-auditoria-2026-07-28.md` | Plan de acción de la auditoría estadística de 2 agentes (28-jul) | Hallazgos ya resueltos o absorbidos en `plan-maestro-2026-07-29.md` §1/§4 |
| `prompt-analisis-emoflow.md` | Prompt de arranque para Fable — auditoría y análisis Emoflow (23-jul) | Ejecutado; entregó `docs/procesos/supabase-estructura.md` |
| `prompt-testing-supabase.md` | Prompt de arranque para Fable — blindaje de seguridad/integridad (23-jul) | Ejecutado; hallazgos resueltos o convertidos en tests permanentes |
| `decision-separacion-db-jc-mr.md` | Decisión de no separar la DB física por programa JC/MR (29-jul, vía `/consejo-medio`) | Fusionada íntegra en `plan-maestro-2026-07-29.md` §7; su pendiente (auditar RLS/policies) pasó a §4/P1 |

Archivados el 2026-08-04 (auditoría de documentación — mapa de grafo, enlaces rotos, notas huérfanas):

| Archivo | Qué era | Por qué se archivó |
|---|---|---|
| `panel-riesgo-mejora.md` | Plan de mejora del panel de riesgo (migración a Supabase + panel de decisiones) | La propia nota ya se autodeclaraba "ARCHIVADO/FUSIONADO (2026-07-30)" en su encabezado — vivía en `docs/procesos/` pese a decir eso; solo se movió la ubicación para que coincida con el estado. Contenido fusionado en `panel-control-jc-mr.md` |
| `n8n-workflows-setup.md` | Guía paso a paso para crear workflows n8n en la UI | Contenido factualmente desactualizado (decía cron `00:00`, el real es `17:45 COT` desde el 2026-07-30) y 100% superado por `docs/procesos/zoom-asistencia.md` |
| `DIAGNOSTICO-2026-07-24.md` | Informe de diagnóstico de automatizaciones para Coordinación (24-jul) | Snapshot de un momento puntual, superado por los `.docx`/`.pdf` de diagnóstico del 28-jul (raíz del repo) y por el estado real actual (las "mejoras que llegarán pronto" que listaba ya están construidas: `panel-control-jc-mr`, backend de `whatsapp-identificacion-manychat`) |
| `prompt-cierre-choques-cursos.md` | Prompt de arranque para cerrar 3 pendientes de vigilancia de cursos (29-jul) | Ejecutado — `alerta-choques-cursos.json`/`alerta-choques-cohorte.json` ya existen en `n8n-workflows/`, confirmando que el Punto 2 se completó; el resto del contexto quedó absorbido en `plan-maestro-2026-07-29.md` |
| `prompt-ejecucion-visualizacion.md` | Prompt de handoff para ejecutar `plan-visualizacion-2026-07-30.md` | Ejecutado — Fase 1 completa (2026-07-30) según `00-vision-global.md`; Fase 2 (GUI) pausada a favor de `panel-control-jc-mr.md`, Fase 3 (Netlify) absorbida en `plan-rediseno-panel-datos-2026-07-30.md` |
| `prompt-fix-alertas-telegram.md` | Prompt para arreglar 4 problemas de las alertas de Telegram (30-jul) | Ejecutado — confirmado por el propio `prompt-ejecucion-visualizacion.md`: "la instancia que arreglaba las alertas de Telegram ya terminó (5 commits, verificado en vivo: 0 procesos vencidos, 0 alertas de severidad alta)" |
| `plan-encadenar-validacion-zoom-2026-07-30.md` | Plan para encadenar `validar_asistencia.py` antes del sync de asistencia Zoom | Ejecutado — `docs/procesos/zoom-asistencia.md` (vía `00-vision-global.md`) documenta esto como "COMPLETADO, FUNCIONAL en producción" desde el 2026-07-30 |
| `prompt-auditoria-documentacion-2026-08-04.md` | Prompt de arranque de esta misma auditoría de documentación | Ejecutado — cumplió su propósito al arrancar la sesión que generó todas las filas de esta tabla |
