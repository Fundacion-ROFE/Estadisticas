-- Normalización de ciudad: función pura (IMMUTABLE) + columna generada + tabla de alias
-- para mismos-municipios-con-nombres-distintos (Bogotá vs Bogotá D.C., Cartagena vs
-- Cartagena de Indias, etc). Aplicada vía Supabase MCP (apply_migration) el 2026-07-24.
--
-- Origen: incidente 2026-07-24 (ver claude_sessions.md y memoria
-- project_supabase_mr_sincronizacion_gap) — una consulta a postulantes_mr filtrando
-- ciudad='BOGOTA' con 'BOGOTA' in ciudad.upper() descartó 431/512 filas porque
-- .upper() no quita tildes ("BOGOTÁ" != "BOGOTA" como substring). Ver también
-- docs/convenciones.md "Normalización de ciudades" (problema documentado 2026-07-24,
-- resuelto con esta migración).

CREATE OR REPLACE FUNCTION public.normalizar_ciudad(valor text)
RETURNS text
LANGUAGE sql
IMMUTABLE
PARALLEL SAFE
AS $$
  SELECT NULLIF(
    trim(
      regexp_replace(
        regexp_replace(
          upper(translate(valor, 'ÁÉÍÓÚÑÜáéíóúñü', 'AEIOUNUaeiounu')),
          '[^A-Z0-9 ]', '', 'g'
        ),
        '\s+', ' ', 'g'
      )
    ),
    ''
  )
$$;

COMMENT ON FUNCTION public.normalizar_ciudad(text) IS
  'Quita tildes/mayúsculas/puntuación de un texto de ciudad para comparación (BOGOTA = Bogotá = BOGOTA D.C -> distinto de BOGOTA DC). No expande alias de mismo-municipio-distinto-nombre; para eso usar ciudad_alias.';

-- Columna generada (se recalcula sola, no requiere backfill ni mantenimiento):
ALTER TABLE public.participants   ADD COLUMN IF NOT EXISTS ciudad_norm text GENERATED ALWAYS AS (public.normalizar_ciudad(ciudad)) STORED;
ALTER TABLE public.postulantes_mr ADD COLUMN IF NOT EXISTS ciudad_norm text GENERATED ALWAYS AS (public.normalizar_ciudad(ciudad)) STORED;
ALTER TABLE public.postulantes_jc ADD COLUMN IF NOT EXISTS ciudad_norm text GENERATED ALWAYS AS (public.normalizar_ciudad(ciudad)) STORED;

CREATE INDEX IF NOT EXISTS idx_participants_ciudad_norm   ON public.participants(ciudad_norm);
CREATE INDEX IF NOT EXISTS idx_postulantes_mr_ciudad_norm ON public.postulantes_mr(ciudad_norm);
CREATE INDEX IF NOT EXISTS idx_postulantes_jc_ciudad_norm ON public.postulantes_jc(ciudad_norm);

COMMENT ON COLUMN public.participants.ciudad_norm IS 'normalizar_ciudad(ciudad) — usar este campo para filtrar por ciudad, nunca el crudo.';
COMMENT ON COLUMN public.postulantes_mr.ciudad_norm IS 'normalizar_ciudad(ciudad) — usar este campo para filtrar por ciudad, nunca el crudo.';
COMMENT ON COLUMN public.postulantes_jc.ciudad_norm IS 'normalizar_ciudad(ciudad) — usar este campo para filtrar por ciudad, nunca el crudo.';

-- Alias: mismo municipio, nombre administrativo distinto (no lo resuelve normalizar_ciudad
-- porque son palabras distintas, no solo tildes/puntuación). clave_norm = valor ya pasado
-- por normalizar_ciudad(); ciudad_canonica = bajo qué llave agrupar.
CREATE TABLE IF NOT EXISTS public.ciudad_alias (
  clave_norm      text PRIMARY KEY,
  ciudad_canonica text NOT NULL,
  nota            text,
  creado_en       timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.ciudad_alias IS
  'Fuente única de verdad para fusionar variantes de ciudad que normalizar_ciudad() no puede resolver solo (mismo municipio, nombre distinto). Editar aquí, no en cada script. Sin PII, pero RLS bloqueado a service_role por consistencia con el resto de tablas base.';

ALTER TABLE public.ciudad_alias ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.ciudad_alias FROM anon, authenticated;

INSERT INTO public.ciudad_alias (clave_norm, ciudad_canonica, nota) VALUES
  ('BOGOTA DC',           'BOGOTA',    'nombre administrativo completo vs común'),
  ('BGT',                 'BOGOTA',    'abreviatura vista en peticiones informales'),
  ('CARTAGENA DE INDIAS', 'CARTAGENA', 'nombre oficial completo vs común'),
  ('CIUDAD DE PANAMA',    'PANAMA',    'nombre completo vs común')
ON CONFLICT (clave_norm) DO NOTHING;

-- Función de consulta: ciudad_canonica(texto) = agrupador final, para usar en reportes SQL.
-- (Los scripts Python vía PostgREST no pueden llamar esta función en un filtro; para eso
-- usan ciudad_utils.py, que expande el filtro a una lista de ciudad_norm vía IN.)
CREATE OR REPLACE FUNCTION public.ciudad_canonica(valor text)
RETURNS text
LANGUAGE sql
STABLE
AS $$
  SELECT COALESCE(
    (SELECT a.ciudad_canonica FROM public.ciudad_alias a WHERE a.clave_norm = public.normalizar_ciudad(valor)),
    public.normalizar_ciudad(valor)
  )
$$;

COMMENT ON FUNCTION public.ciudad_canonica(text) IS
  'normalizar_ciudad() + fusión vía ciudad_alias. Usar en SELECT/GROUP BY de reportes SQL directos. PostgREST no permite filtrar por esta función — para filtros desde scripts usar ciudad_utils.py (expande a ciudad_norm IN (...)).';

-- Verificado tras aplicar (2026-07-24): postulantes_mr WHERE ciudad_norm IN ('BOGOTA','BOGOTA DC')
-- = 508 filas (vs 504 del Excel "Base Mr Bogotá.xlsx" — coincide). Antes de esta migración,
-- el bug de tildes en un script ad-hoc había reportado solo 24.
