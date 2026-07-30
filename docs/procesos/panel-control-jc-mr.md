# Panel de Control JC/MR — herramienta interna nueva (histórico completo, PII, fuentes togglables)

> Pedido de Samuel, 2026-07-30 (sesión de auditoría de geografía JC 2026 — ver
> [[plan-visualizacion-2026-07-30]] §"Bogotá/Medellín"). Decisiones confirmadas por ronda de
> preguntas la misma tarde (ver `claude_sessions.md`). **Documento previo a ejecutar** — a
> pedido explícito de Samuel, esto se escribe ANTES de tocar código.

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
- **Se reusa, no se reescribe:**
  - `v_gui_personas` (migración 033, 2026-07-30) — vista PII por persona×programa×cohorte, ya
    resuelve la mayor parte del cruce manual. Este documento propone **extenderla**, no
    duplicarla.
  - `v_persona_360` (migración 008) — ficha individual por cédula, existe desde 2026-07-23
    **sin consumidor todavía**. Es exactamente la ficha de doble-clic que pide este plan.
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
| Asistencia Zoom | Sí | persona | `asistencia_promedio` | Cobertura parcial, PII. |
| Postulantes históricos | Sí | persona (universo **más amplio** que matriculados) | `postulantes_jc` / `postulantes_mr` | Incluye gente que **nunca matriculó** — ver decisión pendiente en §6. |
| Microcréditos MR | Sí | persona | `mr_microcreditos` | Solo MR, no es empresa patrocinadora (ver `postulantes-mr-supabase.md`). |

---

## 4. Arquitectura de datos propuesta

**Extender `v_gui_personas` en vez de crear una vista paralela** — ya cubre Q10, retiros,
Emoflow, sociodemográficos MR, empresa patrocinadora JC y microcréditos MR. Faltan 2 fuentes
para tener las 3 pedidas hoy completas:

1. `asistencia_promedio` (join por email, mismo patrón que `v_persona_360`).
2. `postulantes_jc`/`postulantes_mr` (join por cédula) — agregar `fuente_postulacion`,
   `rol_postulacion`, `fecha_creacion_postulacion` como columnas informativas.

**El toggle de fuentes es de PRESENTACIÓN en el cliente Python, no de query SQL.** La vista
siempre trae todas las columnas disponibles; la GUI decide cuáles mostrar según los checkboxes
marcados. Ventajas sobre armar queries dinámicas por combinación de fuentes:
- Prender/apagar una fuente es instantáneo — no dispara un nuevo fetch a Supabase.
- Una sola query por (programa, cohorte) cubre cualquier combinación de checkboxes.
- Reduce drásticamente la superficie de bugs (no hay que mantener N combinaciones de SQL).

---

## 5. Plan de fases

### Fase 1 — Ampliar `v_gui_personas`
Agregar `asistencia_promedio` y `postulantes_jc`/`postulantes_mr` como columnas informativas
(no como filas nuevas — ver §6). Verificar con `SET ROLE` que sigue bloqueada para
anon/authenticated (ya lo está, pero cualquier cambio a una vista PII se reverifica).

### Fase 2 — Capa de datos Python
Módulo nuevo (o extensión de `panel_riesgo_datos.py`) con una función que traiga
`v_gui_personas` para **todas** las cohortes de un programa de una sola vez (no solo la
cohorte actual, a diferencia de `leer_h2test()` hoy). Reusar `Supa`/`get_todo`.

### Fase 3 — Interfaz
Selector programa/cohorte + panel de checkboxes de fuentes + tabla con columnas dinámicas +
filtros combinables (ciudad, avance, estado). Reusar `TablaFiltrable`.

### Fase 4 — Ficha 360
Doble clic → popup que consulta `v_persona_360` por cédula. Primer consumidor real de esa
vista desde que se creó (2026-07-23).

### Fase 5 — Pulido
Exportar CSV (ya existe el patrón), semáforo visual con umbrales ya definidos en el proyecto
(no inventar umbrales nuevos — reusar 70% asistencia, banda 0-25 avance, etc.).

---

## 6. Decisión pendiente de confirmar — universo de filas al togglear "Postulantes históricos"

`postulantes_jc`/`postulantes_mr` traen un universo **más amplio** que matriculados (incluye
gente que aplicó pero nunca entró a Q10). Si se prende esta fuente, ¿la tabla:

- **(a) Recomendado — solo agrega columnas** a las personas que ya están en la tabla
  (matriculados vía Q10), mostrando su fecha/rol de postulación original cuando exista. El
  universo base sigue siendo "matriculados", igual que en todo el resto del proyecto
  (`convenciones.md`: *"Supabase `participants` = solo matriculados en Q10, nunca crear desde
  fuentes secundarias"*). No rompe la promesa ya establecida de qué es "un estudiante" en
  ningún reporte existente.
- **(b) Agrega filas nuevas** de gente que postuló pero nunca matriculó, con las columnas de
  Q10/avance/cursos vacías para esas filas. Más información, pero mezcla dos universos
  distintos (matriculado vs. solo-postulante) en la misma tabla — riesgo de que alguien lea
  "estudiantes" y en realidad haya postulantes sin matricular mezclados.

Este documento asume **(a)** como default (consistente con el resto del proyecto) — confirmar
antes de la Fase 1 si se prefiere (b).

---

## 7. Conexiones

[[plan-visualizacion-2026-07-30]] (Fase 2 pausada a favor de este documento) ·
[[panel-riesgo-mejora]] (archivado/fusionado aquí) · [[supabase-estructura]] ·
[[postulantes-mr-supabase]] · [[mapa-codigo]]
