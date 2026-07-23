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

**Propósito:** GUI Tkinter de análisis de riesgo. Cruza el avance real de Q10 (ahora leído de Supabase — `participants`/`enrollments`/`courses`, cohorte actual) × Avance (manual, Sheet) por email, clasifica estudiantes y permite explorar los datos con tablas interactivas. Gestiona también la clasificación de cursos por programa.

**Servicios:** Supabase (`panel-datos-rofe`, REST/PostgREST, `service_role`, solo lectura) para `leer_h2test()` · Google Sheets API (read) para `leer_avance()` (pestaña Avance, manual) y `leer_retirados()` (pestaña Retirados — única excepción, ver Gotcha)

**⚠ PRIVACIDAD:** Maneja PII en memoria. Nunca subir a GitHub. `tools/` está en `.gitignore`. Credenciales Supabase en `.env.local` raíz (mismo patrón `sync_*.py`); credenciales Sheets en `credenciales_service_account.json`.

**Comando:**
```bash
python tools/panel_riesgo_gui.py
```

**Verificación standalone (sin lanzar la GUI):**
```bash
python tools/verificar_supabase_panel_riesgo.py
```

**Arquitectura interna:**

```
_worker()  →  conectar_supabase() + leer_h2test(supa)   (Supabase)
           +  conectar() + leer_avance(gc)               (Sheet Avance, manual)
           +  cruzar()  →  queue
_on_listos()  →  _build_resumen_jc() + _build_tab_mr() + _build_tab_admin()
```

**Migración a Supabase (Fase 1 de `panel-riesgo-mejora.md`, 2026-07-21):** `leer_h2test()` dejó
de leer la pestaña Sheet h2test en vivo — ahora hace GET a `/enrollments` con embeds PostgREST
(`participants!inner`, `courses!inner`) filtrado a la cohorte actual (detectada como el máximo
`cohorte` en `cohorte_ingresos`, sin hardcodear el año). Mismo shape de retorno de siempre
`(q10_jc, q10_mr, cursos_info)` — ningún tab/vista cambió. `leer_avance()` y `leer_retirados()`
NO cambiaron (decisión documentada en `panel-riesgo-mejora.md`): Avance es una fuente manual
genuinamente distinta (el tab Diferencias existe para comparar Q10 automático vs manual) y
Retirados individuales no existen como filas en Supabase (limitación de Q10). Verificado contra
`cohorte_ingresos`/`aprobacion_cursos`: JC 777 activos y MR 283 activos coinciden exacto, 9/9
cursos comparados sin diferencia.

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
| `leer_h2test(supa)` | `(q10_jc, q10_mr, cursos_info)` | **Supabase** (`enrollments`+`participants`+`courses`, cohorte actual), clasifica por `course_config.json`, retorna dicts por programa + lista de cursos para Admin |
| `leer_avance(gc)` | `dict[email→{cursos[]}]` | Sheets — lee pestaña Avance (manual), colapsa por email — sin cambios (Fase 1) |
| `leer_retirados(gc)` | `list[dict]` | Sheets — lee pestaña Retirados; lista vacía si la pestaña no existe (no bloquea el panel) — sin cambios, excepción permanente |
| `conectar_supabase()` | `_Supa` | Cliente REST mínimo con `service_role` (mismo patrón `sync_*.py`), solo lectura |
| `_cohorte_actual(supa)` | `str` | Máximo `cohorte` presente en `cohorte_ingresos` — evita hardcodear el año |
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

**Exclusión de perfiles de prueba (2026-07-21):** este script NO aplicaba
`tools/exclusiones_prueba.json` (ya usado por `export_aprobacion.py` desde 2026-07-08) — "Jovenes
Prueba", "Pruebas Estudiantes JC" y "Pruebas Soporte IT" se colaban en los conteos, todos bajo
`SIN UBICACIÓN` (son cuentas de prueba, no tienen fila real en la BD Seguimiento). Agregado
`cargar_exclusiones()` (mismo patrón, cédula normalizada) y filtro en `leer_sin_completar()` antes
de construir `por_curso`/`por_curso_todos` — afecta automáticamente SinCompletar, Historico,
Semaforo y Balance (todos derivan de esa función). Se purgaron también las 16 filas de prueba que
ya habían quedado en `Historico` de las corridas previas (semanas W29 y W30) con un script puntual
de limpieza (no forma parte del repo). Efecto: `SIN UBICACIÓN` bajó de 9 a 1 fila (student×curso;
el resto de esas 9 eran las cuentas de prueba), total sin completar 546→538, semáforo 768→760
casos. `Mujeres Prueba` (4° perfil del archivo de exclusiones) no aplica aquí — es de Mujeres ROFÉ,
este script es solo JC.

**Nota — grupo `BAQ2` en la BD Seguimiento (aclarado y resuelto 2026-07-21):** no era un subgrupo
real de Barranquilla. Al ir a corregir la fila se descubrió que **el Sheet en vivo ya tenía el
typo corregido** (`Grupo="BAQ"` para ese estudiante) — el `BAQ2` solo existía en un **xlsx local
desactualizado** en Downloads (`RUTA_BD`, 12 filas de diferencia contra el Sheet real) que este
script leía en vez de la fuente viva. Mismo síntoma que motivó la migración de
`sync_sociodemograficos.py` ese mismo día. Fix aplicado: `leer_ubicaciones(gc)` ahora lee
directamente el Sheet **`BD Seguimiento de Monitorias`** (`BD_SHEET_ID =
1ggzoJeZR3fS6AwRCLoGeYA5HEp_B7zvOwFGlGwny0l8`, pestaña `Seguimiento`) vía el mismo `gc` que ya
usa para h2test/SinCompletar — ya no depende de ningún archivo local. `GRUPO_LABEL["BAQ2"]` se
deja como fallback inofensivo por si el typo reaparece a mano, pero no debería.

**Efecto secundario real de la migración (no un bug):** al leer el Sheet vivo, `SIN UBICACIÓN`
subió de 1 a 38 filas (student×curso, 13 estudiantes únicos) — verificado uno por uno: estos
estudiantes SÍ existen en h2test (Q10, con curso incompleto) pero **no tienen fila en absoluto**
en la pestaña `Seguimiento` en vivo (ni por cédula ni por email), aunque sí estaban en el xlsx
local viejo. No es un problema de formato de datos (los IDs en el Sheet vivo son strings de
dígitos limpios, sin notación científica ni comas) — son estudiantes que genuinemente cayeron
del tracking de monitorías: nadie les asignó ciudad/monitor en la fuente que el equipo mantiene
hoy.

**Resuelto — fallback a pestañas por ciudad (2026-07-21, mismo día):** el mismo Sheet gigante de
BD Seguimiento tiene 9 pestañas más, una por ciudad (`Barranquilla`, `Bogotá`, `Cali`,
`Cartagena`, `Medellín`, `Panamá`, `Guayaquil`, `Quito`, `Uruguay`) que los monitores llenan
directamente — resultaron tener MÁS cobertura que la pestaña central `Seguimiento` (759 cédulas
en Seguimiento vs. 832 adicionales solo en las pestañas por ciudad). Los 13 estudiantes sin
ubicación estaban los 13, cada uno en la pestaña de su propia ciudad. `leer_ubicaciones(gc)`
ahora hace una segunda pasada: para cada pestaña de `TABS_CIUDAD`, completa SOLO las cédulas que
`Seguimiento` no tenía (nunca sobreescribe el hub). **Gotcha de formato:** el layout de headers
NO es consistente entre pestañas — algunas tienen la fila de encabezados en la fila 0, otras en
la fila 1 (por una celda "Información General" fusionada arriba); `_leer_tab_ciudad()` prueba
ambas filas y usa la que tenga una columna `id` exacta. Resultado: `sin_ubicacion` bajó de 38 a
**0**.

**BAQ2 purgado de Historico:** además de la migración, se borró (a pedido explícito, no
reetiquetado) la única fila con `ciudad="BAQ2"` que había quedado grabada en `Historico` para la
semana 2026-W29 (del backfill hecho antes de este fix) — pertenecía a Jeyder Jesús Pallares De
La Hoz, que de aquí en adelante siempre resuelve a `BAQ` correctamente. `GRUPO_LABEL["BAQ2"]` se
eliminó del código (ya no hace falta ni como fallback).

**Histórico + Semáforo semanal (2026-07-21):** cada corrida ahora escribe dos pestañas más en el
mismo Sheet `SinCompletar`:

- **`Historico`** — snapshot plano (`Semana | Rango | Ciudad | Curso | Cedula | Nombre | Avance`)
  de la cohorte sin completar de esa corrida. Marca de agua por semana ISO (`AAAA-Www`, función
  `semana_actual()`): cada corrida sobrescribe SOLO las filas de la semana en curso — las semanas
  ya cerradas quedan congeladas. Guarda únicamente incompletos (no el roster completo), así no
  crece con estudiantes que ya llegaron a 100%.
- **`Semaforo`** — contraste semana pasada vs. actual, por ciudad → curso → estudiante. Cohorte =
  quienes estaban SIN COMPLETAR en el histórico de la semana anterior (`semana_mas_reciente_antes()`).
  Para cada uno se busca su avance de HOY en la lectura en vivo de h2test **sin filtrar** (variable
  interna `por_curso_todos`/`ciudades_todos`, no se persiste) — así detecta tanto progreso parcial
  como quienes ya llegaron a 100% (que por eso desaparecieron de `SinCompletar`). Semáforo por caso:
  verde =100% · amarillo 45–99.9% · rojo <45% (función `_semaforo_color()`). Columna Tendencia:
  verde si el avance de hoy es ≥ el de la semana pasada, con el Δ%. Si un cédula de la semana
  anterior no aparece hoy en ningún curso JC, se cuenta como "sin dato" (posible retiro) y se
  excluye de los conteos. Primera corrida de la vida del Sheet (sin semana previa en `Historico`):
  pestaña placeholder indicando que es la línea base — el contraste real aparece la semana ISO
  siguiente.

**Gotcha (histórico y semáforo):** el emparejamiento semana-a-semana es por `(curso, cédula
normalizada)` — si el nombre de un curso cambia en h2test (o se funden/separan periodos) entre
una semana y la siguiente, esos estudiantes caen en "sin dato" en vez de contar el progreso real.
Mismo riesgo que ya existe en `aprobacion_ledger.json` con los cursos fusionados de Desarrollo Web.

**Backfill de la semana base (2026-07-21, uso único):** al no existir todavía una semana anterior
en `Historico` la primera vez que se corrió esta lógica, se sembró una comparación real (no
sintética) recuperando la revisión de Google Drive de `SinCompletar` más cercana al cierre de la
semana 13-17 julio (revisión `108`, generada 2026-07-16 20:54, vía Drive API `files.revisions` con
las mismas credenciales del Service Account — no requiere MCP). Se descargó como xlsx
(`exportLinks` de la revisión) y se parseó con un script puntual (`backfill_semana_pasada.py`,
scratchpad de la sesión, no forma parte del repo) que reconstruye los registros desde el mismo
layout de bloques que escribe `construir_grid()`. Con esos 768 registros sembrados como semana
`2026-W29` en `Historico`, la corrida normal del script generó un semáforo real:
🟢222 completaron · 🟡402 en progreso (45-99%) · 🔴144 en riesgo (<45%), 0 sin dato. Desde la
siguiente semana ISO el ciclo sigue 100% automático con datos en vivo — este backfill fue
puntual, no un mecanismo permanente (Drive no garantiza retener revisiones específicas de cada
semana a futuro).

**Panel Balance (2026-07-21):** el semáforo por estudiante resultó poco accionable a nivel de
resumen ("66/66 mejoraron o se mantuvieron" no dice nada útil de un vistazo — muchos son
estudiantes estancados en 0% que cuentan como "se mantuvo"). Se agregó una pestaña más simple,
**`Balance`**, pensada para que cada monitor de ciudad lea el estado en segundos: tabla
ciudad × materia (filas = ciudad, columnas = curso con doble sub-columna semana pasada/actual,
fila `Total` al final), sin ningún dato por estudiante. Métrica = conteo de estudiantes sin
completar (no promedio ni %). Celda de la semana actual coloreada: verde si bajó o llegó a 0,
amarillo si se mantuvo igual, rojo si subió (`_color_balance()`). Fuente: agregación de
`Historico` (`calcular_balance()`), no de `por_curso` directo, para que use la misma semana ISO
congelada que ya usa el semáforo.

**Nota de validación:** el Sheet ya tenía una pestaña manual **`Balace`** (con ese nombre, sin
"n") que el equipo llenaba a mano con la misma idea (ciudad × materia × semana). Al comparar,
los valores de la **semana actual coinciden exactamente** para las 4 materias que el equipo
trackea a mano (Habilidades esenciales, Emprendimiento, Introducción IA, Introducción Lógica) —
confirma que `Balance` mide lo mismo que ya validaba el equipo, ahora automático. Los valores de
"semana pasada" difieren levemente porque el backfill de `Historico` viene de un snapshot del
jueves 16 en la noche (la revisión de Drive más cercana disponible), no del lunes exacto en que
el equipo tomaba su dato manual — diferencia de timing, no de métrica. La pestaña `Balace`
original NO se tocó ni se reemplazó; sigue existiendo en paralelo hasta que el equipo decida
migrar a `Balance`.

**Balance v2 (2026-07-21, mismo día):** tres mejoras sobre la primera versión, pedidas tras ver
el resultado inicial:

1. **Tercera columna `% avance` por materia** (`calcular_balance()` ahora recibe
   `totales_matriculados` — construido en `main()` desde `ciudades_todos`, la lectura SIN
   filtrar de avance). `% avance = (matriculados − sin_completar_actual) / matriculados × 100`
   — % de esa ciudad×curso que ya completó. Coloreada con **colores fuertes** (no pastel):
   `GREEN_STR #34A853` / `YELLOW_STR #F9AB00` / `RED_STR #EA4335`, mismos umbrales que el
   semáforo por estudiante (100 / 45-99.9 / <45) vía `_semaforo_color()` reutilizado
   (`_color_pct_fuerte()`). Los conteos semana-pasada/actual mantienen el coloreado pastel de
   tendencia ya existente (`_color_balance()`) — dos escalas de color con propósitos distintos
   en la misma tabla, a propósito.
2. **Más espacio visual:** filas de datos a 30px (antes ~21 default), columnas de materia a
   100px, columna Ciudad a 150px, borde derecho sólido entre cada bloque de materia
   (`borde_derecho()`) para separar visualmente sin gastar columnas de por medio.
3. **Tabla resumen por ciudad al final** (`construir_resumen_ciudades()`): ciudad × cantidad
   total sin completar (todas las materias sumadas) por semana + columna Tendencia, más fila
   `Total general`. Va 2 filas debajo de la tabla principal, en la misma pestaña `Balance`
   (mismo `ws.update()`, rango calculado con `fila_resumen0 = len(grid) + 2`).

**% avance = promedio de Supabase, no % de completación de Sheets (2026-07-21, mismo día):**
cambio de métrica pedido explícitamente — antes era `(matriculados − sin_completar) / matriculados`
calculado desde `ciudades_todos` (Sheets); ahora es el **promedio del `porcentaje_avance`
individual** de todos los matriculados de esa ciudad×curso, consultado directo a Supabase
(`panel-datos-rofe`, tablas `enrollments` × `participants!inner(grupo_ciudad)` ×
`courses!inner(nombre,cohorte)`, filtrado a `cohorte=<año actual>`). Nueva función
`calcular_promedio_avance_supabase()` — solo lectura, credenciales `SUPABASE_URL` /
`SUPABASE_SERVICE_ROLE_KEY` de `.env.local` (mismo patrón que `scripts/panel-datos/*.py`, nunca
antes usado en `tools/`). Cruce por `(grupo_ciudad, _norm_curso(curso))` — el nombre de curso en
Supabase coincide con el de h2test tras normalizar (mayúsculas, sin `\xa0`). Si faltan
credenciales o falla la consulta, degrada a `{}` (columna en blanco `—`) sin bloquear el resto
del reporte. **Por qué los valores salen tan altos (98-100% en casi todo menos HTML):** el
promedio incluye a TODOS los matriculados, no solo a los que faltan — un curso con 750 de 780 ya
al 100% arrastra el promedio arriba aunque los 30 restantes vayan mal; HTML se ve más bajo
(60-76%) porque es el curso con más gente aún cursando. Verificado contra Supabase directo antes
de implementar (BAQ×HTML: n=131, promedio=73.5%, coincide con el valor final en Balance).
**Nota de frescura:** el resto del pipeline (SinCompletar/Historico/Semaforo/conteos de Balance)
sigue siendo Sheets en vivo, actualizado cada 4h: la columna `% avance` es la única que depende
del sync diario `q10-sync-supabase` (9:45 COT) — puede ir hasta ~14h más atrasada que el resto
del reporte en el peor caso.

**Celdas más grandes (2026-07-21, mismo día):** filas de datos 30px→36px, columna Ciudad
150px→190px, columnas de cada materia 100px→130px, `fontSize=11` en la celda de `% avance`
(antes heredaba el tamaño por defecto). Borde derecho sólido entre bloques de materia se
mantiene igual.

**Gotcha (merges + columnas congeladas):** `updateSheetProperties.frozenColumnCount` aplica a
**toda la pestaña**, no solo al bloque de arriba — cualquier `mergeCells` que cruce la columna 0
(congelada) con columnas no congeladas falla con "You can't merge frozen and non-frozen columns"
(o, si el merge cubre TODO el ancho incluyendo la fila título, "can't freeze columns which
contain only part of a merged cell" — mismo choque, dos mensajes de error distintos según el
caso). Aplica igual a la tabla de resumen aunque esté en otra sección de la misma hoja. Fix en
ambos casos: no merguear la fila de título — dejar el texto en la primera celda sin combinar
(Sheets lo desborda igual sobre las celdas vacías de la derecha).

**Verificado, sin cambio de código: la comparación semanal ya se adapta al día de la semana.**
Se pidió confirmar que Balance/Semaforo comparen martes-viernes contra "el viernes anterior", y
que el lunes siguiente contraste contra el viernes que acaba de pasar. Simulando `semana_actual()`
con fechas de lunes a domingo (`datetime(2026,7,20..27)`): lunes a domingo de una misma semana
calendario devuelven el MISMO `semana_iso` (ISO week, Python `isocalendar()`), y el lunes
siguiente salta a la semana ISO+1. Como `escribir_historico()` solo sobreescribe las filas de la
semana EN CURSO (las semanas cerradas quedan congeladas — ver sección Histórico), el resultado ya
es exactamente el pedido: cualquier día martes-domingo compara contra la última semana cerrada
(que, al no haber avance sábado/domingo, numéricamente equivale al viernes), y el lunes siguiente
mueve el ancla a la semana que acaba de cerrar. No se tocó `semana_actual()` ni
`semana_mas_reciente_antes()` — ya estaban correctos.

**Verificado, sin cambio necesario: el workflow n8n no requería re-exportar.** Se comparó el
workflow en vivo (`GET /api/v1/workflows/Rblg81qifVshsRae`) contra `n8n-workflows/q10-consolidacion.json`
— 32 nodos, conexiones y metadata **byte-idénticos**. Todos los cambios de esta sesión (Historico,
Semaforo, Balance) viven enteramente dentro de `exportar_sin_completar.py`, que el workflow ya
invocaba sin cambios estructurales — no hizo falta tocar ningún nodo.

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

## `scripts/panel-datos/normalize_q10_data.py`

**Propósito:** Fase 1a del panel de datos Supabase ([[panel-datos-etl]]). Lee h2test (bloques
por curso, patrón `detectar_grupos` de export_stats) + pestaña Retirados → excluye desertores
(Tipo=Desertor) y perfiles de prueba (`tools/exclusiones_prueba.json`) → normaliza (cédula solo
dígitos, email lower+regex, avance clamp 0-100) → valida → payload para Supabase.

**Servicios:** Google Sheets API (read only — credenciales de `scripts/q10-consolidacion/`)

**Comando:**
```bash
python scripts/panel-datos/normalize_q10_data.py                 # corrida completa
python scripts/panel-datos/normalize_q10_data.py --max-filas 100 # muestra de prueba
```

**Salidas (PII → tools/, gitignoreado):** `tools/supabase_payload.json` (participants/courses/
enrollments, determinista/idempotente) · `tools/normalize_report_YYYYMMDD.json` (errores y
advertencias con detalle).

**Reglas canónicas:** aprobado/completado = avance > 80 (`UMBRAL_APROBADO`); estado matrícula:
`completado` (>80) / `en_progreso` (>0) / `inscrito` (0). Duplicado (cédula, curso) → keepMax.

**Gotcha crítico (2026-07-10):** el payload de participants lleva SOLO `q10_id/nombre/email` —
NUNCA agregar claves sociodemográficas con `null`: el upsert merge-duplicates del loader las
escribe tal cual y **borra cada mañana** lo que cargaron los syncs de BD monitorias (JC) y
BD-Mujeres ROFÉ (MR). Así se perdió edad+ciudad de JC el 10-07 (restaurado re-corriendo el sync).

**Output parseable para n8n:**
```
RESUMEN: participantes=N cursos=K matriculas=M errores=E advertencias=W estado=exito
```

---

## `scripts/panel-datos/cargar_supabase.py`

**Propósito:** Carga `tools/supabase_payload.json` a Supabase `panel-datos-rofe`: snapshot previo
→ `participants_snapshots` (Decisión 2), luego upsert participants (`q10_id`) → courses
(`nombre,cohorte`) → enrollments (FKs resueltas, `participant_id,course_id`). Idempotente.

**Servicios:** Supabase REST (service_role de `.env.local` raíz — bypasea RLS, solo backend)

**Comando:**
```bash
python scripts/panel-datos/cargar_supabase.py [--dry-run]
```

**Gotcha:** Supabase rechaza secret keys con User-Agent de navegador → UA propio
`panel-datos-etl/1.0`. PostgREST pagina a ~1000 filas → `get_todo()` pagina con limit/offset.

**Output parseable para n8n:**
```
RESUMEN: participants=N courses=K enrollments=M snapshot=S estado=exito
```

---

## `scripts/panel-datos/sync_sociodemograficos.py`

**Propósito:** BD Seguimiento de Monitorias (Sheet vivo, id `1ggzoJeZR3fS6AwRCLoGeYA5HEp_B7zvOwFGlGwny0l8`,
2026-07-21: dejó de leer el xlsx exportado a mano) → Supabase participants.
Extrae de `Seguimiento` (ID c7, Grupo c2, Fecha Nacimiento c11, Edad c12, Ciudad c13, Género c16)
y `Diagnostico` (doc c3, situación emprendimiento c32 → enum 4 categorías). Cruce por cédula;
actualiza SOLO participantes existentes (sin match → reporte, no se crean). Recomputa agregados.
**Automatizado:** workflow n8n `sociodemograficos-semanal` (lunes 6:00 COT, Telegram en error).

**Comando:** `python scripts/panel-datos/sync_sociodemograficos.py [--dry-run]`

**Gotchas:** (1) openpyxl entrega cédulas como float — `str(1041774123.0)` mete un CERO extra al
normalizar; convertir a int primero. (2) PGRST102: el bulk upsert de PostgREST exige claves
idénticas por batch → agrupar filas por conjunto de claves. (3) NOT NULL se valida ANTES del
ON CONFLICT → upsert parcial necesita eco del `nombre` actual. (4) `Link Emprendimiento` de la BD
es el Zoom de la clase, no un emprendimiento del estudiante. (5) **`en_seguimiento_jc` (agregado
2026-07-23) debe escoparse a la cohorte del año en curso** — sin ese filtro, marca como "alerta
de retiro" a miles de egresados históricos (2023-2025) que nunca estuvieron en ese Sheet.

**`en_seguimiento_jc` (2026-07-23):** alerta operativa de retiro pendiente de confirmar en Q10
— el equipo borra primero del Sheet, Q10 tarda meses en reflejarlo. `false` = no aparece en
Seguimiento pero Q10 sigue activo; **no usar como variable de análisis hasta que se confirme**
(ver [[supabase-estructura]]). Solo JC, cohorte actual (decisión: MR queda fuera, gestión no
confiable ahí). Se calcula en un segundo paso para TODA la cohorte, no solo quien trae el Sheet
(la ausencia es la señal). Migración: `docs/migrations/009_en_seguimiento_jc.sql`.

**Output parseable:** `RESUMEN: actualizados=N sin_match_supabase=X sin_datos=Y alertas_retiro_pendiente=Z estado=exito`

---

## `scripts/panel-datos/sync_sociodemograficos_mr.py`

**Propósito:** BD-Mujeres ROFÉ (Sheet vivo, id `1ZsC4WyY26aOCEMrnZ_l8Tn-l69DB_0ADs5lnecaoEP8`,
2026-07-21: dejó de leer el xlsx exportado a mano) → Supabase participants, SOLO
matriculadas en cursos `programa=mr`. Espejo del sync JC. Lee `General` (cédula c7, Edad c12,
Ciudad c13, Nivel estudios c17, Emprendimiento c19, Estrato c20, Estado civil c21, Vivienda c24)
e `Inactivas` como fuente secundaria (columnas distintas: cédula c5, civil c9, edad c11,
emprendimiento c12, vivienda c15, nivel c16, estrato c17, ciudad c24; General gana). Primera
fuente real de `tipo_vivienda`/`estrato`/`estado_civil`/`nivel_estudio` (JC sigue sin fuente).
`genero='Femenino'` constante. Mapeos por substring a los enums existentes (bachiller→secundaria,
técnica/tecnóloga→técnico, especialización→postgrado; soltera/sola→soltero, separada→divorciado,
viuda/madre cabeza→otro). Recomputa agregados. Alimenta la vista pública `v_mr_demografia`
(6 dimensiones agregadas, GRANT anon).

**Comando:** `python scripts/panel-datos/sync_sociodemograficos_mr.py [--dry-run]`
**Output parseable:** `RESUMEN: actualizados=N sin_match_supabase=X sin_datos=Y estado=exito`

**Gotchas:** (1) hereda los del sync JC (float→cero extra, PGRST102, eco de `nombre`).
(2) El filtro MR usa embed PostgREST `enrollments!inner(courses!inner(programa))` — sin el
`!inner` el filtro no excluye. (3) `HerpowerED` NO se lee (copia de General). (4) La dimensión
`emprendimiento` de `v_mr_demografia` solo cuenta filas con datos de la BD — el default
`tiene_emprendimiento=false` de las históricas sin match inflaría "sin_emprendimiento".
(5) Corrida 2026-07-10: 531 actualizadas (280/282 de la cohorte 2026 = 99.3%; las 739 MR
históricas restantes ya no figuran en la BD 2026 — cobertura 2025: 26.9%).

---

## `scripts/panel-datos/sync_postulantes_mr.py`

**Propósito:** universo COMPLETO de postulantes/candidatas Mujeres ROFÉ (no solo matriculadas)
→ Supabase `postulantes_mr`, tabla paralela a `participants` (ver [[postulantes-mr-supabase]]).
Reutiliza conexión/credenciales de `sync_sociodemograficos_mr.py` (mismo Sheet, mismo Service
Account). Lee 5 pestañas: `General`+`Inactivas` (fuente primaria, mismos índices de columna
que el sync de sociodemográficos) + `Cursos`/`Cursos%`/`Plataforma MR` (exports legados que
aportan 193 cédulas exclusivas — confirmado en auditoría Fase 0, 2026-07-22, no es basura).
Precedencia: General > Inactivas > Plataforma MR > Cursos > Cursos% (primera fuente gana).
Enlaza `participant_id` cuando la cédula matchea un `q10_id` existente; si no, NULL (no crea
`participants`, ver [[convenciones#Supabase `participants` = solo matriculados en Q10]]).

**Comando:** `python scripts/panel-datos/sync_postulantes_mr.py [--dry-run]`
**Output parseable:** `RESUMEN: universo=N cargados=X con_match_participant=Y typos_detectados=Z estado=exito`

**Detección de typos de cédula:** `detectar_typos()` NO es fuerza bruta O(n²) — usa bloqueo
(mismo correo/celular exacto, mismo conjunto de tokens de nombre, vecindad numérica de cédula
ordenada ventana=8) para generar pares candidatos baratos, y solo ahí aplica el criterio
completo de ≥2 señales (ver [[convenciones#Detección de typos de cédula por señales cruzadas]]).
Reporta a `tools/postulantes_mr_report_<fecha>.json` (PII), nunca corrige sola.

**Gotchas:** (1) **`get_todo()` sin `offset += page` es un loop infinito silencioso** — cada
iteración vuelve a pedir offset=0, la API responde rápido (aparenta funcionar) pero nunca
termina; RSS crece sin límite (se vio pasar de cientos de MB a 2 GB) porque `filas.extend()`
seguía acumulando duplicados para siempre. Se manifestó como un "hang de red intermitente" y
costó ~30 min de diagnóstico (se llegó a sospechar el proxy corporativo MITM) antes de
encontrarse con logging por iteración — **si un script con este patrón de paginación se
"cuelga" sin excepción ni traceback, revisar primero que el incremento de `offset` exista**,
antes de asumir que es la red. (2) La primera versión de `detectar_typos()` usaba
`items[i+1:]` dentro de un for — genera una slice nueva de tamaño O(n) en cada iteración
externa, O(n²) en memoria transitoria además de tiempo; con ~5.300 filas eso también se
manifestó como cuasi-cuelgue con RSS de 2 GB. Fix: bloqueo (arriba), nunca slice dentro de
un loop sobre una lista grande. (3) `Cursos%` tiene triple header (cohorte/curso/columna) y
columnas de cédula repetidas por bloque — el offset real de "Número de cédula" está en fila 3
(índice 2), no en fila 2 como en las demás pestañas. (4) `Plataforma MR` tiene un único header
(no doble) — asumir doble header ahí detecta mal la columna de cédula (falso positivo con
"documentType"/"Tipo de documento" al buscar por substring "documento").

**Cuadre verificado 2026-07-22:** 5.351 filas cargadas (general=5.125, inactivas=33,
plataforma_mr=55, cursos=1, cursos_pct=137 — tras deduplicar por precedencia), 557 con
`participant_id`, 52 posibles typos detectados (incluye el caso real Gina Gleisy
22519536/22519636 que motivó todo el proceso). Anon key verificado: 401 (0 filas).

---

## `scripts/panel-datos/sync_aprobacion_supabase.py`

**Propósito:** `docs/aprobacion/data.json` (agregados canónicos de export_aprobacion, ya públicos,
sin PII) → Supabase: `cohorte_ingresos` (cohorte × programa: ingresados/activos/retirados — JC
2026 = 832 = 777 + 57) y `aprobacion_cursos` (cohorte × curso: cursaron, aprobados,
aprobados_retirados, retirados, bandas de avance). Es lo que le da al panel el "total de
ingresados" y el avance sobre la cohorte COMPLETA (no solo activos). Cohorte = campo `anio` del
JSON → escalable por año sin tocar código. Idempotente (upsert por clave).

**Comando:** `python scripts/panel-datos/sync_aprobacion_supabase.py [--dry-run]`
**Output parseable:** `RESUMEN: cursos=N programas=P cohorte=YYYY estado=exito`

**Gotchas:** corre DESPUÉS de `export_aprobacion.py` (consume su JSON); mapa de programa por
etiqueta (`Jóvenes creaTIvos`→jc, `Mujeres ROFÉ`→mr) — un programa nuevo requiere ampliar
`MAPA_PROGRAMA` y el enum. Pendiente encadenarlo al workflow n8n.

---

## `scripts/panel-datos/sync_emoflow.py`

**⚠ DEPRECADO (2026-07-21):** el workflow n8n `q10-sync-supabase` seguía llamando a este
script en producción pese a estar documentado como reemplazado desde el 2026-07-20 —
corregido: el nodo ahora ejecuta `sync_emoflow_api.py` (API directa de Emoflow, sin Sheet
intermedio). Este script se conserva por si hace falta volver atrás, pero no correr más.

**Propósito:** Pestaña `+Ingresos-EmoFlow` del Sheet manual → Supabase `emoflow_ingresos`.
Emoflow es la herramienta de estado de ánimo; hoy se usa como proxy de **"calidad de estudiante"**
vía los **ingresos al sistema** (contador acumulado por estudiante). Normaliza correo/fecha, mapea
`Area` → `grupo_ciudad` canónico (BAQ/BOG/…) y hace upsert por `email`. Idempotente.

**Servicios:** Google Sheets API (read only) · Supabase REST (service_role)

**Sheet:** ID `1ggzoJeZR3fS6AwRCLoGeYA5HEp_B7zvOwFGlGwny0l8`, pestaña `+Ingresos-EmoFlow`
(gid `1288133311`). Columnas: `Usuario | Nombre | Area | Ingresos al sistema | Ultimo ingreso`.

**Comando:**
```bash
python scripts/panel-datos/sync_emoflow.py [--dry-run]
```

**⚠ Llave de cruce = EMAIL.** Emoflow **no expone la cédula** — el correo normalizado (lower+trim)
es la única unión posible con `participants`. Los correos sin match se cargan igual con
`participant_id = NULL` (no se pierden y NO se crean participants desde aquí: Q10 sigue siendo la
fuente de verdad de quién existe).

**Corrida inicial (2026-07-14):** 823 filas, 0 avisos · **757 con match (92.0%)** · 66 sin match.
Cubre **757 de los 777 activos de JC 2026 (97.4%)**. Los 66 sin match son correos que Q10 no
conoce (retirados fuera de `participants`, o correos personales distintos al de Q10).

**Output parseable:** `RESUMEN: filas=N con_match=M sin_match=X estado=exito`

**Gotcha:** el reporte con los correos sin match va a `tools/emoflow_report_YYYYMMDD.json` (PII,
gitignoreado). Duplicados de correo en la hoja → keepMax por ingresos (patrón del proyecto).

---

## `scripts/panel-datos/sync_emoflow_api.py`

**Propósito:** Emoflow API directa (sin Sheet intermedio, 2026-07-20) → Supabase
`emoflow_ingresos`. `POST /login` (PHPSESSID) → `GET /admin/registro-ingresos-exportar`
(CSV, log de eventos con timestamp) → agrega por email (suma ingresos, último ingreso) →
upsert idéntico a `sync_emoflow.py` (mismo destino, misma lógica de match por email).

**Servicios:** API Emoflow (`https://emoflow.sanumbe.com`) · Supabase REST (service_role)

**Credenciales:** `EMOFLOW_URL`/`EMOFLOW_USER`/`EMOFLOW_PASSWORD` + `SUPABASE_URL`/
`SUPABASE_SERVICE_ROLE_KEY` en `.env.local`.

**Comando:** `python scripts/panel-datos/sync_emoflow_api.py [--dry-run]`

**Automatización (corregida 2026-07-21):** nodo `Ejecutar sync_emoflow_api` en
`q10-sync-supabase`, tras `¿Aprobación OK?`. Reemplaza a `sync_emoflow.py` — ver nota de
deprecación arriba.

---

## `scripts/panel-datos/reporte_puntaje.py`

**Propósito:** Ranking de estudiantes por **puntaje compuesto** ("calidad de estudiante") sobre la
vista `v_puntaje_estudiante` (JC, cohorte actual). Pondera señales convertidas a **percentil dentro
de la cohorte**: ingresos Emoflow **60%** · avance Q10 **40%** · asistencia Zoom **0%**.

**Regla de negocio (2026-07-14, pedido de Samuel):** **Emoflow es el criterio mayor y es
obligatorio** — sin ingresos registrados el estudiante NO entra al ranking.

**Comando:**
```bash
python scripts/panel-datos/reporte_puntaje.py                 # top 25 + CSV
python scripts/panel-datos/reporte_puntaje.py --ciudad BOG --limite 100 \
       --excel "%USERPROFILE%\Downloads\100 mejores de bogota.xlsx"
python scripts/panel-datos/reporte_puntaje.py --peso-ingresos 0.8 --peso-avance 0.2
python scripts/panel-datos/reporte_puntaje.py --peso-asistencia 0.2   # cuando la asistencia madure
```

**Salidas:** siempre CSV en `tools/puntaje_estudiantes_YYYYMMDD.csv`; con `--excel`, además un
`.xlsx` con formato (títulos, autofiltro, panel congelado) en la ruta indicada.

**⚠ Por qué percentiles y no valores crudos:** `avance_q10` promedia 92.8 con sd 6.7 — casi no
discrimina. Con peso nominal 50% aportaba **menos** al ranking (0.50×6.7=3.4) que la asistencia con
30% (0.30×22.8=6.8): los pesos no significaban lo que decían. Y al renormalizar sobre crudos, a
quien le faltaba asistencia el avance (~93) le apuntalaba el puntaje → los de 2 señales promediaban
**más** (80.2) que los de 3 (78.8): **faltar dato premiaba**. Con percentiles las 3 señales quedan
uniformes en [0,100] y ambos sesgos desaparecen.

**⚠ La asistencia aún NO es señal madura (2026-07-14):** cubre 408/777, viene de **un solo curso**
(`Desarrollo Web - GIT, HTML y CSS`) y lleva ~11 días de captura → **1.4 sesiones por persona**
(solo 4 con ≥3). Por eso el ranking por defecto es `puntaje_sin_asistencia` (avance 60% + ingresos
40%), comparable entre los 777. Revisar cuando la captura Zoom acumule sesiones y cubra más cursos.

**⚠ PRIVACIDAD:** salida con nombre/correo → `tools/puntaje_estudiantes_YYYYMMDD.csv` (gitignoreado).
La vista `v_puntaje_estudiante` **no tiene GRANT a anon** (a diferencia de las `v_emoflow_*`).

**Gotcha:** `asistencia_zoom` tiene basura de staff/test ("Mi reunión", "Reunión con Katze",
"Prueba - Asistencia", "Entrevista NOVA") — ~10 registros a limpiar.

---

## `scripts/panel-datos/importar_historico_q10.py`

**Propósito:** Cohortes pasadas (2023-2025) de Q10 → Supabase. Login Q10 (reusa `q10_to_sheets`),
descarga Consolidado de los periodos históricos con mapa EXPLÍCITO periodo→(cohorte, programa):
2023=pids 2-7 · 2024=9/10/12/14 ("Único Horario nivel 1-3" sin año, asignados 2024 — confirmar) ·
2025=16 (MR forzado)/17/18/19. Normaliza con las mismas reglas del sync diario; solo inserta
cédulas NUEVAS (no toca a los del sync 2026); desertores y perfiles de prueba excluidos.
Idempotente. Corrida 2026-07-10: +1.816 participantes, 30 cursos·cohorte, 12.377 matrículas, 0 errores.

**Comando:** `python scripts/panel-datos/importar_historico_q10.py [--dry-run] [--solo-pid N]`
**Output parseable:** `RESUMEN: participantes_nuevos=N cursos=K matriculas=M cohortes=C errores=E estado=exito`

**Gotchas:** Q10 reutiliza nombres de curso entre años (UNIQUE nombre+cohorte los separa);
el Consolidado NO devuelve inhabilitados → cohortes pasadas sin retirados; `tools/sondear_periodos_q10.py`
es el explorador que dimensionó todo (re-usarlo si aparecen periodos nuevos).

---

## `scripts/panel-datos/test_cuadre_dashboard.py`

**Propósito:** Fase 4 — cuadre por curso entre `v_curso_completion` (Supabase, anon) y
`docs/aprobacion/data.json`: matriculados==activos y completados==aprobados (avance > 80).
Verificado 9/9 exacto el 2026-07-10 con fuentes de la misma frescura. Con corridas separadas,
los cursos activos derivan (avance real de estudiantes) — tolerancia ±2, no es bug.
`python scripts/panel-datos/test_cuadre_dashboard.py` — exit 1 si hay descuadres.

---

## `scripts/panel-datos/test_conexion_supabase.py`

**Propósito:** Smoke test de la cara pública: con el anon key verifica lectura de agregados,
que RLS oculte participants privados y que la escritura anónima esté bloqueada.
`python scripts/panel-datos/test_conexion_supabase.py` — stdlib + truststore, lee `.env.local`.

---

## `scripts/panel-datos/sync_asistencia_supabase.py`

**Propósito:** Sincroniza `ZOOM-ASISTANCE` (Sheet) → Supabase `asistencia_zoom`. Deduplica por
(email, curso, fecha), upsert por lotes de 100 vía `Prefer: resolution=upsert`. **Es el script
vigente** — ver [[asistencia-zoom-flujo]].

**Comando:** `python scripts/panel-datos/sync_asistencia_supabase.py [--dry-run]`

**Credenciales:** `.env.local` raíz (`SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY`, patrón
`cargar_env_local()`) + `credenciales_service_account.json` (Sheets).

**Scripts obsoletos (2026-07-14):** `sync_asistencia_upsert.py`, `sync_asistencia_directo.py`,
`sync_asistencia_simple.py` — versiones anteriores/experimentales del mismo sync, movidas a
`scripts/panel-datos/_obsoletos/` (no usar; se conservan solo de referencia histórica).

**Scripts obsoletos (2026-07-21):** `sync_emoflow_participacion.py` — eliminado del workflow
`q10-sync-supabase` (el panel ya no consume `emoflow_participacion_semanal`, ver
[[panel-datos-etl#Fuentes de datos aún no centralizadas]]), movido a
`scripts/panel-datos/_obsoletos/`.

---

## `scripts/panel-datos/calcular_asistencia_promedio.py`

**Propósito:** Lee `ZOOM-ASISTANCE` → calcula promedio de asistencia por estudiante y por curso →
upsert en Supabase `asistencia_promedio`. Corre después de `sync_asistencia_supabase.py`. Ver
[[asistencia-zoom-flujo]].

**Comando:** `python scripts/panel-datos/calcular_asistencia_promedio.py`

---

## `scripts/panel-datos/export_supabase_json.py`

**Propósito:** Exporta TODAS las tablas/vistas públicas de Supabase a JSON individuales en
`docs/datos/*.json` (uno por tabla, más `manifest.json` con fecha y conteos). Pensado para que el
panel Netlify pudiera consumir JSON pre-generado en vez de Supabase client-side.

**Servicios:** Supabase REST (anon key — solo agregados vía RLS)

**Comando:**
```bash
python scripts/panel-datos/export_supabase_json.py                    # commit + push
python scripts/panel-datos/export_supabase_json.py --sin-push         # pruebas (no toca git)
python scripts/panel-datos/export_supabase_json.py --output-dir DIR   # override de salida
```

**Tablas/vistas exportadas:** `participants`, `courses`, `enrollments`, `v_curso_completion`,
`v_curso_completion_por_ciudad`, `v_demografia_grupo`, `v_mr_demografia`, `cohorte_stats`,
`emoflow_ingresos`, `v_emoflow_resumen`, `v_emoflow_por_ciudad`, `v_emoflow_bandas`,
`v_emoflow_bandas_ciudad`, `historial_emoflow`, `historial_emoflow_ciudad`,
`emoflow_participacion_semanal`, `cohorte_ingresos`, `aprobacion_cursos`,
`v_aprobacion_cohorte_stats`, `asistencia_zoom`, `asistencia_promedio`, `historial_cursos`,
`historial_cursos_ciudad`.

**Output parseable:** `RESUMEN: tablas=N registros=M estado=exito`

**Git commit y push (agregado 2026-07-21):** `git_commit_y_push()` — mismo patrón de
`export_stats.py`: `git add docs/datos` + commit + `push origin main`. Se agregó porque
`docs/datos/*.json` ya estaba trackeado en git antes de encadenar el script — sin el push, cada
corrida diaria dejaría el directorio permanentemente sucio en disco sin llegar nunca al repo.

**⚠️ Sin consumidor confirmado (2026-07-21):** el frontend real de producción
(`venerable-truffle-331f3c.netlify.app`) consulta Supabase directo desde el cliente (`lib/api.ts`,
anon key) — NO lee estos JSON. El script está encadenado en `q10-sync-supabase` (pedido expreso
de Samuel) pese a esto; ver [[panel-datos-etl#`sync_supabase_to_sheets.py` / `export_supabase_json.py` — continuidad analizada, ENCADENADOS (2026-07-21)]]
para la decisión completa y motivo de mantenerlo así.

**Automatización (2026-07-21):** último tramo de `q10-sync-supabase` (`uSizw3dNzpb6n53H`) —
`¿Emoflow OK?` (rama true) → `Ejecutar export_supabase_json` → `Export JSON OK?` →
`Ejecutar sync_supabase_to_sheets` → `Sheets OK?` → `OK` (con `stopAndError` en cada rama de error).

---

## `scripts/panel-datos/sync_supabase_to_sheets.py`

**Propósito:** Espeja vistas públicas de Supabase de vuelta a Google Sheets (`H1Test` =
participantes, `H2Test` = Emoflow/ingresos, `H3Test` = resumen ejecutivo/KPIs) para que el equipo
consulte los datos sin salir de Excel. Es de **lectura** (Supabase → Sheets); las escrituras
manuales en Sheets se cargan a Supabase por el flujo manual existente, no por este script.

**Servicios:** Supabase REST (anon key) · Google Sheets API (write, Service Account)

**Sheet destino:** ID `1ggzoJeZR3fS6AwRCLoGeYA5HEp_B7zvOwFGlGwny0l8` (mismo Sheet gigante de
Avance/Emoflow) — requiere que existan las pestañas `H1Test`/`H2Test`/`H3Test` de antemano (el
script aborta con advertencia si faltan; no las crea).

**Comando:**
```bash
python scripts/panel-datos/sync_supabase_to_sheets.py                  # Sheet ID por defecto
python scripts/panel-datos/sync_supabase_to_sheets.py --sheet-id ID    # override
```

**Output parseable:** `RESUMEN: estado=exito` (o `estado=error`)

**No toca git** — solo lee Supabase y escribe en Sheets.

**Automatización (2026-07-21):** encadenado en `q10-sync-supabase`, entre `Export JSON OK?` y
`Sheets OK?` (ver detalle en la entrada de `export_supabase_json.py` arriba).

**Credenciales:** `.env.local` raíz (mismo patrón `cargar_env_local()`).

---

## `scripts/panel-datos/extraer_mongo_mr_historico.py` + `cargar_mongo_mr_historico.py`

**Propósito:** Investigación de una sola vez (2026-07-22, cerrada — ver
[[panel-datos-etl#Exploración de MongoDB]]) de un MongoDB Atlas (`mujeres-rofe-db.Users`, backend
histórico de la app Mujeres ROFÉ) como posible fuente para llenar el hueco MR 2023/2024 en
Supabase. Resultado: 99.9% redundante con `postulantes_mr` (ya cubierto por la pestaña
"Plataforma MR" del Sheet BD-Mujeres ROFÉ). Solo 4 registros genuinamente nuevos, exportados a
Excel y NO cargados — no queda como pipeline activo, se documentan como referencia por si se
necesita repetir el acceso.

**Servicios:** MongoDB Atlas (usuario Atlas rol "Read Only", solo lectura, nunca escribe) ·
Supabase REST (`service_role`, solo `postulantes_mr`/`participants`)

**Por qué son DOS scripts separados (no uno):** `pymongo` (extracción) y `urllib`/`truststore`
(carga a Supabase) en el mismo proceso producen un cuelgue que se ve exactamente como un problema
de red (investigado ~20 min antes de encontrar la causa real — ver Gotcha abajo). Separar en dos
procesos lo evita, y de paso deja `tools/mongo_mr_historico_payload.json` (PII, gitignoreado) como
artefacto revisable antes de decidir qué cargar — útil cuando una cohorte necesita revisión humana
antes de tocar producción (ver 2023, pendiente con el superior de Samuel).

**Comando:**
```bash
python scripts/panel-datos/extraer_mongo_mr_historico.py                    # Mongo → payload local
python scripts/panel-datos/cargar_mongo_mr_historico.py --dry-run           # solo reporte
python scripts/panel-datos/cargar_mongo_mr_historico.py --cohortes 2024     # carga solo 2024
```

**Precedencia de carga:** nunca pisa una cédula que ya exista en `postulantes_mr` (las fuentes
Sheet ya tienen precedencia establecida) — solo inserta cédulas genuinamente nuevas.

**Gotcha (root cause real, no lo que parecía):** al escribir `Supa.get_todo()` desde cero en vez
de copiar el ya existente, se reintrodujo el bug de `offset += page` faltante — mismo bug ya
documentado el mismo día en
[[convenciones#Paginación PostgREST: un `offset` que no avanza es un loop infinito silencioso]]
al construir `postulantes_mr`. **Nunca reescribir `Supa`/`get_todo` de memoria — copiar el de
`sync_postulantes_mr.py`.**

**Scripts de un solo uso relacionados (investigación, no producción):** `test_conexion_mongo.py`
(smoke test de acceso), `perfilar_mongo.py` (conteos/rangos de fecha por colección),
`cruzar_mongo_supabase.py` (primer cruce, contra `participants` — quedó obsoleto en favor de
`cargar_mongo_mr_historico.py --dry-run`, que cruza correctamente contra `postulantes_mr`),
`exportar_nuevas_mongo_mr.py` (entregable puntual: Excel a Downloads con las candidatas nuevas).

---

## `scripts/panel-datos/extraer_mongo_jc_historico.py` + `cargar_mongo_jc_historico.py`

**Propósito:** Investigación análoga a la de MR, pero para `jovenes-creativos.User` +
`Applicant` (Mongo Atlas, backend de la app JC) — 2026-07-22. A diferencia de MR (99.9%
redundante, cerrado sin cargar), aquí el hallazgo fue real y se decidió cargarlo. Ver
[[panel-datos-etl#Auditoría Mongo JC]] para el detalle completo de la investigación.

**Resultado de la auditoría previa a cargar:** de 2.560 cédulas (User: 1.699 + Applicant: 861,
User gana si se repite), 466 sin match en `participants` (programa=jc) ni en el Sheet BD
Seguimiento (universo de 828 auditado el mismo día). Descartados como typos (0 confirmados
tras chequeo de vecindad de cédula + nombre/correo dentro del propio Mongo). Tras excluir 3
cuentas `rol=ADMIN`: 463 reales — 378 `EGRESADO` (casi todas 2023, alumnos de cohortes
antiguas) + 85 `ACTUAL` (postulantes 2026 recientes, `Applicant`).

**Decisión: SÍ se cargó** (a diferencia del hallazgo de MR) → tabla `postulantes_jc`
(migración `005_postulantes_jc.sql`, RLS + revoke anon). Se cargó el universo COMPLETO de
Mongo (2.556 tras excluir 1 perfil de prueba), no solo los exclusivos — `participant_id` NULL
para quien no matriculó (464 exclusivos), poblado para quien sí (2.092), mismo patrón que
`postulantes_mr`. Columna `fuente` (`mongo_user`/`mongo_applicant`) — pedido explícito de
Samuel para dejar trazabilidad de que el origen es Mongo, no un Sheet.

**Servicios:** MongoDB Atlas (usuario Atlas rol "Read Only", solo lectura) · Supabase REST
(`service_role`, `postulantes_jc`/`participants`)

**Identidad en Mongo:** anidada en `profile` (no en el nivel raíz del doc, a diferencia de
`mujeres-rofe-db.Users`) — `profile.documentNumber`, `profile.completeName`,
`profile.email`, `profile.phoneNumber`, `profile.rol` (`EGRESADO`/`ACTUAL`/`ADMIN`),
`profile.city.name`, `profile.promoYear`.

**Comando:**
```bash
python scripts/panel-datos/extraer_mongo_jc_historico.py       # Mongo → payload local
python scripts/panel-datos/cargar_mongo_jc_historico.py --dry-run   # solo reporte
python scripts/panel-datos/cargar_mongo_jc_historico.py             # carga real (upsert por cédula)
```

Payload en `tools/mongo_jc_historico_payload.json` (PII, gitignoreado). Entregable de revisión
generado ANTES de cargar: `Downloads/jc_mongo_exclusivos.xlsx` (463 casos).

**Gotcha evitado:** se reutilizó `Supa.get_todo()`/`dist_lev()`/`senales_match()` de
`sync_postulantes_mr.py` importándolo como módulo para el análisis exploratorio, en vez de
reescribirlos — evita repetir el bug de paginación ya documentado dos veces el mismo día.

---

## `scripts/panel-datos/test_integridad_supabase.py`

**Propósito:** suite de integridad/seguridad de la base completa (36 tests, un solo comando,
SOLO lectura): FKs/huérfanos, unicidad (emails, cédulas, q10_id), dominios (catálogo de
ciudades, rangos, fechas futuras), cuadres cruzados con **tolerancias explícitas como
constantes** (Δ emoflow 2%, overlap cohorte [0,5], roster+25), frescura de syncs diarios
(≤2 días), y superficie anon (10 objetos PII deben dar 401/vacío — usa `SUPABASE_ANON_KEY`
de `.env.local`). Salida parseable: `RESUMEN: total=N pass=X fail=Y estado=exito|fallo`,
exit code = nº de fails. Ver triage completo en [[supabase-estructura]].

**Comando:** `python scripts/panel-datos/test_integridad_supabase.py [--rapido]`
(`--rapido` omite la descarga completa de enrollments — para el chequeo diario post-sync)

**Gotchas:** (1) el test de cohorte NO exige `ingresados = activos+retirados` — la definición
canónica es cohorte = habilitados **∪** retirados y hay overlap real (2 reingresos en JC 2026);
exigir igualdad daría falso FAIL permanente. (2) El cuadre emoflow persona↔diario tiene Δ0,7%
estructural (scripts descargan el CSV con parámetros distintos) — por eso tol 2%, no 0.

---

## `tools/analisis_emoflow_resultados.py` (PII — gitignoreado)

**Propósito:** análisis estadístico uso Emoflow ↔ resultados académicos (JC 2026, n=777
activos). Solo LECTURA en Supabase. Descriptivos, Spearman/Pearson, chi² por cuartiles de uso
(V de Cramér), y regresión logística propia (IRLS con numpy — statsmodels no disponible en
este entorno; scipy para p-values) ajustada por género/edad/ciudad. Salidas:
`tools/analisis_emoflow_dataset.csv` (PII) y `tools/analisis_emoflow_resultados.json`
(agregados). Resumen publicable y diccionario de datos: [[supabase-estructura]].

**Comando:** `python tools/analisis_emoflow_resultados.py`

**Gotchas:** (1) redondear una fracción ANTES de escalarla a % la satura (0.992→1.0→"100.0%")
— ocultó no-aprobados reales por ciudad hasta que la verificación por SQL independiente lo
atrapó; escalar primero, redondear después. (2) Ciudades con aprobación 100% producen
separación perfecta en la logística (OR absurdo con IC [0,∞] en ese dummy — inofensivo para
los demás coeficientes, pero no reportar ese OR). (3) Reutiliza `Supa` importando
`sync_postulantes_mr` — no reescribir el cliente (gotcha del offset).

---

## Vista `v_persona_360` (Supabase, no es un script)

**Propósito:** trazabilidad total por cédula en una sola consulta — pedido explícito de
Samuel tras el blindaje QA. Une `participants` + `postulantes_mr` + `postulantes_jc` +
`emoflow_ingresos` + `asistencia_promedio` por cédula (email para los 2 últimos). Migración:
`docs/migrations/008_v_persona_360.sql`. Detalle y ejemplo de uso en [[supabase-estructura]].
Cierra la Fase 5 de [[postulantes-mr-supabase]] (búsqueda unificada) como vista SQL en vez de
script Python — misma idea, sin duplicar lógica de cruce.

**Uso:** `GET /rest/v1/v_persona_360?cedula=eq.<cedula>` — **solo `service_role`** (RLS+REVOKE
estricto, verificado 401 a anon). Nunca exponer al frontend público.

---

## Dependencias comunes

```
gspread · google-auth · truststore · requests · pandas · openpyxl · pymongo
```

Ver `scripts/q10-consolidacion/requirements.txt` para versiones exactas.

**SSL corporativo:** todos los scripts llaman `truststore.inject_into_ssl()` al inicio. Ver [[convenciones#SSL corporativo]].
