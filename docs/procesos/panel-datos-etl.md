# Panel de Datos Supabase (ETL + Dashboard)

**Estado:** En progreso — Fases 0-2 completadas: sync diario activo, sociodemográficos cargados, vistas públicas listas (2026-07-09)
**Última actualización:** 2026-07-09
**Procesos relacionados:** [[q10-consolidacion]] · [[dashboard-web]] · [[mr-actualizacion-datos]] · [[bd-seguimiento-monitorias]]

## Qué hace
Reemplaza Power BI por un panel de visualización alimentado por Supabase (PostgreSQL) como
fuente única de verdad, con ETL diario vía n8n y frontend Next.js en Netlify. Convive en
paralelo con el dashboard GitHub Pages existente hasta validar cuadre de cifras.

Plan maestro en la raíz del repo: `PLAN-DATOS-ANALISIS-PROFUNDO.md` ·
`MATRIZ-DECISIONES-PENDIENTES.md` (completada) · `CLAUDE-CODE-PROMPTS-POR-FASE.md` ·
`ARQUITECTURA-VISUAL.md` · `PROXIMOS-PASOS-SESION-2.md` — todos revisados/corregidos 2026-07-09.

## Disparador (Trigger)
- **Workflow n8n `q10-sync-supabase` (ID `uSizw3dNzpb6n53H`), Schedule diario 9:45 COT, activo.**
  Decisión de diseño: se descartó el 04:00 UTC (23:00 COT) del plan original — el PC estaría
  apagado y los schedules de n8n no se recuperan (convención [[convenciones#Timezone en Schedule Triggers de n8n]]);
  9:45 es después del arranque de n8n (~8:45-8:50 con el login) y del workflow MR (9:30).
- Cadena: `Ejecutar normalize_q10_data` → IF estado=exito → `Ejecutar cargar_supabase` → IF →
  OK / stopAndError (camino de error explícito; "con_advertencias" también alerta — FKs perdidas
  nunca pasan en silencio). Export en `n8n-workflows/q10-sync-supabase.json`.

## Flujo resumido
1. Google Sheets (h2test + Retirados, proxy de Q10) → `normalize_q10_data.py` lee bloques
   de curso (patrón `detectar_grupos`), excluye desertores + perfiles de prueba, normaliza
   y valida → `tools/supabase_payload.json` + reporte `tools/normalize_report_*.json`
2. `cargar_supabase.py`: snapshot previo → `participants_snapshots`, luego upsert
   participants (`q10_id`) → courses (`nombre,cohorte`) → enrollments (FKs resueltas,
   `participant_id,course_id`). Idempotente (verificado con doble corrida).
3. (Fase 1b, pendiente) n8n orquesta 1→2 diario + recompute de agregados
4. Supabase REST (anon key, solo agregados vía RLS) → dashboard Next.js en Netlify

**Primera carga real (2026-07-09):** 1.059 participants (≈ 775 activos JC + 283 MR — cuadra
con la identidad canónica), 9 courses, 5.818 enrollments (4.983 completados > 80 · 528 en
progreso · 307 en 0%), 0 errores, 2 advertencias (avances 101 clampeados), 34 desertores +
9 perfiles de prueba excluidos.

## Fuentes de datos / APIs usadas
- Google Sheets (mismo Service Account de [[q10-consolidacion]])
- Supabase REST API — proyecto `panel-datos-rofe` (`kbxptoowtnteflhrfwid`, us-east-1)
  - URL: `https://kbxptoowtnteflhrfwid.supabase.co`
  - Keys en `.env.local` (gitignoreado); service_role pendiente de copiar del Dashboard
- **Datos sociodemográficos — mapeados y cargados (2026-07-09):** fuente = [[bd-seguimiento-monitorias]]
  (`RUTA_BD` en Downloads; la fuente viva es el Google Sheet — actualizar la ruta al cambiar versión).
  - Pestaña `Seguimiento` (headers fila 1): ID(c7), Grupo(c2), Fecha Nacimiento(c11), Edad(c12),
    Ciudad(c13), Género(c16) — 768 cédulas.
  - Pestaña `Diagnostico`: Número de documento(c3) + situación emprendimiento(c32, 4 categorías
    → enum `emprendimiento_situacion`) — 858 respuestas.
  - Resultado: **775 participantes actualizados** (= activos JC canónicos), 162 de la BD sin match
    (retirados ya no en h2test), las ~283 MR no están en esta BD.
  - ⚠️ La introspección confirmó que **vivienda/estrato/estado_civil/nivel_estudio NO existen en
    ninguna fuente** — quedan nullable y documentados con COMMENT en la BD. `Link Emprendimiento`
    (c98) es el link de Zoom de la clase, NO un emprendimiento del estudiante.

## Destino de los datos
Supabase PostgreSQL — schema en `schema-supabase-completo.sql` (raíz), aplicado como 2 migraciones:
`schema_base_panel_datos` (5 tipos ENUM, 6 tablas: participants, courses, enrollments,
participant_metrics, cohorte_stats + índices + RLS) y `snapshots_diarios_participants`.

## Decisiones de diseño clave (matriz completada 2026-07-09)
1. **Fuente de verdad:** sync n8n diario (A) — mismo patrón del proyecto.
2. **Histórico:** escalonado — Type 1 (upsert) + `participants_snapshots` diario ahora; SCD Type 2 en Fase 2 si se confirma necesidad.
3. **Permisos:** solo n8n/service_role escribe (A). El service_role bypasea RLS — jamás en frontend.
4. **Visibilidad:** dashboard público (A) pero consume SOLO agregados; filas individuales bloqueadas por RLS (verificado con smoke test REST: agregados 200, participants privados 0 filas, escritura anónima 401).
5. **BI Tool:** dashboard custom Next.js + Recharts (A); Metabase solo si piden SQL ad-hoc.
6. **Timeline:** MVP 2 semanas con schema completo (B).
- **Retirados:** usar la definición canónica de [[q10-consolidacion]] (pestaña Retirados, desertores excluidos, identidad 832 = 775 + 57) — NUNCA heurística paralela.

## Gotchas / Limitaciones conocidas
- El project ID original de los docs (`sqmrnirbakcrbhdlfxxz`) nunca existió en la cuenta — se creó `panel-datos-rofe` desde cero. Los otros 2 proyectos de la cuenta se eliminaron (2026-07-09); la cuenta es exclusiva de este proyecto.
- `uuid_generate_v4()` fallaba (extensión `uuid-ossp` nunca creada) → `gen_random_uuid()` nativo.
- **Supabase rechaza secret keys con User-Agent de navegador** ("Forbidden use of secret API key in browser") — PowerShell `Invoke-RestMethod` manda UA `Mozilla/...` y falla. Los scripts usan UA propio `panel-datos-etl/1.0`. n8n (axios) no tiene el problema.
- `courses` no traía UNIQUE(nombre, cohorte) → el upsert habría duplicado el catálogo en cada corrida. Migración `courses_unique_nombre_cohorte` (2026-07-09).
- Un nombre de curso MR contiene coma ("DE LA IDEA A LA ACCIÓN, TU GUÍA...") — no parsear listas de cursos por coma.
- El schema no tiene campo `programa` (JC/MR) en courses — la clasificación vive en `tools/course_config.json`. Decidir en Fase 2 si se agrega columna o vista.
- Free tier: **pausa el proyecto tras ~1 semana sin actividad** y **no incluye backups automáticos** (eso es plan Pro ~$25/mes). El sync diario lo mantiene vivo si el PC está encendido.
- Los 5 docs del plan (generados en claude.ai) traían 13 fallas corregidas el 2026-07-09 — ver notas ⚠️ al pie de cada uno.

## Pendiente / Próximos pasos
- [x] Secret key en `.env.local` (2026-07-09; validada con insert/read/delete real)
- [x] Fase 1a: `scripts/panel-datos/normalize_q10_data.py` — corrida real 0 errores
- [x] Loader `scripts/panel-datos/cargar_supabase.py` + carga inicial (idempotencia verificada)
- [x] Sociodemográficos mapeados y cargados (`sync_sociodemograficos.py`, 775 actualizados)
- [x] Fase 2 — vistas públicas de agregados: `v_demografia_grupo`, `v_emprendimiento_situacion`,
      `v_emprendimiento_vs_cursos`, `v_curso_completion`, `v_edad_distribucion` (GRANT a anon;
      lint security_definer aceptado y documentado — solo agregados sin PII)
- [ ] Re-correr `sync_sociodemograficos.py` cuando cambie la BD (manual; evaluar integrarlo a n8n
      leyendo el Google Sheet vivo en vez del export xlsx)
- [x] Fase 1b: workflow n8n `q10-sync-supabase` (`uSizw3dNzpb6n53H`, diario 9:45, activo) + JSON exportado
- [x] Recompute de agregados: función SQL `recompute_aggregates()` (migración `recompute_aggregates_fn`,
      solo service_role) invocada por el loader — 1.059 métricas + cohorte 2026 poblada
- [ ] Verificar la primera corrida automática (mañana 9:45) en ejecuciones de n8n
- [ ] Fase 2: materialized views (retirados con definición canónica) + decidir campo `programa`
- [ ] Fase 3: Next.js + Netlify
- [ ] Fase 4: test de cuadre contra `docs/dashboard|aprobacion|retirados/data.json` antes de reemplazar nada
