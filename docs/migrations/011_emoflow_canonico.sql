-- =============================================================================
-- 011_emoflow_canonico.sql — Vistas Emoflow restringidas al universo canónico
-- Fundación ROFÉ | Jóvenes creaTIvos | 2026-07-23
-- =============================================================================
--
-- CONTEXTO
-- --------
-- Auditoría de coherencia del panel (2026-07-23): de las 26 fuentes que consume
-- el frontend, 21 ya respetan la verdad canónica de "quién es estudiante"
-- (pestaña Seguimiento → participants.en_seguimiento_jc). El bloque Emoflow NO:
-- las 4 vistas leen `emoflow_ingresos` en crudo y reportan 827 personas, cuando
-- el universo canónico de la cohorte JC 2026 es 760.
--
-- Desglose verificado de los 827:
--   742  estudiantes canónicos (matriculados + presentes en Seguimiento)
--    17  con en_seguimiento_jc = false (retiro probable, pendiente de confirmar)
--    68  SIN participant_id — no son participantes en Supabase en absoluto
--        (56 de ellos sí están en postulantes_jc → postulantes/retirados
--         antiguos; ver la brecha estructural 832 vs 777 documentada en
--         supabase-estructura.md)
--
-- DECISIÓN (Samuel, 2026-07-23): NO reemplazar las vistas existentes. El panel
-- debe poder mostrar AMBOS universos con un toggle — "Todos (histórico)" con los
-- 827, y "Solo estudiantes actuales" con los 742. Por eso esta migración solo
-- AGREGA 4 vistas paralelas `_canonico`; las originales quedan intactas y
-- ningún consumidor actual se rompe.
--
-- Criterio canónico aplicado:
--   participant_id IS NOT NULL           → excluye los 68 sin matrícula
--   AND en_seguimiento_jc IS DISTINCT FROM false → excluye los 17 en duda
--   (IS DISTINCT FROM false, no = true: deja pasar NULL, que es el estado
--    conservador de un participante recién creado por el sync de Q10 antes de
--    que corra el cálculo del flag)
--
-- Mismas columnas que las vistas originales → el frontend reutiliza las mismas
-- interfaces TypeScript, solo cambia el endpoint según el toggle.
--
-- SEGURIDAD: agregados sin PII (igual que las originales) → GRANT SELECT a anon.
-- =============================================================================

-- 1) Resumen global -----------------------------------------------------------
CREATE OR REPLACE VIEW public.v_emoflow_resumen_canonico AS
SELECT count(*)                                                            AS participantes,
       count(e.participant_id)                                             AS con_match_supabase,
       round(avg(e.ingresos), 1)                                           AS ingresos_promedio,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY e.ingresos::double precision)::integer AS ingresos_mediana,
       max(e.ingresos)                                                     AS ingresos_max,
       count(*) FILTER (WHERE e.ultimo_ingreso >= CURRENT_DATE - 7)        AS activos_7d,
       count(*) FILTER (WHERE e.ultimo_ingreso >= CURRENT_DATE - 14)       AS activos_14d,
       count(*) FILTER (WHERE e.ultimo_ingreso <  CURRENT_DATE - 30)       AS inactivos_30d,
       max(e.fecha_corte)                                                  AS fecha_corte
FROM public.emoflow_ingresos e
JOIN public.participants p ON p.id = e.participant_id
WHERE p.en_seguimiento_jc IS DISTINCT FROM false;

-- 2) Por ciudad ---------------------------------------------------------------
CREATE OR REPLACE VIEW public.v_emoflow_por_ciudad_canonico AS
SELECT COALESCE(e.grupo_ciudad, 'SIN_CIUDAD'::character varying)           AS grupo_ciudad,
       count(*)                                                            AS participantes,
       round(avg(e.ingresos), 1)                                           AS ingresos_promedio,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY e.ingresos::double precision)::integer AS ingresos_mediana,
       count(*) FILTER (WHERE e.ultimo_ingreso >= CURRENT_DATE - 7)        AS activos_7d,
       count(*) FILTER (WHERE e.ultimo_ingreso <  CURRENT_DATE - 30)       AS inactivos_30d
FROM public.emoflow_ingresos e
JOIN public.participants p ON p.id = e.participant_id
WHERE p.en_seguimiento_jc IS DISTINCT FROM false
GROUP BY COALESCE(e.grupo_ciudad, 'SIN_CIUDAD'::character varying);

-- 3) Bandas de uso ------------------------------------------------------------
CREATE OR REPLACE VIEW public.v_emoflow_bandas_canonico AS
WITH base AS (
    SELECT e.participant_id,
           e.ingresos,
           CASE WHEN e.ingresos <= 5  THEN 1
                WHEN e.ingresos <= 15 THEN 2
                WHEN e.ingresos <= 30 THEN 3
                WHEN e.ingresos <= 60 THEN 4
                ELSE 5 END AS orden,
           CASE WHEN e.ingresos <= 5  THEN '1-5'
                WHEN e.ingresos <= 15 THEN '6-15'
                WHEN e.ingresos <= 30 THEN '16-30'
                WHEN e.ingresos <= 60 THEN '31-60'
                ELSE '61+' END AS banda
    FROM public.emoflow_ingresos e
    JOIN public.participants p ON p.id = e.participant_id
    WHERE p.en_seguimiento_jc IS DISTINCT FROM false
), avance AS (
    SELECT en.participant_id,
           avg(en.porcentaje_avance)                                  AS avance_promedio,
           count(*) FILTER (WHERE en.porcentaje_avance > 80)          AS cursos_aprobados,
           count(*)                                                   AS cursos
    FROM public.enrollments en
    JOIN public.courses c ON c.id = en.course_id
    WHERE c.cohorte::text = '2026' AND c.programa = 'jc'::programa_type
    GROUP BY en.participant_id
)
SELECT b.banda,
       b.orden,
       count(*)                                                       AS participantes,
       round(avg(b.ingresos), 1)                                      AS ingresos_promedio,
       round(avg(a.avance_promedio), 1)                               AS avance_promedio,
       round(100.0 * sum(a.cursos_aprobados) / NULLIF(sum(a.cursos), 0::numeric), 1) AS pct_aprobacion
FROM base b
LEFT JOIN avance a ON a.participant_id = b.participant_id
GROUP BY b.banda, b.orden;

-- 4) Bandas por ciudad --------------------------------------------------------
CREATE OR REPLACE VIEW public.v_emoflow_bandas_ciudad_canonico AS
WITH base AS (
    SELECT e.participant_id,
           e.grupo_ciudad,
           e.ingresos,
           CASE WHEN e.ingresos <= 5  THEN 1
                WHEN e.ingresos <= 15 THEN 2
                WHEN e.ingresos <= 30 THEN 3
                WHEN e.ingresos <= 60 THEN 4
                ELSE 5 END AS orden,
           CASE WHEN e.ingresos <= 5  THEN '1-5'
                WHEN e.ingresos <= 15 THEN '6-15'
                WHEN e.ingresos <= 30 THEN '16-30'
                WHEN e.ingresos <= 60 THEN '31-60'
                ELSE '61+' END AS banda
    FROM public.emoflow_ingresos e
    JOIN public.participants p ON p.id = e.participant_id
    WHERE p.en_seguimiento_jc IS DISTINCT FROM false
      AND e.grupo_ciudad IS NOT NULL
), avance AS (
    SELECT en.participant_id,
           avg(en.porcentaje_avance)                                  AS avance_promedio,
           count(*) FILTER (WHERE en.porcentaje_avance > 80)          AS cursos_aprobados,
           count(*)                                                   AS cursos
    FROM public.enrollments en
    JOIN public.courses c ON c.id = en.course_id
    WHERE c.cohorte::text = '2026' AND c.programa = 'jc'::programa_type
    GROUP BY en.participant_id
)
SELECT b.grupo_ciudad,
       b.banda,
       b.orden,
       count(*)                                                       AS participantes,
       round(avg(b.ingresos), 1)                                      AS ingresos_promedio,
       round(avg(a.avance_promedio), 1)                               AS avance_promedio,
       round(100.0 * sum(a.cursos_aprobados) / NULLIF(sum(a.cursos), 0::numeric), 1) AS pct_aprobacion
FROM base b
LEFT JOIN avance a ON a.participant_id = b.participant_id
GROUP BY b.grupo_ciudad, b.banda, b.orden;

-- Permisos: agregados sin PII, mismo trato que las vistas públicas existentes.
GRANT SELECT ON public.v_emoflow_resumen_canonico       TO anon, authenticated;
GRANT SELECT ON public.v_emoflow_por_ciudad_canonico    TO anon, authenticated;
GRANT SELECT ON public.v_emoflow_bandas_canonico        TO anon, authenticated;
GRANT SELECT ON public.v_emoflow_bandas_ciudad_canonico TO anon, authenticated;

COMMENT ON VIEW public.v_emoflow_resumen_canonico IS
  'Espejo de v_emoflow_resumen restringido al universo canónico (matriculados en Supabase y presentes en la pestaña Seguimiento). Alimenta el toggle "Solo estudiantes actuales" del panel. La vista sin sufijo conserva el universo histórico completo (827).';
COMMENT ON VIEW public.v_emoflow_por_ciudad_canonico IS
  'Espejo canónico de v_emoflow_por_ciudad. Ver COMMENT de v_emoflow_resumen_canonico.';
COMMENT ON VIEW public.v_emoflow_bandas_canonico IS
  'Espejo canónico de v_emoflow_bandas. Ver COMMENT de v_emoflow_resumen_canonico.';
COMMENT ON VIEW public.v_emoflow_bandas_ciudad_canonico IS
  'Espejo canónico de v_emoflow_bandas_ciudad. Ver COMMENT de v_emoflow_resumen_canonico.';
