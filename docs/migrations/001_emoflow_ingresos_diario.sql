-- Tabla: emoflow_ingresos_diario
-- Serie DIARIA REAL de ingresos a Emoflow por ciudad (+ fila NACIONAL por día).
-- Fuente: timestamps del CSV /admin/registro-ingresos-exportar (columna "Fecha emociones").
-- La alimenta scripts/panel-datos/extract_emoflow_ingresos_diario.py (upsert idempotente,
-- re-lee todo el histórico ~120 días en cada corrida).
-- Reemplaza el backfill plano de historial_emoflow (que repetía un mismo valor).

CREATE TABLE IF NOT EXISTS public.emoflow_ingresos_diario (
  fecha DATE NOT NULL,
  grupo_ciudad VARCHAR(10) NOT NULL,          -- BAQ, BOG, CAL, CTG, MED, GYL, QTO, PAN, UY o NACIONAL
  ingresos INT NOT NULL DEFAULT 0,            -- check-ins (emociones) ese día en esa ciudad
  usuarios_activos INT NOT NULL DEFAULT 0,    -- usuarios únicos con ≥1 ingreso ese día
  fuente VARCHAR(40) DEFAULT 'emoflow-csv',
  updated_at TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY (fecha, grupo_ciudad)
);

CREATE INDEX IF NOT EXISTS idx_emoflow_diario_fecha  ON public.emoflow_ingresos_diario(fecha);
CREATE INDEX IF NOT EXISTS idx_emoflow_diario_ciudad ON public.emoflow_ingresos_diario(grupo_ciudad);

ALTER TABLE public.emoflow_ingresos_diario ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Lectura publica emoflow_ingresos_diario" ON public.emoflow_ingresos_diario;
CREATE POLICY "Lectura publica emoflow_ingresos_diario"
  ON public.emoflow_ingresos_diario FOR SELECT USING (TRUE);
