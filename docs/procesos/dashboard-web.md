# Dashboard Web — GitHub Pages

**Estado:** Completado / En producción
**Última actualización:** 2026-06-26
**Procesos relacionados:** [[q10-consolidacion]]

## Qué hace

Expone estadísticas agregadas (sin datos personales) de todos los programas de Fundación ROFÉ en un sitio estático en GitHub Pages. Dos fuentes de datos públicas:

- **h2test** (Sheet Q10) → `docs/dashboard/data.json` — avance por curso, separado por programa
- **Avance** (Sheet manual) → `docs/avance/data.json` — avance por curso (% progreso)

Un panel local (GUI) cruza ambas fuentes con PII para análisis interno sin publicar nada personal.

## Disparadores

| Acción | Cómo |
|---|---|
| Actualizar stats Q10 | `python export_stats.py` — lee h2test, genera JSON, push |
| Actualizar avance manual | `python export_avance.py` — lee pestaña Avance, genera JSON, push |
| Panel de riesgo local | `python tools/panel_riesgo_gui.py` — GUI con PII, sin push |

## Arquitectura

```
Google Sheets h2test                    tools/course_config.json
        │                                       │
        │ export_stats.py                       │ (clasificación JC/MR/Stand-by)
        │   _cargar_config_cursos()  ◄──────────┘
        │   _clasificar_curso()
        ▼
docs/dashboard/data.json
  { por_curso[] (JC),         ← top-level siempre = Jóvenes creaTIvos
    anomalias[], totales{},
    mr: { por_curso[], ... }, ← Mujeres ROFÉ
    stand: { por_curso[], ... } ← cursos sin programa asignado
  }

Google Sheets Avance (manual)
        │
        │ export_avance.py
        ▼
docs/avance/data.json

        git push → GitHub Pages
        ┌───────────────────────────────────────────┐
        │     fundacion-rofe.github.io/Estadisticas  │
        │                                           │
        │  docs/dashboard/index.html  (4 pestañas) │
        │  docs/mujeres-rofe/index.html             │
        └───────────────────────────────────────────┘

Google Sheets h2test  ──┐
                         ├──► panel_riesgo_gui.py  (solo local, PII)
Google Sheets Avance  ──┘     4 tabs interactivos
```

## Regla de privacidad (obligatoria)

**NUNCA va a GitHub Pages:** nombres, cédulas, correos, celulares, IDs Q10 ni ningún campo que identifique a una persona individual.

Solo sube: totales, promedios, conteos por curso, mínimos, máximos, anomalías.

Los datos individuales solo existen en `tools/` (gitignoreado) y en RAM del `panel_riesgo_gui.py`.

---

## Separación de programas — course_config.json

La clasificación de cursos en JC / MR / Stand-by se controla en **`tools/course_config.json`** (archivo local, no va a GitHub). Tiene precedencia sobre los keywords de fallback en el código.

```json
{
  "jc":    ["BIENVENIDOS A JÓVENES CREATIVOS", "EMPRENDIMIENTO: IDEA DE NEGOCIO JC", ...],
  "mr":    ["DE LA IDEA A LA ACCIÓN, TU GUÍA PARA EMPRENDER CON ÉXITO", "HABILIDADES DEL SER..."],
  "stand": []
}
```

**Flujo para agregar un curso nuevo:**
1. Abrir `panel_riesgo_gui.py` → Tab ⚙ Admin
2. Asignar el curso nuevo a JC / MR / Stand-by
3. Guardar → escribe `course_config.json`
4. Correr `export_stats.py` → el nuevo curso aparece en el programa correcto del dashboard

**Fallback (si el curso no está en el config):** keywords `["emprendedoras", "idea a la acci"]` → MR; todo lo demás → JC.

---

## Dashboard público — docs/dashboard/index.html

| Tab | Fuente | Contenido |
|---|---|---|
| Estadísticas Q10 | `data.json` top-level | KPIs · tabla por curso con semáforo · anomalías — **solo JC** |
| Avance Manual | `avance/data.json` | KPIs · tabla por curso · anomalías manuales |
| Comparativo | Ambos JSONs | Tabla Manual vs Q10 · Δ diferencia · anomalías cruzadas |
| Admin | `data.json` (todos) | Resumen por programa (JC/MR/Stand-by) · barras por curso · tabla detalle |
| Mujeres ROFÉ ↗ | Link a panel MR | Navega a `docs/mujeres-rofe/index.html` |

El Tab Admin lee las tres secciones del JSON (`por_curso`, `mr.por_curso`, `stand.por_curso`) y los muestra juntos con código de color por programa.

## Panel Mujeres ROFÉ — docs/mujeres-rofe/index.html

Panel independiente con identidad visual MR (paleta rose/warm). Lee `../dashboard/data.json` y accede a `data.mr`. No filtra con JS — la separación ya viene hecha desde Python.

KPIs: Mujeres inscritas (`mr.totales.total_estudiantes_unicos`) · # Cursos · Promedio · Avance 0%.

---

## Semáforo (fijo en toda la app)

| Rango  | Color    | Etiqueta      |
|---|---|---|
| ≥ 80%  | Verde    | Satisfactorio |
| 60–79% | Amarillo | En riesgo     |
| < 60%  | Rojo     | Atención      |

---

## Estructura de data.json (export_stats.py)

```json
{
  "ultima_actualizacion": "2026-06-26T15:45:55-05:00",

  "por_curso": [
    {"curso": "BIENVENIDOS A JÓVENES CREATIVOS", "estudiantes": 863, "promedio": 98.47, "min": 0.0, "max": 100.0}
  ],
  "anomalias": [
    {"categoria": "SIN MATCH",        "cantidad": 0},
    {"categoria": "AVANCE 0%",         "cantidad": 163},
    {"categoria": "AVANCE IRREGULAR",  "cantidad": 2}
  ],
  "totales": {
    "total_cursos": 6,
    "total_estudiantes_unicos": 863,
    "total_habilitados": 863,
    "total_db": 1146
  },

  "mr": {
    "por_curso": [
      {"curso": "DE LA IDEA A LA ACCIÓN...", "estudiantes": 136, "promedio": 13.87, "min": 0.0, "max": 100.0},
      {"curso": "HABILIDADES DEL SER...",     "estudiantes": 244, "promedio": 30.55, "min": 0.0, "max": 100.0}
    ],
    "anomalias": [
      {"categoria": "AVANCE 0%",        "cantidad": 215},
      {"categoria": "AVANCE IRREGULAR", "cantidad": 0}
    ],
    "totales": {
      "total_cursos": 2,
      "total_estudiantes_unicos": 283,
      "total_habilitados": 283
    }
  },

  "stand": {
    "por_curso": [],
    "totales": {"total_cursos": 0, "total_estudiantes_unicos": 0, "total_habilitados": 0}
  }
}
```

**Nota importante — AVANCE 0% en MR:** el valor 215 es por matrícula (student × course), no por estudiante único. De 283 estudiantes únicas, 211 tienen promedio 0% en todos sus cursos y 72 tienen algún progreso. Esta distinción se gestiona en el panel GUI, no en el JSON.

## Estructura de data.json (avance — export_avance.py)

```json
{
  "ultima_actualizacion": "ISO8601",
  "segmento": "Logica-Nivel 2-2026",
  "por_curso": [
    {"nombre": "Bienvenida", "estudiantes": 863, "promedio": 98.49, "min": 0.0, "max": 100.0}
  ],
  "totales": {
    "total_cursos": 6,
    "total_registros": 5048,
    "estudiantes_unicos_id": 863,
    "promedio_general": 94.06
  },
  "anomalias": [
    {"categoria": "AVANCE 0%",        "cantidad": 170},
    {"categoria": "AVANCE IRREGULAR", "cantidad": 2},
    {"categoria": "SIN PROGRESO",     "cantidad": 0}
  ]
}
```

---

## Panel de riesgo local — tools/panel_riesgo_gui.py

GUI Tkinter con datos individuales (PII). Nunca sube a GitHub.

### Tabs

| Tab | Descripción |
|---|---|
| 🎓 Jóvenes creaTIvos | 6 KPI cards clickeables → tabla dinámica por vista |
| 💡 Mujeres ROFÉ | 6 KPI cards clickeables → tabla dinámica por vista |
| ⚙ Admin | Clasificación de cursos JC/MR/Stand-by · Guardar → course_config.json |
| 🔀 Diferencias | Comparativa cruzada Manual vs Q10 · 3 vistas: Solo Q10, Solo Manual, En Ambas |

### Vistas del tab 🎓 Jóvenes creaTIvos

| Tarjeta | Tabla que aparece | Columnas |
|---|---|---|
| EN Q10 JC | Todos los estudiantes JC en Q10 | Nombre · Email · # Cursos · Promedio Q10 % |
| MATCH AMBAS | Estudiantes en Q10 y en manual | Nombre · Cédula · Email · Q10 % · Manual % · Estado |
| ATENCIÓN | (student, curso) con avance < umbral | Nombre · Cédula · Email · Curso · Q10 % · Manual % · Estado |
| AVANCE 0% | Sin actividad en plataforma | Nombre · Cédula · Email · # Cursos · Manual % · Diagnóstico |
| SIN MATCH | En Q10 sin registro manual | Nombre · Email · # Cursos · Promedio Q10 % |
| OK ✓ | Avance ≥ umbral en todos sus cursos | Nombre · Cédula · Email · Q10 % · Manual % |

### Vistas del tab 💡 Mujeres ROFÉ

| Tarjeta | Tabla que aparece | Columnas |
|---|---|---|
| MUJERES | Todas las estudiantes únicas (283) | Nombre · Cédula · Email · # Cursos · Promedio · Estado |
| CURSOS | Resumen de los 2 cursos MR | Curso · Inscritas · Promedio · Mín · Máx · Estado |
| PROMEDIO | Todas con nota por curso | Nombre · Email · [Curso 1] · [Curso 2] · Promedio |
| ≥ 80% OK | Filtro avg ≥ 80% | Nombre · Email · [Curso 1] · [Curso 2] · Promedio |
| EN RIESGO 60–79% | Filtro 60 ≤ avg < 80 | Nombre · Email · [Curso 1] · [Curso 2] · Promedio |
| AVANCE 0% | avg = 0% | Nombre · Email · [Curso 1] · [Curso 2] |

En todas las vistas: doble clic en una fila → popup con todos los detalles. Exportar CSV → descarga solo la vista activa con nombre descriptivo (ej. `mr_ok_20260626.csv`).

### Tab 🔀 Diferencias (nuevo)

Compara las dos fuentes (Q10 JC vs Avance Manual) para detectar inconsistencias de captación.

| Vista (KPI card) | Qué muestra | Columnas |
|---|---|---|
| EN Q10 SIN registro manual | Estudiantes en Q10 que no aparecen en Avance Manual | Nombre · Email · # Cursos Q10 · Promedio Q10 % |
| EN MANUAL SIN registro Q10 | Estudiantes en Avance Manual que no aparecen en Q10 | Nombre · Cédula · Email · # Cursos Manual · Promedio Manual % |
| EN AMBAS fuentes | Estudiantes que sí cruzaron en ambas fuentes | Nombre · Cédula · Email · Q10 % · Manual % · Estado |

**Cruce por email:** si un estudiante tiene emails distintos en cada sistema, aparece como "no encontrado" aunque exista en ambos. Esa es la causa más común de diferencias.

**Por qué el dashboard GitHub muestra más "AVANCE 0%" que el panel:**
- Dashboard GitHub: cuenta por *matrícula* (un estudiante en 6 cursos todos a 0% = 6).
- Panel .py "AVANCE 0%": cuenta estudiantes *únicos* que están en AMBAS fuentes y tienen 0% en todos sus cursos Q10. Los que están en Q10 pero no en Manual caen en "Solo Q10", no en "AVANCE 0%".

### Tab Admin (clasificación de cursos)

Lista scrollable con todos los cursos detectados en h2test. Cada curso tiene un ComboBox (JC / MR / Stand-by). Botón "Guardar" → escribe `tools/course_config.json`. Los cambios se aplican en el próximo "Actualizar datos".

---

## Mapeo de nombres (Tab Comparativo)

Las dos fuentes usan nombres distintos. Hardcodeado en `ALIAS_Q10` en `docs/dashboard/index.html`:

| Nombre en Avance (manual) | Nombre en h2test (Q10) |
|---|---|
| Bienvenida | BIENVENIDOS A JÓVENES CREATIVOS |
| Hackea Tu Cerebro | HACKEA TU CEREBRO: APRENDE EN MENOS TIEMPO Y SIN SUFRIR |
| Habilidades Esenciales | HABILIDADES ESENCIALES PARA SER UN EMPRENDEDOR EXITOSO |
| Emprendimiento | EMPRENDIMIENTO: IDEA DE NEGOCIO JC |
| IA | INTRODUCCIÓN A LA IA GENERATIVA - 2026 |
| Lógica de Programación | FUNDAMENTOS LÓGICA DE PROGRAMACIÓN - 2026 |

Si los nombres cambian en alguna fuente, actualizar `ALIAS_Q10` en `docs/dashboard/index.html`.

---

## Cómo actualizar el dashboard

```bash
# Desde scripts/q10-consolidacion/
python export_stats.py    # Q10 → dashboard/data.json → push
python export_avance.py   # Manual → avance/data.json → push

# Si el push falla (SSL):
git push origin main
```

Ambos scripts hacen `git add + commit + push` automáticamente.

## Cómo abrir el panel de riesgo

```bash
python tools/panel_riesgo_gui.py
```

Requiere acceso Viewer al Sheet h2test y al Sheet Avance desde el Service Account.

---

## Contingencia manual

1. **export_stats.py falla:** verificar que el Service Account tiene acceso al Sheet h2test (ID: `1q4VNn4ltqVEMsOjo-c2ZbsbW3VIt-XomPgXeLSN_LTs`).
2. **export_avance.py falla:** verificar acceso al Sheet Avance (ID: `1ggzoJeZR3fS6AwRCLoGeYA5HEp_B7zvOwFGlGwny0l8`) y que la pestaña se llama exactamente `Avance`.
3. **Git push falla SSL:** `git config --local http.sslBackend schannel` (ver [[convenciones#SSL corporativo]]).
4. **Dashboard en blanco:** abrir devtools → consola → ver error de fetch. Comparar estructura del JSON con la esperada arriba.
5. **course_config.json falta:** `export_stats.py` usa keywords de fallback automáticamente. Reconstruir config desde el Tab Admin del GUI.

---

## Gotchas

- **AVANCE 0% ≠ "estudiantes sin progreso":** el contador de anomalías cuenta por matrícula (una estudiante en 2 cursos con 0% suma 2). Para contar personas únicas, usar el panel GUI.
- **Doble encabezado en h2test y Avance:** fila 1 = nombres de cursos fusionados, fila 2 = sub-headers. `detectar_grupos()` lo maneja en todos los scripts. Ver [[convenciones#Doble encabezado en Google Sheets]].
- **Cruce por email, no por ID:** las dos fuentes usan IDs incompatibles (cédula vs código interno Q10). Si un estudiante tiene emails distintos en cada sistema queda como SIN MATCH.
- **tools/ está gitignoreado:** `course_config.json` vive en `tools/` y nunca sube a GitHub. Si se pierde, reconstruirlo desde el Tab Admin del GUI (los cursos se cargan de h2test en tiempo real).

---

## Conexiones del sistema

- [[mapa-codigo]] — detalle técnico de `export_stats.py`, `export_avance.py`, `panel_riesgo_gui.py`
- [[q10-consolidacion]] — produce el Sheet h2test que consume `export_stats.py`
- [[convenciones]] — SSL corporativo · doble encabezado en Sheets
- Dashboard en producción: `https://fundacion-rofe.github.io/Estadisticas/dashboard/`
