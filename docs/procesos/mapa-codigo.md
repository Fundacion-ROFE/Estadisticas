# Mapa de Código

> Índice esquemático de todos los scripts del proyecto. Sin código fuente.
> Actualizar cuando se agregue/modifique un script.
> **Conexiones:** [[q10-consolidacion]] · [[dashboard-web]] · [[zoom-asistencia]]

---

## Ubicaciones raíz

| Carpeta / Archivo | Contiene |
|---|---|
| `scripts/q10-consolidacion/` | Scripts de extracción Q10 y exportación a Sheets/JSON |
| `scripts/q10-consolidacion/organizador/` | App GUI standalone (.exe) para operadores |
| `tools/` | Herramientas locales — gitignoreado |
| `tools/panel_riesgo_gui.py` | GUI de análisis de riesgo con PII |
| `tools/course_config.json` | Clasificación JC/MR/Stand-by de cursos (editada desde GUI Admin) |
| `docs/dashboard/` | Dashboard público GitHub Pages — solo JSON agregados |

---

## `q10_to_sheets.py`

**Propósito:** Login multi-paso en Q10 → descarga Consolidado de los 3 periodos activos (21, 22, 23) → extrae info del estudiante directamente del Consolidado → sube a Google Sheets. Sin endpoint Estudiantes, sin JOIN.

**Servicios:** Q10 (`site6.q10.com` — endpoints internos AJAX, no API pública) · Google Sheets API

**Credenciales:** `credenciales_service_account.json` · usuario/password Q10 hardcodeados en el script

**Comando:**
```bash
python q10_to_sheets.py --grupo h1test          # → pestaña H1Test (Sheet interno)
python q10_to_sheets.py --grupo h2test          # → pestaña h2test (Sheet público)
python q10_to_sheets.py --grupo retirados       # → pestaña Retirados (reporte Estudiantes cancelados)
python q10_to_sheets.py --grupo h1test --anio 2025  # forzar año distinto al actual
```

**Funciones principales:**

| Función | Parámetros | Retorna | Descripción |
|---|---|---|---|
| `login_q10()` | — | `requests.Session` | 7 pasos AJAX encadenados (ver [[convenciones#Q10 Login multi-paso]]) |
| `leer_excel_bytes(contenido)` | `bytes` | `pd.DataFrame` | Parse xlsx, auto-detecta fila header por palabras clave |
| `descargar_todos_consolidados(session, anio)` | `Session, str` | `pd.DataFrame` | **Autodescubre** periodos: sondea `RANGO_PERIODOS`, conserva solo los del `anio` (columna `Período`), concatena |
| `_periodo_es_del_anio(etiqueta, anio)` | `str, str` | `bool` | Año = último token tras el guión: `Unico MR-2026` → `2026` |
| `mapear_columnas(df_cons)` | `pd.DataFrame` | `pd.DataFrame` | Consolidado → formato H1Test (ID, Nombre, Celular, Email, Curso, Avance, Estado) |
| `descargar_retirados(session)` | — | `pd.DataFrame` | Reporte `GestionAcademica/EstudiantesCancelados` — histórico completo, sin filtros |
| `mapear_columnas_retirados(df)` | `pd.DataFrame` | `pd.DataFrame` | Reporte cancelados → formato Retirados (10 columnas, ver abajo) |
| `_q10_post_ajax(session, url, data, referer)` | — | `Response` | Helper AJAX POST con headers corporativos |

**Grupo `retirados`:** usa el reporte `Estudiantes cancelados` (no el Consolidado). Columnas de la pestaña `Retirados`: `Identificacion | Nombre | TipoDocumento | Telefono | Programa | Sede | FechaCancelacion | Causa | Descripcion | Tipo`. `Tipo` ∈ {Cancelado, Desertor, Aplazado}. **El reporte NO incluye Email ni Curso** — no se puede cruzar por email con h2test/Avance. La pestaña se autocrea si no existe.

**Variables clave en script:**
```
MAPEO_GRUPOS: dict         # --grupo → nombre pestaña Sheets
MAPEO_SHEET_IDS: dict      # --grupo → Sheet ID
RANGO_PERIODOS = range(18,41)  # IDs de periodo a sondear (ampliar si Q10 supera 40)
AÑO_OBJETIVO = str(año actual) # solo periodos de este año; override con --anio
TAMANIO_LOTE = 500         # Filas por lote al subir (cuota API)
PAUSA_LOTE = 1.2           # Segundos entre lotes
COL_PERIODO = "Período"    # texto autoetiquetado con el año, ej. "Logica-Nivel 2-2026"
COL_NOMBRES/APELLIDOS/ID/CELULAR/EMAIL/CURSO/AVANCE  # Columnas del Excel Consolidado
```

**Autodescubrimiento por año (desde 2026-07-05):** en vez de una lista fija de periodos, el script
sondea `RANGO_PERIODOS`, lee la columna `Período` de cada uno y conserva **solo los del año en curso**
(o `--anio YYYY`). Así entra cualquier curso/cohorte nuevo del año sin tocar código, y nunca se mezclan
años previos (evita doble conteo). Mapa de periodos verificado 2026-07-05:

| ID | Período | Programa/Curso | ¿Incluido? |
|---|---|---|---|
| 18 | Logica-Nivel 2-**2025** | JC (año viejo) | ❌ descartado |
| 19 | Habilidades-Nivel 1-**2025** | JC (año viejo) | ❌ descartado |
| 20 | Desarrollo-Nivel 3-2026 | **Desarrollo Web HTML** (502) | ✅ |
| 21 | Logica-Nivel 2-2026 | Lógica + IA (777) | ✅ |
| 22 | Habilidades-Nivel 1-2026 | Bienvenida/Hackea/Emprend/Habilid (780) | ✅ |
| 23 | Unico MR-2026 | Mujeres ROFÉ (283) | ✅ |
| 24 | Desarrollo-Avanzado-2026 | **Desarrollo Web HTML** (275) | ✅ |

Las periodos 20 y 24 comparten el mismo `Nombre asignatura` (`Desarrollo Web Front-End - HTML - 2026`),
cédulas disjuntas → el `organizador` las fusiona en un bloque de **777** (= columna HTML del manual).

**Gotcha:** IDs 25–40 devuelven `not_results` — descartados sin error. URLs Azure Blob expiran en ~3 min.
El Consolidado incluye toda la info del estudiante — no se necesita el endpoint `/Estudiantes`.

---

## `export_stats.py`

**Propósito:** Lee pestaña `h2test` → clasifica cursos por programa (JC/MR/Stand-by) → agrega estadísticas por curso → genera `docs/dashboard/data.json` → git commit + push.

**Servicios:** Google Sheets API (read only)

**Sheet:** `h2test` — ID `1q4VNn4ltqVEMsOjo-c2ZbsbW3VIt-XomPgXeLSN_LTs`

**Clasificación de cursos:** lee `tools/course_config.json` primero; si el curso no está en el config, usa keywords `["emprendedoras", "idea a la acci"]` → MR; todo lo demás → JC.

**Comando:**
```bash
python export_stats.py
```

**Funciones principales:**

| Función | Retorna | Descripción |
|---|---|---|
| `detectar_grupos(row0, row1)` | `list[dict]` | Detecta grupos de cursos desde doble encabezado (celdas fusionadas) |
| `_cargar_config_cursos()` | `dict` | Lee `tools/course_config.json`; retorna `{"jc":[], "mr":[], "stand":[]}` |
| `_clasificar_curso(nombre, config)` | `"jc"\|"mr"\|"stand"` | Config tiene precedencia sobre keywords |
| `_procesar_grupos(filas, grupos)` | `(por_curso, emails, habilitados, av0, avirr)` | Agrega estadísticas para un subconjunto de grupos |
| `procesar_h2test(all_values)` | `(pc_jc, pc_mr, pc_stand, anom_jc, anom_mr, n_jc, hab_jc, n_mr, hab_mr, n_stand, hab_stand, total_db)` | Separa y procesa los tres programas |
| `generar_json(...)` | `dict` | Construye JSON con secciones JC (top-level) + `mr` + `stand` |
| `enriquecer_con_maximos(*listas)` | `dict` | Marca de agua: añade `inscritos`/`finalizados`/`promedio_pico`/`finalizado` a cada curso in-place; retorna dict de máximos |
| `_enriquecer_curso(c, maximos, hoy)` | — | Actualiza el pico del curso y calcula el flag `finalizado` |
| `_seed_maximos_desde_history()` | `dict` | Siembra máximos iniciales desde `history.json` (pico de matrícula) |
| `guardar_maximos(maximos)` | — | Escribe `docs/dashboard/maximos_cursos.json` |
| `guardar_json(datos)` | — | Escribe `docs/dashboard/data.json` |
| `git_commit_y_push(timestamp)` | — | `git add` (data.json + maximos_cursos.json) + `commit` + `push origin main` |

**Output JSON:** `docs/dashboard/data.json` — cada curso lleva ahora `estudiantes` (activos hoy),
`inscritos`/`finalizados`/`promedio_pico`/`finalizado` (marca de agua congelada). Estructura general:
`{por_curso[] (JC), anomalias[], totales{}, mr:{...}, stand:{...}}`. Estado persistente en
`docs/dashboard/maximos_cursos.json`.

**Gotcha:** `total_estudiantes_unicos` en la sección `mr` es el count de emails únicos (dedup entre ambos cursos MR), no la suma de inscritas. El contador de anomalías "AVANCE 0%" es por matrícula, no por estudiante única.

**Gotcha (marca de agua):** `finalizados` en vivo también encoge si un estudiante al 100% se archiva;
por eso se congela el máximo. `inscritos` de cursos con pico **anterior** al 26-jun (inicio de
history.json) puede quedar subestimado — no hay forma de recuperarlo desde Q10. Ver [[dashboard-web#Cursos finalizados — marca de agua (inscritos → finalizados)]].

---

## `export_avance.py`

**Propósito:** Lee pestaña `Avance` del Sheet manual → agrega avance por curso → genera `docs/avance/data.json` → git commit + push.

**Servicios:** Google Sheets API (read only)

**Sheet:** `Avance` — ID `1ggzoJeZR3fS6AwRCLoGeYA5HEp_B7zvOwFGlGwny0l8`

**Comando:**
```bash
python export_avance.py
python export_avance.py --segmento "Logica-Nivel 2-2026"
python export_avance.py --sin-push     # pruebas (no toca git)
```

**Funciones principales:** (mismo patrón que `export_stats.py`)

| Función | Retorna | Descripción |
|---|---|---|
| `detectar_grupos(row0, row1)` | `list[dict]` | Detecta grupos por sub-header "Número identificación" en fila 2 |
| `procesar_avance(all_values)` | `(por_curso, totales, anomalias)` | Agrega % progreso por curso nombrado; cuenta SIN ETIQUETA |
| `generar_json(...)` | `dict` | Incluye campo `segmento` y `anomalias[]` |
| `git_commit_y_push(timestamp)` | — | Push a `docs/avance/data.json` |

**Output JSON:** `docs/avance/data.json` — estructura `{segmento, por_curso[], totales{}, anomalias[]}`.
Desde 2026-07-07 cada curso lleva además `aprobados` (avance ≥ 100) y `pct_aprobados`, y `totales.total_aprobados` — los consume el Tab 2 del dashboard (formato barras apiladas de aprobación).

**Gotcha:** Los primeros 3 grupos de columnas en la hoja Avance no tienen nombre de curso en fila 1 → se cuentan como SIN ETIQUETA. Los 6 cursos nombrados empiezan en col 15.

---

## `export_aprobacion.py`

**Propósito:** Aprobación por curso con la **cohorte 2026 completa** (habilitados + inhabilitados). Loguea directo en Q10 (no pasa por Sheets), cruza 3 reportes por cédula y genera `docs/aprobacion/data.json` (solo agregados) → git commit + push.

**Servicios:** Q10 (`site6.q10.com` — 3 reportes Excel internos) · git

**Fuentes cruzadas (por cédula normalizada — solo dígitos):**

| Reporte Q10 | Qué aporta |
|---|---|
| Consolidado Educación Virtual (por periodo) | Activos con avance por asignatura |
| Consolidado Estudiantes Matriculados — modo **Detallado** (por periodo) | Cohorte completa del periodo, **incluye inhabilitados** (Programa, Jornada, Nivel, Estudiante, Identificación) |
| Estudiantes cancelados (histórico) | Confirma que inhabilitado = retirado |

**Lógica:** `inhabilitados = cohorte_matriculados − activos_virtual`. **Aprobado = avance > 80** (cambio 2026-07-09; antes ≥ 100 — `UMBRAL_APROBADO=80.0` con operador `>`). Los retirados del periodo se atribuyen a cada asignatura del periodo. Asignaturas con el mismo nombre en varios periodos se fusionan (Desarrollo Web: periodos 20+24).

**Bandas de progreso (2026-07-09):** cada curso lleva `banda_0_25` / `banda_26_80` / `banda_81_100` — conteo de los **activos** por rango de avance (suman exacto a `activos`; `banda_81_100` == `aprobados`). Las consumen las barras de los frontends: en cursos **en curso** (`!finalizado`) la barra apilada muestra estas 3 bandas (naranja `--orange` riesgo 0-25 · ámbar 26-80 · verde >80 en meta) + aprobó-y-retiró + retirado, para ver el riesgo respecto al avance esperado; en cursos **finalizados** se mantiene el formato de 4 segmentos. Paleta validada con el validador CVD de dataviz. El mismo render está en `docs/aprobacion/index.html` (`cursoRow`) y `docs/dashboard/index.html` (`stackRow`); los cursos MR (sin bandas) caen al formato viejo.

**Ledger de avances (2026-07-08):** Q10 inhabilita **todas** las matrículas del estudiante y su avance desaparece del Consolidado. Para no perder a los que ya habían aprobado, el script mantiene `tools/aprobacion_ledger.json` (PII, gitignoreado): máximo avance visto por estudiante×curso, keepMax en cada corrida. Con él, cada inhabilitado se clasifica por curso en `aprobados_retirados` (alcanzó ≥ 100 antes de irse) o `retirados` (se fue sin aprobar). El % aprobó usa `aprobados_total = aprobados + aprobados_retirados`. Sembrado inicial desde la hoja manual Avance con `tools/seed_ledger_avance.py` (863 estudiantes, mapeo ALIAS manual→Q10, fusiona bloques duplicados con keepMax). Resultado primera corrida: 66 de los 80 inhabilitados de Nivel 1 habían aprobado Bienvenida → su % pasó de 90.2 a 97.9. Marca de agua en `docs/aprobacion/maximos.json`: ahora protege `aprobados_total`; si el conteo vivo baja, el déficit se **reclasifica** de `retirados` a `aprobados_retirados` (los 4 segmentos siempre suman `cursaron`).

**Comando:**
```bash
python export_aprobacion.py              # año en curso, commit + push
python export_aprobacion.py --sin-push   # pruebas (no toca git)
python export_aprobacion.py --anio 2026
```

**Funciones principales:**

| Función | Retorna | Descripción |
|---|---|---|
| `descargar_matriculados_periodo(session, pid)` | `pd.DataFrame` | Reporte matriculados Detallado; el POST replica los hidden `Filtros[i].Name/PartialName` del form (sin ellos → HTTP 400) |
| `descargar_fuentes(session, anio)` | `(virtual, cohortes, retirados)` | Autodescubre periodos del año (mismo patrón que `q10_to_sheets`) y baja las 3 fuentes |
| `cargar_ledger()` / `actualizar_ledger()` / `guardar_ledger()` | `dict` | `{cedula: {curso: max_avance}}` — memoria keepMax en `tools/aprobacion_ledger.json` |
| `agregar_por_curso(..., ledger)` | `(lista, anomalias, prog_stats, prog_stats_raw)` | Agrega por asignatura normalizada; fusiona periodos homónimos; clasifica inhabilitados contra el ledger. `prog_stats_raw` lleva los sets de cédulas (cohorte/retirados) por programa |
| `guardar_cohorte(prog_stats_raw, anio)` | — | Persiste `tools/cohorte_2026.json` (PII): cohorte y retirados únicos por programa. Lo consume `export_retirados.py` para filtrar a 2026 sin re-descargar de Q10 (2026-07-09) |
| `aplicar_maximos(lista)` | — | Marca de agua sobre `aprobados_total`/`cursaron`; déficit → `aprobados_retirados` |
| `generar_json(...)` | `dict` | `{por_curso[], por_programa[], totales{}, anomalias{}, periodos[]}` |

**Output JSON:** `docs/aprobacion/data.json` — por curso: `cursaron`, `activos`, `aprobados` (activos ≥ 100), `aprobados_retirados`, `aprobados_total`, `no_aprobados`, `sin_finalizar`, `retirados` (sin aprobar), `pct_aprobados` (sobre total), `promedio`, `finalizado` (promedio ≥ 90). Totales incluyen `total_aprobados_retirados`. En `por_programa[]` (2026-07-08): `estudiantes_cohorte`, `habilitados_unicos`, `retirados_unicos`, `matriculas_activas`, `sin_finalizar` — fuente de los KPIs solo-JC del Tab 1 y del panel de aprobación. Identidad garantizada: `cursaron == aprobados + aprobados_retirados + sin_finalizar + retirados` (la marca de agua reclasifica déficits en vez de romperla). Excluye usuarios de prueba vía `tools/exclusiones_prueba.json` (ver [[convenciones#Exclusión de usuarios de prueba en exporters]]).

**Consumidor:** `docs/aprobacion/index.html` (panel público, botón "Aprobación ↗" en el dashboard) y los tabs 1–3 de `docs/dashboard/index.html`. Ambos muestran barra apilada de **4 segmentos**: verde aprobó-activo · azul `#3A6FB8` aprobó-y-se-retiró · ámbar sin completar · rojo retirado sin aprobar (paleta validada CVD con el validador de dataviz; el azul de marca `#406C9E` falla el piso de croma — no usar en marcas de datos). El panel `aprobacion/` filtra a **solo Jóvenes creaTIvos** (const `PROGRAMA` en el HTML) y sus KPIs salen de `por_programa[]` (`estudiantes_cohorte`, `retirados_unicos`, `pct_aprobados` — 2026-07-08); el tab 1 del dashboard sigue mostrando ambos programas.

**Automatización (2026-07-07):** integrado al workflow n8n `Bot Q10 - Actualizar Grupos` (ID `Rblg81qifVshsRae`) en ambas ramas: `Sched: export_aprobacion` (Schedule 4h) y `Ejecutar export_aprobacion` (comando Telegram — el bot reporta "Aprobación → GitHub Pages (% aprobó)").

**Orden de dependencia corregido (2026-07-09):** en el workflow, `export_aprobacion` ahora corre **ANTES** de `export_retirados` en ambas ramas (cadena: `organizar retirados → export_aprobacion → export_retirados → export_sin_completar`). `export_aprobacion` **genera** `tools/cohorte_2026.json` y `tools/aprobacion_ledger.json`, que `export_retirados` **consume**. Antes corrían al revés → el panel de retirados usaba la cohorte del ciclo anterior (atraso de 4h, se auto-corregía pero desincronizaba retirados vs aprobación). `export_aprobacion` loguea directo en Q10, no depende de la pestaña Retirados, así que puede ir primero sin problema.

**Gotchas (hallazgos de la exploración 2026-07-07):**
- El switch **"¿Incluir archivados?"** (`archivado=true`) del Consolidado de Educación Virtual **NO devuelve a los inhabilitados** — retorna exactamente los mismos activos. Los inhabilitados solo salen por el reporte de Matriculados.
- El reporte **ConsolidadoNotasCuantitativo** es por logro/actividad (~16k filas para Bienvenida) y Q10 corta en **5.000 registros** → inviable como fuente.
- El Excel de matriculados trae título/filtros arriba: los headers reales están en la fila que contiene `Identificación`; la identificación viene con prefijo de tipo de documento (`C.C. 123...`) → normalizar a solo dígitos para cruzar.
- La cohorte de matriculados puede ser menor que el pico histórico de h2test (860 vs 863 en Bienvenida): Q10 elimina del reporte a algunas matrículas anuladas del todo. Diferencia ≤ 3 estudiantes, asumida.
- `anomalias.inhabilitados_sin_retiro` (5 casos al 2026-07-07): inhabilitados que no están en el reporte de cancelados — posibles archivados al cerrar curso; vigilar si crece.
- **Q10 inhabilita por estudiante, no por curso** (práctica del equipo, confirmada 2026-07-08): al inhabilitar se pierden TODAS sus matrículas del Consolidado, incluidas las de cursos ya aprobados. Sin el ledger, cada inhabilitación restaba aprobados reales de cursos ganados (Bienvenida mostraba 90.2% en vez de 97.9%).

---

## `export_asistencia.py`

**Propósito:** Lee pestaña `asistencias` (registro manual por sesión, 4 col/módulo: Nombre/Apellido/Correo/ID) → genera `docs/asistencia/data.json`.

**Estado:** Funcional pero actualmente no usado por el dashboard (reemplazado por `export_avance.py`). Útil si se necesita análisis de sesiones presenciales.

**Comando:**
```bash
python export_asistencia.py --segmento "Logica-Nivel 2-2026"
```

**Output JSON:** `docs/asistencia/data.json` — estructura `{segmento, sesiones[{nombre, asistentes}], totales{}}`

---

## `export_retirados.py`

**Propósito:** Lee pestaña `Retirados` → **filtra a la cohorte 2026** → agrega por tipo/causa/programa/mes **y por etapa de retiro** → genera `docs/retirados/data.json` (sin PII) → git commit + push.

**Servicios:** Google Sheets API (read only)

**Sheet:** `Retirados` — mismo Sheet que h2test (`1q4VNn4ltqVEMsOjo-c2ZbsbW3VIt-XomPgXeLSN_LTs`)

**Filtro 2026 (2026-07-09):** cruza las cédulas de la pestaña contra `tools/cohorte_2026.json`
(generado por `export_aprobacion.py`). El conjunto autoritativo de retirados 2026 son los
**inhabilitados de la cohorte** (`por_programa[*].retirados`) — el mismo `retirados_unicos` del
panel de aprobación (82), NO se filtra por `FechaCancelacion` (poco fiable). Los inhabilitados sin
registro en la pestaña se cuentan como `sin_registro_hoja` para que los totales cuadren exacto.
Si falta `cohorte_2026.json`, degrada al histórico completo (353) con advertencia — funciones
`procesar_2026()` vs `procesar_historico()`.

**Etapa de retiro (heurística, 2026-07-09):** para cada retirado, su "última etapa completada" =
último curso de la ruta 2026 (const `RUTA_2026`, orden cronológico) con avance ≥ 100 en
`tools/aprobacion_ledger.json`. Agrupa en `por_etapa[]` (orden 0 = "no completó ninguno", 1..7 =
índice en la ruta). Q10 no guarda fecha de retiro por estudiante fiable → la etapa se infiere del
avance máximo, no de cuándo dejó de estudiar. `etapa_de_retiro(cedula, ledger)` → `(orden, etiqueta)`.

**Comando:**
```bash
python export_aprobacion.py --sin-push   # PRIMERO — genera tools/cohorte_2026.json
python export_retirados.py --sin-push    # luego — lee la cohorte y filtra a 2026
```

**Output JSON:** `docs/retirados/data.json` — `{anio, totales{total_retirados, cancelados, desertores, aplazados, sin_registro_hoja}, por_tipo[], por_causa[], por_programa[], por_mes[], por_etapa[{orden, etapa, cantidad}], ruta[]}`. Con `anio=null` (fallback histórico) `por_etapa` va vacío.

**Consumidor:** `docs/retirados/index.html` (panel público, botón "Retirados ↗" en el dashboard) — KPIs cohorte 2026 + gráfico "¿En qué etapa de la ruta los perdimos?". El render degrada al histórico si `anio` es null.

---

## `setup_headers.py`

**Propósito:** Escribe la fila 1 de headers en H1Test o h2test. **Uso único** (inicialización). Modo diagnóstico por defecto — requiere `--confirmar` para escribir.

**Servicios:** Google Sheets API (write)

**Comando:**
```bash
python setup_headers.py --pestaña h2test              # diagnóstico
python setup_headers.py --pestaña h2test --confirmar  # escribe
```

**Pestañas configuradas:** `H1Test` · `h2test` · `Retirados`

**Headers escritos (H1Test):** `Identificacion | Nombre | Celular | Email | Curso | Avance | Estado` (7 cols — `Estado` alinea con lo que sube `q10_to_sheets.mapear_columnas()`; `organizador_headless` lo lee por nombre vía `get_all_records`)
**Headers escritos (h2test):** `Identificacion | Nombre | Celular | Email | Curso | Avance` (config legacy; hoy h2test se escribe en bloques por curso desde `organizador_headless`)
**Headers de Retirados:** `Identificacion | Nombre | TipoDocumento | Telefono | Programa | Sede | FechaCancelacion | Causa | Descripcion | Tipo`

**Gotcha:** la guarda de `main()` solo escribe si la fila 1 está **vacía** o ya coincide — nunca sobrescribe un header con contenido distinto (por seguridad). Para *agregar* una columna a un header existente, escribir la celda directamente (ej. `G1`). El script ahora fuerza stdout/stderr a UTF-8 para no crashear con `→`/acentos en consolas cp1252.

---

## `organizador/organizador_headless.py`

**Propósito:** Versión sin GUI del organizador — para uso en n8n y automatizaciones. Lee H1Test, ordena por curso, escribe h2test en formato de bloques horizontales + pestañas Observaciones y Estadisticas.

**Servicios:** Google Sheets API (read H1Test + write h2test, Observaciones, Estadisticas)

**Sheets:**
- Origen: H1Test — ID `1d3S41J9nlVI3qCy-WF_D3ZezTwRCW17vnL7u284XDG0`
- Destino: h2test — ID `1q4VNn4ltqVEMsOjo-c2ZbsbW3VIt-XomPgXeLSN_LTs`

**Comando:**
```bash
python organizador/organizador_headless.py
```

**Funciones principales:**

| Función | Retorna | Descripción |
|---|---|---|
| `leer_h1test(gc)` | `pd.DataFrame` | Lee H1Test, normaliza columnas (flexible al casing) |
| `calcular_observaciones(df)` | `pd.DataFrame` | Detecta SIN MATCH, SIN CURSO, AVANCE 0%, AVANCE IRREGULAR |
| `calcular_estadisticas(df)` | `dict` | Promedio/min/max por curso, totales, anomalías |
| `escribir_h2test(gc, df)` | `(cursos, sin_curso)` | Escribe bloques horizontales por curso (5 cols + 2 sep) |
| `escribir_observaciones(gc, df)` | `int` | Escribe pestaña Observaciones con los casos anómalos |
| `escribir_estadisticas(gc, df)` | `dict` | Escribe pestaña Estadisticas con resumen general y por curso |

**Output parseable para n8n:**
```
RESUMEN: cursos=N estudiantes=M promedio=P estado=exito
```

**Formato h2test:** cada curso es un bloque de 5 columnas (`Identificacion, Nombre, Celular, Email, Avance`) con fila 0 = nombre del curso en mayúsculas. Los bloques se concatenan horizontalmente con 2 columnas vacías de separación. Esta estructura es la que leen `detectar_grupos()` en `export_stats.py`.

---

## `organizador/retirados_headless.py`

**Propósito:** Lee pestaña `Retirados` (cruda) → limpia fechas/duplicados → escribe `Retirados-complete` en bloques horizontales por Tipo (CANCELADO / DESERTOR / APLAZADO) + bloque RESUMEN (totales por tipo y causa). Sin GUI — para n8n.

**Servicios:** Google Sheets API (read Retirados + write Retirados-complete, mismo Sheet de h2test)

**Comando:**
```bash
python organizador/retirados_headless.py
```

**Formato Retirados-complete:** cada tipo es un bloque de 8 columnas (`Identificacion, Nombre, TipoDocumento, Telefono, Programa, FechaCancelacion, Causa, Descripcion`) con fila 0 = tipo en mayúsculas, fila 1 = sub-headers, ordenado por fecha desc. Bloques concatenados horizontalmente con 2 columnas de separación (mismo patrón que h2test). Último bloque = RESUMEN (Metrica | Valor).

**Output parseable para n8n:**
```
RESUMEN: retirados=N cancelados=X desertores=Y aplazados=Z estado=exito
```

---

## `organizador/organizador_Q10.py`

**Propósito:** App GUI (CustomTkinter, dark mode) para operadores no técnicos. Interfaz visual para revisar y aprobar la carga de H1Test → h2test antes de automatizar. Se distribuye como `.exe` compilado con PyInstaller.

**Estado:** Secundario — la automatización usa `organizador_headless.py`. El `.exe` sigue disponible para revisión manual con interfaz gráfica.

**Servicios:** Google Sheets API (read H1Test + write h2test)

**Sheets:**
- Origen: H1Test — ID `1d3S41J9nlVI3qCy-WF_D3ZezTwRCW17vnL7u284XDG0`
- Destino: h2test — ID `1q4VNn4ltqVEMsOjo-c2ZbsbW3VIt-XomPgXeLSN_LTs`

**Compilar .exe:**
```bash
cd scripts/q10-consolidacion/organizador
build_exe.bat
```

**Credenciales en .exe:** `credenciales_service_account.json` embebido vía PyInstaller. Ruta resuelta dinámicamente por `obtener_ruta_credenciales()` según si corre en dev o PyInstaller (`sys._MEIPASS`).

---

## `tools/panel_riesgo_gui.py`

**Propósito:** GUI Tkinter de análisis de riesgo. Cruza h2test (Q10) × Avance (manual) por email, clasifica estudiantes y permite explorar los datos con tablas interactivas. Gestiona también la clasificación de cursos por programa.

**Servicios:** Google Sheets API (read — ambos Sheets)

**⚠ PRIVACIDAD:** Maneja PII en memoria. Nunca subir a GitHub. `tools/` está en `.gitignore`.

**Comando:**
```bash
python tools/panel_riesgo_gui.py
```

**Arquitectura interna:**

```
_worker()  →  leer_h2test() + leer_avance() + cruzar()  →  queue
_on_listos()  →  _build_resumen_jc() + _build_tab_mr() + _build_tab_admin()
```

**Tabs:**

| Tab | Descripción |
|---|---|
| 🎓 Jóvenes creaTIvos | 6 KPI cards clickeables → tabla dinámica (ver vistas abajo) |
| ⚠ Atención | Una fila por (estudiante, curso) con avance < umbral; doble clic → popup detalle |
| 💡 Mujeres ROFÉ | 6 KPI cards clickeables → tabla dinámica (ver vistas abajo) |
| ⚙ Admin | Lista de todos los cursos con ComboBox JC/MR/Stand-by; Guardar → `course_config.json` |
| 🚪 Retirados | 5 KPI cards clickeables (Todos/Cancelados/Desertores/Aplazados/Causas) → tabla con info completa del retiro; doble clic → popup detalle; lee pestaña `Retirados` |

**Vistas JC** (tarjeta activa se resalta; tabla cambia en tiempo real):

| Vista | Fuente de datos | Columnas clave |
|---|---|---|
| EN Q10 JC | `q10_jc.values()` | Nombre · Email · **una columna por curso JC** (etiqueta corta `_etiqueta_jc()`) · Promedio |
| CURSOS | `_jc_by_course` (agregado por curso) | Curso · Activos · Promedio · Mín · Máx · Aprobados ≥100% · % Aprobó (activos). ⚠ Denominador = solo activos en h2test; el panel público de aprobación divide entre la cohorte completa (incluye retirados) — por eso los % difieren |
| MATCH AMBAS | `casos["atencion"] + avance_0 + ok` | Nombre · Cédula · Email · Q10 % · Manual % · Estado |
| ATENCIÓN | `casos["atencion"]` | Nombre · Cédula · Email · **Curso** · Q10 % · Manual % · Estado |
| AVANCE 0% | `casos["avance_0_cruzado"]` | Nombre · Cédula · Email · # Cursos · Manual % · Diagnóstico |
| SIN MATCH | `casos["sin_match_manual"]` | Nombre · Email · # Cursos · Promedio Q10 % |
| OK ✓ | `casos["ok"]` cruzado con `q10_jc` | Nombre · Cédula · Email · Q10 % · Manual % |

**Vistas MR:**

| Vista | Columnas clave |
|---|---|
| MUJERES | Nombre · Cédula · Email · # Cursos · Promedio · Estado |
| CURSOS | Nombre curso · Inscritas · Promedio · Mín · Máx · Estado |
| PROMEDIO / OK / RIESGO | Nombre · Email · [Curso 1] · [Curso 2] · Promedio |
| AVANCE 0% | Nombre · Email · [Curso 1] · [Curso 2] |

**Componente `TablaFiltrable`:** búsqueda de texto en tiempo real · filtro por columna específica · ordenamiento por header · doble clic configurable · exportar CSV de la vista activa.

**Funciones clave de datos:**

| Función | Retorna | Descripción |
|---|---|---|
| `leer_h2test(gc)` | `(q10_jc, q10_mr, cursos_info)` | Lee h2test, clasifica por `course_config.json`, retorna dicts por programa + lista de cursos para Admin |
| `leer_avance(gc)` | `dict[email→{cursos[]}]` | Lee pestaña Avance, colapsa por email |
| `leer_retirados(gc)` | `list[dict]` | Lee pestaña Retirados; lista vacía si la pestaña no existe (no bloquea el panel) |
| `cruzar(q10, avance, umbral)` | `(casos, total_av, total_q)` | JOIN por email → atencion/avance_0_cruzado/sin_match_manual/ok |
| `_build_resumen_jc(...)` | — | Construye tab JC con header + KPIs clickeables + frame de tabla |
| `_set_jc_view(vista)` | — | Resalta tarjeta activa y regenera tabla según la vista |
| `_build_tab_mr(q10_mr)` | — | Construye tab MR con header + KPIs clickeables + barras + frame de tabla |
| `_set_mr_view(vista)` | — | Resalta tarjeta activa MR y regenera tabla |
| `_build_tab_admin(cursos_info)` | — | Lista scrollable de cursos con ComboBox; lee config inicial |
| `_guardar_admin()` | — | Lee todos los ComboBox → escribe `tools/course_config.json` |

**Gotcha:** `cruzar()` solo ve estudiantes que están en Q10 JC. Los que solo están en el manual (no en Q10) no aparecen en ninguna vista JC — solo se cuenta su total en el header.

---

## `tools/course_config.json`

**Propósito:** Fuente de verdad para la clasificación de cursos por programa. Editado desde el Tab Admin de `panel_riesgo_gui.py` — nunca a mano.

**⚠ PRIVACIDAD:** No contiene PII, pero está en `tools/` (gitignoreado) porque es configuración operativa local que puede cambiar entre ciclos. No subir a GitHub.

**Estructura:**
```json
{
  "jc":    ["NOMBRE EXACTO DEL CURSO EN MAYÚSCULAS", ...],
  "mr":    ["DE LA IDEA A LA ACCIÓN...", "HABILIDADES DEL SER..."],
  "stand": []
}
```

Los nombres deben coincidir exactamente con cómo aparecen en fila 1 de h2test (espacios normalizados, sin `\xa0`). Si el archivo no existe o un curso no aparece en ninguna lista, `_clasificar_curso()` en `export_stats.py` usa keywords de fallback.

---

## `tools/panel_riesgo.py`

**Propósito:** Cruza pestaña `Avance` (manual) × pestaña `h2test` (Q10) por email → identifica estudiantes en riesgo → 4 secciones de reporte en consola + CSV opcional.

**Servicios:** Google Sheets API (read — ambos Sheets)

**⚠ PRIVACIDAD:** Maneja PII (nombres, IDs, correos). Nunca subir a GitHub. `tools/` está en `.gitignore`.

**Comando:**
```bash
python tools/panel_riesgo.py
python tools/panel_riesgo.py --segmento "Logica-Nivel 2-2026"
python tools/panel_riesgo.py --csv              # exporta tools/reportes/*.csv
python tools/panel_riesgo.py --umbral 50        # umbral de atención (default 60%)
```

**Secciones del reporte:**

| Sección | Contenido |
|---|---|
| Resumen de cruce | Totales, % con Q10, % SIN MATCH, % atención |
| Casos de atención | Avance < umbral%, con sesiones presenciales |
| SIN MATCH | En hoja manual pero sin registro en Q10 |
| Avance 0% cruzado | Distingue "acceso bloqueado" vs "abandono" según asistencia |

**Funciones principales:**

| Función | Retorna | Descripción |
|---|---|---|
| `leer_h2test(gc)` | `dict[email → {cursos[]}]` | Agrupa filas de h2test por email |
| `leer_asistencias(gc)` | `dict[email → {sesiones[]}]` | Lee pestaña Avance (nombre interno legacy) |
| `cruzar(q10, asist, umbral)` | `(casos, total_ses, total)` | Join por email, clasifica en atencion/sin_match/avance_0/ok |
| `exportar_csv(casos, segmento, umbral)` | — | Escribe 3 CSVs en `tools/reportes/` |

**Nota:** `leer_avance()` lee la pestaña `Avance` del Sheet manual (no la pestaña `asistencias`).

---

## `scripts/mr-actualizacion-datos/actualizar_bd_mr.py`

**Propósito:** Sincroniza la pestaña `General` de **BD-Mujeres ROFÉ 2026** con las respuestas del
Google Form "Actualización de datos MR2024". Cruce por cédula; actualiza solo celdas que cambian;
fila tocada → `Fecha Actualización` (col AL) con la fecha de la corrida. Respuestas sin match se
clasifican: cédula en pestaña `Inactivas` → RETIRADA (no se agrega); ≥2 señales de match con otra
fila (correo/celular/nombre/cédula parecida) → POSIBLE TYPO (no se agrega, se reporta); solo las
realmente nuevas van al final con fondo naranja. Ver [[mr-actualizacion-datos]].

**Servicios:** Google Sheets API (read fuente + write destino)

**Sheets:**
- Fuente: `Actualización de datos MR2024 (respuestas)` — ID `13a32oExVw64Scpo2YgnMjytXsIIMVNi07NvYoD8QYH0`, pestaña `Respuestas de formulario 1`
- Destino: `BD-Mujeres ROFÉ 2026` — ID `1ZsC4WyY26aOCEMrnZ_l8Tn-l69DB_0ADs5lnecaoEP8`, pestaña `General`

**Comando:**
```bash
python actualizar_bd_mr.py            # escribe
python actualizar_bd_mr.py --dry-run  # solo reporta
```

**Funciones principales:**

| Función | Retorna | Descripción |
|---|---|---|
| `leer_fuente(gc)` | `(total, {cedula: (ts, fila)}, omitidas)` | Deduplica por cédula — gana la marca temporal más reciente |
| `construir_valores(fila_form)` | `dict[col→valor]` | Normaliza nombre (title case), correo (lower), celular (10 dígitos), tipo doc (`cc`/`ce`/`ppt`), emprendimiento (`No`→`N/A`) |
| `difiere(actual, nuevo, col)` | `bool` | Diff **insensible a tildes**; vacío nunca sobreescribe |
| `sin_tildes(v)` | `str` | Unaccent NFD para comparación |
| `senales_match(ced, nombre, correo, celular, cand)` | `list[str]` | Señales de misma persona: correo igual, celular igual, nombre exacto/contenido, cédula Levenshtein ≤2 |
| `clasificar_sin_match(nuevas, gen_cand, inac_ced, inac_cand)` | `(retiradas, typos, reales)` | Clasifica respuestas sin match; typo requiere ≥2 señales o cédula = su propio celular |

**Output parseable para n8n:**
```
RESUMEN: respuestas=N unicas=M filas_actualizadas=X sin_cambios=Y nuevas=Z retiradas=R posibles_typos=T omitidas=W estado=exito
```

**Gotcha:** la columna `Fecha Actualización` se localiza por header (no índice fijo) porque la fila 1
de General tiene una celda basura en AK. El form llega sin tildes → sin comparación unaccent el diff
"actualiza" nombres correctos degradándolos. Workflow n8n: `mr-actualizacion-datos`
(ID `LgkDbNPERYgKMrYj`, diario 7:30).

---

## `scripts/zoom-asistencia/`

**Propósito:** Automatización de asistencia Zoom. Workflow n8n activo (`Zoom - Asistencia`,
ID `jkNaE51PKQ4TQzNq`). Ver [[zoom-asistencia]] para detalle completo de nodos y pruebas.

| Archivo | Contiene |
|---|---|
| `.env` | Credenciales Zoom S2S OAuth (`ZOOM_ACCOUNT_ID`, `ZOOM_CLIENT_ID`, `ZOOM_CLIENT_SECRET`, `ZOOM_WEBHOOK_SECRET_TOKEN`) — gitignoreado. Cargado como env vars del proceso n8n por `iniciar_n8n.bat`. |
| `nodo-calcular-momentos-dorados.js` | Código del nodo Code `Calcular Momentos Dorados` en el workflow — calcula si cada participante estuvo conectado en los 3 "momentos dorados" (min 10, mitad, 10 min antes del fin) a partir de `join_time`/`leave_time` de `past_meetings/{uuid}/participants`. Copia de referencia — la fuente de verdad real es `n8n-workflows/zoom-asistencia.json`. |
| `setup_zoom_asistance.py` | Setup (idempotente) de las pestañas `ZOOM-ASISTANCE` (destino del workflow, formato condicional <70% rojo / >=70% verde), `CUPOS` (inscritos por clase desde `tools/cupos_clases.json` + `Día`/`Hora` parseados con `parsear_horario()` + tabla `Palabra clave → Área`; columna `Alias Zoom` editable que se preserva al regenerar) y `ZOOM-STATS` (estadísticas por sesión y por semana ISO, solo fórmulas; cupo resuelto en cascada: nombre exacto → alias → área+día+hora del evento con tolerancia ±45 min). Constantes clave: `SHEET_ID`, `UMBRAL=70`, `FILAS_ASIST=20000`, `KEYWORDS_AREA`. **Gotcha:** el spreadsheet es locale `es_ES` — helper `loc()` convierte `,`→`;` en fórmulas; los arrays `{...}` usan `\` como separador de columnas; evitar decimales literales en fórmulas (usar `3/4`, no `0.75`). |

## `tools/corroborar_asistencia_h3test.py` (local, gitignoreado)

**Propósito:** Validación persona por persona de la asistencia Zoom — cruza los correos de los asistentes (pestaña `H3Test` o `ZOOM-ASISTANCE`) contra `h2test` (Q10, correos reales) y reporta por sesión: estudiantes verificados como matriculados, no encontrados (correo con typo, email distinto al de Q10, invitado externo o bot), staff y sin email. ⚠ Imprime PII en consola — solo local. `python tools/corroborar_asistencia_h3test.py [--pestaña ZOOM-ASISTANCE]`

## `tools/analizar_cupos_bd.py` (local, gitignoreado)

**Propósito:** Análisis de la BD Seguimiento de Monitorias (xlsx pseudonimizado en Downloads) — cuenta estudiantes asignados por clase en las columnas `Horario *` de la pestaña `Seguimiento` → escribe `tools/cupos_clases.json` (89 clases, sin PII: nombre de clase + conteo). Re-ejecutar cuando cambie la BD y luego correr `setup_zoom_asistance.py` para refrescar `CUPOS`.

## `tools/exportar_sin_completar.py` (local, gitignoreado)

**Propósito:** Toma de estudiantes JC **sin completar** curso (avance < 100 en h2test) con ubicación —
cruza por cédula normalizada (fallback email) contra la BD Seguimiento de Monitorias (pestaña
`Seguimiento`: columna `Grupo` = ciudad del encargado) y escribe **bloques horizontales por
ciudad** (tabla primaria = ciudad lado a lado, mismo patrón que h2test, 2 cols de separación;
dentro de cada bloque los cursos = tablas secundarias apiladas) en el Sheet **SinCompletar**
(ID `1OkafT8PYfGOUuTbojTYGy8pbuc4Jf6hO-_IOlQ3Fge8`, pestaña `SinCompletar`). Cursos MR excluidos
(`course_config.json` + keywords). Columnas: Nombre · Cédula · Email · Celular · Ciudad · Avance %.
Formato: jerarquía en azul ROFÉ (ciudad oscuro / curso claro), avance con formato condicional
(<60 rojo claro, 60–99 amarillo claro), fila título congelada. Idempotente: recrea la pestaña en
cada corrida (add tmp → delete vieja → rename). `python tools/exportar_sin_completar.py [--dry-run]`

**Gotchas:** El API rechaza decimales literales en `ConditionValue` con locale es → usar enteros
(mismo tipo de gotcha que las fórmulas de `setup_zoom_asistance.py`). La BD referencia
`BD Seguimiento de Monitorias - JC2026.xlsx` (sin codificar, Downloads) — actualizar `RUTA_BD` si
cambia la versión del archivo. Primera corrida 2026-07-08: 709 matrículas sin completar, 11 sin
ubicación (98.4% match), grupos BOG/CTG/BAQ/MED/GYL/UY/CAL/PAN/QTO/BAQ2 (+`GRUPO_LABEL`).
**El Sheet destino debe estar compartido como Editor con el Service Account**
(`q10-automatizacion@n8n-automatizacion-q10.iam.gserviceaccount.com`) — el acceso de edición
por enlace es frágil: el 2026-07-08 se degradó a solo-lectura y la escritura empezó a dar 403.

**Automatización (2026-07-08):** integrado al workflow n8n `Bot Q10 - Actualizar Grupos`
(ID `Rblg81qifVshsRae`) en ambas ramas, después de export_aprobacion: `Sched: export_sin_completar`
(Schedule 4h) y `Ejecutar export_sin_completar` (comando Telegram, antes de `Responder OK` — el bot
reporta "Sin completar → Sheet (N en K ciudades)"). Al insertar el nodo antes de `Responder OK`,
las referencias `$json` de ese nodo (que apuntaban a export_aprobacion) se cambiaron a
`$('Ejecutar export_aprobacion')`.

## `tools/verificar_retirados_bd.py` (local, gitignoreado)

**Propósito:** Verificación de coherencia de retirados — cruza la pestaña `S Retirados` de la BD Seguimiento de Monitorias (pseudonimizada; restaura ID/nombre/email en memoria con la clave del pseudonimizador `clave_samuel_2026-07-02.json` de Downloads) contra el reporte `Estudiantes cancelados` de Q10 (descarga fresca vía `q10_to_sheets`). Match por cédula normalizada, fallback por nombre. Reporta: en ambas / en BD sin Q10 (→ CSV en `tools/reportes/`) / en Q10-2026 sin BD (informativo). ⚠ Imprime PII en consola — solo local. Última corrida (2026-07-03): 55/55 retirados de la BD confirmados en Q10 por cédula. `python tools/verificar_retirados_bd.py` — actualizar las rutas `RUTA_BD`/`RUTA_CLAVE` cuando cambie la versión del archivo.

**Gotcha:** el script asume que el nodo "Info Reunion" (`GET /past_meetings/{uuid}`) y el nodo "Participantes" (`GET /past_meetings/{uuid}/participants`) ya existen en el workflow con esos nombres exactos — si se renombran en n8n, hay que actualizar las referencias `$('Info Reunion')` dentro del Code.

## `n8n-workflows/zoom-asistencia.json`

**Propósito:** Export del workflow `Zoom - Asistencia` (14 nodos: Webhook Trigger + validación
CRC/firma HMAC vía nodos Crypto + fan-out ack-inmediato/procesamiento-en-fondo + Wait 90s +
OAuth manual a Zoom + Info Reunion + Participantes paginado + Code + Google Sheets Append).

**Credenciales n8n asociadas (creadas vía API, no en el JSON por seguridad):**
- `Zoom S2S Basic Auth` (httpBasicAuth) — client_id/secret de Zoom.
- `Zoom Webhook HMAC Secret` (crypto) — Secret Token de Zoom Webhook. Editar manualmente desde
  la UI de n8n cuando Zoom lo entregue (la API pública no soporta editar credenciales).
- `Q10 Automatizacion Service Account` (googleApi) — mismo Service Account de
  `credenciales_service_account.json`, con acceso ya confirmado a `H3Test`.

---

## Dependencias comunes

```
gspread · google-auth · truststore · requests · pandas · openpyxl
```

Ver `scripts/q10-consolidacion/requirements.txt` para versiones exactas.

**SSL corporativo:** todos los scripts llaman `truststore.inject_into_ssl()` al inicio. Ver [[convenciones#SSL corporativo]].
