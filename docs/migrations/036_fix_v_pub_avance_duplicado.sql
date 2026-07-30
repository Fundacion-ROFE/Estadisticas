-- 036_fix_v_pub_avance_duplicado.sql
-- Aplicada 2026-07-30 vía Supabase MCP. Fase 3 (conectar el frontend Netlify).
--
-- Hallazgo al conectar el frontend: v_pub_avance (migración 034) duplicaba EXACTAMENTE
-- v_cohorte_estudiantes_distribucion (existente desde 2026-07-15, migración
-- 20260715134437, ya consumida por el frontend como `estudiantesDist` en lib/api.ts) --
-- mismos números verificados fila por fila (jc/2026: 1,2,4,5,6,7,8 cursos aprobados, mismo
-- conteo de personas en ambas). No se había revisado el frontend/las vistas existentes antes
-- de escribir la migración 034 -- lección para la próxima vista nueva: buscar si ya existe
-- algo equivalente antes de escribir una definición independiente.
--
-- Redefinida como wrapper (mismo patrón que v_pub_cohorte sobre cohorte_ingresos) en vez de
-- mantener dos definiciones independientes que podrían divergir con el tiempo si alguien
-- edita una y no la otra.

drop view if exists v_pub_avance;

create view v_pub_avance as
select cohorte, programa, cursos_aprobados, estudiantes as personas
from v_cohorte_estudiantes_distribucion;

comment on view v_pub_avance is
  'Wrapper de v_cohorte_estudiantes_distribucion (ya existente, mismo cálculo) con nombre estable de la familia v_pub_*. Distribución pública de personas por cantidad de cursos aprobados (avance>80), programa x cohorte. anon: solo SELECT.';

revoke insert, update, delete, truncate, references, trigger
  on v_pub_avance
  from anon, authenticated;
grant select on v_pub_avance to anon, authenticated;

-- Verificado: SET ROLE anon -> 40 filas legibles, sin error.
