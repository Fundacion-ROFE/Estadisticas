-- 044 — v_pub_demografia + v_pub_geografia reconciliadas (APLICADA 2026-08-12 vía MCP Supabase)
-- ============================================================================
-- Contexto: las dos superficies públicas por cohorte del panel Vercel armaban su
-- base solo desde `participants JOIN enrollments` (matrícula), así que 2024 JC
-- reflejaba 470 en vez del universo real 608 (le faltaban los 139 retirados que
-- Q10 purgó del Consolidado). El KPI de cohorte (v_pub_cohorte) ya era correcto (608).
--
-- Fix NO REGRESIVO:
--   * Se agregan los retirados de cohortes CERRADAS (excluye 2026, cuyo activo =
--     Seguimiento) como personas con avance NULL: cuentan en `personas` pero el
--     promedio de avance se pondera solo por quienes SÍ tienen avance.
--   * Municipios/cohortes sin retirados recuperados quedan idénticos.
--
-- Resultado verificado (JC): geografía 2024 470→607 (−1 = persona con grupo_ciudad NULL,
-- no ubicable); demografía 2024 recupera retirados con género/edad conocidos (resto bajo
-- supresión n<5). 2023/2025/2026 sin cambios. Suite test_integridad_supabase.py: 53/53 PASS.
-- El frontend (repo comunicaciones-ai/Panel-De-Datos) lee estas vistas EN VIVO
-- (page.tsx 'use client' + fetch), así que el cambio aparece al recargar, sin redeploy.
-- ============================================================================

CREATE OR REPLACE VIEW public.v_pub_geografia AS
 WITH persona_curso AS (
         SELECT p.id AS participant_id, c.programa, c.cohorte, p.grupo_ciudad, p.ciudad_norm, p.ciudad,
            avg(e.porcentaje_avance) AS avance_persona
           FROM participants p JOIN enrollments e ON e.participant_id = p.id JOIN courses c ON c.id = e.course_id
          WHERE p.grupo_ciudad IS NOT NULL AND p.en_seguimiento_jc IS DISTINCT FROM false
          GROUP BY p.id, c.programa, c.cohorte, p.grupo_ciudad, p.ciudad_norm, p.ciudad
        UNION ALL
         SELECT p.id, r0.programa, r0.cohorte, p.grupo_ciudad, p.ciudad_norm, p.ciudad, NULL::numeric AS avance_persona
           FROM ( SELECT DISTINCT rr.participant_id, rr.programa, rr.cohorte
                    FROM retiros rr WHERE rr.participant_id IS NOT NULL AND rr.cohorte <> 'no_cohorte' AND rr.cohorte <> '2026' ) r0
             JOIN participants p ON p.id = r0.participant_id
          WHERE p.grupo_ciudad IS NOT NULL
            AND NOT (EXISTS ( SELECT 1 FROM enrollments e JOIN courses c ON c.id = e.course_id
                     WHERE e.participant_id = p.id AND c.programa = r0.programa AND c.cohorte::text = r0.cohorte::text))
        ), base AS (
         SELECT pc.programa, pc.cohorte, pc.grupo_ciudad,
            COALESCE(ca.ciudad_canonica, pc.ciudad_norm) AS municipio_clave,
            mode() WITHIN GROUP (ORDER BY pc.ciudad) AS municipio_nombre,
            count(*) AS personas,
            count(*) FILTER (WHERE pc.avance_persona IS NOT NULL) AS personas_avance,
            avg(pc.avance_persona) AS avance_promedio,
            count(*) FILTER (WHERE pc.avance_persona > 80::numeric) AS aprobados
           FROM persona_curso pc LEFT JOIN ciudad_alias ca ON ca.clave_norm = pc.ciudad_norm
          GROUP BY pc.programa, pc.cohorte, pc.grupo_ciudad, (COALESCE(ca.ciudad_canonica, pc.ciudad_norm))
        ), etiquetado AS (
         SELECT base.programa, base.cohorte, base.grupo_ciudad, base.municipio_clave, base.municipio_nombre,
            base.personas, base.personas_avance, base.avance_promedio, base.aprobados,
                CASE WHEN base.personas < umbral_supresion_municipio() THEN 'Área metropolitana'::character varying
                     ELSE base.municipio_nombre END AS municipio_pub
           FROM base
        )
 SELECT programa, cohorte, grupo_ciudad, municipio_pub AS municipio,
    sum(personas) AS personas,
    round(sum(avance_promedio * personas_avance::numeric) / NULLIF(sum(personas_avance), 0)::numeric, 1) AS avance_promedio,
    sum(aprobados) AS aprobados
   FROM etiquetado
  GROUP BY programa, cohorte, grupo_ciudad, municipio_pub
  ORDER BY programa, cohorte, grupo_ciudad, municipio_pub;

CREATE OR REPLACE VIEW public.v_pub_demografia AS
 WITH base AS (
         SELECT DISTINCT p.id AS participant_id, p.q10_id, p.genero, p.edad, p.estrato,
            p.estado_civil, p.nivel_estudio, p.tipo_vivienda, p.grupo_ciudad, c.programa, c.cohorte
           FROM participants p JOIN enrollments e ON e.participant_id = p.id JOIN courses c ON c.id = e.course_id
        UNION ALL
         SELECT DISTINCT p.id, p.q10_id, p.genero, p.edad, p.estrato,
            p.estado_civil, p.nivel_estudio, p.tipo_vivienda, p.grupo_ciudad, r0.programa, r0.cohorte
           FROM ( SELECT DISTINCT rr.participant_id, rr.programa, rr.cohorte
                    FROM retiros rr WHERE rr.participant_id IS NOT NULL AND rr.cohorte <> 'no_cohorte' AND rr.cohorte <> '2026' ) r0
             JOIN participants p ON p.id = r0.participant_id
          WHERE NOT (EXISTS ( SELECT 1 FROM enrollments e JOIN courses c ON c.id = e.course_id
                   WHERE e.participant_id = p.id AND c.programa = r0.programa AND c.cohorte::text = r0.cohorte::text))
        ), clasificado AS (
         SELECT b.participant_id, b.q10_id, b.genero, b.edad, b.estrato, b.estado_civil,
            b.nivel_estudio, b.tipo_vivienda, b.grupo_ciudad, b.programa, b.cohorte,
                CASE WHEN retiro_registrado(b.participant_id, b.q10_id, b.programa) THEN 'retirado'::text
                     ELSE 'activo'::text END AS estado,
                CASE
                    WHEN b.programa = 'jc'::programa_type THEN
                    CASE WHEN b.edad IS NULL THEN NULL::text
                         WHEN b.edad < 15 THEN '< 15'::text
                         WHEN b.edad >= 15 AND b.edad <= 17 THEN '15-17'::text
                         WHEN b.edad >= 18 AND b.edad <= 20 THEN '18-20'::text
                         WHEN b.edad >= 21 AND b.edad <= 24 THEN '21-24'::text
                         ELSE '25+'::text END
                    WHEN b.programa = 'mr'::programa_type THEN
                    CASE WHEN b.edad IS NULL THEN NULL::text
                         WHEN b.edad < 26 THEN '18-25'::text
                         WHEN b.edad < 36 THEN '26-35'::text
                         WHEN b.edad < 46 THEN '36-45'::text
                         WHEN b.edad < 61 THEN '46-60'::text
                         ELSE '60+'::text END
                    ELSE NULL::text END AS edad_rango
           FROM base b
        ), dims AS (
         SELECT clasificado.programa, clasificado.cohorte, clasificado.estado, clasificado.grupo_ciudad,
            'genero'::text AS dimension, clasificado.genero AS categoria FROM clasificado WHERE clasificado.genero IS NOT NULL
        UNION ALL
         SELECT clasificado.programa, clasificado.cohorte, clasificado.estado, clasificado.grupo_ciudad,
            'edad_rango'::text, clasificado.edad_rango FROM clasificado WHERE clasificado.edad_rango IS NOT NULL
        UNION ALL
         SELECT clasificado.programa, clasificado.cohorte, clasificado.estado, clasificado.grupo_ciudad,
            'estrato'::text, clasificado.estrato::text FROM clasificado WHERE clasificado.estrato IS NOT NULL
        UNION ALL
         SELECT clasificado.programa, clasificado.cohorte, clasificado.estado, clasificado.grupo_ciudad,
            'estado_civil'::text, clasificado.estado_civil::text FROM clasificado WHERE clasificado.estado_civil IS NOT NULL
        UNION ALL
         SELECT clasificado.programa, clasificado.cohorte, clasificado.estado, clasificado.grupo_ciudad,
            'nivel_estudio'::text, clasificado.nivel_estudio::text FROM clasificado WHERE clasificado.nivel_estudio IS NOT NULL
        UNION ALL
         SELECT clasificado.programa, clasificado.cohorte, clasificado.estado, clasificado.grupo_ciudad,
            'tipo_vivienda'::text, clasificado.tipo_vivienda::text FROM clasificado WHERE clasificado.tipo_vivienda IS NOT NULL
        ), agg AS (
         SELECT dims.programa, dims.cohorte, dims.estado, dims.grupo_ciudad, dims.dimension, dims.categoria, count(*) AS n
           FROM dims GROUP BY dims.programa, dims.cohorte, dims.estado, dims.grupo_ciudad, dims.dimension, dims.categoria
        )
 SELECT programa, cohorte, estado, grupo_ciudad, dimension, categoria,
        CASE WHEN n < 5 THEN NULL::bigint ELSE n END AS total
   FROM agg
  ORDER BY programa, cohorte, estado, dimension, categoria;
