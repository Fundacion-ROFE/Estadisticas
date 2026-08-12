# Panel de Control JC/MR — herramienta interna nueva (histórico completo, PII, fuentes togglables)

> **Conexiones:** [[00-vision-global]] · [[plan-visualizacion-2026-07-30]] ·
> [[panel-riesgo-mejora]] · [[bd-seguimiento-monitorias]] · [[supabase-estructura]]
>
> Pedido de Samuel, 2026-07-30 (sesión de auditoría de geografía JC 2026 — ver
> [[plan-visualizacion-2026-07-30]] §"Bogotá/Medellín"). Decisiones confirmadas por ronda de
> preguntas la misma tarde (ver `claude_sessions.md`). **Documento previo a ejecutar** — a
> pedido explícito de Samuel, esto se escribe ANTES de tocar código.
>
> **Estado (2026-07-30, noche): Fases 1-3 ✅ HECHAS** (ver §5). Verificadas solo parcialmente
> — sin traceback al lanzar la app (un bug real de Tkinter sí se encontró y corrigió así:
> `pady=(10,0)` no es válido en el constructor de un `Frame`, solo en `.pack()`), pero sin
> inspección visual (no hay herramienta de captura para apps de escritorio en este entorno);
> la ventana quedó abierta en el escritorio real para que Samuel la revise. Fases 4-5 sin
> empezar.

---

## 0. Decisiones ya tomadas — no volver a preguntar

| Decisión | Valor confirmado |
|---|---|
| ¿Evolucionar `panel_riesgo_gui.py` o herramienta nueva? | **Herramienta nueva desde cero.** |
| Fuentes que se pueden prender/apagar individualmente | **BD Seguimiento** (sociodemográficos + ciudad + `en_seguimiento_jc`) · **Retiros + Emoflow + Asistencia Zoom** · **Postulantes históricos (Mongo) + Microcréditos MR** |
| Fuente base (siempre visible, no togglable) | **Q10/Supabase** (`participants`+`enrollments`+`courses`) |
| Alcance histórico | **Todas las cohortes disponibles**: 2023-2026 (JC), 2025-2026 (MR) |

**Heredado sin objeción de `panel-riesgo-mejora.md` (decisión de Samuel, 2026-07-21) — sigue
vigente salvo que se diga lo contrario:** Tkinter/escritorio, **no web** (evita exponer PII a
internet y no requiere autenticación nueva); `service_role`, solo lectura, nunca escribe en
Supabase. Si esta sesión implica lo contrario (ej. querer acceso remoto), confirmarlo
explícitamente antes de cambiar de stack — es una decisión de arquitectura ya tomada una vez,
con motivo documentado.

---

## 1. Relación con planes existentes — para no duplicar trabajo

- **Supersede a `docs/procesos/panel-riesgo-mejora.md`.** Su Fase 1 (migrar
  `panel_riesgo_gui.py` de Sheets a Supabase) ya está hecha (2026-07-21) y se hereda tal cual.
  Sus Fases 2-3 (tab "Decisiones" con botones curados, ficha ampliada, semáforo) quedan
  **absorbidas en este documento** — mismos conceptos, herramienta distinta. Ese archivo se
  marca como archivado/fusionado (ver nota al final del archivo).
- **`plan-visualizacion-2026-07-30.md` Fase 2 (mejoras incrementales sobre
  `panel_riesgo_gui.py`) queda PAUSADA.** No tiene sentido seguir invirtiendo en la GUI vieja en
  paralelo a construir la nueva — se anota ahí mismo.
- **Se reusa, no se reescribe — y no se extiende (corrección tras revisión, ver §4):**
  - `v_gui_personas` (migración 033, 2026-07-30) — vista PII por persona×programa×cohorte, se
    consume **tal cual**, sin agregarle columnas nuevas.
  - `v_persona_360` (migración 008) — ficha individual por cédula, existe desde 2026-07-23
    **sin consumidor todavía**. Se consume **tal cual** para la ficha de doble-clic (§5 Fase 4)
    y para las columnas de Asistencia Zoom/Postulantes históricos (§4) — no se le agrega nada.
  - Patrones `Supa`/`get_todo`/`_cargar_env_local` ya extraídos en `tools/panel_riesgo_datos.py`
    — reusar esas funciones (o el archivo completo como base), nunca reescribir el paginador
    (ver `convenciones.md`, gotcha ya documentado 2 veces).
  - `TablaFiltrable` (componente Tkinter de `panel_riesgo_gui.py`: búsqueda + filtro por
    columna + ordenamiento + exportar CSV) — reusar el componente tal cual, es independiente de
    la fuente de datos.

---

## 2. Qué es (visión)

Una tabla de personas filtrable que cubre **todas las cohortes** de JC y MR, donde el usuario
decide qué fuentes de información quiere ver activas — las columnas de la tabla y las
estadísticas de cabecera se recalculan según esa selección. Responde preguntas del tipo "de
los matriculados en 2024, ¿quiénes tienen retiro registrado Y no tienen Emoflow?" sin que nadie
tenga que escribir SQL.

**Componentes de la interfaz:**
1. Selector de programa (JC / MR).
2. Selector de cohorte — **todas las disponibles**, no solo la actual (2023, 2024, 2025, 2026
   para JC; 2025, 2026 para MR).
3. Panel de fuentes con checkboxes on/off (ver §3) — Q10 siempre marcado y deshabilitado
   (no se puede apagar la fuente base).
4. Filtros combinables: ciudad/`grupo_ciudad`, rango de avance, estado (activo/retirado).
5. Tabla principal (`TablaFiltrable`) — columnas dinámicas según fuentes activas.
6. Doble clic en una fila → ficha 360 (`v_persona_360`).
7. Exportar CSV de la vista actual (mismo patrón ya existente).

---

## 3. Fuentes y su rol

| Fuente | Togglable | Grano | Objeto Supabase | Nota de cobertura/gotcha |
|---|---|---|---|---|
| Q10 / Supabase | **No — base** | persona × programa × cohorte | `participants`+`enrollments`+`courses` | Siempre visible. Define el universo de filas (ver §6). |
| BD Seguimiento | Sí | persona | `participants.ciudad`/`grupo_ciudad`/`estrato`/`en_seguimiento_jc` | **Cobertura parcial documentada hoy** (auditoría 2026-07-30): hub cities JC ~30-48%, satélites (Envigado/Sabaneta/Itagüí) 0%. MR: prácticamente completo (BD-Mujeres ROFÉ). Mostrar "sin dato", nunca 0%/vacío. |
| Retiros | Sí | persona × programa × cohorte | `retiros` | MR: `cohorte` de la fila no es confiable (motivo lo dice explícito) — usar `retiro_cohorte_registrado` de `v_gui_personas`, no la cohorte de la fila directamente. |
| Emoflow | Sí | persona | `emoflow_ingresos` | **Solo JC** — 0 en MR (no desplegado, no es "0% de uso"). |
| Asistencia Zoom | Sí | persona | `asistencia_promedio`, vía `v_persona_360` (§4) | Cobertura parcial, PII. |
| Postulantes históricos | Sí | persona (universo **más amplio** que matriculados) | `postulantes_jc`/`postulantes_mr`, vía `v_persona_360` en estado 1; tabla directa en estado 2 (§4, §6) | Incluye gente que **nunca matriculó** — ver el modelo de 3 estados, confirmado en §6. |
| Microcréditos MR | Sí | persona | `mr_microcreditos`, vía `v_gui_personas` | Solo MR, no es empresa patrocinadora (ver `postulantes-mr-supabase.md`). |

---

## 4. Arquitectura de datos propuesta

**Revisado (2026-07-30, corrección tras feedback de Samuel): NO hace falta extender
`v_gui_personas`.** El diseño original de este documento proponía agregarle
`asistencia_promedio` y `postulantes_jc`/`postulantes_mr` — pero **`v_persona_360`
(migración 008) ya tiene esas dos exactas** (`asistencia_promedio`, `asistencia_n_registros`,
`nombre_postulante_mr`/`jc`, `fuente_mr`/`jc`, `rol_jc`, `estado_mr`, `celular_mr`/`jc`) desde
2026-07-23. Agregarlas también a `v_gui_personas` habría sido **duplicar la misma lógica de
cruce por cédula/email en dos vistas** — exactamente lo que el punto (f) de la corrección de
Samuel pide evitar. Ver §6.1 para el detalle de por qué ninguna de las dos vistas sobra: cubren
grano distinto (persona×programa×cohorte vs. persona única con historial agregado).

**Reparto final de fuentes entre las dos vistas — cero SQL nuevo para la Fase 1:**

| Fuente togglable | De dónde sale | ¿Ya existe? |
|---|---|---|
| BD Seguimiento (sociodemográficos + ciudad + `en_seguimiento_jc`) | `v_gui_personas` | ✅ ya está (migración 033) |
| Retiros | `v_gui_personas` (`fecha_retiro`/`motivo_retiro`/`retirado`) | ✅ ya está |
| Emoflow | `v_gui_personas` (`emoflow_ingresos`/`emoflow_ultimo_ingreso`) | ✅ ya está |
| Microcréditos MR | `v_gui_personas` (`tiene_microcredito`/`microcredito_tipos`) | ✅ ya está |
| Asistencia Zoom | `v_persona_360` (`asistencia_promedio`, `asistencia_n_registros`) | ✅ ya está, sin cambios |
| Postulantes históricos | `v_persona_360` (`nombre_postulante_*`, `fuente_*`, `rol_jc`/`estado_mr`, `celular_*`) | ✅ ya está, sin cambios |

**El toggle de fuentes es de PRESENTACIÓN en el cliente Python, no de query SQL.** La capa de
datos hace 2 consultas por (programa, cohorte) — una a `v_gui_personas` (grano
persona×programa×cohorte, siempre) y una a `v_persona_360` filtrada por las cédulas visibles
(grano persona única, solo si algún toggle de Asistencia/Postulantes está prendido) — y las
mergea en memoria por cédula. Los checkboxes solo deciden qué columnas ya descargadas se
muestran. Ventajas:
- Prender/apagar una fuente ya descargada es instantáneo — no dispara un nuevo fetch.
- Cero migraciones nuevas para la Fase 1 → nada que reverificar contra
  `test_integridad_supabase.py` esta vez (ver §7 para la regla que sí aplica a cambios futuros).
- Ninguna lógica de cruce por cédula/email se reescribe — las dos vistas ya la resuelven.

---

## 5. Plan de fases

### Fase 1 — Capa de datos Python (sin SQL nuevo) — ✅ HECHO 2026-07-30

`tools/panel_control_datos.py` (nuevo, gitignoreado): `leer_personas_todas_cohortes(supa,
programa)` (todas las cohortes de `v_gui_personas` de una sola serie de llamadas paginadas) +
`leer_persona_360_por_cedulas(supa, cedulas)` (lotes de 400 cédulas, nunca una llamada por
persona) + `leer_panel_control(programa)` que las mergea en memoria por cédula. Reusa
`Supa`/`get_todo`/`conectar_supabase` de `panel_riesgo_datos.py` — no se reescribió el
paginador. **Cero migraciones de Supabase**, como decía §4.

**Verificado con datos reales** (`tools/verificar_panel_control_datos.py`, sin imprimir PII —
solo conteos agregados):

| | JC | MR |
|---|---|---|
| Filas totales (persona×cohorte) | 2.316 | 1.363 |
| Cohortes | 2023 (336) · 2024 (470) · 2025 (733) · 2026 (777) | 2025 (1.254) · 2026 (109) |
| Asistencia Zoom con dato | 456/2.316 (19,7%) | 1/1.363 (0,1%) |
| Postulantes históricos con dato | 2.094/2.316 (90,4%, `postulantes_jc`) | 465/1.363 (34,1%, `postulantes_mr`) |

JC 2026 = 777 coincide exacto con el universo ya conocido. Confirmado contra una llamada REST
sin paginar que el total de filas y la distribución por cohorte de `v_gui_personas` se leen
completos (get_todo pagina correctamente más allá del límite de 1.000 filas de PostgREST).

**Observación, no un bug de esta fase:** la distribución MR 2025/2026 (1.254/109) es distinta
a la medida esta mañana al construir `v_gui_personas` (1.016/347) — el total (1.363) es
idéntico en ambas medidas, así que no se perdieron ni se agregaron filas, solo cambió la
etiqueta de cohorte de ~238 filas entre una medición y otra. Encaja con el patrón ya
documentado de "rename o cierre de curso = fila duplicada, no un update" (`convenciones.md`) —
`courses.cohorte` para MR ya tenía duplicados Title-Case/MAYÚSCULAS con cohorte `2025` vs
`2026` para el mismo curso real (visto al auditar `v_aprobacion_cursos_vigencia`). No se
investigó a fondo porque está fuera de alcance de la Fase 1 (leer las vistas tal cual, no
depurar la fuente) — si se quiere cerrar, es trabajo de `courses`/`cursos_alias`, no de este
módulo.

### Fase 2 — Interfaz: selector + toggles + tabla base (estado 1 del toggle, ver §6) — ✅ HECHO 2026-07-30

`tools/panel_control_gui.py` (nuevo, gitignoreado). Reusa la paleta y `TablaFiltrable` de
`panel_riesgo_gui.py` por import directo (cero código copiado) y toda la capa de datos de la
Fase 1 (`panel_control_datos.leer_panel_control`).

- **Selector de programa** (JC/MR, radiobuttons) + **selector de cohorte** (dinámico, todas
  las cohortes presentes en los datos cargados de ese programa — 2023-2026 JC, 2025-2026 MR).
- **3 checkboxes de fuentes** (BD Seguimiento · Retiros+Emoflow+Asistencia ·
  Postulantes históricos+Microcréditos MR) + "Q10 (base)" siempre marcado y deshabilitado.
  Reparto de columnas por grupo documentado en el propio código (`COLUMNAS_BASE`,
  `TOGGLE_BD_SEGUIMIENTO`, etc.) — city/grupo_ciudad y el flag `retirado` quedan en la base
  (se usan como filtro con o sin el toggle prendido); el detalle sociodemográfico/de retiro
  vive en los toggles.
- **Filtros combinables:** ciudad/grupo (dropdown dinámico según lo cargado), banda de avance
  (Todos / En riesgo 0-25% / En progreso 26-80% / Al día >80% — mismas bandas ya establecidas
  en el proyecto, no se inventó ninguna nueva), estado (Todos/Activos/Retirados).
- **Estadísticas de cabecera** recalculadas sobre el conjunto filtrado: personas, avance
  promedio, % al día, % retirados. **KPI "En Seguimiento (activos)" (2026-08-11):** cuenta
  `en_seguimiento_jc = true` — el conteo de "activo" canónico en JC (751 para 2026), alineado con
  el panel público (ver [[convenciones]] "activo JC = Seguimiento" y
  [[plan-coherencia-cohortes-2026-08-11]]). Solo aparece cuando la cohorte tiene el dato (JC viva);
  en históricas/MR `en_seguimiento_jc` es None y un "0" engañaría. Complementa (no reemplaza) al KPI
  "Retirados" que sigue derivando del flag Q10 — la disparidad entre ambos vive en la pestaña
  "Datos desactualizados Q10".
- Al prender/apagar un toggle, `TablaFiltrable` se **destruye y recrea** con el nuevo set de
  columnas (el componente fija sus columnas en el constructor; se reusa tal cual, sin
  modificarlo, tal como pedía §1).
- Toggle de "Postulantes históricos" en **estado 1 confirmado**: solo agrega columnas
  (`Postulante JC`/`Postulante MR`/`Rol/fuente JC`/`Estado MR`/`Microcrédito`) a las filas de
  matriculados que ya trajo la Fase 1 — cero filas nuevas.
- Reglas de "sin dato" aplicadas (`_sin_dato()`/`_si_no()`): ninguna columna muestra 0%/vacío
  cuando la fuente no tiene cobertura para esa persona.

**Verificación — parcial, con una limitación honesta que hay que decir:** el módulo importa
limpio (`python -c "import panel_control_gui"`, sin lanzar la GUI) y la app se lanzó en
segundo plano sin ningún traceback en 9+ segundos (tiempo de sobra para que el hilo de datos
termine — la misma llamada a Supabase ya tardó unos segundos en la verificación de la Fase 1).
**No se pudo verificar visualmente la ventana ni las interacciones** (clicks en toggles,
combos, etc.) — no hay herramienta de captura/computer-use para apps de escritorio nativas de
Windows en este entorno (solo hay automatización de navegador). La ventana quedó abierta en el
escritorio real de Samuel al terminar esta fase — pendiente que la revise él mismo antes de
darla por buena del todo.

### Fase 3 — Modo aparte "Postulantes que nunca matricularon" (estado 2 del toggle, ver §6) — ✅ HECHO 2026-07-30

`panel_control_datos.leer_postulantes_sin_matricula(programa, supa)` (nuevo): consulta
`postulantes_jc`/`postulantes_mr` directo con `participant_id=is.null&select=*` — nunca llama
ni se mergea con `leer_panel_control()`. **Reverificado en vivo antes de tocar código** (no se
copió el número del documento, como pedía esta misma sección): **462 JC / 4.757 MR** — igual
a la medición de la corrección de ayer, estable.

En la interfaz: `panel_control_gui.py` ahora tiene un `ttk.Notebook` con **2 pestañas que
nunca se muestran juntas** — "Matriculados" (Fase 2) y "Postulantes sin matrícula" (esta
fase). La segunda pestaña tiene su propio contador (`_kpi` en naranja, para diferenciarla
visualmente de la pestaña de matriculados), su propia tabla (`TablaFiltrable` con columnas
propias por programa — `postulantes_jc`/`postulantes_mr` no comparten esquema) y una nota
explícita en la parte superior recordando que es un universo distinto. Sin toggles ni filtro
de cohorte (ese universo no tiene cohorte asignada) — solo la búsqueda/orden que ya trae
`TablaFiltrable` gratis.

**Bug real encontrado y corregido al lanzar la app (no solo al importar el módulo):**
`tk.Frame(..., pady=(10, 0))` — una tupla de padding es válida en `.pack()`/`.grid()` pero
**no** en el constructor del widget (`_tkinter.TclError: bad screen distance "10 0"`). Fix:
mover el padding vertical al `.pack()`. Este es exactamente el tipo de error que
`import panel_control_gui` (sin lanzar la GUI) no detecta — reforzó la necesidad de lanzar la
app de verdad, no solo importarla, como paso de verificación mínimo en este entorno sin
captura visual.

### Fase 4 — Ficha 360
Doble clic sobre una fila de matriculados → popup que consulta `v_persona_360` por cédula.
Primer consumidor real de esa vista desde que se creó (2026-07-23). El modo "postulantes que
nunca matricularon" (Fase 3) no tiene ficha 360 con este mismo popup — esas personas no tienen
matrícula/avance/cursos que mostrar; si se quiere detalle ahí, es una ficha más simple aparte
(fuera de alcance por ahora).

### Fase 5 — Pulido
Exportar CSV (ya existe el patrón), semáforo visual con umbrales ya definidos en el proyecto
(no inventar umbrales nuevos — reusar 70% asistencia, banda 0-25 avance, etc.).

---

## 6. ✅ CONFIRMADO (2026-07-30) — "Postulantes históricos" son 3 estados, no 2

Corrección de Samuel sobre la primera versión de este documento: no son dos opciones
mutuamente excluyentes, son **tres estados**, y el tercero es la regla que no se puede violar.

**Estado 1 — Default, y lo que hace el toggle "Postulantes históricos" al prenderse:**
Solo agrega **columnas** (fecha/rol/fuente de postulación) a las personas que ya están en la
tabla de matriculados. **Cero filas nuevas.** Universo base = matriculados, igual que en todo
el resto del proyecto (`convenciones.md`: *"Supabase `participants` = solo matriculados en
Q10, nunca crear desde fuentes secundarias"*).

**Razón medida en vivo (2026-07-30, vía REST directo — MCP de Supabase estaba desconectado en
el momento de escribir esto):** `postulantes_jc` tiene **462** filas con `participant_id IS
NULL` (2.556 total) y `postulantes_mr` tiene **4.757** (5.310 total). *(Samuel había medido
452/4.588 esa misma mañana — la diferencia de 10 y 169 es esperable entre dos medidas del
mismo día con syncs corriendo cada 2h; **usar siempre el número medido en el momento de
construir la Fase 3**, no el de este documento.)* Si esas filas entraran a la tabla principal,
MR quedaría con ~13× más postulantes que estudiantes (4.757 vs 338 activas) y ningún conteo en
pantalla volvería a significar "estudiantes" sin una aclaración constante — el mismo problema
de fondo que ya se resolvió con `en_seguimiento_jc`: una alerta operativa no puede filtrarse
silenciosamente hacia adentro de un número canónico.

**Estado 2 — Modo aparte y explícito: "Postulantes que nunca matricularon".**
Vista/pestaña separada, con su propio contador visible y su propio encabezado (ej. *"452 JC ·
4.588 MR postulantes sin matrícula"* — reverificado al construirla). **Ahí sí son filas**,
porque en ese modo esa es la unidad de análisis real. Nunca sumado al total de estudiantes,
nunca mezclado en la misma grilla que el estado 1.

**Estado 3 — Lo que no puede existir: ningún estado intermedio que mezcle ambos universos en
una sola cifra.** No hay un "modo combinado" ni un total que sume matriculados + postulantes
sin matrícula bajo una sola etiqueta. Si en el futuro alguien pide eso, es una señal de que la
pregunta real es otra (probablemente "tasa de conversión postulante → matriculado", que se
responde con dos números divididos, no con uno sumado).

### 6.1 Por qué `v_persona_360` y `v_gui_personas` coexisten sin duplicar lógica

`v_persona_360` ya resuelve la trazabilidad cruzada por cédula/email entre `participants`,
`postulantes_mr`, `postulantes_jc`, `emoflow_ingresos` y `asistencia_promedio` — desde
2026-07-23, sin consumidor hasta este plan. Este documento la reusa tal cual (§4, §5 Fase 1) en
vez de reimplementar esos mismos cruces dentro de `v_gui_personas` o del panel. Las dos vistas
no compiten porque su grano es distinto y complementario:

| | `v_gui_personas` | `v_persona_360` |
|---|---|---|
| Grano | persona × **programa × cohorte** | persona única (agrega todas las cohortes) |
| Para qué sirve aquí | la **tabla principal**, filtrable por cohorte | la **ficha de detalle** (Fase 4) y las columnas de Asistencia/Postulantes que se mergean en memoria (Fase 1) |
| Creada | 2026-07-30 (migración 033, esta misma sesión) | 2026-07-23 (migración 008) |

Ninguna reemplaza a la otra. El estado 2 de §6 (postulantes sin matrícula) **no usa ninguna de
las dos** — consulta `postulantes_jc`/`postulantes_mr` directo, porque ninguna vista existente
tiene ese universo (ambas están ancladas a `participants`/matriculados).

---

## 7. Regla dura para cualquier extensión futura de vistas con PII

Si en cualquier fase futura resulta necesario agregar una columna a `v_gui_personas`,
`v_persona_360` o crear una vista nueva con PII: correr `test_integridad_supabase.py` completo
**antes** de tocar nada (baseline) y **después** de aplicar el cambio, y reportar ambos
números. La columna nueva no puede ampliar la superficie visible para `anon`/`authenticated`
(verificar con `SET ROLE anon`, no solo `information_schema` — ver el gotcha ya documentado en
`convenciones.md` sobre `security_invoker`). Baseline verificado hoy antes de escribir esta
sección: **53/53 PASS**.

---

## 7.5 Extensión 2026-08-03 — universo canónico 832 + exportar CSV

Pedido de Lina en preparación de una reunión de equipo: el panel mostraba 777 para JC/2026
(universo de matrícula) en vez de los **832 "ingresados" canónicos**
([[diccionario-metricas]]). Verificado en vivo: el hueco de 55 no era un bug de la vista —
esas 55 personas (Q10 las marca inhabilitadas) **nunca tuvieron fila en `participants`**
porque nunca tuvieron una matrícula activa sincronizada.

**Cambios:**
- `export_aprobacion.py` ahora captura también el nombre por cédula (columna "Estudiante"
  del reporte Detallado) y lo persiste en `tools/cohorte_2026.json` junto a cohorte/retirados.
- Tabla nueva **`cohorte_2026_ceds`** (migración 038): cédula × programa × cohorte × nombre ×
  retirado — el canon Q10 completo (832 JC / 346 MR), poblada por
  `scripts/panel-datos/sync_cohorte_2026.py`, que además inserta en `participants` las
  cédulas sin fila (55 nuevas, con nombre).
- **`v_gui_personas` reescrita (migración 039):** su universo ahora es
  `enrollments` (como antes) **UNION** `cohorte_2026_ceds` sin matrícula para esa
  cohorte — cursos/avance quedan `NULL` ("sin dato", nunca 0) para esas 55.
- **`retirado` en la vista:** JC usa el flag de `cohorte_2026_ceds` (canon Q10) cuando existe
  fila para esa cohorte; si no, cae al flag de `retiros` (Sheets) de siempre.
  **MR queda excluida a propósito** — ver gotcha abajo.

**Gotcha real (encontrado al verificar, corregido antes de dejarlo así):** la primera versión
aplicó el canon Q10 a JC *y a MR por igual*, y `mr/2026` saltó de 0 a **167** "retiradas". Eso
contradice una decisión ya confirmada por Lina (2026-07-29, ver [[00-vision-global]]): en MR,
Q10 inhabilita **todas** las matrículas al cerrar un curso del programa — "inhabilitada" no
significa retiro real. La única baja real de MR es la pestaña Inactivas (`retiros`,
`fuente='inactivas_mr'`, hoy 8). Se corrigió con un `CASE WHEN programa='jc'` antes de dejar
la vista aplicada — MR sigue usando exclusivamente `retiros`, igual que en la migración 033
original.

**Verificado tras aplicar:** conteos por programa×cohorte sin cambios fuera de jc/2026 (jc
2023/2024/2025 y mr 2025/2026 idénticos a antes); jc/2026 = 832 (antes 777), 83 retirados, 55
con cursos/avance en `NULL`; `panel_control_datos.leer_panel_control('jc')` confirma las
mismas cifras end-to-end (la GUI ya renderiza `None` como "sin dato"/"—", cero cambios de
código ahí). Suite `test_integridad_supabase.py`: **53/53 PASS** (incluye `anon bloqueado en
v_gui_personas`).

**Además:** botón "📥 Exportar CSV" agregado a `panel_control_gui.py` (mismo patrón que
`panel_riesgo_gui.py` — exporta la pestaña activa con los filtros de programa/cohorte/
ciudad/avance/estado ya aplicados, no el universo completo cacheado).

Ver [[q10-consolidacion]] (export_aprobacion.py) y `docs/migrations/038_cohorte_2026_ceds.sql`
/ `039_v_gui_personas_universo_canonico.sql` para el detalle técnico completo.

---

## 7.6 Extensión 2026-08-06 — toggle "Mostrar staff" + ciudad JC 2025 + fix de PII

Al auditar si el panel reflejaba correctamente el cierre de JC 2025 ([[validacion-cohortes]])
y el trabajo de [[demografia-historica-jc]], salieron dos huecos reales verificados en vivo
contra `v_gui_personas`:

1. **Las 14 cuentas de staff/mentores/aliados de JC 2025** (mismo hallazgo que
   `validacion-cohortes.md`) aparecían en el panel como estudiantes activos normales —
   `retirado=False`, con cursos/avance reales (Q10 no distingue rol al exportar). Inflaban
   cualquier conteo de "activos" o promedio de avance calculado desde el panel para esa
   cohorte, sin ninguna señal visual de que no eran estudiantes.
2. **`grupo_ciudad`/`municipio` casi vacíos en JC 2025** (732/733 sin dato) — el filtro de
   ciudad del panel no servía de nada para esa cohorte específica. No era un bug de la vista:
   simplemente nunca se había cargado ese dato (el trabajo de demografía de agosto cargó
   estrato/edad/género/vivienda/nivel_estudio, nunca ciudad).

**Fix 1 — toggle "Mostrar staff":**
- `tools/panel_control_datos.py`: `leer_panel_control()` ahora etiqueta cada fila con
  `es_staff` (bool), cruzando por cédula contra `tools/cohorte-2025-jc/staff_excluidos.json`
  (lista de rutas en `_RUTAS_STAFF_EXCLUIR`, pensada para agregar archivos hermanos si
  aparecen casos en otras cohortes/programas).
- `tools/panel_control_gui.py`: checkbox "Mostrar staff" (naranja, junto al filtro de
  ciudad) — **off por defecto**. `_aplicar_filtros()` descarta filas `es_staff=True` antes de
  llegar a la tabla Y a los KPIs de cabecera (mismo paso, así que prender el toggle también
  los suma a las estadísticas automáticamente, sin código aparte). Columna nueva "Staff"
  (Sí/No) en `COLUMNAS_BASE` para que se vea cuál es cuál cuando el toggle está prendido.
- Verificado end-to-end (`leer_panel_control('jc')` real, sin mock): 733 filas jc/2025,
  14 `es_staff=True`, 719 `False` — coincide exacto con el hallazgo original.

**Fix 2 — ciudad JC 2025:** `scripts/panel-datos/cargar_ciudad_2025_jc.py` (nuevo) — cruza
`oficial_559_aprobados.csv` + `oficial_163_retirados.csv` (ya tienen `ciudad_codigo` limpio,
mismo formato que `grupo_ciudad` — más simple que parsear el texto libre de los formularios
Fase 1) contra el roster, llena solo `NULL`s. **Resultado: grupo_ciudad 0.1%→98.2% (720/733),
municipio →95.2% (698/733)** — timeout SSL transitorio a mitad de la primera corrida (346/719
ya aplicadas), resuelto re-corriendo (idempotente, solo quedaban los 373 restantes).

**Fix 3 — corrección de privacidad real:** las 14 cédulas+nombres de staff estaban
hardcodeadas directo en `scripts/panel-datos/marcar_aprobados_2025_jc.py`, un script **que sí
se sube a git** — viola la regla del proyecto ("PII nunca a GitHub", `CLAUDE.md`). Movidas a
`tools/cohorte-2025-jc/staff_excluidos.json` (gitignoreado, mismo archivo que ahora usa
también el panel); el script quedó leyendo de ahí con un loader que avisa (no revienta) si el
archivo no aparece.

**Verificación:** `import panel_control_datos`/`import panel_control_gui` limpios; app
lanzada de verdad (no solo importada — mismo criterio que el bug de `pady` en Fase 3) sin
traceback en el log. Sin inspección visual (misma limitación de siempre en este entorno) —
ventana abierta en el escritorio real para revisión.

## 7.7 Extensión 2026-08-06 (mismo día) — caché en disco 24h + botón "Forzar actualización"

Pedido explícito de Samuel: limitar las consultas a Supabase de esta app a ~1x/día (no era el
mayor consumidor de egress del proyecto — eso vive en los cron de n8n, ver
[[panel-datos-etl#Optimización de egress]] — pero es gratis implementarlo y reduce el impacto
de abrir/cerrar la app varias veces el mismo día).

- `panel_control_datos.py`: `cargar_cache_si_vigente(programa, ttl_horas=24)` /
  `guardar_cache(programa, filas, sin_matricula)` — JSON en `tools/cache/panel_control_
  <programa>.json` (gitignoreado, ya cubierto por la regla `tools/` del `.gitignore`).
  Degrada limpio (vuelve a consultar Supabase) si el archivo no existe, está vencido, o está
  corrupto — nunca revienta la carga por un caché roto.
- **Prioridad de carga:** caché en memoria de la sesión (instantáneo) → caché en disco
  <24h (evita ir a Supabase si ya se abrió la app hoy) → Supabase en vivo (y guarda el
  resultado en el caché de disco para la próxima).
- **Botón nuevo "🔄 Forzar actualización"** (rojo, junto a "Cargar"): salta las dos capas de
  caché a propósito. Necesario porque un día de correcciones activas (como este mismo
  2026-08-06 — sellado de JC 2025, fix de email, ciudad, staff) necesita ver el cambio
  YA, no esperar a que venza el caché de 24h.
- La barra de estado ahora muestra el origen del dato y la hora exacta ("datos de caché
  (2026-08-06 11:35, hasta 24h de antigüedad, usa 'Forzar actualización'...)" vs "consultado a
  Supabase ahora (...)").
- **Verificado real, no solo por código:** app relanzada, caché generado en disco
  (`tools/cache/panel_control_jc.json`, 2.523 filas jc) tras la primera carga; una lectura
  posterior de `cargar_cache_si_vigente('jc')` devolvió los mismos datos en ~1s sin ninguna
  llamada de red (confirmado que no hay tráfico a Supabase en esa ruta).

## 7.8 Extensión 2026-08-06 (mismo día) — toggles dinámicos por disponibilidad real de datos

Pedido de Samuel, con una premisa a corregir de paso: creía que "BD Seguimiento" (el toggle
que agrupa Estrato/Estado civil/Nivel estudio/Vivienda/En seguimiento/Empresa patroc.) era
relevante solo para 2026. **Falso para 4 de esas 6 columnas** — revisando
`sync_sociodemograficos.py` en código real: ese script (el Sheet en vivo) solo escribe
`en_seguimiento_jc` (a propósito solo cohorte actual — aplicarlo a histórico marcaría como
"alerta de retiro" a egresados normales) y `empresa_patrocinadora`. **Estrato/estado
civil/nivel estudio/vivienda NO vienen de ese Sheet en absoluto** — vienen del trabajo de
[[demografia-historica-jc]] (Mongo, archivo maestro, formularios Fase 1), que sí cargó datos
reales para las 4 cohortes (66-99%). Esconder el toggle completo fuera de 2026 habría ocultado
datos reales que se cargaron el mismo día.

**Fix implementado — data-driven, no por nombre de cohorte:** `_actualizar_disponibilidad_
filtros()` en `panel_control_gui.py` revisa, para las filas de la cohorte×programa
seleccionada, si CUALQUIER columna detrás de cada toggle (`GRUPOS_TOGGLE_CLAVES`, claves
crudas — no las lambdas ya formateadas a "sin dato") tiene algún valor real. Si no, el
checkbox se deshabilita (y se apaga solo si estaba prendido, para no dejar una tabla con
columnas 100% vacías). Mismo criterio para "Mostrar staff" (`es_staff` — efectivamente solo
tiene efecto en cohorte 2025, ahí sí la premisa de Samuel era correcta). Se recalcula en cada
cambio de cohorte/programa, dentro de `_refrescar_tabla()`.

**Aclarado de paso (pregunta real de Samuel, no solo la premisa del toggle):** los checkboxes
de "Fuentes" NUNCA filtran filas, solo muestran/ocultan columnas — por eso prender "BD
Seguimiento" nunca cambia los KPIs de cabecera, en ninguna cohorte, por diseño (ver §4). Y el
754 de `cohorte_ingresos.activos` vs el 756 de "Al día" en el panel no deberían coincidir: son
métricas distintas (activos = no retirado; al día = avance>80%), no la misma cifra medida dos
veces.

**Verificado:** módulo importa limpio; app relanzada en primer plano (foreground, 8s sin
traceback — el intento anterior en segundo plano dio un falso positivo de crash por cómo esta
shell maneja `&`/redirección, no por la app) y usó el caché de disco de la corrida anterior
(sin volver a golpear Supabase, confirmando además que el caché del §7.7 sigue funcionando
junto con este cambio).

## 7.9 Extensión 2026-08-06 (mismo día) — pestaña "⚠ Datos desactualizados Q10"

Pedido de Samuel: agilizar el proceso de actualización en Q10 identificando rápido los casos
donde Q10 y el Sheet "Seguimiento" (`https://docs.google.com/spreadsheets/d/1ggzoJeZR...`,
mismo Sheet que lee `sync_sociodemograficos.py`) no coinciden — Administración actualiza ese
Sheet en tiempo real, Q10 depende de actualización manual con demora reportada. Contexto de
Samuel confirmado correcto contra el código real: el propio docstring de
`sync_sociodemograficos.py` ya documentaba exactamente ese mecanismo antes de este pedido.

**Medido en vivo antes de construir nada (no se asumió el resultado):** de las dos direcciones
posibles de disparidad, la que Samuel esperaba (Q10 atrasado, sin marcar un retiro que
Seguimiento ya confirmó) dio **0 casos ahora mismo** — Q10 está al día en esa dirección. Pero
apareció la dirección contraria, no anticipada: **5 casos donde Q10 ya marcó retiro y
Seguimiento sigue mostrando a la persona activa** (posible error de Q10, o alguien que se
pausó y volvió sin corrección). Se decidió cubrir ambas direcciones, no solo la esperada.

**Implementación (cero SQL/migraciones nuevas — deriva de columnas que `v_gui_personas` ya
trae):**
- `panel_control_datos.filtrar_desactualizados_q10(filas)`: compara `en_seguimiento_jc`
  (Seguimiento) contra `not retirado` (derivado de Q10) sobre las filas YA cargadas por
  `leer_panel_control()` — sin consulta nueva a Supabase. Solo puede haber disparidad donde
  `en_seguimiento_jc` no es `None`, lo que limita el resultado a JC cohorte viva por diseño
  de origen (`sync_sociodemograficos.py` solo lo calcula para el año en curso) — sin
  hardcodear programa/año en este módulo.
- Pestaña nueva en el `Notebook` (3ª, junto a "Matriculados"/"Postulantes sin matrícula"):
  tabla con cédula/nombre/cohorte/tipo de disparidad/ambos flags/fecha de verificación/
  avance/municipio + 2 KPIs ("Q10 sin marcar retiro" en rojo, "Q10 marcó retiro de más" en
  naranja). Se recalcula cada vez que se recarga "Matriculados" (Cargar/Forzar) — no tiene
  botón propio, mismo patrón que "Postulantes sin matrícula". Exportar CSV ya la reconoce.

**Verificado:** `filtrar_desactualizados_q10()` corrido contra el caché real de disco dio
5/5 "Q10 marcó retiro de más" — coincide exacto con la consulta directa a Supabase hecha
antes de programar nada. App relanzada en primer plano, sin traceback.

## 7.10 Extensión 2026-08-06 (mismo día) — filtro real "En Seguimiento" (Sí/No/Todos)

Samuel esperaba que el checkbox "BD Seguimiento" (columnas) redujera las filas al prenderlo —
confusión ya explicada una vez (§7.6/§7.8: esos 3 checkboxes de "Fuentes" NUNCA filtran, solo
muestran/ocultan columnas, por diseño) pero volvió a aparecer, así que se agregó lo que
realmente faltaba: un **filtro de verdad**, `En Seguimiento: Todos/Sí/No`, junto a "Estado" en
la barra de filtros — reduce filas de verdad, igual que Ciudad/Avance/Estado. Mismo criterio
de disponibilidad dinámica que el resto (§7.8): combo deshabilitado y forzado a "Todos" si la
cohorte seleccionada no tiene ningún dato de `en_seguimiento_jc` (todo excepto JC cohorte
viva).

**Verificado contra datos reales (caché de disco, mismos números que la consulta directa a
Supabase hecha antes de programar):** cohorte 2026/jc = 832 personas, filtro "Sí" → 754,
filtro "No" → 23. Coincide exacto con lo medido en vivo — no se reprodujo ninguna disparidad
de "2 personas de más" con este filtro; queda pendiente que Samuel confirme con el nuevo
filtro delante si el conteo que él tenía en mente sigue sin cuadrar (posible causa si persiste:
comparar contra un conteo manual del Sheet en un momento distinto al de la sincronización, o
estar comparando contra una columna/pestaña distinta a "Seguimiento").

## 7.11 Extensión 2026-08-06 (mismo día) — "BD Seguimiento" ahora también filtra en la cohorte viva

Cierre de la duda de los "2 estudiantes de más" (§7.10): con el filtro nuevo delante, Samuel
reconcilió los números él mismo — **749 activos (Q10) + 5 (Q10 marcó retiro, Seguimiento aún
los muestra) = 754 exacto**. Confirma además que esos 5 SÍ están bien marcados como retirados
en Q10 (no es un error de Q10) — quedan ahí solo porque Administración no los ha quitado
todavía del Sheet, no porque Q10 se haya equivocado. Sin acción pendiente sobre esos 5 por
ahora (queda abierto investigar más adelante cómo visualizarlos aparte si hace falta).

**Pedido de UX resultante:** que "BD Seguimiento" no sea solo un toggle de columnas para
Administración — al prenderlo, quieren ver únicamente a los vigentes en Seguimiento (los 754),
dejando "Q10 (base)" para ver a todos los estudiantes sin importar su estado (ya cubierto por
el filtro Estado).

**Implementado:** `_on_cambio_toggle()` ahora sincroniza el checkbox "BD Seguimiento" con el
filtro `En Seguimiento` agregado en §7.10 — al prenderlo, pone el filtro en "Sí"; al apagarlo,
lo vuelve a "Todos" (si estaba en "Sí" por este mecanismo). **Solo cuando la cohorte
seleccionada tiene datos de `en_seguimiento_jc`** (medido en vivo, no por nombre de cohorte) —
en 2023-2025 (que no tienen esa columna poblada, solo 2026 la tiene) el checkbox se queda
siendo solo de columnas, para no filtrar a 0 filas la demografía cargada en
[[demografia-historica-jc]]. El filtro `En Seguimiento` sigue disponible para selección manual
independiente (ej. ver el "No" = 23 sin tocar el checkbox).

**Verificado:** import limpio, app relanzada en primer plano sin traceback; confirmado con el
caché real que `en_seguimiento_jc` es `None` en las 3 cohortes históricas (2023: 488, 2024:
470, 2025: 733 filas) y solo tiene valores reales en 2026 (832 filas) — la nueva sincronización
checkbox↔filtro no puede disparar en las históricas.

---

## 7.12 Cierre 2026-08-06 (mismo día) — los 5 casos de §7.9 eran un bug real en `export_aprobacion.py`, no un atraso de Q10

Samuel desconfió (con razón) de la interpretación de §7.9: abrió H1Test manualmente y
encontró a uno de los 5 con 100% de avance y "Activo", contradiciendo directamente que "Q10
sí los tiene marcados como retirados". Se investigó a fondo — ver el gotcha completo en
`mapa-codigo.md` → `export_aprobacion.py`. Resumen: **era un bug real** (comparación de
inhabilitados aislada por periodo, en vez de contra la unión de todos los periodos del año),
no un atraso de Administración corrigiendo el Sheet. Las 5 personas tenían 100% de avance en
6-8 cursos cada una — de las mejores de la cohorte, mal clasificadas por avanzar más rápido de
lo normal entre niveles de una misma ruta (Desarrollo Web Nivel 3 → Avanzado).

**Corregido de punta a punta:** fix en `export_aprobacion.py` (activos globales, no por
periodo) → validado en vivo contra Q10 (83→78 retirados JC, exactamente -5) →
`sync_cohorte_2026.py` + `sync_aprobacion_supabase.py` re-corridos → `test_integridad_
supabase.py` 50/50 PASS (antes 754+83−832=5 "reingresos" fantasma, ahora 754+78=832 exacto).
La pestaña "Datos desactualizados Q10" de §7.9 ahora debería mostrar 0 casos para estos 5 en
la próxima carga del panel — validó exactamente el problema para el que se construyó.

**Lección:** cuando el dato de un pipeline automatizado contradice lo que alguien ve a mano en
la fuente original, no asumir que la fuente automatizada tiene razón por ser la "oficial" —
Samuel insistió y tenía razón. Mismo patrón que otros hallazgos de esta sesión (email
duplicado, hueco de ciudad): verificar contra la fuente cruda antes de aceptar un número
derivado como definitivo.

---

## 7.13 Extensión 2026-08-06 (mismo día) — Fase 4: ficha 360 al hacer doble clic

Pedido de Lina: igual que `panel_riesgo_gui.py` (doble clic → detalle con cursos y
desglose), el panel nuevo necesitaba su propia ficha por persona — la Fase 4 del plan
original (§5) que había quedado pendiente desde el 2026-07-30.

**Hallazgo antes de programar:** ni `v_gui_personas` ni `v_persona_360` tienen el curso
por curso — ambas solo exponen el agregado (`cursos_matriculados`/`cursos_aprobados`/
`avance_promedio` o `total_cursos`/`cursos_completados`/`avance_promedio`). Para mostrar
"Cursos: nombre + % avance individual" (lo que pedía Lina explícitamente) hacía falta una
consulta nueva a las tablas base — no había ningún atajo con las vistas ya existentes.

**Implementado:**
- `panel_control_datos.leer_cursos_por_participante(supa, participant_id)` (nuevo): una
  sola consulta con embed de PostgREST (`/enrollments?participant_id=eq.<id>&select=
  porcentaje_avance,estado,courses(nombre,cohorte,programa)`) — sin `v_gui_personas`/
  `v_persona_360` de por medio, es la única función de todo el módulo que toca tablas base
  directamente. A propósito **no se limita a la cohorte seleccionada** — trae todo el
  historial de matrículas de la persona en `enrollments`, coherente con el resto del panel
  (histórico completo, no solo la cohorte viva).
- `panel_control_gui._detalle_persona(vals)` (nuevo, wireado a
  `self._tabla.on_doble_click` en `_recrear_tabla`): popup scrollable con:
  1. Datos generales + las 3 secciones de "Fuentes" (BD Seguimiento, Retiros+Emoflow+
     Asistencia, Postulantes+Microcrédito) — **siempre visibles en la ficha**, sin
     depender de qué checkboxes estén prendidos en la tabla (reusa las mismas lambdas de
     `COLUMNAS_BASE`/`GRUPOS_TOGGLE`, cero lógica de formato duplicada).
  2. Historial por cohorte — de los datos ya cargados en `self._cache`, cero fetch nuevo
     (solo aparece si la cédula tiene más de una fila cargada).
  3. Cursos — detalle: la única sección que pide datos en vivo. Corre en un hilo aparte
     (mismo patrón `queue.Queue` + `after()` que la carga principal) para no congelar la
     ventana; muestra "Cargando…" y se reemplaza sola cuando el hilo responde. Colorea
     cada curso (verde ≥80%, amarillo ≥40%, rojo <40% — mismos umbrales de
     `panel_riesgo_gui.py`).
- Scroll con rueda del mouse ligado solo mientras el cursor está sobre el canvas del popup
  (`bind`/`unbind_all` en `<Enter>`/`<Leave>`) — nunca `bind_all` permanente, para no dejar
  la rueda "pegada" a una ventana ya cerrada.

**Verificado:** `import panel_control_gui` limpio; app relanzada en primer plano, 10s sin
traceback. **No verificado visualmente el popup en sí** (abrir con doble clic, ver que
carguen los cursos) — misma limitación de siempre en este entorno (sin herramienta de
captura para apps de escritorio nativas). Pendiente que Samuel/Lina lo prueben en el
escritorio real con datos reales antes de darlo por cerrado del todo.

---

## 7.14 Extensión 2026-08-10 — llevar "En Seguimiento" al panel público (Vercel/Netlify), solo como KPI agregado

Pedido de Samuel: tras sacar a 3 personas de la pestaña Seguimiento, quería ver ese cambio
reflejado también en el panel web público (`comunicaciones-ai/Panel-De-Datos`, deploy en
Netlify **y** Vercel — el README del repo del frontend documenta el segundo deploy desde
~2026-08, todavía no sincronizado con `panel-datos-etl.md` en este repo).

**Corrección importante encontrada en el camino:** `en_seguimiento_jc` (líneas 248-321 de
`sync_sociodemograficos.py`) **NO es upsert parcial** como el resto de columnas demográficas —
se recalcula completo (true/false) para TODOS los JC de la cohorte viva en cada corrida,
comparando cada cédula contra la pestaña Seguimiento. Sacar a alguien de esa pestaña **sí** lo
marca `en_seguimiento_jc=false` en el próximo sync (semanal, lunes 6:00 COT, o manual) — pero
eso es una ALERTA operativa, no un retiro real (no toca `retirado`/`cohorte_ingresos`/
`aprobacion_cursos`). Hoy solo se ve en la GUI local (filtro "En Seguimiento", pestaña
"⚠ Datos desactualizados Q10") — el panel público no tiene ningún campo relacionado
(confirmado revisando `lib/api.ts` completo).

**Decisión de alcance (pregunta directa a Samuel):** exponer esto en el panel público SOLO como
KPI agregado (conteo, sin nombres/cédulas) — nunca la ficha individual, para no romper la
decisión de arquitectura ya tomada dos veces (`panel-riesgo-mejora.md`,
`panel-control-jc-mr.md §0`: PII se queda local).

**Implementado (pendiente de aplicar):** `docs/migrations/042_v_pub_seguimiento_PROPUESTA.sql`
— vista `v_pub_seguimiento` (programa × cohorte × estado × grupo_ciudad × en_seguimiento_jc →
total, supresión n<5), mismo patrón que `v_pub_asistencia`/`v_pub_demografia` (037), reusa
`retiro_registrado()` sin reescribirla. **No aplicada aún — el MCP de Supabase estaba
desconectado al escribir esto** (mismo problema ya anotado con la migración 040). Pendiente:
(1) reconectar MCP o aplicar a mano en el SQL editor, verificando el próximo número libre
contra `list_migrations` antes de correrla; (2) `test_integridad_supabase.py` antes/después;
(3) verificar con anon key; (4) renombrar a `_APLICADA`; (5) SOLO ENTONCES agregar a
`lib/api.ts`/`app/page.tsx` del repo `panel-datos-rofe` — agregar el fetch antes de que la
vista exista rompería `cargarTodo()` completo (`Promise.all` falla entero si un solo request
da 404), tumbando el panel para todos los visitantes hasta el próximo deploy.

**Pendiente aparte, no resuelto por esta migración:** no existe comando de Telegram para forzar
`sync_sociodemograficos.py` (el bot solo tiene `q10/panel/asistencia/mr/rebotes/alerta/
backfill`, ver `n8n-workflows/q10-consolidacion.json`). Para ver el cambio de las 3 personas
YA (sin esperar al lunes) hay que correr el script a mano o disparar el workflow
`sociodemograficos-semanal` desde el editor de n8n.

## 7.15 Extensión 2026-08-11 — rediseño UI/UX pasos 1-3 (consejo-profundo): métrica "Al día", KPIs con definición, banner de contexto

Pedido de Samuel: el equipo administrativo (no técnico) se confundía con conceptos triviales para
el desarrollador. Se corrió `/consejo-profundo` (3 subagentes aislados + juez). Veredicto:
**adelante con ajustes**, priorizando cambios de alto impacto / bajo costo ANTES de un rediseño
mayor a "vistas por pregunta", y con un hallazgo del escéptico que reordenó todo — *"Al día
incluye retirados" no es un problema de UI, es una métrica que miente; arreglar el cálculo, no
solo la etiqueta*. Se implementaron los pasos 1-3 (todo en `tools/panel_control_gui.py`, cero SQL,
cero cambios en la capa de datos — es rediseño de presentación).

**Paso 1 — métrica "Al día" corregida.** El KPI contaba `al_dia` (flag crudo de `v_gui_personas`
= avance ≥80%) sobre TODAS las filas filtradas, incluyendo retirados que habían llegado a ≥80%
antes de irse. Ahora `al_dia = activos con ≥80%` (`f.get("al_dia") and not f.get("retirado")`) y
el % es **sobre activos**, no sobre el total ("744 de 754 activos"). Denominador "activo" =
`not retirado`, el mismo criterio del filtro Estado=Activos (coherencia), no `en_seguimiento_jc`
(que solo existe para JC cohorte viva). La columna por-fila "Al día" se renombró a **"≥80%
avance"** para que no se llame igual que el KPI curado y reintroduzca la confusión.

**Paso 2 — KPIs con definición inline (no tooltip).** El helper `_kpi()` acepta ahora un
`subtitulo` (texto pequeño debajo del valor). Los 5-6 KPIs quedaron: **Matriculados** ("incluye
retirados") · **Activos** ("sin retiro en Q10") · **En Seguimiento** ("vigentes en el Sheet",
solo JC viva) · **Al día** ("activos con avance ≥80%") · **Retirados** · **Avance promedio**. Se
agregó "Activos" explícito para atar los tres números gemelos que el equipo confundía (Activos ⊃
Al día; Retirados = complemento; En Seguimiento = universo del Sheet). Se reportan SIEMPRE ambos
(754 activos vs 751 Seguimiento), nunca uno solo en silencio (regla de [[00-vision-global]]).

**Paso 3 — banner de contexto en lenguaje plano** arriba de los KPIs (`self._contexto_txt`,
actualizado en `_actualizar_contexto()` dentro de `_refrescar_tabla`). Dice qué se está viendo:
*"Mostrando Jóvenes creaTIvos · cohorte 2026 · 832 personas (sin filtros · incluye activos y
retirados). Cada fila es una persona; usá los filtros de la derecha para acotar."* — resuelve la
confusión #1 (qué significa el número inicial). Con filtros activos los enumera ("con filtros:
Ciudad=Bogotá, Estado=Activos"). La barra de estado gris inferior ya daba esta info pero nadie la
miraba.

**Verificado con datos reales (caché de disco, sin PII — solo conteos):** JC 2026 sin staff =
832 matriculados = 754 activos + 78 retirados (cuadra con §7.12); En Seguimiento 751; "Al día"
bajó de 757 (viejo, con retirados) a 744 (nuevo, solo activos) — exactamente los 13 retirados con
≥80% que el bug contaba de más. App relanzada de verdad (no solo importada — criterio del bug de
`pady` en §7.3): 4s sin traceback, banner poblado correctamente. **Falta revisión visual de
Samuel/Lina** en el escritorio real (misma limitación de siempre: sin captura de apps de
escritorio en este entorno).

**Continuación → §7.16** (pasos 4-5). El paso (d) tooltips/modo-avanzado se descartó (costo
hundido: ya falló 3 veces).

## 7.16 Extensión 2026-08-11 (mismo día) — pasos 4-5: pestaña "Vistas rápidas" + kit de validación

Continuación de §7.15. El consejo priorizó los pasos 1-3 (baratos) y condicionó los 4-5 a
evidencia real. Estado ahora:

**Paso 5 — pestaña "🏠 Vistas rápidas" (CONSTRUIDA, tarjetas PROVISIONALES).** Nueva pestaña de
entrada (primera, seleccionada al abrir) con tarjetas por PREGUNTA en el lenguaje del equipo
("¿Quiénes están en riesgo?", "¿Quiénes se retiraron?", "En seguimiento (Sheet)", etc.). Al
hacer clic, `_aplicar_vista(estado=…, banda=…, en_seg=…, grupo=…)` setea los filtros y salta a
"Explorar". **El mecanismo reusa TODA la lógica de filtros existente — cero duplicación** — y es
independiente de qué preguntas ganen: solo cambia la lista `vistas` en `_build_tab_vistas`.
Resuelve la contradicción del escéptico **sin esconder el poder analítico**: la pestaña
"Matriculados" se renombró "🔎 Explorar (todos los filtros)" y queda entera y visible; las
tarjetas son atajos aditivos, si una no calza el usuario cae en Explorar (el UI de hoy), nunca
"peor". `_exportar_csv` pasó a comparar la pestaña activa por widget (no por índice) para
sobrevivir al reordenamiento.

**Lista de tarjetas anclada en preguntas ya documentadas** (riesgo/deserción, retiros,
seguimiento, desactualizados Q10, postulantes) — NO inventadas, pero **provisionales hasta el
paso 4**.

**Paso 4 — validación con usuarios (KIT ENTREGADO, PENDIENTE de correr).** Claude no puede
ejecutarlo (requiere hablar con personas). Guía lista en
[[panel-control-validacion-usuarios]]: ~15 min × 2 usuarios, con lo que hay que preguntar ANTES
de mostrar el panel (descubrir sus preguntas en sus palabras), qué observar con el panel abierto,
y cómo traducir hallazgos en ediciones de la lista `vistas`. **Condición dura del escéptico:
correr esto antes de dar las tarjetas por buenas** — hoy son una hipótesis con prototipo, no una
verdad validada.

**Verificado:** import limpio; app relanzada de verdad (5s sin traceback); se ejerció
`_aplicar_vista` programáticamente — aplica filtros, salta a "Explorar", el banner narra "con
filtros: Avance=En riesgo (0-25%), Estado=Activos" y las 4 pestañas quedan en orden. **Falta
revisión visual de Samuel/Lina** (misma limitación) y correr el paso 4.

## 7.17 Extensión 2026-08-11 (mismo día) — canon oficial por cohorte en el panel (no destructivo)

Pedido de Samuel: en cohortes cerradas (2023/24/25) el panel no mostraba el canon oficial CON
retirados (ej. 2024 = 608 = 433 culminantes + 175 retirados), porque `v_gui_personas` cuenta por
matrícula y Q10 nunca exportó los retirados históricos a nivel individuo. Propuesta que evaluó
Samuel: "descartar" filas para cuadrar el canon. **Rechazada por diseño** (ver análisis en la
conversación): forzar que el nivel-persona sume al canon exigiría (a) inventar ~481 filas fantasma
de retirados (viola `convenciones.md` "nunca crear participants desde fuentes secundarias" y §6 del
plan de canon) o (b) borrar personas reales (destructivo, difícil de revertir, y aun así no agrega
los retirados). El canon es una **verdad agregada** a otro grano; nunca reconcilia fila por fila
con el nivel-persona para cohortes cerradas.

**Solución implementada (no destructiva, cero cambios en Supabase):** el panel LEE el canon
agregado ya existente (`v_pub_cohorte`, la misma fuente del panel público, backing
`cohorte_historico`) y lo muestra ENCIMA de la lista de personas.

- `panel_control_datos.leer_canon_cohortes(programa, supa)` — lee `v_pub_cohorte` (8 filas,
  público, egress despreciable). NO recalcula desde matrícula.
- Caché en disco extendido con la clave `canon` (`guardar_cache`/`cargar_cache_si_vigente`); un
  caché viejo sin ella cae en el `except` → refetch → se regraba (auto-sana).
- `panel_control_gui._actualizar_canon(base)` — banner arriba de los KPIs con el canon de la
  cohorte seleccionada + el Δ contra los individuos en la base. Detecta cohorte viva (la última) vs
  cerrada para etiquetar "activos hoy (Seguimiento)"/"avance provisional" vs "culminantes"/
  "retención". Independiente de los filtros de fila (usa la cohorte completa).

**Verificado en vivo** (`v_pub_cohorte` leído desde la conexión del panel = tabla canon exacta:
2023 488=345+143, 2024 608=433+175, 2025 722=559+163, 2026 832=751+81). App relanzada: cohorte
2024 muestra *"608 ingresados = 433 culminantes + 175 retirados · 71,2% retención"* + *"En la base
hay 470 de los 608 del canon — faltan ~138 retirados históricos…"*; cohorte 2026 *"832 = 751
activos hoy + 81 retirados"* + *"La base coincide con el canon (832)"*. Sin traceback.

**Regla que queda:** el conteo de filas del panel NO es el universo de una cohorte cerrada — el
canon de arriba sí. La lista sirve para gestión individual de a quién sí tenemos en Q10.

## 7.18 Extensión 2026-08-11 (mismo día) — badge amarillo "+n en duda" + diagnóstico canon vs `retiros` por año

Pedido de Samuel: (1) marcar en amarillo, en cada lugar con posible choque por desactualización de
Q10, el "+n" de estudiantes en duda, clickable para ver el detalle; (2) revisar por qué 2024 no
muestra los retirados que debe (608 canon vs 470 en panel) y confirmar si la medida
"todo el que no es activo = retirado" cuadra o hay caso excepcional.

**(1) Badge amarillo (implementado):** `_actualizar_kpis` agrega un KPI amarillo "⚠ En duda (Q10)
= +n" y `_actualizar_canon` una línea amarilla, ambos clickables → pestaña "⚠ Datos desactualizados
Q10". `n` = `len(filtrar_desactualizados_q10(cohorte))`, sobre la cohorte completa (no los filtros).
Solo aparece si n>0 (hoy solo JC 2026 = 3). Helper `_hacer_clickable(widget, comando)` nuevo.
**(2026-08-11, ampliación confirmada por Samuel):** el badge también va en la tarjeta "Datos
desactualizados Q10" de la pestaña 🏠 Vistas rápidas (`_actualizar_badge_vistas`, conteo
program-wide como la pestaña de detalle a la que salta la tarjeta).

**(2) Diagnóstico verificado en vivo contra Supabase (v_gui_personas × canon × tabla `retiros`):**

| Año | Canon ing=act+ret | Panel act/ret | activos ok | `retiros` JC | Veredicto |
|---|---|---|---|---|---|
| 2023 | 488=345+143 | 345/143 | ✓ | 147 | Completo |
| 2024 | 608=433+175 | 433/**37** | ✓ | **176** | Excepción (ver abajo) |
| 2025 | 722=559+163 | 559/160 | ✓ | 163 | Casi completo (−3) |
| 2026 | 832=751+81 | 754/78 | ✗ | 78 | Excepción (ver abajo) |
| 2019–22 | solo agregado | 0 filas | — | — | Sin nivel-persona |

**La medida "no-activo = retirado" cuadra.** A nivel canon se cumple por construcción todos los años
(retirados = ingresados − culminantes). Los activos/culminantes coinciden EXACTO en todas las
cerradas. Dos excepciones:
- **2024:** los 139 retirados que no se ven en el panel SÍ existen — en la tabla `retiros` (176 =
  canon 175 + 1 perfil de prueba). No entran a `v_gui_personas` porque esa vista se arma desde
  `enrollments` y esos 139 nunca tuvieron matrícula sincronizada (Q10 no los exportó a nivel
  individuo). No es dato perdido: es de dónde lee el panel.
- **2026:** "activo" tiene dos definiciones — Seguimiento (751, canon) vs no-retirado en Q10 (754,
  panel); Δ3 = los "en duda" del badge. Único año con `en_seguimiento_jc`, único donde la medida da
  distinto según qué "activo" se use.

**Decisión de Samuel (2026-08-11):** NO unir `retiros` a la lista del panel — se mantiene
"matriculados" (a quién tenemos en Q10 para gestión individual). Los 175 retirados oficiales de 2024
ya se ven en el banner de canon (§7.17) con el Δ explicado; no hace falta listarlos uno por uno.
Coherente con `convenciones.md` ("nunca crear personas desde fuentes secundarias"). La opción de unir
`retiros` (universo matrículas ∪ retiros) quedó evaluada y descartada a propósito, no por olvido.

## 7.19 Extensión 2026-08-11 (mismo día) — "en duda" contados como retirados por defecto (datos digeridos)

Corrección del pedido anterior. La primera versión de la casilla ESCONDÍA a los "en duda" por
defecto (832→829), pero Samuel aclaró dos cosas: (1) **832 es constante, nunca se debe reducir**
en "Matriculados"/"ver todos"; (2) **los "en duda" deben contarse como RETIRADOS** por defecto —
lo más probable es que lo sean, y el equipo necesita datos DIGERIDOS que cuadren directo con el
canon sin que un analista les explique el "limbo" (a Samuel lo cuestionaron por reportar 78
retirados cuando el canon dice 81; los 3 en limbo lo justificaban, pero acá no hay quién lo
explique).

**Implementado — retiro EFECTIVO:** `_marcar_retirado_efectivo(base)` stampa `_ret_efectivo` en
cada fila = `retirado` crudo **OR** "en duda" (por defecto). Los "en duda" ya NO se quitan de la
lista (832 constante); se **cuentan como retirados**. El filtro Estado, los KPIs (Activos/
Retirados/Al día) y la columna "Retirado" usan `_ret_efectivo`, no el `retirado` crudo. Es solo
presentación en memoria — no toca Supabase ni la pestaña de detalle (que sigue mostrando el estado
crudo de Q10).

**Casilla "Contar 'en duda' como activos"** (`self._en_duda_activos`, off por defecto): al
prenderla, los "en duda" vuelven a su estado CRUDO de Q10 (activos) — para quien sepa. Se
deshabilita en cohortes sin casos.

**Verificado en vivo (JC 2026):**
- Default (en duda = retirados): **832 = 751 activos + 81 retirados** → cuadra EXACTO con el canon,
  y "Activos" (751) = "En Seguimiento" (751). Cero limbo en la vista normal.
- Casilla ON (en duda = activos crudos): 832 = 754 + 78 (la vista de experto).
- 2024 (cerrada, sin en duda): 470/433/37, casilla deshabilitada.
El badge amarillo "+3" y la pestaña de detalle siguen visibles siempre (el aviso para el experto),
independientes de la casilla. Sin traceback.

## 7.20 Extensión 2026-08-11 (mismo día) — KPIs de cohortes cerradas desde el canon (contrato de datos)

Samuel trajo el **contrato de datos** de otra instancia (autoritativo) y aportó CSVs de JC 2024
(433 culminantes + retirados). Dos resultados:

**(A) NO se importan los CSVs como personas — evaluado y descartado.** El contrato es explícito:
en cohortes cerradas no hay estado por persona, se usa el agregado (`cohorte_historico` ámbito
'nacional' / `v_pub_cohorte`). Además, medido en vivo: la unión de los 3 CSVs de retirados son
solo **52 cédulas** (48 nuevas → el panel llegaría a 518, ni 470 ni 608); incluso la tabla
`retiros` (176) es más completa y llegaría a ~609. El 608 del canon incluye ~90 seleccionados que
nunca ingresaron (no están en ninguna lista de retiro de Seguimiento). Reconstruir a nivel persona
crearía un tercer número equivocado. La regla queda: cerradas = agregado, no reconstruir.

**(B) Los KPIs de cohortes cerradas ahora salen del canon (`v_pub_cohorte`)** — decisión de Samuel,
alineada con el contrato ("v_pub_cohorte es la vista ideal para las tarjetas"). `_actualizar_kpis`
detecta cohorte cerrada (`_es_cohorte_viva()` = la última con canon es la viva) y llama a
`_kpis_cohorte_cerrada`: tarjetas **Ingresados / Culminantes / Retirados / Retención** fijas desde
`v_pub_cohorte`, + "En la base" (conteo person-level filtrable, el drill-down). La cohorte viva
(2026) mantiene los KPIs por-persona (activo=Seguimiento) y filtrables. El banner de canon
(§7.17) ya no repite las cifras en cerradas (las tarjetas las tienen) — solo aclara qué es la tabla.

**Verificado en vivo:** JC 2024 (cerrada) → tarjetas 608/433/175/71,2% + "En la base 470"; JC 2026
(viva) → 832/751/81 por-persona + badge "+3 en duda". Sin traceback. Cero cambios en Supabase.

**Espejo en el panel PÚBLICO (Vercel, repo `panel-datos-rofe`, commit e68bb7d 2026-08-11):** el
frontend armaba las tarjetas de cohorte desde `cohorte_ingresos` (solo cohorte viva 2026), así que
las cerradas salían en blanco. Se cableó `v_pub_cohorte` (`lib/api.ts` campo `pubCohorte`) y
`ingresosProg` (`app/page.tsx`) cae a esa vista para las cerradas. **Gotcha (commit 7e4513a):** no
bastaba con el dato — el KPI canónico estaba `gated a esActual`, así que las cerradas caían al KPI
viejo "Participantes (histórico Q10)" y no mostraban el canon. Se destrabó el render para cerradas
(sin filtro de ciudad, porque el canon no tiene desglose por ciudad; título Culminantes/Retirados/
Ingresados según el filtro Estado). Ahora Vercel muestra 2024 = 608 = 433 culminantes + 175
retirados. Commits e68bb7d + 7e4513a en `comunicaciones/main` (deploy Vercel). Ver [[panel-datos-etl]].

**Contrato de datos (referencia, para no reintroducir bugs):** dos regímenes — (1) cerradas: canon
de `cohorte_historico`/`v_pub_cohorte`, `culminantes + retirados = seleccionados`; (2) viva:
activo = `en_seguimiento_jc=true` (≈751), retirado = `retiros`, reportar Δ vs Q10 (754), nunca uno
en silencio. `source_system` 'bd_monitorias_2023_csv'/'bd_seguimiento_2024_seleccionados' son cargas
históricas con `en_seguimiento_jc=NULL` (no cuentan como activos actuales). En MR "inhabilitada" ≠
retiro. Celdas n<5 en vistas públicas vienen NULL a propósito (privacidad) → mostrar "—", no 0.

## 7.21 Extensión 2026-08-12 — sección "Enriquecimiento histórico" en la ficha 360

Cierre de la etapa final de enriquecimiento histórico (ver [[project_enriquecimiento_historico_final]]
y `docs/procesos/plan-enriquecimiento-final-2026-08-12.md`): 4 subagentes extrajeron 379.979
registros de las 66 fuentes 2019-2025 (Excel/CSV fuera de Q10/Supabase); tras el filtro de
privacidad del usuario (solo `participant_id` real + excluir match-por-nombre) se cargaron
**37.788 filas / ~3.700 personas** en 4 tablas nuevas (`enriquecimiento_socioeconomico`,
`_empleabilidad`, `_resultados`, `_mr_extendido`), RLS bloqueado a `anon`/`authenticated` igual
que `postulantes_jc`/`retiros`.

**Nueva función de datos** `leer_enriquecimiento_por_participante()` en `panel_control_datos.py`
(mismo patrón on-demand que `leer_cursos_por_participante`, sin cache) trae las 4 tablas por
`participant_id`. En la GUI, la ficha 360 (§7.13) ahora pide cursos + enriquecimiento en el MISMO
hilo/worker (una sola consulta en vivo extra) y agrega la sección "Enriquecimiento histórico
(fuentes 2019-2025, fuera de Q10)" debajo de "Cursos — detalle": agrupa por `campo` con etiqueta
legible (`CAMPOS_ENRIQUECIMIENTO_LABELS`, fallback automático a snake_case→Capitalizado para
campos futuros) y muestra hasta 3 valores distintos con su año de fuente entre paréntesis (ej.
"IED tal (2022) · Colegio X (2023)"), para no ocultar que un campo puede venir de varias
convocatorias. Si la persona no tiene nada, mensaje explícito ("no aparece en las 66 fuentes, o
solo match por nombre — excluido"), nunca una sección vacía silenciosa.

Verificado con datos reales antes de publicar: una persona JC con `estado_convocatoria=RETIRADO`
(2026) y una mujer MR con 8 campos (dirección, departamento, sostenimiento, canal de adquisición,
presentación personal, ingresos familiares, personas del núcleo, quién le ayudó a llenar el
formulario) — tildes correctas en UTF-8 real (el `�` que se ve en la consola de PowerShell es
solo el codepage de la terminal, no un problema del dato, mismo gotcha del clúster F).

**Pendiente:** validar la cobertura extraída contra la lista de campos del Power BI del usuario
(aún no entregada) para confirmar que no falta ninguna dimensión que el equipo ya usa.

## 7.22 Extensión 2026-08-12 (mismo día) — fix bug MR 2025 (1.016→302) + pestaña "Retiros por año"

Continuación de §7.21, al verificar la premisa "MR: 4 hallazgos que bloquean" documentada en
`docs/procesos/plan-enriquecimiento-final-2026-08-12.md`. Con OK explícito del usuario:

**1. Bug 1.016→302 FIJADO en producción.** Causa raíz: `importar_historico_q10.py` pid 16
("Unico 2025") forzaba TODO el periodo a `programa='mr'`, pisando 2 cursos JC que Q10 mezcla
en ese mismo periodo ("Emprendimiento: Idea de Negocio JC", "Fundamentos Lógica de
Programación - 2026" — 713+681 matrículas, ~714 personas dobles). `UPDATE courses SET
programa='jc'` en esos 2 ids + `recompute_aggregates()` → `v_programa_stats`/`cohorte_stats`
MR 2025 ya dan **302** (antes 1.016), JC 2025 sube a 737. Código corregido para que la
próxima corrida de `importar_historico_q10.py` no revierta el fix: `MAPA_PERIODOS[16]` pasó
de `("2025","mr")` a `("2025", None)` — cada curso de ese periodo se clasifica individualmente
por `clasificar_curso()`. Como los otros 2 cursos MR reales de ese periodo ("Empoderamiento en
Ventas...", "Transforma tu negocio...") no tenían ningún mecanismo de clasificación propio
(dependían solo del override ciego que se acaba de quitar), se agregaron 2 keywords nuevos a
`KEYWORDS_MR` en `normalize_q10_data.py` — verificado que no colisionan con ningún curso JC.

**Gotcha nuevo encontrado de paso:** `course_config.json` guarda nombres en MAYÚSCULAS pero
`clasificar_curso()` compara sin bajar a minúsculas — esa comparación NUNCA hace match hoy
(deuda anotada en el código, no corregida en este fix por alcance; toda la clasificación real
cae en `KEYWORDS_MR` + default `'jc'`).

**2. "retiros MR roto estructuralmente" (doc de 2026-07-27) — RE-VERIFICADO Y DESCARTADO.**
Al leer la hoja "Inactivas" EN VIVO: la columna 27 sí se llama "Año-retiro" (el diagnóstico
viejo decía "Año-Ingreso", equivocado o desactualizado). El 0%/bajo cruce por cédula real no
es un bug de matching: **25 de 33 retiros MR pertenecen a candidatas que se dieron de baja
ANTES de matricular** (existen en `postulantes_mr`, nunca tuvieron fila en `participants` —
coherente con el diseño; `retiros.participant_id` es nullable a propósito). El problema real
era de VISIBILIDAD: como toda la UI de personas parte de `v_gui_personas` (que exige
`participants`), esas 25 mujeres eran invisibles en ambos paneles.

**3. Pestaña nueva "📅 Retiros por año".** `leer_retiros_por_anio(programa, supa)` en
`panel_control_datos.py` lee `retiros` directo (no `v_gui_personas`), agrupa por `cohorte`
(=año) y cuenta total / con-participante / sin-matrícula-previa. Nueva pestaña en el notebook,
independiente del selector de cohorte de arriba — para MR se etiqueta "año" y no "cohorte"
(confirmado por el usuario: MR no se organiza por cohortes de selección anual como JC).
Incluye en pantalla el aviso de limitación de fuente: la base MR que se recibió viene en un
solo bloque sin seccionar por año de origen (a diferencia de JC, que sí trae carpetas
2019-2025), así que el desglose no puede ser más fino que el año de retiro/baja registrado —
se documenta para poder pedirle al equipo las bases MR separadas año por año.

Cambio de caché: `cargar_cache_si_vigente`/`guardar_cache` ganan una 4ª clave `retiros_anio`
(mismo patrón auto-sana que "canon" — caché viejo sin la clave cae a None y se regraba
completo). Verificado con datos reales: MR 2025 = 25 total/5 en la base/20 sin matrícula
previa, MR 2026 = 8/3/5; JC ya resolvía bien (>97% con participante en todas las cohortes,
salvo el bucket "no_cohorte" que es una categoría aparte).

**No se tocó:** el panel público (Vercel) — esta pestaña es de gestión interna con PII a
nivel-persona (motivo de retiro), no aplica al panel agregado público.

## 7.23 Extensión 2026-08-12 — filtros Año + Ciudad en "Postulantes sin matrícula" (MR)

Pedido del usuario: la sección de mujeres MR (universo grande de candidatas sin Q10) no se
analiza por cohorte-curso como JC, sino por variables; quería filtrar p.ej. "Bogotá 2026" con
dos filtros y sin demora. La pestaña "Postulantes sin matrícula" solo tenía la barra de
búsqueda del componente `TablaFiltrable` (una columna a la vez). Se le agregó una **barra de
filtros propios Año + Ciudad** que combinan con AND, con combos poblados dinámicamente de los
datos reales de cada programa (`_refrescar_tabla_sin_matricula` + `_anio_postulante`).

Decisiones:
- **Año:** MR = año de `fecha_creacion` (Plataforma MR, ver §7.22 y plan-enriquecimiento-final);
  JC = `promo_year` (Mongo). Extraído con `_extraer_anio` de panel_control_datos.py.
- **Ciudad:** se filtra por `ciudad_norm` (columna ya normalizada), NO por `ciudad` cruda —
  había ~10 variantes de "Bogotá" (BOGOTA, Bogotá D.C., Bogots…) que ciudad_norm colapsa a 2-3.
- La sección MR muestra además la columna "Año" al frente + 7 columnas ricas (§7.22) y ordena
  por año desc. El KPI muestra "Mostrando N de Total" cuando hay filtro activo.
- Verificado headless: 2026+BOGOTA DC → 5, 2023+BOGOTA DC → 155, instantáneo.

Todas las mujeres MR quedan accesibles en el panel de control: las ~588 con Q10 en «Explorar»
(v_gui_personas, con los filtros de cohorte de siempre), las ~4.752 sin Q10 aquí con estos
filtros propios. Los campos que aportaría Q10 quedan NULL para las que no lo tienen.

## 7.24 Extensión 2026-08-12 — sección "Mujeres ROFÉ" propia (toggle Q10) en vez del split de JC

Pedido del usuario: MR no tiene por qué copiar la estructura de dos pestañas de JC
(Matriculados vs Postulantes). Quería UNA vista de mujeres donde: **toggle Q10 apagado** = las
~5k del CSV "Plataforma MR" completas; **toggle Q10 encendido** = solo las pocas que sí tienen
datos de Q10. Rediseño (estructura propia de MR, no copia de JC):

- **Fuente nueva** `leer_mujeres_mr_todas()` (panel_control_datos.py): `postulantes_mr` COMPLETO
  (con y sin `participant_id`), no el filtro `participant_id IS NULL` de
  `leer_postulantes_sin_matricula` (que se mantiene para JC). El worker usa una u otra según
  programa.
- **La pestaña "Postulantes sin matrícula" se vuelve "👩 Mujeres ROFÉ" cuando el programa es
  MR** (etiqueta del notebook + nota + KPI dinámicos). Para JC sigue igual.
- **Toggle "Solo con Q10"** (checkbox, default OFF): OFF muestra las 5.318; ON filtra a
  `participant_id IS NOT NULL` (566 con Q10). Solo habilitado para MR. Columna nueva "¿En Q10?"
  (Sí/No) para verlo por fila. KPI "De ellas, con Q10: 566".
- Combina con los filtros Año + Ciudad (§7.23) con AND. Verificado headless: Q10 OFF=5.318,
  Q10 ON=566, Q10 ON+2026=182, Q10 OFF+2026=435.
- Los datos de curso/avance de Q10 de las 566 siguen en «Explorar»/ficha 360 (v_gui_personas);
  esta vista es el universo + variables (año/ciudad/sociodemografía/campos ricos), sin Q10.

Las 566 con Q10 aparecen tanto aquí (con toggle) como en «Explorar» — solape intencional: esta
pestaña es "todas las mujeres", «Explorar» es el detalle Q10.

## 7.25 Extensión 2026-08-12 — botones de año de arriba = filtro de "Mujeres ROFÉ" (MR)

Continuación de §7.24. El usuario pidió que los botones de año de la barra superior (que ya
filtran «Explorar») sean TAMBIÉN el filtro de año de la sección "Mujeres ROFÉ", para no tener
un dropdown de año redundante. Cambios (solo MR, JC intacto):

- **Selector de año superior (MR):** ya no es matrícula∪canon (que daba solo 2025/2026), sino
  **"Todos" + los años reales del universo de mujeres** (2022-2026, de `postulantes_mr`
  fecha_creacion). Sin años vacíos. Default = "Todos". JC sigue con v_gui_personas∪canon
  (2019-2026, default el más reciente).
- **Los botones filtran ambas pestañas:** `_build_selector_cohorte` ahora llama a
  `_on_cambio_cohorte` (refresca «Explorar» Y «Mujeres ROFÉ»). `_filas_programa_cohorte` trata
  "Todos" como sin-filtro. Verificado: MR "2024" → Mujeres ROFÉ 1.063, "2022" → 671, "Todos" →
  5.318.
- **Dropdown de Año eliminado de la pestaña Mujeres ROFÉ** (redundante) — el `_frame_pm_anio`
  se oculta en MR; en JC (pestaña Postulantes) se mantiene. Quedan Ciudad + toggle Q10.
- **"De ellas, con Q10" solo se muestra en "Todos"** — al cambiar de año la lectura se volvía
  confusa (pedido explícito). El título del KPI cambia a "Mujeres ROFÉ — 2024" al filtrar.

Tradeoff conocido: como los botones son compartidos, elegir 2022-2024 en «Explorar» (que solo
tiene matriculadas 2025/2026) muestra la tabla vacía ahí — es correcto (no hubo matriculadas
esos años en MR); el análisis de esos años se hace en «Mujeres ROFÉ». Default "Todos" evita
toparse con eso de entrada.

**Cierre 2026-08-12 (v2, pedido del usuario "no tapar todos los botones"):** en vez de ocultar
la barra entera en «Explorar», se ocultan SOLO los botones de años sin matriculadas (vistas
vacías inútiles). `_cohortes_mr_para_vista()` + `_on_tab_change` (ligado a `<<NotebookTabChanged>>`):
en «Explorar» MR los botones = "Todos" + años con matrícula en `v_gui_personas` (hoy 2025, 2026);
en «Mujeres ROFÉ» = "Todos" + todos los años de registro (2022-2026). La barra queda siempre
visible. Al cambiar de pestaña, si el año seleccionado ya no está en el set, cae a "Todos".
Verificado: MR+Explorar botones=[Todos,2026,2025]; MR+Mujeres ROFÉ=[Todos,2026,2025,2024,2023,2022].

**Diferencia de conteo panel (5.318) vs CSV Plataforma MR (5.157):** los 161 de más son mujeres
que ya estaban en `postulantes_mr` desde OTRAS pestañas del Sheet BD-Mujeres ROFÉ (cursos_pct=107,
inactivas=30, general=24), no en el CSV de la plataforma. De esas 161, 156 son las "sin año"
(vinieron de fuentes sin fecha de registro). `postulantes_mr` es la UNIÓN de todas las fuentes MR.

## 8. Conexiones

[[plan-visualizacion-2026-07-30]] (Fase 2 pausada a favor de este documento — pendientes vivos
migrados en su §3, no se pierden) · [[panel-riesgo-mejora]] (archivado/fusionado — ver desglose
punto por punto en su propio archivo) · [[bd-seguimiento-monitorias]] (hallazgo Envigado/
Sabaneta/Itagüí documentado ahí, no aquí — este documento solo lo referencia) ·
[[supabase-estructura]] · [[postulantes-mr-supabase]] · [[mapa-codigo]] ·
[[panel-control-validacion-usuarios]] (paso 4 del rediseño 2026-08-11)
