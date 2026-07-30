-- 035_v_aprobacion_cursos_vigencia.sql
-- Aplicada 2026-07-30 vía Supabase MCP (apply_migration). Fase 1.4 (guarda 2) de
-- plan-visualizacion-2026-07-30.md.
--
-- UMBRAL_PROMEDIO_FIN=90 (export_aprobacion.py) tiene un punto ciego demostrado: un curso que
-- cierra con avance bajo (MR "De la idea a la acción...", 41.9%) nunca se habría marcado
-- finalizado. Esta vista complementa esa señal con `visto_en_fuente_at`: un curso también se
-- considera finalizado si dejó de aparecer en la última corrida de su programa/cohorte —
-- reusa el mismo umbral de 12h ya calibrado y en producción en v_choques_cursos (no se inventó
-- uno nuevo). aprobacion_cursos no tiene FK a courses (se llavea por nombre en texto, Title
-- Case vs MAYÚSCULAS) -- el join usa upper(btrim(...)), mismo patrón que v_choques_cursos.

create or replace view v_aprobacion_cursos_vigencia as
with ultima_corrida as (
  select programa, cohorte, max(visto_en_fuente_at) as ts
  from courses
  group by programa, cohorte
)
select
  ac.cohorte,
  ac.curso,
  ac.programa,
  ac.cursaron,
  ac.activos,
  ac.aprobados,
  ac.aprobados_total,
  ac.retirados,
  ac.promedio,
  ac.pct_aprobados,
  ac.finalizado as finalizado_por_promedio,
  c.visto_en_fuente_at,
  (c.visto_en_fuente_at is not null and c.visto_en_fuente_at < (u.ts - interval '12 hours')) as no_visto_en_fuente,
  (ac.finalizado or (c.visto_en_fuente_at is not null and c.visto_en_fuente_at < (u.ts - interval '12 hours'))) as finalizado_real
from aprobacion_cursos ac
left join courses c
  on c.programa = ac.programa and c.cohorte = ac.cohorte
  and upper(btrim(c.nombre)) = upper(btrim(ac.curso))
left join ultima_corrida u on u.programa = ac.programa and u.cohorte = ac.cohorte;

comment on view v_aprobacion_cursos_vigencia is
  'aprobacion_cursos + finalizado_real = finalizado_por_promedio (UMBRAL_PROMEDIO_FIN=90) OR no_visto_en_fuente (curso ausente >12h de la última corrida de su programa/cohorte, mismo umbral que v_choques_cursos). Cierra el punto ciego documentado en plan-visualizacion-2026-07-30.md §0. Sin PII, agregado por curso. anon: solo SELECT.';

revoke insert, update, delete, truncate, references, trigger
  on v_aprobacion_cursos_vigencia
  from anon, authenticated;
grant select on v_aprobacion_cursos_vigencia to anon, authenticated;

-- Verificado tras aplicar, cohorte 2026 (11 cursos):
--   "De la idea a la acción..." (MR, promedio 41.9%): finalizado_por_promedio=false,
--   no_visto_en_fuente=true (última vez visto 2026-07-21) -> finalizado_real=true. Corrige el
--   punto ciego.
--   "Habilidades del ser..." (MR, promedio 32.07%, cerró 29-jul): mismo patrón,
--   finalizado_real=true.
--   "Finanzas Inteligentes..." (MR, promedio 7.8%, curso NUEVO visto hoy) y "Desarrollo Web
--   Front-End - JavaScript" (JC, promedio 2.1%, curso NUEVO visto hoy): no_visto_en_fuente=false
--   -> finalizado_real=false, correcto -- avance bajo por ser recién arrancados, no por cierre.
--   `SET ROLE anon`: 11 filas legibles, sin error.
--
-- Nota: NO se tocó export_aprobacion.py (fuera de alcance de esta fase -- lee Q10 directo, no
-- Supabase). Esta vista es la fuente para cualquier consumidor que quiera el finalizado
-- corregido leyendo Supabase directamente (futuro frontend, GUI, etc.).
