-- 047 — v_pub_retencion_ciudad (PENDIENTE DE APLICAR)
-- ============================================================================
-- Habilita la pestaña "Retención" del panel Vercel: distribuye la retención/deserción del
-- canon a lo largo de las ciudades y las rankea, para dar seguimiento a cuáles retienen mejor.
--
-- Por (programa, cohorte, grupo_ciudad):
--   * activos   = personas activas por ciudad. MISMO criterio EXACTO que v_pub_geografia (matrícula
--                 con en_seguimiento_jc IS DISTINCT FROM false) para que sume igual al canon en la
--                 cohorte viva (750 en JC 2026). Solo la cohorte VIGENTE es canon-exacta (el
--                 frontend restringe la pestaña a esActual); en cerradas el canon no tiene ciudad.
--   * retirados = retiros de esa (programa, cohorte) cuyo participante tiene esa grupo_ciudad.
--   * ingresados = activos + retirados; retencion_pct = 100*activos/ingresados (1 decimal).
--   * k-anon: si (activos+retirados) < 5 se suprime toda la fila (NULL), como el resto de vistas
--     públicas.
--
-- Verificado contra el canon (JC 2026): Σactivos=750, Σretirados=82, Σingresados=832 → 90.1%,
-- idéntico a v_pub_cohorte. Peor ciudad UY 77.9%, mejor GYL 98.8%.
--
-- El frontend (repo comunicaciones-ai/Panel-De-Datos, page.tsx 'use client' + fetch) ya la lee
-- EN VIVO con leerSeguro() — mientras esta vista no exista, la pestaña muestra "en construcción";
-- al aplicarla se enciende sola sin redeploy.
--
-- ⚠ CÓMO APLICAR: no hay MCP de Supabase ni psql en la sesión que la generó. Pegar este bloque en
--   el editor SQL de Supabase (proyecto panel-datos-rofe / kbxptoowtnteflhrfwid) y ejecutarlo.
-- ============================================================================

CREATE OR REPLACE VIEW public.v_pub_retencion_ciudad AS
 WITH activos AS (
         SELECT c.programa,
                c.cohorte::text AS cohorte,
                p.grupo_ciudad,
                count(DISTINCT p.id) AS n
           FROM participants p
           JOIN enrollments e ON e.participant_id = p.id
           JOIN courses c ON c.id = e.course_id
          WHERE p.grupo_ciudad IS NOT NULL
            AND p.en_seguimiento_jc IS DISTINCT FROM false
          GROUP BY c.programa, c.cohorte, p.grupo_ciudad
        ), retirados AS (
         SELECT r.programa,
                r.cohorte::text AS cohorte,
                p.grupo_ciudad,
                count(DISTINCT r.participant_id) AS n
           FROM retiros r
           JOIN participants p ON p.id = r.participant_id
          WHERE p.grupo_ciudad IS NOT NULL
            AND r.participant_id IS NOT NULL
            AND r.cohorte <> 'no_cohorte'
          GROUP BY r.programa, r.cohorte, p.grupo_ciudad
        ), j AS (
         SELECT COALESCE(a.programa, rt.programa) AS programa,
                COALESCE(a.cohorte, rt.cohorte) AS cohorte,
                COALESCE(a.grupo_ciudad, rt.grupo_ciudad) AS grupo_ciudad,
                COALESCE(a.n, 0) AS activos,
                COALESCE(rt.n, 0) AS retirados
           FROM activos a
           FULL OUTER JOIN retirados rt
             ON a.programa = rt.programa AND a.cohorte = rt.cohorte AND a.grupo_ciudad = rt.grupo_ciudad
        )
 SELECT programa, cohorte, grupo_ciudad,
        CASE WHEN (activos + retirados) < 5 THEN NULL::bigint ELSE activos END AS activos,
        CASE WHEN (activos + retirados) < 5 THEN NULL::bigint ELSE retirados END AS retirados,
        CASE WHEN (activos + retirados) < 5 THEN NULL::bigint ELSE (activos + retirados) END AS ingresados,
        CASE WHEN (activos + retirados) < 5 THEN NULL::numeric
             ELSE round(100.0 * activos / NULLIF(activos + retirados, 0), 1) END AS retencion_pct
   FROM j
  ORDER BY programa, cohorte, grupo_ciudad;

GRANT SELECT ON public.v_pub_retencion_ciudad TO anon;
