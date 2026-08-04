# Prompt para Claude Code — cerrar los 3 pendientes de vigilancia de cursos

> Creado 2026-07-29 (sesión Cowork con Lina), tras aplicar las migraciones 026/027.
> Copiar el bloque de abajo como primer mensaje de una sesión de Claude Code en la raíz del
> repo. Modelo recomendado: **Sonnet** (trabajo mecánico con reglas ya escritas). Escalar a
> Opus solo si el punto 3 se vuelve una discusión de diseño.

---

```
Vas a cerrar 3 pendientes concretos de panel-datos-rofe (Fundación ROFÉ / Jóvenes creaTIvos).
El diagnóstico ya está hecho y las migraciones ya están aplicadas — tu trabajo es ejecutar,
verificar y reportar, no rediseñar.

## Lectura obligatoria antes de tocar nada
1. CLAUDE.md — reglas duras del proyecto.
2. docs/convenciones.md, secciones "Un ETL que solo hace upsert nunca reconcilia lo que
   desaparece de la fuente" y "Fuente desordenada: sellar última vez visto, no modelar
   estados". Son de ayer y explican el porqué de todo lo de abajo.
3. docs/migrations/026_cursos_alias_y_frescura_APLICADA.sql y
   027_v_choques_cursos_APLICADA.sql — YA APLICADAS en producción. No las vuelvas a correr.
4. La última entrada de claude_sessions.md ("Renombre de curso en Q10: causa raíz...").
5. docs/procesos/mapa-codigo.md antes de tocar cualquier script.

## Contexto en una frase
Q10 renombró un curso sin aviso el 24-jul. Como los ETL solo hacen upsert y nunca reconcilian
lo que desaparece de la fuente, quedó un curso fantasma duplicado en 4 tablas. Ya se limpió y
se construyó la vigilancia (cursos_alias + visto_en_fuente_at + v_choques_cursos). Faltan 3
cosas que no se pudieron hacer sin credenciales ni acceso a n8n.

## Estado verificado en Supabase (kbxptoowtnteflhrfwid) al cerrar la sesión anterior
Si alguno de estos números NO coincide cuando arranques, PARA y repórtalo antes de ejecutar
nada — significa que algo corrió en el medio y el diagnóstico cambió.

  courses cohorte 2026 ................ 10 (7 jc + 3 mr)
  enrollments jc 2026 ................. 5.422 crudas = 5.320 vigentes + 102 fantasmas
  enrollments mr 2026 ................. 559 crudas, 0 fantasmas
  cohorte_ingresos 2026 activos ....... jc=760 · mr=322
  v_programa_stats jc 2026 ............ 5.320 matrículas · 98.1% avance · 760 participantes
  suma participantes por ciudad ....... 760 exacto
  aprobacion_cursos jc 2026 rango ..... 81.1% a 100.0%
  datos_archivados .................... 839 filas
  v_choques_cursos .................... 1 fila, informativa (curso MR que cerró clases)
  cursos_alias ........................ 1 fila (el renombre HTML confirmado por Lina)

Los 102 fantasmas son 17 personas dadas de baja × 6 cursos. Sus matrículas siguen en
enrollments porque el ETL no borra. Las vistas ya los excluyen vía
`en_seguimiento_jc IS DISTINCT FROM false`, por eso 5.320 ≠ 5.422. Eso es correcto hoy.

## Reglas duras (ya validadas en este proyecto, no las reinventes)
- Importa Supa/get_todo/cargar_env_local de un script existente (sync_postulantes_mr.py o
  test_integridad_supabase.py). NUNCA reescribas el paginador: un offset que no avanza es un
  loop infinito silencioso que ya pasó dos veces acá.
- truststore.inject_into_ssl() al inicio de todo script Python nuevo.
- Nunca imprimas secretos ni PII en chat, logs ni commits. PII solo en tools/ (gitignoreado).
- Al editar workflows n8n por API: el JSON siempre desde archivo UTF-8, nunca inline por
  PowerShell (mutila tildes y ñ).
- Si un número no cuadra con lo esperado: PARA y repórtalo con la query exacta. No ajustes
  tolerancias ni umbrales para que algo pase.
- Un commit por punto resuelto, mensaje en español, sin PII. ⚠ El árbol de trabajo tiene
  cambios previos sin commitear de otras sesiones: haz `git add` SOLO de los archivos que
  tocaste tú, nunca `git add -A` ni `git commit -a`.

---

## PUNTO 1 — Correr los 2 ETL parcheados ayer

`cargar_supabase.py` y `sync_aprobacion_supabase.py` fueron modificados ayer para absorber
renombres desde `cursos_alias` y sellar `visto_en_fuente_at`. La sintaxis está verificada con
py_compile, pero NUNCA se ejecutaron. Sos el primero en correrlos.

Secuencia, sin saltarte pasos:

  a) `python scripts/panel-datos/normalize_q10_data.py` — regenera tools/supabase_payload.json
     fresco. Reportá su línea RESUMEN:.
  b) `python scripts/panel-datos/cargar_supabase.py --dry-run` — confirmá que no truena.
  c) `python scripts/panel-datos/cargar_supabase.py` — corrida real.
  d) `python scripts/panel-datos/sync_aprobacion_supabase.py --dry-run` y luego real.
  e) `python scripts/panel-datos/test_integridad_supabase.py --rapido` → tiene que dar
     estado=exito.

Qué esperar (y qué NO):
- El log debería decir "Renombres absorbidos desde cursos_alias: 0 cursos, 0 matrículas" o
  no decir nada de renombres. Es lo correcto: h2test ya solo trae el nombre nuevo, y
  data.json también. El código de remapeo es defensivo, para cuando el nombre viejo
  reaparezca. Si dice un número > 0, reportalo — significa que el nombre viejo volvió.
- `courses.visto_en_fuente_at` debe quedar en la hora de la corrida para los 7 cursos JC y
  los 2 MR vivos, y **debe seguir en 2026-07-21** para el curso MR
  "DE LA IDEA A LA ACCIÓN, TU GUÍA PARA EMPRENDER CON ÉXITO". Si ese también se actualiza,
  hay un bug en el parche: verificá con
  `SELECT nombre, visto_en_fuente_at FROM courses WHERE cohorte='2026' ORDER BY 2;`
- NO debe aparecer ningún curso nuevo en cohorte 2026. Si aparece uno, corré
  `SELECT * FROM v_choques_cursos WHERE severidad='alta';` — probablemente hubo otro renombre.
- Los 102 fantasmas van a seguir ahí. Es esperado: este ETL no borra. Los aborda el punto 3.

Al terminar, verificá que los números canónicos no se movieron (760/322, suma por ciudad
760) y reportá el antes/después de cada uno.

---

## PUNTO 2 — Conectar v_choques_cursos a n8n + Telegram

Objetivo: que las alertas de severidad alta lleguen solas, sin que nadie consulte la vista.
Hoy la vigilancia existe pero es invisible.

- Copiá el patrón del workflow **`alerta-frescura-vencida`**, que ya está activo y hace
  exactamente esto (consulta una vista, evalúa, avisa a Telegram). Exportalo, leelo, y armá
  el nuevo con la misma estructura y las mismas credenciales. No inventes un patrón nuevo.
- Nombre del workflow: `alerta-choques-cursos` (convención `[area]-[accion]`, minúsculas con
  guiones).
- Consulta: `SELECT * FROM v_choques_cursos WHERE severidad = 'alta';`
  ⚠ **Solo severidad alta.** Las informativas son contexto para revisión semanal, no para
  interrumpir a nadie — hoy hay 1 informativa permanente (el curso MR que cerró) y si la
  incluís, el canal se vuelve ruido y la gente lo silencia.
- Cadencia: una vez al día es suficiente, después de que corra la cadena de sync. Mirá a qué
  hora termina `q10-sync-supabase` y programalo después.
- Cuando no haya filas, NO mandar mensaje. Silencio = todo bien.
- El mensaje debe incluir tipo, curso y el campo `detalle` (ya viene redactado en español y
  con la acción sugerida). Nada de PII: la vista no tiene datos personales, no agregues.
- Error handling explícito: asigná `errorWorkflow` como el resto de los workflows del
  proyecto. Ningún workflow puede fallar en silencio.
- Exportá el JSON a `n8n-workflows/` en el mismo commit (convención del proyecto).

Probalo antes de activarlo: forzá una alerta alta temporal (por ejemplo consultando con
`WHERE severidad IS NOT NULL` en una corrida manual) para confirmar que el mensaje llega
bien formateado con tildes, y devolvé el filtro a `= 'alta'` antes de dejarlo activo.

---

## PUNTO 3 — Criterio de "matrícula vigente" (esto NO lo decidas solo)

Problema: 102 matrículas (17 personas dadas de baja × 6 cursos) siguen en `enrollments`
congeladas desde el 23-jul, porque el ETL no borra lo que desaparece de la fuente. Hoy las
vistas las excluyen con `en_seguimiento_jc IS DISTINCT FROM false`, que funciona pero es
indirecto: depende de una columna de alerta operativa, no de un hecho sobre la matrícula.

Restricción de diseño (decisión de Lina, 2026-07-29, no la contradigas): **nada se borra** y
**no se modelan estados** que la fuente no confirma. La administración de cursos en Q10 es
impredecible: se permite retomar actividad en cursos pasados, así que una matrícula
"cerrada" puede revivir. Por eso esto se resuelve con criterio de consulta, no borrando
filas ni agregando un flag booleano que mienta.

Tu tarea: **investigá y presentá 2 o 3 opciones a Lina con su trade-off, y esperá su
decisión antes de implementar.** Lo mínimo que cada opción debe responder:
- ¿Cómo se define "matrícula vigente" de forma verificable contra la fuente?
- ¿Qué vistas habría que tocar y qué números cambiarían? (dá el antes/después real, medido)
- ¿Qué pasa si una de esas 17 personas reingresa? La respuesta correcta es que reviva sola.

Una opción a evaluar (no necesariamente la mejor): replicar en `enrollments` el patrón que
ya funcionó en `courses` — un `visto_en_fuente_at` por matrícula, y "vigente" = confirmada en
la última corrida. Tiene la ventaja de ser el mismo patrón ya documentado y de revivir solo;
la desventaja de ser una migración sobre una tabla de 18.196 filas y de que hoy `updated_at`
ya cumple esa función de facto (el upsert lo sella incluso sin cambios) — verificá si eso
último es cierto antes de proponer una columna nueva, porque si `updated_at` ya sirve, la
migración es innecesaria.

No implementes nada del punto 3 sin el OK explícito de Lina.

---

## Al terminar (siempre, sin excepción)
1. Actualizá `docs/procesos/supabase-estructura.md` si cambió el estado de alguna tabla.
2. Patrón reutilizable nuevo → `docs/convenciones.md`.
3. Workflow n8n nuevo → JSON exportado a `n8n-workflows/` en el mismo commit.
4. Entrada al FINAL de `claude_sessions.md` (5-10 líneas, formato del archivo).
5. Marcá los puntos 7, 8 y 9 de la sección 4/P1 de
   `docs/procesos/plan-maestro-2026-07-29.md` según cómo quedaron.

Arrancá por el punto 1 y reportá el resultado real (línea RESUMEN: + query de verificación)
antes de pasar al 2.
```
