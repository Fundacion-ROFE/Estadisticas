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

## Divergencia de numeración repo ↔ Supabase (detectada 2026-07-30)

El numerado de los archivos en este directorio y el log real de migraciones aplicadas en
Supabase (`mcp__Supabase__list_migrations`) son **dos secuencias distintas que divergieron el
2026-07-28**: varias migraciones quedaron aplicadas en Supabase con números (028-032) que en el
repo corresponden a contenido distinto (022-025), y el 29-jul y 30-jul varias sesiones sin
visibilidad entre sí reusaron los números 026-029 para migraciones nuevas — llegaron a existir
dos archivos `028` distintos el mismo día. No rompe nada técnico (Supabase versiona por
timestamp, el número de archivo es solo una etiqueta), pero deja el rastro de auditoría
ambiguo — el mismo tipo de trampa que el hueco del `004` de abajo.

**Regla:** antes de crear una migración nueva, el próximo número es el **máximo entre las dos
secuencias + 1** — verificar con `ls docs/migrations/` **y** `list_migrations` del MCP de
Supabase, nunca asumir que el repo solo basta. El 2026-07-30 esto dio **033** (repo llegaba a
029, el log de Supabase a 032). **Nunca renombrar una migración ya aplicada** para "corregir" su
número — el archivo miente sobre su número, pero renombrarlo mentiría sobre el orden real de
aplicación, que es peor.

## Estado por archivo (2026-07-24, desactualizada desde — ver migraciones 018 en adelante en [[supabase-estructura]])

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
