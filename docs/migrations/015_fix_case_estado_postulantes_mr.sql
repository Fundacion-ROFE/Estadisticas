-- Variante de mayúsculas encontrada en la auditoría de coherencia de toda la DB 2026-07-24:
-- postulantes_mr.estado tenía 'retirada' (3 filas, minúscula) vs 'Retirada' (30 filas) —
-- mismo significado, fragmentaba cualquier conteo/reporte por estado. Se unifica a la
-- grafía mayoritaria. Aplicada vía Supabase MCP (apply_migration) el 2026-07-24.
--
-- Resto de columnas de texto libre revisadas en la misma auditoría (participants.genero,
-- postulantes_mr.genero, participants.source_system, postulantes_jc.fuente/rol,
-- postulantes_mr.fuente_pestana): vocabularios controlados por script, sin variantes.
UPDATE public.postulantes_mr SET estado = 'Retirada' WHERE estado = 'retirada';
