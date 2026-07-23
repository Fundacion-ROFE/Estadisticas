-- ============================================================================
-- 006 — Endurecimiento de seguridad — APLICADA PARCIALMENTE 2026-07-23
-- Samuel aprobó el bloque completo. Al revisar dependencias ANTES de ejecutar
-- (mismo hábito que ya evitó un incidente horas antes con el REVOKE de
-- `participants`) se encontraron 2 bloques que romperían funcionalidad real —
-- se aplicaron los 6 bloques seguros, se descartaron 2 permanentemente.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- (1) ❌ NO APLICADO — descartado permanentemente
-- participa_en(): revocar EXECUTE a anon rompía 4 vistas públicas que la usan
-- internamente y SÍ reciben tráfico anon real: v_demografia_grupo,
-- v_edad_distribucion, v_emprendimiento_situacion, v_emprendimiento_vs_cursos
-- (verificado: SELECT viewname FROM pg_views WHERE definition ILIKE '%participa_en%').
-- La función sigue expuesta por RPC (WARN de bajo impacto real: solo permite
-- sondear membresía por uuid ya conocido, sin enumeración posible de uuids).
-- REVOKE EXECUTE ON FUNCTION public.participa_en(uuid, programa_type) FROM anon, authenticated;

-- ----------------------------------------------------------------------------
-- (2) ✅ APLICADO 2026-07-23
-- es_publico(): expuesta vía RPC pero SÍ la usan 2 policies (enrollments_
-- publico_lectura, metrics_publico_lectura) evaluadas como anon. Fix sin
-- romperlas: mover a schema no expuesto por PostgREST (las policies
-- referencian por OID, sobreviven el move).
-- Verificado: POST /rpc/es_publico anon → 404 · GET /enrollments anon → 200+[]
CREATE SCHEMA IF NOT EXISTS interno;
GRANT USAGE ON SCHEMA interno TO anon, authenticated;
ALTER FUNCTION public.es_publico(uuid) SET SCHEMA interno;

-- ----------------------------------------------------------------------------
-- (3) ✅ APLICADO 2026-07-23
-- asistencia_zoom: policy UPDATE mal formada (USING implícito = true). Sin
-- exposición real (anon sin GRANT en la tabla desde 2026-07-14), pero quedaba
-- como trampa futura.
DROP POLICY IF EXISTS "asistencia_update_admin" ON public.asistencia_zoom;
CREATE POLICY "asistencia_update_admin" ON public.asistencia_zoom
  FOR UPDATE
  USING ((auth.jwt() ->> 'role') = 'service_role')
  WITH CHECK ((auth.jwt() ->> 'role') = 'service_role');

-- ----------------------------------------------------------------------------
-- (4) ❌ NO APLICADO — descartado permanentemente
-- v_puntaje_estudiante SÍ tiene consumidor real: scripts/panel-datos/
-- reporte_puntaje.py (ranking de estudiantes, vía service_role). La vista ya
-- estaba correctamente bloqueada para anon (401, verificado antes Y después
-- del resto de esta migración) — el DROP no era mejora de seguridad, solo
-- rompía una herramienta activa.
-- DROP VIEW IF EXISTS public.v_puntaje_estudiante;

-- ----------------------------------------------------------------------------
-- (5) ✅ APLICADO 2026-07-23
-- Documentar como decisión INTENCIONAL las tablas PII que dependen solo de
-- "RLS sin policy" (efecto correcto: solo service_role; sin policy explícita
-- porque no la necesitan — service_role bypasea RLS).
COMMENT ON TABLE public.postulantes_mr  IS 'Universo completo de postulantes/candidatas Mujeres ROFÉ. PII: acceso SOLO service_role (RLS sin policy + REVOKE anon/authenticated = intencional, decisión 2026-07-23).';
COMMENT ON TABLE public.postulantes_jc  IS 'Personas del Mongo de la app JC. PII: acceso SOLO service_role (RLS sin policy + REVOKE = intencional, decisión 2026-07-23).';
COMMENT ON TABLE public.email_optout    IS 'Opt-out de campañas. PII: SOLO service_role (RLS sin policy + REVOKE = intencional, 2026-07-23).';
COMMENT ON TABLE public.email_bounces   IS 'Rebotes de correo. PII: SOLO service_role (RLS sin policy + REVOKE = intencional, 2026-07-23).';
COMMENT ON TABLE public.campanas_enviadas IS 'Log agregado de campañas (sin correos individuales). SOLO service_role por defecto (RLS sin policy = intencional, 2026-07-23).';
COMMENT ON TABLE public.asistencia_promedio IS 'Asistencia promedio por estudiante (email=PII). SOLO service_role; policy permisiva revocada tras incidente 2026-07-14. RLS sin policy = intencional (2026-07-23).';

-- ----------------------------------------------------------------------------
-- (6) ✅ APLICADO 2026-07-23 (corregido respecto a la propuesta original)
-- Supresión de celdas pequeñas en v_demografia_grupo (k-anonimato): 3 celdas
-- con n<5 (ej. otros_genero=1 en BAQ) revelaban el marcador de género de una
-- persona única. La propuesta original OMITÍA el filtro `participa_en(id,'jc')`
-- de la vista real (confirmado con pg_get_viewdef antes de aplicar) — se
-- corrigió para preservarlo. Verificado: la vista sigue devolviendo 9 ciudades
-- (solo JC) y ahora otros_genero sale NULL donde antes había conteos <5.
CREATE OR REPLACE VIEW public.v_demografia_grupo AS
SELECT grupo_ciudad,
       count(*) AS total,
       round(avg(edad), 1) AS edad_promedio,
       CASE WHEN count(*) FILTER (WHERE genero::text = 'Femenino'::text) < 5 THEN NULL
            ELSE count(*) FILTER (WHERE genero::text = 'Femenino'::text) END AS mujeres,
       CASE WHEN count(*) FILTER (WHERE genero::text = 'Masculino'::text) < 5 THEN NULL
            ELSE count(*) FILTER (WHERE genero::text = 'Masculino'::text) END AS hombres,
       CASE WHEN count(*) FILTER (WHERE genero::text <> ALL (ARRAY['Femenino'::character varying, 'Masculino'::character varying]::text[])) < 5 THEN NULL
            ELSE count(*) FILTER (WHERE genero::text <> ALL (ARRAY['Femenino'::character varying, 'Masculino'::character varying]::text[])) END AS otros_genero
FROM public.participants p
WHERE grupo_ciudad IS NOT NULL AND participa_en(id, 'jc'::programa_type)
GROUP BY grupo_ciudad;
-- Pendiente de Samuel: confirmar visualmente en el frontend Netlify que las
-- celdas NULL se grafican bien (no se pudo verificar el código del frontend
-- desde esta sesión — vive en un repo aparte).

-- ----------------------------------------------------------------------------
-- (7) ✅ APLICADO 2026-07-23
-- Limpieza: 3 participants con edad=0 (BD monitorias trae "0" como
-- desconocido). El sync ya tiene clamp [10,90] agregado el mismo día
-- (sync_sociodemograficos.py) pero el upsert no pisaba con NULL registros viejos.
UPDATE public.participants SET edad = NULL WHERE edad = 0;

-- ----------------------------------------------------------------------------
-- (8) ✅ APLICADO 2026-07-23
-- Fila huérfana en emoflow_ingresos (fecha_corte=2026-07-21, el sync API ya
-- no la ve — usuario desaparecido del CSV, acumulado no verificable contra la fuente).
DELETE FROM public.emoflow_ingresos WHERE fecha_corte < CURRENT_DATE - INTERVAL '2 days';
