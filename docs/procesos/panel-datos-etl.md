# Panel de Datos Supabase (ETL + Dashboard)

**Estado:** ✅ MVP completo (Fases 0-4) — en producción: https://classy-pasca-eecdd6.netlify.app (2026-07-10)
**Última actualización:** 2026-07-14

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

## Filtro por ciudad en el panel JC (2026-07-14, pedido stakeholders)
Botonera de ciudad en el panel de Jóvenes creaTIvos. `grupo_ciudad` (BAQ, BOG, CAL, CTG, MED,
GYL, QTO, PAN, UY) viene de la **BD de monitorias** vía `sync_sociodemograficos.py`.

- **Vistas por ciudad** (lectura pública, solo agregados): `v_demografia_grupo`,
  `v_programa_stats_por_ciudad`, `v_curso_completion_por_ciudad`, `v_emprendimiento_por_ciudad`.
- **Alcance del filtro:** al elegir ciudad se filtran KPIs, completación por curso,
  emprendimiento, demografía e historial. El selector **solo aparece en la cohorte actual** —
  la BD de monitorias únicamente cubre el año en curso; en cohortes pasadas `grupo_ciudad` es
  NULL y el filtro mostraría cifras del 2026. Se limpia al cambiar de programa o de cohorte.

### Qué NO tiene desglose por ciudad (y por qué) — leer antes de "arreglar" el filtro
Dos fuentes canónicas no traen la ciudad. No es un bug del frontend: el dato no existe.

1. **Cohorte canónica / aprobación.** `cohorte_ingresos` y `aprobacion_cursos` salen de
   `docs/aprobacion/data.json`, que no tiene `grupo_ciudad` (los retirados no llegan con
   ciudad). Por eso, con una ciudad elegida, el Resumen **cambia de gráfico**: en vez de
   `GraficoAprobacion` (aprobados/retirados sobre la cohorte completa) muestra
   `GraficoCursos` sobre `v_curso_completion_por_ciudad`, y el KPI pasa de "Ingresados 832"
   a "Participantes en <Ciudad>" (activos). Mezclar ambos daría un total nacional dentro de
   una vista de ciudad.
2. **Histórico por ciudad — no es reconstruible hacia atrás.** `historial_cursos` (serie desde
   2026-06-26) solo guarda `fecha × curso × programa`; nunca guardó la ciudad. Y
   `enrollments.fecha_inscripcion` está **100% NULL** (18.196 filas), así que tampoco se puede
   inferir cuándo entró cada quien. ⚠️ Gotcha: una vista que intente reconstruirlo con
   `fecha_inscripcion <= fecha` compila y devuelve **puros ceros** (se creó y se eliminó
   `v_historial_por_ciudad` por esto).
   - **Solución:** tabla `historial_cursos_ciudad` (UNIQUE `fecha,curso,grupo_ciudad`, lectura
     pública), que `cargar_supabase.py` llena con un snapshot diario desde
     `v_curso_completion_por_ciudad` — mismo patrón que `historial_cursos`. **La serie arranca
     el 2026-07-14** (63 filas: 9 ciudades × 7 cursos) y crece un punto por día. El gráfico lo
     dice en su nota; el histórico nacional previo sigue intacto sin filtro.

## Emoflow — ingresos al sistema como proxy de "calidad de estudiante" (2026-07-14)
Emoflow es la herramienta de estado de ánimo de los estudiantes. De momento **no** medimos la
emoción sino los **ingresos al sistema** (contador acumulado por estudiante) como proxy de
engagement / calidad.

- **Fuente:** pestaña `+Ingresos-EmoFlow` del Sheet manual (mismo de `Avance`, gid `1288133311`):
  `Usuario | Nombre | Area | Ingresos al sistema | Ultimo ingreso` — 823 filas.
- **Script:** `sync_emoflow.py` → tabla `emoflow_ingresos` (upsert por `email`, idempotente).
- **⚠️ Llave de cruce = EMAIL, y es la única posible.** Emoflow **no expone la cédula** (el resto
  del ETL cruza por cédula). El correo se normaliza (lower+trim). Los correos sin match se cargan
  con `participant_id = NULL` — no se crean `participants` desde aquí (Q10 es la fuente de verdad
  de quién existe).
- **Cruce medido (2026-07-14):** **757/823 = 92.0%** con match. Cubre **757 de los 777 activos
  de JC 2026 (97.4%)**. Los 66 sin match son correos que Q10 no conoce (retirados que ya no están
  en `participants`, o correo personal distinto al registrado en Q10).
- **Privacidad:** la tabla lleva email+nombre (PII) → RLS **sin lectura anónima** (verificado:
  anon obtiene 0 filas). El panel consume solo agregados vía 3 vistas públicas (GRANT anon):
  - `v_emoflow_resumen` — KPIs (participantes, promedio 23.2, mediana 18, máx 309, activos 7d/14d,
    inactivos 30d).
  - `v_emoflow_por_ciudad` — usa el mismo código `grupo_ciudad` (BAQ/BOG/…) del filtro de ciudad,
    así que el `Area` de Emoflow se mapea a los 9 grupos canónicos y el filtro funciona igual.
  - `v_emoflow_bandas` — bandas de ingresos (1-5 · 6-15 · 16-30 · 31-60 · 61+) **cruzadas con el
    avance real** de la cohorte JC 2026. Responde "¿el que más entra, avanza más?".
- **Hallazgo:** la relación es **monótona pero suave** — banda 1-5: 88.1% de avance y 82.5% de
  aprobación; banda 31-60: 94.6% / 88.2%. Más ingresos correlaciona con más avance, pero la
  diferencia es de ~6 puntos: sirve para detectar el extremo bajo (102 estudiantes con ≤5 ingresos),
  no como predictor fino.
- **Automatizado (2026-07-14):** `sync_emoflow.py` encadenado al workflow n8n `q10-sync-supabase`
  tras `¿Aprobación OK?` (nodos `Ejecutar sync_emoflow` → `¿Emoflow OK?` → `OK` / `Error Emoflow`).
  14 nodos, activo, corre solo cada día a las 9:45.

## Puntaje compuesto de "calidad de estudiante" (2026-07-14)
Vista `v_puntaje_estudiante` (JC, cohorte actual) + `reporte_puntaje.py`. Combina avance Q10,
asistencia Zoom e ingresos Emoflow, cada señal como **percentil dentro de la cohorte**.

**Regla de negocio vigente (pedido de Samuel):** **Emoflow (ingresos) es el criterio MAYOR — 60% —
y es obligatorio: sin Emoflow el estudiante no cuenta** (queda fuera del ranking). Avance Q10 40%.
Asistencia 0% por ahora (ver abajo). Los pesos se ajustan por CLI (`--peso-ingresos`,
`--peso-avance`, `--peso-asistencia`), no hay que tocar SQL.

**Ojo con la exclusión:** es una decisión de negocio, no un default técnico. En Bogotá deja fuera a
5 de 133; a nivel cohorte, a los 20 sin Emoflow. Si un día Emoflow deja de cubrir bien a alguien,
ese estudiante desaparece del ranking sin aviso — vigilar la cobertura (hoy 757/777 = 97%).

**Cobertura de las 3 señales sobre los 777 de JC 2026:** avance **777 (100%)** · Emoflow
**757 (97%)** · asistencia **408 (53%)** — las 3 juntas solo **398**.

**Dos trampas que se encontraron construyéndolo (y por eso NO se usan valores crudos):**
1. **Techo del avance.** `avance_q10` = 92.8 ± 6.7: casi no discrimina. Con peso nominal 50%
   aportaba lo **menos** al ranking (0.50×6.7 = 3.4) mientras la asistencia con 30% aportaba lo
   **más** (0.30×22.8 = 6.8). Los pesos no significaban lo que decían.
2. **Faltar dato premiaba.** Renormalizando sobre crudos, a quien no tenía asistencia el avance
   (~93) le apuntalaba el puntaje → los de 2 señales promediaban **más** (80.2) que los de 3
   (78.8). Con percentiles (las 3 señales uniformes en [0,100]) ambos sesgos desaparecen.

**Las 3 señales son casi independientes:** corr avance↔asistencia **0.10**, avance↔ingresos
**0.27**, asistencia↔ingresos **0.18**. No hay un "factor calidad" latente detrás — el compuesto
promedia cosas distintas. Vale mostrar también las señales por separado, no solo el número.

**⚠ La asistencia todavía no es usable como componente:** viene de **un solo curso**
(`Desarrollo Web - GIT, HTML y CSS`, 3 salas) y lleva ~11 días de captura (1→11 jul) → **1.4
sesiones por persona**, solo **4 estudiantes con ≥3**. Un promedio sobre 1 sesión es ruido. Por eso
el ranking por defecto (`puntaje_sin_asistencia` = avance 60% + ingresos 40%) cubre a los 777.
Revisar cuando la captura acumule sesiones y llegue a más cursos.

**Limpieza pendiente:** `asistencia_zoom` tiene ~10 registros de staff/test ("Mi reunión",
"Reunión con Katze", "Prueba - Asistencia", "Entrevista NOVA", "Reunión Semanal de Monitores").
- **Futuro:** la pestaña `Emoflow` cruda (11.946 filas, formato ancho `Semana 1..15` con bloques
  `Email | Nombre | Ciudad | Registro Emoción | Fecha`) tiene el registro emocional semanal — es la
  extensión natural cuando se quiera medir ánimo y no solo ingresos.

## 🔴 Incidente de PII: vistas expuestas a anon (detectado y tapado 2026-07-14)
Al planear el tab de Emoflow se descubrió que **el anon key (público, va en el bundle de Netlify)
podía leer datos personales**:

| Objeto | Exponía | Origen |
|---|---|---|
| `v_puntaje_estudiante` | **777 nombres + correos** | Creada ese mismo día |
| `asistencia_promedio` | **490 correos** | Policy `allow_read` permisiva, preexistente |

**Causa raíz:** Supabase concede `SELECT` a `anon` **por defecto** en `public`, y **una vista corre
con los privilegios de su dueño → ignora el RLS** de las tablas que consulta. Por eso
`emoflow_ingresos` (tabla con RLS) daba 0 filas a anon, pero la **vista sobre ella** daba las 777.
No basta con "no dar GRANT": hay que **revocar explícitamente**.

**Fix** (migración `revocar_pii_anon`): `revoke all ... from anon, authenticated` sobre
`v_puntaje_estudiante`, `asistencia_promedio` y `asistencia_zoom`; eliminada la policy `allow_read`.
Verificado con el anon key: las 5 fuentes con PII → 401 / 0 filas; los 8 agregados que consume el
panel → siguen respondiendo. Regla completa en [[convenciones#⚠️ Supabase: una VISTA con PII se expone a `anon` aunque nunca le des GRANT]].

**Lección de método:** las consultas de verificación como `postgres`/service_role **mienten** — ven
todo bien. Cualquier cambio de exposición se valida **con el anon key**.

## Tab Emoflow en el panel (2026-07-14)
Tab nuevo en el panel Netlify (solo JC + cohorte actual — la fuente no tiene dimensión de cohorte y
tiene 0 matrículas MR). Consume 4 vistas de agregados: `v_emoflow_resumen`, `v_emoflow_por_ciudad`,
`v_emoflow_bandas` y `v_emoflow_bandas_ciudad` (nueva — sin ella, con una ciudad elegida el gráfico
mostraría cifras **nacionales** dentro de una vista de ciudad; misma trampa del historial).
Contenido: 4 KPIs (estudiantes, ingresos promedio, activos 7d, inactivos +30d) · distribución de uso
por bandas · "¿el que más entra, aprueba más?" (con nota honesta: la relación es suave, 82→88%) ·
uso por ciudad (solo en vista nacional). Respeta el filtro de ciudad.

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
- **Filtro por ciudad (2026-07-14):** se agregó selector de ciudades en el tab Resumen (solo JC).
  Clickear una ciudad filtra KPIs y gráfico de demografía para mostrar solo datos de esa ciudad.
  Los participantes mostrados reflejan la ciudad seleccionada; botón "Todas" vuelve al resumen global.
  Commit `f47cebe`.
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
- Cadena (desde 2026-07-10 incluye aprobación): `Ejecutar normalize_q10_data` → IF estado=exito →
  `Ejecutar cargar_supabase` → IF → `Ejecutar sync_aprobacion` → IF → OK / stopAndError en cada
  paso (camino de error explícito; "con_advertencias" también alerta — FKs perdidas nunca pasan
  en silencio). El sync de aprobación consume `docs/aprobacion/data.json` del ciclo de las 8:00
  del pipeline GitHub Pages (frescura ≤ 1h45m a las 9:45). Export en
  `n8n-workflows/q10-sync-supabase.json`.

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

## ⚠️ El sync diario estuvo ROTO del 10-jul al 14-jul (detectado y corregido 2026-07-14)
El workflow `q10-sync-supabase` falló en `Ejecutar cargar_supabase` los días 10-07 y 14-07
(`status=error` en las ejecuciones). **Dos causas independientes, ambas corregidas:**

1. **Secret key revocada.** La `SUPABASE_SERVICE_ROLE_KEY` de `.env.local` devolvía
   `401 Unregistered API key` — ningún script podía escribir. Reemplazada el 14-07.
   Diagnóstico rápido: `python scripts/panel-datos/test_conexion_supabase.py`, o pegarle a
   `/rest/v1/cohorte_stats` con cada key y comparar (anon 200 vs secret 401 ⇒ key revocada).
2. **Colisión de `historial_cursos` por el import histórico.** El snapshot diario leía
   `v_curso_completion` **sin filtrar cohorte**. Como Q10 **reutiliza los nombres de curso entre
   años**, tras el import de 2023-2025 (10-07) la vista devuelve el mismo `curso` en varias
   cohortes; `historial_cursos` tiene `UNIQUE(fecha, curso)` → el lote llegaba con `curso`
   repetido y PostgREST abortaba **todo** el upsert con
   `21000: ON CONFLICT DO UPDATE command cannot affect row a second time`.
   **Fix:** filtrar el snapshot a la cohorte viva (`&cohorte=eq.{cohorte}`) en los pasos 6 y 7 de
   `cargar_supabase.py`. La serie histórica siempre fue de la cohorte actual — el filtro
   restituye esa semántica.
   **Regla general:** con `merge-duplicates` de PostgREST, **dos filas del mismo lote que colisionan
   en la clave del `on_conflict` no se resuelven entre sí — revientan el request entero.** Deduplicar
   SIEMPRE antes de mandar el lote.

Lección de proceso: el workflow sí tenía camino de error explícito (`stopAndError`), pero **nadie
lo estaba mirando** — falló 2 veces sin que se notara. Vale la pena una alerta (Telegram) en los
nodos de error, como ya la tiene el bot de Q10.

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
- [x] Encadenar `sync_aprobacion_supabase.py` al workflow n8n (2026-07-10: nodo tras ¿Carga OK?
      con IF + stopAndError propio; el 832 se refresca solo cada día a las ~9:47)
- [ ] **Futuro — Hoja Maestra de Participantes:** una sola pestaña limpia como fuente
      sociodemográfica diaria + actualización de usuarios vía Forms, reemplaza los syncs
      manuales de xlsx. Diseño completo en [[hoja-maestra-participantes]] (en espera,
      otras prioridades — 2026-07-10)
- [ ] Verificar la primera corrida automática (hoy 9:45) en ejecuciones de n8n
- [ ] Renombrar sitio Netlify (`classy-pasca-eecdd6` → ej. `panel-rofe`) — opcional, Samuel
- [ ] Fase 2: materialized views (retirados con definición canónica) + decidir campo `programa`
- [ ] Fase 3: Next.js + Netlify
- [ ] Fase 4: test de cuadre contra `docs/dashboard|aprobacion|retirados/data.json` antes de reemplazar nada
