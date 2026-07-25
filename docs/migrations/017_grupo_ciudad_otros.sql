-- Unifica el resto de municipios sin hub cercano (Santa Marta, Quibdó, Villavicencio,
-- Cúcuta, Carmen del Darién, y ~115 más, la mayoría con 1-3 personas) bajo un único
-- grupo_ciudad = 'OTROS' — decisión de Samuel 2026-07-24: para análisis agregados
-- (dashboards por grupo) no vale la pena un código por cada municipio con 1-2 personas;
-- si se necesita analizar alguno individualmente, `ciudad`/`ciudad_norm` (sin tocar)
-- sigue teniendo el municipio real, así que no se pierde información, solo se resume.
-- Aplicada vía Supabase MCP (apply_migration).
--
-- EXCLUYE 5 filas con basura real en el campo `ciudad` (ver
-- "Gotcha: basura en ciudad (source_system=q10)" en docs/convenciones.md) — a esas NO se
-- les asigna 'OTROS' porque no se conoce su ciudad real (sería inventar que "Colombia" o
-- "hijos" es un municipio válido). Quedan NULL a propósito.

UPDATE public.participants
SET grupo_ciudad = 'OTROS'
WHERE grupo_ciudad IS NULL
  AND ciudad IS NOT NULL
  AND ciudad_norm NOT IN ('MENOR A 1 SMLV', 'COLOMBIA', 'HIJOS', 'GALAPA SOY UNA MUJER');

-- Verificado tras aplicar: grupo_ciudad='OTROS' -> 222 filas. Quedan 5 NULL con ciudad
-- conocida (las excluidas por basura) + 1.621 NULL sin ciudad en absoluto (sin dato).
