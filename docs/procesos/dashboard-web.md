# Dashboard Web — GitHub Pages

**Estado:** Completado / En producción
**Última actualización:** 2026-06-24
**Procesos relacionados:** [[q10-consolidacion]]

## Qué hace

Expone estadísticas agregadas (sin datos personales) del programa Jóvenes creaTIvos
en un sitio estático en GitHub Pages. Dos fuentes de datos:

- **h2test** (Sheet Q10) → `docs/dashboard/data.json` — avance por curso, anomalías
- **Avance** (Sheet manual de plataforma) → `docs/avance/data.json` — avance por curso (% progreso)

El dashboard se actualiza ejecutando scripts Python localmente → commit → push → Pages se actualiza automáticamente.

## Disparador (Trigger)

Manual — el operador corre los scripts cuando necesita actualizar el dashboard.
No hay Schedule ni bot de Telegram para esta parte. El flujo es:

1. `python export_stats.py` — lee h2test, genera `docs/dashboard/data.json`, hace push
2. `python export_avance.py` — lee pestaña Avance, genera `docs/avance/data.json`, hace push

## Arquitectura

```
Script Python (local)
  ├── export_stats.py      → lee h2test (Q10) → docs/dashboard/data.json
  └── export_avance.py     → lee Avance (manual) → docs/avance/data.json

GitHub Pages (público)
  └── docs/
      ├── dashboard/
      │   ├── index.html     ← dashboard 3 pestañas
      │   └── data.json      ← stats Q10 agregadas (sin PII)
      └── avance/
          └── data.json      ← stats Avance manual agregadas (sin PII)

Máquina local (privado, gitignoreado)
  └── tools/
      ├── panel_riesgo.py    ← cruce individual por email (PII)
      └── reportes/          ← CSVs con nombres/IDs (nunca a GitHub)
```

## Regla de privacidad (obligatoria)

**NUNCA va a GitHub Pages:** nombres, cédulas, correos, celulares, IDs Q10, o
cualquier campo que identifique a una persona individual.

Solo sube: totales, promedios, conteos por curso, mínimos, máximos, anomalías.

## Pestañas del dashboard (docs/dashboard/index.html)

| Pestaña | Fuente | Contenido |
|---|---|---|
| Estadísticas Q10 | `docs/dashboard/data.json` | 4 KPIs · tabla por curso con semáforo · scorecards de anomalías |
| Avance Manual | `docs/avance/data.json` | 4 KPIs · tabla por curso con semáforo · scorecards de anomalías Avance |
| Comparativo | Ambos JSONs | Tabla lado a lado Q10 vs Manual · Δ diferencia · anomalías de ambas fuentes |

## Semáforo

| Rango | Color | Etiqueta |
|---|---|---|
| ≥ 80% | Verde | Satisfactorio |
| 60–79% | Amarillo | En riesgo |
| < 60% | Rojo | Atención |

## Scripts clave

| Script | Ruta | Qué genera |
|---|---|---|
| `export_stats.py` | `scripts/q10-consolidacion/` | `docs/dashboard/data.json` |
| `export_avance.py` | `scripts/q10-consolidacion/` | `docs/avance/data.json` |
| `panel_riesgo.py` | `tools/` | Reporte en consola + CSV local (solo PII) |

Ver [[mapa-codigo]] para detalle completo de cada script.

## Estructura de data.json (Q10 — export_stats.py)

```json
{
  "ultima_actualizacion": "ISO8601",
  "por_curso": [
    {"curso": "NOMBRE COMPLETO Q10", "estudiantes": 862, "promedio": 96.37, "min": 0.0, "max": 100.0}
  ],
  "anomalias": [
    {"categoria": "SIN MATCH", "cantidad": 3415},
    {"categoria": "AVANCE 0%", "cantidad": 3904},
    {"categoria": "AVANCE IRREGULAR", "cantidad": 2}
  ],
  "totales": {"total_cursos": 8, "total_estudiantes_unicos": 4563}
}
```

## Estructura de data.json (Avance — export_avance.py)

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
    {"categoria": "AVANCE 0%", "cantidad": 0},
    {"categoria": "AVANCE IRREGULAR", "cantidad": 0},
    {"categoria": "SIN ETIQUETA", "cantidad": 0}
  ]
}
```

## Mapeo de nombres de cursos (Tab 3 Comparativo)

Las dos fuentes usan nombres distintos para los mismos cursos. El HTML tiene un `ALIAS_Q10` hardcodeado:

| Nombre en Avance (manual) | Nombre en h2test (Q10) |
|---|---|
| Bienvenida | BIENVENIDOS A JÓVENES CREATIVOS |
| Hackea Tu Cerebro | HACKEA TU CEREBRO: APRENDE EN MENOS TIEMPO Y SIN SUFRIR |
| Habilidades Esenciales | HABILIDADES ESENCIALES PARA SER UN EMPRENDEDOR EXITOSO |
| Emprendimiento | EMPRENDIMIENTO: IDEA DE NEGOCIO JC |
| IA | INTRODUCCIÓN A LA IA GENERATIVA - 2026 |
| Lógica de Programación | FUNDAMENTOS LÓGICA DE PROGRAMACIÓN - 2026 |

Si los nombres cambian en alguna de las fuentes, actualizar el objeto `ALIAS_Q10` en `docs/dashboard/index.html`.

## Cómo actualizar el dashboard

```bash
# Actualizar datos Q10
python scripts/q10-consolidacion/export_stats.py

# Actualizar datos Avance manual
python scripts/q10-consolidacion/export_avance.py

# Ambos scripts hacen git add + commit + push automáticamente.
# Si push falla (SSL), hacer manualmente:
git push origin main
```

## Cómo correr el análisis de riesgo (local, privado)

```bash
python tools/panel_riesgo.py --segmento "Logica-Nivel 2-2026"
python tools/panel_riesgo.py --csv           # exporta CSVs a tools/reportes/
python tools/panel_riesgo.py --umbral 50     # umbral personalizado
```

Requiere: Service Account con acceso Viewer a ambos Sheets.

## Contingencia manual

Si los scripts fallan o el push no llega:

1. **export_stats.py falla:** verificar acceso del Service Account al Sheet h2test (ID: `1q4VNn4ltqVEMsOjo-c2ZbsbW3VIt-XomPgXeLSN_LTs`). Correr con `python -v` para tracing.
2. **export_avance.py falla:** verificar acceso al Sheet Avance (ID: `1ggzoJeZR3fS6AwRCLoGeYA5HEp_B7zvOwFGlGwny0l8`). Confirmar que la pestaña se llama exactamente `Avance`.
3. **Git push falla SSL:** `git config --local http.sslBackend schannel` (ver [[convenciones#SSL corporativo]]).
4. **Dashboard no se actualiza en Pages:** Pages puede tardar hasta 2 minutos. Si persiste, ir a Settings → Pages y verificar que Source es `main / /docs`.
5. **JSON malformado / dashboard en blanco:** abrir devtools del navegador → consola → ver error. Comparar estructura del JSON con la esperada arriba.

## Cruce de identidad (gotcha importante)

**No cruzar por ID numérico.** Las dos fuentes usan IDs diferentes:
- Hoja Avance → Número de Identificación = cédula (CC nacional)
- h2test → Identificacion = código interno de fila en Q10

**Cruzar por email (correo electrónico).** Ambas fuentes lo tienen.
Riesgo de calidad: si un estudiante registró emails diferentes en cada sistema,
quedará como SIN MATCH aunque sí esté activo.

## Gotchas

- **Doble encabezado en h2test y Avance:** ambas pestañas tienen fila 1 = nombres de cursos fusionados, fila 2 = sub-headers. `detectar_grupos()` lo maneja en ambos scripts. Ver [[convenciones#Doble encabezado en Google Sheets]].
- **SIN ETIQUETA en Avance:** los primeros 3 grupos de columnas no tienen nombre de curso en fila 1 → se cuentan como anomalía SIN ETIQUETA. Solo los 6 cursos con nombre se incluyen en estadísticas.
- **tools/ está gitignoreado completo:** cualquier archivo bajo `tools/` nunca se subirá a GitHub aunque hagas `git add .`.
- **export_asistencia.py:** script legacy que lee pestaña `asistencias` (sesiones presenciales). No se usa actualmente en el dashboard, reemplazado por `export_avance.py`. Se conserva por si se necesita análisis de sesiones.

## Conexiones del sistema

- [[mapa-codigo]] — detalle técnico de `export_stats.py`, `export_avance.py`, `panel_riesgo.py`
- [[q10-consolidacion]] — produce el Sheet h2test que consume `export_stats.py`
- [[convenciones]] — SSL corporativo, doble encabezado en Sheets
- Dashboard en producción: `https://fundacion-rofe.github.io/Estadisticas/dashboard/`
