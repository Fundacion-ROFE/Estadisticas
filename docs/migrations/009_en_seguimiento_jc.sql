-- 009 — en_seguimiento_jc: alerta operativa de retiro temprano (JC), no variable de análisis
-- Pedido 2026-07-23: el equipo borra primero de la pestaña "Seguimiento" del Sheet BD
-- Seguimiento de Monitorias cuando alguien se retira, y solo MESES después lo refleja en Q10.
-- Q10 queda desactualizado como señal de "¿sigue activo hoy?" — el Sheet es más reciente.
--
-- Alcance: SOLO Jóvenes creaTIvos. MR se descarta explícitamente (decisión de Samuel:
-- "MR tiene problemas de gestión respecto a eso" — el mismo patrón de disciplina de borrado
-- no es confiable ahí, así que esta columna sería ruido, no señal, para MR).
--
-- Regla de interpretación (importante, no es un booleano de retiro confirmado):
--   en_seguimiento_jc = true  → aparece en la pestaña Seguimiento hoy. Normal.
--   en_seguimiento_jc = false → NO aparece en Seguimiento pero Q10 lo sigue marcando activo.
--     Es una ALERTA DE RETIRO PENDIENTE DE CONFIRMAR, no un hecho. Dos desenlaces posibles:
--       (a) Q10 eventualmente se actualiza y confirma el retiro → en ese punto el estado real
--           de matrícula (enrollments.estado) ya lo captura, esta columna cumplió su función.
--       (b) Reaparece en Seguimiento (falsa alarma / error de captura) → vuelve a true.
--   MIENTRAS ESTÁ EN DUDA (false + Q10 sigue activo): NO usar como variable de resultado en
--   ningún análisis estadístico (ej. uso Emoflow ↔ retención) — es una señal operativa para
--   que el equipo verifique, no un dato confirmado. Ver docs/procesos/supabase-estructura.md.

ALTER TABLE public.participants
  ADD COLUMN IF NOT EXISTS en_seguimiento_jc BOOLEAN,
  ADD COLUMN IF NOT EXISTS fecha_verificacion_seguimiento DATE;

COMMENT ON COLUMN public.participants.en_seguimiento_jc IS
  'Presencia en la pestaña "Seguimiento" del Sheet BD Seguimiento de Monitorias JC (sync_sociodemograficos.py, credencial Service Account trazable ya usada por el resto del pipeline JC). SOLO se calcula para participantes de programa=jc (NULL para MR, decisión explícita). false = alerta de retiro pendiente de confirmar en Q10, NO un retiro confirmado — no usar en análisis estadístico hasta que el estado real de matrícula (enrollments.estado) lo refleje.';

COMMENT ON COLUMN public.participants.fecha_verificacion_seguimiento IS
  'Fecha de la última corrida de sync_sociodemograficos.py que verificó la presencia/ausencia en la pestaña Seguimiento — trazabilidad de cuándo se confirmó este estado.';
