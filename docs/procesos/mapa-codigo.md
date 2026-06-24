# Mapa de Código

> Índice esquemático de todos los scripts del proyecto. Sin código fuente.
> Actualizar cuando se agregue/modifique un script.
> **Conexiones:** [[q10-consolidacion]] · [[dashboard-web]] · [[zoom-asistencia]]

---

## Ubicaciones raíz

| Carpeta | Contiene |
|---|---|
| `scripts/q10-consolidacion/` | Scripts de extracción Q10 y exportación a Sheets/JSON |
| `scripts/q10-consolidacion/organizador/` | App GUI standalone (.exe) para operadores |
| `tools/` | Herramientas locales con PII — nunca a GitHub |

---

## `q10_to_sheets.py`

**Propósito:** Login multi-paso en Q10 → descarga Estudiantes + Consolidado (4 periodos) → LEFT JOIN por email → sube a Google Sheets.

**Servicios:** Q10 (`site6.q10.com` — endpoints internos AJAX, no API pública) · Google Sheets API

**Credenciales:** `credenciales_service_account.json` · usuario/password Q10 hardcodeados en el script

**Comando:**
```bash
python q10_to_sheets.py --grupo h1test   # → pestaña H1Test (Sheet interno)
python q10_to_sheets.py --grupo h2test   # → pestaña h2test (Sheet público)
```

**Funciones principales:**

| Función | Parámetros | Retorna | Descripción |
|---|---|---|---|
| `login_q10()` | — | `requests.Session` | 7 pasos AJAX encadenados (ver [[convenciones#Q10 Login multi-paso]]) |
| `leer_excel_bytes(contenido)` | `bytes` | `pd.DataFrame` | Parse xlsx, auto-detecta fila header por palabras clave |
| `_q10_post_ajax(session, url, data, referer)` | — | `Response` | Helper AJAX POST con headers corporativos |

**Variables clave en script:**
```
MAPEO_GRUPOS: dict         # --grupo → nombre pestaña Sheets
MAPEO_SHEET_IDS: dict      # --grupo → Sheet ID
PERIODOS = [21, 22, 23, 1] # Periodos Q10 con datos (20 siempre vacío)
TAMANIO_LOTE = 500         # Filas por lote al subir (cuota API)
PAUSA_LOTE = 1.2           # Segundos entre lotes
```

**Gotcha:** Periodo 20 devuelve `not_results` — omitido sin error. URLs Azure Blob expiran en ~3 min, descargar inmediatamente.

---

## `export_stats.py`

**Propósito:** Lee pestaña `h2test` → agrega estadísticas por curso en Python → genera `docs/dashboard/data.json` → git commit + push.

**Servicios:** Google Sheets API (read only)

**Sheet:** `h2test` — ID `1q4VNn4ltqVEMsOjo-c2ZbsbW3VIt-XomPgXeLSN_LTs`

**Comando:**
```bash
python export_stats.py
```

**Funciones principales:**

| Función | Retorna | Descripción |
|---|---|---|
| `detectar_grupos(row0, row1)` | `list[dict]` | Detecta grupos de cursos desde doble encabezado (celdas fusionadas) |
| `procesar_h2test(all_values)` | `(por_curso, anomalias, total_unicos)` | Agrega avance por curso, cuenta SIN MATCH / AVANCE 0% / IRREGULAR |
| `generar_json(por_curso, anomalias, total)` | `dict` | Construye estructura JSON pública |
| `guardar_json(datos)` | — | Escribe `docs/dashboard/data.json` |
| `git_commit_y_push(timestamp)` | — | `git add` + `commit` + `push origin main` |

**Output JSON:** `docs/dashboard/data.json` — estructura `{por_curso[], anomalias[], totales{}}`

**Gotcha:** h2test tiene doble encabezado (fila 1 = nombres de cursos fusionados, fila 2 = sub-headers). `detectar_grupos()` detecta los grupos por la posición del sub-header "Identificacion" en fila 2.

---

## `export_avance.py`

**Propósito:** Lee pestaña `Avance` del Sheet manual → agrega avance por curso → genera `docs/avance/data.json` → git commit + push.

**Servicios:** Google Sheets API (read only)

**Sheet:** `Avance` — ID `1ggzoJeZR3fS6AwRCLoGeYA5HEp_B7zvOwFGlGwny0l8`

**Comando:**
```bash
python export_avance.py
python export_avance.py --segmento "Logica-Nivel 2-2026"
```

**Funciones principales:** (mismo patrón que `export_stats.py`)

| Función | Retorna | Descripción |
|---|---|---|
| `detectar_grupos(row0, row1)` | `list[dict]` | Detecta grupos por sub-header "Número identificación" en fila 2 |
| `procesar_avance(all_values)` | `(por_curso, totales, anomalias)` | Agrega % progreso por curso nombrado; cuenta SIN ETIQUETA |
| `generar_json(...)` | `dict` | Incluye campo `segmento` y `anomalias[]` |
| `git_commit_y_push(timestamp)` | — | Push a `docs/avance/data.json` |

**Output JSON:** `docs/avance/data.json` — estructura `{segmento, por_curso[], totales{}, anomalias[]}`

**Gotcha:** Los primeros 3 grupos de columnas en la hoja Avance no tienen nombre de curso en fila 1 → se cuentan como SIN ETIQUETA. Los 6 cursos nombrados empiezan en col 15.

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

## `setup_headers.py`

**Propósito:** Escribe la fila 1 de headers en H1Test o h2test. **Uso único** (inicialización). Modo diagnóstico por defecto — requiere `--confirmar` para escribir.

**Servicios:** Google Sheets API (write)

**Comando:**
```bash
python setup_headers.py --pestaña h2test              # diagnóstico
python setup_headers.py --pestaña h2test --confirmar  # escribe
```

**Pestañas configuradas:** `H1Test` · `h2test`

**Headers escritos (ambas pestañas):** `Identificacion | Nombre | Celular | Email | Curso | Avance`

---

## `organizador/organizador_Q10.py`

**Propósito:** App GUI (CustomTkinter, dark mode) para operadores no técnicos. Lee datos de H1Test y los copia a h2test con validaciones visuales. Se distribuye como `.exe` compilado con PyInstaller.

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

**Nota pendiente:** `leer_asistencias()` actualmente apunta a pestaña `asistencias` — debería actualizarse a pestaña `Avance` para ser consistente con `export_avance.py`.

---

## Dependencias comunes

```
gspread · google-auth · truststore · requests · pandas · openpyxl
```

Ver `scripts/q10-consolidacion/requirements.txt` para versiones exactas.

**SSL corporativo:** todos los scripts llaman `truststore.inject_into_ssl()` al inicio. Ver [[convenciones#SSL corporativo]].
