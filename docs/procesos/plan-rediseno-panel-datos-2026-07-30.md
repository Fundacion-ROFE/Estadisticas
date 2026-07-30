# Rediseño del panel de datos público (desde cero) — especificación

> **Conexiones:** [[00-vision-global]] · [[panel-control-jc-mr]] · [[plan-visualizacion-2026-07-30]] ·
> [[diccionario-metricas]] · [[supabase-estructura]] · [[panel-datos-etl]]
>
> Pedido de Samuel, 2026-07-30 (noche). Igual que con `panel-control-jc-mr.md`: **primero se
> escribe/afina la especificación, después se construye.**
>
> **Estado: especificación + plan de 4 fases listos (ver §3 decisiones, §4 plan). Sin
> ejecutar todavía** — esperando confirmación explícita antes de tocar Supabase o
> `panel-datos-rofe`.
>
> **No duplica trabajo existente:** revisado contra `plan-visualizacion-2026-07-30.md` (ya
> cerrado, agregó geografía/frescura al panel actual sin tocar su estructura de navegación) y
> `panel-control-jc-mr.md` (herramienta interna de escritorio con PII — este documento es sobre
> el panel PÚBLICO, agregados sin PII, otro proyecto). No existe ningún plan previo de
> reorganizar la UX de este panel — es trabajo genuinamente nuevo.

---

## 0. Pedido original de Samuel (tal cual, para no perder matices al resumir)

> "genuinamente el panel de datos requiere una reconfiguracion igualmente que el gui podrias
> analizar los datos que muestra y organizarlos con filtros que se adapten de mejor manera a
> la informacion del programa con y sin habilitados, con las cohortes, con la demografia, los
> dos programas MR-JC, las estadisticas, la asistencia y emoflow y que lo muestre con mayor
> sencilles y UI/UX para el usuario"

---

## 1. Diagnóstico del panel actual (`panel-datos-rofe`, `app/page.tsx` + `lib/api.ts`)

Leído completo antes de escribir esta sección — hallazgos concretos, no impresiones:

### 1.1 No existe ningún filtro de "habilitados / todos"
Búsqueda exhaustiva en `app/page.tsx`: la única exposición de activos/ingresados/retirados es
como **KPIs de solo lectura** (`kpis.activos`, `kpis.retirados`, `kpis.ingresados`) — no hay
ningún control que el usuario pueda accionar para decir "mostrame solo habilitados" o
"mostrame todos, incluyendo quien se retiró". Es exactamente el hueco que señaló Samuel: el
dato existe (`cohorte_ingresos.ingresados/activos/retirados`, ya es la fuente canónica del
diccionario), pero no es un **filtro**, es solo una tarjeta fija.

### 1.2 Lógica condicional duplicada entre "Resumen" y "Cursos"
Ambos tabs tienen una rama casi idéntica (`esActual && aprobacionProg.length > 0`) que decide
entre mostrar el gráfico de aprobación canónica (cursaron/aprobaron/en curso/retirados) o el
gráfico de "completación" (matriculados/completados) — la misma decisión, calculada dos veces,
en dos lugares distintos del archivo (`app/page.tsx:687` y `:833`). Right now un cambio en una
rama fácilmente puede desalinearse de la otra sin que nada lo avise.

### 1.3 "Demografía" son dos tabs distintos disfrazados de uno
Para MR: estado civil, nivel de estudios, tipo de vivienda, estrato, edad, emprendimiento (6
gráficos). Para JC: participantes por grupo, género, edad (3 gráficos, ninguno compartido con
MR). No hay ningún elemento visual compartido — el usuario que cambia de programa en el mismo
tab ve una pantalla completamente distinta sin aviso de por qué (la razón real —
`estrato`/`vivienda`/`estado_civil` no existen para JC, `emprendimiento` de la encuesta
diagnóstico tampoco — es correcta y ya está en `diccionario-metricas.md`, pero la UI no la
comunica, solo cambia el contenido en silencio).

### 1.4 Tabs que aparecen/desaparecen según el programa, sin aviso previo
`tabsDisponibles(programa, esActual)` oculta "Emprendimiento" y "Emoflow" completo cuando
`programa === 'mr'`, y "Historial"/"Emprendimiento"/"Demografía"/"Emoflow" cuando la cohorte
no es la actual. El usuario descubre que un tab "no aplica" solo al ver que desapareció de la
barra de navegación — no hay una explicación en el momento.

### 1.5 Asistencia Zoom **no está en el panel público en absoluto**
No es un problema de organización — es una ausencia total. `type Tab` no incluye
"Asistencia", y ninguna llamada de `lib/api.ts` trae `asistencia_promedio` o
`asistencia_zoom`. Esa fuente existe en Supabase (490+ estudiantes, agregable sin PII), pero
hoy solo la consume la GUI interna (`panel_riesgo_gui.py`/`panel_control_gui.py`), nunca el
panel público. Samuel la mencionó explícitamente en el pedido — hay que decidir si esto es un
hueco a cerrar en el rediseño o si se deja fuera a propósito (ver §4).

### 1.6 El filtro de ciudad y el drill-down de municipio viven en dos lugares distintos
El selector de ciudad (`ciudadElegida`, barra superior) solo existe para JC y solo para la
cohorte actual (`v_demografia_grupo` es JC-only). La sección "Geografía" que se agregó ayer
(municipio, ambos programas, vía `v_pub_geografia`) vive dentro del tab Resumen, desconectada
del selector de arriba. Un rediseño real debería unificar esto en un solo mecanismo de filtro
por geografía, no dos.

---

## 2. Prompt mejorado — especificación funcional

Reescritura del pedido de Samuel en requisitos concretos, agrupados por lo que él pidió:

### 2.1 Filtros globales (aplican a TODAS las secciones, no solo KPIs sueltos)
1. **Programa** (JC / MR) — ya existe, se mantiene.
2. **Cohorte** — ya existe (todas las disponibles, no solo la actual), se mantiene.
3. **Estado — NUEVO.** Reemplaza la exposición pasiva actual por un control real:
   - "Activos (habilitados)" — default, usa `cohorte_ingresos.activos` / `v_pub_cohorte`.
   - "Todos (ingresados)" — cohorte completa, activos + retirados.
   - "Retirados" — solo quien se retiró, útil para análisis de deserción.
   Este filtro debe propagarse a Resumen, Cursos y Demografía de forma consistente — hoy cada
   sección decide su propio universo sin que el usuario lo controle.
4. **Ciudad/Municipio — unificado.** Un solo selector (no dos como hoy) que cubra ambos
   programas vía `v_pub_geografia`, con drill-down grupo→municipio integrado en el selector
   mismo, no en una sección aparte.

### 2.2 Secciones (reemplaza los 6 tabs actuales por una estructura más consistente)
- **Resumen** — KPIs del filtro vigente (programa×cohorte×estado×ciudad) + estado de la
  cohorte. Sin la lógica duplicada de §1.2 — un solo lugar decide cursaron/aprobaron/en
  curso/retirados vs. completación, no dos.
- **Cursos** — detalle por curso, unificado (no duplicar la decisión de §1.2 con Resumen).
- **Demografía** — misma estructura visual para JC y MR (mismo grid de tarjetas), pero cada
  tarjeta que no aplica para un programa dice explícitamente **"No aplica — [razón corta]"**
  en vez de no aparecer. Ej.: "Estrato — no aplica (JC no captura este dato)" en vez de que la
  tarjeta desaparezca sin explicación.
- **Historial** — evolución en el tiempo, se mantiene.
- **Emprendimiento** — se mantiene, solo JC, pero con el mismo tratamiento de "no aplica" que
  Demografía cuando el programa es MR (en vez de ocultar el tab).
- **Emoflow** — se mantiene, solo JC, mismo tratamiento de "no aplica" para MR.
- **Asistencia — NUEVA (confirmado, ver §4).** Tab nuevo, agregado sin PII vía una vista
  pública nueva análoga a `v_pub_geografia`, fuente `asistencia_promedio`.

### 2.3 Reglas duras que el rediseño NO puede romper (ya establecidas, no se renegocian)
- Nunca mostrar 0%/vacío donde el dato no aplica — siempre "no aplica" o "sin dato" con razón.
- Supresión de municipios con `n < 5` (`umbral_supresion_municipio()`) — ya implementado, se
  mantiene tal cual.
- Fecha del dato visible (`v_frescura`) — ya implementado ayer, se mantiene.
- Definiciones canónicas de `diccionario-metricas.md` (activos = `cohorte_ingresos.activos`,
  aprobado = avance > 80%, etc.) — el filtro de "Estado" nuevo debe usar exactamente estas
  definiciones, no inventar una paralela.
- Solo vistas de agregados para `anon` — ninguna columna con PII en el panel público.

---

## 3. Decisiones confirmadas por Samuel (2026-07-30, noche)

| Pregunta | Decisión |
|---|---|
| ¿Stack? | **Mismo repo/stack** (Next.js + Tailwind + Recharts) — reescritura completa de `app/page.tsx`, no un proyecto aparte. |
| ¿Asistencia Zoom entra al panel público? | **Sí.** Vista pública nueva + tab nuevo. |
| ¿El filtro "Estado" aplica a todas las secciones? | **Sí, a todas** — Resumen, Cursos, Demografía, Emprendimiento, Emoflow y Asistencia. Implica vistas de Supabase nuevas (ver §5 Fase 1) — no es solo reordenar la UI existente. |
| ¿Prioridad frente a `panel-control-jc-mr.md` Fases 4-5? | **Este rediseño primero.** |

---

## 4. Plan de fases

### Fase 1 — Backend: vistas públicas nuevas con dimensión "estado" (activo/retirado)

**Regla de diseño:** ninguna vista existente se modifica en el lugar — todo se crea como
vistas `v_pub_*` **nuevas y paralelas**, para que el panel en producción (con `app/page.tsx`
viejo) siga funcionando sin cambios hasta que la Fase 3 esté lista para el cutover. Mismo
patrón ya usado con `v_pub_cohorte`/`v_pub_geografia` (plan-visualizacion-2026-07-30.md).

- **Resumen/Cursos: sin SQL nuevo.** `v_pub_cohorte` (ingresados/activos/retirados) y
  `aprobacion_cursos`/`v_aprobacion_cursos_vigencia` (cursaron/activos/retirados por curso) ya
  tienen las 3 cifras como columnas separadas — el filtro de Estado ahí es solo lógica de
  frontend (elegir qué columna leer), no requiere una vista nueva.
- **`v_pub_demografia` (nueva).** Unifica `v_demografia_grupo` + `v_mr_demografia` +
  `v_edad_distribucion` en una sola vista ancha: `programa, cohorte, estado, grupo_ciudad,
  genero, edad_rango, estrato, estado_civil, nivel_estudio, tipo_vivienda, total`. Las
  columnas que no aplican a un programa (`estrato` para JC, por ejemplo) quedan `NULL` de
  forma natural — el frontend ya sabe mostrar "no aplica" ahí (§2.3). `estado` se calcula con
  la misma lógica de `retirado` que ya usa `v_gui_personas` (participante en `retiros` =
  retirado; el resto = activo) — **no** con `en_seguimiento_jc` (esa es la alerta operativa,
  no el estado de retiro real, ver `supabase-estructura.md`).
- **`v_pub_emprendimiento` (nueva).** Unifica `v_emprendimiento_situacion` +
  `_por_ciudad` + `_vs_cursos`, mismo patrón de `estado` que arriba. Solo JC tiene datos —
  las filas de MR simplemente no existen (el frontend ya sabe mostrar "no aplica" cuando la
  vista no trae filas para ese programa).
- **`v_pub_asistencia` (nueva, primera vez que esta fuente es pública).** `programa, cohorte,
  estado, grupo_ciudad, promedio, n_estudiantes` desde `asistencia_promedio` (join por email a
  `participants`, mismo patrón que `v_persona_360`) — agregado, sin PII. Verificar con `SET
  ROLE anon` como todas las vistas públicas de esta sesión.
- **Emoflow: reusar el par `_canonico`/original ya existente (migración 011) como las 2
  primeras posiciones del filtro de Estado** (Activos = `_canonico`, Todos = vista original) —
  es exactamente el mismo concepto que ya se resolvió el 2026-07-23, no hace falta una vista
  nueva para eso. Falta decidir en esta misma fase si el 3er estado ("Solo retirados") necesita
  una vista adicional o si se calcula como `original − canonico` en el frontend.
- **Guarda obligatoria (regla ya establecida en `panel-control-jc-mr.md` §7, aplica igual
  aquí):** `test_integridad_supabase.py` completo antes y después, reportar ambos números.
  Verificar con `SET ROLE anon` que cada vista nueva es legible por `anon` (son públicas, a
  diferencia de `v_gui_personas`/`v_persona_360`) y que ninguna expone PII.

### Fase 2 — `lib/api.ts`: tipos y llamadas para las vistas nuevas

Agregar interfaces + llamadas para `v_pub_demografia`, `v_pub_emprendimiento`,
`v_pub_asistencia`. Mantener temporalmente las llamadas viejas (`v_demografia_grupo`, etc.) sin
usarlas desde `page.tsx` hasta confirmar que las nuevas cuadran exacto contra ellas — mismo
principio de verificación cruzada que ya se usó para `v_pub_avance` (encontró una vista
duplicada esta misma sesión, ver `034_vistas_publicas_visualizacion.sql`/`036_fix_v_pub_avance`).

### Fase 3 — `app/page.tsx`: reescritura completa

- **Filtro global "Estado"** (3 botones: Activos/Todos/Retirados) en la barra superior, junto
  a Programa/Cohorte/Ciudad — se propaga a las 6 secciones.
- **Elimina la duplicación de §1.2**: una sola función/hook decide qué vista de cursos mostrar
  (cohorte completa vs. completación), no dos copias en Resumen y Cursos.
- **Demografía unificada** JC/MR en un solo layout, con "no aplica" explícito por tarjeta.
- **Selector de ciudad/municipio unificado** (uno solo, con drill-down integrado — no el
  selector de arriba + la sección "Geografía" aparte como hoy).
- **Tab nuevo "Asistencia"**, mismo patrón visual que Emoflow.
- **Emprendimiento/Emoflow**: mismo tratamiento "no aplica" que Demografía en vez de ocultar
  el tab completo cuando el programa no aplica.

### Fase 4 — Pulido + verificación

`npx tsc --noEmit` + `npm run build` limpios, `npm run dev` para revisión visual de Samuel
(la extensión de Chrome sigue sin conectar en este entorno — mismo límite ya declarado en
`panel-control-jc-mr.md`). Sin `git push` a `comunicaciones/main` hasta confirmación explícita
(deploy Netlify).
