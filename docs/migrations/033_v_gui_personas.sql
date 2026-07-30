-- 033_v_gui_personas.sql
-- Aplicada 2026-07-30 vía Supabase MCP (apply_migration). Fase 1.1 de
-- plan-visualizacion-2026-07-30.md.
--
-- v_gui_personas: vista nivel individuo para tools/panel_riesgo_gui.py (service_role solamente)
-- Reemplaza los cruces manuales que hoy hace la GUI leyendo Sheets + Supabase por separado.
-- Grano: (participant_id, programa, cohorte) -- una fila por persona x programa x cohorte en la
-- que tiene al menos una matricula (via enrollments/courses).
--
-- Gotcha encontrado y corregido al verificar con datos reales: el match inicial de retiro
-- (participant_id + programa + cohorte) daba 0 retiradas MR en vez de 8. Causa: retiros.cohorte
-- para MR NO es confiable (el propio motivo lo documenta: "no cohorte confirmada, ver 007") y
-- retiros.participant_id viene NULL en 5 de 8 filas MR (nunca cruzaron por cédula en el sync).
-- Las 8 retiradas MR resultaron tener su matrícula real bajo cohorte='2025', no '2026'. Fix:
-- LEFT JOIN LATERAL que matchea por participante (id, o cédula si participant_id es NULL) +
-- programa solamente, sin exigir cohorte igual — expone `retiro_cohorte_registrado` aparte para
-- que quien use la GUI vea la cohorte que trae la fuente sin que la vista la de por buena.

drop view if exists v_gui_personas;

create view v_gui_personas
with (security_invoker = on) as
with enroll_resumen as (
  select
    e.participant_id,
    c.programa,
    c.cohorte,
    count(*) as cursos_matriculados,
    sum((e.porcentaje_avance > 80)::int) as cursos_aprobados,
    round(avg(e.porcentaje_avance), 1) as avance_promedio
  from enrollments e
  join courses c on c.id = e.course_id
  group by e.participant_id, c.programa, c.cohorte
),
mc_agg as (
  select
    cedula,
    count(*) as microcreditos_count,
    string_agg(distinct tipo_credito, ', ') as tipos_credito
  from mr_microcreditos
  group by cedula
)
select
  p.id as participant_id,
  p.q10_id as cedula,
  p.nombre,
  p.email,
  p.genero,
  p.edad,
  er.programa,
  er.cohorte,
  p.ciudad as municipio,
  p.grupo_ciudad,
  er.cursos_matriculados,
  er.cursos_aprobados,
  er.avance_promedio,
  (er.avance_promedio > 80) as al_dia,
  r.fecha_retiro,
  r.motivo as motivo_retiro,
  r.cohorte_registrado as retiro_cohorte_registrado,
  (r.motivo is not null) as retirado,
  p.empresa_patrocinadora,
  em.ingresos as emoflow_ingresos,
  em.ultimo_ingreso as emoflow_ultimo_ingreso,
  p.estrato,
  p.estado_civil,
  p.nivel_estudio,
  p.tipo_vivienda,
  coalesce(mc.microcreditos_count, 0) > 0 as tiene_microcredito,
  mc.tipos_credito as microcredito_tipos,
  p.en_seguimiento_jc,
  p.fecha_verificacion_seguimiento
from participants p
join enroll_resumen er on er.participant_id = p.id
left join lateral (
  select r2.fecha_retiro, r2.motivo, r2.cohorte as cohorte_registrado
  from retiros r2
  where r2.programa = er.programa
    and (r2.participant_id = p.id or (r2.participant_id is null and r2.cedula = p.q10_id))
  order by r2.fecha_retiro desc nulls last, r2.updated_at desc
  limit 1
) r on true
left join emoflow_ingresos em on lower(btrim(em.email)) = lower(btrim(p.email))
left join mc_agg mc on mc.cedula = p.q10_id;

revoke all on v_gui_personas from anon, authenticated;

comment on view v_gui_personas is
  'Vista nivel individuo (PII) para tools/panel_riesgo_gui.py. service_role solamente. Grano: participant_id x programa x cohorte. retiro_cohorte_registrado puede no coincidir con la cohorte de matricula (MR: cohorte de retiros no confirmada, ver tabla retiros). Plan de visualizacion 2026-07-30.';

-- Verificado tras aplicar:
--   information_schema.role_table_grants: anon/authenticated sin ningún GRANT (solo
--   postgres/service_role).
--   jc/2026: 777 filas, 17 retirados (coincide con los 17 "fantasmas" ya confirmados como
--   retiros reales). mr/2025: 1.016 filas, 8 retirados (las 8 de Inactivas, ahí es donde vive
--   su matrícula real). mr/2026: 347 filas, 0 retirados en esa cohorte específica — correcto
--   dado el hallazgo de arriba.
