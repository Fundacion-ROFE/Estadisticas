# Panel de Riesgo — Plan de mejora (migración a Supabase + panel de decisiones)

**Estado:** Fase 1 completada (2026-07-21) — fuente de datos migrada a Supabase, misma UI.
Fases 2-3 pendientes. Decisión de arquitectura
tomada con Samuel: **se mantiene la GUI de escritorio (Tkinter)**, no se construye un panel
web nuevo. Motivo: no expone PII a internet (sigue 100% local), no requiere autenticación
nueva, y el equipo que lo usa ya sabe correr scripts Python localmente.
**Última actualización:** 2026-07-21
**Procesos relacionados:** [[panel-datos-etl]] · [[dashboard-web]] · [[q10-consolidacion]] · [[postulantes-mr-supabase]] (candidato natural para la Fase 5 de búsqueda unificada por cédula/email)

## Qué hace (visión)

`tools/panel_riesgo_gui.py` hoy cruza h2test/Avance/Retirados (Sheets) por email y muestra
6 vistas por programa + tab Admin. Es útil pero quedó **atrás de Supabase**: no ve la cohorte
canónica (832), ni Emoflow, ni el puntaje compuesto, ni el filtro por ciudad — todo eso ya
existe en `panel-datos-rofe` a nivel agregado, pero nadie lo puede consultar a nivel de
**estudiante individual** con botones de acción.

**Objetivo:** que sea el "panel de datos, pero para tomar decisiones sobre personas
concretas" — mismos conceptos (cohorte canónica, puntaje, ciudad, Emoflow, asistencia) pero
con nombre/cédula/email visibles y botones que disparan las consultas que hoy se piden a
mano ("dame los estudiantes en riesgo de Bogotá", "quiénes no tienen Emoflow", etc.).

## Por qué ahora
Motivación de Samuel: no hay una persona dedicada a análisis de datos — el panel debe
**hacer las preguntas por el usuario**, no esperar a que alguien escriba una consulta SQL o
arme un cruce manual. Botones > flexibilidad libre.

## Alcance — qué cambia y qué no

| | Hoy | Plan |
|---|---|---|
| Fuente de datos | Sheets (h2test, Avance, Retirados) leídos en vivo | Supabase (`service_role`, mismo patrón de los scripts backend) |
| Interfaz | Tkinter, 5 tabs fijos | Tkinter, tabs existentes **+** tab nuevo "Decisiones" |
| Alcance de datos | Solo Q10 + Avance manual | Cohorte canónica (832), Emoflow, asistencia, puntaje compuesto, filtro ciudad — todo lo que ya está en Supabase |
| Privacidad | Local, gitignoreado | Igual — sigue sin tocar internet |
| Programas | JC + MR + Retirados (ya existente) | Igual, se añade el filtro por ciudad (JC) |

**No cambia:** sigue siendo una herramienta local, en `tools/`, sin publicar. No reemplaza el
panel público de Netlify (agregados) — es complementario, para uso interno del equipo.

## Plan por fases

### Fase 1 — Cambiar la fuente de datos (Sheets → Supabase), misma UI ✅ COMPLETADA 2026-07-21
Reescribir `leer_h2test()`/`leer_avance()`/`leer_retirados()` para leer de Supabase en vez de
gspread: `participants` + `enrollments` + `courses` (reemplaza h2test/Avance) y
`cohorte_ingresos`/`aprobacion_cursos` (reemplaza el cruce manual de aprobación). Mismo
`.env.local` raíz (`SUPABASE_SERVICE_ROLE_KEY`) que ya usan `sync_*` — la GUI pasa a ser un
**consumidor de solo lectura** del mismo proyecto, nunca escribe.

**Por qué primero:** de inmediato hereda gratis la cohorte canónica, Emoflow y asistencia sin
tocar la UI — valor inmediato con el menor riesgo (no se toca ninguna vista existente).

**Qué se hizo (2026-07-21):**
- `leer_h2test(gc)` → **`leer_h2test(supa)`**: ahora hace GET a `/enrollments` con embeds
  PostgREST `participants!inner(nombre,email,q10_id)` + `courses!inner(nombre,cohorte)`
  (mismo patrón que `alerta_desercion.py`), filtrado a la **cohorte actual**. La cohorte
  actual se detecta automáticamente como el máximo `cohorte` presente en `cohorte_ingresos`
  (`_cohorte_actual()`) — sin hardcodear el año, mismo principio de escalabilidad del resto
  del panel. Retorna exactamente el mismo shape `(q10_jc, q10_mr, cursos_info)` de antes, así
  que ningún tab/vista/KPI tuvo que cambiar. La clasificación jc/mr/stand se sigue resolviendo
  con `tools/course_config.json` en local (no con `courses.programa` de Supabase), para que el
  Tab Admin siga surtiendo efecto inmediato al presionar "Actualizar datos".
- Nuevo cliente REST mínimo `_Supa` + `conectar_supabase()` + `_cargar_env_local()` dentro de
  `panel_riesgo_gui.py` (mismo patrón `.env.local` + `SUPABASE_SERVICE_ROLE_KEY` +
  User-Agent `panel-datos-etl/1.0` que `sync_*.py`/`alerta_desercion.py`/`reporte_puntaje.py`).
  Solo lectura (GET) — la GUI nunca escribe en Supabase.
- **`leer_avance(gc)` — decisión: se mantiene sin cambios**, sigue leyendo la pestaña Sheet
  `Avance` (entrada manual de monitores). Motivo: Supabase (`participants`/`enrollments`) ya
  viene de Q10 directo — la misma fuente que antes poblaba h2test —, así que no puede
  sustituir a Avance sin vaciar de sentido el tab "Diferencias", cuyo propósito es justo
  comparar el registro automático de Q10 contra el seguimiento manual. Migrarla habría
  requerido una tabla nueva en Supabase + un sync propio, fuera del alcance de "cambiar SOLO
  la fuente de datos, sin tocar la UI". Reevaluar en una fase futura si se decide
  institucionalizar el seguimiento manual en Supabase.
- **`leer_retirados(gc)` — NO cambia** (como estaba previsto): los retirados individuales no
  existen como filas en `participants` (limitación de Q10), Supabase solo tiene el agregado
  (`cohorte_ingresos.retirados`). Sigue leyendo la pestaña Sheet `Retirados` tal cual, con un
  comentario en el docstring explicando por qué es la excepción.

**Verificación:** script standalone `tools/verificar_supabase_panel_riesgo.py` (no lanza la
GUI) — importa `panel_riesgo_gui` y llama `conectar_supabase()` + `leer_h2test(supa)`,
comparando contra `cohorte_ingresos`/`aprobacion_cursos`:
- JC: `leer_h2test` = 777 estudiantes == `cohorte_ingresos.activos` = 777 (cohorte 832 = 777
  activos + 57 retirados) ✅
- MR: `leer_h2test` = 283 == `cohorte_ingresos.activos` = 283 ✅ (la cifra de referencia "282"
  documentada en `panel-datos-etl.md` queda 1 por debajo de la cifra viva actual — no es un
  bug de esta migración, ambas fuentes de Supabase concuerdan entre sí exactamente)
- 9/9 cursos comparados 1:1 contra `aprobacion_cursos.activos` (cruce por nombre normalizado,
  ya que `courses.nombre` viene del header crudo de Q10 y `aprobacion_cursos.curso` de
  `export_aprobacion.py` con formato distinto) — **0 diferencias**.

### Fase 2 — Tab nuevo "Decisiones" con botones de consulta
Lista inicial de botones (ampliable, cada uno = una vista pre-armada sobre las tablas/vistas
de Supabase que ya existen — no requiere SQL nuevo del usuario):

| Botón | Fuente | Qué muestra |
|---|---|---|
| **Estudiantes en riesgo (puntaje bajo)** | `v_puntaje_estudiante` | Percentil bajo en avance+ingresos Emoflow, cohorte actual |
| **Sin registro Emoflow** | `emoflow_ingresos` LEFT JOIN `participants` | Quiénes no tienen ingresos registrados (excluidos del ranking por regla de negocio) |
| **Asistencia Zoom < 70%** | `asistencia_promedio` | Umbral ya usado en `ZOOM-ASISTANCE`/formato condicional |
| **En banda de riesgo (0-25% avance)** | `aprobacion_cursos` (bandas) | Activos por curso en banda roja |
| **Retirados recientes** | `cohorte_ingresos` + pestaña Retirados | Ya existe como tab, se integra al mismo lenguaje de botones |
| **Filtro por ciudad** | `grupo_ciudad` (BD monitorias) | Cualquiera de los botones anteriores, acotado a una ciudad — mismo patrón del panel público |

Cada botón = una función `consulta_xxx()` que arma el filtro SQL/PostgREST y llena la tabla
dinámica ya existente (`TablaFiltrable`) — se reusa el componente, no hay que rehacer UI.

### Fase 3 — Pulido
- Doble clic en un estudiante → ficha completa (avance por curso, Emoflow, asistencia,
  puntaje) — hoy el popup solo mezcla Q10+Avance+asistencia, falta Emoflow y puntaje.
- Exportar CSV de cualquier vista de Decisiones (ya existe el patrón en `TablaFiltrable`).
- Semáforo visual (verde/ámbar/rojo) reusando los umbrales ya definidos en el proyecto
  (70% asistencia, banda 0-25 avance, sin Emoflow) — no inventar umbrales nuevos.

## Decisiones de diseño clave
- **Tkinter, no web** (decisión de Samuel 2026-07-21): evita exponer PII fuera de la red
  local y evita construir autenticación para un panel interno. Revisar esta decisión si el
  equipo crece y necesita acceso remoto — en ese momento sí tendría sentido una web interna
  con login, reusando el stack de `panel-datos-rofe`.
- **service_role, no anon key:** esta herramienta necesita ver PII (nombre/cédula/email) —
  igual que los scripts `sync_*`, nunca se expone al frontend público.
- Los "botones de decisión" son vistas **fijas y curadas**, no un constructor de consultas
  libre — mantiene la promesa de "sin persona dedicada a analítica, el panel pregunta por ti".

## Gotchas anticipados
- `v_puntaje_estudiante` no tiene GRANT a anon (a propósito, tiene PII) — la GUI debe usar
  `service_role`, igual que `reporte_puntaje.py` (mismo patrón, se puede reusar su lógica de
  percentiles en vez de reescribirla).
- El filtro por ciudad en Supabase solo cubre la cohorte **actual** (2026) — igual limitación
  que el panel público, documentada en [[panel-datos-etl#Filtro por ciudad en el panel JC]].
- Retirados individuales siguen sin existir como filas en `participants` (limitación de Q10) —
  el tab Retirados debe seguir leyendo la pestaña Sheet para el detalle individual, aunque el
  resto de la GUI ya use Supabase. Documentado también en [[panel-datos-etl#Fuentes de datos aún no centralizadas]].

## Pendiente / Próximos pasos
- [x] Fase 1: reescribir las 3 funciones lectoras de `panel_riesgo_gui.py` contra Supabase
      (2026-07-21 — `leer_h2test()` migrada; `leer_avance()`/`leer_retirados()` sin cambios
      por decisión de diseño documentada arriba)
- [ ] Fase 2: implementar tab "Decisiones" con los 6 botones listados arriba
- [ ] Fase 3: ficha de estudiante ampliada + export CSV + semáforo
- [ ] Reevaluar Tkinter-vs-web si el equipo de analítica crece o necesita acceso remoto
