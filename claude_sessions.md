# Bitácora de Sesiones — Claude Code

> Diario cronológico de trabajo. Se agrega una entrada al FINAL de cada sesión.
> Nunca se borra ni reescribe el historial. Formato fijo para que sea fácil de
> escanear rápido al iniciar una sesión nueva.

---

## Cómo usar este archivo (instrucciones para Claude)

Al final de cada sesión de trabajo, agrega una entrada nueva usando esta plantilla:

```
## YYYY-MM-DD — [Proceso] Título corto de lo que se hizo

**Estado:** En progreso / Completado / Bloqueado
**Proceso relacionado:** [[nombre-del-proceso]]

- Qué se hizo (2-4 líneas, lo esencial)
- Decisiones clave tomadas
- Pendiente para la próxima sesión
- Bloqueos (si aplica): qué falta y de quién depende
```

Al iniciar una sesión nueva, lee al menos las últimas 3-5 entradas antes de continuar.

---

## 2026-06-22 — [Setup] Estructura inicial del proyecto

**Estado:** Completado
**Proceso relacionado:** [[00-vision-global]]

- Se creó la estructura de carpetas base: `docs/`, `n8n-workflows/`, `skills/`.
- Se definió `CLAUDE.md` como guía de documentación automática por tarea.
- Se definió este archivo (`claude_sessions.md`) como bitácora cronológica.
- Pendiente: documentar el primer proceso real (Q10) usando esta estructura.

---

## 2026-06-23 — [Q10] Migración del proyecto BOT-Q10 a esta estructura

**Estado:** Completado
**Proceso relacionado:** [[q10-consolidacion]]

- Se migró el proyecto BOT-Q10 (ya operativo en producción desde 2026-06-22) a esta estructura centralizada.
- Archivos creados: `scripts/q10-consolidacion/` con `q10_to_sheets.py`, `setup_headers.py`, `requirements.txt`, `.gitignore`.
- Workflow exportado a `n8n-workflows/q10-consolidacion.json` con ruta del comando actualizada al nuevo path.
- `docs/procesos/q10-consolidacion.md` completada con toda la información real (flujo, endpoints, decisiones, gotchas).
- `docs/convenciones.md` actualizada con 3 patrones nuevos: SSL corporativo, Q10 login multi-paso, expresiones n8n 2.x.
- `docs/00-vision-global.md` actualizada: Q10 movido a completados, stack corregido (n8n local + cloudflared, no Docker).
- Pendiente para próxima sesión: copiar `credenciales_service_account.json` y `.env` a `scripts/q10-consolidacion/`, reimportar workflow en n8n con la ruta nueva, y escribir headers fila 1 con `setup_headers.py --confirmar`.

---

## 2026-06-23 — [Sistema] Upgrade del sistema de documentación y skills

**Estado:** Completado
**Proceso relacionado:** transversal (afecta todos los procesos)

- Evaluación de la documentación: 6.5/10 escalabilidad, 2/10 para guiar operadores (H2Test inexistente, Power BI ausente).
- Creadas 3 skills invocables: `/compact` (modo keyword, ahorra tokens), `/proceso-nuevo`, `/doc-sync`.
- Creados 2 hooks hookify: protección de `.env`/credenciales (bloqueo) y recordatorio de documentación al cerrar.
- Creado `runbooks/q10-actualizar.md` — guía para operadores no técnicos del proceso Q10.
- Creada memoria persistente del proyecto (4 archivos en `.claude/projects/.../memory/`).
- CLAUDE.md ampliado con mapa de arquitectura real y tabla de skills.
- Pendiente: configurar H2Test en `MAPEO_GRUPOS` de `q10_to_sheets.py` y documentar conexión con Power BI.

---

## 2026-06-24 — [Q10] h2test operativa + evaluación Looker Studio

**Estado:** Completado
**Proceso relacionado:** [[q10-consolidacion]]

- h2test confirmada operativa: datos de Q10 subiendo correctamente a la pestaña `h2test` del Sheet de Fundación ROFÉ.
- Setup h2test completado: Service Account con acceso Editor, headers fila 1 escritos, `/actualizar h2test` funcional.
- Decisión de visualización: se evalúa Looker Studio (datastudio.google.com) como alternativa a Power BI — sin código extra, conector nativo Google Sheets.
- Documentados pasos de conexión y visualizaciones sugeridas en `docs/procesos/q10-consolidacion.md`.
- Pendiente: armar el informe en Looker Studio y regenerar token del bot con BotFather.

---

## 2026-06-24 — [Q10] Decisión de visualización: dashboard web GitHub Pages

**Estado:** Completado (decisión) / En construcción (implementación)
**Proceso relacionado:** [[q10-consolidacion]]

- Descartadas opciones Looker Studio y Power BI como visualizadores.
- Decisión: Python lee h2test → genera `data.json` → commit a GitHub → GitHub Pages muestra el dashboard.
- Ventaja clave: credenciales nunca salen del PC, JSON solo tiene datos agregados (sin datos personales).
- Contenido definido: tabla POR CURSO (8 cursos) + 3 scorecards de anomalías.
- Pendiente próxima sesión: crear `export_stats.py`, repo GitHub Pages, y sitio HTML con Chart.js.

---

## 2026-06-24 — [Q10] Dashboard web: export_stats.py + index.html funcionales

**Estado:** Completado (archivos listos) / Pendiente de activar GitHub Pages
**Proceso relacionado:** [[q10-consolidacion]]

- Problema resuelto: `export_stats.py` original leía pestaña `estadísticas` que no existía → fallo garantizado.
- Solución: reescrito para leer `h2test` directamente y computar todas las estadísticas en Python.
- `index.html` reemplazado: dashboard completo con tabla POR CURSO (barras de progreso CSS) + scorecards de anomalías.
- Descartada migración a admin/panel externo — flujo definitivo: h2test → JSON → GitHub Pages.
- Pendiente: (1) `git push` al repositorio remoto para activar GitHub Pages, (2) primera corrida de `export_stats.py` para generar `data.json`, (3) configurar Settings → Pages → main → /docs en GitHub.

---

## 2026-06-24 — [Asistencia] Script de extracción de hoja de asistencias

**Estado:** Completado (script listo) / Pendiente de correr + compartir Sheet
**Proceso relacionado:** nuevo proceso — dashboard asistencia manual

- Creado `scripts/q10-consolidacion/export_asistencia.py` — lee pestaña `asistencias` del Sheet `1ggzoJeZR3fS6AwRCLoGeYA5HEp_B7zvOwFGlGwny0l8`.
- Parsea estructura de doble encabezado: fila 1 = nombres de módulos, fila 2 = sub-columnas, filas 3+ = datos.
- Genera `docs/asistencia/data.json` con asistentes por sesión + lista de estudiantes (para cruce mañana).
- `index.html` del usuario va en `docs/asistencia/index.html`.
- Pendiente: compartir Sheet con Service Account, correr script, subir index.html.

---

## 2026-06-24 — [Dashboard] Fase 2 completa: dashboard unificado + privacidad + panel de riesgo

**Estado:** Completado (Fase 2) / Listo para Fase 3
**Proceso relacionado:** [[dashboard-web]]

- `docs/dashboard/index.html` reemplazado por dashboard 3 pestañas unificado: Estadísticas Q10 · Asistencia · Comparativo.
- Semáforo implementado: ≥80% verde/Satisfactorio, 60-79% amarillo/En riesgo, <60% rojo/Atención.
- `docs/asistencia/data.json` saneado para publicación: eliminados todos los arrays `estudiantes` con PII.
- `.gitignore` actualizado: `tools/`, `local_data/`, `*_personal.json`, `*_estudiantes.json` nunca a GitHub.
- `tools/panel_riesgo.py` creado: script local que cruza hoja manual × h2test por email, genera 4 secciones de reporte y exporta CSVs con `--csv`. Detecta automáticamente SIN MATCH, avance 0% vs presencia física, y casos de atención.
- Decisión de cruce: por email (correo electrónico), no por ID — los IDs son incompatibles entre sistemas.
- Pendiente Fase 3: (1) compartir Sheet asistencias con Service Account, (2) correr export_asistencia.py con datos reales, (3) validar cruce panel_riesgo.py, (4) activar GitHub Pages en Settings → Pages → main → /docs.

---

## 2026-06-24 — [Dashboard] Fase 3: datos reales + pestaña Avance + dashboard en producción

**Estado:** Completado
**Proceso relacionado:** [[dashboard-web]]

- Descubierto y corregido doble encabezado en h2test: `export_stats.py` reescrito con `detectar_grupos()`.
- Corrección crítica de fuente: la "hoja manual" es la pestaña **Avance** (% progreso por curso), no la de sesiones presenciales. Creado `export_avance.py` desde cero.
- Tab 2 del dashboard renombrado "Avance Manual"; Tab 3 Comparativo reescrito con mapeo `ALIAS_Q10` (nombres cortos Avance ↔ nombres largos Q10).
- SSL corporativo bloqueaba git push → resuelto con `git config --local http.sslBackend schannel`; documentado en `convenciones.md`.
- Dashboard publicado en producción: `fundacion-rofe.github.io/Estadisticas/dashboard/`.
- Datos reales: 863 estudiantes únicos, 94.06% promedio general Avance; 4,563 únicos Q10.

---

## 2026-06-24 — [Sistema] Plan Maestro — Cerebro de Conocimiento completado

**Estado:** Completado
**Proceso relacionado:** transversal

- PASO 1: Eliminado `automatizaciones-empresa/` (copia huérfana, nunca en git). Borrado `docs/otro-proceso-si-aplica.md` y `docs/Untitled.base`.
- PASO 2: Creado `docs/procesos/mapa-codigo.md` — índice esquemático de los 7 scripts (propósito, servicios, funciones, variables, gotchas).
- PASO 3: `CLAUDE.md` reescrito (arquitectura real, tabla de componentes, convenciones actualizadas). `docs/00-vision-global.md` reescrito como Home de Obsidian con diagrama ASCII y tabla de estado por proceso.
- PASO 3.3: Sección "## Conexiones del sistema" añadida a los 3 archivos de proceso. Sección "## Contingencia manual" añadida donde faltaba.
- PASO 4: `convenciones.md` actualizado con sección "Doble encabezado en Google Sheets" y enlace bidireccional. Stale refs corregidos (Looker Studio → GitHub Pages, Docker → cloudflared, estadísticas tab → h2test).
- Sin huérfanos: todos los `.md` en `docs/` tienen enlace de entrada desde `00-vision-global.md`.

---

## 2026-06-24 — [Q10] Pipeline completo — eliminado el .exe del flujo de automatización

**Estado:** Completado (pendiente: reimportar workflow en n8n y probar end-to-end)
**Proceso relacionado:** [[q10-consolidacion]]

- Creado `organizador_headless.py` — extrae toda la lógica de negocio de `organizador_Q10.py` sin GUI: lee H1Test, ordena por curso, escribe h2test en bloques horizontales (5 cols por curso + 2 cols separador), genera pestaña Observaciones (SIN MATCH / SIN CURSO / AVANCE 0% / IRREGULAR) y pestaña Estadisticas.
- Workflow n8n actualizado: `q10_to_sheets.py` ahora siempre usa `--grupo h1test`; `/actualizar h2test` encadena organizador → export_stats → export_avance → GitHub Pages; `/actualizar h1test` solo extrae (para revisión sin publicar).
- Documentación actualizada: flujo de 3 fases en `q10-consolidacion.md`, nueva entrada en `mapa-codigo.md`, diagrama ASCII corregido en `00-vision-global.md`.
- **Pendiente:** reimportar `n8n-workflows/q10-consolidacion.json` en la instancia n8n local (ID producción actual: `Rblg81qifVshsRae`), desactivar el anterior y activar el nuevo. Luego probar con `/actualizar h2test` en Telegram.

---

## 2026-06-25 — [Q10] Pipeline n8n validado + columna Estado A/I incorporada al flujo completo

**Estado:** Completado
**Proceso relacionado:** [[q10-consolidacion]], [[dashboard-web]]

- Pipeline end-to-end confirmado funcional (ejecución n8n ID 11, commits a las 5:07 PM del 24/06).
- Sesión anterior completada (pipeline OK) + nueva tarea: incorporar campo `Estado` (A=activo, I=inactivo) al flujo completo.
- `q10_to_sheets.py`: removido filtro `Estado=A` del payload Estudiantes (ahora retorna todos los estados), campo `Estado` añadido a `columnas_deseadas` y `COLS_FINALES` → H1Test tendrá columna 7 `Estado`.
- `organizador_headless.py`: dedup por `(Identificacion, Curso)` keepMax(Avance) añadida; Estado en bloques h2test (6 cols); categoría `NO HABILITADO` en Observaciones; `total_habilitados` en Estadisticas y en línea RESUMEN.
- `export_stats.py`: `detectar_grupos` detecta `offset_estado`; `procesar_h2test` computa `ids_habilitados` (Estado=A/vacío); `generar_json` añade `total_habilitados` al JSON.
- `docs/dashboard/index.html`: KPI "Estudiantes activos" = `total_habilitados`, subtexto "de N matriculados"; ANOM_DESC con `NO HABILITADO`.
- Workflow n8n actualizado vía API (mensaje Telegram ahora muestra "Activos: X | Total: Y").
- Ejecutar `/Actualizar Q10` para ver datos reales con la separación activos/inactivos.

---

## 2026-06-25 — [Q10] Dos bugs críticos corregidos + pipeline end-to-end validado

**Estado:** Completado
**Proceso relacionado:** [[q10-consolidacion]], [[dashboard-web]]

- **Bug 1 — h2test clear insuficiente:** `values_clear("A1:Z1000")` solo cubre 26 cols × 1000 filas; h2test necesita 72 cols y 3400+ filas. Datos viejos persistían → export_stats leía 8845 filas en lugar de 3415 y todos los conteos salían iguales (~4554). Fix: `ws_h2.clear()`.
- **Bug 2 — dedup por Identificacion:** mismo estudiante tiene Código distinto en cada período → el dedup no eliminaba duplicados cross-period. Fix: dedup por `(Email, Curso)` keepMax(Avance).
- Pipeline validado con ground truth H1Test: 1145 únicos con curso (2026) + 3409 histórico = 4553 total DB.
- `export_stats.py` y `export_avance.py` corridos y pusheados: dashboard en producción muestra valores correctos.
- Commit `a573690` con todos los cambios del pipeline Estado + fixes.

---

## 2026-06-25 — [Q10] Schedule 12h + arranque automático al iniciar sesión

**Estado:** Completado
**Proceso relacionado:** [[q10-consolidacion]]

- **Schedule Trigger 12h** añadido al workflow n8n (`Rblg81qifVshsRae`): camino paralelo independiente al de Telegram — corre q10_to_sheets → organizador → export_stats → export_avance sin notificación Telegram (errores visibles en log de n8n). Push vía API con desactivación previa (el tunnel expirado bloqueaba el PUT con workflow activo).
- **Task Scheduler** registrada en Windows: tarea "Iniciar n8n ROFE" ejecuta `iniciar_n8n.bat` (minimizado) al iniciar sesión de EstudiantesJC sin intervención manual. Registrada sin `RunLevel Highest` (no requiere admin).
- Patrón "trigger dual Schedule + Telegram" documentado en [[convenciones]] como reutilizable para otros procesos.
- `docs/00-vision-global.md`, `docs/convenciones.md` y `docs/procesos/q10-consolidacion.md` actualizados con nuevo disparador, datos correctos y checklist al día.

---

## 2026-06-25 — [Dashboard] Identidad visual ROFÉ + separación SIN PROGRESO / AVANCE 0%

**Estado:** Completado
**Proceso relacionado:** [[dashboard-web]], [[q10-consolidacion]]

- `docs/dashboard/index.html` rediseñado con identidad visual Fundación ROFÉ: paleta oficial (#406C9E, #EEC935, #D1793F, #C12D4C, #6EA050), tipografía Gilroy/Century Gothic, fondo blanco, logo en header y footer con eslogan y misión.
- Logo subido: `docs/img/logo_rofe_aplicacion2.png` (70KB, Aplicación 2 web/digital — fondo blanco).
- **Bug corregido — SIN ETIQUETA:** se contaban filas de columnas estructurales sin nombre (artifact del Sheet), no datos reales. Eliminado completamente de `export_avance.py`.
- **Separación SIN PROGRESO / AVANCE 0%:** celda vacía → SIN PROGRESO (ID presente, sin dato); "0" literal → AVANCE 0%. Fix en `_limpiar_porcentaje`: verificar `av_raw.strip()` antes de parsear.
- Resultado confirmado: SIN PROGRESO=0 (hoja manual sin celdas vacías), AVANCE 0%=170, AVANCE IRREGULAR=2.
- Descripciones ANOM_DESC actualizadas en Tab 1 (Q10) y Tab 2 (Avance) para reflejar el concepto paralelo: "ID sin curso" ↔ "ID sin avance".
- Commit `57830b6`: `export_avance.py` + `index.html` en producción.

---

## 2026-06-25 — [Panel Riesgo] Diagnóstico duplicados DB manual + Tab Errores DB en GUI

**Estado:** Completado
**Proceso relacionado:** [[dashboard-web]]

- Consulta puntual sobre `yovadisherrera05@gmail.com`: Q10 confirma EMPRENDIMIENTO en 0% (74% promedio real). El 78.4% que mostraba el GUI venía de un duplicado de "Emprendimiento" al 96% en la hoja Avance manual.
- Script `detectar_duplicados_avance.py` (en scratchpad) detectó 19 estudiantes con curso duplicado — todos en "Emprendimiento" — causado por un segundo bloque de columnas del mismo nombre en la hoja. 6 casos con valores distintos entre las dos entradas (conflicto real).
- **Nuevo tab "⚠ Errores DB"** agregado a `tools/panel_riesgo_gui.py`: tabla de 5 columnas (Email, Nombre Q10, Curso, Manual dup, Q10 %) con filas rojas para valores distintos y amarillas para mismo valor duplicado. Card de conteo añadida al Resumen.
- Decisión: duplicados quedan marcados en el GUI como error de DB manual — la corrección en el Sheet la hace el equipo manualmente. Q10 es la fuente autoritativa.

---

## 2026-06-26 — [Q10] Diagnóstico workflow inactivo + fix bat iniciar_n8n

**Estado:** Completado
**Proceso relacionado:** [[q10-consolidacion]]

- Workflow encontrado inactivo (`active: false`) — nunca había disparado el schedule de 4h. Causa: quedó desactivado tras el PUT de actualización del 2026-06-25 y no se reactivó.
- Cloudflared también estaba caído — activar el workflow sin él falla con "Failed to resolve host" porque n8n intenta registrar el webhook de Telegram con la URL del tunnel.
- **Fix `iniciar_n8n.bat`:** reemplazado `wmic process` (deprecated y colgado en Windows 11) por `Get-CimInstance Win32_Process` vía PowerShell — instantáneo y confiable.
- **Loop de monitoreo mejorado:** cada 60s verifica cloudflared (lo reinicia si cae, espera 20s por nueva URL) y verifica estado del workflow (lo reactiva automáticamente si está inactivo).
- Gotcha documentado en [[q10-consolidacion]]: WEBHOOK_URL se inyecta al arrancar n8n — si cloudflared cambia URL, hay que reiniciar el bat completo para que Telegram registre la nueva URL.

---

## 2026-06-26 — [Q10] Refactor arquitectura — Consolidado como única fuente

**Estado:** Completado
**Proceso relacionado:** [[q10-consolidacion]]

- Descubierto vía HAR + 3 Excel en `excels/`: el endpoint `/ConsolidadoEducacionVirtual` ya incluye toda la información del estudiante (`Número identificación estudiante`, `Nombres/Apellidos estudiante`, `Celular`, `Email`). El endpoint `/Estudiantes` era redundante.
- **Cambio arquitectural en `q10_to_sheets.py`:** eliminado `descargar_estudiantes()` y el LEFT JOIN por email. Reemplazado por `mapear_columnas()` que extrae todo directamente del Consolidado. Flujo: login → Consolidado × 3 periodos → mapear → H1Test.
- 3 periodos activos 2026 confirmados: 21=Logica-Nivel 2, 22=Habilidades-Nivel 1, 23=Unico MR. Periodos 20 y 24 devuelven `not_results`.
- Estado="A" hardcodeado en `mapear_columnas()` — `archivado=false` en el POST ya filtra inactivos.
- Documentación actualizada: `mapa-codigo.md`, `q10-consolidacion.md` (flujo Fase 1, tabla endpoints, decisiones de diseño).
- Pendiente: correr `/Actualizar Q10` para validar que H1Test se llena correctamente con la nueva lógica.

---

## 2026-06-26 — [Dashboard] Panel Mujeres ROFÉ + separación visual JC / MR

**Estado:** Completado
**Proceso relacionado:** [[dashboard-web]]

- **Panel `docs/mujeres-rofe/index.html`:** página independiente con identidad visual Mujeres ROFÉ (paleta rose/warm: #C12D4C, #D1793F, #EEC935; bombilla SVG como decoración). Lee `../dashboard/data.json` y filtra los 2 cursos MR por nombre exacto (`CURSOS_MR` array en JS). Muestra 4 KPIs, 2 tarjetas de curso con barras animadas, panel comparativo, footer oscuro.
- **`docs/dashboard/index.html`:** link "Mujeres ROFÉ ↗" añadido en la barra de tabs. Cursos MR excluidos con `filtrarJC()` en JS — `data.json` permanece con los 8 cursos para que el panel MR siga funcionando.
- **`tools/panel_riesgo_gui.py`:** Tab 5 "💡 Mujeres ROFÉ" agregado con estilos rose; tabs 1-4 ahora solo muestran estudiantes JC. `leer_h2test()` devuelve `(q10_jc, q10_mr)` separados por `_es_curso_mr()`.
- Decisión de diseño: `data.json` NO se divide en dos archivos — el panel MR lee el mismo JSON que el dashboard JC y filtra en JS. Esto mantiene un solo script `export_stats.py` sin lógica de separación.

---

## 2026-06-26 — [Panel Riesgo + Dashboard] Refactor mayor GUI + tab Admin + course_config

**Estado:** Completado
**Proceso relacionado:** [[dashboard-web]]

- **`tools/panel_riesgo_gui.py` reescrito completamente:** de 5 tabs → 4 tabs (Resumen, Atención, MR, Admin). Eliminados: "Sin match manual", "Avance 0%" y "Errores DB". Tab Atención: ahora genera una fila por (estudiante, curso en riesgo) en lugar de una por estudiante — permite filtrar por curso. Tab MR: una fila por estudiante único, doble clic abre popup con todos sus cursos. Tab Admin: lista scrollable de todos los cursos con ComboBox JC/MR/Stand-by, botón Guardar → escribe `tools/course_config.json`.
- **`tools/course_config.json` creado:** clasifica los 8 cursos actuales (6 JC, 2 MR, 0 stand). Fuente de verdad para clasificación de programas — tiene precedencia sobre los keywords de fallback.
- **`scripts/q10-consolidacion/export_stats.py`:** agrega `_cargar_config_cursos()` + `_clasificar_curso()` que usa config primero y keywords como fallback. `procesar_h2test()` ahora extrae un tercer grupo `cursos_stand`. `generar_json()` incluye nueva sección `"stand"`. `main()` actualizado para desempaquetar 12 valores.
- **`docs/dashboard/index.html`:** Tab 4 "Admin" añadido. `renderAdmin(d)` muestra resumen por programa (tarjetas KPI con color por programa), gráfico de barras horizontales para todos los cursos (color por programa), tabla detalle. Lee `d.por_curso` (JC), `d.mr.por_curso` (MR) y `d.stand.por_curso` (Stand-by).
- Decisión: la clasificación vive en `tools/course_config.json` (local, gitignoreado potencialmente), no hardcodeada — permite que Samuel añada nuevos cursos sin tocar código.

---

## 2026-06-26 — [Panel Riesgo + Dashboard] KPI cards clickeables + vistas dinámicas JC y MR

**Estado:** Completado
**Proceso relacionado:** [[dashboard-web]]

- **Tab 💡 Mujeres ROFÉ — 6 vistas dinámicas:** las 6 tarjetas KPI superiores se convirtieron en botones (cursor hand2, bind `<Button-1>`). Al hacer clic la tarjeta activa se resalta con `PRIMARY_LT`. Cada vista regenera la tabla: MUJERES (283 únicas), CURSOS (resumen 2 cursos), PROMEDIO (nota por curso + promedio), ≥ 80% OK, EN RIESGO 60–79%, AVANCE 0%. Conteos por estudiante único (no por matrícula) usando `student_stats` agrupado por email.
- **Tab 🎓 Jóvenes creaTIvos (antes "Resumen") — 6 vistas dinámicas:** mismo patrón KPI clickeable. Vistas: EN Q10 JC (todos en plataforma), MATCH AMBAS (cruzados manual+Q10), ATENCIÓN (cursos en riesgo), AVANCE 0%, SIN MATCH (en Q10 sin registro manual), OK ✓. La pestaña pasó de mostrar un resumen estático a ser completamente interactiva.
- **Exportar CSV selectivo:** `_exportar_csv()` detecta el tab activo y la vista activa (`_jc_vista_activa`, `_mr_vista_activa`) → descarga solo la tabla visible con nombre descriptivo (ej. `mr_ok_20260626.csv`). Tab Admin bloqueado.
- **Gotcha confirmado:** AVANCE 0% en data.json = 215 es por matrícula. En el GUI: 211 estudiantes únicas con avg=0%, 72 con avg>0%. El panel es correcto — la distinción se documenta en [[dashboard-web#Gotchas]].
- Documentación final actualizada: `dashboard-web.md` (reescritura completa), `mapa-codigo.md` (panel_riesgo_gui.py 4 tabs + course_config.json), `00-vision-global.md` (flujo y tabla de procesos).

---

## 2026-06-30 — [Panel Riesgo] Tab Diferencias + explicación discrepancia dashboard vs GUI

**Estado:** Completado
**Proceso relacionado:** [[dashboard-web]]

- **Diagnóstico discrepancia "AVANCE 0%":** dashboard GitHub muestra 167 por *matrícula* (una persona en 6 cursos todos a 0% = 6); panel GUI muestra 6 porque solo cuenta estudiantes *únicos* que están en AMBAS fuentes (Q10 ∩ Manual) con avance 0% en todos sus cursos. Diferencia documentada en `dashboard-web.md#gotchas`.
- **Nuevo tab "🔀 Diferencias"** agregado a `tools/panel_riesgo_gui.py` (tab índice 3). Tres vistas KPI clickeables: "EN Q10 SIN registro manual" (= `sin_match_manual` de `cruzar()`), "EN MANUAL SIN registro Q10" (nuevo: `ea - eq`), "EN AMBAS fuentes" (tabla completa de cruzados). Permite identificar si la diferencia es error de captación en Q10 o en manual.
- `leer_avance()` actualizado para capturar campo `nombre` de la pestaña Avance (antes se perdía).
- `cruzar()` añade clave `"solo_manual"` con estudiantes en Avance pero no en Q10.
- `_exportar_csv()` actualizado para soportar tab índice 3.


## 2026-06-30 — [Pseudonimizador] Arquitectura definida + documentación del plan semanal

**Estado:** En progreso (Fase 1 completada)
**Proceso relacionado:** [[pseudonimizador]]

- **Proceso nuevo iniciado:** herramienta de pseudonimización para compartir datos con IA sin violar privacidad.
- **Decisión de arquitectura:** app web estática en `docs/pseudonimizador/index.html` → GitHub Pages, cero instalación, procesamiento 100% en el navegador (ningún byte sube a servidores).
- **Motor de encriptación:** HMAC-SHA256(valor + clave_personal) → primeros 12 hex chars. Determinístico (misma cédula = mismo hash en todas las pestañas → IA puede cruzar registros). Reversible mediante diccionario .json descargado por el usuario. Auditable: cada persona tiene clave propia.
- **Flujo:** usuario → codificador → [xlsx para IA + .json privado] → IA hace cambios → usuario → decodificador → datos reales → DB original.
- **Multi-formato:** xlsx, xls, csv (vía SheetJS desde CDN).
- **Clave personal por usuario:** auditabilidad — si hay mal manejo se sabe quién generó el archivo.
- **Plan semanal documentado** en [[pseudonimizador]] con 5 fases: UI base → motor codificación → motor decodificación → buscador + UX → deploy y demo.
- Pendiente columna `Retirados` en Q10 (decisión del equipo) — no bloquea el pseudonimizador.

---

## 2026-06-30 — [Pseudonimizador] App completa construida — Fase 2+3+4 en una sesión

**Estado:** Lista para deploy (pendiente push a GitHub Pages y prueba con equipo)
**Proceso relacionado:** [[pseudonimizador]]

- **`docs/pseudonimizador/index.html` creado:** app de una sola página, ~520 líneas HTML+CSS+JS.
- **Tab Codificar:** pasos numerados (identidad → archivo → columnas → descargar). Drag-and-drop. SheetJS para leer xlsx/xls/csv. Detección automática PII por nombre de columna (regex) y por contenido (>50% coincide con emails/cédulas/celulares). Checkboxes por pestaña y por columna. HMAC-SHA256 vía Web Crypto API nativa (sin dependencias extra). Genera Excel codificado + .json con metadata (usuario, fecha, pestañas procesadas, columnas protegidas, diccionario pseudónimo→real).
- **Tab Decodificar:** upload par (Excel modificado + .json). Sustituye pseudónimos → valores reales en todas las celdas. Descarga `_restaurado.xlsx`.
- **Tab Buscar:** carga .json → búsqueda bidireccional (valor real → pseudónimo o pseudónimo → valor real).
- **Decisión:** pseudónimos de 16 chars hex (64 bits de entropía HMAC-SHA256) — suficiente para evitar colisiones accidentales y opaco para la IA.
- **Prueba con equipo y push a GitHub Pages pendientes para Fase 5.**


## 2026-06-30 — [Pseudonimizador] Web Worker para archivos de 22 MB / 44 pestañas

**Estado:** Completado
**Proceso relacionado:** [[pseudonimizador]]

- **Problema raíz identificado:** `runEncode` y `runDecode` acumulaban las 44 pestañas en el objeto `newWb` del hilo principal hasta que `XLSX.write` las serializaba todas juntas — pico de ~600 MB que reventaba el heap del navegador con OOM.
- **Solución:** todo el procesamiento (fases Analizar → HMAC → Reemplazar → Escribir) migrado a un **Web Worker inline** (Blob URL generada en runtime). El Worker tiene su propio heap, aislado de la UI. `XLSX.write` usa `type:'uint8array'` para devolver un `ArrayBuffer` transferible sin copia.
- **Barra de progreso** añadida al overlay de carga — muestra avance por pestaña en cada fase.
- Commit `9c6ffb3` · deploy a GitHub Pages automático.
- Pendiente: demo con el equipo (único ítem de Fase 5 sin completar).

## 2026-07-01 — [Pseudonimizador] Auditoría de seguridad + 4 correcciones críticas

**Estado:** Completado
**Proceso relacionado:** [[pseudonimizador]]

- **Auditoría externa** (Claude + ChatGPT + Gemini) sobre el archivo `_codificado.xlsx` real detectó fugas de PII: columna "Nombres" (plural) no encriptada, credenciales en texto plano, emails en campos de texto libre, y explosión de tamaño 22 MB → 202 MB.
- **Fix 1 — detección PII ampliada:** `\bnombre\b` → `\bnombres?\b`; añadidos `contraseña`, `credencial`, `clave`, `password`, `foto`, `imagen`, `rostro`; valores: prefijos `+NNN` e URLs `http/https`.
- **Fix 2 — emails en texto libre:** Fase 1 del Worker ahora escanea con regex en todas las columnas (no solo PII marcadas); Fase 3 los reemplaza inline.
- **Fix 3 — explosión de tamaño:** reemplazo directo celda-a-celda (`for addr in ws`) en lugar de rebuild AoA con `defval:''`. Preserva estructura dispersa del xlsx original.
- **Fix 4 — tipo XLSX.write:** `uint8array` no existe en SheetJS 0.18.5 → corregido a `buffer`.

## 2026-07-01 — [Pseudonimizador] Tab "Pegar texto" con codificación y decodificación

**Estado:** Completado
**Proceso relacionado:** [[pseudonimizador]]

- **Nuevo tab "📋 Pegar texto"** para rangos simples sin subir archivo completo.
- **Codificar:** identidad → pegar TSV (Ctrl+C desde Excel/Sheets) → seleccionar columnas → copiar resultado codificado + descargar `.json`. Misma clave HMAC → pseudónimos compatibles con el flujo de archivo.
- **Decodificar (misma pestaña):** cargar `.json` → pegar TSV codificado → restaurar → copiar. Incluye decodificación de pseudónimos embebidos dentro de texto (regex `[0-9a-f]{16,20}`).
- Crypto corre en hilo principal (datos pequeños, no necesita Worker).
- Commits `6888a8f` y `bd33d3a` · en producción GitHub Pages.

---

## 2026-07-01 — [Zoom Asistencia] Arquitectura revisada + credenciales S2S listas

**Estado:** En progreso
**Proceso relacionado:** [[zoom-asistencia]]

- **Revisión de arquitectura:** trigger cambiado de Google Calendar a Webhook Zoom
  (`meeting.ended`); endpoint cambiado de `/report/meetings/{id}/participants` (reportes
  consolidados, lento) a `/past_meetings/{uuid}/participants` (timestamps individuales
  `join_time`/`leave_time`, casi instantáneo).
- **Requisito nuevo:** verificar 3 "momentos dorados" por alumno (min 10, mitad, 10 min
  antes del fin). Se decidió NO filtrar a nadie — se registra a todos los participantes
  con una columna nueva `Instancias` (`"0/3"`..`"3/3"`) como dato crudo; la penalización
  es un proceso posterior. Nombre/Apellido se separan con heurística simple (primer
  espacio) porque la validación fuerte del Sheet corre por Correo/Identificación.
- Nodo Code `scripts/zoom-asistencia/nodo-calcular-momentos-dorados.js` escrito y
  validado con `node --check` — agrupa sesiones por email (o nombre normalizado como
  fallback, ver gotcha de correlación en la nota del proceso).
- **App Server-to-Server OAuth creada y activada en Zoom Marketplace.** Credenciales
  guardadas en `scripts/zoom-asistencia/.env` (gitignoreado) y probadas con `curl` contra
  `zoom.us/oauth/token` → HTTP 200. Scopes identificados (cruzando doc oficial + Zoom
  Community, no verificados 100% en pantalla real): `meeting:read:past_meeting:admin`,
  `meeting:read:list_past_participants:admin`.
- Documentado en `convenciones.md`: patrón Zoom S2S OAuth completo (credenciales, prueba
  con curl, scopes, Event Subscriptions no es de pago, Publish ≠ configurar webhook,
  UUID vs Meeting ID / doble URL-encode).
- **Pendiente próxima sesión:** construir el workflow real en n8n (Webhook Trigger +
  validación CRC/firma + el resto del flujo diseñado), exportar JSON a `n8n-workflows/`,
  y solo entonces completar Event Subscriptions en Zoom con la URL de cloudflared vigente
  (la URL es efímera, cambia en cada reinicio del túnel).

---

## 2026-07-01 — [Zoom Asistencia] Workflow construido y activo en n8n vía API

**Estado:** En progreso
**Proceso relacionado:** [[zoom-asistencia]]

- Se construyó el workflow completo `Zoom - Asistencia` (14 nodos) directamente vía la API
  de n8n (sin usar la UI), leyendo el código fuente instalado de `n8n-nodes-base` en
  `C:/nvm4w/nodejs/node_modules/n8n/node_modules/n8n-nodes-base/dist` para obtener los
  parámetros exactos de cada nodo (Webhook, Crypto, HTTP Request con paginación, Google
  Sheets resourceMapper, etc.) sin adivinar.
- Decisión clave: NO se usó el flujo OAuth2 "Client Credentials" nativo de n8n para Zoom
  porque Zoom exige `grant_type=account_credentials` (propietario) y n8n fuerza
  `client_credentials` en el body — en su lugar, HTTP Request manual con Basic Auth, igual
  al patrón ya probado con curl.
- Creadas 3 credenciales en n8n vía API: `Zoom S2S Basic Auth`, `Zoom Webhook HMAC Secret`
  (con secreto placeholder, pendiente de actualizar manualmente en la UI cuando Zoom
  entregue el Secret Token real — la API no permite editar credenciales existentes), y
  reutilizado el Service Account de Q10 para Google Sheets.
- El Sheet destino de pruebas es `H3Test` (ID `1VyXOYsnpD9ksKcJFHiiRR6fr4UUCea4WmGG96NV0WP0`),
  confirmado por Samuel — sheet exclusivo de testing, sin `Validar`/`Seguimiento` todavía.
- Probado con payloads sintéticos: validación CRC coincide byte a byte con cálculo
  independiente en Python; el evento `meeting.ended` con firma válida confirmó ack inmediato
  (~40ms) + fan-out a procesamiento en segundo plano + Wait 90s + OAuth Zoom real exitoso +
  `Info Reunion` devolvió un 404 legítimo de la API real de Zoom (UUID inventado) — valida
  toda la cadena de auth hasta ese punto.
- JSON exportado a `n8n-workflows/zoom-asistencia.json`. Workflow activo.
- **Pendiente próxima sesión:** configurar Event Subscriptions en Zoom Marketplace con la URL
  de cloudflared vigente, actualizar el Secret Token real en la credencial `Zoom Webhook HMAC
  Secret` (vía UI), y probar con una reunión Zoom real para validar `Participantes` → Code →
  Google Sheets (aún no probado con datos reales).
- **Bloqueo:** ninguno técnico — depende de que ocurra una clase Zoom real para la prueba
  final, y de que Samuel complete el paso manual en Zoom Marketplace.

---

## 2026-07-01 — [Zoom Asistencia] Primera prueba real exitosa de punta a punta

**Estado:** Funcional (casos límite pendientes)
**Proceso relacionado:** [[zoom-asistencia]]

- Se configuró Event Subscriptions en Zoom Marketplace con el Secret Token real
  (`3c9DF8ArSpiKeQLj15l8lQ`). Dos gotchas resueltos en el camino: (1) el token se genera
  *antes* de validar la URL — firmar con placeholder causa "URL validation failed" aunque el
  endpoint responda bien; (2) la URL del webhook es `/webhook/zoom-asistencia`, no la URL
  del editor `/workflow/<id>`.
- Prueba con reunión Zoom real (36 min, 2 participantes): ejecución #36 falló en
  `Obtener Token Zoom` (`invalid_client` — credencial Basic Auth corrupta por edición manual
  en la UI de n8n que guardó el Secret Token encima del client secret). Se recreó la
  credencial vía API (`Zoom S2S Basic Auth v2`) y se reintentó **reenviando el mismo evento
  firmado localmente con el UUID real** — no hizo falta repetir la reunión.
- Ejecución #37: éxito completo en los 11 nodos. 2 filas reales escritas en `H3Test` con
  `Instancias 3/3`. La agrupación por reconexión (participante con 2 sesiones) funcionó como
  se diseñó — quedó en una sola fila.
- Credenciales viejas/corruptas eliminadas de n8n; JSON re-exportado a
  `n8n-workflows/zoom-asistencia.json`.
- **Pendiente:** Prueba 2 (reunión ≤20 min, caso límite de checkpoints) y Prueba 4
  (invitado sin cuenta Zoom escribiendo "Nombre correo cédula" — valida el parseo de texto
  libre, aún no ejercitado). Decidir Sheet de producción con Validar/Seguimiento.

---

## 2026-07-01 — [Zoom Asistencia] Columnas Curso y Fecha para coordinar con las clases

**Estado:** Funcional
**Proceso relacionado:** [[zoom-asistencia]]

- Se identificó que las filas de asistencia no indicaban a qué clase pertenecían — crítico
  con cursos en horarios distintos y 2 salas. Decisión (confirmada con Samuel): las clases
  se programan una a una con el nombre del curso como tema de la reunión → se usa el topic
  como columna `Curso` + columna `Fecha` (inicio real, hora Colombia UTC-5).
- Cambio en el nodo Code (workflow vivo + `nodo-calcular-momentos-dorados.js` local) y
  headers de `H3Test` ampliados a 7 columnas.
- Validado reenviando el `meeting.ended` de la reunión de prueba (ejecución #38 exitosa):
  filas con `Curso="Mi reunión"` y `Fecha="2026-07-01 16:14"` correctas. Se llenaron las
  filas viejas y se eliminaron duplicados del Sheet de prueba.
- Regla operativa nueva documentada: el equipo debe nombrar las reuniones de Zoom con el
  nombre del curso — de ahí sale `Curso` literal. Alternativa futura si cambia el esquema:
  mapeo por Meeting ID con reuniones recurrentes.
- JSON re-exportado a `n8n-workflows/zoom-asistencia.json`.

---

## 2026-07-02 — [Zoom Asistencia] Columna "% Asistencia" con fusión de intervalos

**Estado:** Funcional
**Proceso relacionado:** [[zoom-asistencia]]

- Nueva columna `% Asistencia` en el nodo Code: por participante se fusionan los intervalos
  join→leave solapados/contiguos (las sesiones de reconexión pueden solaparse — no sumar
  doble), se recorta cada intervalo a `[inicio, finReal]` (tope natural de 100%), se suman
  los ms conectados, se divide por la duración real de `Info Reunion` y se redondea (`"NN%"`).
- Cambio aplicado en AMBAS copias: `scripts/zoom-asistencia/nodo-calcular-momentos-dorados.js`
  y el workflow vivo vía PUT `/api/v1/workflows/jkNaE51PKQ4TQzNq`; JSON re-exportado a
  `n8n-workflows/zoom-asistencia.json`. Header `% Asistencia` agregado en `H1` de `H3Test`
  vía gspread — el nodo Sheets no necesitó cambios (auto-map por nombre de columna).
- Validado reenviando el `meeting.ended` firmado localmente con el UUID real de la reunión
  de prueba (ejecución #44 exitosa): filas con `98%` y `96%`, coherentes con 36 min y una
  reconexión sin doble conteo. Filas duplicadas viejas de esa prueba eliminadas del Sheet.
- Hallazgo: la clase real "Desarrollo Web - GIT, HTML y CSS" del 2026-07-01 (ejecución #40,
  51 filas) corrió antes del cambio → filas con `% Asistencia` vacío. Se rellenaron
  retroactivamente: UUID desde los datos de la ejecución #40 en n8n
  (`GET /api/v1/executions/40?includeData=true`), participantes re-consultados a la API
  de Zoom (conserva datos de reuniones terminadas), misma lógica de fusión, match por
  correo → 51/51 filas actualizadas, columna completa en el Sheet.
  Ninguna fila de esa clase trae `Identificacion` — refuerza la urgencia de la Prueba 4
  (parseo de "Nombre correo cédula" en texto libre).
- **Pendientes (no de esta tarea):** filtro para reuniones no-clase (prefijo de nombre o
  lista de cursos) antes de producción, Prueba 2 (reunión ≤20 min) y Prueba 4.

---

## 2026-07-02 — [Zoom Asistencia] Pestaña ZOOM-ASISTANCE + CUPOS + ZOOM-STATS

**Estado:** Funcional
**Proceso relacionado:** [[zoom-asistencia]]

- Nuevo destino del workflow: pestaña `ZOOM-ASISTANCE` (mismo spreadsheet H3Test). Nodo
  renombrado a `Escribir Asistencia ZOOM-ASISTANCE` vía API; 104 filas históricas migradas;
  `H3Test` queda congelada. Probado end-to-end con reenvío firmado (ejecución #48, 2 filas
  a la pestaña nueva) y filas de prueba eliminadas.
- Formato condicional automático: fila roja si `% Asistencia` < 70%, celda verde si >= 70%.
- Análisis profundo de la BD Seguimiento de Monitorias (xlsx pseudonimizado): 777 estudiantes
  activos asignados en columnas `Horario *` de `Seguimiento` → 89 clases con cupos de 32-63.
  Script `tools/analizar_cupos_bd.py` → `tools/cupos_clases.json` (sin PII).
- Pestaña `CUPOS` (clase → inscritos + columna `Alias Zoom` editable, preservada al
  regenerar) y `ZOOM-STATS` (solo fórmulas: por sesión — conectados, "X de Y estudiantes",
  % del cupo, promedio % estancia, alumnos <70%; y por semana ISO). Setup idempotente en
  `scripts/zoom-asistencia/setup_zoom_asistance.py`.
- **Gotcha nuevo (a convenciones):** el spreadsheet es locale `es_ES` — fórmulas vía API con
  `;` y arrays `{...}` con `\`; aplica también a CUSTOM_FORMULA de formato condicional.
- Hallazgo: el `meeting.ended` real de la clase de las 10 llegó solo a las 12:24 al cerrarse
  la sala (ejecución #46, 51 filas) — el evento tarda pero llega; confundió la validación
  del cambio porque corrió en paralelo con la prueba sintética.
- **Pendiente:** llenar `Alias Zoom` en CUPOS (los topics de Zoom no matchean los nombres de
  clase de la BD), decidir Sheet de producción, filtro de reuniones no-clase.

---

## 2026-07-02 — [Zoom Asistencia] Cupo por horario: "cantidad que debería haber vs la que entró"

**Estado:** Funcional
**Proceso relacionado:** [[zoom-asistencia]]

- El "X de Y estudiantes" de ZOOM-STATS ya no depende de que el topic de Zoom coincida con
  el nombre de clase de la BD. Cascada: nombre exacto → Alias Zoom → **match por horario**
  (área inferida del topic vía tabla editable `CUPOS!H:I` de palabras clave + día/hora de
  la Fecha real del evento, tolerancia ±45 min, suma de inscritos de la franja).
- CUPOS ganó columnas `Día`/`Hora` parseadas del nombre de clase (`parsear_horario()` —
  la primera hora del nombre es siempre COL/ECU/PAN). ZOOM-STATS ganó columna `Match cupo`
  (trazabilidad: nombre exacto / alias / horario / sin match) y helpers ocultos P:Q.
- Validado con datos reales: "Desarrollo Web - GIT, HTML y CSS" jueves 9:54 → "51 de 51
  estudiantes" (100% del cupo) vía HTML - Jueves 10:00 A.M.; miércoles 17:36 → HTML 6:00
  P.M. por la tolerancia. "Mi reunión" → sin match, como corresponde.
- Gotcha es_ES adicional: no usar decimales literales en fórmulas (`0.75` no parsea) —
  usar fracciones (`3/4`).
- Caveat documentado: si varios grupos de la misma área comparten franja (Sábado 8:00
  Uno/Dos/Avanzado) el cupo por horario los suma — verificar con el equipo si van en
  reuniones separadas; en ese caso usar Alias Zoom.

---

## 2026-07-02 — [Q10] Fase 4: Retirados (Cancelado/Desertor/Aplazado) → Sheets + panel público + GUI

**Estado:** Completado
**Procesos relacionados:** [[q10-consolidacion]] · [[dashboard-web]]

- El Consolidado NO trae estado de matrícula (verificado con archivado=true/false: idéntico).
  Los retirados viven en el reporte `GestionAcademica/EstudiantesCancelados` — descubierto
  explorando `/Informes`. Payload simple (sede/programa/rangoFechas vacíos = histórico completo).
  **El reporte no incluye Email ni Curso** → no se puede cruzar por email con h2test/Avance.
- `q10_to_sheets.py --grupo retirados` → pestaña `Retirados` (Sheet h2test, autocreada,
  10 cols con `Tipo` ∈ Cancelado/Desertor/Aplazado). `setup_headers.py` actualizado.
- Nuevo `organizador/retirados_headless.py` → `Retirados-complete`: bloques horizontales
  por Tipo (patrón h2test) + bloque RESUMEN. Emite `RESUMEN: retirados=N ... estado=exito`.
- Nuevo `export_retirados.py` → `docs/retirados/data.json` (solo agregados: por tipo, causa,
  programa y mes) → git push. Panel público `docs/retirados/index.html` (acento naranja) +
  botón "Retirados ↗" en el dashboard junto a Mujeres ROFÉ.
- `panel_riesgo_gui.py`: nueva tab 🚪 Retirados con 5 KPI clickeables (Todos/Cancelados/
  Desertores/Aplazados/Causas), tabla filtrable con info individual completa, popup de
  detalle y export CSV. `leer_retirados()` tolera pestaña inexistente.
- Workflow n8n `Rblg81qifVshsRae` actualizado vía API (desactivar→PUT→reactivar): +6 nodos
  (3 en rama Telegram con mensaje OK ampliado, 3 en rama Schedule 4h). Export sincronizado
  en `n8n-workflows/q10-consolidacion.json`.
- Probado end-to-end 2 veces: 328 → 353 registros en minutos (el equipo estaba marcando
  desertores en Q10 durante la sesión). Decisión: incluir los 3 tipos, no solo "Cancelado".

---

## 2026-07-03 — [Zoom Asistencia] Auditoría del "51 de 51" → exclusión de cuentas staff

**Estado:** Funcional
**Proceso relacionado:** [[zoom-asistencia]]

- Samuel cuestionó el "51 de 51 estudiantes" — auditoría con los datos reales: los 51
  conectados eran únicos y sin solapamiento entre sesiones, PERO incluían cuentas de la
  fundación (comunicaciones@, soporte.it@, jovenescreativos@). Valor real: 50 de 51
  (jueves) y 49 de 51 (miércoles). No era asistencia perfecta ni error de fórmula: era
  conteo inflado por staff.
- Fix: lista editable `CUPOS!G` "Excluir de conteos (email contiene)" (default
  tocaunavida.org, preservada al regenerar) + helpers V:W en ZOOM-STATS (email +
  REGEXMATCH) → Conectados, prom. % estancia y alumnos <70% (sesión y semana) ahora
  excluyen staff. Las filas staff siguen en ZOOM-ASISTANCE como registro crudo.
- "Mi reunión" (prueba, 2 cuentas staff) bajó a 0 conectados — confirma la exclusión.
- Límite documentado: el "X de Y" compara cantidades, no personas — el cruce persona a
  persona (Validar vs Seguimiento) necesita el Sheet de producción con correos reales.

---

## 2026-07-03 — [Zoom Asistencia] Corroboración persona por persona contra h2test (Q10)

**Estado:** Funcional
**Proceso relacionado:** [[zoom-asistencia]] · [[q10-consolidacion]]

- Pedido de Samuel: validar que los asistentes de H3Test sean coherentes con quienes
  deberían estar, SIN usar la BD pseudonimizada. Como Q10 no tiene grupos de horario ni
  curso "Desarrollo Web", el cruce factible es de identidad: correo del asistente vs
  correos reales de h2test → `tools/corroborar_asistencia_h3test.py` (PII, solo local).
- Resultado clases reales: miércoles 44/49 verificados (90%), jueves 42/50 (84%).
  Los no encontrados: bot notetaker fred@fireflies.ai (agregado a exclusiones CUPOS!G,
  jueves quedó "49 de 51"), typos de correo al entrar a Zoom (vbuesaquilloo@ doble o) y
  estudiantes con correo distinto al de Q10.
- Conclusión: no hubo asistencia perfecta ni error de fórmula — 49 de 51 con ~85-90% de
  identidad verificada. El cruce fino por grupo de horario queda para el Sheet de
  producción; cupos por horario (BD Monitorias) marcados como provisionales.

---

## 2026-07-03 — [Q10] Verificación de coherencia: BD S Retirados vs extracción de retirados

**Estado:** Completado
**Procesos relacionados:** [[q10-consolidacion]]

- Nuevo `tools/verificar_retirados_bd.py` (local, PII): restaura la pestaña `S Retirados`
  de la BD Seguimiento de Monitorias (pseudonimizada) con la clave del pseudonimizador
  y la cruza contra el reporte `Estudiantes cancelados` de Q10 descargado en vivo.
- **Resultado: 100% coherente.** Los 55 retirados de la BD están todos en Q10,
  matcheados por cédula (0 por fallback de nombre, 0 faltantes). No hubo que ajustar
  la extracción ni agregar usuarios.
- Informativo (dirección inversa): 25 desertores marcados en Q10 el 2026-07-02
  ("Decisión de la Institución") aún no aparecen en la BD — la BD exportada es de la
  mañana de ese día y los marcaron en la tarde; es desfase de snapshot, no error.
- Gotcha: la BD `_codificado_restaurado_codificado.xlsx` tiene TODO pseudonimizado
  (IDs incluidos) — cualquier cruce requiere la clave `clave_*.json` de Downloads.

---

## 2026-07-03 — [Zoom Asistencia] Incidente: túnel muerto — asistencia de 2 reuniones perdida y sistema restaurado

**Estado:** Restaurado (requiere acción manual de Samuel en Zoom Marketplace)
**Proceso relacionado:** [[zoom-asistencia]]

- Reporte de Samuel: "Entrevista Nova" y "Mi vida sí importa" no registraron asistencia.
  Diagnóstico: el quick tunnel de cloudflared murió en silencio (~tarde del 07-02, PC
  dormido) — DNS del hostname eliminado en Cloudflare aunque el proceso local reportaba
  conexión; n8n además se saltó los schedules de Q10 de 00:00Z y 04:00Z. Los meeting.ended
  rebotaron: no llegó NI una ejecución fallida.
- Hallazgo colateral grave: `.gitignore`, `CLAUDE.md`, `claude_sessions.md` e
  `iniciar_n8n.bat` aparecieron BORRADOS del working tree (causa desconocida, ~1:20 AM).
  Restaurados con `git checkout -- <archivos>`.
- Restauración: matado cloudflared zombie, relanzado stack vía bat temporal sin watchdog
  (WMI para sobrevivir a la sesión; `timeout /t` no funciona desatendido — gotcha nuevo).
  Túnel nuevo: `https://championship-benz-initiative-agency.trycloudflare.com`. Workflows
  Q10 y Zoom reactivados; CRC probado por el túnel público con hash correcto. ✅
- **Pendiente Samuel:** pegar la URL nueva en Zoom Marketplace (Event Subscriptions);
  conseguir Meeting IDs de las 2 reuniones perdidas (o agregar scopes de listado) para
  recuperar su asistencia con reenvío sintético; decidir túnel nombrado — cada logon
  regenera la URL y rompe el webhook (ya no es opcional).

---

## 2026-07-03 — [Infraestructura] Investigación: borrado recurrente de archivos raíz

**Estado:** Investigado — causa probable identificada, confirmación pendiente en UI de Avast
**Proceso relacionado:** [[zoom-asistencia]] (incidente del túnel)

- Hechos del incidente (03-jul 1:22-1:27 AM): los 4 archivos SUELTOS de la raíz del repo
  (.gitignore, CLAUDE.md, claude_sessions.md, iniciar_n8n.bat) borrados sin pasar por la
  Papelera; carpetas intactas. iniciar_n8n.bat desapareció exactamente entre su lanzamiento
  con Start-Process (1:25:11, sin error) y 90 s después, sin ejecutar ni una línea (el log
  viejo quedó intacto) — firma de bloqueo-en-ejecución de antivirus.
- Descartados con evidencia: Storage Sense (limpieza de Downloads desactivada), OneDrive
  (sin redirección), tareas programadas de limpieza (ninguna), Defender (pasivo, 0
  detecciones), las dos sesiones de Claude Code (transcripts auditados comando por comando:
  solo lecturas/appends), borrado manual vía Explorer (no está en la Papelera).
- Sospechoso principal: **Avast** (activo desde el 24-jun, Defender en pasivo). Cuadra:
  remediación al ejecutar un .bat sin firma que lanza cloudflared (herramienta muy abusada
  por malware); SecurityCenter re-registró el estado de Avast a la 1:28:32 (4 min después);
  chest/logs no accesibles sin admin para confirmación programática.
- Ocasiones ANTERIORES (Papelera): son otra cosa — borrados manuales vía Explorer de
  archivos similares (README/.gitignore 27-abr, AI_CONTEXT_*.md 01-jun, CLAUDE.md y
  otro-proceso-si-aplica.md 24-jun). PC compartido: alguien "limpia" archivos que le
  parecen basura.
- Mitigación aplicada: git como red de seguridad (restauración inmediata con checkout).
- **Pendiente Samuel:** (1) abrir Avast → Historial de protección y buscar entradas del
  03-jul ~1:22-1:28 AM — confirmación definitiva; (2) agregar el repo como excepción de
  Avast; (3) decidir mover el repo FUERA de Downloads (zona objetivo de todos los
  limpiadores) a p.ej. C:\ROFE\ — requiere actualizar Task Scheduler y rutas hardcodeadas;
  (4) preguntar al equipo por los borrados manuales históricos.

---

## 2026-07-03 — [zoom-asistencia] Rotación de túnel cloudflared + re-registro de webhooks

**Estado:** Resuelto en el lado de n8n — pendiente confirmar Zoom Marketplace (externo)
**Proceso relacionado:** [[zoom-asistencia]] · [[q10-consolidacion]]

- Rotó el quick tunnel a `https://based-disco-yale-traveller.trycloudflare.com` (confirmado
  contra `http://127.0.0.1:20241/quicktunnel`). Samuel reportó haber actualizado "el nodo de
  Telegram" con la URL — pero la URL es la del webhook de Zoom (`.../webhook/zoom-asistencia`).
- Aclaración de topología: el nodo n8n NO almacena la URL pública. `iniciar_n8n.bat` fija
  `WEBHOOK_URL=<túnel>` y mata la instancia vieja; Webhook de Zoom y Telegram Trigger heredan
  la URL nueva al reiniciar. No había nada literal que "editar" en un nodo.
- Verificado: POST dummy al webhook público de Zoom → HTTP 401 (firma inválida) = el túnel
  nuevo enruta correctamente a n8n. Ambos workflows activos.
- Acción hecha por API: desactivar+activar `Bot Q10` (ID `Rblg81qifVshsRae`) para forzar
  `setWebhook` de Telegram contra la URL nueva; `activate` → 200 (Telegram aceptó). No se
  necesitó el token del bot.
- **Único paso NO automatizable / pendiente Samuel:** actualizar la URL del Event Subscription
  en el **Zoom Marketplace** a `.../webhook/zoom-asistencia` (la API pública de n8n no toca
  eso). Es probablemente lo que Samuel ya hizo cuando dijo "actualizamos con [URL]".
- Doc del proceso actualizada con el procedimiento de rotación en la sección de gotchas.

---

## 2026-07-03 — [zoom-youtube] Nuevo proceso documentado: grabaciones Zoom → YouTube

**Estado:** Idea / En diseño — solo documentado, sin implementar
**Proceso relacionado:** [[zoom-asistencia]] (misma app Zoom S2S OAuth)

- Samuel preguntó si es viable subir automáticamente las grabaciones de Zoom a YouTube.
  Confirmado: sí, caso estándar de n8n. Por ahora **solo documentar**.
- Parámetros de negocio confirmados: Zoom de **pago** (grabación en la nube) y videos
  **públicos** en YouTube con autorización previa de la Fundación por video.
- Diseño: trigger webhook `recording.completed` (distinto de `meeting.ended`) → descargar
  MP4 vía `download_url` + token → `videos.insert` de YouTube Data API v3. Reusa la app Zoom
  S2S OAuth, el CRC + firma y el túnel cloudflared de zoom-asistencia; solo suma el scope de
  cloud recording y el evento nuevo.
- Gotchas anticipadas documentadas: cuota YouTube (1.600 u/subida, ~6/día por defecto),
  OAuth de usuario obligatorio (Service Account NO sirve para canales) + publicar la app para
  que el refresh_token no expire, PII (rostros de jóvenes → evaluar unlisted + revisión humana
  antes de público), tamaño/tiempo de descarga-subida, y el mismo túnel efímero.
- Creada nota `docs/procesos/zoom-youtube.md`; enlazada bidireccionalmente con zoom-asistencia
  y agregada a "Procesos identificados" en la visión global.
- **Pendiente Samuel:** decidir visibilidad final (público directo vs unlisted→humano→público);
  crear OAuth Client de YouTube en Google Cloud; solicitar ampliación de cuota si >6 videos/día.

---

## 2026-07-03 — [dashboard-web] Fix build de GitHub Pages: `.nojekyll`

**Estado:** Resuelto y en producción
**Proceso relacionado:** [[dashboard-web]]

- Samuel reportó "pages build and deployment failed" repetido en el repo `Fundacion-ROFE/
  Estadisticas` (runs #87, #90, #92, #96). No era problema de datos ni de código.
- Causa raíz: GitHub Pages procesaba `docs/` con Jekyll (default). Jekyll intenta renderizar
  todos los `.md`, incluidas las notas de Obsidian. La línea 70 de `docs/convenciones.md`
  tiene una expresión n8n `{{ 'texto ' + $json.var }}`; el parser Liquid la evalúa,
  `$json.var` no es válido → el build entero falla en cada push.
- Solución: creado `docs/.nojekyll` (archivo vacío) → desactiva Jekyll por completo. El sitio
  son dashboards HTML estáticos (`index.html` + `data.json`), no pierde nada; deploys más
  rápidos y sin fallos. Commit `5287241`, push a main.
- Nota: primer push dio "Connection was reset" (red transitoria, posible relación con la red
  corporativa/Avast ya investigada); reintento OK.
- Gotcha documentado en `docs/procesos/dashboard-web.md`: `.nojekyll` es obligatorio, NO
  borrar (si el borrado recurrente de archivos raíz lo elimina, los fallos vuelven).

---

## 2026-07-05 — [q10-consolidacion] Autodescubrimiento de periodos por año + curso Desarrollo Web

**Estado:** Implementado y validado en vivo (falta correr cadena a producción)
**Proceso relacionado:** [[q10-consolidacion]] · [[dashboard-web]]

- Samuel notó 7 cursos en el panel manual (Avance) vs 6 en Q10 (h2test): el faltante era
  **HTML** (777 estudiantes, 50.53%). Confirmado leyendo h2test: no existía columna HTML.
- Sondeo en vivo de Q10 (periodos 18–40): el curso SÍ existe como **"Desarrollo Web Front-End
  - HTML - 2026"**, en los periodos **20 (Desarrollo-Nivel 3, 502) y 24 (Desarrollo-Avanzado,
  275)** — ambos 2026, ambos fuera de la lista fija `PERIODOS = [21, 22, 23]`. 502+275=777,
  cédulas disjuntas → cuadra exacto con el manual.
- Verificado que 18/19 son cohortes **2025** (traslape 0 con 21/22) → estaban bien excluidos;
  la lista fija solo fallaba con Desarrollo Web. El gotcha viejo ("periodos 20 y 24 dan
  not_results") era **falso** — corregido en mapa-codigo.
- **Cambio:** `q10_to_sheets.py` pasa de `PERIODOS` fija a **autodescubrimiento por año**:
  sondea `RANGO_PERIODOS = range(18,41)`, lee la columna `Período` y conserva solo los del
  `AÑO_OBJETIVO` (año en curso; override `--anio YYYY`). Nuevos helpers `_etiqueta_periodo()`,
  `_periodo_es_del_anio()`; `descargar_todos_consolidados(session, anio)` reescrita con log de
  incluidos/descartados. Adaptativo a cursos/cohortes nuevos sin tocar código y sin doble
  conteo de años previos.
- Prueba en vivo: incluye [20,21,22,23,24], descarta [18,19]; 9 cursos, 1063 cédulas únicas,
  Desarrollo Web con 777. Docs actualizados: mapa-codigo (tabla de periodos + firmas).
- **Cadena corrida a producción:** `q10_to_sheets --grupo h1test` (5827 filas) →
  `organizador_headless` (9 cursos, Desarrollo Web 777) → `export_stats` (JC 6→7 cursos, push).
  Desarrollo Web ya en el dashboard público (777, 52.22% — coherente con el 50.53% del manual).
  El panel de riesgo lo toma solo (lee h2test en vivo). Commits `510afad` (data.json) y `81d2dae`
  (código + docs).
- **Fix header H1Test:** el header tenía 6 cols y `mapear_columnas()` sube 7 (con `Estado`).
  No era bug activo (`organizador` repone `Estado="A"` por defecto y todas las filas son "A"),
  pero se alineó: agregado `Estado` a `HEADERS_POR_PESTANA["H1Test"]` en `setup_headers.py` y
  escrito en `G1`. La guarda del script no sobrescribe headers con contenido → se escribió la
  celda directa. De paso, agregado wrapper UTF-8 a `setup_headers.py` (crasheaba con `→` en cp1252).

---

## 2026-07-04 — [zoom-asistencia] Flujo secundario: control temprano al minuto 10 (trigger dual)

**Estado:** Código listo y desplegado (workflow en vivo, 20 nodos) — pendiente activar evento
+ scope en Zoom Marketplace y prueba real (punto 4 y 5 del plan)
**Proceso relacionado:** [[zoom-asistencia]]

- Objetivo pedido: además de la toma completa al `meeting.ended`, un snapshot temprano de
  quién ya ingresó ~10 min después de iniciar, para control rápido de la clase.
- Diseño: el webhook pasa a **trigger dual**. Tras validar firma, un IF `Evento
  meeting.started?` bifurca — `meeting.ended` → rama completa **intacta**; `meeting.started`
  → `Esperar 10 min` → `Obtener Token Zoom 2` → `Participantes en Vivo` → `Presentes @10min`
  → `Escribir ASISTENCIA-10MIN`.
- Reto clave resuelto: con la reunión en curso `past_meetings` no existe → se usa la
  **Dashboard API** `GET /metrics/meetings/{uuid}/participants?type=live` (requiere plan
  Business ✓ + scope `dashboard_meetings:read:admin`). Curso/Fecha salen del payload del
  webhook, no de una llamada extra.
- Implementado (pasos 1-3): `setup_zoom_asistance.py` +función `construir_asistencia_10min()`
  y flag `--solo-10min`; **pestaña `ASISTENCIA-10MIN` creada** (7 cols, append); nodo Code
  `scripts/zoom-asistencia/nodo-presentes-10min.js` (sin %, dedup por email/nombre); workflow
  editado vía API n8n (PUT `jkNaE51PKQ4TQzNq`) y re-exportado. Sigue **activo**.
- Seguro por diseño: la rama nueva queda **inerte** hasta que Zoom envíe `meeting.started`, así
  que la rama `meeting.ended` de producción no corrió ningún riesgo al editar en vivo.
- Verificado: `py_compile` OK, `node --check` OK, grafo en vivo correcto, tab creada.
- **Pendiente Samuel (punto 4):** en la app S2S OAuth agregar evento `meeting.started` +
  scope `dashboard_meetings:read:admin` y re-activar; luego prueba real (punto 5).
- Docs: sección "Flujo secundario" + 5 gotchas anticipadas en la nota del proceso.

---

## 2026-07-06 — [zoom-asistencia] Prueba real del 10-min: bloqueo Dashboard API + hallazgo 2 cuentas

**Estado:** Rama `meeting.started` corre completa pero bloqueada en `Participantes en Vivo`
(Dashboard API). Descubierto que la cuenta **soporte** no está cubierta. Ambos = pendientes.
**Proceso relacionado:** [[zoom-asistencia]]

- **Túnel rotado tras reinicio de PC:** el `cloudflared` del logon murió en silencio (proceso vivo,
  `/quicktunnel` reportaba hostname viejo pero ya sin DNS). Se levantó túnel nuevo
  `automotive-cluster-amp-shared.trycloudflare.com`, se reinició n8n con ese `WEBHOOK_URL` y se
  re-activó Bot Q10 (Telegram OK). Ruteo verificado con **handshake CRC completo** (encryptedToken
  de n8n == HMAC con el Secret real). URL pegada en el Event Subscription del Marketplace.
- **Config Zoom (Samuel):** agregado evento `meeting.started` + scope. **Scope correcto confirmado
  leyendo el token:** el granular es `dashboard:read:list_meeting_participants:admin` (NO el clásico
  `dashboard_meetings:read:admin` que era tentativo).
- **Prueba real (ejecución #85, "TEST TOMA TEMPRANA AUTOMATICA N 1"):** el flujo corrió de punta a
  punta — evento recibido, `Esperar 10 min` exacto (14:50→15:00Z), token OK, doble-encode UUID OK —
  y **solo falló `Participantes en Vivo` con 400**: *"…Business or higher accounts that have enabled
  the Dashboard feature."* Reproducido con `type=live` y `type=past` (mismo token/scope) → **no es
  scope ni código ni timing: es un flag de cuenta**. Confirmado: plan **Business** ✓, **Panel web
  funciona** ✓, permiso de rol "Panel de control → Reuniones" ya marcado ✓. → **Requiere ticket a
  soporte de Zoom** para habilitar el acceso por API al Dashboard. Ticket redactado (EN) en el chat.
- **HALLAZGO grande — 2 cuentas Zoom:** la operación usa **comunicaciones** (us06web) y **soporte**
  (us02web), cuentas Business independientes. Cruzadas las **38 ejecuciones**: todos los eventos
  reales son `account_id=u08qlWbRTR2VBSs0bRwZPQ` (comunicaciones); **ningún** meeting ID de soporte
  aparece. Los 2 `host_id` vistos son 2 usuarios de comunicaciones, no 2 cuentas. → **Las clases de
  soporte no se automatizan** (ni `meeting.ended` ni 10 min). Cubrirlo pide 2º app S2S + workflow
  multi-cuenta (firma y token por `account_id`, secretos distintos). Documentado en la nota del proceso.
- **Plan acordado:** (1) ticket Zoom → habilitar Dashboard API; (2) probar 10-min en comunicaciones;
  (3) cubrir soporte; (4) túnel permanente.
- **Cobertura soporte — bloqueada en acceso:** la cuenta Zoom de soporte la **facilita Colegio Colombia
  2020** (`colegiocolombia2020@gmail.com`); Samuel no tiene permiso de desarrollador ahí. Se redactó
  **carta formal HTML** con membrete ROFÉ (Artifact) y un **borrador de correo** (Gmail de Samuel →
  `soportejunior@`, HTML email-safe con logo desde GitHub Pages) pidiendo el permiso "Aplicación de
  OAuth de servidor a servidor" para `soportejunior@` (Opción A) o los 4 valores del app (Opción B).
  Pendiente que Samuel lo reenvíe a Colegio. Diseño para cuando haya acceso: workflow **clonado
  aislado**, path `…/webhook/zoom-asistencia-soporte`, sin tocar comunicaciones.
- **Túnel permanente resuelto con ngrok** (en vez del subdominio de tocaunavida.org — el DNS estaba en
  el hosting y delegar era enredado; como la URL solo la usa Zoom, un dominio ngrok da igual). Dominio
  estático gratis **`ergonomic-absinthe-refract.ngrok-free.dev`**; config `%LOCALAPPDATA%\ngrok\ngrok.yml`
  (tunnel `n8n`→5678). Gotchas: agente ≥3.20 (update 3.3.1→3.39.9); `ngrok service install` pide admin
  (falló) → irá por `iniciar_n8n.bat`. n8n reiniciado con `WEBHOOK_URL`=dominio fijo; Telegram
  re-registrado solo (tráfico `91.108.*` en log). Memoria [[reference-ngrok-tunel-fijo]]. **Falta:**
  repegar URL fija en Zoom comunicaciones + validar, retirar cloudflared, editar `iniciar_n8n.bat`.
- Cambios de código/docs de estas sesiones siguen **sin comitear** en el working tree.


---

## 2026-07-06 — [dashboard-web] Cursos finalizados: marca de agua inscritos → finalizados

**Estado:** Implementado en código y docs. **Pendiente que Samuel corra `python export_stats.py`**
(hace commit+push a producción; no lo ejecuté yo por ser acción de cara al público).
**Proceso relacionado:** [[dashboard-web]]

- **Problema (pedido nuevo):** el panel encogía los cursos ya finalizados. Q10 usa `archivado=false`
  (solo activos), así que al inhabilitar/retirar gente el conteo baja (Bienvenida 863 → 780). Pidieron
  mostrar el logro real de cursos terminados (ej. 830 inscritos → 820 finalizaron) y dejar en tiempo
  real solo los cursos abiertos.
- **Hallazgos clave:** (1) el filtro "solo 2026" ya está resuelto río arriba en `q10_to_sheets.py`
  (autodescubre periodos y descarta años viejos), no hay que filtrar reciclados. (2) **Q10 NO expone un
  flag de "curso cerrado"** — el Consolidado solo trae activos + avance. (3) history.json ya tenía el
  pico (863 el 26-jun) → sirve de semilla.
- **Solución — marca de agua (`export_stats.py`):** nuevo `docs/dashboard/maximos_cursos.json`
  monótono. Por curso: `inscritos`=máx histórico de estudiantes, `finalizados`=máx de avance>=100,
  `promedio_pico`, y flag `finalizado` = promedio>=90% y matrícula ya bajó del pico (>=2%). Se
  siembra desde history.json si no existe. Funciones nuevas: `enriquecer_con_maximos`,
  `_enriquecer_curso`, `_seed_maximos_desde_history`, `guardar_maximos`. Conteo `finalizados`
  agregado en `_procesar_grupos`.
- **Dashboard (Tab 1):** cursos finalizados → badge "✓ Finalizado" + celda "863 inscritos → 820
  finalizaron" (congelado); abiertos → "activos hoy". Render retrocompatible con data.json viejo.
- **Verificación offline (sin red):** simulado con data.json+history.json → Bienvenida recupera 863 y
  marca FINALIZADO; Desarrollo Web (53%) queda ABIERTO. Correcto.
- **Límite conocido:** cursos con pico anterior al 26-jun ya encogido no se recuperan; `finalizados`
  arranca en 0 hasta la 1ª corrida real (history no guarda el conteo al 100%).

---

## 2026-07-07 — [zoom-asistencia] Migración a ngrok cerrada: iniciar_n8n.bat sin cloudflared

**Estado:** Hecho y verificado end-to-end. **Pendiente solo:** Samuel repega la URL fija en el
Event Subscription de Zoom comunicaciones y pulsa Validate.
**Proceso relacionado:** [[zoom-asistencia]] · [[q10-consolidacion]]

- **Contexto:** al encender el PC, el bat seguía arrancando cloudflared (paso 3 pendiente de ayer)
  y ngrok NO corría — la URL fija estaba muerta y n8n arrancó con URL rotativa otra vez.
- **Cambio en `iniciar_n8n.bat`:** bloque cloudflared reemplazado por `ngrok start n8n` (con guard
  de agente único — free tier), `WEBHOOK_URL` hardcodeada al dominio fijo, espera del túnel vía API
  local `:4040`, y watchdog del loop ahora vigila/revive ngrok. Gotcha batch: dentro de bloques `()`
  usar `if errorlevel 1` (dinámico), no `%errorlevel%` ni `!…!` sin delayed expansion.
- **Aplicado en vivo:** matado bat viejo + cloudflared, relanzado bat nuevo. Verificado: túnel
  `ergonomic-absinthe-refract.ngrok-free.dev` arriba, healthz público 200, workflows Bot Q10 y
  Zoom-Asistencia activos, y handshake CRC de Zoom OK (POST `endpoint.url_validation` devolvió
  `encryptedToken`) → el Validate de Zoom pasará.
- **Docs actualizados:** convenciones (tunnel estándar ahora ngrok; nota histórica del x509 viejo),
  zoom-asistencia (migración cerrada), q10-consolidacion (gotcha WEBHOOK_URL), CLAUDE.md (árbol).
- **Nota:** `TELEGRAM_BOT_TOKEN` del `.env` da 401 contra api.telegram.org — parece desactualizado
  (n8n usa su credencial interna, el bot no se afecta; el bat tampoco lo usa para el registro).

---

## 2026-07-07 — [q10-consolidacion] Diagnóstico /actualizar simultáneos + token .env sincronizado

**Estado:** Diagnóstico documentado; sin cambios de código. **Proceso relacionado:** [[q10-consolidacion]]
- **Consulta:** qué pasó con el `/actualizar Q10` de ~09:05. Respuesta: llegaron DOS — Cristian
  (09:05:04, ejecución #101, exitosa en 3m19s, datos actualizados) y Samuel 35 s después
  (#102, falló con `HTTP 444` de Q10 al bajar el Consolidado: sesión concurrente con la misma
  cuenta rechazada). Inofensivo — la primera dejó todo al día. Gotcha nuevo en la doc.
- **Corridas programadas 03:00 y 07:00 fallaron** ("server closed the connection unexpectedly");
  la de 23:00 pasó bien. Se observa la de 11:00 — si falla de nuevo, investigar.
- **`.env` q10-consolidacion:** Samuel sincronizó `TELEGRAM_BOT_TOKEN` con el token vigente de la
  credencial de n8n (daba 401). La regeneración con BotFather sigue pendiente.
- **Pendiente nuevo:** candado anti-concurrencia en el workflow Bot Q10 (responder "ya hay una
  actualización corriendo" si hay ejecución en curso).

---

## 2026-07-07 — [mr-actualizacion-datos] Form MR2024 → BD-Mujeres ROFÉ (proceso nuevo, completado)

**Estado:** Completado — script + backfill + workflow n8n activo.
**Proceso:** [[mr-actualizacion-datos]]

- Pedido: actualizar la pestaña `General` de BD-Mujeres ROFÉ 2026 con lo que llega del form
  "Actualización de datos MR2024" + columna con la fecha de actualización del dato.
- Decisiones de Samuel: actualizar TODO lo que traiga el form; sin match → fila nueva al final
  con color; fecha = fecha de la corrida; automatizar con n8n diario.
- Script nuevo `scripts/mr-actualizacion-datos/actualizar_bd_mr.py`: cruce por cédula (5,109
  únicas en General), diff por celda **insensible a tildes** (el form llega sin acentos — sin esto
  degradaba nombres correctos), vacío nunca sobreescribe, `--dry-run`, RESUMEN parseable.
- Backfill: 286 filas actualizadas, 24 nuevas (filas 5112–5135, fondo naranja — varias parecen
  typos de cédula o inactivas → revisión humana), 37 respuestas sin cédula omitidas.
  Columna `Fecha Actualización` creada en AL. Re-corrida = 0 cambios (idempotente ✓).
- Workflow n8n `mr-actualizacion-datos` (ID `LgkDbNPERYgKMrYj`) creado vía API y activo:
  Schedule diario 7:30 → Execute Command → IF estado=exito → Stop-and-Error si falla.
  Export en `n8n-workflows/mr-actualizacion-datos.json`.
- Ambas hojas compartidas al Service Account (destino Editor, fuente Lector).

---

## 2026-07-07 — [dashboard-web] Panel público "Aprobación por Curso" (cohorte completa 2026)

**Estado:** Implementado y verificado local. **Pendiente que Samuel corra `python export_aprobacion.py`**
(hace commit+push a producción) y suba `docs/aprobacion/index.html` + botón del dashboard con git.
**Proceso relacionado:** [[dashboard-web]] · [[q10-consolidacion]]

- **Pedido:** ver por curso cuántos lo cursaron en 2026 (habilitados + inhabilitados) y qué % aprobó
  (aprobado = avance >= 100, hay casos de 101). El panel actual solo muestra activos.
- **Exploración Q10:** el switch "¿Incluir archivados?" del Consolidado virtual NO trae inhabilitados
  (mismos datos con true/false — verificado). El reporte ConsolidadoNotasCuantitativo es por
  logro (~16k filas Bienvenida) y Q10 corta en 5.000 registros → inviable. La fuente correcta:
  **Consolidado Estudiantes Matriculados (modo Detallado)** — sí incluye inhabilitados; el POST debe
  replicar los hidden Filtros[i].Name/PartialName o da 400.
- **Cruce por cédula (verificado):** p22 = 860 matriculados vs 780 activos → 80 inhabilitados, y los
  80 están TODOS en el reporte de cancelados → inhabilitado = retirado = no aprobó.
- **Nuevo `export_aprobacion.py`:** Q10 directo (sin Sheets) → cruza 3 reportes → 
  `docs/aprobacion/data.json` (solo agregados). Marca de agua en `docs/aprobacion/maximos.json`.
  Corrida real: 9 cursos, 1.143 estudiantes cohorte, 6.183 matrículas, 77,5% aprobación global
  (Bienvenida 90,2% · Emprendimiento 81,2% · MR en curso 29%/14%).
- **Panel `docs/aprobacion/index.html`:** barras apiladas 100% (verde/ámbar/rojo — paleta validada
  CVD + contraste), badges Finalizado/En curso, tablas por curso y programa, tooltips.
  Botón "Aprobación ↗" agregado al dashboard. Verificado con captura headless de Edge.
- **Gotchas** documentados en [[mapa-codigo]] (límite 5000, archivado inútil, headers del Excel de
  matriculados, cohorte 860 vs pico 863, `inhabilitados_sin_retiro`=5 a vigilar).

---

## 2026-07-07 — [dashboard-web] Dashboard rediseñado sobre la cohorte completa + tendencia diaria

**Estado:** Implementado, verificado con capturas headless y **publicado (commit+push de este alcance)**.
**Proceso relacionado:** [[dashboard-web]]

- **Pedido (supervisor):** la vista de Q10 con solo activos no satisface; usar los datos de
  aprobación (cohorte completa) en todo el dashboard y alimentar la tendencia con el histórico.
- **Tab 1 Estadísticas Q10:** ahora lee `../aprobacion/data.json` — KPIs de cohorte 2026, barras
  apiladas % aprobó por curso y tabla detalle. Reemplaza la vista de activos + marca de agua.
- **Tab 2 Avance Manual:** mismo formato. `export_avance.py` ahora exporta `aprobados`/`pct_aprobados`
  por curso (avance >= 100) + `--sin-push`. Aprobación manual global: 73,1%.
- **Tab 3 Comparativo:** % aprobación Manual vs Q10 cohorte con Δ por curso (alias en `ALIAS_APROB`,
  reemplaza `ALIAS_Q10`; los 3 grupos HTML del manual se fusionan). Δ positiva esperable (el manual
  no incluye retirados).
- **Tab 5 Tendencia:** `history.json` regenerado con **snapshots diarios** desde git (9 puntos,
  26-jun → 7-jul; se excluyeron 24–25 jun por estar contaminados con años previos, 4.563 est).
  El appender de export_stats.py sigue con su cadencia — regenerar con el script si se quiere densidad diaria.
- **Extra:** deep-link por hash (`/dashboard/#t3`) para abrir una pestaña directa.
- Tab 4 Admin sigue con `data.json` (export_stats.py). Los cambios de zoom/ngrok/MR del working
  tree quedaron fuera del commit.

---

## 2026-07-07 — [q10-consolidacion] export_aprobacion.py integrado al workflow n8n (cada 4 h)

**Estado:** Integrado vía API, verificado de punta a punta y comiteado.
**Proceso relacionado:** [[q10-consolidacion]] · [[dashboard-web]]

- **Workflow:** `Bot Q10 - Actualizar Grupos` (`Rblg81qifVshsRae`) — 24 → 26 nodos, sigue activo.
- **Rama Schedule 4h:** `Sched: export_retirados` (antes terminal) → nuevo `Sched: export_aprobacion`.
- **Rama Telegram:** `Ejecutar export_retirados` → nuevo `Ejecutar export_aprobacion` → `Responder OK`.
- **Responder OK:** al insertar el nodo antes, `$json` dejó de apuntar a retirados — se reancló
  `retOk` a `$('Ejecutar export_retirados')` y se agregó línea "Aprobación → GitHub Pages (X% aprobó)"
  parseando el `EXPORT:` del stdout.
- **Verificación:** se corrió el comando exacto del nodo bajo cmd (`cd ... && python export_aprobacion.py`)
  → descarga, cruce, commit y push OK (datos frescos: HTML 268 aprobados, IA 745).
- **Gotcha:** en el JS de los nodos Telegram las flechas/emoji van como texto literal `→` (no el
  carácter) — al editar expresiones por API hay que matchear esos escapes literales.
- JSON re-exportado a `n8n-workflows/q10-consolidacion.json` (26 nodos).

---

## 2026-07-07 — [mr-website] Documentación inicial del website Mujeres ROFÉ

**Estado:** Nodo de documentación creado; cambios al sitio aún sin alcance definido.
**Proceso relacionado:** [[mr-website]] · [[mr-actualizacion-datos]]

- Código en `C:\Users\EstudiantesJC\Downloads\Mujeres-Rofe-Website` (repo independiente, **sin .git local**):
  `back/` Express 4 + TS + Mongoose (Cloudinary, SendGrid, JWT) · `front/` Angular 15 (SCAM, ngx-sub-form).
- Deploy: push a main → GitHub Action → SSH a droplet DigitalOcean → compose en repo `rofe-composal`.
  Dominios: `mujeresrofe.com` / `api.mujeresrofe.com`.
- Decisión: el código NO se integra a admin-usable — nota [[mr-website]] en el vault (precedente n8n/tools)
  + `CLAUDE.md` local en la carpeta del website apuntando de vuelta al vault.
- Gotcha: `environment.ts` de dev del front apunta a la API de producción.
- Hallazgo: la BD Mongo del website y BD-Mujeres ROFÉ 2026 (Sheets) son bases paralelas no sincronizadas.
- Pendiente: alcance de cambios, clonar repos remotos, verificar acceso a droplet/secretos.

---

## 2026-07-08 — [dashboard-web] Notas por curso en el panel GUI (tab JC)

**Estado:** Completado.
**Proceso relacionado:** [[dashboard-web]] · Script: `tools/panel_riesgo_gui.py`

- Vista **EN Q10 JC** ahora muestra una columna por curso JC con el avance individual (etiquetas cortas
  vía `_etiqueta_jc()`) + columna Promedio, en vez de solo "# Cursos / Promedio".
- Nueva tarjeta KPI **CURSOS** en el tab JC: agregado por curso (Activos, Promedio, Mín, Máx,
  Aprobados ≥100%, % Aprobó sobre activos).
- Análisis de coherencia del panel público de aprobación: los números cuadran internamente
  (aprobados + sin_finalizar + retirados = cursaron). La diferencia percibida: el % Aprobó público
  divide entre la **cohorte completa (incluye retirados)**; la GUI divide entre activos de h2test.
  Ej. Bienvenida: 776/860 = 90.2% (público) vs 776/780 = 99.5% (activos).
- Smoke test headless con datos falsos: OK. `mapa-codigo.md` actualizado (tabla Vistas JC).

---

## 2026-07-08 — [q10-consolidacion] Toma "sin completar" con ubicación → Sheet SinCompletar

**Estado:** Completado — primera corrida exitosa.
**Proceso relacionado:** [[q10-consolidacion]] · Script nuevo: `tools/exportar_sin_completar.py`

- Nuevo script local (gitignoreado): cruza h2test (avance < 100, solo cursos JC) × BD Seguimiento
  de Monitorias (`Grupo` = ciudad) por cédula, fallback email. 709 matrículas sin completar,
  solo 11 sin ubicación (98.4% match).
- Salida: Sheet `SinCompletar` (1OkafT8PY...) con tablas anidadas ciudad → curso, formato con
  paleta ROFÉ y condicional en Avance (<60 rojo / 60-99 amarillo). Idempotente (recrea pestaña).
- Gotcha: ConditionValue del API no acepta decimales con locale es → límites enteros.
- Gotcha: la BD codificada referenciada en scripts previos ya no existe en Downloads — ahora se usa
  `BD Seguimiento de Monitorias - JC2026.xlsx` (sin codificar); hay clave nueva 2026-07-07.
- Distribución: BOG 125 · CTG 103 · BAQ 97 · MED 84 · GYL 82 · UY 71 · CAL 55 · PAN 43 · QTO 37.

---

## 2026-07-08 — [q10-consolidacion] exportar_sin_completar integrado al workflow n8n

**Estado:** Integrado y verificado — pendiente: re-compartir Sheet destino con el Service Account.
**Proceso relacionado:** [[q10-consolidacion]] · Workflow `Bot Q10 - Actualizar Grupos` (Rblg81qifVshsRae)

- 2 nodos nuevos vía API (26 → 28): `Sched: export_sin_completar` (rama Schedule 4h, tras
  export_aprobacion) y `Ejecutar export_sin_completar` (rama Telegram, antes de Responder OK).
- `Responder OK`: `$json` apuntaba a export_aprobacion; al insertar el nodo intermedio se cambió a
  `$('Ejecutar export_aprobacion')` y se agregó línea "Sin completar → Sheet (N en K ciudades)".
- Gotcha (re-confirmado): el JS de nodos Telegram guarda emoji/tildes como escapes literales
  \uXXXX — para editar por API usar anclas ASCII y construir escapes con chr(92).
- Gotcha nuevo: el Sheet destino perdió edición por enlace el mismo día (403 al escribir, lectura
  OK) — hay que compartirlo como Editor con q10-automatizacion@...iam.gserviceaccount.com.
- JSON re-exportado a `n8n-workflows/q10-consolidacion.json` (28 nodos).

---

## 2026-07-08 — [q10-consolidacion] SinCompletar: verificación end-to-end + bloques horizontales

**Estado:** Completado.
**Proceso relacionado:** [[q10-consolidacion]] · `tools/exportar_sin_completar.py`

- Sheet destino compartido como Editor con el Service Account → el comando del nodo n8n corre
  con exit 0 (se resolvió el 403 de la entrada anterior).
- Formato rediseñado a pedido: las ciudades (tablas primarias) ahora van como **bloques
  horizontales** lado a lado (patrón h2test, 2 cols de separación, orden por volumen desc),
  con los cursos apilados verticalmente dentro de cada bloque. 143 filas × 86 cols, 11 bloques.
- El formato condicional del Avance ahora aplica sobre la columna F de cada bloque
  (una regla con múltiples rangos).

---

## 2026-07-08 — [mr-actualizacion-datos] Clasificación de sin-match: retiradas y typos de cédula

**Estado:** Completado.
**Proceso relacionado:** [[mr-actualizacion-datos]] · `scripts/mr-actualizacion-datos/actualizar_bd_mr.py`

- Análisis de las 24 filas naranjas del backfill: 7 eran retiradas (pestaña `Inactivas`),
  13 posibles typos de cédula (mismo nombre + correo/celular igual que fila existente) y
  4 realmente nuevas.
- Script ampliado: respuestas sin match ahora se clasifican antes de agregar — cédula en
  `Inactivas` → RETIRADA (no se agrega); ≥2 señales (correo/celular/nombre/cédula Levenshtein ≤2)
  o cédula = su propio celular → POSIBLE TYPO (no se agrega, se reporta); resto → naranja.
- Las 7 filas naranjas de retiradas se eliminaron de General (verificando cédula antes de borrar).
- RESUMEN gana campos `retiradas=` y `posibles_typos=`; el IF de n8n solo busca `estado=exito`,
  no requiere cambios. Dry-run verificado: `nuevas=0 retiradas=7 posibles_typos=0`.
- Gotcha: una sola señal no basta — hubo un caso de celular compartido entre dos mujeres
  distintas (Maricela Montalban / Arlenis Nieto) que un umbral de 1 señal marcaría como typo.
- Pendiente humano: corregir las 13 cédulas con typo (a veces el error está en la BD, no en el
  form — ej. `11433751119` de 11 dígitos) y confirmar las 4 nuevas reales.

---

## 2026-07-08 — [q10-consolidacion · mr-actualizacion-datos] Auditoría de disparadores por tiempo

**Estado:** Completado (verificación del ciclo 16:00 en curso).
**Procesos relacionados:** [[q10-consolidacion]] · [[mr-actualizacion-datos]] · [[convenciones]]

- Hallazgo 1: dashboard congelado desde las 8:50 — el Schedule 4h SÍ disparó (15:00) pero
  `organizador_headless.py` moría con `GSpreadException: header row contains duplicates`.
  Causa: fórmula manual `FILTRAR(...)` en `H1Test!J1` (quedó `#NAME?`, dejó H1/I1 como
  encabezados vacíos). Fórmula rescatada y removida:
  `=FILTRAR(E1:F5828; ISNUMBER(SEARCH("Emprendimiento: Idea de Negocio JC"; E1:E5828)) * (F1:F5828<>"100%") * ...)`
- Fix de raíz: lectura tolerante `leer_registros()` (ignora encabezados vacíos/duplicados) en
  `organizador_headless.py`, `retirados_headless.py`, `export_retirados.py` y `organizador_Q10.py`
  (el .exe de operadores necesita rebuild). Convención nueva en [[convenciones]].
- Hallazgo 2: los Schedule Triggers corrían en America/New_York (default n8n sin GENERIC_TIMEZONE);
  el trigger de MR (7:30) equivalía a 6:30 Colombia y nunca disparó (n8n arranca ~8:45).
- Fix: `settings.timezone=America/Bogota` en ambos workflows vía API + `GENERIC_TIMEZONE` y `TZ`
  en `iniciar_n8n.bat`; trigger de MR movido a 9:30 am. JSONs re-exportados a `n8n-workflows/`.
- Catch-up manual: organizador + export_stats corridos a mano (dashboard al día, push OK).
- Zoom-Asistencia no tiene triggers de tiempo (solo webhook) — no aplica.

---

## 2026-07-08 — [q10-consolidacion] Ledger de avances: "aprobó y se retiró" como 4° segmento

**Estado:** Completado — corrida real verificada, paneles publicados.
**Proceso relacionado:** [[q10-consolidacion]] · [[dashboard-web]] · `export_aprobacion.py`

- Problema: Q10 inhabilita TODAS las matrículas del estudiante y su avance desaparece del
  Consolidado → cursos ya aprobados contaban como "no aprobó" en el panel de aprobación.
- Solución: ledger local `tools/aprobacion_ledger.json` (PII, gitignoreado) con máximo avance
  visto por estudiante×curso (keepMax por corrida). Cada inhabilitado se clasifica por curso:
  `aprobados_retirados` (≥100 antes de irse) o `retirados` (se fue sin aprobar).
- Siembra histórica: `tools/seed_ledger_avance.py` vuelca la hoja manual Avance (863 estudiantes,
  cohorte completa) al ledger — única fuente del avance de los ya inhabilitados.
- Resultado: 66/80 inhabilitados de Nivel 1 habían aprobado Bienvenida → 90.2% → 97.9%
  (Hackea +49 → 95.7%, Habilidades +21 → 88.2%, Emprendimiento +2).
- Paneles aprobacion/ y dashboard/ (tab 1): barra de 4 segmentos — azul `#3A6FB8` = "aprobó y
  se retiró" (el azul de marca #406C9E falla el piso de croma del validador dataviz).
- maximos.json ahora protege `aprobados_total`; déficit se reclasifica a aprobados_retirados
  (los 4 segmentos siempre suman `cursaron`). Test sintético OK.
- Ajuste final: panel aprobacion/ filtrado a solo Jóvenes creaTIvos — KPIs desde por_programa[]
  (estudiantes_cohorte=860, retirados_unicos=85, % global JC 84.3 sin mezclar MR), se quitó la
  tarjeta "Matrículas en cursos" y la tabla resumen por programa. Tab 1 del dashboard sigue
  mostrando ambos programas.

---

## 2026-07-08 — [dashboard-web] Fase 1 refactorización 2026: Tab 1 solo-JC + exclusión de pruebas

**Estado:** Completado — criterio de cuadre EXITOSO (bloqueante para Fase 2, cumplido).
**Proceso relacionado:** [[dashboard-web]] · [[q10-consolidacion]] · Plan: PROMPT-plan-dashboard-2026.md

- Tab 1 del dashboard filtrado a Jóvenes creaTIvos: KPIs desde `por_programa[]` (nuevos campos
  `habilitados_unicos`, `matriculas_activas`, `sin_finalizar` por programa) — ya no mezcla MR.
  Nuevo KPI "Estudiantes hábiles" (777 hábiles, 5.439 matrículas activas).
- El "bug pct_aprobados por programa" del plan YA estaba corregido (d95e010); aplicar la corrección
  literal habría contado doble los aprobados_retirados (84.4→86.8 era espejismo).
- Exclusión de usuarios de prueba: son 4 (el plan decía 3 — también existe "Mujeres Prueba" en MR).
  Lista en tools/exclusiones_prueba.json (gitignoreado) aplicada en aprobacion/stats/retirados.
  Efecto: cohorte Nivel 1 860→857, retirados únicos JC 85→82 (3 pruebas contaban como retirados).
- maximos.json reiniciado (re-sembrado sin pruebas); la marca de agua ahora preserva la identidad
  cursaron == aprobados + aprobados_retirados + sin_finalizar + retirados (déficits se reclasifican).
- --sin-push agregado a export_stats.py y export_retirados.py (antes siempre publicaban).
- Cuadre verificado: identidad en los 9 cursos + sumas de tabla == KPIs por programa, exacto.
  Patrón de exclusión documentado en [[convenciones]].

---

## 2026-07-08 — [dashboard-web] Fase 2 refactorización 2026: Comparativo solo-JC + panel MR con cohorte

**Estado:** Completado — solo frontend, ningún exporter cambió (no aplicó corrida --sin-push).
**Proceso relacionado:** [[dashboard-web]] · Plan: PROMPT-plan-dashboard-2026.md

- Barrido de años < 2026 en todos los HTML de docs/: cero coincidencias — nada que limpiar.
- Tab Admin: sin cambios; la exclusión de pruebas de Fase 1 ya vive en export_stats.py y el JSON
  publicado cuadra con aprobación (JC 777, MR 282 = habilitados_unicos).
- Tab Comparativo: la columna "Q10" usaba totales{} (mezclaba MR: 1.139/6.168/81,1%); ahora usa
  por_programa[] JC (857/5.789/84,7%) y los 2 cursos MR ya no salen como filas grises "solo Q10".
- Panel Mujeres ROFÉ: ahora lee también ../aprobacion/data.json — KPIs de cohorte MR 2026
  (282 mujeres, 26,4% aprobación = 100/379 matrículas, 0 retiradas), barra apilada de aprobación
  por curso (misma paleta 4 segmentos que JC), semáforo sobre % aprobó de la cohorte, y
  degradación elegante a solo-avance si falta el JSON de aprobación.
- Gotcha documentado: las dos fuentes capitalizan distinto los nombres de curso (Título vs
  MAYÚSCULAS) — cruce con toUpperCase() + colapso de espacios.
- Verificación: sintaxis JS OK + smoke test en Node (stubs DOM/fetch sobre los JSON reales):
  joins MR 2/2, identidad de cuadre por curso true, KPIs y filas verificados.

---

## 2026-07-09 — [dashboard-web] Fase 3 refactorización 2026: Retirados 2026 + etapa + funnel

**Estado:** Completado — corrida real --sin-push verificada, JSON regenerados (pendiente push).
**Proceso relacionado:** [[dashboard-web]] · [[q10-consolidacion]] · Plan: PROMPT-plan-dashboard-2026.md

- Panel Retirados filtrado a la cohorte 2026: pasa de 353 histórico a **82 retirados únicos**,
  el mismo número que `retirados_unicos` del panel de aprobación (cuadre exacto verificado).
  Filtro por cédula contra `tools/cohorte_2026.json`, NO por FechaCancelacion.
- Nuevo handoff PII entre exporters: `export_aprobacion.py` persiste `tools/cohorte_2026.json`
  (cohorte + retirados únicos por programa, con cédulas, gitignoreado); `export_retirados.py` lo
  lee para filtrar sin re-loguear en Q10. Degrada al histórico si el archivo falta.
- Heurística de etapa de retiro (con `tools/aprobacion_ledger.json`): cada retirado se ubica en el
  último curso de la ruta 2026 con avance ≥ 100. Gráfico "¿En qué etapa de la ruta los perdimos?"
  en el panel. Hallazgo real: **78 de 82 se retiraron en los 3 primeros cursos**, pico de 28 tras
  Hackea tu Cerebro; solo 14 no completaron ninguno. Es heurística de secuencia, no temporal
  (Q10 no da fecha de retiro fiable) — así documentado en la UI.
- Tab Tendencia: nuevo **funnel de retención** desde aprobacion/data.json (cursos en orden de ruta,
  largo ∝ cursaron, verde = aprobaron / ámbar = quedaron en el camino); la línea de snapshots de
  history.json queda como vista secundaria debajo.
- `sin_registro_hoja` (2): inhabilitados de la cohorte sin registro formal en la pestaña Retirados;
  se cuentan aparte para que por_tipo/causa/programa/etapa sumen exacto al total (82).
- Gotcha de orden: en el workflow n8n export_retirados corre antes que export_aprobacion, así que
  usa la cohorte del ciclo anterior (4 h de lag, aceptable — el set cambia lento). El archivo ya
  existe tras esta corrida manual, sin hueco.
- Verificación: py_compile OK · corrida real export_aprobacion + export_retirados --sin-push ·
  smoke test de render (Node) de retirados (2026 y fallback histórico) y del funnel Tab 5 ·
  paleta del gráfico de etapa validada con el validador de dataviz. Patrones nuevos en [[convenciones]].

---

## 2026-07-09 — [q10-consolidacion] Excluir desertores de todas las estadísticas + reconciliación 857/82

**Estado:** Completado (código + docs) — corrida real --sin-push verificada, JSON regenerados (pendiente push).
**Proceso relacionado:** [[q10-consolidacion]] · [[dashboard-web]]

- Duda del usuario resuelta: el desajuste 777 vs 775 = el par fantasma (2 inhabilitados sin
  cancelación, Samuel Murcia 1034662377 + Vicenzo Vecchio 58464721) contado como retirado y a la
  vez restado del último curso. Activos reales = 775; identidad cierra como 857=775+82 o 855=775+80,
  nunca 777. Documentado como decisión pendiente (no aplicar hasta confirmar si siguen activos).
- **Desertores excluidos de TODAS las estadísticas** (`Tipo=Desertor` / "Decisión de la Institución"):
  se tratan como perfiles de prueba. `export_aprobacion.py` (fuente de verdad) ahora deriva el set de
  desertores del dict `retirados` y lo une a `cargar_exclusiones()` antes de `aplicar_exclusiones()`
  (`TIPOS_RETIRO_EXCLUIDOS = {"desertor"}` + helper `cedulas_por_tipo_retiro`). Propaga solo a los dos
  paneles vía `cohorte_2026.json`; el frontend consume los JSON dinámicamente (nada hardcodeado).
- **Gotcha marca de agua:** al bajar la cohorte, el watermark `cursaron` de `maximos.json` resucitaba
  a los desertores como retirados (`deficit_cursaron`). Fix: resetear las 7 entradas JC de maximos.json
  (conservando las 2 de Mujeres ROFÉ) para rebaselinar. Mismo patrón del fix fantasma revertido.
- Verificación corrida real --sin-push: 34 desertores en el histórico, 25 en cohorte 2026 →
  cohorte JC 857→832, retirados únicos 82→57 (55 cancelados + 2 fantasma), desertores 0. Identidad
  832 = 775 activos + 57 retirados. maximos.json rebaselinó a 832/791/779 sin resucitar a nadie.
  export_retirados --sin-push coherente (total 57, cancelados 55, desertores 0). py_compile OK.
- Pendiente: push a producción (dashboard público) — no ejecutado, a la espera de OK del usuario.

---

## 2026-07-09 — [panel-datos-etl] Revisión del plan + Fase 0 Supabase completada

**Estado:** Fase 0 completada — proyecto Supabase vivo, schema aplicado, RLS verificada.
**Proceso relacionado:** [[panel-datos-etl]] (nuevo) · [[dashboard-web]] · [[q10-consolidacion]]

- Auditados los 5 docs del plan (raíz, generados en claude.ai): 13 fallas corregidas — MySQL→PostgreSQL,
  ENUM inline inválido, uuid_generate_v4 sin extensión, regla de validación falsa (primaria⇒edad<20),
  rate limiting inexistente, backups solo-Pro, netlify.toml roto, react-query@3 obsoleto, PII expuesta
  en endpoint público, view_retirados contradiciendo la definición canónica (832=775+57), contradicción
  histórico SCD2 vs MVP, fuente sociodemográfica sin confirmar. Notas ⚠️ al pie de cada doc.
- Hallazgo crítico verificado por MCP: el project ID `sqmrnirbakcrbhdlfxxz` de los docs NO existía en
  la cuenta (solo 2 proyectos INACTIVE). Creado `panel-datos-rofe` (`kbxptoowtnteflhrfwid`, us-east-1, $0/mes).
- Matriz de 6 decisiones completada con las recomendadas: 1A sync n8n · 2 escalonada (Type1+snapshots→SCD2)
  · 3A solo admin · 4A público solo-agregados · 5A Next.js custom · 6B MVP 2 semanas.
- Schema aplicado en 2 migraciones (schema_base_panel_datos + snapshots_diarios_participants): 6 tablas
  con RLS, advisor de seguridad limpio. Smoke test REST con anon key: agregados 200, participants
  privados 0 filas, escritura anónima 401. Datos de prueba insertados y borrados.
- Artefactos: `.env.example` + `.env.local` (gitignoreado; agregado `.env.*` a .gitignore),
  `scripts/panel-datos/test_conexion_supabase.py` (stdlib+truststore, corrida real TODO OK),
  `docs/procesos/panel-datos-etl.md`, credencial documentada en [[convenciones]].
- Bloqueadores Fase 1a: confirmar fuente de datos sociodemográficos (no están en pestañas Q10;
  candidatas BD-MR y BD monitorias) + copiar service_role key del Dashboard a `.env.local` (manual).

---

## 2026-07-09 — [panel-datos-etl] Fase 1a + carga inicial a Supabase

**Estado:** Completado — normalización y carga real verificadas, BD poblada.
**Proceso relacionado:** [[panel-datos-etl]] · [[q10-consolidacion]]

- Cuenta Supabase depurada: Samuel eliminó los 2 proyectos viejos; queda solo `panel-datos-rofe`.
  Secret key validada (insert/read/delete real). Gotcha nuevo: Supabase rechaza secret keys con
  User-Agent de navegador → scripts usan UA propio `panel-datos-etl/1.0`.
- `normalize_q10_data.py` (Fase 1a): h2test en bloques (patrón detectar_grupos) + Retirados;
  excluye desertores (34) y perfiles de prueba (9); cédula solo dígitos, aprobado > 80, keepMax
  en duplicados. Corrida real: 1.059 participantes / 9 cursos / 5.818 matrículas, 0 errores,
  2 advertencias (avances 101 clampeados). Cuadre: 1.059 ≈ 775 activos JC + 283 MR ✔.
- `cargar_supabase.py`: snapshot previo → participants_snapshots, upserts por lotes de 500 con
  FKs resueltas. Migración nueva `courses_unique_nombre_cohorte` (sin ella el upsert duplicaba
  catálogo). Doble corrida = mismos conteos + snapshot 1.059 filas → idempotencia verificada.
- Estados en BD: 4.983 completado (>80) · 528 en_progreso · 307 inscrito (0%). PII solo en
  tools/ (payload + reporte de validación); nada nuevo en docs/ públicos.
- Gotcha: un curso MR contiene coma en el nombre — no parsear listas por coma.
- Pendiente: Fase 1b (workflow n8n normalize→cargar diario), recompute de agregados
  (participant_metrics/cohorte_stats vacíos), mapeo sociodemográfico BD monitorias, campo
  `programa` JC/MR (hoy solo en tools/course_config.json). Sin commit aún.

---

## 2026-07-09 — [panel-datos-etl] Fase 1b: agregados + workflow n8n q10-sync-supabase activo

**Estado:** Completado — sync diario automático en producción.
**Proceso relacionado:** [[panel-datos-etl]] · [[convenciones]]

- Migración `recompute_aggregates_fn`: función SQL (SECURITY DEFINER, solo service_role;
  REVOKE a anon/authenticated) que upserta participant_metrics y cohorte_stats desde
  enrollments/courses y limpia huérfanos. `cargar_supabase.py` la invoca vía /rpc al final de
  cada carga. Corrida real: 1.059 métricas + cohorte 2026 poblada; anon ya lee agregados reales.
- Workflow n8n `q10-sync-supabase` (ID `uSizw3dNzpb6n53H`) creado y activado por API, exportado a
  `n8n-workflows/q10-sync-supabase.json`. Cadena: Schedule diario 9:45 COT → normalize → IF
  estado=exito → cargar → IF → OK/stopAndError. Decisión: 9:45 en vez del 04:00 UTC del plan
  (PC apagado a las 23:00; n8n arranca ~8:45 y el workflow MR corre 9:30). "con_advertencias"
  (FKs perdidas) también dispara el camino de error — nunca en silencio.
- Gotcha API n8n: POST /activate sin body → "unsupported media type"; mandar JSON '{}' explícito.
- Pendiente: verificar 1ª corrida automática (mañana 9:45), mapear sociodemográficos (BD
  monitorias), Fase 2 (materialized views + campo programa), Fase 3 (Next.js + Netlify),
  Fase 4 (cuadre vs dashboard GitHub Pages). Sin commit aún.

---

## 2026-07-09 — [panel-datos-etl] Fase 2: sociodemográficos reales + vistas públicas

**Estado:** Completado — commit 72d827d (fases 0-1b) + esta fase.
**Proceso relacionado:** [[panel-datos-etl]] · [[bd-seguimiento-monitorias]]

- Introspección de la BD de monitorias (35 pestañas): SÍ hay género/fecha nac/edad/ciudad/grupo
  (Seguimiento) y situación de emprendimiento (Diagnostico c32, 4 categorías limpias); NO existen
  vivienda/estrato/estado_civil/nivel_estudio en ninguna fuente → nullable documentados.
  `Link Emprendimiento` es el Zoom de la clase, no emprendimiento del estudiante.
- Migraciones: `sociodemograficos_reales` (enum emprendimiento_situacion + 4 columnas + índices)
  y `vistas_agregadas_dashboard` (5 vistas v_* con GRANT anon; lint security_definer_view
  aceptado y documentado — solo agregados). `sync_sociodemograficos.py`: 775 actualizados
  (= activos JC canónicos), 162 sin match (retirados), edad promedio 18.0, emprendimiento
  98/180/363/55. Hallazgo: emprendimiento ~no correlaciona con cursos (6.16 vs 6.34).
- Gotchas nuevos (en mapa-codigo): float→str de openpyxl mete cero extra en cédulas;
  PGRST102 bulk exige claves idénticas; NOT NULL se valida antes del ON CONFLICT.
- Pendiente: 1ª corrida automática n8n (10-jul 9:45), Fase 3 (Next.js + Netlify), retirados
  en Supabase (hoy solo activos), re-correr sync al cambiar la BD (evaluar leer el Sheet vivo).

---

## 2026-07-09 — [panel-datos-etl] Fase 3: frontend Next.js en repo dedicado

**Estado:** Construido y compilado — pendiente: crear repo GitHub + conectar Netlify (Samuel).
**Proceso relacionado:** [[panel-datos-etl]]

- Repo nuevo `downloads/panel-datos-rofe` (commit inicial e7fe030). Next.js 14 App Router con
  **output:'export'** → sitio 100% estático (decisión: los datos se consultan client-side a las
  vistas públicas con anon key, así Netlify publica `out/` sin plugin ni SSR — se elimina de raíz
  el netlify.toml roto del plan original).
- 4 tabs: Resumen (KPIs + completación por curso, criterio >80 = mismo del panel de aprobación),
  Cursos (stacked bars + tabla), Emprendimiento (dona 4 categorías + relación con cursos, con el
  hallazgo "avanzan parejo"), Demografía (grupos, género apilado, edades en rangos).
- Identidad ROFÉ: paleta oficial 2025 en tailwind.config (azul marca #406C9E solo chrome, datos
  con verde/amarillo/naranja/rojo/azul2), Century Gothic, logo Aplicación 2, eslogan en footer.
- Build OK: First Load JS 195 kB (criterio < 500 kB). Preview local verificado (http.server 3210).
- Gotcha: tsconfig de Next sin `target` → es5 rechaza regex \p{L}; fijar ES2018.
- Pendiente Samuel: crear repo GitHub `panel-datos-rofe` + push + Netlify import. Luego Fase 4
  (cuadre vs GitHub Pages) y retirados en Supabase.

---

## 2026-07-10 — [panel-datos-etl] Fase 4: MVP en producción + cuadre 9/9 exacto

**Estado:** MVP COMPLETO — panel público vivo en https://classy-pasca-eecdd6.netlify.app
**Proceso relacionado:** [[panel-datos-etl]] · [[dashboard-web]]

- Samuel creó el repo GitHub y conectó Netlify: deploy verificado (HTTP 200, título y logo OK).
- `test_cuadre_dashboard.py` (Fase 4): v_curso_completion vs docs/aprobacion/data.json.
  Primera corrida: 2 descuadres (+4/+9 aprobados en cursos ACTIVOS) → diagnóstico: frescura,
  no bug (aprobacion regenerado hoy 8:32 por el pipeline 4h; carga Supabase de ayer 20:28 —
  12 h de avance real). Re-sync fresco → **9/9 cursos exactos en activos Y aprobados** (0 de
  tolerancia usada). Deriva esperada documentada: sync diario acota a ≤24 h.
- Pendiente: verificar 1ª corrida automática n8n (hoy 9:45 — a las 8:33 aún sin ejecuciones,
  correcto), retirados en Supabase, campo programa JC/MR, renombrar sitio Netlify (opcional).

---

## 2026-07-10 — [panel-datos-etl] Sección JC/MR + historial de datos Q10

**Estado:** Completado y en producción (push frontend → Netlify auto-deploy).
**Proceso relacionado:** [[panel-datos-etl]] · [[dashboard-web]]

- Pedido stakeholders: panel separado Jóvenes creaTIvos / Mujeres ROFÉ + visualizar historial.
- Migración `programa_e_historial`: enum programa_type en courses (clasificación canónica
  course_config.json + keywords en normalize), tabla `historial_cursos` (UNIQUE fecha+curso,
  pública, sin PII), v_curso_completion + programa, vista nueva v_programa_stats (JC 777/MR 282 ✔).
- Historial: backfill de docs/dashboard/history.json (75 filas, 9 snapshots desde 2026-06-26)
  vía backfill_historial.py + snapshot diario nuevo en cargar_supabase (paso 6) — la serie crece
  sola con el workflow n8n de las 9:45.
- Frontend: selector de programa (JC azul / MR naranja), tabs Emprendimiento y Demografía solo
  en JC (fuente = BD monitorias JC), tab Historial con líneas de matrículas y avance por curso.
  Build 198 kB. Repo GitHub real: soportejunior-codeJR/PowerBi.
- Backlog: sociodemográficos MR desde BD-Mujeres ROFÉ, retirados en Supabase.

---

## 2026-07-10 — [panel-datos-etl] Cohortes históricas Q10 (2023-2025) importadas

**Estado:** Completado — 2.875 participantes totales en Supabase, selector de cohorte en producción.
**Proceso relacionado:** [[panel-datos-etl]] · [[q10-consolidacion]]

- Confirmación de diseño: courses.cohorte + UNIQUE(nombre, cohorte) ya soportaba multi-cohorte.
- Sondeo empírico de Q10 (tools/sondear_periodos_q10.py, pids 1-40): el Consolidado conserva el
  histórico CON avance — 2.880 cédulas únicas; pids 25-40 vacíos. Los +3.000 = 2.880 + 353
  retirados históricos (inhabilitados, invisibles al Consolidado — limitación documentada).
- importar_historico_q10.py con mapa EXPLÍCITO periodo→cohorte (sin inferencias): 2023 pids 2-7,
  2024 pids 9/10/12/14 (⚠ "Único Horario nivel 1-3" sin año — asignados 2024, confirmar con
  equipo), 2025 pids 16(MR)/17/18/19. 2026 excluido (fuente = sync diario). Solo cédulas nuevas.
- Resultado: +1.816 participantes (2.875 totales, cuadra con sondeo menos exclusiones), 39
  cursos·cohorte, 18.195 matrículas, 0 errores/0 sin_fk. v_programa_stats ganó dimensión cohorte.
- Frontend: selector de cohorte (2026/2025/2024/2023); cohortes pasadas → Resumen+Cursos con
  nota "no incluye retirados". Gotcha clave: Q10 reutiliza nombres de curso entre años.
