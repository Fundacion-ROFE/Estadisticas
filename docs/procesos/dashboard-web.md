# Dashboard Web — GitHub Pages

**Estado:** Fase 2 completada / Fase 3 pendiente
**Última actualización:** 2026-06-24
**Procesos relacionados:** [[q10-consolidacion]]

## Qué hace

Expone estadísticas agregadas (sin datos personales) del programa Jóvenes creaTIvos
en un sitio estático en GitHub Pages. Dos fuentes de datos:

- **h2test** (Sheet Q10) → `docs/dashboard/data.json` — avance por curso, anomalías
- **asistencias** (Sheet manual) → `docs/asistencia/data.json` — retención por sesión

El dashboard se actualiza ejecutando scripts Python localmente → commit → push → Pages.

## Arquitectura

```
Script Python (local)
  ├── export_stats.py     → lee h2test → docs/dashboard/data.json
  └── export_asistencia.py → lee asistencias → docs/asistencia/data.json

GitHub Pages (público)
  └── docs/
      └── dashboard/
          ├── index.html    ← dashboard 3 pestañas
          └── data.json     ← stats Q10 agregadas (sin PII)
      └── asistencia/
          └── data.json     ← stats asistencia agregadas (sin PII)

Máquina local (privado, gitignoreado)
  └── tools/
      ├── panel_riesgo.py   ← cruce individual por email
      └── reportes/         ← CSVs con nombres/IDs (nunca a GitHub)
```

## Regla de privacidad (obligatoria)

**NUNCA va a GitHub Pages:** nombres, cédulas, correos, celulares, IDs Q10, o
cualquier campo que identifique a una persona individual.

Solo sube: totales, promedios, conteos por curso/sesión, % de retención.

## Pestañas del dashboard (docs/dashboard/index.html)

| Pestaña | Contenido |
|---|---|
| Estadísticas Q10 | 4 KPIs · tabla por curso con semáforo · scorecards de anomalías |
| Asistencia | 4 KPIs · barras horizontales por sesión (verde=max, rojo=min) |
| Comparativo | Retención vs avance · anomalías en contexto · info panel_riesgo.py |

## Semáforo

| Rango | Color | Etiqueta |
|---|---|---|
| ≥ 80% | Verde | Satisfactorio |
| 60–79% | Amarillo | En riesgo |
| < 60% | Rojo | Atención |

Umbral configurable: `--umbral N` en panel_riesgo.py (default 60).

## Scripts clave

| Script | Ruta | Qué genera |
|---|---|---|
| export_stats.py | scripts/q10-consolidacion/ | docs/dashboard/data.json |
| export_asistencia.py | scripts/q10-consolidacion/ | docs/asistencia/data.json |
| panel_riesgo.py | tools/ | Reporte en consola + CSV local |

## Estructura de data.json (Q10)

```json
{
  "ultima_actualizacion": "ISO8601",
  "por_curso": [{"nombre": "...", "promedio": 72.3, "min": 5, "max": 100, "total": 12}],
  "anomalias": {"sin_match": 0, "avance_0": 3, "avance_irregular": 0},
  "total_estudiantes_unicos": 78
}
```

## Estructura de data.json (Asistencia)

```json
{
  "ultima_actualizacion": "ISO8601",
  "segmento": "Logica-Nivel 2-2026",
  "sesiones": [{"nombre": "...", "asistentes": 45}],
  "totales": {
    "total_sesiones": 6,
    "total_registros": 217,
    "estudiantes_unicos_id": 78,
    "porcentaje_retencion": 62.2,
    "promedio_sesiones_por_estudiante": 2.7,
    "sesion_max": {"nombre": "...", "asistentes": 45},
    "sesion_min": {"nombre": "...", "asistentes": 28}
  }
}
```

## Cómo actualizar el dashboard

```bash
# 1. Actualizar datos Q10
python scripts/q10-consolidacion/export_stats.py

# 2. Actualizar datos asistencia
python scripts/q10-consolidacion/export_asistencia.py

# 3. Ambos scripts hacen git add + commit + push automáticamente
#    Si algo falla, hacer push manual:
git push origin main
```

## Cómo correr el análisis de riesgo (local, privado)

```bash
python tools/panel_riesgo.py --segmento "Logica-Nivel 2-2026"
python tools/panel_riesgo.py --csv           # exporta CSVs a tools/reportes/
python tools/panel_riesgo.py --umbral 50     # umbral personalizado
```

Requiere: Service Account con acceso a ambos Sheets.

## Cruce de identidad (gotcha importante)

**No cruzar por ID numérico.** Las dos fuentes usan IDs diferentes:
- Hoja asistencias → Número de Identificación = cédula (CC nacional)
- h2test → Identificacion = código interno de fila en Q10

**Cruzar por email (correo electrónico).** Ambas fuentes lo tienen.
Riesgo de calidad: si un estudiante registró emails diferentes en cada sistema,
quedará como SIN MATCH aunque sí esté activo.

## Gotchas

- **Celdas fusionadas en asistencias:** Google Sheets API devuelve el valor de celda
  fusionada solo en la primera columna del grupo; las siguientes vienen vacías.
  `export_asistencia.py` detecta módulos escaneando row[0] por celdas no vacías.
- **export_asistencia.py necesita acceso explícito:** compartir la Sheet de asistencias
  con el Service Account antes de correr el script.
- **tools/ está gitignoreado completo:** cualquier archivo bajo tools/ (incluidos
  panel_riesgo.py y reportes/) nunca se subirá a GitHub aunque hagas `git add .`.

## Fase 3 — pendiente

- [ ] Compartir Sheet asistencias con Service Account si aún no está hecho
- [ ] Correr `export_asistencia.py` con datos reales y verificar JSON generado
- [ ] Correr `panel_riesgo.py` y validar cruce con cédulas reales
- [ ] Activar GitHub Pages: Settings → Pages → main → /docs
- [ ] Primera corrida completa: export_stats + export_asistencia → push → verificar URL pública
