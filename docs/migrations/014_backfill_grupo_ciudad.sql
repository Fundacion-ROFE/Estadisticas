-- Backfill de participants.grupo_ciudad para filas con ciudad conocida pero grupo_ciudad
-- NULL, usando el mapeo ciudad_canonica -> grupo_ciudad YA establecido por humanos en la
-- propia tabla (100% consistente, verificado sin ambigüedades antes de aplicar: ningún
-- ciudad_canonica mapea a más de un grupo_ciudad distinto). No se inventan códigos nuevos.
-- Aplicada vía Supabase MCP (apply_migration) el 2026-07-24.
--
-- Motivación: auditoría de coherencia de toda la DB pedida por Samuel tras el incidente de
-- normalización de ciudad (ver 013_normalizar_ciudad.sql). Se encontró que
-- v_demografia_grupo, v_curso_completion_por_ciudad y v_programa_stats_por_ciudad filtran
-- `WHERE grupo_ciudad IS NOT NULL` — cualquier participante sin grupo_ciudad queda
-- INVISIBLE en esos reportes (no aparece ni como "SIN_CIUDAD", desaparece). 531
-- participants con ciudad conocida no tenían grupo_ciudad; de esos, 246 correspondían a
-- ciudades con código ya existente (BOG/BAQ/CTG/CAL/MED/PAN) y solo les faltaba la
-- etiqueta por captura manual incompleta en la columna "Grupo" de la Sheet BD Seguimiento
-- (`sync_sociodemograficos.py`).
--
-- grupo_ciudad NO es lo mismo que ciudad_canonica — es un código operativo (JC) que a
-- veces agrupa VARIAS ciudades bajo un mismo código de país/región (ej. "UY" cubre
-- Montevideo/Paysandú/Colonia/Tacuarembó/..., "PAN" cubre Ciudad de Panamá/Arraiján/San
-- Miguelito/...). Por eso el backfill NO inventa códigos nuevos para ciudades sin código
-- previo (Santa Marta, Quibdó, Soledad, Villavicencio, etc. — 285 filas quedan sin
-- grupo_ciudad, es una decisión de negocio pendiente, no un bug).
--
-- emoflow_ingresos y todas las tablas/vistas derivadas de Emoflow (emoflow_ingresos_diario,
-- emoflow_actividad_semanal, emoflow_participacion_semanal, historial_*_ciudad) se
-- verificaron limpias (0 grupo_ciudad nulos) — Emoflow usa un dropdown cerrado de 9 áreas,
-- no texto libre, así que no sufren este problema.

WITH mapeo_canonico AS (
  SELECT DISTINCT public.ciudad_canonica(ciudad) AS clave_canonica, grupo_ciudad
  FROM public.participants
  WHERE grupo_ciudad IS NOT NULL AND ciudad IS NOT NULL
)
UPDATE public.participants p
SET grupo_ciudad = m.grupo_ciudad
FROM mapeo_canonico m
WHERE p.grupo_ciudad IS NULL
  AND p.ciudad IS NOT NULL
  AND public.ciudad_canonica(p.ciudad) = m.clave_canonica;

-- Verificado tras aplicar: 767 -> 1013 participants con grupo_ciudad (+246).
-- BOG 132->200, CTG 99->189, BAQ 131->172, CAL 93->122, MED 94->111, PAN 35->36.
-- Quedan 1906 NULL: 1621 sin ciudad en absoluto (nada que rellenar), 285 con ciudad
-- conocida pero sin código de grupo establecido (ver arriba).
