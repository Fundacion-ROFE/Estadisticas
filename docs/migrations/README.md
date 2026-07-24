# `docs/migrations/` — convenciones y estado

Migraciones SQL de Supabase (`kbxptoowtnteflhrfwid`), numeradas y aplicadas manualmente
(no hay migration runner — cada archivo se corre a mano en el SQL editor de Supabase y
queda documentado aquí). Ver [[supabase-estructura]] para el diccionario de datos completo.

## Convención de nombres

`NNN_descripcion_ESTADO.sql`, donde `ESTADO` es uno de:

- `APLICADA` — corrida completa en producción, sin bloques pendientes.
- `APLICADA_PARCIAL` — algunos bloques se aplicaron y otros se descartaron
  intencionalmente (el propio archivo documenta cuáles y por qué).
- `PROPUESTA` — escrita pero NO corrida en producción; requiere aprobación de Samuel
  antes de ejecutarse (ver checklist de riesgo en el bloque inicial de cada propuesta).

Un archivo con sufijo `_PROPUESTA` que ya fue aplicado es un archivo desactualizado —
renombrarlo en el mismo commit que se confirma la aplicación (gotcha detectado
2026-07-24: `006` y `007` llevaban semanas aplicadas con el sufijo `_PROPUESTA` todavía
puesto, lo que hacía mentir el nombre).

## Hueco de numeración: no existe `004`

La numeración salta de `003_postulantes_mr.sql` a `005_postulantes_jc.sql` — **no falta
ningún archivo, nunca existió un `004`** (se descartó en su momento antes de aplicarse,
sin dejar rastro en el repo). Documentado aquí para que nadie pierda tiempo buscándolo.
Si en el futuro se necesita una migración `004`, usar el siguiente número libre
(`012` en adelante) en vez de reutilizar el hueco, para no confundir el orden histórico
real de aplicación.

## Estado por archivo (2026-07-24)

| Archivo | Estado real | Nota |
|---|---|---|
| `001_emoflow_ingresos_diario.sql` | APLICADA | tabla `emoflow_ingresos_diario` |
| `002_emoflow_actividad_semanal.sql` | APLICADA | tabla `emoflow_actividad_semanal` |
| `003_postulantes_mr.sql` | APLICADA | tabla `postulantes_mr` |
| `004` | — no existe (ver arriba) | |
| `005_postulantes_jc.sql` | APLICADA | tabla `postulantes_jc` |
| `006_seguridad_hardening_APLICADA_PARCIAL.sql` | APLICADA_PARCIAL | 6/8 bloques aplicados, 2 descartados por dependencias reales (ver cabecera del archivo) |
| `007_retiros_APLICADA.sql` | APLICADA | esquema de `retiros` (tabla vacía hasta `sync_retiros.py`, Track B de la Ola 1) |
| `008_v_persona_360.sql` | APLICADA | vista `v_persona_360` |
| `009_en_seguimiento_jc.sql` | APLICADA | tabla `en_seguimiento_jc` |
| `010_excluir_en_seguimiento_de_vistas.sql` | APLICADA | ajuste de vistas públicas |
| `011_emoflow_canonico.sql` | APLICADA | 4 vistas `_canonico` |
| `012_drop_emoflow_participacion_semanal.sql` | **PROPUESTA — NO aplicada** | DROP de tabla deprecada `emoflow_participacion_semanal`; requiere 🙋 OK de Samuel. Reversible (ver cabecera: respaldo CSV previo + CREATE de reimport documentado) |
