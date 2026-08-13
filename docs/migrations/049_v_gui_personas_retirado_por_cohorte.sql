-- 049 — v_gui_personas: `retirado` (JC) reconoce el retiro de la MISMA cohorte
-- ============================================================================
-- Bug (reportado 2026-08-13): 4 personas de JC 2026 (Taliana Duran 1109668853, Sharon Jiménez
-- 1106518644, Abelardo Villar 1041772751, Margareth Meza 1007688398) salieron de Seguimiento y
-- SÍ están en `retiros` (fuente sheet_retirados_q10, retiro voluntario 6-10 ago), pero
-- v_gui_personas las mostraba `retirado=False` → la pestaña "Datos desactualizados Q10" las
-- marcaba como "Q10 sin marcar retiro" (falso) e inconsistencia con el canon (v_pub_cohorte ya
-- las cuenta en los 82 retirados de 2026).
--
-- Causa: la 043 hacía `retirado = COALESCE(cq.retirado, r.motivo IS NOT NULL)`. `cq.retirado`
-- viene de `cohorte_2026_ceds` (lista canon de cédulas cargada antes de estos retiros → marca a
-- los 4 como activos). Como cq.retirado NO es NULL, el COALESCE lo prefiere e IGNORA el retiro real.
--
-- Fix: retirado(JC) = COALESCE(cq.retirado, false) OR (existe retiro de la MISMA programa+cohorte).
-- Se exige misma cohorte a propósito, para NO reintroducir el falso positivo de reingreso
-- (56603709 Luca Fontana: retiro 2024 + reingreso ACTIVO 2026 en Seguimiento; su retiro es de 2024,
-- no de 2026 → su fila 2026 sigue retirado=False). Verificado contra los datos: los 4 tienen
-- retiros_cohorte=2026, Luca tiene 2024.
--
-- MR (rama ELSE) sin cambios: retiros.cohorte de MR no es confiable (ver comentario retiro_registrado),
-- se mantiene `r.motivo IS NOT NULL` (cualquier retiro).
--
-- ⚠ CÓMO APLICAR: no hay MCP de Supabase ni psql en la sesión. Pegar en el editor SQL de Supabase.
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
         SELECT p_1.id AS participant_id, p_1.q10_id AS cedula, er.programa, er.cohorte,
            er.cursos_matriculados, er.cursos_aprobados, er.avance_promedio
           FROM participants p_1 JOIN enroll_resumen er ON er.participant_id = p_1.id
        UNION ALL
         SELECT p_1.id, p_1.q10_id, cq_1.programa, cq_1.cohorte, NULL::bigint, NULL::bigint, NULL::numeric
           FROM cohorte_2026_ceds cq_1 JOIN participants p_1 ON p_1.q10_id::text = cq_1.cedula::text
          WHERE NOT (EXISTS ( SELECT 1 FROM enroll_resumen er2
                  WHERE er2.participant_id = p_1.id AND er2.programa = cq_1.programa AND er2.cohorte::text = cq_1.cohorte::text))
        UNION ALL
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
        CASE WHEN b.programa = 'jc'::programa_type THEN
                 COALESCE(cq.retirado, false)
                 OR EXISTS ( SELECT 1 FROM retiros rj
                       WHERE rj.programa = b.programa
                         AND (rj.participant_id = b.participant_id
                              OR (rj.participant_id IS NULL AND rj.cedula::text = b.cedula::text))
                         AND rj.cohorte::text = b.cohorte::text)
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
