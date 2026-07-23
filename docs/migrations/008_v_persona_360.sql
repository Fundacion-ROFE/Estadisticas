-- Vista: v_persona_360 — APLICADA 2026-07-23
-- Trazabilidad total por cédula en una sola consulta (pedido explícito de
-- Samuel: "para un informe individual podamos tener todo de una persona en
-- una sola consulta"). Une, por cédula, TODOS los sistemas que hoy conocen a
-- una persona: participants (matrícula Q10), postulantes_mr, postulantes_jc,
-- emoflow_ingresos (match por email) y asistencia_promedio (match por email).
--
-- Uso previsto: scripts locales con service_role, ej.
--   GET /rest/v1/v_persona_360?cedula=eq.<cedula>
-- NUNCA desde el frontend público — ver REVOKE abajo.

CREATE OR REPLACE VIEW public.v_persona_360 AS
WITH identidades AS (
  SELECT q10_id AS cedula FROM public.participants WHERE q10_id IS NOT NULL
  UNION
  SELECT cedula FROM public.postulantes_mr
  UNION
  SELECT cedula FROM public.postulantes_jc
),
enroll_resumen AS (
  SELECT e.participant_id,
         count(*) AS total_cursos,
         count(*) FILTER (WHERE e.estado = 'completado') AS cursos_completados,
         round(avg(e.porcentaje_avance), 1) AS avance_promedio,
         string_agg(DISTINCT c.programa::text, ',') AS programas_matriculado,
         string_agg(DISTINCT c.cohorte, ',' ORDER BY c.cohorte) AS cohortes
  FROM public.enrollments e
  JOIN public.courses c ON c.id = e.course_id
  GROUP BY e.participant_id
)
SELECT
  i.cedula,
  p.id            AS participant_id,
  p.nombre, p.email, p.genero, p.edad, p.ciudad, p.grupo_ciudad,
  p.estrato, p.estado_civil, p.nivel_estudio, p.tipo_vivienda,
  p.tiene_emprendimiento, p.nombre_emprendimiento, p.situacion_emprendimiento,
  er.programas_matriculado, er.cohortes, er.total_cursos, er.cursos_completados, er.avance_promedio,
  pm.nombre AS nombre_postulante_mr, pm.fuente_pestana AS fuente_mr, pm.estado AS estado_mr, pm.celular AS celular_mr,
  pj.nombre AS nombre_postulante_jc, pj.fuente AS fuente_jc, pj.rol AS rol_jc, pj.celular AS celular_jc,
  em.ingresos AS emoflow_ingresos, em.ultimo_ingreso AS emoflow_ultimo_ingreso, em.grupo_ciudad AS emoflow_grupo_ciudad,
  ap.promedio_general AS asistencia_promedio, ap.n_registros AS asistencia_n_registros,
  (p.id IS NOT NULL)       AS matriculada_q10,
  (pm.cedula IS NOT NULL)  AS en_postulantes_mr,
  (pj.cedula IS NOT NULL)  AS en_postulantes_jc,
  (em.email IS NOT NULL)   AS usa_emoflow
FROM identidades i
LEFT JOIN public.participants p         ON p.q10_id = i.cedula
LEFT JOIN public.postulantes_mr pm      ON pm.cedula = i.cedula
LEFT JOIN public.postulantes_jc pj      ON pj.cedula = i.cedula
LEFT JOIN enroll_resumen er             ON er.participant_id = p.id
LEFT JOIN public.emoflow_ingresos em    ON lower(trim(em.email)) = lower(trim(p.email))
LEFT JOIN public.asistencia_promedio ap ON lower(trim(ap.email)) = lower(trim(p.email));

COMMENT ON VIEW public.v_persona_360 IS
  'Trazabilidad total por cédula: participants + postulantes_mr + postulantes_jc + emoflow_ingresos + asistencia_promedio en una sola fila. PII densa -> RLS/REVOKE estricto, SOLO service_role.';

ALTER VIEW public.v_persona_360 OWNER TO postgres;
REVOKE ALL ON public.v_persona_360 FROM anon, authenticated, public;

-- Verificación aplicada: GET anon → 401 · GET service_role → 8.100 identidades
-- (2.919 matriculadas, 5.310 en postulantes_mr, 2.556 en postulantes_jc, 759 con Emoflow)
