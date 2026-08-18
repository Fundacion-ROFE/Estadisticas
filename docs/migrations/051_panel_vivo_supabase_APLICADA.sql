-- Fase 2 del panel de clase en vivo (docs/procesos/panel-clase-vivo.md): mueve el roster
-- (MATRICULADOS-VIVO), la config de salas (CUPOS) y la "lectura oficial" congelada de
-- Sheets/JSON local a Supabase, y abre acceso de solo-lectura acotado a monitores
-- autenticados (@tocaunavida.org) sobre las piezas de Fase 2 ya existentes
-- (zoom_reuniones_activas, zoom_live_log) -- hasta ahora solo accesibles por service_role.
-- Objetivo: que panel-datos-rofe/app/panel-vivo pueda leer Supabase directo, client-side,
-- sin depender de servidor_panel_vivo.py local ni de una API route (el sitio es
-- output:'export', sin server-side). Ver plan de sesion 2026-08-18.
--
-- No se toca el bloqueo existente de postulantes_jc/postulantes_mr (decision 2026-07-23) ni
-- de correo_alias (migracion 041) -- se agregan funciones SECURITY DEFINER de alcance
-- angosto en vez de una policy de SELECT sobre esas tablas completas.

-- ============================================================================
-- 1) Tablas nuevas
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.matriculados_vivo (
  horario        text NOT NULL,
  nombre         text NOT NULL,
  correo         text NOT NULL,
  actualizado_en timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (horario, correo)
);
COMMENT ON TABLE public.matriculados_vivo IS
  'Roster real por horario (reemplaza la pestana MATRICULADOS-VIVO de Sheets / tools/cupos_clases.json) -- fuente para el panel de clase en vivo en Vercel. PII (nombre+correo de estudiantes). Se repuebla con scripts/zoom-asistencia/sync_panel_vivo_config_supabase.py, tan fresco como la ultima corrida de analizar_cupos_bd.py -- misma limitacion ya aceptada para MATRICULADOS-VIVO.';

CREATE TABLE IF NOT EXISTS public.zoom_cupos_config (
  id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  area           text,
  clase          text NOT NULL,
  alias_zoom     text,
  dia            text,
  hora           numeric,
  inscritos      integer,
  actualizado_en timestamptz NOT NULL DEFAULT now()
);
COMMENT ON TABLE public.zoom_cupos_config IS
  'Config de horarios/salas (reemplaza la pestana CUPOS de Sheets para el panel en vivo) -- alias de topic Zoom, dia/hora oficial para la cascada de resolucion (ver panel_logic.resolver_fila_cupos / lib/panelLogic.ts). Sin PII. Se repuebla con sync_panel_vivo_config_supabase.py.';

CREATE TABLE IF NOT EXISTS public.zoom_lecturas_panel (
  clave        text PRIMARY KEY,  -- "{horario}|{fecha}", ej "HTML - Sabado 10AM|2026-08-22"
  hora_lectura text NOT NULL,
  resumen      jsonb NOT NULL,
  creado_en    timestamptz NOT NULL DEFAULT now()
);
COMMENT ON TABLE public.zoom_lecturas_panel IS
  'Snapshot UNICO de la "lectura oficial" del panel en vivo (reemplaza tools/lecturas_panel_vivo.json) -- se congela una sola vez por horario+fecha, 10 min despues de la hora oficial (UMBRAL_LECTURA_MIN, ver panel_logic.py/panelLogic.ts), para que un monitor pueda citar el numero sin que le cambie si vuelve a mirar. Sin PII (resumen = conteos agregados).';

ALTER TABLE public.matriculados_vivo   ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.zoom_cupos_config   ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.zoom_lecturas_panel ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- 2) Chequeo de dominio + policies para monitores autenticados
-- ============================================================================
-- Mismo chequeo que lib/auth.ts hace client-side (defensa en profundidad: si el consent
-- screen de Google alguna vez queda "External", RLS sigue bloqueando).

CREATE OR REPLACE FUNCTION public.es_monitor_panel_vivo()
RETURNS boolean
LANGUAGE sql
STABLE
SET search_path = public
AS $$
  SELECT COALESCE((auth.jwt() ->> 'email') ILIKE '%@tocaunavida.org', false)
$$;
COMMENT ON FUNCTION public.es_monitor_panel_vivo() IS
  'true si el JWT autenticado actual es una cuenta @tocaunavida.org -- condicion de las policies y RPC del panel de clase en vivo.';
REVOKE EXECUTE ON FUNCTION public.es_monitor_panel_vivo() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.es_monitor_panel_vivo() TO authenticated;
-- REVOKE FROM PUBLIC no basta: Supabase otorga EXECUTE a `anon` por default privileges del
-- proyecto en funciones nuevas -- hay que revocarlo de anon puntualmente (detectado por
-- get_advisors tras aplicar, fix en el mismo commit: migracion panel_vivo_supabase_fix_grants).
REVOKE EXECUTE ON FUNCTION public.es_monitor_panel_vivo() FROM anon;

CREATE POLICY monitor_select_matriculados_vivo ON public.matriculados_vivo
  FOR SELECT TO authenticated USING (public.es_monitor_panel_vivo());
CREATE POLICY monitor_select_zoom_cupos_config ON public.zoom_cupos_config
  FOR SELECT TO authenticated USING (public.es_monitor_panel_vivo());
CREATE POLICY monitor_select_zoom_lecturas_panel ON public.zoom_lecturas_panel
  FOR SELECT TO authenticated USING (public.es_monitor_panel_vivo());
CREATE POLICY monitor_insert_zoom_lecturas_panel ON public.zoom_lecturas_panel
  FOR INSERT TO authenticated WITH CHECK (public.es_monitor_panel_vivo());

REVOKE ALL ON public.matriculados_vivo FROM anon;
REVOKE INSERT, UPDATE, DELETE ON public.matriculados_vivo FROM authenticated;
REVOKE ALL ON public.zoom_cupos_config FROM anon;
REVOKE INSERT, UPDATE, DELETE ON public.zoom_cupos_config FROM authenticated;
REVOKE ALL ON public.zoom_lecturas_panel FROM anon;
REVOKE UPDATE, DELETE ON public.zoom_lecturas_panel FROM authenticated;

-- zoom_reuniones_activas / zoom_live_log ya existen (Fase 2, "solo service_role") -- agregar
-- SELECT para monitores sin tocar el resto (n8n sigue escribiendo con service_role, que
-- ignora RLS).
GRANT SELECT ON public.zoom_reuniones_activas TO authenticated;
GRANT SELECT ON public.zoom_live_log TO authenticated;

CREATE POLICY monitor_select_zoom_reuniones_activas ON public.zoom_reuniones_activas
  FOR SELECT TO authenticated USING (public.es_monitor_panel_vivo());
CREATE POLICY monitor_select_zoom_live_log ON public.zoom_live_log
  FOR SELECT TO authenticated USING (public.es_monitor_panel_vivo());

-- ============================================================================
-- 3) RPCs de alcance angosto sobre tablas de PII bloqueadas
-- ============================================================================
-- postulantes_jc/mr y correo_alias siguen SIN policy de SELECT para authenticated
-- (decision 2026-07-23 / migracion 041) -- estas 3 funciones exponen solo lo minimo
-- necesario para el panel en vivo, nunca la tabla completa via PostgREST directo.

-- 3a) Universo completo nombre+email (para "sin identificar": el match por nombre se hace
-- EN EL CLIENTE con lib/panelLogic.ts, igual que hoy hace panel_logic.py en Python -- no se
-- reimplementa el matching en SQL).
CREATE OR REPLACE FUNCTION public.universo_postulantes_panel_vivo()
RETURNS TABLE(nombre text, email text, fuente text)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  IF NOT public.es_monitor_panel_vivo() THEN
    RAISE EXCEPTION 'no autorizado';
  END IF;
  RETURN QUERY
    SELECT p.nombre::text, p.email::text, 'postulantes_jc'::text
    FROM public.postulantes_jc p WHERE p.email IS NOT NULL AND p.nombre IS NOT NULL
    UNION ALL
    SELECT p.nombre::text, p.email::text, 'postulantes_mr'::text
    FROM public.postulantes_mr p WHERE p.email IS NOT NULL AND p.nombre IS NOT NULL;
END;
$$;
COMMENT ON FUNCTION public.universo_postulantes_panel_vivo() IS
  'nombre+email de TODO postulantes_jc/mr, solo para monitores @tocaunavida.org -- equivalente a panel_logic.cargar_universo_postulantes(). El match por nombre se hace client-side (lib/panelLogic.ts).';

-- 3b) Enriquecimiento celular+ciudad, acotado a la lista de correos que pida el panel
-- (roster de las salas activas, no el universo completo).
CREATE OR REPLACE FUNCTION public.enriquecer_panel_vivo(correos text[])
RETURNS TABLE(email text, celular text, ciudad text)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  IF NOT public.es_monitor_panel_vivo() THEN
    RAISE EXCEPTION 'no autorizado';
  END IF;
  RETURN QUERY
    SELECT p.email::text, p.celular::text, p.ciudad::text
    FROM public.postulantes_jc p WHERE p.email = ANY(correos)
    UNION ALL
    SELECT p.email::text, p.celular::text, p.ciudad::text
    FROM public.postulantes_mr p WHERE p.email = ANY(correos);
END;
$$;
COMMENT ON FUNCTION public.enriquecer_panel_vivo(text[]) IS
  'celular+ciudad (SIN cedula) para una lista puntual de correos, solo monitores @tocaunavida.org -- equivalente a api_panel_vivo.enriquecer_celular_ciudad().';

-- 3c) Alias de correo -> correo oficial, reusando correo_a_participante() (migracion 041).
CREATE OR REPLACE FUNCTION public.resolver_alias_panel_vivo(correos text[])
RETURNS TABLE(correo_alterno text, correo_oficial text)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  IF NOT public.es_monitor_panel_vivo() THEN
    RAISE EXCEPTION 'no autorizado';
  END IF;
  RETURN QUERY
    SELECT a.correo_norm, public.normalizar_correo(p.email)
    FROM public.correo_alias a
    JOIN public.participants p ON p.id = a.participant_id
    WHERE a.correo_norm = ANY(correos);
END;
$$;
COMMENT ON FUNCTION public.resolver_alias_panel_vivo(text[]) IS
  'Resuelve una lista de correos alternos (los que entraron a Zoom) a su correo oficial via correo_alias+participants, solo monitores @tocaunavida.org -- reemplaza la pestana CORREO-ALIAS para el panel en Vercel.';

REVOKE EXECUTE ON FUNCTION public.universo_postulantes_panel_vivo() FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.enriquecer_panel_vivo(text[]) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.resolver_alias_panel_vivo(text[]) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.universo_postulantes_panel_vivo() TO authenticated;
GRANT EXECUTE ON FUNCTION public.enriquecer_panel_vivo(text[]) TO authenticated;
GRANT EXECUTE ON FUNCTION public.resolver_alias_panel_vivo(text[]) TO authenticated;
-- misma razon que arriba: revocar de anon puntualmente, no solo de PUBLIC.
REVOKE EXECUTE ON FUNCTION public.universo_postulantes_panel_vivo() FROM anon;
REVOKE EXECUTE ON FUNCTION public.enriquecer_panel_vivo(text[]) FROM anon;
REVOKE EXECUTE ON FUNCTION public.resolver_alias_panel_vivo(text[]) FROM anon;
