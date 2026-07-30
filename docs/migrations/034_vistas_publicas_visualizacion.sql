-- 034_vistas_publicas_visualizacion.sql
-- Aplicada 2026-07-30 vía Supabase MCP (apply_migration + fix 034b en el mismo día). Fase 1.2 de
-- plan-visualizacion-2026-07-30.md.
--
-- v_pub_cohorte, v_pub_geografia (con supresión k-anonimato en municipio), v_pub_avance.
--
-- Gotcha real encontrado al verificar con `SET ROLE anon` (no asumir el GRANT, probarlo): la
-- primera versión puso `security_invoker = on` en las tres vistas, siguiendo al pie de la letra
-- la regla general del prompt ("vistas nuevas... security_invoker = on"). Rompió el acceso de
-- anon con `permission denied for table participants` / `ciudad_alias` — esas tablas tienen
-- REVOKE explícito de anon (hardening 2026-07-23) precisamente para proteger PII, y con
-- security_invoker=on la vista deja de correr con los privilegios del dueño y exige que el rol
-- que consulta (anon) tenga GRANT directo en las tablas base, cosa que nunca va a tener.
-- `security_invoker=on` es correcto SOLO para vistas de nivel individuo consumidas por
-- service_role (ver 033_v_gui_personas.sql, donde no aplica el problema porque service_role
-- bypasea RLS/GRANTs de todas formas). Las vistas públicas de agregados de este proyecto usan
-- deliberadamente el patrón owner-privilege (sin security_invoker) — ya documentado y aceptado
-- en supabase-estructura.md para v_demografia_grupo y hermanas ("no cambiar a SECURITY INVOKER
-- — rompería los dashboards públicos"). Revertido en 034b, reverificado con `SET ROLE anon`.

-- Umbral de supresión nombrado (decisión de Lina, 2026-07-30, plan-visualizacion §1.3): el
-- desglose público de municipio dentro de un grupo_ciudad solo muestra el nombre cuando
-- n >= este umbral; el resto se agrupa como "Área metropolitana". Mismo patrón de k-anonimato
-- que v_demografia_grupo (migración 018), aplicado ahora a geografía en vez de género.
create or replace function umbral_supresion_municipio()
returns integer
language sql
immutable
as $function$ select 5 $function$;

comment on function umbral_supresion_municipio() is
  'Umbral de k-anonimato para el desglose público de municipio en v_pub_geografia (n < umbral se agrupa como "Área metropolitana"). Decisión de Lina, 2026-07-30 -- ver docs/procesos/plan-visualizacion-2026-07-30.md §1.3.';

revoke all on function umbral_supresion_municipio() from public;
grant execute on function umbral_supresion_municipio() to anon, authenticated, service_role;

-- v_pub_cohorte: wrapper de cohorte_ingresos (ya pública) con nombre estable de la familia
-- v_pub_* para que el frontend no dependa del nombre de la tabla de staging del ETL.
create or replace view v_pub_cohorte as
select programa, cohorte, ingresados, activos, retirados, pct_aprobados
from cohorte_ingresos;

-- v_pub_geografia: programa x cohorte x grupo_ciudad x municipio, con supresión de celdas
-- chicas de municipio. "aprobados" = personas con avance promedio > 80, mismo umbral que
-- v_cohorte_estudiantes.al_dia. municipio_clave usa ciudad_alias (mismo mecanismo ya usado en
-- toda la normalización de ciudad) para colapsar variantes (Bogotá/Bogota/Bogotá D.C. -> una
-- sola fila); el nombre mostrado es el más frecuente (mode()) dentro de cada grupo normalizado.
create or replace view v_pub_geografia as
with persona_curso as (
  select
    p.id as participant_id,
    c.programa,
    c.cohorte,
    p.grupo_ciudad,
    p.ciudad_norm,
    p.ciudad,
    avg(e.porcentaje_avance) as avance_persona
  from participants p
  join enrollments e on e.participant_id = p.id
  join courses c on c.id = e.course_id
  where p.grupo_ciudad is not null
    and p.en_seguimiento_jc is distinct from false
  group by p.id, c.programa, c.cohorte, p.grupo_ciudad, p.ciudad_norm, p.ciudad
),
base as (
  select
    pc.programa,
    pc.cohorte,
    pc.grupo_ciudad,
    coalesce(ca.ciudad_canonica, pc.ciudad_norm) as municipio_clave,
    mode() within group (order by pc.ciudad) as municipio_nombre,
    count(*) as personas,
    avg(pc.avance_persona) as avance_promedio,
    count(*) filter (where pc.avance_persona > 80) as aprobados
  from persona_curso pc
  left join ciudad_alias ca on ca.clave_norm = pc.ciudad_norm
  group by pc.programa, pc.cohorte, pc.grupo_ciudad, coalesce(ca.ciudad_canonica, pc.ciudad_norm)
),
etiquetado as (
  select
    *,
    case
      when personas < umbral_supresion_municipio() then 'Área metropolitana'
      else municipio_nombre
    end as municipio_pub
  from base
)
select
  programa,
  cohorte,
  grupo_ciudad,
  municipio_pub as municipio,
  sum(personas) as personas,
  round(sum(avance_promedio * personas) / nullif(sum(personas), 0), 1) as avance_promedio,
  sum(aprobados) as aprobados
from etiquetado
group by programa, cohorte, grupo_ciudad, municipio_pub
order by programa, cohorte, grupo_ciudad, municipio;

-- v_pub_avance: programa x cohorte x cursos_aprobados -> personas. "Aprobado" = avance > 80 en
-- ese curso (mismo UMBRAL_APROBADO que export_aprobacion.py).
create or replace view v_pub_avance as
with persona_cursos as (
  select
    p.id as participant_id,
    c.programa,
    c.cohorte,
    count(*) filter (where e.porcentaje_avance > 80) as cursos_aprobados
  from participants p
  join enrollments e on e.participant_id = p.id
  join courses c on c.id = e.course_id
  where p.en_seguimiento_jc is distinct from false
  group by p.id, c.programa, c.cohorte
)
select programa, cohorte, cursos_aprobados, count(*) as personas
from persona_cursos
group by programa, cohorte, cursos_aprobados
order by programa, cohorte, cursos_aprobados;

comment on view v_pub_cohorte is
  'Agregado público programa x cohorte: ingresados/activos/retirados/pct_aprobados. Wrapper estable de cohorte_ingresos. Owner-privilege view (sin security_invoker). anon: solo SELECT. Plan de visualización 2026-07-30.';
comment on view v_pub_geografia is
  'Agregado público programa x cohorte x grupo_ciudad x municipio, con supresión n<umbral_supresion_municipio() agrupada como "Área metropolitana" (decisión de Lina 2026-07-30). JC no tiene granularidad real de municipio -- el frontend debe aclararlo. Owner-privilege view (sin security_invoker), mismo patrón que v_demografia_grupo. anon: solo SELECT.';
comment on view v_pub_avance is
  'Distribución pública de personas por cantidad de cursos aprobados (avance>80), programa x cohorte. Owner-privilege view (sin security_invoker). anon: solo SELECT. Plan de visualización 2026-07-30.';

-- Supabase otorga ALL por defecto a objetos nuevos del schema public -- dejar solo SELECT.
revoke insert, update, delete, truncate, references, trigger
  on v_pub_cohorte, v_pub_geografia, v_pub_avance
  from anon, authenticated;
grant select on v_pub_cohorte, v_pub_geografia, v_pub_avance to anon, authenticated;

-- Verificado tras aplicar con `SET ROLE anon` (no solo mirar information_schema):
--   v_pub_cohorte, v_pub_geografia, v_pub_avance: las 3 responden sin error a anon.
--   Cuadre: v_pub_cohorte.activos (jc/2026)=760; sum(v_pub_geografia.personas) jc/2026=760;
--   sum(v_pub_avance.personas) jc/2026=760. Los tres coinciden exactos.
--   Supresión real observada: mr/2026/BOG -> "Bogotá" 28 personas + "Área metropolitana" 6
--   (municipios satélite < 5 cada uno, agrupados). Ningún municipio con n<5 queda expuesto.
