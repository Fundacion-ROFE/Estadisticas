# Supabase panel-datos-rofe — Estructura y diccionario de datos

**Estado:** Auditoría completa + suite de blindaje 2026-07-23 (35/36 tests PASS; 1 hallazgo de
datos corregido en pipeline, limpieza en migración propuesta).
**Última actualización:** 2026-07-23 (QA/seguridad)
**Procesos relacionados:** [[panel-datos-etl]] · [[postulantes-mr-supabase]] · [[mapa-codigo]]

> Proyecto `kbxptoowtnteflhrfwid` (us-east-1). 24 tablas en `public` + ~20 vistas de agregados.
> Toda afirmación de este documento salió de queries ejecutadas el 2026-07-22/23 (auditoría de
> solidez + auditoría Emoflow); no de suposiciones.

## Convenciones de estado

- 🟢 **confiable** — verificada (integridad, unicidad, privacidad) y con pipeline activo.
- 🟡 **con observaciones** — usable, pero con limitaciones documentadas abajo.
- 🔴 **no usar** — obsoleta o reemplazada; candidata a deprecar.

## Identidad y llaves de cruce (verificadas con queries)

| Cruce | Llave | Tasa real de match |
|---|---|---|
| `emoflow_ingresos` → `participants` | email normalizado (lower/trim) | **91.8%** (759/827); estable — re-derivada en vivo da idéntico |
| `postulantes_mr` → `participants` | cédula (= `q10_id`) | 10.5% (557/5.310) — esperado: embudo ≫ matrícula |
| `postulantes_jc` → `participants` | cédula (= `q10_id`) | 81.9% (2.094/2.556) |
| `enrollments` → `participants`/`courses` | UUID FK | 100% (0 huérfanas) |
| Sheet BD Seguimiento JC → `participants` | cédula | 93.4% (773/828) |

Reglas de oro: **cédula normalizada (solo dígitos)** es la única llave inter-fuentes confiable;
el correo solo se usa donde no hay cédula (Emoflow no la expone). `participants` = SOLO
matriculados Q10 (ver [[convenciones]]); los universos amplios viven en `postulantes_*`.

---

## Dominio: núcleo académico (Q10)

### `participants` 🟢 — 2.919 filas
Fuente: `cargar_supabase.py` (diario n8n 9:45) + enriquecimiento `sync_sociodemograficos*.py`
(semanal lunes 6:00) + `importar_historico_q10.py` (histórico, una vez).
PK `id` uuid · UNIQUE `q10_id` (cédula) · RLS + REVOKE anon (endurecido 2026-07-23).

| Columna | Tipo | Origen / nota |
|---|---|---|
| `q10_id` | varchar UNIQUE | cédula normalizada — llave inter-fuentes |
| `nombre`, `email` | varchar | Q10; email verificado sin duplicados normalizados |
| `genero`, `edad`, `ciudad`, `grupo_ciudad`, `fecha_nacimiento` | — | BD monitorias (JC) / BD-Mujeres ROFÉ (MR); cobertura JC-2026 activos: 98.7% |
| `estrato`, `estado_civil`, `nivel_estudio`, `tipo_vivienda` | — | **solo MR** (JC sin fuente — 0% cobertura, no usar como control en análisis JC) |
| `tiene_emprendimiento`, `nombre_emprendimiento`, `situacion_emprendimiento` | — | encuesta diagnóstico (JC) / BD MR |
| `is_public` | bool | **siempre false hoy (0/2.919)** — las policies públicas de `enrollments`/`participant_metrics` dependen de él vía `es_publico()` |

### `courses` 🟢 — 39 filas · `enrollments` 🟢 — 18.196 filas
UNIQUE (`nombre`,`cohorte`) · UNIQUE (`participant_id`,`course_id`) · avance 0-100 con CHECK.
Verificado 2026-07-23: 0 huérfanas, 0 duplicados, 0 fuera de rango.
🟡 Obs: `enrollments.estado` (completado/en_progreso/inscrito) **no es variable de resultado
confiable** — 5.131/5.439 "completado" en JC-2026 no refleja aprobación real; usar
`porcentaje_avance`. **El universo de enrollments JC-2026 son los 777 activos** — los 69
retirados de la cohorte NO están como filas individuales (solo el agregado en
`cohorte_ingresos`); el retiro individual vive fuera de Supabase (Sheet Retirados).

### `participant_metrics` 🟢 · `cohorte_stats` 🟢 · `cohorte_ingresos` 🟢 · `aprobacion_cursos` 🟢
Agregados recomputados a diario (`recompute_aggregates()`); frescura verificada (<1 día).
`cohorte_ingresos` = cifras canónicas (JC 2026: 832 ingresados / 765 activos / 69 retirados).

### `participants_snapshots` 🟢 — 8 filas
Respaldo diario pre-upsert (rollback). RLS + REVOKE anon (endurecido 2026-07-23).

---

## Dominio: Emoflow

### `emoflow_ingresos` 🟢 — 827 filas (individuo, acumulado)
Fuente: `sync_emoflow_api.py` (diario n8n 9:45; API directa, filtro `empresa=Fundación ROFÉ`).
UNIQUE `email` · granularidad: 1 fila por usuario, `ingresos` = check-ins acumulados,
`ultimo_ingreso` = fecha del último. RLS + REVOKE anon.
🟡 Obs: (1) **1 fila huérfana** con `fecha_corte=2026-07-21` que el sync ya no ve (el upsert
no borra — si un usuario desaparece del CSV su fila queda congelada). (2) Sin cédula — cruce
solo por email (91.8%). (3) Sin dimensión temporal por persona (solo acumulado + último día).

### `emoflow_ingresos_diario` 🟢 — 1.184 filas (ciudad × día)
Fuente: `extract_emoflow_ingresos_diario.py` (diario n8n 21:30; **scope=all sin filtro de
empresa** — ver discrepancia abajo). PK (`fecha`,`grupo_ciudad`). Serie REAL desde timestamps:
2026-03-18 → hoy, 122 días con datos de 127 calendario (los 5 faltantes son 21-25 marzo,
consecutivos al arranque — cero actividad real, no hueco de pipeline). Fila NACIONAL incluye
eventos con ciudad no mapeada (NACIONAL 27.594 vs suma ciudades 27.346 = 248 eventos sin mapeo).

### `emoflow_actividad_semanal` 🟢 — 181 filas (ciudad × semana ISO)
Misma fuente/corrida que la diaria. PK (`semana_inicio`,`grupo_ciudad`). `roster` = alguna vez
activo (844 nacional); `pct_activos` = activos de la semana / roster.

### `historial_emoflow` 🟡 — 20 filas · `historial_emoflow_ciudad` 🟡 — 45 filas
Snapshots diarios de las vistas `v_emoflow_*` (los escribe `sync_emoflow_api.py`). Sin PK
formal (solo UNIQUE). 🟡 Obs: para series de tiempo **preferir siempre
`emoflow_ingresos_diario`/`actividad_semanal`** (derivadas de timestamps reales); estos
snapshots solo capturan el estado del acumulado en el día que corrieron (historial_emoflow
arranca 2026-04-07 con huecos; _ciudad solo desde 2026-07-15).

### `emoflow_participacion_semanal` 🔴 — 171 filas
Fuente vieja: bloque EMOFLOW de la hoja de monitorias (script ya en `_obsoletos/`, nodo n8n
eliminado 2026-07-21). Reemplazada por `emoflow_actividad_semanal` (misma pregunta, fuente
real). **No usar para análisis nuevos; candidata a archivar/eliminar.**

### Discrepancias cuantificadas entre tablas Emoflow (2026-07-23)

| Comparación | Valores | Explicación |
|---|---|---|
| Σ`ingresos` persona vs serie diaria NACIONAL | 27.408 vs 27.594 (Δ186, 0,7%) | Los 2 scripts bajan el CSV con **parámetros distintos**: `sync_emoflow_api` filtra `empresa=Fundación ROFÉ` y descarta emails inválidos; el diario usa scope=all sin filtro. + corridas en días distintos (9:45 vs 21:30) |
| usuarios 827 vs roster nacional 844 (Δ17) | mismo motivo | el roster semanal incluye emails fuera del filtro de empresa/validez |
| NACIONAL vs Σ9 ciudades (Δ248 eventos) | por diseño | eventos con `Area` no mapeada solo cuentan en NACIONAL |

Ninguna discrepancia indica doble conteo: el pipeline deprecado (`sync_emoflow.py`, Sheet)
escribía en la MISMA tabla por email con upsert de reemplazo total — al pasar al API sync
(2026-07-21 en n8n) el acumulado se recalcula completo en cada corrida, sin solapamiento.
Único residuo: la fila huérfana de `fecha_corte=2026-07-21`.

---

## Dominio: universos de postulación (paralelo a participants)

### `postulantes_mr` 🟢 — 5.310 filas
Fuente: `sync_postulantes_mr.py` (manual; Fase 4 n8n pendiente). UNIQUE cédula · RLS+REVOKE.
5 pestañas del Sheet BD-Mujeres ROFÉ + trazabilidad `fuente_pestana`. 36 duplicados fusionados,
16 pares discordantes pendientes de revisión humana, 5 cuentas institucionales purgadas
(2026-07-22). `participant_id` NULL = no matriculó (mayoría).

### `postulantes_jc` 🟢 — 2.556 filas
Fuente: `extraer_mongo_jc_historico.py` + `cargar_mongo_jc_historico.py` (manual, una vez).
UNIQUE cédula · RLS+REVOKE · `fuente` = mongo_user/mongo_applicant. 464 exclusivas (sin
matrícula Q10). Fuente casi estática (el Mongo se actualiza ~4 veces/año).

---

## Dominio: asistencia y correos

| Tabla | Estado | Nota |
|---|---|---|
| `asistencia_zoom` (509) | 🟢 | webhook Zoom → n8n diario 00:00 |
| `asistencia_promedio` (490) | 🟡 | PII; policy permisiva revocada tras incidente 2026-07-14; consumida por panel de riesgo local |
| `email_optout` (0) / `email_bounces` (392) | 🟢 | pipeline correos MR; REVOKE anon endurecido 2026-07-23 |
| `campanas_enviadas` (14) / `alertas_datos` (2) | 🟢 | logs agregados sin PII |
| `historial_cursos` (138) / `historial_cursos_ciudad` (378) | 🟢 | series de agregados del sync diario |

---

## Seguridad (estado 2026-07-23)

- Todas las tablas PII con RLS + **REVOKE explícito** de anon/authenticated (barrido completo
  de anon key sobre las 24 tablas: PII → 401, agregados → 200). El endurecimiento del
  2026-07-23 cerró 5 tablas que solo tenían "RLS sin policy" (`participants`,
  `emoflow_ingresos`, `email_optout`, `email_bounces`, `participants_snapshots`).
- Gotcha documentado: revocar GRANT de una tabla rompe policies de OTRAS tablas que le hacen
  subquery — resuelto con `es_publico()` SECURITY DEFINER (ver [[convenciones]]).
- El panel público solo consume vistas `v_*` de agregados; PII individual solo por
  `service_role` → `tools/`.

## Plan priorizado — "única fuente de verdad"

1. **(hecho 2026-07-23)** REVOKE anon en las 5 tablas PII sin red de seguridad.
2. **Retiro individual**: única variable de resultado NO disponible en Supabase (solo agregado
   69). Traer la pestaña Retirados del Sheet (cédula + fecha + motivo) a una tabla
   `retiros` con FK a participants — habilitaría el análisis retención↔Emoflow que hoy es
   imposible. *Prioridad alta para análisis.*
3. **Deprecar `emoflow_participacion_semanal`** (🔴): sin consumidores nuevos; archivar.
4. **Purgar la fila huérfana** de `emoflow_ingresos` (`fecha_corte` viejo) o hacer que
   `sync_emoflow_api.py` marque/eliminé filas que ya no vienen en el CSV.
5. **Unificar el parámetro de descarga del CSV Emoflow** entre los 2 scripts (`empresa=`
   filtrado vs scope=all) para que persona-acumulado y serie diaria cuadren exacto.
6. **Fase 4 de postulantes_mr** (n8n semanal) + resolver los 16 pares discordantes.
7. PK formal en `historial_emoflow(_ciudad)` (hoy solo UNIQUE) — cosmético, baja prioridad.

## Blindaje QA/Seguridad 2026-07-23 — triage de hallazgos

Suite reproducible: `scripts/panel-datos/test_integridad_supabase.py` (36 tests, un comando,
tolerancias explícitas; `--rapido` para el chequeo diario). Estado tras aplicar la migración
de seguridad: **36/36 PASS**.

**`006_seguridad_hardening.sql` — APLICADA PARCIALMENTE** (Samuel aprobó completo; 2 de 8
bloques se descartaron al encontrarles dependencias reales antes de ejecutar — mismo hábito
de verificación que ya evitó romper `enrollments` horas antes):
- ✅ Aplicados: `es_publico()` movida a schema no expuesto (rompe nada, RPC directo → 404),
  policy `asistencia_zoom` UPDATE reformada, 6 `COMMENT` de intencionalidad en tablas PII,
  `v_demografia_grupo` con supresión k-anonimato (n<5 → NULL, corrigiendo además que la
  propuesta original había omitido el filtro `participa_en(id,'jc')` de la vista real),
  limpieza de 3 `edad=0` y 1 fila huérfana de `emoflow_ingresos`.
- ❌ Descartados permanentemente: revocar `participa_en()` a anon (rompía 4 vistas públicas
  que la usan — `v_demografia_grupo`, `v_edad_distribucion`, `v_emprendimiento_situacion`,
  `v_emprendimiento_vs_cursos`); borrar `v_puntaje_estudiante` (tiene consumidor real,
  `reporte_puntaje.py`, ya estaba correctamente bloqueada para anon).

`007_retiros_PROPUESTA.sql` sigue sin aplicar — pendiente de decisión sobre el diseño.

### `en_seguimiento_jc` — alerta de retiro pendiente de confirmar (2026-07-23)

Columnas nuevas en `participants`: `en_seguimiento_jc` (boolean) + `fecha_verificacion_seguimiento`
(date). Origen del pedido: el equipo borra primero de la pestaña "Seguimiento" del Sheet BD
Seguimiento de Monitorias cuando alguien se retira, y solo **meses después** lo refleja en
Q10 — así que Q10 queda desactualizado como señal de "¿sigue activo hoy?".

**No es un booleano de retiro confirmado — es una alerta operativa.** `false` significa "no
aparece en Seguimiento pero Q10 todavía lo marca activo": dos desenlaces posibles, (a) Q10
eventualmente confirma el retiro (en ese punto ya lo captura `enrollments.estado`), o (b)
reaparece en el Sheet (falsa alarma). **Mientras está en duda: NO usar como variable de
resultado en análisis estadístico** (ej. uso Emoflow ↔ retención) — solo como aviso para que
el equipo verifique. Complementa, no reemplaza, la tabla `retiros` propuesta (`007`): esta
columna da un sí/no de hoy, `retiros` daría fechas para análisis histórico.

Alcance: **solo JC, cohorte del año en curso** (2026) — decisión explícita de Samuel, MR queda
fuera ("tiene problemas de gestión respecto a eso", la misma disciplina de borrado no es
confiable ahí). Escopar a la cohorte actual fue un ajuste necesario: la primera corrida sin
ese filtro marcó 1.557/2.316 participantes JC históricos (2023-2025) como "alerta", que en
realidad eran egresados normales nunca trackeados en ese Sheet — con el filtro correcto
(cohorte 2026, n=777) salieron **18 alertas reales**, todas con avance Q10 sustancial
(46%-82%), consistente con la hipótesis de retiro real aún no reflejado.

Calculado por `sync_sociodemograficos.py` (mismo Service Account ya trazado, sin credencial
nueva), en un segundo paso separado del resto del script (los demás campos solo enriquecen a
quien el Sheet trae; esta bandera se calcula para TODOS los de la cohorte, estén o no en el
Sheet — es la ausencia lo que importa). Reporte con las cédulas en alerta:
`tools/sociodemograficos_report_<fecha>.json` (PII).

**Decisión de Samuel (2026-07-23, mismo día): estas 18 personas se EXCLUYEN de "estudiante
actual" en TODOS los sistemas** (no solo se marcan visualmente) — dashboard público Netlify,
`panel_riesgo_gui.py`, `reporte_puntaje.py`. Implementado sin tocar los números canónicos de
Q10 (`enrollments.estado`, `cohorte_ingresos` siguen intactos — esos son la fuente oficial):
el filtro se aplicó en la CAPA DE VISUALIZACIÓN/ANÁLISIS únicamente —
- **11 vistas de Supabase** reescritas con `en_seguimiento_jc IS DISTINCT FROM false`
  (`v_demografia_grupo`, `v_edad_distribucion`, `v_emprendimiento_situacion`,
  `v_emprendimiento_vs_cursos`, `v_cohorte_estudiantes`, `v_cohorte_estudiantes_distribucion`,
  `v_curso_completion`, `v_curso_completion_por_ciudad`, `v_programa_stats`,
  `v_programa_stats_por_ciudad`, `v_puntaje_estudiante`) — como el dashboard público de
  Netlify consume estas vistas directamente, quedó cubierto sin tocar ese repo aparte.
  Verificado: JC 2026 pasó de 777 → 759 participantes en todas las vistas (777−18); MR sin
  cambios (343, columna siempre NULL ahí).
- **`panel_riesgo_gui.py`** (herramienta local): la función que arma `por_email_jc` ahora
  excluye matrículas con `en_seguimiento_jc=false` antes de construir el diccionario que
  alimenta toda la GUI.
- `reporte_puntaje.py` no necesitó cambios de código — hereda el filtro automáticamente al
  leer `v_puntaje_estudiante`.
- `IS DISTINCT FROM false` (no `= true`) es a propósito: dejar pasar `NULL` (histórico
  2023-2025, y MR entero) sin afectarlo — solo excluye el `false` explícito de la cohorte
  actual.

**Corrección importante encontrada el mismo día (2026-07-23, tarde):** al investigar por qué
un gráfico por curso del dashboard (Netlify local) no cuadraba con los paneles ya ajustados,
se descubrió que **17 de los 18 `en_seguimiento_jc=false` YA estaban confirmados como
retirados en el pipeline oficial** (`export_aprobacion.py` → `tools/cohorte_2026.json`, vía un
reporte de Q10 DISTINTO al que puebla `enrollments.estado` — "Detallado Estudiantes
Matriculados" + "Reporte Estudiantes cancelados"). La premisa inicial ("Q10 tarda meses en
reflejar el retiro") es cierta para `enrollments.estado` (que en la práctica nunca marca
`abandonado`), pero **no para este otro reporte**, que sí lo trackea bien — solo que
**Supabase tenía la foto vieja de las 9:45**, mientras `docs/aprobacion/data.json` ya se había
regenerado más tarde (12:04) con la cifra correcta (74 retirados, 760 habilitados — 760
coincide EXACTO con Seguimiento). Solo 1 de los 18 (`63851795`) es un caso genuinamente
exclusivo de la detección por Sheet, sin confirmar aún en ningún reporte de Q10.
**Resuelto corriendo `sync_aprobacion_supabase.py`** (ya generado, solo faltaba subirlo) —
`cohorte_ingresos`/`aprobacion_cursos` ahora reflejan 760/74. Las 3 piezas construidas hoy
(`en_seguimiento_jc`, `v_retiro_probable_jc`, `v_aprobacion_cursos_jc_ajustado`) se
**mantienen como red de seguridad** (decisión de Samuel) — detectan casos entre corridas del
pipeline oficial, como el único caso real que sigue sin confirmar.

**Barrido de coherencia total del panel (mismo día, tras el hallazgo anterior):** se
inventariaron las 24 fuentes exactas que consume el frontend (`lib/api.ts` de
`~/panel-datos`) y se encontraron 2 más sin el ajuste de `en_seguimiento_jc`:
- **`v_emprendimiento_por_ciudad`** — a diferencia de sus vistas hermanas
  (`v_emprendimiento_situacion`, `v_emprendimiento_vs_cursos`), no tenía NI el filtro
  `participa_en(id,'jc')` ni la exclusión de la alerta. Corregida para alinearla.
- **`cohorte_stats`** (tabla, no vista — poblada por `recompute_aggregates()`, la función
  `SECURITY DEFINER` que corre tras cada sync) — mostraba 777 para JC 2026. Función editada
  para excluir `en_seguimiento_jc=false` solo en el cómputo de `total_participantes`/
  `con_emprendimiento`/`edad_promedio` (histórico 2023-2025 y MR intactos vía
  `IS DISTINCT FROM false`), y re-ejecutada — ahora 759.

Las demás fuentes del frontend (`historial_cursos*`, `historial_emoflow*` — snapshots
diarios, correctos tal cual quedaron en su momento, no se re-escriben retroactivamente;
`v_emoflow_*`, `emoflow_ingresos_diario`, `emoflow_actividad_semanal` — población propia de
Emoflow, no de "estudiante activo"; `v_mr_demografia` — MR, fuera de alcance) no necesitaron
cambios. Suite completa tras estos 2 fixes: 38/38 PASS.

### `retiros` — esquema aplicado (2026-07-23)

`docs/migrations/007_retiros_PROPUESTA.sql` aplicada (solo esquema: tabla + índices + RLS +
`REVOKE`, verificado 401 con anon key). Tabla **vacía** — el script de sync
(`sync_retiros.py`, fuentes: Sheet Retirados JC + S Retirados monitorias + Inactivas MR) sigue
sin escribirse, es el siguiente paso para cerrar de verdad el gap #1 (retiro individual con
fecha, necesario para el análisis uso-Emoflow ↔ retención). Agregada a la lista de tablas PII
verificadas por `test_integridad_supabase.py` (ahora 39 tests).

**Complemento (mismo día): `v_retiro_probable_jc`.** Excluir a los 18 de "activos" sin
mostrarlos en ningún otro lado habría vuelto a romper el cuadre de cifras (mismo problema que
ya se corrigió en la auditoría del día anterior). Se decidió con Samuel: **categoría separada,
NO mezclada con `cohorte_ingresos.retirados`** (que sigue siendo 100% Q10-oficial e intacto).
Vista nueva `v_retiro_probable_jc` (agregado, sin PII, `GRANT` a anon igual que las demás
vistas públicas): `retiro_probable_total` / `retiro_probable_aprobado` (avance>80 antes de
desaparecer del Sheet, mismo umbral que `aprobacion_cursos`) / `retiro_probable_no_aprobado` /
`avance_promedio`. Cohorte 2026: **18 total, 7 ya habían aprobado, 11 no** (avance promedio
grupal 70,2%). Ninguno de los 18 tiene `enrollments.estado='abandonado'` en Q10 — confirma que
Q10 genuinamente no sabe todavía que se fueron. Dos tests permanentes agregados a
`test_integridad_supabase.py` (cuadre exacto contra `en_seguimiento_jc=false`, y
aprobado+no_aprobado=total) — ya no son 36, son 38/38 PASS.

**Falso positivo confirmado dentro de los 18 (2026-07-23): Angeles Isabella Navas Rodriguez,
`q10_id`/celular `63851795`.** Samuel pegó la lista cruda de 760 emails de Seguimiento para
verificar el panel; al cruzarla contra `en_seguimiento_jc` aparecieron 5 discrepancias por
email. 4 se resolvieron solas (2 personas con dos correos distintos — uno de Q10, otro de su
postulación original — verificadas por cédula directamente contra la pestaña Seguimiento en
vivo: SÍ están presentes). La 5ª (Angeles) sí es un caso real de investigar: su fila en
Seguimiento (#668) tiene "ID"=`293` (no matchea con nada de Supabase) y "Celular"=`63851795`
(el mismo valor que trae `participants.q10_id` y `postulantes_jc.cedula`).

**Diagnóstico corregido tras comparar contra otros estudiantes PAN del mismo Sheet:** en TODO
el grupo Panamá, "Celular"/"Celular Alterno" siguen sin excepción el patrón panameño (8
dígitos, empieza en 6); "ID" varía en longitud (6-9 dígitos) pero nunca tiene esa forma.
`63851795` encaja exacto con el patrón de celular — **es su teléfono, no su documento**. Su
"ID" real en el Sheet es `293`, anormalmente corto frente al resto (nadie más tiene 3
dígitos). Conclusión: **Q10 registró su número de teléfono como si fuera su documento desde
el origen** (de ahí que `participants.q10_id` y `postulantes_jc.cedula` coincidan con el
celular — no son 3 fuentes independientes confirmando un documento, son 3 sistemas que
heredan el mismo error de intake). Su verdadero documento no está confiablemente en ningún
sistema — lo único disponible es el "293" del Sheet, que también parece incompleto.

Lo que SÍ se mantiene sin cambios: ella no está retirada (84% de avance, 6/7 cursos
completados, Emoflow activo hasta 2026-06-11) — el `q10_id` mal cargado igual lleva su
rastro de actividad real, así que el diagnóstico de "falso positivo dentro de los 18" sigue
siendo correcto, solo cambió el porqué.

**Decisión:** el Sheet de Seguimiento es inmanipulable para nosotros (fuera de nuestro
control operativo) — no se edita ninguna celda. Queda documentado que **este 1 caso de los 18
es un falso positivo por un error de intake en Q10 (teléfono usado como documento)**, no un
retiro real. Samuel confirmó (2026-07-23): dejar todo tal cual está — Tipo ID `Pasaporte`
= `293` (su documento real) y `63851795` es su celular, no hace falta corregir nada en
Supabase (el `q10_id` sigue funcionando como llave de matrícula interna, aunque no coincida
con su documento real).

**Corrección aplicada (mismo día): se pidió que volviera a contar como activa en los
paneles.** Como su `q10_id` (63851795) nunca va a matchear contra el "ID" real de Seguimiento
(293), forzar `en_seguimiento_jc` una sola vez con un UPDATE manual se habría revertido en el
siguiente sync automático. Se aplicó el mismo patrón que ya existía para las cuentas de
prueba (`tools/exclusiones_prueba.json`): nuevo archivo
**`tools/excepciones_seguimiento_jc.json`** (PII, gitignoreado) con su caso documentado, y
`sync_sociodemograficos.py` modificado para forzar `en_seguimiento_jc=true` en cualquier
`q10_id` listado ahí, sin importar el match contra Seguimiento. Sync corrido en real:

- `v_cohorte_estudiantes` (JC 2026): activos 759→**760** (coincide exacto con el oficial de
  Q10), al_dia 749→**750**.
- `v_retiro_probable_jc`: total 18→**17**, aprobado 7→**6**.
- `cohorte_stats.total_participantes`: 759→**760**.

Caso cerrado — persiste correctamente en cada sync futuro sin intervención manual.

### Auditoría de coherencia total del panel vs. la verdad canónica (2026-07-23)

A pedido de Samuel ("cerciorarnos que todo lo que visualizamos de JC use esta nueva verdad"),
se auditaron **las 26 fuentes** que consume `lib/api.ts`, contrastando cada una contra el
universo canónico (pestaña Seguimiento → `en_seguimiento_jc` → 760).

**Resultado: 21 coherentes, 5 no.** Las coherentes dan 760 exacto (`cohorte_stats`,
`v_cohorte_estudiantes`, `v_programa_stats`, `v_curso_completion`,
`v_cohorte_estudiantes_distribucion`, `cohorte_ingresos.activos`) o un subconjunto explicable
por cobertura de datos (`v_demografia_grupo` 759 = 1 sin `grupo_ciudad`;
`v_edad_distribucion` 757 = 3 sin edad; `v_emprendimiento_*` 681 = cobertura de la encuesta).

**Brecha 1 — el bloque Emoflow ignoraba el filtro (4 vistas + 1 tabla).**
`v_emoflow_resumen` / `_por_ciudad` / `_bandas` / `_bandas_ciudad` reportaban **827** y
`emoflow_actividad_semanal.roster` **844**, con el panel diciendo 760 arriba. Desglose
verificado de los 827: **742** canónicos + **17** en retiro probable + **68 sin
`participant_id`** (nunca fueron participantes en Supabase; 56 de ellos sí están en
`postulantes_jc` → son postulantes/retirados antiguos, la misma brecha estructural 832 vs 777).
**Decisión de Samuel: no reemplazar, sino permitir ver ambos universos.** Migración
`011_emoflow_canonico.sql` (aplicada) agrega 4 vistas paralelas `_canonico` con las mismas
columnas; las originales quedan intactas. El frontend gana un toggle
**"Solo estudiantes actuales" (742, default) / "Todos (histórico)" (827)**. Dato interesante:
el promedio de ingresos sube de 33,1 a 35,3 al filtrar — los excluidos usaban menos Emoflow,
consistente con ser retirados. 5 tests permanentes agregados (39→**44/44 PASS**).

**Brecha 2 (crítica) — la verdad canónica se refrescaba SEMANAL, el panel sincroniza DIARIO.**
Verificado contra la API de n8n **en vivo** (no solo el JSON exportado):
`sync_sociodemograficos.py` —el único script que calcula `en_seguimiento_jc`— vivía solo en
`sociodemograficos-semanal` (lunes 6:00), mientras `q10-sync-supabase` corre a diario 9:45.
Consecuencias: (a) de martes a domingo el panel podía contar como activo a alguien que el
equipo ya sacó del Sheet — hasta **6 días de desfase** sobre el dato más canónico que
tenemos; (b) peor, `cargar_supabase.py` escribe el snapshot diario de `historial_cursos`
desde `v_curso_completion`, que depende de ese flag rancio → **la serie histórica heredaba el
desfase de forma permanente** (el snapshot de hoy quedó en 777, no 760).
**Corregido:** `sync_sociodemograficos` insertado en la cadena diaria **entre
`normalize_q10_data` y `cargar_supabase`** (con su nodo IF + `stopAndError`, siguiendo el
patrón del workflow). Ese orden es deliberado: el flag se refresca ANTES de que se escriba el
snapshot del día. Un participante creado por el sync de Q10 ese mismo día queda con
`en_seguimiento_jc=NULL`, que `IS DISTINCT FROM false` deja pasar como activo — comportamiento
conservador correcto. Workflow re-exportado a `n8n-workflows/q10-sync-supabase.json`.
Nota: `sociodemograficos-semanal` sigue activo por `sync_sociodemograficos_mr.py`; el JC corre
dos veces los lunes, lo cual es inocuo (idempotente).

### Cadencia casi-tiempo-real en ventana fuera de horario laboral (2026-07-23)

Samuel pidió que el entorno esté actualizado "al entrar y al salir" y que los picos de carga
no interfieran con el trabajo: actualizaciones **de 17:30 a 07:30**, y mencionó tanto "cada 4
horas" como "cada 2 horas". Al medir duraciones reales en n8n resultó que **no se puede
tratar igual a los dos workflows**, y ambos números terminaron aplicando:

| Workflow | Qué hace | Duración real medida | Cadencia nueva |
|---|---|---|---|
| `Bot Q10 - Actualizar Grupos` | **Scrapea Q10** (browser headless) → Sheets → `export_aprobacion.py` → `docs/aprobacion/data.json` | **2,8 min a 309 min (5 h)**, muy variable | **cada 4 h**: `0 17,21,1,5 * * *` |
| `q10-sync-supabase` | Lee Sheets + Supabase (NO toca Q10) → panel | 0,2–4,3 min, estable | **cada 2 h**: `30 17,19,21,23,1,3,5,7 * * *` |

**Por qué el scraper no puede ir cada 2 h:** una corrida llegó a 309 min. A 2 h de cadencia se
solaparían varias sesiones de browser headless contra Q10 simultáneamente. A 4 h se mantiene la
densidad que ya tenía (no se empeora un riesgo preexistente) y se saca de la franja laboral.

**Por qué el pipeline del panel sí puede ir cada 2 h:** `normalize_q10_data.py` lee la hoja
h2test, no Q10 directamente — por eso corre en menos de 5 min. Es seguro.

**Orden de dependencia (importante):** el scraper produce `docs/aprobacion/data.json`, que
`sync_aprobacion_supabase.py` consume dentro del pipeline. Por eso el scraper arranca en punto
(17:00, 21:00…) y el pipeline a los :30 — media hora de colchón. Las cifras oficiales de
aprobación se refrescan cada 4 h; el resto del panel (Seguimiento, avance, Emoflow) cada 2 h.

**Resultado:** 8 corridas del panel al día, ninguna entre 08:00 y 17:00. Entorno fresco a las
07:30 (llegada) y 17:30 (salida). El `telegramTrigger` del bot quedó intacto — el equipo sigue
pudiendo disparar actualizaciones a demanda desde Telegram.

⚠️ **Deuda detectada al medir esto:** el último nodo del pipeline
(`sync_supabase_to_sheets.py`) **viene fallando desde hace días** — las hojas `H1Test`,
`H2Test`, `H3Test` ya no existen en el Sheet (alguien las borró) y el script aborta pidiendo
que se creen. Todos los pasos de datos anteriores terminan en `exito`, así que **el panel se
actualiza bien**; lo único roto es el volcado de vuelta a Sheets para el equipo. Con 8
corridas diarias esto pasa de 1 a 8 fallos por día — pendiente decidir si se recrean las hojas
o se retira el paso.

### Verificación cruzada corregida + hallazgo estructural (2026-07-23)

Samuel reportó que la tabla de verificación cruzada (oficial vs. `v_aprobacion_cursos_jc_ajustado`)
salía completamente vacía en "oficial" y "Revisar" en las 7 filas. Dos causas, una de display y
una real:

**1) Bug de comparación (arreglado):** el frontend comparaba `curso === curso` con igualdad
exacta de string, pero los nombres vienen en formato distinto en cada fuente — oficial en
Título ("Hackea tu cerebro..."), recalculado en MAYÚSCULAS crudas de `courses.nombre`
("HACKEA TU CEREBRO..."). Nunca iban a matchear. Arreglado comparando normalizado
(`trim().toUpperCase()`) en `app/page.tsx`.

**2) "Cursaron (recalculado)" no era una métrica real (rediseñada, a pedido de Samuel):**
en Supabase, **los 777 participantes de la cohorte tienen fila de `enrollments` para los 7
cursos por construcción** (se cargan en bloque al matricular, incluso con avance=0%) — por
eso ese número daba 777 fijo en las 7 filas, sin variar como el oficial (832/791/779, que sí
refleja participación real por curso desde Q10). Reemplazada por **"Cursando ahora"** =
`banda_0_25 + banda_26_80` (activos con avance <80% en ESE curso puntual) — sí varía de forma
útil (HTML: 247 cursando vs. Lógica: 12, Emprendimiento: 3), responde "qué estudiantes
quedan" en vez de fingir un "cursaron" no comparable. La columna "¿Coincide?" ahora solo
evalúa Aprobados (la única pareja con la misma definición en ambos lados).

**3) Hallazgo real, no un bug — el "Revisar" en Aprobados de 4 de los 7 cursos es esperado:**
Q10 tiene **832 ingresados totales** (`cohorte_ingresos`: 760 activos + 74 retirados
oficiales acumulados), pero Supabase solo llegó a cargar **777** (760 activos + 17 de la
alerta de retiro reciente) — **~55 personas que Q10 ya procesó como retiradas hace tiempo
nunca se cargaron en Supabase** (confirma H7, documentado antes: "n=777 = alguna vez cargado
activo en enrollments"). El recálculo desde Supabase sub-cuenta aprobados en los cursos
**tempranos** de la ruta (Bienvenida: 72 aprobados-retirados oficiales vs. solo 17 posibles
en Supabase; Habilidades 52; Hackea 65; Emprendimiento 24) porque esos ~55 retirados antiguos
sí alcanzaron a completarlos antes de irse. En los cursos **tardíos** (Lógica: 5,
IA: 10) casi no hay diferencia — esos retirados antiguos probablemente se fueron antes de
llegar tan lejos, así que su ausencia en Supabase no distorsiona esos dos cursos. Por eso
Lógica e IA dan "Sí" y los otros 4 dan "Revisar" — **es el patrón esperado, no indica un sync
atrasado.** Nota agregada directamente en el panel para que el equipo no lo confunda con algo
roto. Cerrar esta brecha de raíz requeriría cargar retroactivamente esas ~55 personas
(back-fill histórico) — no se hizo, queda fuera de alcance de esta sesión.

### `v_persona_360` — trazabilidad total por persona (2026-07-23)

Vista nueva (`docs/migrations/008_v_persona_360.sql`), a pedido explícito: "para un informe
individual podamos tener todo de una persona en una sola consulta". Une por cédula:
`participants` (matrícula/avance real + `en_seguimiento_jc`), `postulantes_mr`,
`postulantes_jc`, `emoflow_ingresos` (match por email) y `asistencia_promedio` (match por
email) — 8.100 identidades únicas cubiertas. Uso: `GET /rest/v1/v_persona_360?cedula=eq.<cedula>` **solo con service_role**
(RLS+REVOKE estricto, verificado 401 a anon). Reemplaza el ejercicio manual multi-fuente que
motivó [[postulantes-mr-supabase]] en primer lugar — cierra de facto la Fase 5 de esa nota
(herramienta de búsqueda unificada), aunque como vista SQL en vez de script `tools/`.

| # | Hallazgo | Sev. | Evidencia | Estado / remediación |
|---|---|---|---|---|
| H1 | 17 vistas `v_*` SECURITY DEFINER (no 21: el advisor duplica) | Alta→**mitigada** | Barrido anon de las 17: **solo agregados**, cero email/nombre/cédula. `v_puntaje_estudiante` (la del incidente) → 401 | Aceptado+documentado. Propuesta: DROP de `v_puntaje_estudiante` (sin consumidores; superficie latente) — 006(4) |
| H2 | RPC `es_publico`/`participa_en` ejecutables por anon | Media | POST /rpc/* con anon → 200 | `participa_en`: NINGUNA policy la usa → REVOKE — 006(1). `es_publico`: la usan 2 policies → mover a schema `interno` no expuesto (las policies sobreviven por OID) — 006(2) |
| H3 | Policy UPDATE `asistencia_zoom` con USING implícito true | Baja | pg_policies: qual=null | Sin exposición real (anon sin GRANT en la tabla desde 07-14); recrear bien formada — 006(3) |
| H4 | 6 tablas PII "RLS sin policy" (implícito) | Baja | pg_policies vacío en ellas | Efecto correcto (solo service_role). Decisión **intencional** — formalizada con COMMENTs — 006(5) |
| H5 | Cuadre cohorte 832 ≠ 765+69 | Resuelto | `aprobacion/data.json`: cohorte = habilitados **∪** retirados; **2 personas en ambos** (retiro+reingreso) | Definicional, no error. Test permanente: overlap ∈ [0,5] — PASS |
| H6 | Δ0,7% emoflow persona vs diario | Resuelto | 27.408 vs 27.594; causa: params de descarga distintos (`empresa=` vs scope=all) | Test permanente con tol 2% — PASS. Fix de fondo (unificar params) queda en plan |
| H7 | n=777 vs activos=765 | Resuelto | 777 = "alguna vez cargado activo" en enrollments (upsert no borra); 765 = habilitados HOY en Q10 | Documentado aquí como definición estándar: para análisis usar enrollments (con la salvedad); para cifras oficiales, cohorte_ingresos |
| H8 | 3 participants con edad=0 | Media | Test C de la suite (FAIL actual) | Clamp [10,90] agregado a `sync_sociodemograficos.py` (hecho); limpieza one-off — 006(7) |
| H9 | 1 fila huérfana emoflow (fecha_corte vieja) | Baja | fecha_corte=2026-07-21 (1/827) | DELETE propuesto — 006(8) |
| H10 | Celdas n<5 en `v_demografia_grupo` (ciudad×género) | Media | 3 celdas; ej. otros_genero=1 en BAQ (k=1 sobre atributo sensible) | Supresión <5 propuesta — 006(6); requiere confirmar que el frontend tolere NULL |
| H11 | Repo | Limpio | `git ls-files`: tools/ no trackeado, solo `.env.example`, 0 claves hardcodeadas, 0 PII en data.json públicos | Sin acción |
| H12 | Backups | Media | Free tier: **sin backups automáticos ni PITR** | Runbook abajo; decisión Pro ($25/mes) pendiente con la migración de infra |

### Frontend conectado a `v_retiro_probable_jc` y `v_aprobacion_cursos_jc_ajustado` (2026-07-23)

Ambas vistas existían en Supabase desde el hallazgo del H5/stale-sync pero no tenían UI —
Samuel pidió conectarlas ("agrégalo"). Cambios en `~/panel-datos` (repo `comunicaciones-ai/Panel-De-Datos`):

- `lib/api.ts`: interfaces `RetiroProbableJc` y `AprobacionCursoAjustado`; agregadas a `Datos`
  y al `Promise.all` de `cargarTodo()` (ahora 26 fuentes, no 24).
- `app/page.tsx`, pestaña Resumen, solo JC y cohorte actual:
  - Sección **"Retiro probable (pendiente de confirmar en Q10)"** — 3 `EstadoStat` (ya habían
    aprobado / no habían aprobado / total en duda), justo debajo de "Estado de la cohorte".
    Se renderiza solo si `retiro_probable_total > 0`. Texto explícito: no resta de
    `cohorte_ingresos.retirados`, es una alerta en trámite.
  - Sección **"Verificación cruzada: aprobación oficial vs. recalculada"** — tabla por curso
    comparando `aprobacion_cursos` (oficial) contra `v_aprobacion_cursos_jc_ajustado`
    (recalculado), columna "¿Coincide?" en verde/rojo. Si un futuro sync se vuelve a atrasar
    (como el del H5), la fila lo muestra en rojo sin que alguien tenga que ir a buscarlo en SQL.
- La tabla `retiros` se dejó fuera deliberadamente — sigue vacía, sin `sync_retiros.py`, nada
  que mostrar todavía.
- Verificado: dev server local (`next dev`, puerto 3000) recompiló sin errores tras los
  cambios. No se pudo verificar visualmente por captura (extensión de Chrome no conectada en
  esta sesión) — pendiente que Samuel confirme visualmente en `localhost:3000` pestaña JC.

### Runbook de restauración (estado actual, free tier)

No hay backup de Supabase — la estrategia real es **reconstrucción desde fuentes**, todas re-consultables:
1. `participants`: restaurar del snapshot diario (`participants_snapshots`, jsonb completo) o re-correr `cargar_supabase.py`.
2. Todo lo demás: re-correr el pipeline correspondiente (Q10/Sheets/Emoflow CSV/Mongo — ver [[mapa-codigo]]); todos los syncs son upserts idempotentes que convergen al estado de la fuente.
3. Esquema: re-aplicable desde `docs/migrations/` + `schema-supabase-completo.sql`.
Límite honesto: series históricas cuyas fuentes ya no existen (`historial_*` viejos, snapshots) se perderían — son las únicas tablas no reconstruibles. Si eso importa, subir a plan Pro.

### Robustez de pipelines (evaluación 2026-07-23)

- **Idempotencia:** todos los syncs usan upsert `on_conflict` + `merge-duplicates` (verificado
  en código); `sync_postulantes_mr` verificado empíricamente con doble corrida (2026-07-22,
  mismo conteo). No se re-corrieron los demás syncs hoy (escribirían en prod — restricción
  solo-lectura); la garantía es estructural + convergencia al re-ejecutar.
- **Fallo ruidoso:** los scripts imprimen `RESUMEN: ... estado=error` y exit≠0 (n8n los
  detecta); el workflow diario tiene camino de error con alerta Telegram (verificado en vivo
  2026-07-21). Sin fallos silenciosos conocidos.
- **Fallo parcial:** no hay transaccionalidad — un crash a mitad de upsert deja lotes
  parciales, pero la siguiente corrida converge (idempotencia). Red de seguridad real solo
  para `participants` (snapshot previo diario). Aceptado y documentado; mitigación extra si
  se quisiera: snapshots para emoflow/postulantes (no propuesto — bajo valor vs. costo).

### Matriz de cobertura programa × dato (el panorama completo)

| Dato | JC | MR |
|---|---|---|
| Postulantes (universo amplio) | 🟢 `postulantes_jc` 2.556 (Mongo; 464 sin matrícula) | 🟢 `postulantes_mr` 5.310 (Sheet 5 pestañas; 16 pares pendientes) |
| Matrícula / cohorte | 🟢 4 cohortes (2023-2026); 2026: 832 | 🟡 solo 2025-2026 (Q10 no trackeó MR antes de 2025 — confirmado, no recuperable); 2026: 342 |
| Sociodemográficos | 🟡 género/edad/ciudad 98,7%; **sin estrato/vivienda/civil/estudios** | 🟢 completos (BD-Mujeres ROFÉ): estrato, vivienda, civil, estudios |
| Uso Emoflow | 🟢 individual (827 usuarios, match 91,8%) + series día/semana por ciudad | 🔴 **cero** — Emoflow es solo JC (0/1.314 participantes MR con fila; verificado) |
| Avance cursos (individual) | 🟢 5.439 matrículas 2026 | 🟢 existe (480 cursaron; 194 con avance>0) |
| Aprobación (agregado) | 🟢 92,8% por matrícula / 88,3% por estudiante | 🟢 pero **dos métricas distintas conviven**: 15,2% (por matrícula, data.json) vs 31,6% (por estudiante, cohorte_ingresos) — no es contradicción, son denominadores distintos; etiquetar siempre cuál se usa |
| Asistencia Zoom | 🟢 490 estudiantes | 🟡 mezclada en las mismas tablas (sin split por programa verificado) |
| **Retiro individual** | 🔴 solo agregado (69) | 🔴 solo agregado (25) + 33 filas históricas en Inactivas |

**Qué le falta a MR para replicar el análisis uso↔resultado de JC:** (1) Emoflow — no está
desplegado para MR; sin eso no hay variable de uso (gap de producto, no de datos); (2) retiro
individual (igual que JC — lo cubre `007_retiros`); (3) definición única de aprobación
(etiquetar métrica). Con avance individual ya disponible, si Emoflow se habilitara para MR el
análisis sería replicable tal cual.

### Deprecación formal (plan, no ejecutado)

1. `emoflow_participacion_semanal` (🔴): sin pipeline (nodo eliminado 2026-07-21), sin
   consumidores nuevos. Plan: (a) verificar que el frontend ya no la consulte, (b) exportar
   CSV de respaldo a `tools/`, (c) DROP en una migración futura (008). Hasta entonces: no usar.
2. `sync_emoflow.py` (deprecado 2026-07-20): ya fuera de n8n; mover a `_obsoletos/` en la
   próxima limpieza de repo (hoy sigue en `scripts/panel-datos/` con warning en el header).

### Monitoreo continuo (propuesta — pendiente de aprobación)

Workflow n8n `panel-verificacion-diaria` (candidato): Schedule 10:30 COT (tras el sync de
9:45) → Execute Command `python scripts/panel-datos/test_integridad_supabase.py --rapido` →
IF exit≠0 → Telegram a Samuel (chat 8141703221, credencial existente `Telegram Q10 Bot`).
Opcional (requiere aprobar la escritura): upsert del resultado en `alertas_datos`
(id=`integridad_supabase`, activa=true/false, detalle=tests fallidos). No se implementó nada
en n8n todavía — al aprobarse, exportar JSON a `n8n-workflows/` según checklist.

## Análisis Emoflow 2026-07-23 — resumen de hallazgos (agregados)

**Pregunta:** ¿el uso de Emoflow está asociado con resultados académicos (JC 2026, n=777 activos)?

- **Uso**: mediana 28 check-ins, p90 60, máx 404; solo 18/777 (2,3%) con cero usos.
- **Asociación uso↔avance**: Spearman ρ=0.337 (p≈4e-22). Chi² cuartiles×aprobado-80:
  p≈6e-7, V de Cramér=0.202 (efecto pequeño-mediano). % aprobado-80: Q1 92,1% → Q3-Q4 ~100%.
- **Regresión logística** (ajustada por género, edad y ciudad; estrato sin cobertura JC):
  OR=2.36 por unidad de log-uso, IC95 [1.51, 3.69], p=1.8e-4. Con umbral aprobado-100
  (56,8% base, más variación): OR=1.90, IC95 [1.56, 2.31], p=1.3e-10. Género y edad no
  significativos.
- **Por ciudad** (normalizado): mayor uso promedio QTO (42,4), BAQ (42,1), PAN (41,4);
  menor MED (26,1). Mayor % aprobado-100: CAL 81,7%, UY 70,8%; menor MED 42,6%, GYL 44,3%.
  Tendencia % activos semanal (primeras vs últimas 4 semanas): subiendo MED (+14,2), QTO
  (+8,3); cayendo fuerte GYL (−27,5), CAL (−9,6), UY (−8,5).
- **Límites (explícitos)**: asociación ≠ causalidad — el uso de Emoflow puede ser marcador de
  compromiso general, no causa del avance. El resultado "aprobado-80 entre activos" está casi
  saturado (97,3%); la variable donde el uso realmente discrimina es avance completo (100).
  **El retiro — el resultado más importante — no es analizable a nivel individual con
  Supabase hoy** (ver plan, punto 2). Para afirmar causalidad haría falta diseño longitudinal
  (uso ANTES del resultado, hoy ambos son acumulados al mismo corte) o experimento.
- Detalle completo (con IDs internos, sin nombres): `tools/analisis_emoflow_resultados.json`;
  dataset PII: `tools/analisis_emoflow_dataset.csv`; script: `tools/analisis_emoflow_resultados.py`.
