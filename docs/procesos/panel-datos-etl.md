# Panel de Datos Supabase (ETL + Dashboard)

**Estado:** ✅ MVP completo (Fases 0-4) — en producción: https://venerable-truffle-331f3c.netlify.app
**Última actualización:** 2026-07-21

## Frontend (Fase 3) — EN PRODUCCIÓN
**URL vigente (2026-07-16, migración de hosting):** https://venerable-truffle-331f3c.netlify.app
— reemplaza a `classy-pasca-eecdd6.netlify.app` (repo viejo dejó de reflejar commits; se movió el
mismo historial a **github.com/comunicaciones-ai/Panel-De-Datos**, colaborador `soportejunior-codeJR`
con Write). Esta sección tenía la URL vieja desactualizada — corregido 2026-07-21 al auditar
centralización de fuentes (ver [[panel-datos-etl#Fuentes de datos aún no centralizadas]]).
Deploy automático on push. Repo dedicado local: `C:\Users\EstudiantesJC\downloads\panel-datos-rofe`.

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
- **Fuente (2026-07-21: pasó a leer el Sheet en vivo, ya no el xlsx exportado a mano):**
  Google Sheet de [[mr-actualizacion-datos]] (id `1ZsC4WyY26aOCEMrnZ_l8Tn-l69DB_0ADs5lnecaoEP8`),
  actualizado a diario 9:30 por n8n. Pestañas: `General` (5.126 cédulas) + `Inactivas`
  (retiradas, fuente secundaria — General gana). `HerpowerED` NO se lee (copia de General).
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

## Emoflow — ingresos al sistema como proxy de "calidad de estudiante" (2026-07-14, API directa 2026-07-20)
Emoflow es la herramienta de estado de ánimo de los estudiantes. De momento **no** medimos la
emoción sino los **ingresos al sistema** (contador acumulado por estudiante) como proxy de
engagement / calidad.

- **Fuente (CAMBIO 2026-07-20):** API de Emoflow (`https://emoflow.sanumbe.com`), sin Sheet intermedio.
  - Antes: pestaña manual `+Ingresos-EmoFlow` (mantenimiento, desactualizaciones).
  - Ahora: `POST /login` (credenciales en `.env.local`) → `GET /admin/registro-ingresos-exportar` (CSV, 27K registros).
  - La API devuelve cada ingreso como una fila → se agrupa por email (suma ingresos, obtiene último).
- **Script:** `sync_emoflow_api.py` (NEW, 2026-07-20) → tabla `emoflow_ingresos` (upsert por `email`, idempotente).
  `sync_emoflow.py` (DEPRECATED 2026-07-20, se mantiene por inercia) ya no se usa.
- **⚠️ Llave de cruce = EMAIL, y es la única posible.** Emoflow **no expone la cédula** (el resto
  del ETL cruza por cédula). El correo se normaliza (lower+trim). Los correos sin match se cargan
  con `participant_id = NULL` — no se crean `participants` desde aquí (Q10 es la fuente de verdad
  de quién existe).
- **Cruce medido (2026-07-20):** **759/826 = 91.9%** con match (coherente con el 92% anterior). 826 usuarios únicos en Emoflow.
  Los sin match son correos que Q10 no conoce (retirados que ya no están en `participants`, o correo personal distinto).
- **Privacidad:** la tabla lleva email+nombre (PII) → RLS **sin lectura anónima** (verificado:
  anon obtiene 0 filas). El panel consume solo agregados vía 3 vistas públicas (GRANT anon):
  - `v_emoflow_resumen` — KPIs (participantes, promedio, mediana, máx, activos 7d/14d, inactivos 30d).
  - `v_emoflow_por_ciudad` — usa el mismo código `grupo_ciudad` (BAQ/BOG/…) del filtro de ciudad,
    así que el `Area` de Emoflow se mapea a los 9 grupos canónicos y el filtro funciona igual.
  - `v_emoflow_bandas` — bandas de ingresos (1-5 · 6-15 · 16-30 · 31-60 · 61+) **cruzadas con el
    avance real** de la cohorte JC 2026. Responde "¿el que más entra, avanza más?".
- **Hallazgo:** la relación es **monótona pero suave** — banda 1-5: 82.5% de aprobación; banda 31-60: 88.2%.
  Más ingresos correlaciona con más avance, pero la diferencia es de ~6 puntos: sirve para detectar el extremo bajo,
  no como predictor fino.
- **Automatizado — corregido 2026-07-21:** el nodo `sync_emoflow_api.py` se documentó como
  encadenado el 2026-07-20 pero **el workflow en vivo seguía llamando al script deprecado**
  `sync_emoflow.py` (Sheet manual) — verificado consultando `GET /workflows/{id}` en vivo, no
  solo el JSON exportado. Corregido 2026-07-21 vía API: el nodo ahora ejecuta
  `sync_emoflow_api.py` de verdad (`Ejecutar sync_emoflow_api` → `¿Emoflow OK?` → `OK` /
  `Error Emoflow`), diario 9:45. **Lección:** el JSON en `n8n-workflows/` puede desalinearse
  del workflow real si se edita por API sin re-exportar — verificar siempre contra
  `GET /workflows/{id}` cuando la duda importe. Credenciales: `EMOFLOW_USER`,
  `EMOFLOW_PASSWORD` en `.env.local` (nunca en git).

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

## Backfill del historial de participación Emoflow (2026-07-15)
El gráfico "Evolución de la participación semanal" arrancaba plano en la Semana 16 (el sync diario
`sync_emoflow_participacion.py` solo captura la semana en curso del bloque `Estadísticas`). Para
alargarlo hacia atrás se rescataron las **Semanas 1-15** desde la **pestaña `Emoflow` cruda**
(gid `175161020`, registro individual de check-ins por semana) con
`backfill_emoflow_participacion.py` (uso único).
- **Hallazgo clave:** la columna `Registro Emoción` NO es la emoción — es `Si`/`No` (si diligenció
  el check-in esa semana). No hay ánimo/emoción real en el Sheet. Lo aprovechable es el conteo de
  check-ins semanales.
- **El histórico va como CONTEO (`completado`), no como %:** el `Real` (denominador) de cada semana
  pasada no existe; usar el Real actual daría **>100%** en ciudades cuya cohorte encogió (CAL: 102
  check-ins en Sem.2 vs 93 hoy). El conteo es **fiel** — validado contra el bloque Estadísticas
  para la Semana 16 (coincide en 7/9 ciudades, ±1 en las otras 2). El frontend cambió el gráfico
  de evolución de `avance_pct` → `completado` ("Check-ins").
- Cada semana lleva su fecha real (de la columna `Fecha`); `fuente='backfill-crudo'`. La Semana 16
  no se tocó (la maneja el sync diario en vivo, y aparece más baja por estar en curso).
- **Tendencia revelada:** la participación decae durante el semestre (total ~690 en Sem.1 → ~530 en
  Sem.15). Serie ahora de 16 fechas (antes 1).

## Tab Emoflow en el panel (2026-07-14)
Tab nuevo en el panel Netlify (solo JC + cohorte actual — la fuente no tiene dimensión de cohorte y
tiene 0 matrículas MR). Consume 4 vistas de agregados: `v_emoflow_resumen`, `v_emoflow_por_ciudad`,
`v_emoflow_bandas` y `v_emoflow_bandas_ciudad` (nueva — sin ella, con una ciudad elegida el gráfico
mostraría cifras **nacionales** dentro de una vista de ciudad; misma trampa del historial).
Contenido: 4 KPIs (estudiantes, ingresos promedio, activos 7d, inactivos +30d) · distribución de uso
por bandas · "¿el que más entra, aprueba más?" (con nota honesta: la relación es suave, 82→88%) ·
uso por ciudad (solo en vista nacional). Respeta el filtro de ciudad.

## Tab Emoflow — rehecho: serie diaria/semanal REAL y "todo directo de Emoflow" (2026-07-20/21)
Pedido de Samuel: **toda la pestaña Emoflow debe venir directo de Emoflow** (Emoflow→Supabase cuenta;
hojas u otras fuentes NO). Se auditó cada dato y se corrigió la cadena.

- **Descubrimiento clave (vía .har + credenciales):** el CSV de `/admin/registro-ingresos-exportar`
  es un **log de EVENTOS con timestamp**, no un acumulado. ~27k eventos, 844 usuarios, **120 días**
  (desde 2026-03-18). Columnas: `Usuario, Nombre, Empresa, Area, Fecha emociones, Fechas bienestar,
  Dimensiones bienestar completadas`. **Bienestar viene vacío** para la org; solo se miden ingresos.
- **Definiciones (se confundían):** `ingresos` = **registros de emoción** (una persona genera VARIOS
  por día — ej. 37 en un día, varios en el mismo minuto); NO son logins. `usuarios_activos` =
  **personas distintas**.
- **Se DESCARTÓ un enfoque 4h inventado** (métricas emociones/bienestar/rangos hardcodeadas) —
  tabla/workflow/script/doc borrados. No usar `emoflow_ingresos_agregados_4h` (ya no existe).
- **Script `extract_emoflow_ingresos_diario.py`** (una corrida llena 2 tablas, idempotente, re-lee
  los 120 días):
  - `emoflow_ingresos_diario` (fecha × grupo_ciudad + NACIONAL): ingresos + usuarios_activos por día.
  - `emoflow_actividad_semanal` (semana_inicio=lunes ISO × grupo_ciudad): usuarios_activos, roster
    (matrícula Emoflow = distinct histórico de la ciudad), pct_activos = 100·activos/roster.
  - **n8n `emoflow-ingresos-diario`** (id `DFPiF1RtD58FhGoZ`), scheduleTrigger **diario 21:30 COT**,
    ACTIVO. Gotcha: activar por API `/activate` (el UPDATE directo en SQLite no registra el trigger);
    connections deben ir en formato `{"main": [[...]]}`.
- **Panel (repo comunicaciones-ai/Panel-De-Datos):**
  - "Evolución de ingresos al sistema" = serie diaria real (nacional; por ciudad al filtrar);
    reemplaza el backfill plano de `historial_emoflow` (repetía 32.5). Notas aclaran ingresos vs usuarios.
  - "Participación semanal" ahora sale de **`emoflow_actividad_semanal`** (100% Emoflow), no del Sheet.
    Métrica = **% de matrícula activa** por semana/ciudad. Eje X por **lunes ISO** (orden temporal
    correcto — antes ordenaba "Sem 1, Sem 10, Sem 2…" por localeCompare del label en GraficoHistorial).
  - **Solo semanas COMPLETAS:** una semana entra cuando pasa su domingo (según la última fecha con
    datos). La semana en curso llevaría pocos días y aparecería como el punto más bajo del histórico
    (artefacto, no bajón real). El snapshot por ciudad usa la última semana completa.
  - "Participar → aprobar" se **mantiene pero etiquetado** (la aprobación viene de **Q10**, cruce).
  - **Gotcha frontend:** PostgREST corta en 1000 filas aunque se pida `limit` mayor → se agregó
    `leerPaginado()` (header Range) en `lib/api.ts`; si no, se perdían los días recientes.
- **`sync_emoflow_participacion.py` — ELIMINADO del pipeline (2026-07-21).** Seguía corriendo
  a diario en `q10-sync-supabase` sin que el panel lo consumiera desde el rehecho de arriba.
  Confirmado con Samuel que genuinamente no se quiere: se quitaron los 3 nodos del workflow
  en vivo (`Ejecutar sync_emoflow_participacion` → `¿Participación OK?` → `Error Participación`,
  reconectando `¿Emoflow OK?` directo a `OK`) y el script se movió a
  `scripts/panel-datos/_obsoletos/`. La tabla `emoflow_participacion_semanal` queda en
  Supabase sin escrituras nuevas (no se borró — es dato histórico, bajo riesgo dejarla
  dormida; se puede eliminar más adelante si se confirma que nadie la necesita).

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

## Histórico diario de Emoflow (ingresos al sistema) (2026-07-15)
Pedido de Samuel: "ir tomando un rastro de valores diarios de emoflow para graficar los avances".
`sync_emoflow.py` hacía **upsert puro** (`on_conflict=email`) — sobrescribía el estado cada día sin
dejar rastro histórico, así que no había nada que graficar en el tiempo.

**Fix:** tras el upsert de `emoflow_ingresos`, el script ahora hace un snapshot diario de los
**agregados** (nunca filas individuales — PII) en dos tablas nuevas (mismo patrón que
`historial_cursos`/`historial_cursos_ciudad`):
- `historial_emoflow` (nacional, `UNIQUE(fecha)`): participantes, ingresos_promedio/mediana/max,
  activos_7d/14d, inactivos_30d. Se lee de `v_emoflow_resumen` ya actualizada.
- `historial_emoflow_ciudad` (`UNIQUE(fecha, grupo_ciudad)`): mismo desglose por ciudad, de
  `v_emoflow_por_ciudad`.

Ambas con GRANT anon, verificadas sin PII. **Primer snapshot real cargado 2026-07-15** (823
participantes, 757 con match). Como `sync_emoflow.py` ya estaba encadenado en el workflow n8n
`q10-sync-supabase` (último paso, 9:45 diario), la captura queda automática **sin tocar el
workflow**. Frontend: sección "Evolución de ingresos al sistema" en el tab Emoflow (reusa
`GraficoHistorial`), commit `d81f42d`. La serie es nueva — arranca plana y se vuelve útil según
se acumulan días/semanas.

## % de participación semanal por ciudad (bloque EMOFLOW de Estadísticas) — COMPLETADO 2026-07-15
Segunda parte del pedido de histórico de Emoflow: graficar en el tiempo el **% de participación**
que Samuel ubica en la pestaña **Estadísticas** de la BD Seguimiento de Monitorias (hoja de 35+
pestañas, ver [[bd-seguimiento-monitorias]]). Confirmado con Samuel: es el bloque con encabezado
en columna A `EMOFLOW` (no toda la pestaña) — 9 filas de ciudad + fila total, columnas
`Seleccionados | Seleccionados|F | Real | Revocados | Retirados | Sin completar | Completado |
Avance`. El **`Avance`** (= Completado/Real) es el "% de participación". El bloque lleva una
etiqueta **"Semana N"** una fila arriba, en la misma columna donde otros bloques traen el rótulo
de banda (offset, no en columna A).

**Descubrimiento clave — el Sheet ID YA era conocido:** al pedirle a Samuel el link para dar
acceso, resultó ser **el mismo Sheet ID `1ggzoJeZR3fS6AwRCLoGeYA5HEp_B7zvOwFGlGwny0l8`** que ya
usan `sync_emoflow.py`/`export_avance.py` ("Sheet manual, mismo de Avance") — es decir, "BD
Seguimiento de Monitorias" **no es un archivo separado con Sheet ID propio**: es la MISMA hoja
gigante (42 pestañas: Seguimiento, Estadísticas, Avance, +Ingresos-EmoFlow, las 9 ciudades, etc.),
y el service account **ya tenía acceso** (verificado abriendo el Sheet en vivo, sin esperar el
permiso nuevo). La suposición anterior en esta nota (dos sheets distintos) era incorrecta —
corregida aquí.

**El bloque se mueve de posición cada semana — verificado empíricamente:** entre el export local
del 09-jul (bloque en fila 169, "Semana 15") y la lectura en vivo del 15-jul (fila 184, "Semana
16") la fila cambió. `sync_emoflow_participacion.py` por eso **nunca asume fila fija**: busca
"EMOFLOW" en columna A en cada corrida (`ws.col_values(1)`), y la etiqueta de semana buscando
"semana" en toda la fila anterior (no solo columna A). No hay semanas anteriores preservadas en
la hoja — se captura desde ahora, sin backfill posible.

**Tabla `emoflow_participacion_semanal`** (migración `fix_rls_historial_emoflow_y_participacion`,
RLS + policy pública de solo lectura desde el inicio): `fecha_corte, semana, grupo_ciudad,
seleccionados, seleccionados_f, real, revocados, retirados, sin_completar, completado,
avance_pct` — `UNIQUE(fecha_corte, grupo_ciudad)`. **Upsert diario, no por semana**: leer el
mismo bloque "Semana N" varios días seguidos captura cómo sube Completado/Real DENTRO de la
semana (no solo el salto cuando cambia el número). Sin PII (no hay cédulas/correos en este
bloque). No se guarda la fila de totales — es agregable desde las 9 filas de ciudad.

**Script `sync_emoflow_participacion.py`:** conecta al Sheet vivo (gspread, mismas credenciales
del Service Account de siempre), localiza el bloque por texto, parsea números con formato
español (`'53,85%'` → `53.85`), valida `grupo_ciudad` contra el set canónico de 9 ciudades.
Primera corrida real: Semana 16, 9 ciudades, sin errores.

**Encadenado a n8n (vía API, en vivo):** nuevo tramo al final del workflow
`q10-sync-supabase` (`uSizw3dNzpb6n53H`) — `¿Emoflow OK?` ahora apunta a
`Ejecutar sync_emoflow_participacion` → `¿Participación OK?` → `OK` / `Error Participación`
(antes `¿Emoflow OK?` iba directo a `OK`). 17 nodos totales, activo, verificado con
`GET /workflows/{id}` tras el `PUT`. Exportado a `n8n-workflows/q10-sync-supabase.json`.

**⚠️ Gotcha de seguridad detectado y corregido en el camino:** `historial_emoflow` y
`historial_emoflow_ciudad` (creadas la sesión anterior) habían quedado con **RLS deshabilitado**
— solo tenían `GRANT SELECT`, sin `ENABLE ROW LEVEL SECURITY` + policy, a diferencia del patrón
correcto usado en `historial_cursos`/`historial_cursos_ciudad`. El advisor de Supabase lo marcó
como hallazgo CRÍTICO al crear la tabla nueva. Corregido en la misma migración (RLS + policy
`for select to public using (true)`, igual que las tablas gemelas) — verificado con anon key que
la lectura sigue funcionando y que un POST anónimo da 401. **Regla:** toda tabla pública nueva
debe llevar `ENABLE ROW LEVEL SECURITY` + policy explícita en el MISMO statement que la crea,
nunca solo `GRANT SELECT` (que no genera la alerta de RLS pero deja la tabla en un estado frágil
si algún día se le da un GRANT más amplio sin querer).

**Frontend:** dos secciones nuevas en el tab Emoflow — barra "% de participación — Semana N"
(snapshot más reciente, 9 ciudades) y "Evolución de la participación semanal" (línea por ciudad,
reusa `GraficoHistorial`). Ambas ocultas con ciudad elegida (evita mezclar universos, mismo
patrón que el resto del panel). Commit `41e6946`.

## Botón "Fuentes de datos" — probado y revertido (2026-07-15)
Se implementó un botón/panel desplegable en la barra superior (commit `d6612dc`) que explicaba de
qué fuente venía cada bloque de información (Q10 directo / Sheet vía Q10 / Sheets sociodemográficos
/ Sheet Emoflow). Samuel pidió eliminarlo tras verlo — revertido con `git revert` (commit `db121cc`,
limpio, sin restos de código). Si se retoma la idea en el futuro, el diseño y la redacción de las
4 categorías quedan en el historial de git de ese commit (`git show d6612dc`).

## Toggle Matrículas / Estudiantes en "Estado de la cohorte" (2026-07-14)
Botón para cambiar la unidad del desglose entre **matrículas** (inscripciones) y **estudiantes**
(personas únicas) — pedido de Samuel ("análisis por matrículas o cambia a estudiantes en general").

- **Por matrículas** (5.689 JC): aprobadas 4.858 / progreso 568 / riesgo 163 / retiradas 100 —
  de `aprobacion_cursos` (una persona cuenta en cada curso).
- **Por estudiantes** (832 JC): al día 753 / progreso 23 / riesgo 1 / retirados 57 — de la vista
  nueva `v_cohorte_estudiantes`; el estado es por **avance promedio del estudiante** en sus cursos.
- **Contraste clave para decisión:** 85.4% de matrículas aprobadas vs **96.9% de estudiantes al
  día**. No se contradicen: cada estudiante tiene ~7 cursos, ya aprobó ~6.1 (los cerrados) y va a
  mitad en Front-End (único abierto), así que su promedio individual sigue > 80 aunque esa
  matrícula puntual esté baja. La vista por matrículas "castiga" más porque cada inscripción a
  medias cuenta aparte.

**Vista `v_cohorte_estudiantes`** (migración `v_cohorte_estudiantes_agregado`, GRANT anon):
agrega `enrollments × courses` por (cohorte, programa, participante) → clasifica cada estudiante
en al_dia/en_progreso/en_riesgo por su avance promedio, y devuelve **solo conteos** por
(cohorte, programa) — 6 filas, sin PII, sin filas individuales. Los retirados no salen de aquí
(no tienen enrollments); el frontend los toma de `cohorte_ingresos`. **Privacidad verificada con
el anon key:** la vista responde agregados, `participants` sigue devolviendo `[]`.
Frontend: estado `unidadEstado` + `EstadoStat` reutilizado. Commit `74f27c2`.

**Toggle también en el tab Cursos (2026-07-15, commit `50887ee`):** el mismo `unidadEstado`
(compartido con el Resumen) cambia el tab Cursos entre:
- **Por matrículas:** gráfico apilado + tabla por curso (lo anterior).
- **Por estudiantes:** histograma "¿cuántos cursos ha aprobado cada estudiante?" — JC 2026:
  650 van 6/7 (83.7%), 95 completos 7/7 (12.2%), ~32 rezagados (≤5 cursos). Suma 777 activos.

Nueva vista `v_cohorte_estudiantes_distribucion` (migración homónima, GRANT anon): conteos por
(cohorte, programa, cursos_aprobados) → estudiantes. Sin PII (verificada con anon key). El
frontend rellena 0..max cursos para un histograma continuo (`GraficoBarras` reutilizado). A nivel
de un curso individual matrícula=estudiante, así que la distinción solo aporta agregando: por eso
"por estudiantes" en Cursos es la distribución por persona, no una tabla por curso paralela.

⚠️ **Ojo con "reprobadas":** las 100 de la tarjeta son **retiros sin aprobar**. Reprobadas
DEFINITIVAS (cursos ya cerrados, no aprobaron) = 100 + 49 `sin_finalizar` de finalizados = **149**.
Las ~682 restantes sin aprobar están en Front-End (en curso) → aún pueden aprobar, no reprobadas.

## Sección "Estado de la cohorte" — desglose accionable (2026-07-14)
Pedido de Samuel: "la mayor cantidad de valores para la toma de decisiones". Se añadió al tab
Resumen (cohorte actual, sin filtro de ciudad) una sección con el desglose canónico de las
matrículas en los 4 estados que suman a `cursaron`, cada uno con conteo, % y semáforo de color:

| Estado | Fuente (suma sobre `aprobacion_cursos`) | JC 2026 |
|---|---|---|
| 🟢 Aprobadas (>80%) | `aprobados_total` (incl. aprobados_retirados) | 4.858 · 85.4% |
| 🟡 En progreso (26-80%) | `banda_26_80` | 568 · 10.0% |
| 🟠 En riesgo (0-25%) | `banda_0_25` | 163 · 2.9% |
| 🔴 Retiradas sin aprobar | `retirados` | 100 · 1.8% |

Los 4 suman exacto las matrículas totales (5.689 JC). Componente `EstadoStat` en `page.tsx`;
el agregado se calcula en el `kpis` useMemo (`estado`) solo cuando `esCanonico`. Auto-adaptable:
suma sobre todos los cursos de `aprobacion_cursos`, sin nombres hardcodeados. Commit `43ca6a2`.

**Contexto — aprobación global vs promedio aritmético (duda de Samuel):** el dashboard GitHub
(Tab Q10, `renderT1`) muestra "Aprobación global" = `pct_aprobados` = aprobados/cursaron = 85.4%
(tasa binaria: cuántas matrículas cruzaron el 80%). El "Avance promedio" (~93%) es el promedio
del % de avance (continuo). Difieren porque miden cosas distintas; la brecha la genera sobre todo
el curso Front-End (en curso: 547 en banda 26-80 suben el promedio pero no aprueban). Ambos son
correctos; para "aprobación" el número honesto es 85.4%. Netlify ahora muestra los dos + el
desglose por estado, así que la distinción queda explícita.

## Encabezado de la cohorte actual = 100% canónico Supabase (2026-07-14)
Pedido de Samuel: "que Netlify use los aprobados canónicos, manejemos los mismos datos en todo
momento y dependamos lo mínimo posible de las Sheets". Antes había una mezcla de fuentes que
producía cifras distintas entre paneles para el mismo concepto:

| KPI cohorte actual | Antes (fuente) | Ahora (fuente) |
|---|---|---|
| Ingresados 832 | `cohorte_ingresos` ✅ | igual |
| Aprobados 85.4% JC / 31.1% MR | — (no existía) | `cohorte_ingresos.pct_aprobados` ✅ |
| Matrículas | `v_programa_stats` = 5439 (solo activos, vía Sheet h2test) | `sum(aprobacion_cursos.cursaron)` = **5689** (cohorte completa) ✅ |
| Avance promedio | `v_programa_stats` = 92.8% (Sheet h2test) | ponderado por cursaron de `aprobacion_cursos` = **93.1%** ✅ |
| Gráfico + tabla de cursos | `aprobacion_cursos` ✅ | igual |

- **Por qué importa la fuente:** `aprobacion_cursos` + `cohorte_ingresos` los alimenta
  `export_aprobacion.py`, que **entra directo a Q10** (login propio) → `docs/aprobacion/data.json`
  → `sync_aprobacion_supabase.py`. **No pasa por el Sheet h2test.** En cambio `v_programa_stats`
  y `v_curso_completion` derivan de `enrollments`, poblado por `normalize_q10_data.py` leyendo el
  **Sheet h2test**. Usar el canónico cumple "depender lo mínimo de las Sheets".
- **Nueva columna:** `cohorte_ingresos.pct_aprobados numeric(5,1)` (migración vía MCP; GRANT anon),
  calculada en `sync_aprobacion_supabase.py` desde `por_programa[].aprobados / cursaron`.
- **Frontend (`app/page.tsx`, `kpis` useMemo):** con `esActual && aprobacionProg.length > 0 &&
  !hayFiltroCiudad` (flag `esCanonico`), Matrículas/Avance/aprobados se agregan desde
  `aprobacionProg`. El frontend solo **suma/pondera** valores ya canónicos — no re-deriva desde
  matrículas crudas. Commits `cab3fb7` + `db204ce`.
- **Qué sigue usando la vista de Sheets (y por qué es correcto):** (a) cohortes históricas
  2023-2025 — `aprobacion_cursos`/`cohorte_ingresos` solo tienen 2026, no existe canónico para
  atrás; (b) vista con ciudad elegida — el canónico no trae `grupo_ciudad`. En ambos casos
  `esCanonico=false` y el KPI cae a `v_programa_stats`/`v_curso_completion` con su etiqueta propia.

## Adaptabilidad a cursos nuevos — paridad con GitHub Pages verificada (2026-07-14)
Se confirmó que el panel Netlify tiene la misma adaptabilidad automática a cursos nuevos que el
dashboard GitHub Pages: `lib/api.ts` (frontend) no tiene ningún nombre de curso hardcodeado —
lee genérico de las vistas/tablas Supabase — y el pipeline diario de n8n (`q10-sync-supabase`)
ya encadena los 4 pasos (`normalize_q10_data` → `cargar_supabase` → `sync_aprobacion` →
`sync_emoflow`, cada uno con IF + `stopAndError`), así que un curso nuevo en Q10 se propaga solo
sin intervención manual — siempre que esté clasificado en `tools/course_config.json` o matchee
las keywords MR de fallback (misma lógica canónica compartida por `normalize_q10_data.py` y
`export_stats.py`, antes duplicada sin cross-check).

**Gotcha corregido:** ese fallback por keywords caía en silencio a "jc" cuando un curso no
estaba en `course_config.json` y no matcheaba ninguna keyword MR — sin aviso, en ambos scripts.
Se agregó `rep.warn("curso_sin_config", …)` en `normalize_q10_data.py` (aparece en
`advertencias` del reporte y en el `RESUMEN` de stdout) y un log `ADVERTENCIA:` equivalente en
`export_stats.py`. No cambia clasificación ni salida — solo hace visible cuándo un curso
realmente nuevo necesita agregarse a la config (vía `tools/course_config.json` o el tab Admin
de `panel_riesgo.py`).

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
**Procesos relacionados:** [[q10-consolidacion]] · [[dashboard-web]] · [[mr-actualizacion-datos]] · [[bd-seguimiento-monitorias]] · [[postulantes-mr-supabase]]

## Qué hace
Reemplaza Power BI por un panel de visualización alimentado por Supabase (PostgreSQL) como
fuente única de verdad, con ETL diario vía n8n y frontend Next.js en Netlify. Convive en
paralelo con el dashboard GitHub Pages existente hasta validar cuadre de cifras.

Plan maestro histórico (archivado en `docs/archivo/`, fase de planeación 2026-07-09):
`PLAN-DATOS-ANALISIS-PROFUNDO.md` · `MATRIZ-DECISIONES-PENDIENTES.md` (completada) ·
`CLAUDE-CODE-PROMPTS-POR-FASE.md` · `ARQUITECTURA-VISUAL.md` · `PROXIMOS-PASOS-SESION-2.md`.

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
- **Datos sociodemográficos — mapeados y cargados (2026-07-09; automatizado 2026-07-21):**
  fuente = [[bd-seguimiento-monitorias]], Sheet id `1ggzoJeZR3fS6AwRCLoGeYA5HEp_B7zvOwFGlGwny0l8`
  (mismo Sheet gigante que Emoflow/Avance). `sync_sociodemograficos.py` y
  `sync_sociodemograficos_mr.py` **dejaron de leer el xlsx exportado a mano de Downloads** —
  ahora leen el Sheet en vivo vía gspread, lo que permitió encadenarlos a un workflow n8n
  nuevo: `sociodemograficos-semanal` (lunes 6:00 COT, alerta Telegram en error — no
  `stopAndError` porque no bloquea el pipeline diario crítico). Antes requerían re-corrida
  manual cada vez que alguien descargaba una versión nueva de la BD — riesgo de
  desactualización silenciosa, ya cerrado.
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

## Fuentes de datos aún no centralizadas — auditoría + decisiones (2026-07-21)
Análisis a fondo pedido por Samuel de qué fuentes faltan por centralizar en Supabase, con
decisión tomada para cada una (no todo se resuelve ahora — algunas quedan documentadas
adrede como "problema separado" para retomar después, dado que hoy no hay una persona
dedicada a analítica de datos).

### Retirados históricos (2023-2025) — limitación, no bug (parqueado)
`importar_historico_q10.py` excluye a propósito los retirados de las cohortes 2023-2025:
el reporte Consolidado histórico de Q10 **no expone inhabilitados**, solo el reporte de
matriculados **del periodo activo actual** los distingue. No hay endpoint de Q10 que traiga
"quién se retiró en 2024", así que no es automatizable con las fuentes que existen hoy.
**Dos caminos si se quiere cerrar esto en el futuro** (ninguno se ejecuta ahora):
1. **Aceptar el hueco** — las cohortes pasadas en el panel muestran solo activos/aprobados
   (ya es el comportamiento actual); documentar la limitación donde se muestre el dato
   (nota al pie en el frontend) en vez de intentar reconstruirlo.
2. **Búsqueda puntual** — si en algún backup/Excel viejo del equipo (fuera de Q10) existe un
   registro de retiros pre-2026, se podría hacer una carga única manual a
   `cohorte_ingresos`/`aprobacion_cursos` de esas cohortes — pero requiere que ese archivo
   exista y aparezca; no se sabe si existe.

   **Camino 2 ejecutado (2026-07-21):** búsqueda de solo lectura en `Downloads/` (xlsx/csv con
   "retirad"/"cancelad"/"desertor"/"aplazad"/2023/2024), en el repo (`docs/archivo/`,
   `tools/`), en el historial de git (`git log --all --diff-filter=D`) y en Google Drive
   (`retirados 2023/2024`, "cancelados", "desertores"). Resultado:
   - **JC — nada nuevo.** La pestaña `S Retirados` de `BD Seguimiento de Monitorias - JC2026.xlsx`
     (Downloads) solo tiene `Fecha de retiro` en 2026 (55/58 filas) — es el mismo tracking del
     año en curso ya cubierto, cero rastro de 2023-2024.
   - **MR — hallazgo parcial, pequeño, YA semi-conectado.** La pestaña `Inactivas` de
     `BD-Mujeres ROFÉ 2026.xlsx` (Downloads; mismo Sheet que ya lee `sync_sociodemograficos_mr.py`
     como fuente secundaria) tiene **33 filas usables** con `Año-Ingreso` real de 2022 (2) · 2023
     (~14) · 2024 (~5) · 2025 (2) y columnas `Motivos`/`Estado`(Retirada)/`Año-retiro`. **Ojo:**
     `Año-retiro` vale casi siempre 2025 o 2026 — parece ser cuándo se registró la baja en la
     hoja, NO el año de cohorte de retiro, así que no mapea directo al esquema
     periodo→cohorte de `importar_historico_q10.py` sin revisarlo caso a caso. Es MR-only (no
     hay equivalente JC) y cubre una fracción mínima de los ~353 retirados históricos totales
     (mayoría JC). **Si se quisiera usar:** decidir con el equipo si `Año-Ingreso` es la cohorte
     correcta para cada fila (vs. Q10), y hacer una carga manual única y pequeña — no amerita
     automatizar por el volumen. Queda como pendiente opcional, no ejecutado.
   - **Git history:** sin archivos de retiro histórico borrados alguna vez (el único match de
     `--diff-filter=D` fue un `git-rewrite` de limpieza de los archivos ACTUALES de retirados,
     no una fuente vieja perdida).
   - **Google Drive:** `search_files` con esos términos no devolvió ninguna hoja/archivo
     dedicado a retiros 2023/2024 fuera de lo ya conectado (solo menciones de "retirados" en
     reportes semanales/presentaciones existentes).
   - **Conclusión:** no hay una fuente recuperable que cierre el hueco completo de 2023-2025
     (sobre todo JC). Queda parqueado; el hallazgo MR de arriba es la única pista con datos
     reales, y es opcional/menor.
Se deja documentado aquí para no re-investigarlo desde cero cuando se retome.

### `sync_supabase_to_sheets.py` / `export_supabase_json.py` — continuidad analizada, ENCADENADOS (2026-07-21)
Ambos existían y funcionaban pero no estaban encadenados a ningún workflow n8n. Decisión previa
(2026-07-21, misma fecha) fue deprorizarlos; horas después Samuel pidió explícitamente
encadenarlos igual, así que se revirtió esa decisión:

- `sync_supabase_to_sheets.py`: espeja vistas públicas de Supabase de vuelta a Sheets
  (`H1Test`/`H2Test`/`H3Test`) para que el equipo consulte sin salir de Excel. Solo lectura de
  Supabase (anon key) + escritura en Sheets — no toca git.
- `export_supabase_json.py`: exporta TODAS las tablas/vistas públicas a `docs/datos/*.json`.

**⚠️ Consumidor no confirmado — vigente, no se resolvió con el encadenado.** El docstring del
script apunta al sitio `venerable-truffle-331f3c.netlify.app` (sitio de producción vigente, ver
corrección de URL arriba), pero el frontend real de ese repo consulta Supabase **client-side con
la anon key** (`lib/api.ts`), no lee `docs/datos/*.json`. Es decir: el script se encadenó porque
así se pidió, pero hoy nadie consume su salida. Reconsiderar si en el futuro el frontend migra a
JSON estático, o eliminar el paso si se confirma que nunca se va a usar.

**Encadenado al final de `q10-sync-supabase` (2026-07-21):** tras `¿Emoflow OK?` (rama true),
ahora sigue `Ejecutar export_supabase_json` → `Export JSON OK?` → `Ejecutar sync_supabase_to_sheets`
→ `Sheets OK?` → `OK`, cada IF con su propio `stopAndError` (mismo patrón del resto de este
workflow — sin Telegram aquí). 20 nodos totales, verificado con `GET /workflows/{id}` tras el PUT:
activo, sin referencias huérfanas.

**Decisión sobre el `git push` de `export_supabase_json.py`:** se le agregó `git_commit_y_push()`
(mismo patrón de `export_stats.py`/`export_aprobacion.py`, con flag `--sin-push` para pruebas) en
vez de dejarlo solo-disco. Motivo: los archivos de `docs/datos/*.json` **ya estaban trackeados en
git** (confirmado con `git ls-files` antes de tocar nada) — sin el push, cada corrida diaria dejaría
el working tree sucio para siempre (escrito en disco, nunca commiteado), degradando lo que ya hay
en el repo sin nunca actualizarlo. Con el push, al menos el repo se mantiene consistente con la
última corrida, aunque hoy no haya nada que lea esos archivos.

**Hallazgo colateral durante el encadenado — bug de producción pre-existente, corregido:** al
verificar el `GET /workflows/{id}` en vivo antes de tocar nada, el objeto `connections` completo
del workflow tenía **todas** las referencias a nodos IF/stopAndError rotas (claves con `¿`/tildes
corrompidas a `U+FFFD` que ya no coincidían con el `name` real de esos nodos, corrompido a su vez
a `?` ASCII plano) — arrastre de una edición de PowerShell anterior ese mismo día (la que quitó
`sync_emoflow_participacion`, ver sección de arriba). Confirmado con el historial de ejecuciones
(`GET /executions`): la corrida de las 9:45 de hoy corrió con nombres correctos (antes de esa
edición); cualquier corrida después de esa hora se habría detenido en silencio justo después de
`Ejecutar normalize_q10_data`, sin alcanzar ningún IF, ningún `stopAndError`, ni el nodo `OK` —
sin alertar, porque el error no es una excepción sino un grafo desconectado. Se reparó
remapeando cada clave/target de `connections` al `name` real de cada nodo (misma normalización en
todo el flujo, no solo en el tramo nuevo) antes de encadenar los pasos nuevos. Verificado: los 20
nodos y las 13 conexiones resuelven sin huérfanos. **Lección para la próxima edición por API:** no
basta con verificar que el PUT no lance excepción — hay que recorrer programáticamente
`connections` y confirmar que cada clave y cada `target.node` aparece en `nodes[].name` (lo que se
hizo aquí); un mismatch de encoding no lanza error en el PUT, solo desconecta el grafo en
silencio.

### Vivienda / estrato / estado civil / nivel de estudio para JC — sin fuente (pendiente próximo año)
Confirmado: **no existe ninguna fuente para estos 4 campos en Jóvenes creaTIvos** (a
diferencia de MR, que los tiene vía BD-Mujeres ROFÉ). No es un problema de sync — el dato
simplemente no se recolecta hoy para JC en ningún formulario/proceso.
**Plan (para cuando se prepare la estructura del próximo año, no ahora):** al armar el
onboarding/matrícula de la próxima cohorte, diseñar una captura automatizada de estos 4
campos desde el arranque (ej. Google Form de inscripción con estas preguntas → Sheet →
mismo patrón de sync que ya existe para MR) en vez de intentar recolectarlo retroactivo a
mitad de año. Anotado aquí para no llegar tarde otra vez a esta conversación.
**Diseño detallado (2026-07-21, sin implementar):** ver [[captura-sociodemografica-jc]] —
Form propuesto (sin pregunta de género, JC es mixto), pestaña Sheet destino con cruce por
cédula (mismo criterio de `actualizar_bd_mr.py`) y script `sync_sociodemograficos_jc_extra.py`
propuesto, reutilizando los mismos 4 enums de `sync_sociodemograficos_mr.py` sin crear
mapeos nuevos.

### Panel de riesgo (`tools/panel_riesgo_gui.py`) — plan de mejora completo
Ver [[panel-riesgo-mejora]] — plan de 3 fases para migrarlo de Sheets a Supabase y agregar
un tab de "Decisiones" con botones de consulta (estudiantes en riesgo, sin Emoflow,
asistencia baja, etc.). Decisión tomada: se mantiene como GUI de escritorio Tkinter (no se
construye un panel web nuevo), por privacidad (PII) y simplicidad.

### Contexto — próxima migración Netlify → DigitalOcean
Confirmado con Samuel: la convivencia GitHub Pages / Netlify es efectivamente una fase de
transición. El siguiente paso grande después de terminar esta migración a Supabase es mover
el frontend de `panel-datos-rofe` de Netlify a un droplet de DigitalOcean — Netlify tiene
límites (free tier) que se van a quedar cortos. No se ha planeado en detalle todavía; queda
como la "próxima gran decisión" de infraestructura, después de cerrar los puntos de esta
sección.

## Exploración de MongoDB (backend histórico de las apps ROFÉ) — investigación cerrada 2026-07-22
Samuel confirmó acceso a una base MongoDB Atlas que alimentaba un panel Power BI de un tercero
("le pagaron a alguien... millares de datos históricos, no se actualiza más de 4 veces al año").
Objetivo: ver qué trae de más antes de decidir si vale la pena gestionar el acceso formalmente
con el equipo. **Conclusión: prácticamente todo ya está en Supabase por otra vía — se cierra sin
cargar nada, salvo 4 registros puntuales.**

**Acceso:** usuario Atlas rol "Read Only" (solo lectura, verificado — nunca se escribió en Mongo),
`MONGO_URI` en `.env.local` (mismo patrón que el resto de credenciales del proyecto).

**Lo que hay realmente (7 bases, perfilado con `perfilar_mongo.py`):** no es un export estático —
son los backends reales (o sus copias) de varias apps:
- `mujeres-rofe-db.Users` (5.165 docs, 2022-2026) — backend de la plataforma Mujeres ROFÉ, con el
  mismo detalle sociodemográfico que ya trae MR (estrato, vivienda, estado civil, educación...).
- `jovenes-creativos.User`/`Applicant` — backend de postulantes/usuarios JC.
- `Asistencia-JC`, `emoflow-reports` — datasets recientes y chicos (9 y ~860 docs), no históricos.
- `test`, `test-jovenes`, `plataforma_dev` — copias de desarrollo, descartadas del alcance
  (mismo patrón de fechas que las bases reales, no autoritativas).

**Primer cruce (equivocado) — contra `participants`:** 97% de `mujeres-rofe-db.Users` 2023 y 88%
de 2024 no tenían cédula en `participants` (matriculados Q10). Parecía una brecha enorme — pero
`participants` es la tabla equivocada para comparar: este Mongo es *registro de usuarias de la
app*, no matrícula/avance en curso (mismo criterio de [[postulantes-mr-supabase]]: universo ≠
matriculadas).

**Segundo cruce (correcto) — contra `postulantes_mr`:** creada esa misma mañana
(2026-07-22, ver [[postulantes-mr-supabase]]) desde el Sheet BD-Mujeres ROFÉ, que incluye una
pestaña **"Plataforma MR"** — un export de una plataforma legada. Al cruzar por cédula:
**2.583/2.586 (99.9%) de 2023 y 1.004/1.006 (99.8%) de 2024 YA estaban en `postulantes_mr`.**
Conclusión: "Plataforma MR" es casi con certeza un export de este mismo Mongo (o su misma
fuente) — el Sheet ya se adelantó a cerrar esta brecha.

**Las 6 candidatas restantes, verificadas una por una** (cruce por cédula Y por email contra
`participants`, `postulantes_mr`, y las colecciones Mongo de `jovenes-creativos`):
- 1 es cuenta institucional/prueba (`soporte.it@tocaunavida.org`) — ya en `participants` y en
  `jovenes-creativos.Applicant`. Descartada.
- 1 es la misma persona con un typo de cédula (`111505265` en Mongo vs `1110505265`, correcta,
  ya en `postulantes_mr` fuente "General"). No es nueva.
- **4 confirmadas exclusivas de Mongo** (sin match en ningún sistema revisado) — exportadas a
  `Downloads/mongo_mr_nuevas_2023_2024_v2.xlsx` a pedido de Samuel, NO cargadas a Supabase (el
  volumen no justifica tocar producción; queda como entregable puntual).

**Decisión:** no se construye ningún sync ni import recurrente — la fuente casi no se actualiza y
ya está cubierta. Si en el futuro se necesita re-verificar algo puntual contra este Mongo, el
patrón de acceso (usuario Read Only + `MONGO_URI`) y los scripts de extracción/cruce quedan
disponibles como referencia, no como pipeline activo.

**Gotcha de diagnóstico (root cause corregida, no era lo que parecía):** al escribir
`cargar_mongo_mr_historico.py` desde cero (en vez de reutilizar el `Supa.get_todo()` ya existente
de otro script), se reintrodujo el **mismo bug de `offset += page` faltante** ya documentado ese
mismo día en [[convenciones#Paginación PostgREST: un `offset` que no avanza es un loop infinito silencioso]]
tras construir `postulantes_mr`. El síntoma llevó a sospechar (incorrectamente, ~20 min) un
conflicto entre `pymongo` y `urllib`/`truststore` en el mismo proceso — aislado con un test
standalone que sí funcionaba, y confirmado como loop infinito real solo al loggear el `offset` en
cada vuelta. **Lección reforzada:** antes de escribir un helper nuevo de paginación PostgREST,
revisar si ya existe uno para reutilizar/copiar tal cual, no reescribirlo de memoria.

**Separación extracción/carga (patrón nuevo, sí reutilizable):** aun así, separar "extraer de
Mongo → archivo local" (`extraer_mongo_mr_historico.py`) de "cargar archivo → Supabase"
(`cargar_mongo_mr_historico.py`) en dos procesos distintos resultó una buena práctica por
separado: dejó un artefacto (`tools/mongo_mr_historico_payload.json`, PII) revisable antes de
decidir qué cargar, útil cuando una cohorte necesita revisión humana antes de tocar producción
(como pidió Samuel para 2023, pendiente con su superior).

## Histórico de matrícula real MR en Q10 (2023/2024) — cerrado 2026-07-22

`courses` solo tenía cohortes `programa=mr` para 2025 (6 cursos) y 2026 (2 cursos) — a
diferencia de JC, que tiene las 4 (2023-2026). Antes de asumir que era un import faltante, se
releyó el sondeo ya cacheado (`tools/sondeo_periodos_20260710.json`, hecho el 2026-07-10 para
JC) para ver si Q10 siquiera conserva periodos MR de 2023/2024 — **sin necesidad de volver a
loguearse en Q10**, el JSON ya tenía la respuesta.

**Resultado: los periodos 1-24 completos de Q10 solo traen cursos con nombre JC** (Emprendimiento:
Idea de Negocio JC, Habilidades esenciales, Fundamentos Lógica, Desarrollo Web, Sistema de
Control de Versiones) **hasta el periodo 16 ("Único 2025")**, donde por primera vez aparecen
cursos MR mezclados (`De la idea a la acción...`). El periodo 23 ("Único MR-2026") es el primer
periodo dedicado 100% a MR. Ningún periodo de 2023/2024 tiene un solo curso MR.

**Conclusión: no falta ningún import — Q10 nunca trackeó cursos de Mujeres ROFÉ antes de 2025.**
La actividad MR de 2023/2024 vivió en otros sistemas (Mongo `mujeres-rofe-db.Users`, pestaña
"Plataforma MR" del Sheet) que son registro/postulación, no matrícula-con-avance — no hay una
fuente de "matrícula real 2023/2024" que traer a `enrollments`/`courses`. Se cierra la búsqueda;
el hueco en `courses` refleja la realidad, no un dato perdido.

## Auditoría Mongo JC (`jovenes-creativos.User`/`Applicant`) — hallazgo real, 2026-07-22

Mismo patrón que la investigación MR, pero con resultado MUY distinto: de **2.560 cédulas**
extraídas (User: 1.699 + Applicant: 861, precedencia User gana), **2.092 ya estaban** en
`participants` (programa=jc) o en el Sheet BD Seguimiento (universo de 828 cédulas auditado el
mismo día, ver [[panel-datos-etl]] sección de calidad JC) — pero **466 son exclusivas de Mongo
(18%)**. Se descartó que fueran typos de cédula de personas ya conocidas (vecindad numérica +
coincidencia de nombre/correo dentro del propio Mongo): **0 confirmados**.

Desglose de las 466 (tras excluir 3 cuentas `rol=ADMIN`, quedan 463 reales):
- **378 `rol=EGRESADO`, casi todas con `creationDate` de 2023** — cuentas de alumnos de
  cohortes antiguas cuyo registro de app nunca se cruzó contra el histórico de Q10.
- **85 `rol=ACTUAL`, todas de la colección `Applicant` (2026)** — postulantes recientes que
  aún no aparecen ni en `participants` ni en el Sheet (rezago normal de inscripción, o
  candidatos que no llegaron a matricularse).

**Esto corrige una conclusión de la misma sesión** ("JC probablemente no tiene el embudo de
postulación que sí tiene MR", basada solo en que BD Seguimiento es del tamaño de la cohorte
matriculada). El embudo sí existe — solo que vive en Mongo, no en un Sheet gigante como en MR.

**Decisión tomada (2026-07-22, mismo día): SÍ se creó `postulantes_jc`** — Samuel confirmó
que el hallazgo era real e importante ("Mongo tenía datos que definitivamente nos harían
falta"), pidiendo una columna explícita de trazabilidad de origen. Migración
`docs/migrations/005_postulantes_jc.sql` (RLS + `REVOKE ALL` de anon/authenticated en el mismo
statement, verificado 401 con anon key). A diferencia de `postulantes_mr`, aquí se cargó **todo
el universo Mongo** (2.556 cédulas, no solo los exclusivos) — `participant_id` queda NULL para
quien no matriculó (2.092 con match, 464 exclusivos) y poblado para quien sí, mismo patrón que
`postulantes_mr`. Columna `fuente` (`mongo_user`/`mongo_applicant`) deja explícito que el
origen es Mongo, no un Sheet — el pedido puntual de Samuel.

Scripts: `extraer_mongo_jc_historico.py` (Mongo → payload, separado de la carga por el mismo
motivo que MR) + `cargar_mongo_jc_historico.py` (payload → `postulantes_jc`, upsert idempotente
por cédula). Entregable de revisión previo a la carga: `Downloads/jc_mongo_exclusivos.xlsx`
(463 casos sin match, generado antes de decidir cargar).

**A diferencia de MR:** no hubo gate de `--cohortes` explícito ni revisión de un superior antes
de cargar — Samuel autorizó la carga completa directamente en el mismo mensaje del hallazgo.

**Pruebas de coherencia post-carga (2026-07-22, mismo día, a pedido de Samuel):** 6 chequeos de
solo lectura contra Mongo y `postulantes_jc` —
1. Conteo total estable (Mongo no cambió desde la extracción) ✅
2. Duplicados de `documentNumber` DENTRO de cada colección: 0 ✅
3. Conflictos `User` vs `Applicant` (misma cédula, nombre distinto): **0 cédulas comparten
   ambas colecciones** — la precedencia "User gana" nunca tuvo que decidir nada en la práctica.
4. Formato de `documentNumber`: 0 vacíos, 0 muy cortos; **4 "muy largos" (>11 dígitos)**.
5. Cruce inverso — participantes JC matriculados sin ningún rastro en Mongo: 224/2.316 (9.7%,
   esperable — no todo el que matricula en Q10 pasa por la app).
6. Spot-check de 15 filas al azar de `postulantes_jc` contra Mongo en vivo: 15/15 coinciden.

**Bug real encontrado por el chequeo 4 — y corregido:** de los 4 `documentNumber` "muy largos",
1 era la cuenta admin/institucional (`soporte@tocaunavida.org`, `rol=ADMIN`, ya excluida
correctamente por el filtro de rol pese al bug) y **3 eran personas reales con la cédula
corrompida por el mismo gotcha float→string ya documentado en convenciones.md** (BSON guarda
`documentNumber` como `double` cuando el valor es entero — ej. `11086478896.0` — y el
`norm_id()` del extractor JC no tenía el guard `if isinstance(valor, float) and
valor.is_integer(): valor = int(valor)` que sí tienen los demás `norm_id` del proyecto,
agregando un cero espurio de la parte decimal). Corregido en
`extraer_mongo_jc_historico.py`, las 3 filas corrompidas borradas de `postulantes_jc` y
re-cargadas con la cédula correcta — **2 de las 3 resultaron SÍ estar matriculadas en Q10**
(`con_match_participant` subió de 2.092 a 2.094 tras el fix). Cuenta admin agregada a
`tools/exclusiones_prueba.json` por si algún script futuro procesa esta colección distinto.

## Auditoría de estructura + análisis Emoflow (2026-07-23) — diagnóstico de funcionalidad

Auditoría completa de esquema y calidad (todas las queries en [[supabase-estructura]], el
diccionario de datos nuevo). Diagnóstico corto:

- **Sirve y está sano:** núcleo Q10 (`participants`/`courses`/`enrollments`/agregados — 0
  huérfanas, 0 duplicados, frescura <1 día), Emoflow serie real (`emoflow_ingresos_diario`,
  `emoflow_actividad_semanal`), universos `postulantes_*`, asistencia, correos.
- **Con observaciones:** `emoflow_ingresos` (1 fila huérfana de la era pre-API; sin cédula →
  match 91.8% por email), `historial_emoflow(_ciudad)` (snapshots con huecos — usar las series
  reales en su lugar), `enrollments.estado` (no es resultado académico confiable — usar
  `porcentaje_avance`).
- **Roto/redundante:** `emoflow_participacion_semanal` (🔴 fuente vieja de monitorias, ya sin
  pipeline — deprecar). Discrepancia de 0,7% entre acumulado-persona y serie diaria por
  **parámetros de descarga distintos** entre los 2 scripts Emoflow (uno filtra
  `empresa=Fundación ROFÉ`, el otro scope=all) — unificar.
- **El hueco que importa:** el retiro individual NO existe en Supabase (solo el agregado
  69/832 en `cohorte_ingresos`) — es la variable de resultado más valiosa y hoy imposible de
  cruzar con Emoflow. Plan en [[supabase-estructura]] (punto 2).

**Análisis uso Emoflow ↔ resultados (JC 2026, n=777):** asociación positiva, significativa y
robusta a controles (Spearman ρ=0.337; OR ajustado 2.36 IC95 [1.51-3.69] por log-uso;
sensibilidad con umbral 100: OR 1.90 [1.56-2.31]). NO establece causalidad (uso y avance son
acumulados al mismo corte; el uso puede ser marcador de compromiso). Detalle y por-ciudad en
[[supabase-estructura#Análisis Emoflow 2026-07-23]]; individual solo en `tools/`.

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
- [x] ~~Renombrar sitio Netlify~~ — superado: el sitio se migró de repo (2026-07-16, ver
      corrección de URL arriba), no solo se renombró. URL vigente: `venerable-truffle-331f3c`.
- [ ] Fase 2: materialized views (retirados con definición canónica) + decidir campo `programa`
- [ ] Fase 3: Next.js + Netlify
- [ ] Fase 4: test de cuadre contra `docs/dashboard|aprobacion|retirados/data.json` antes de reemplazar nada

## Corrección de documentación desactualizada — nodos y cadencia reales (2026-07-24)

La cadencia y el conteo de nodos de `q10-sync-supabase` (`uSizw3dNzpb6n53H`) documentados
arriba (sección 2026-07-21: "20 nodos totales", "diario 9:45") quedaron desactualizados por
cambios posteriores no reflejados aquí — corregido en el Track C de la Ola 1
(plan-produccion-datos-2026-07-24.md), verificado con `GET /workflows/uSizw3dNzpb6n53H` en
vivo (ID de trigger tomado de `ola1_prompts.md`, ver Ola 1 · Anexo A):

- **Nodos reales: 23** (no 20). El delta son los nodos agregados tras el 2026-07-21
  (`Ejecutar export_supabase_json`/`Export JSON OK?`/`Ejecutar sync_supabase_to_sheets`/
  `Sheets OK?` ya estaban contados; el resto del delta viene de ajustes posteriores al mismo
  workflow — no re-auditados línea por línea en este track, solo el conteo total).
- **Cadencia real: `30 17,19,21,23,1,3,5,7 * * *`** (cada 2 h, ventana 17:30–07:30 COT) — NO
  "diario 9:45" como quedó escrito en la sección de 2026-07-21 (esa fue la cadencia ORIGINAL
  antes de pasar a la ventana nocturna de dos velocidades; el nombre del trigger en n8n seguía
  diciendo "Schedule Diario 9:45" pese a que la expresión cron ya no correspondía — renombrado
  a "Schedule 2h (17:30–07:30)" en el Track A de la misma ola).
- Las referencias a "9:45" en las secciones fechadas ANTES del 2026-07-21 arriba (Fase 1b,
  cohorte canónica, etc.) se dejan tal cual — son verdad histórica de cuando se escribieron,
  no se reescribe el pasado. Esta sección es la corrección vigente para cualquier lectura
  posterior del estado actual.

**Otros cierres de este track (2026-07-24):**
- `sync_supabase_to_sheets.py` / `export_supabase_json.py` — el gotcha de permisos de la SA
  (403 al autocrear pestaña) se cerró de verdad hoy compartiendo el Sheet AUTO dedicado como
  Editor; ver detalle en [[mapa-codigo]] y [[supabase-estructura]]. La sección de 2026-07-21
  arriba ("ENCADENADOS") describía el encadenado correcto pero no conocía este bug de permisos
  (apareció después).
- `export_supabase_json.py` recortado de 23 a 16 tablas/vistas configuradas (7 fuera: 4 PII con
  401 vía anon, 1 siempre-0-filas por RLS, 1 vista inexistente, 1 deprecada) + `estado=error`
  real si algo falla + manifest dinámico. Detalle completo en [[mapa-codigo]].
- `calcular_asistencia_promedio.py`: ya no imprime `[OK]` si `errores > 0` — retorna 1.
- `sync_emoflow_api.py`: detecta y (opcionalmente, `--purgar-huerfanos`) borra filas huérfanas
  de `emoflow_ingresos`; la huérfana conocida (`fecha_corte=2026-07-21`) se purgó a mano.
- `sync_emoflow.py` movido a `_obsoletos/`; migraciones `006`/`007` renombradas de `_PROPUESTA`
  a `_APLICADA(_PARCIAL)` (su contenido ya decía "aplicada", el nombre mentía); migración `012`
  (DROP `emoflow_participacion_semanal`) escrita pero **NO aplicada** — pendiente 🙋 OK de
  Samuel. Ver `docs/migrations/README.md` (nuevo).

**Cierre verificado con corridas reales (2026-07-24, no solo `py_compile`):**
- `export_supabase_json.py` corrido a mano completo, CON push real, antes de la cadena
  nocturna: `RESUMEN: tablas=16 ok=16 fallidas=0 filas_cero=ninguna registros=991 estado=exito`
  — commit `9ae1f4e`, confirmado en `git log`. El diseño de "0 filas = error" se refinó a pedido
  de Samuel tras la revisión: solo `cohorte_stats`/`aprobacion_cursos`/`historial_cursos`
  (constante `NUNCA_VACIAS`) abortan la corrida si dan 0 filas; el resto de la lista solo genera
  advertencia (`filas_cero=[...]` en el RESUMEN y en `manifest.json`) sin tumbar las 8 corridas
  nocturnas por un agregado que se vacíe de forma legítima.
- `test_integridad_supabase.py` corrido completo al cierre (cambio real en Supabase: la
  purga de la fila huérfana de `emoflow_ingresos` vía service_role): **`RESUMEN: total=47
  pass=47 fail=0 estado=exito`** — incluye las 3 pruebas nuevas de `retiros` (Track B) y
  confirma sana la purga de Track C.
