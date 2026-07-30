# Panel de Control JC/MR — herramienta interna nueva (histórico completo, PII, fuentes togglables)

> **Conexiones:** [[00-vision-global]] · [[plan-visualizacion-2026-07-30]] ·
> [[panel-riesgo-mejora]] · [[bd-seguimiento-monitorias]] · [[supabase-estructura]]
>
> Pedido de Samuel, 2026-07-30 (sesión de auditoría de geografía JC 2026 — ver
> [[plan-visualizacion-2026-07-30]] §"Bogotá/Medellín"). Decisiones confirmadas por ronda de
> preguntas la misma tarde (ver `claude_sessions.md`). **Documento previo a ejecutar** — a
> pedido explícito de Samuel, esto se escribe ANTES de tocar código.
>
> **Estado (2026-07-30, noche): Fase 1 ✅ HECHA y verificada** (ver §5) — Samuel autorizó
> empezar a construir. Fases 2-5 sin empezar.

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

### Fase 2 — Interfaz: selector + toggles + tabla base (estado 1 del toggle, ver §6)
Selector de programa/cohorte + panel de checkboxes de fuentes + tabla con columnas dinámicas +
filtros combinables (ciudad, avance, estado). Reusar `TablaFiltrable`. El toggle de
"Postulantes históricos" en este estado **solo agrega columnas** a las filas de matriculados
ya visibles — cero filas nuevas (ver §6, estado 1).

### Fase 3 — Modo aparte "Postulantes que nunca matricularon" (estado 2 del toggle, ver §6)
Vista/pestaña separada y explícita, con su propio contador ("452 JC · 4.588 MR" o el número
vigente al momento de construirla — **reverificar en vivo, no copiar el número de este
documento**), que lista `postulantes_jc`/`postulantes_mr` con `participant_id IS NULL`. Nunca
se mezcla con la tabla de matriculados ni se suma a ningún total de "estudiantes".

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

## 8. Conexiones

[[plan-visualizacion-2026-07-30]] (Fase 2 pausada a favor de este documento — pendientes vivos
migrados en su §3, no se pierden) · [[panel-riesgo-mejora]] (archivado/fusionado — ver desglose
punto por punto en su propio archivo) · [[bd-seguimiento-monitorias]] (hallazgo Envigado/
Sabaneta/Itagüí documentado ahí, no aquí — este documento solo lo referencia) ·
[[supabase-estructura]] · [[postulantes-mr-supabase]] · [[mapa-codigo]]
