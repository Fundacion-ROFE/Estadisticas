-- v_frescura: sube umbral 6h -> 12h para cohorte_ingresos, aprobacion_cursos y
-- retiros (sync_retiros). Bloque de "arreglar alertas de Telegram" pedido por Lina
-- en Cowork 2026-07-30, tras auditoria del canal (8 alertas falsas/dia).
--
-- Diagnostico medido en vivo (2026-07-30, media tarde): los 3 procesos aparecian
-- vencido=true a las 7.0h de antiguedad contra un umbral de 6h, con el sync
-- funcionando perfectamente (q10-sync-supabase corrio a las 07:31 sin fallar).
--
-- Causa raiz: q10-sync-supabase corre con cron 30 17,19,21,23,1,3,5,7 * * * (ventana
-- nocturna). Entre la ultima corrida del dia (07:30) y la primera de la tarde (17:30)
-- hay un hueco de DISENO de 10h. Un umbral de 6h < 10h dispara todos los dias de
-- 13:30 a 17:30, y alerta-frescura-vencida corre cada 30 min => 8 mensajes falsos/dia.
--
-- Mismo patron ya corregido una vez: la migracion 021 subio emoflow_ingresos_diario
-- de 6h a 30h por esta misma razon (ver comentario de 019_v_frescura.sql). Quedo sin
-- aplicar a estos 3 procesos, que comparten el mismo cron de origen.
--
-- Por que 12h y no otro numero:
--   - a las 17:29 la antiguedad maxima posible es 9.98h (10h de hueco - 1 minuto) =>
--     12h nunca dispara por el hueco de diseno. Cero falsas alarmas.
--   - si la corrida de las 17:30 falla, a las 19:30 la antiguedad llega a 12h =>
--     dispara. Detecta una falla real en ~2h (una corrida perdida).
--   - NO se sube a 30h (como emoflow_ingresos_diario): esos 3 procesos corren 8 veces
--     por ventana nocturna (cadencia real 2h), y 30h dejaria pasar una noche entera de
--     fallas sin avisar. Formula general: umbral > hueco maximo entre corridas
--     consecutivas + una corrida de tolerancia.
--
-- Verificado tras aplicar (2026-07-30): 0 procesos vencidos a media tarde
-- (cohorte_ingresos/aprobacion_cursos/retiros en 7.0h, umbral 12h); un proceso
-- simulado a 13h de antiguedad sigue disparando vencido=true (detecta corrida
-- real perdida).
--
-- No se toca 019/020/021/026 (viejas) — CREATE OR REPLACE de la vista completa, unica
-- forma de cambiar un literal dentro del SELECT.
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
  SELECT 'cohorte_ingresos', MAX(updated_at AT TIME ZONE 'UTC'), 12
  FROM cohorte_ingresos
  UNION ALL
  SELECT 'aprobacion_cursos', MAX(updated_at AT TIME ZONE 'UTC'), 12
  FROM aprobacion_cursos
  UNION ALL
  SELECT 'emoflow_ingresos (sync_emoflow_api)', MAX(fecha_corte)::timestamptz, 30
  FROM emoflow_ingresos
  UNION ALL
  SELECT 'emoflow_ingresos_diario', MAX(updated_at AT TIME ZONE 'UTC'), 30
  FROM emoflow_ingresos_diario
  UNION ALL
  SELECT 'retiros (sync_retiros)', MAX(updated_at AT TIME ZONE 'UTC'), 12
  FROM retiros
  UNION ALL
  SELECT 'asistencia_promedio (zoom)', MAX(actualizado_en), 30
  FROM asistencia_promedio
  UNION ALL
  SELECT 'historial_cursos (snapshot diario)', MAX(fecha)::timestamptz, 30
  FROM historial_cursos
) datos_por_proceso;

COMMENT ON VIEW v_frescura IS 'Antiguedad en horas del ultimo dato de cada proceso + umbral/vencido. cohorte_ingresos/aprobacion_cursos/retiros en 12h desde 2026-07-30 (migracion 029) para no disparar en el hueco de diseno de q10-sync-supabase. Ver docs/procesos/plan-testing-produccion-2026-07-29.md Bloque 1 y docs/convenciones.md.';

GRANT SELECT ON v_frescura TO anon;
