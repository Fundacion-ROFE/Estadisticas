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

