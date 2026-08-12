-- 046 — postulantes_mr: campos ricos del CSV "Plataforma MR" (APLICADA 2026-08-12 vía MCP)
-- ============================================================================
-- Pedido del usuario: llenar el historial completo de las ~5.157 mujeres del export de la
-- plataforma — a las que ya tienen participant_id (Q10 real) se les añade la info a
-- `enriquecimiento_mr_extendido` + backfill de columnas nativas de `participants`; a las
-- que NO tienen participant_id se les agrega esta misma info aquí, en `postulantes_mr`
-- (que es el universo COMPLETO de candidatas, con o sin matrícula), para no perderlas.
-- Mismo vocabulario de campos que enriquecimiento_mr_extendido (cluster F, 2026-08-12) para
-- no crear una segunda taxonomía. Todo TEXT (nunca ENUM) — se llena tal cual viene, null si
-- no hay dato, nunca se inventa. Cargador: scripts/panel-datos/cargar_plataforma_mr_completa.py
-- ============================================================================
ALTER TABLE postulantes_mr
  ADD COLUMN IF NOT EXISTS direccion text,
  ADD COLUMN IF NOT EXISTS presentacion_personal text,
  ADD COLUMN IF NOT EXISTS personas_nucleo text,
  ADD COLUMN IF NOT EXISTS ingresos_familiares text,
  ADD COLUMN IF NOT EXISTS canal_adquisicion text,
  ADD COLUMN IF NOT EXISTS grupo_etnico text,
  ADD COLUMN IF NOT EXISTS sostenimiento text;

COMMENT ON COLUMN postulantes_mr.direccion IS
 'Dirección de residencia — fuente: BD-Mujeres ROFÉ 2026 - Plataforma MR.csv (2026-08-12).';
COMMENT ON COLUMN postulantes_mr.canal_adquisicion IS
 '¿Por dónde conoció Mujeres ROFÉ? — mismo campo que enriquecimiento_mr_extendido.canal_adquisicion.';
