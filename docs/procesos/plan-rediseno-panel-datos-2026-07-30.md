# Rediseño del panel de datos público (desde cero) — especificación

> **Conexiones:** [[00-vision-global]] · [[panel-control-jc-mr]] · [[plan-visualizacion-2026-07-30]] ·
> [[diccionario-metricas]] · [[supabase-estructura]] · [[panel-datos-etl]]
>
> Pedido de Samuel, 2026-07-30 (noche). Igual que con `panel-control-jc-mr.md`: **primero se
> escribe/afina la especificación, después se construye.** Este documento NO es el plan de
> ejecución todavía — es el prompt mejorado que Samuel pidió, más el diagnóstico que lo
> respalda. Falta resolver las preguntas de §4 antes de pasar a un plan de fases ejecutable.
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
- **Asistencia — pendiente de decisión** (ver §4.2). Si se agrega, mismo patrón: agregado sin
  PII vía una vista pública nueva análoga a `v_pub_geografia`.

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

## 3. Lo que esto NO resuelve todavía (a propósito)

Este documento es la especificación, no el plan de fases ni el diseño visual pixel-a-pixel.
Antes de construir falta: (a) decidir las preguntas de §4, (b) un plan de fases al estilo
`panel-control-jc-mr.md` §5, (c) probablemente wireframes o al menos una descripción de layout
más detallada una vez resueltas las preguntas — no tiene sentido diseñar el layout final antes
de saber si Asistencia entra o no, por ejemplo.

---

## 4. Preguntas abiertas — necesito que Samuel elija antes de pasar al plan de fases

1. **¿Reescribir `app/page.tsx` desde cero (mismo repo/stack: Next.js + Tailwind + Recharts) o
   evaluar un stack distinto?** "Desde 0" en el pedido puede significar "una reestructuración
   completa del archivo" (recomendado — el stack ya funciona, el problema es la organización
   de la información, no la tecnología) o "un proyecto aparte". Asumo la primera lectura salvo
   que se diga lo contrario.
2. **¿Se agrega Asistencia Zoom al panel público (hueco real, §1.5) o queda fuera a
   propósito?** Si entra, es una vista pública nueva (agregado sin PII) + un tab nuevo — trabajo
   real, no solo reorganización. Si no entra, aclarar que fue una decisión, no un olvido.
3. **El filtro "Estado" (§2.1.3) — ¿aplica también a Demografía/Emprendimiento/Emoflow, o solo
   a Resumen/Cursos?** Demografía hoy no distingue activos de retirados en sus gráficos (son
   agregados de toda la cohorte con dato sociodemográfico) — extenderle el filtro de estado
   podría no tener sentido si esas vistas de Supabase no lo soportan sin una migración nueva.
4. **Prioridad frente a otros pendientes:** ¿esto va antes o después de la Fase 4-5 de
   `panel-control-jc-mr.md` (ficha 360, CSV, semáforo — la GUI interna)? Ambos son "reconfigurar
   para mejor UX", pero son proyectos separados (uno público sin PII, otro interno con PII) y
   compiten por el mismo tiempo.
