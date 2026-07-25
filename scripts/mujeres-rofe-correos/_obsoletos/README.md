# Obsoletos — scripts/mujeres-rofe-correos

## extraer_lista_bogota.py / generar_lista_y_enviar.py (archivados 2026-07-24)

Reemplazados por `../extraer_lista_ciudad_mr.py`. Ambos tenían bugs de ciudad
descubiertos el mismo día (ver `claude_sessions.md` y memoria
`project_supabase_mr_sincronizacion_gap`):

- `extraer_lista_bogota.py`: consultaba `participants`+`enrollments`
  (`courses.programa='mr'`) — la tabla de **matriculadas en curso**, no el universo
  completo de postulantes MR. Por diseño nunca iba a devolver más de un puñado de
  personas para una ciudad.
- `generar_lista_y_enviar.py`: sí consultaba la tabla correcta (`postulantes_mr`)
  pero filtraba con `if 'BOGOTA' in ciudad.upper():` — `.upper()` en Python no quita
  tildes, así que descartaba silenciosamente "Bogotá D.C." (431 de 512 filas).

`extraer_lista_ciudad_mr.py` corrige ambos: usa `postulantes_mr` (universo completo)
y filtra por la columna generada `ciudad_norm` + `ciudad_alias`
(ver `docs/migrations/013_normalizar_ciudad.sql`), que sí normaliza tildes/mayúsculas/
puntuación y fusiona nombres administrativos distintos del mismo municipio.

No borrar sin releer — quedan como referencia de qué NO volver a hacer.
