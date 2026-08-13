-- 047 — v_pub_retencion_ciudad
-- ============================================================================
-- Habilita la pestaña "Retención" del panel Vercel: distribuye la retención/deserción del
-- canon a lo largo de las ciudades y las rankea, para dar seguimiento a cuáles retienen mejor.
--
-- Por (programa, cohorte, grupo_ciudad):
--   * activos   = personas activas por ciudad. MISMO criterio EXACTO que v_pub_geografia (matrícula
--                 con en_seguimiento_jc IS DISTINCT FROM false) → suma igual al canon en la cohorte
--                 viva (JC 2026 = 750). Solo la cohorte VIGENTE es canon-exacta (el frontend
--                 restringe la pestaña a esActual); en cerradas el canon no tiene desglose por ciudad.
--   * retirados = retiros de esa (programa, cohorte) cuyo participante tiene esa grupo_ciudad.
--   * ingresados = activos + retirados; retencion_pct = 100*activos/ingresados (1 decimal).
--   * k-anon: WHERE final oculta ciudades con < 5 personas (a nivel grupo_ciudad ninguna cae por
--     debajo en JC, se deja por principio).
--
-- Verificado vs canon (JC 2026): Σactivos=750, Σretirados=82, Σingresados=832 → 90.1%. Peor UY,
-- mejor GYL 98.8%.
--
-- El frontend (comunicaciones-ai/Panel-De-Datos, page.tsx 'use client' + fetch) lee EN VIVO con
-- leerSeguro() → mientras la vista no exista la pestaña muestra "en construcción"; al aplicarla se
-- enciende sola sin redeploy.
--
-- ⚠ CÓMO APLICAR: no hay MCP de Supabase ni psql en la sesión que la generó. Pegar este bloque en
--   el editor SQL de Supabase (proyecto panel-datos-rofe / kbxptoowtnteflhrfwid) y ejecutarlo.
--   (Versión sin castes ::bigint/::numeric ni CASE para minimizar corrupción al copiar/pegar.)
-- ============================================================================

create or replace view public.v_pub_retencion_ciudad as
with activos as (
  select c.programa, c.cohorte::text as cohorte, p.grupo_ciudad, count(distinct p.id) as n
  from participants p
  join enrollments e on e.participant_id = p.id
  join courses c on c.id = e.course_id
  where p.grupo_ciudad is not null
    and p.en_seguimiento_jc is distinct from false
  group by c.programa, c.cohorte, p.grupo_ciudad
),
retirados as (
  select r.programa, r.cohorte::text as cohorte, p.grupo_ciudad, count(distinct r.participant_id) as n
  from retiros r
  join participants p on p.id = r.participant_id
  where p.grupo_ciudad is not null and r.participant_id is not null and r.cohorte <> 'no_cohorte'
  group by r.programa, r.cohorte, p.grupo_ciudad
),
j as (
  select coalesce(a.programa, rt.programa) as programa,
         coalesce(a.cohorte, rt.cohorte) as cohorte,
         coalesce(a.grupo_ciudad, rt.grupo_ciudad) as grupo_ciudad,
         coalesce(a.n, 0) as activos,
         coalesce(rt.n, 0) as retirados
  from activos a
  full outer join retirados rt
    on a.programa = rt.programa and a.cohorte = rt.cohorte and a.grupo_ciudad = rt.grupo_ciudad
)
select programa, cohorte, grupo_ciudad, activos, retirados,
       activos + retirados as ingresados,
       round(100.0 * activos / nullif(activos + retirados, 0), 1) as retencion_pct
from j
where activos + retirados >= 5
order by programa, cohorte, grupo_ciudad;

grant select on public.v_pub_retencion_ciudad to anon;
