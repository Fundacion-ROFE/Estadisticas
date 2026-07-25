-- Auditoría "a fondo" de la DB con los advisors nativos de Supabase (security + performance)
-- + revisión manual, 2026-07-24. Aplicada vía Supabase MCP (apply_migration), en 3 pasos
-- reales (el 2º se revirtió tras verificar en vivo que rompía producción — ver abajo).

-- ============================================================
-- PASO 1 (se queda): campanas_enviadas — RLS activado, SIN política.
-- ============================================================
-- Con RLS enabled + 0 políticas, anon puede ejecutar el SELECT (tiene privilegio de
-- tabla) pero RLS filtra todas las filas -> responde 200 con [] en vez de 401. Es
-- exactamente el mismo patrón ya corregido en participants/emoflow_ingresos/
-- email_optout/email_bounces/participants_snapshots el 2026-07-21 ("incidente
-- 2026-07-14" en convenciones.md) — esta tabla se quedó fuera de esa pasada. Sin PII de
-- personas (registra campañas de correo enviadas, no destinatarios), pero se corrige por
-- consistencia con el resto de tablas base.
REVOKE ALL ON public.campanas_enviadas FROM anon, authenticated;

-- ============================================================
-- PASO 2 (se queda): search_path mutable en funciones creadas hoy (migración 013).
-- ============================================================
-- El linter de seguridad marcó normalizar_ciudad/ciudad_canonica sin SET search_path
-- explícito (WARN). Riesgo real bajo aquí (solo llaman funciones de pg_catalog + tablas
-- ya fully-qualified con public.), pero se corrige por buena práctica / para que el
-- advisor deje de marcarlo.
ALTER FUNCTION public.normalizar_ciudad(text) SET search_path = pg_catalog, public;
ALTER FUNCTION public.ciudad_canonica(text) SET search_path = pg_catalog, public;

-- ============================================================
-- PASO 3 (REVERTIDO — ver PASO 3b): participa_en(uuid, programa_type).
-- ============================================================
-- El advisor marcó que anon/authenticated pueden ejecutar esta función SECURITY DEFINER
-- directo vía RPC (/rest/v1/rpc/participa_en), probablemente por el GRANT a PUBLIC que
-- Postgres pone por default al crear una función. Se intentó revocar asumiendo que las
-- vistas que la usan (v_demografia_grupo, v_emprendimiento_situacion), al ser también
-- SECURITY DEFINER, no necesitarían que anon tuviera EXECUTE directo.
--
-- FALSO. Verificado en vivo con la anon key real: revocar EXECUTE de participa_en()
-- rompió AMBAS vistas para anon (401 "permission denied for function participa_en").
-- Lección: en Postgres, el acceso "como el dueño" que dan las vistas normales cubre las
-- TABLAS subyacentes, pero NO las FUNCIONES invocadas dentro del cuerpo de la vista — el
-- rol que consulta necesita su propio EXECUTE en cualquier función que la vista llame,
-- sin importar si esa función es SECURITY DEFINER o si la vista es SECURITY DEFINER.
-- Lo que el advisor marcaba como "exceso de permiso" era en realidad un prerrequisito
-- real. Revertido de inmediato (mismo turno, verificado con la anon key antes y después,
-- nunca quedó roto en producción):
--   REVOKE EXECUTE ON FUNCTION public.participa_en(uuid, public.programa_type) FROM anon, authenticated;
--   REVOKE EXECUTE ON FUNCTION public.participa_en(uuid, public.programa_type) FROM PUBLIC;
--   (revertido con) GRANT EXECUTE ON FUNCTION public.participa_en(uuid, public.programa_type) TO anon, authenticated;
--
-- Estado final: participa_en sigue ejecutable por anon/authenticated (como estaba antes
-- de esta auditoría) — es necesario, no un descuido.
