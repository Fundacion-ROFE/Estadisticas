-- ============================================================================
-- STAGED — NO APLICAR hasta el go pos-reunión (Fase 6).
-- Plan: docs/procesos/plan-coherencia-cohortes-2026-08-11.md  (Fase 3)
-- Riesgo: ALTO — TOCA EL PANEL PÚBLICO EN VIVO (Vercel leen esta vista; Netlify de baja
-- 2026-08-11, ya no es un consumidor real).
-- Requiere: 2026-08-11_a_cohorte_historico.sql aplicado primero.
-- Antes de aplicar: correr test_integridad_supabase.py y dejar la suite en verde.
-- ============================================================================
-- v_pub_cohorte coherente:
--   * cohortes CERRADAS (2019-2025)  -> desde cohorte_historico (canon oficial)
--   * cohorte EN CURSO  (2026)       -> activos = Seguimiento (en_seguimiento_jc = true);
--                                       retirados = ingresados - activos  (832 = 751 + 81)
-- Resuelve P2 (card 754 vs demografia 751) y P3 (años por matrícula).

-- Nota: v_pub_cohorte corre con privilegios del OWNER (reloptions=null, no security_invoker),
-- igual que v_pub_geografia. Por eso puede leer participants/cohorte_2026_ceds/cohorte_historico
-- (todas bloqueadas a anon) y exponer solo el agregado. NO hace falta GRANT a anon.
CREATE OR REPLACE VIEW v_pub_cohorte AS
WITH cerradas AS (
  SELECT programa::programa_type AS programa,
         cohorte::varchar        AS cohorte,
         seleccionados           AS ingresados,
         culminantes             AS activos,
         retirados,
         round(100.0 * culminantes / NULLIF(seleccionados,0), 1)::numeric(5,1) AS pct_aprobados
  FROM cohorte_historico
  WHERE ambito = 'nacional'
),
actual AS (   -- cohorte en curso: activo operativo = Seguimiento (solo JC; MR no usa la columna)
  SELECT ci.programa,
         ci.cohorte,
         ci.ingresados,
         CASE WHEN ci.programa = 'jc'
              THEN (SELECT count(*)::int FROM participants p
                      JOIN cohorte_2026_ceds c ON c.cedula = p.q10_id AND c.programa = 'jc'
                     WHERE p.en_seguimiento_jc = true)
              ELSE ci.activos END AS activos,
         ci.pct_aprobados
  FROM cohorte_ingresos ci
  WHERE ci.cohorte = '2026'
)
SELECT programa, cohorte, ingresados, activos, retirados, pct_aprobados FROM cerradas
UNION ALL
SELECT programa, cohorte, ingresados, activos,
       (ingresados - activos) AS retirados,  -- salidas = ingresados - activos (coherente por construcción)
       pct_aprobados
FROM actual;

-- ----------------------------------------------------------------------------
-- TODO Fase 3 (NO en este archivo, requiere el desglose por ciudad de cohorte_historico):
--   * v_pub_geografia: contar el universo real (unir retiros), no solo matrícula del año;
--     decidir el filtro grupo_ciudad IS NOT NULL (hoy deja caer 3 en 2026).
--   * v_activos_2026: vista canónica única = el set de Seguimiento (protocolo N), para que
--     card, demografía y geografía lean del MISMO lugar.
-- ----------------------------------------------------------------------------
