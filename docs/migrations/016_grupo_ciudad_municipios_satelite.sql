-- Fusión de municipios satélite (área metropolitana/conurbación) al grupo_ciudad de la
-- ciudad hub más cercana — confirmado por Samuel 2026-07-24 tras la auditoría de
-- coherencia de toda la DB (ver docs/migrations/014_backfill_grupo_ciudad.sql y
-- claude_sessions.md). NO se toca `ciudad`/`ciudad_canonica` (Soledad sigue siendo
-- Soledad, no es la misma ciudad que Barranquilla) — solo se asigna el código operativo
-- de grupo, asumiendo que comparte monitor/equipo regional con la ciudad hub. Aplicada
-- vía Supabase MCP (apply_migration).
--
-- No se tocaron los ~120 municipios restantes sin hub cercano (Santa Marta, Quibdó,
-- Villavicencio, Cúcuta, Carmen del Darién, etc. — mayoría con 1-3 personas, algunos con
-- basura evidente en el campo ciudad, ej. "MENOR A 1 SMLV", "COLOMBIA" — parecen
-- respuestas de otra pregunta del formulario coladas en esa columna, revisar aparte):
-- asignarles un código inventaría presencia operativa que no se puede confirmar desde
-- los datos.

UPDATE public.participants
SET grupo_ciudad = 'BAQ'
WHERE grupo_ciudad IS NULL AND ciudad_norm = 'SOLEDAD';

UPDATE public.participants
SET grupo_ciudad = 'CAL'
WHERE grupo_ciudad IS NULL AND ciudad_norm IN ('JAMUNDI', 'PALMIRA', 'YUMBO', 'CANDELARIA', 'DAGUA');

UPDATE public.participants
SET grupo_ciudad = 'MED'
WHERE grupo_ciudad IS NULL AND ciudad_norm IN ('BELLO', 'ITAGUI');

UPDATE public.participants
SET grupo_ciudad = 'BOG'
WHERE grupo_ciudad IS NULL AND ciudad_norm IN ('SOACHA', 'FUNZA', 'MADRID', 'FACATATIVA', 'CAJICA', 'CHIA', 'GUADUAS', 'TOCAIMA');

-- Verificado tras aplicar: BOG 200->214 (+14), BAQ 172->197 (+25), CAL 122->137 (+15),
-- MED 111->115 (+4). Total +58. NULL 1906->1848.
