-- ============================================================================
-- 007 — Tabla `retiros`: retiro INDIVIDUAL — ESQUEMA APLICADO 2026-07-23
-- Cierra el gap #1 de la auditoría 2026-07-23: hoy el retiro solo existe como
-- agregado (cohorte_ingresos: 74 JC / 25 MR tras el resync del mismo día) y es
-- la variable de resultado más valiosa para el análisis uso-Emoflow ↔ retención,
-- imposible hoy.
--
-- Aplicado: tabla + índices + RLS + REVOKE (verificado 401 con anon key, suite
-- test_integridad_supabase.py 38/38 PASS). Tabla vacía — el script de sync
-- (sync_retiros.py) sigue sin escribirse, es el siguiente paso pendiente.
--
-- Fuentes individuales disponibles (verificadas):
--   JC: pestaña "Retirados"/"Retirados-complete" del Sheet h2test (pipeline
--       retirados ya la puebla a diario; trae cédula, curso, tipo, fecha) y
--       pestaña "S Retirados" de BD Seguimiento (64 cédulas, con motivo+fecha).
--   MR: pestaña "Inactivas" de BD-Mujeres ROFÉ (33 filas con Motivos/Estado/
--       Año-retiro — ojo: Año-retiro ≈ año de registro de la baja, no cohorte).
--
-- Script de sync propuesto: scripts/panel-datos/sync_retiros.py (por escribir
-- tras aprobar esta migración) — mismo patrón upsert por (participant_id,fecha).
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.retiros (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  participant_id UUID REFERENCES public.participants(id),
  cedula         VARCHAR(20) NOT NULL,      -- llave de cruce aunque no haya participant
  programa       programa_type NOT NULL,
  cohorte        VARCHAR(10) NOT NULL,      -- ej. '2026'
  fecha_retiro   DATE,                      -- NULL si la fuente solo trae año
  anio_retiro    VARCHAR(10),               -- crudo de la fuente cuando no hay fecha
  motivo         VARCHAR(300),
  etapa          VARCHAR(120),              -- último curso completado (ledger, heurística)
  fuente         VARCHAR(40) NOT NULL,      -- sheet_retirados | s_retirados_monitorias | inactivas_mr
  created_at     TIMESTAMP DEFAULT NOW(),
  updated_at     TIMESTAMP DEFAULT NOW(),
  UNIQUE (cedula, cohorte, programa)
);

CREATE INDEX IF NOT EXISTS idx_retiros_participant ON public.retiros(participant_id);
CREATE INDEX IF NOT EXISTS idx_retiros_cohorte     ON public.retiros(cohorte, programa);

COMMENT ON TABLE public.retiros IS
  'Retiros INDIVIDUALES por cohorte×programa (fuentes: Sheet Retirados JC, S Retirados monitorias, Inactivas MR). PII (motivo puede ser sensible) -> RLS sin acceso anon. Complementa el agregado de cohorte_ingresos; test de cuadre: count(retiros cohorte X) ≈ cohorte_ingresos.retirados ± tolerancia.';

ALTER TABLE public.retiros ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.retiros FROM anon, authenticated;

-- Verificación post-aplicación (checklist estándar tabla PII):
--   GET /rest/v1/retiros?select=*&limit=1 con anon key → 401
-- Test de cuadre a agregar en test_integridad_supabase.py tras el primer sync:
--   |count(retiros 2026/jc) − cohorte_ingresos.retirados(2026,jc)| ≤ 3
