-- 050_v_retiro_probable_jc_excluir_confirmados
-- Aplicada 2026-08-18 vía MCP de Supabase (project panel-datos-rofe, kbxptoowtnteflhrfwid).
--
-- Bug real encontrado: v_retiro_probable_jc (migración/nombre original
-- crear_v_retiro_probable_jc, 2026-07-23) solo filtraba en_seguimiento_jc = false — nunca
-- revisaba si Q10 ya había confirmado el retiro. Cuando se creó eso bastaba porque casi nadie
-- tenía el retiro confirmado todavía; después de la migración 049 (2026-08-13, fix de
-- v_gui_personas.retirado por cohorte) el canon de Q10 se puso al día con esas mismas
-- personas y la vista siguió contándolas como "en duda" para siempre.
--
-- Verificado en vivo antes de aplicar (2026-08-18): JC 2026 = 27 en la vista, 27/27 ya
-- retirados en Q10 según v_gui_personas -> 0 casos realmente en duda.
--
-- Fix: se agrega LEFT JOIN a v_gui_personas (reusa la lógica canon de retirado por cohorte,
-- no se duplica) y se filtra COALESCE(g.retirado, false) = false.
--
-- Test de regresión actualizado en scripts/panel-datos/test_integridad_supabase.py (la
-- aserción vieja asumía la definición con el bug: vista == count(en_seguimiento_jc=false) sin
-- descontar confirmados). Suite 53/53 PASS tras el fix.
--
-- Ver docs/procesos/panel-control-jc-mr.md §7.23 para el relato completo.

CREATE OR REPLACE VIEW v_retiro_probable_jc AS
WITH alerta AS (
  SELECT p.id,
         c.cohorte,
         avg(e.porcentaje_avance) AS avance_prom
  FROM participants p
  JOIN enrollments e ON e.participant_id = p.id
  JOIN courses c ON c.id = e.course_id
  WHERE c.programa = 'jc'::programa_type
    AND p.en_seguimiento_jc = false
  GROUP BY p.id, c.cohorte
)
SELECT a.cohorte,
       count(*)::integer AS retiro_probable_total,
       count(*) FILTER (WHERE a.avance_prom > 80::numeric)::integer AS retiro_probable_aprobado,
       count(*) FILTER (WHERE a.avance_prom <= 80::numeric)::integer AS retiro_probable_no_aprobado,
       round(avg(a.avance_prom), 1) AS avance_promedio
FROM alerta a
LEFT JOIN v_gui_personas g
  ON g.participant_id = a.id AND g.programa = 'jc' AND g.cohorte = a.cohorte
WHERE COALESCE(g.retirado, false) = false
GROUP BY a.cohorte;
