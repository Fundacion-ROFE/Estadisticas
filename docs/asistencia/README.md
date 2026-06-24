# Dashboard Asistencia — GitHub Pages

Sitio estático que muestra estadísticas de asistencia por sesión.
Los datos vienen de la pestaña `asistencias` del Sheet de registro manual.

## Cómo actualizar data.json

```bash
cd scripts/q10-consolidacion
python export_asistencia.py
```

El script lee la hoja, cuenta asistentes por módulo y hace git push automático.

## Estructura

```
docs/asistencia/
├── index.html   ← sitio (colocar aquí el HTML del usuario)
├── data.json    ← generado por export_asistencia.py, nunca editar a mano
└── README.md    ← este archivo
```

## Requisito previo

Compartir el Sheet con el Service Account como Lector:
  q10-automatizacion@n8n-automatizacion-q10.iam.gserviceaccount.com
  Sheet: https://docs.google.com/spreadsheets/d/1ggzoJeZR3fS6AwRCLoGeYA5HEp_B7zvOwFGlGwny0l8
