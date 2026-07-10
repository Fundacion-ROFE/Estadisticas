# Panel de Datos Supabase (ETL + Dashboard)

**Estado:** ✅ MVP completo (Fases 0-4) — en producción: https://classy-pasca-eecdd6.netlify.app (2026-07-10)
**Última actualización:** 2026-07-10

## Frontend (Fase 3) — EN PRODUCCIÓN
**URL:** https://classy-pasca-eecdd6.netlify.app (deploy automático on push; renombrable en
Netlify → Site settings → Change site name, ej. `panel-rofe`).
Repo dedicado: `C:\Users\EstudiantesJC\downloads\panel-datos-rofe` (GitHub conectado a Netlify).

## Sección por programa + Historial (2026-07-10, pedido de stakeholders)
- **Programa JC/MR:** columna `courses.programa` (enum `programa_type`), clasificación canónica
  en `normalize_q10_data.py` (course_config.json precedencia + keywords MR, misma lógica de
  export_stats). Vista `v_programa_stats` (JC 777 / MR 282 participantes únicos — canónicos).
- **Historial:** tabla `historial_cursos` (UNIQUE fecha+curso, lectura pública, serie de tiempo
  sin PII): backfill único desde `docs/dashboard/history.json` (75 filas desde 2026-06-26,
  `backfill_historial.py`) + snapshot diario que agrega `cargar_supabase.py` en cada corrida
  (con `completados`, que el backfill no trae → NULL en filas viejas).
- **Frontend:** selector Jóvenes creaTIvos / Mujeres ROFÉ (segmenta KPIs/cursos/historial) +
  tab Historial (evolución de matrículas y avance por curso). Demografía existe para ambos
  programas con fuente propia (JC: BD monitorias · MR: `v_mr_demografia`, desde 2026-07-10);
  Emprendimiento (encuesta diagnóstico) sigue solo JC.

## Cohortes históricas Q10 (2026-07-10, pedido de stakeholders)
- **Sondeo empírico** (`tools/sondear_periodos_q10.py` → `tools/sondeo_periodos_20260710.json`):
  el Consolidado de Q10 SÍ conserva los periodos históricos CON avance — 2.880 cédulas únicas
  en los periodos 1-24. IDs 25-40 vacíos. Los +3.000 del equipo = 2.880 + retirados históricos
  (353, inhabilitados que NO salen del Consolidado — limitación documentada).
- **`importar_historico_q10.py`:** mapa EXPLÍCITO periodo→cohorte (2023: pids 2-7 ·
  2024: 9/10/12/14 · 2025: 16-19; pid 16 "Unico 2025" = MR forzado). ⚠️ "Único Horario nivel
  1-3" no trae año en la etiqueta — asignados a 2024, **confirmar con el equipo**. 2026 NO se
  re-importa (es del sync diario). Participantes existentes no se tocan; solo cédulas nuevas.
- **Resultado:** +1.816 participantes nuevos → **2.875 totales** · 39 cursos·cohorte ·
  **18.195 matrículas** · 0 errores, 0 FKs perdidas. Por cohorte: 2023=336 · 2024=470 ·
  2025=1.038 · 2026=1.059. Gotcha: Q10 reutiliza nombres de curso entre años ("…- 2026" en
  cohorte 2023) — UNIQUE(nombre, cohorte) los separa.
- **Frontend:** selector de cohorte (verde) junto al de programa; cohortes pasadas muestran
  Resumen + Cursos (Historial/Emprendimiento/Demografía son de la cohorte actual).
- Re-ejecución: idempotente; correr de nuevo solo si Q10 gana periodos históricos nuevos.

## Sociodemográficos MR (2026-07-10, pedido stakeholders)
- **Fuente:** `BD-Mujeres ROFÉ 2026 (2).xlsx` (Downloads; la fuente viva es el Google Sheet de
  [[mr-actualizacion-datos]], actualizado a diario 9:30 por n8n — actualizar `RUTA_BD` al cambiar
  versión del export). Pestañas: `General` (5.126 cédulas) + `Inactivas` (retiradas, fuente
  secundaria — General gana). `HerpowerED` NO se lee (copia de General).
- **Script:** `sync_sociodemograficos_mr.py` — espejo del sync JC, restringido a participantes
  con matrícula en cursos `programa=mr` (una cédula en ambos programas no pisa los datos JC de
  la BD monitorias). Mapeo por substring a los enums existentes.
- **Novedad clave:** primera fuente real de `tipo_vivienda`, `estrato`, `estado_civil` y
  `nivel_estudio` — los 4 campos que estaban "SIN FUENTE" ahora se llenan para MR (para JC
  siguen sin fuente; COMMENTs de columna actualizados en la migración `sociodemograficos_mr`).
  Además: edad, ciudad, `genero='Femenino'` (constante — programa de mujeres) y
  `nombre_emprendimiento`/`tiene_emprendimiento` (c19 Emprendimiento con nombre real).
- **Vista pública:** `v_mr_demografia` (GRANT anon, solo conteos) — 6 dimensiones:
  estado_civil, nivel_estudio, tipo_vivienda, estrato, edad_rango, emprendimiento. La dimensión
  emprendimiento solo cuenta filas con datos de la BD (el default `false` inflaría el "sin").
- **Corrida inicial (2026-07-10):** 531 actualizadas — **280/282 de la cohorte 2026 (99.3%)**;
  las MR históricas 2025 solo 26.9% (ya no figuran en la BD 2026 — limitación de fuente,
  no de proceso). 9 migraciones totales.
- Re-ejecución: manual tras cambios grandes en la BD (mismo criterio que el sync JC); idempotente.

## Cohorte canónica en el panel — "Ingresados 832" (2026-07-10, pedido stakeholders)
El total mostrado para el año en curso es la **cohorte canónica** (todos los registros del año
menos retiros institucionales/desertores y perfiles de prueba): JC 2026 = **832** = 777 activos
+ 57 retirados; MR = 282. El avance por curso se muestra **sobre la cohorte completa**
(`cursaron`), no solo sobre los activos.
- **Tablas nuevas** (migración `aprobacion_cohorte_canonica`, lectura pública, sin PII):
  `cohorte_ingresos` (cohorte × programa: ingresados/activos/retirados) y `aprobacion_cursos`
  (cohorte × curso: cursaron, aprobados, aprobados_retirados, retirados, bandas, promedio).
- **Fuente:** `docs/aprobacion/data.json` (ya público) vía `sync_aprobacion_supabase.py` —
  re-correr tras cambios relevantes del panel de aprobación (candidato a encadenarse en n8n).
- **Escalabilidad de año:** nada hardcodeado — la cohorte sale del campo `anio` del JSON y el
  frontend deriva la "cohorte actual" como la mayor presente en los datos. Cambio de año =
  el pipeline escribe el año nuevo y el panel lo adopta solo.
- **Frontend (commit `a84fe45`):** KPI "Ingresados" en la cohorte actual; Resumen y Cursos con
  gráfico apilado sobre la cohorte (aprobó / en curso / aprobó y se retiró / retiró sin aprobar
  — mismos criterios del panel de aprobación); cohortes históricas siguen con v_curso_completion.
  Demografía JC muestra ciudades completas (`ETIQUETA_GRUPO`: BAQ→Barranquilla, BOG→Bogotá,
  CAL→Cali, CTG→Cartagena, MED→Medellín, GYL→Guayaquil, QTO→Quito, PAN→Panamá, UY→Uruguay).
- Con esto queda cubierto el pendiente "retirados en Supabase" a nivel de agregados (las filas
  individuales de retirados siguen sin existir en `participants` — limitación del Consolidado).

## Cuadre (Fase 4) — VERIFICADO 2026-07-10
`test_cuadre_dashboard.py`: v_curso_completion (Supabase) vs docs/aprobacion/data.json —
**9/9 cursos exactos en activos y aprobados** (misma frescura de fuentes). Gotcha: con fuentes
de corridas distintas, los cursos ACTIVOS derivan (+4/+9 aprobados en 12 h de avance real de
estudiantes) — es frescura, no bug; el sync diario acota la deriva a ≤24 h vs las 4 h del
pipeline GitHub Pages.
Next.js 14 **export estático** (`output:'export'` → carpeta `out/`, sin SSR ni plugin Netlify —
decisión que elimina el netlify.toml problemático del plan original). 4 tabs: Resumen / Cursos /
Emprendimiento / Demografía, consumiendo las vistas `v_*` + `cohorte_stats` con anon key.
Identidad ROFÉ (paleta Manual 2025, Century Gothic, logo Aplicación 2). First Load JS 195 kB.
Preview local: `python -m http.server` sobre `out/`.
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
  - ~~⚠️ La introspección confirmó que **vivienda/estrato/estado_civil/nivel_estudio NO existen en
    ninguna fuente**~~ → **corregido 2026-07-10:** la BD-Mujeres ROFÉ SÍ los trae para la población
    MR (ver sección "Sociodemográficos MR"). Para JC siguen sin fuente. `Link Emprendimiento`
    (c98) es el link de Zoom de la clase, NO un emprendimiento del estudiante.
- **Datos sociodemográficos MR — cargados (2026-07-10):** fuente = BD-Mujeres ROFÉ
  ([[mr-actualizacion-datos]]), script `sync_sociodemograficos_mr.py` (ver sección arriba).

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

## Separación JC / MR (2026-07-10, pedido stakeholders)
Son dos secciones separadas de la fundación — la demografía de cada programa solo puede salir
de su propia población. Migración `separacion_programas_jc_mr`:
- **Función helper `participa_en(participant_id, programa)`** (matrícula en cursos del programa).
- **Vistas JC con filtro explícito:** `v_demografia_grupo`, `v_edad_distribucion`,
  `v_emprendimiento_situacion`, `v_emprendimiento_vs_cursos` — antes eran "JC" solo de forma
  implícita (solo JC tenía esos campos) y la carga MR las contaminó (525 mujeres en la
  distribución de edad JC).
- **`cohorte_stats` por (cohorte, programa)** — PK compuesta, `recompute_aggregates()`
  actualizado. Edad promedio 2026: JC 18.0 / MR 39.6 (antes una sola fila mezclada 39.58).
- **Frontend:** KPIs buscan por cohorte+programa; el KPI Edad promedio aparece en ambos
  programas sin mezclarse (commit `bc18381`).

## Gotchas / Limitaciones conocidas
- **Una función dentro de una vista corre con los privilegios del CALLER, no del dueño de la
  vista (2026-07-10).** Al separar programas, `participa_en()` (SECURITY INVOKER) dejó las vistas
  JC **vacías para anon**: RLS bloqueaba enrollments/courses dentro de la función, el EXISTS daba
  false y el panel de Demografía/Emprendimiento JC quedó en blanco — mientras las consultas de
  verificación (como postgres) veían todo bien. Los joins escritos directo en el cuerpo de la
  vista sí corren como el dueño (por eso v_mr_demografia nunca falló). Fix: `SECURITY DEFINER` +
  `set search_path` (migración `participa_en_security_definer`). Regla: helper llamado desde
  vistas públicas → SECURITY DEFINER, y **verificar siempre con el anon key**, no solo con SQL.
- **⚠️ El upsert diario BORRABA los sociodemográficos (detectado y corregido 2026-07-10).**
  `normalize_q10_data.py` mandaba `edad/ciudad/tipo_vivienda/estrato/estado_civil/nivel_estudio`
  como `null` explícito en cada participante y el `merge-duplicates` del loader los sobreescribía
  cada mañana a las 9:45 (JC perdió edad+ciudad el 10-07; género/grupo/fecha_nacimiento/situación
  sobrevivieron porque esas claves nunca fueron parte del payload). Fix: el payload solo lleva las
  claves que el ETL conoce (`q10_id`, `nombre`, `email`). Los datos JC se restauraron re-corriendo
  `sync_sociodemograficos.py`. Regla general: **con PostgREST merge-duplicates, un `null` explícito
  ES una escritura** — nunca incluir claves que otro proceso posee.
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
- [x] Sociodemográficos MR cargados (`sync_sociodemograficos_mr.py`, 531 actualizadas, 2026-07-10)
      + vista `v_mr_demografia` — mismo criterio de re-corrida manual que el sync JC
- [x] Frontend: tab Demografía para MR consumiendo `v_mr_demografia` (2026-07-10, commit `7ef41b1`
      del repo frontend — 6 gráficos: estado civil, estudios, vivienda, estrato, edad, emprendimiento;
      etiquetas en femenino sobre los enums genéricos). Emprendimiento (encuesta) sigue solo JC.
- [x] Fase 1b: workflow n8n `q10-sync-supabase` (`uSizw3dNzpb6n53H`, diario 9:45, activo) + JSON exportado
- [x] Recompute de agregados: función SQL `recompute_aggregates()` (migración `recompute_aggregates_fn`,
      solo service_role) invocada por el loader — 1.059 métricas + cohorte 2026 poblada
- [x] Fase 4: cuadre 9/9 exacto vs dashboard canónico (2026-07-10, `test_cuadre_dashboard.py`)
- [x] Deploy Netlify en producción (2026-07-10)
- [x] Cohorte canónica en el panel: `cohorte_ingresos` + `aprobacion_cursos` +
      `sync_aprobacion_supabase.py` (2026-07-10, ver sección "Cohorte canónica")
- [ ] Encadenar `sync_aprobacion_supabase.py` al workflow n8n (corre manual por ahora —
      re-correr cuando cambien las cifras del panel de aprobación)
- [ ] Verificar la primera corrida automática (hoy 9:45) en ejecuciones de n8n
- [ ] Renombrar sitio Netlify (`classy-pasca-eecdd6` → ej. `panel-rofe`) — opcional, Samuel
- [ ] Fase 2: materialized views (retirados con definición canónica) + decidir campo `programa`
- [ ] Fase 3: Next.js + Netlify
- [ ] Fase 4: test de cuadre contra `docs/dashboard|aprobacion|retirados/data.json` antes de reemplazar nada
