# Dashboard Web — GitHub Pages

**Estado:** Completado / En producción
**Última actualización:** 2026-07-14
**Procesos relacionados:** [[q10-consolidacion]] · [[panel-datos-etl]]

## Qué hace

Expone estadísticas agregadas (sin datos personales) de todos los programas de Fundación ROFÉ en un sitio estático en GitHub Pages. Dos fuentes de datos públicas:

- **h2test** (Sheet Q10) → `docs/dashboard/data.json` — avance por curso, separado por programa
- **Avance** (Sheet manual) → `docs/avance/data.json` — avance por curso (% progreso)
- **Retirados** (Sheet Q10, misma hoja de h2test) → `docs/retirados/data.json` — retiros agregados por tipo/causa/programa/mes

Un panel local (GUI) cruza ambas fuentes con PII para análisis interno sin publicar nada personal.

## Disparadores

| Acción | Cómo |
|---|---|
| Actualizar stats Q10 | `python export_stats.py` — lee h2test, genera JSON, push |
| Actualizar avance manual | `python export_avance.py` — lee pestaña Avance, genera JSON, push |
| Actualizar retirados | `python export_retirados.py` — lee pestaña Retirados, genera JSON, push |
| Actualizar aprobación | `python export_aprobacion.py` — descarga directa Q10 (3 reportes), genera JSON, push. **Automático cada 4 h** vía workflow n8n `Bot Q10 - Actualizar Grupos` y con el comando del bot Telegram (desde 2026-07-07) |
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

## Cursos finalizados — marca de agua (inscritos → finalizados)

**Problema:** el Consolidado de Q10 usa `archivado=false` (solo estudiantes activos). Cuando alguien
se inhabilita/retira, desaparece del Consolidado → de h2test → y el conteo del curso **encoge** con el
tiempo (Bienvenida cayó de 863 a 780). Para cursos ya **finalizados** eso subrepresenta el logro real.

**Solución (2026-07-06):** `export_stats.py` mantiene una **marca de agua** por curso en
`docs/dashboard/maximos_cursos.json` (monótona, nunca baja). En cada corrida:

- `inscritos` = máximo histórico de `estudiantes` (matrícula pico 2026 — nunca decae).
- `finalizados` = máximo histórico de estudiantes con `avance >= 100` (cubre los casos de 101).
- `promedio_pico` = promedio al momento del pico de matrícula.
- `finalizado` (bool) = `promedio >= 90%` **y** `estudiantes_hoy <= inscritos * 0.98` (la matrícula
  ya bajó del pico → Q10 empezó a archivar la cohorte al terminar el curso). Constantes:
  `UMBRAL_AVANCE_FIN`, `UMBRAL_PROMEDIO_FIN`, `MARGEN_DECLIVE` en `export_stats.py`.

**Q10 no expone un flag de "curso cerrado"** — el Consolidado solo trae activos + avance. Por eso la
detección es por avance + declive de matrícula, no por un campo de Q10.

**Semilla inicial:** si `maximos_cursos.json` no existe, se siembra desde `history.json` (el pico de
matrícula ya registrado desde el 26-jun). Limitación: cursos cuyo pico real fue **antes** del 26-jun y
que ya habían encogido no se pueden recuperar exactamente; `finalizados` arranca en 0 hasta la primera
corrida real (history.json no guarda el conteo al 100%).

**En el dashboard (Tab 1):** los cursos con `finalizado:true` muestran badge "✓ Finalizado" y la celda
`863 inscritos → 820 finalizaron` (congelado); los abiertos muestran `estudiantes activos` en vivo.
El render es retrocompatible: si faltan los campos nuevos (data.json viejo) trata el curso como abierto.

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

**Rediseño 2026-07-07** (pedido del supervisor: la vista de solo-activos no servía): los tabs 1–3
ahora usan la **cohorte completa** de `aprobacion/data.json` como fuente Q10.

**Fase 1 refactorización 2026 (2026-07-08):** Tab 1 es **solo Jóvenes creaTIvos** — KPIs desde
`por_programa[]` (JC: `estudiantes_cohorte`, `habilitados_unicos`, `retirados_unicos`,
`matriculas_activas`) en vez de `totales{}` que mezclaba MR; barras y tabla filtradas por programa.
Nuevo KPI "Estudiantes hábiles" ("Actualmente hay X estudiantes hábiles, sumando un total de Y
matrículas activas"). **Exclusión de usuarios de prueba** (4 perfiles, ver
`tools/exclusiones_prueba.json` gitignoreado) aplicada en `export_aprobacion.py`, `export_stats.py`
y `export_retirados.py` — las pruebas inflaban cohorte (860→857 en Nivel 1) y retirados (85→82).
Criterio de cuadre verificado: `cursaron == aprobados + aprobados_retirados + sin_finalizar +
retirados` en los 9 cursos, y sumas de tabla == KPIs por programa, exacto.

**Fase 2 refactorización 2026 (2026-07-08):** Tab Comparativo **solo JC** — la columna "Q10" usa
`por_programa[]` JC (857 cohorte / 5.789 matrículas / 84,7%) en vez de `totales{}` que mezclaba MR,
y los 2 cursos MR ya no aparecen como filas grises "solo Q10". Barrido de años < 2026 en todos los
HTML de `docs/`: cero coincidencias (nada que limpiar). Tab Admin sin cambios — la exclusión de
pruebas de Fase 1 vive en `export_stats.py` y sus totales cuadran con aprobación
(JC 777 / MR 282 = `habilitados_unicos`). Panel Mujeres ROFÉ rediseñado sobre la cohorte (ver
sección abajo). Solo frontend — ningún exporter cambió.

| Tab | Fuente | Contenido |
|---|---|---|
| Estadísticas Q10 | `../aprobacion/data.json` | **Solo JC** — KPIs cohorte 2026 desde `por_programa[]` · barras apiladas % aprobó por curso (verde/azul/ámbar/rojo, 4 segmentos) · tabla detalle cursaron/aprobaron/retirados |
| Avance Manual | `avance/data.json` | Mismo formato: KPI % aprobación manual · barras apiladas aprobó/sin completar · tabla · anomalías manuales |
| Comparativo | `aprobacion` + `avance` | **Solo JC** — % aprobación Manual vs Q10 cohorte por curso (resumen desde `por_programa[]` JC) · Δ diferencia (grupos manuales homónimos se fusionan, ej. 3× HTML) |
| Admin | `data.json` (todos) | Resumen por programa (JC/MR/Stand-by) · barras por curso · tabla detalle — sigue usando export_stats.py |
| Tendencia | `aprobacion` + `history.json` | **Funnel de retención** (2026-07-09): barras por curso en orden de ruta 2026 — largo ∝ cuántos cursaron (la cohorte se encoge), verde = aprobaron · ámbar = quedaron en el camino. Debajo, línea de promedio global JC + cursos individuales (**snapshots diarios** desde 2026-06-26) como vista secundaria |
| Aprobación ↗ | Link a panel aprobación | Navega a `docs/aprobacion/index.html` |
| Retirados ↗ | Link a panel retirados | Navega a `docs/retirados/index.html` |

Deep-link por hash: `/dashboard/#t3` abre directamente esa pestaña (t1–t5).
`data.json` (export_stats.py, solo activos) sigue alimentando el Tab Admin y el header.
| Mujeres ROFÉ ↗ | Link a panel MR | Navega a `docs/mujeres-rofe/index.html` |

El Tab Admin lee las tres secciones del JSON (`por_curso`, `mr.por_curso`, `stand.por_curso`) y los muestra juntos con código de color por programa.

## Panel Retirados — docs/retirados/index.html

Panel independiente con acento naranja. Lee `./data.json` (generado por `export_retirados.py`).
Botón "← Dashboard" para volver.

**Fase 3 (2026-07-09): filtrado a la cohorte 2026 + etapa de retiro.** Antes mostraba el histórico
completo (353 desde 2023). Ahora `export_retirados.py` cruza las cédulas de la pestaña contra
`tools/cohorte_2026.json` (generado por `export_aprobacion.py`) y muestra **solo los 82 retirados
únicos de 2026** — el mismo número que `retirados_unicos` del panel de aprobación. El filtro es por
**cédula contra la cohorte matriculada**, NO por `FechaCancelacion` (poco fiable). Los inhabilitados
sin registro formal en la pestaña se cuentan como `sin_registro_hoja` para que los totales cuadren.

KPIs: Retirados 2026 · Cancelados · Desertores · Aplazados. Barras: **etapa de retiro** (nuevo),
distribución por tipo, causas, retirados por programa, retiros por mes.

**Gráfico "¿En qué etapa de la ruta los perdimos?"** — cada retirado se ubica en el último curso de
la ruta 2026 que completó (avance ≥ 100 en el ledger). Barras en orden de ruta (no por cantidad):
"No completó ninguno" en rojo, el resto en naranja. Es una heurística de secuencia — Q10 no da fecha
de retiro por estudiante, así que se infiere del avance máximo alcanzado. Hallazgo primera corrida
(2026-07-09): 78 de 82 se retiraron durante los tres primeros cursos; pico de 28 tras Hackea tu Cerebro.

**Solo agregados** — la info individual de cada retirado (nombre, ID, teléfono, descripción)
se consulta en el tab 🚪 Retirados del `panel_riesgo_gui.py` local.

**Estructura de data.json (export_retirados.py):**
```json
{
  "ultima_actualizacion": "ISO8601",
  "anio": "2026",
  "totales": {"total_retirados": 82, "cancelados": 55, "desertores": 25, "aplazados": 0,
              "sin_registro_hoja": 2},
  "por_tipo":     [{"tipo": "Cancelado", "cantidad": 55}],
  "por_causa":    [{"causa": "Voluntario", "cantidad": 40}],
  "por_programa": [{"programa": "Jóvenes creaTIvos", "cantidad": 82}],
  "por_mes":      [{"mes": "2026-06", "cantidad": 31}],
  "por_etapa":    [{"orden": 0, "etapa": "No completó ningún curso", "cantidad": 14},
                   {"orden": 2, "etapa": "Hackea tu cerebro: ...", "cantidad": 28}],
  "ruta":         ["Bienvenidos a Jóvenes creaTIvos", "..."]
}
```

Fallback: si falta `tools/cohorte_2026.json`, `anio` es `null`, `por_etapa` va vacío y el panel
muestra el histórico completo (el render lo detecta por `anio`).

## Panel Aprobación por Curso — docs/aprobacion/index.html

Panel independiente con acento verde (2026-07-07). Lee `./data.json` (generado por
`export_aprobacion.py` — directo desde Q10, sin pasar por Sheets). Botón "Aprobación ↗" en el dashboard.

**Por qué existe:** el Tab 1 del dashboard solo muestra a los estudiantes *activos* (el Consolidado
virtual excluye a los inhabilitados), así que no respondía "¿qué % de los que cursaron aprobó?".
Este panel reconstruye la **cohorte completa 2026** (habilitados + inhabilitados) cruzando por cédula
el reporte de Matriculados (Detallado) con el Consolidado virtual y el reporte de retirados.

**Regla de aprobación:** avance ≥ 100 (hay pocos casos de 101 por actividades extra).
Retirado/inhabilitado = no aprobó (verificado: los 80 inhabilitados del periodo 22 están todos
en el reporte de cancelados).

KPIs: Estudiantes cohorte 2026 · Matrículas en cursos · % Aprobación global · Retirados 2026.
Por curso: barra apilada 100% (Aprobaron verde `#6EA050` / Sin completar ámbar `#B8860B` /
Retirados rojo `#C12D4C` — paleta validada CVD y contraste ≥3:1 sobre blanco), badge
✓ Finalizado / En curso, tooltip por segmento, tabla detalle y resumen por programa.

En cursos **finalizados** el % es definitivo; en cursos **en curso**, "sin completar" = aún avanzando.

**Estructura de data.json (export_aprobacion.py):** ver [[mapa-codigo#export_aprobacion.py]].
Estado persistente (marca de agua) en `docs/aprobacion/maximos.json`.

---

## Panel Mujeres ROFÉ — docs/mujeres-rofe/index.html

Panel independiente con identidad visual MR (paleta rose/warm). **Fase 2 (2026-07-08):** aplica el
mismo rigor de cohorte que JC — lee dos fuentes:

- `../dashboard/data.json` → `data.mr` (avance de activas: promedio/mín/máx por curso)
- `../aprobacion/data.json` → `por_programa[]` / `por_curso[]` del programa "Mujeres ROFÉ"
  (cohorte 2026 completa, con exclusión de perfiles de prueba desde Python)

El cruce entre fuentes es por **nombre de curso normalizado a mayúsculas** (aprobación usa
Tipo título, stats usa MAYÚSCULAS). Si `aprobacion/data.json` no carga, el panel degrada a la
vista de solo-avance (los bloques de cohorte no se muestran).

KPIs: Mujeres cohorte 2026 (`estudiantes_cohorte` = 282) · % Aprobación del programa
(`pct_aprobados` = 26,4%) · Avance promedio ponderado · Retiradas 2026 (`retirados_unicos`).
Cada tarjeta de curso muestra: barra apilada de aprobación (misma paleta de 4 segmentos que el
panel JC), badge ✓ Finalizado / En curso, semáforo sobre el **% aprobó de la cohorte** (ya no
sobre el avance promedio) y stats Cursaron / Aprobaron / Retiradas. El resumen global del programa
es el % de aprobación de la cohorte MR.

**Nota:** "Mujeres" = programa Mujeres ROFÉ. NO existe campo de género para estudiantes JC —
no es un cruce de género dentro de JC.

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
    {"curso": "BIENVENIDOS A JÓVENES CREATIVOS", "estudiantes": 780, "promedio": 99.65, "min": 0.0, "max": 100.0,
     "inscritos": 863, "finalizados": 820, "promedio_pico": 98.47, "finalizado": true}
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
| 🚪 Retirados | 5 KPI cards (Todos/Cancelados/Desertores/Aplazados/Causas) → tabla con info completa del retiro (nombre, ID, teléfono, fecha, causa, descripción) · doble clic → popup · exportar CSV · lee pestaña `Retirados` |

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
- **Nombres de curso con capitalización distinta por fuente:** `aprobacion/data.json` trae los
  cursos en Tipo título ("Habilidades del ser para…") y `dashboard/data.json` en MAYÚSCULAS.
  El panel MR cruza ambas fuentes con `toUpperCase()` + colapso de espacios. Si un cruce falla,
  revisar primero tildes/espacios dobles en el nombre del curso en Q10. (2026-07-08)
- **tools/ está gitignoreado:** `course_config.json` vive en `tools/` y nunca sube a GitHub. Si se pierde, reconstruirlo desde el Tab Admin del GUI (los cursos se cargan de h2test en tiempo real).
- **`.nojekyll` obligatorio en `docs/`:** el sitio son dashboards HTML estáticos, pero GitHub Pages procesa `docs/` con Jekyll por defecto. Las notas de Obsidian con sintaxis Liquid (p.ej. expresiones n8n `{{ ... $json.var }}` en `convenciones.md`) rompen el build → "pages build and deployment failed" en cada push. `docs/.nojekyll` (archivo vacío) desactiva Jekyll y arregla todos los fallos de una vez. No borrar. (2026-07-03)

---

## Conexiones del sistema

- [[mapa-codigo]] — detalle técnico de `export_stats.py`, `export_avance.py`, `panel_riesgo_gui.py`
- [[q10-consolidacion]] — produce el Sheet h2test que consume `export_stats.py`
- [[convenciones]] — SSL corporativo · doble encabezado en Sheets
- Dashboard en producción: `https://fundacion-rofe.github.io/Estadisticas/dashboard/`
