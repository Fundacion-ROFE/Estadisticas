-- 045 — Tablas de la etapa final de enriquecimiento histórico (2019-2025).
-- ESTADO: PENDIENTE DE APLICAR (el MCP de Supabase se cayó a mitad de sesión 2026-08-12;
-- reintentar con mcp__claude_ai_Supabase__apply_migration en cuanto reconecte).
--
-- Contienen PII (dirección, ingreso, notas, etnia...) → RLS + bloqueadas a anon/authenticated,
-- igual que `participants`/`retiros`. SOLO service_role (cargador + panel privado) las lee.
-- Cargador (`scripts/panel-datos/cargar_enriquecimiento.py`) filtra:
--   (a) participant_id debe existir en `participants` real (excluye postulantes nunca
--       seleccionados) — decisión explícita del usuario 2026-08-12 por cuidado de PII;
--   (b) excluye metodo_match='nombre' (riesgo de homónimos).

CREATE TABLE IF NOT EXISTS enriquecimiento_socioeconomico (
  id bigserial PRIMARY KEY,
  participant_id uuid NOT NULL REFERENCES participants(id),
  campo text NOT NULL,
  valor text,
  fuente_archivo text,
  hoja text,
  anio text,
  metodo_match text NOT NULL CHECK (metodo_match IN ('cedula','email')),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (participant_id, campo, fuente_archivo, hoja, anio, valor)
);

CREATE TABLE IF NOT EXISTS enriquecimiento_empleabilidad (
  id bigserial PRIMARY KEY,
  participant_id uuid NOT NULL REFERENCES participants(id),
  campo text NOT NULL,
  valor text,
  fuente_archivo text,
  hoja text,
  anio text,
  metodo_match text NOT NULL CHECK (metodo_match IN ('cedula','email')),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (participant_id, campo, fuente_archivo, hoja, anio, valor)
);

CREATE TABLE IF NOT EXISTS enriquecimiento_resultados (
  id bigserial PRIMARY KEY,
  participant_id uuid NOT NULL REFERENCES participants(id),
  campo text NOT NULL,
  valor text,
  fuente_archivo text,
  hoja text,
  anio text,
  metodo_match text NOT NULL CHECK (metodo_match IN ('cedula','email')),
  nombre_crudo text,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (participant_id, campo, fuente_archivo, hoja, anio, valor)
);

CREATE TABLE IF NOT EXISTS enriquecimiento_mr_extendido (
  id bigserial PRIMARY KEY,
  participant_id uuid NOT NULL REFERENCES participants(id),
  campo text NOT NULL,
  valor text,
  fuente_archivo text,
  metodo_match text NOT NULL CHECK (metodo_match IN ('cedula','email')),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (participant_id, campo, fuente_archivo, valor)
);

ALTER TABLE enriquecimiento_socioeconomico ENABLE ROW LEVEL SECURITY;
ALTER TABLE enriquecimiento_empleabilidad  ENABLE ROW LEVEL SECURITY;
ALTER TABLE enriquecimiento_resultados     ENABLE ROW LEVEL SECURITY;
ALTER TABLE enriquecimiento_mr_extendido   ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON enriquecimiento_socioeconomico FROM anon, authenticated;
REVOKE ALL ON enriquecimiento_empleabilidad  FROM anon, authenticated;
REVOKE ALL ON enriquecimiento_resultados     FROM anon, authenticated;
REVOKE ALL ON enriquecimiento_mr_extendido   FROM anon, authenticated;

CREATE INDEX IF NOT EXISTS idx_enr_socio_participant ON enriquecimiento_socioeconomico(participant_id);
CREATE INDEX IF NOT EXISTS idx_enr_empleo_participant ON enriquecimiento_empleabilidad(participant_id);
CREATE INDEX IF NOT EXISTS idx_enr_result_participant ON enriquecimiento_resultados(participant_id);
CREATE INDEX IF NOT EXISTS idx_enr_mr_participant ON enriquecimiento_mr_extendido(participant_id);
