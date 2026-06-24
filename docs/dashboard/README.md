# Dashboard Q10 — GitHub Pages

Sitio estático que publica estadísticas agregadas de avance de estudiantes.
Los datos vienen de Google Sheets (pestaña `estadísticas` del Sheet `h2test`) y se
exponen como JSON sin PII (sin nombres, emails ni cédulas).

## Cómo actualizar data.json

```bash
cd scripts/q10-consolidacion
python export_stats.py
```

El script:
1. Lee la pestaña `h2test` directamente (datos crudos — 8,818 filas)
2. Agrega en Python: tabla POR CURSO + conteos de anomalías (SIN MATCH, AVANCE 0%, IRREGULAR)
3. Escribe `docs/dashboard/data.json` (sin PII — solo estadísticas)
4. Ejecuta `git add → commit → push` automáticamente

Si el commit falla (nada que commitear, o git no inicializado), el script lo advierte
y termina sin error.

## Publicar en GitHub Pages

1. Ir a **Settings → Pages** del repositorio en GitHub
2. Source: `Deploy from a branch`
3. Branch: `main` / Folder: `/docs`
4. Guardar — el sitio queda en `https://<usuario>.github.io/<repo>/dashboard/`

El archivo `data.json` se lee con `fetch('./data.json')` desde `index.html`, por lo que
ambos deben estar en la misma carpeta (`docs/dashboard/`).

## Estructura

```
docs/dashboard/
├── index.html   ← sitio (diseñado con 21.dev)
├── data.json    ← generado por export_stats.py, nunca editar a mano
└── README.md    ← este archivo
```

## Formato de data.json

```json
{
  "ultima_actualizacion": "2026-06-24T10:00:00-05:00",
  "por_curso": [
    { "curso": "Nombre del curso", "estudiantes": 100, "promedio": 75.5, "min": 0.0, "max": 100.0 }
  ],
  "anomalias": [
    { "categoria": "SIN MATCH",        "cantidad": 3415 },
    { "categoria": "AVANCE 0%",        "cantidad": 413  },
    { "categoria": "AVANCE IRREGULAR", "cantidad": 2    }
  ],
  "totales": {
    "total_cursos": 8,
    "total_estudiantes_unicos": 4559
  }
}
```

**Nota SIN MATCH:** agrupa todas las filas con Curso vacío tras el LEFT JOIN — incluye
estudiantes sin matrícula virtual Y estudiantes cuyo email no coincidió en Consolidado.
Son indistinguibles en h2test sin columna adicional.
