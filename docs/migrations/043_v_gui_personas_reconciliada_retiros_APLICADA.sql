-- 043 — v_gui_personas reconciliada con retiros (APLICADA 2026-08-12 vía MCP Supabase)
-- ============================================================================
-- Contexto: la lista persona-por-persona del panel GUI se armaba solo desde
-- `enrollments` (matrícula). Q10 purga del Consolidado a los inhabilitados
-- (retirados), así que las cohortes cerradas subcontaban: JC 2024 mostraba 470
-- individuos en vez de los 608/609 reales. Los 138 faltantes SÍ existen a nivel
-- persona (identidad en `participants` + registro en `retiros`), pero sin
-- `enrollments` se caían de la vista.
--
-- Fix: se agrega una 3ª rama al CTE `base` que recupera a los retirados de
-- cohortes cerradas (excepto 2026, cuyo activo = Seguimiento) cuyo participante
-- no está ya presente vía enrollment ni vía cohorte_2026_ceds.
-- cursos_matriculados/aprobados/avance quedan NULL: ese dato Q10 no lo conserva.
--
-- Resultado verificado (JC): 2023=488, 2024=609 (470 con avance + 139 sin), 2025=733, 2026=832.
-- Suite test_integridad_supabase.py: 53/53 PASS (v_gui_personas sigue anon-bloqueada).
-- ============================================================================
CREATE OR REPLACE VIEW public.v_gui_personas AS
 WITH enroll_resumen AS (
         SELECT e.participant_id, c.programa, c.cohorte,
            count(*) AS cursos_matriculados,
            sum((e.porcentaje_avance > 80)::integer) AS cursos_aprobados,
            round(avg(e.porcentaje_avance), 1) AS avance_promedio
           FROM enrollments e JOIN courses c ON c.id = e.course_id
          GROUP BY e.participant_id, c.programa, c.cohorte
        ), mc_agg AS (
         SELECT mr_microcreditos.cedula,
            count(*) AS microcreditos_count,
            string_agg(DISTINCT mr_microcreditos.tipo_credito::text, ', '::text) AS tipos_credito
           FROM mr_microcreditos GROUP BY mr_microcreditos.cedula
        ), base AS (
         -- 1) Personas con inscripción (avance real desde Q10)
         SELECT p_1.id AS participant_id, p_1.q10_id AS cedula, er.programa, er.cohorte,
            er.cursos_matriculados, er.cursos_aprobados, er.avance_promedio
           FROM participants p_1 JOIN enroll_resumen er ON er.participant_id = p_1.id
        UNION ALL
         -- 2) Cohorte 2026 sin inscripción todavía (desde el canon de cédulas)
         SELECT p_1.id, p_1.q10_id, cq_1.programa, cq_1.cohorte, NULL::bigint, NULL::bigint, NULL::numeric
           FROM cohorte_2026_ceds cq_1 JOIN participants p_1 ON p_1.q10_id::text = cq_1.cedula::text
          WHERE NOT (EXISTS ( SELECT 1 FROM enroll_resumen er2
                  WHERE er2.participant_id = p_1.id AND er2.programa = cq_1.programa AND er2.cohorte::text = cq_1.cohorte::text))
        UNION ALL
         -- 3) RECONCILIACIÓN: retirados de cohortes cerradas cuyo avance Q10 purgó del Consolidado.
         SELECT p_1.id, p_1.q10_id, r0.programa, r0.cohorte, NULL::bigint, NULL::bigint, NULL::numeric
           FROM ( SELECT DISTINCT rr.participant_id, rr.programa, rr.cohorte
                    FROM retiros rr WHERE rr.participant_id IS NOT NULL AND rr.cohorte <> 'no_cohorte' ) r0
             JOIN participants p_1 ON p_1.id = r0.participant_id
          WHERE NOT (EXISTS ( SELECT 1 FROM enroll_resumen er3
                  WHERE er3.participant_id = p_1.id AND er3.programa = r0.programa AND er3.cohorte::text = r0.cohorte::text))
            AND NOT (EXISTS ( SELECT 1 FROM cohorte_2026_ceds cq2
                  WHERE cq2.cedula::text = p_1.q10_id::text AND cq2.programa = r0.programa AND cq2.cohorte::text = r0.cohorte::text))
        )
 SELECT b.participant_id, b.cedula, p.nombre, p.email, p.genero, p.edad, b.programa, b.cohorte,
    p.ciudad AS municipio, p.grupo_ciudad, b.cursos_matriculados, b.cursos_aprobados, b.avance_promedio,
    b.avance_promedio > 80::numeric AS al_dia,
    r.fecha_retiro, r.motivo AS motivo_retiro, r.cohorte_registrado AS retiro_cohorte_registrado,
        CASE WHEN b.programa = 'jc'::programa_type THEN COALESCE(cq.retirado, r.motivo IS NOT NULL)
             ELSE r.motivo IS NOT NULL END AS retirado,
    p.empresa_patrocinadora, em.ingresos AS emoflow_ingresos, em.ultimo_ingreso AS emoflow_ultimo_ingreso,
    p.estrato, p.estado_civil, p.nivel_estudio, p.tipo_vivienda,
    COALESCE(mc.microcreditos_count, 0::bigint) > 0 AS tiene_microcredito, mc.tipos_credito AS microcredito_tipos,
    p.en_seguimiento_jc, p.fecha_verificacion_seguimiento
   FROM base b
     JOIN participants p ON p.id = b.participant_id
     LEFT JOIN cohorte_2026_ceds cq ON cq.cedula::text = b.cedula::text AND cq.programa = b.programa AND cq.cohorte::text = b.cohorte::text
     LEFT JOIN LATERAL ( SELECT r2.fecha_retiro, r2.motivo, r2.cohorte AS cohorte_registrado
           FROM retiros r2
          WHERE r2.programa = b.programa AND (r2.participant_id = p.id OR r2.participant_id IS NULL AND r2.cedula::text = p.q10_id::text)
          ORDER BY r2.fecha_retiro DESC NULLS LAST, r2.updated_at DESC LIMIT 1) r ON true
     LEFT JOIN emoflow_ingresos em ON lower(btrim(em.email::text)) = lower(btrim(p.email::text))
     LEFT JOIN mc_agg mc ON mc.cedula::text = p.q10_id::text;
