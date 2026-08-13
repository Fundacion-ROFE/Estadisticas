-- 048 — v_frescura: umbral 12h -> 16h para cohorte_ingresos / aprobacion_cursos / retiros
-- ============================================================================
-- Re-calibración a la lógica REAL del cron (verificado en n8n vivo 2026-08-13, no en el doc,
-- que estaba desactualizado). El workflow q10-sync-supabase corre con cron:
--     30 17,21,1,5 * * *   ->  17:30, 21:30, 01:30, 05:30  (cada 4h)
-- NO el `30 17,19,21,23,1,3,5,7` (cada 2h) que asumía la migración 029 / CLAUDE.md.
--
-- Huecos entre corridas consecutivas: 4h, 4h, 4h y **05:30 -> 17:30 = 12h** (hueco diurno de
-- diseño). Fórmula de 029: umbral > hueco_maximo + una_corrida_de_tolerancia.
--   hueco_maximo real = 12h   (antes se creía 10h)
--   una_corrida        = 4h    (cadencia real, antes se creía 2h)
--   => umbral = 12 + 4 = 16h
--
-- Por qué 12h (029) quedó MAL tras conocer el cron real: a las 17:29 la antigüedad real llega a
-- ~11.98h; con umbral 12h el margen es ~0 -> cualquier corrida de 17:30 que arranque tarde dispara
-- falsa alarma. Con 16h hay 4h de margen (cero falsas alarmas en el hueco de diseño) y aún detecta
-- una caída real de 2 corridas consecutivas (~21:30). Nota: este cálculo es sobre la antigüedad
-- REAL — depende del fix de 2026-08-13 que hace que updated_at se escriba en UTC (antes salía
-- inflada +5h). Ver runbooks/recuperacion-frescura.md y migración 029.
--
-- No se tocan los umbrales de 30h (procesos 1x/día) ni el resto de la vista.
--
-- ⚠ CÓMO APLICAR: no hay MCP de Supabase ni psql en la sesión. Pegar en el editor SQL de Supabase.
-- ============================================================================

CREATE OR REPLACE VIEW v_frescura AS
SELECT proceso, ultimo_dato,
       ROUND(EXTRACT(EPOCH FROM (now() - ultimo_dato)) / 3600.0, 1) AS horas_desde_ultimo,
       umbral_horas,
       (EXTRACT(EPOCH FROM (now() - ultimo_dato)) / 3600.0) > umbral_horas AS vencido
FROM (
  SELECT 'q10_sync (participants_snapshots)' AS proceso,
         MAX(snapshot_date)::timestamptz AS ultimo_dato, 30 AS umbral_horas
  FROM participants_snapshots
  UNION ALL
  SELECT 'cohorte_ingresos', MAX(updated_at AT TIME ZONE 'UTC'), 16
  FROM cohorte_ingresos
  UNION ALL
  SELECT 'aprobacion_cursos', MAX(updated_at AT TIME ZONE 'UTC'), 16
  FROM aprobacion_cursos
  UNION ALL
  SELECT 'emoflow_ingresos (sync_emoflow_api)', MAX(fecha_corte)::timestamptz, 30
  FROM emoflow_ingresos
  UNION ALL
  SELECT 'emoflow_ingresos_diario', MAX(updated_at AT TIME ZONE 'UTC'), 30
  FROM emoflow_ingresos_diario
  UNION ALL
  SELECT 'retiros (sync_retiros)', MAX(updated_at AT TIME ZONE 'UTC'), 16
  FROM retiros
  UNION ALL
  SELECT 'asistencia_promedio (zoom)', MAX(actualizado_en), 30
  FROM asistencia_promedio
  UNION ALL
  SELECT 'historial_cursos (snapshot diario)', MAX(fecha)::timestamptz, 30
  FROM historial_cursos
) datos_por_proceso;

COMMENT ON VIEW v_frescura IS 'Antiguedad en horas del ultimo dato de cada proceso + umbral/vencido. cohorte_ingresos/aprobacion_cursos/retiros en 16h desde 2026-08-13 (migracion 048): cron real q10-sync-supabase = 30 17,21,1,5 (cada 4h, hueco diurno 12h) + 4h tolerancia. Frescura real depende del fix updated_at-en-UTC (2026-08-13). Ver runbooks/recuperacion-frescura.md.';

GRANT SELECT ON v_frescura TO anon;
