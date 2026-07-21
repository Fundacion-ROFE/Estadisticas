-- Tabla: emoflow_actividad_semanal
-- Actividad SEMANAL real por ciudad, derivada del CSV de Emoflow (100% Emoflow, sin la hoja
-- de monitorías). La alimenta extract_emoflow_ingresos_diario.py (misma corrida que la diaria).
-- Reemplaza la "participación semanal" que venía del Sheet de seguimiento.
--
-- Métrica: usuarios activos únicos por semana ÷ roster de la ciudad (matrícula Emoflow = personas
-- alguna vez activas). La semana se etiqueta por su LUNES ISO → eje X en orden temporal correcto.

CREATE TABLE IF NOT EXISTS public.emoflow_actividad_semanal (
  semana_inicio DATE NOT NULL,                 -- lunes ISO de la semana
  grupo_ciudad VARCHAR(10) NOT NULL,           -- BAQ..UY o NACIONAL
  usuarios_activos INT NOT NULL DEFAULT 0,     -- personas distintas activas esa semana
  roster INT NOT NULL DEFAULT 0,               -- matrícula Emoflow de la ciudad (distinct histórico)
  pct_activos NUMERIC(5,1) NOT NULL DEFAULT 0, -- 100 * activos / roster
  fuente VARCHAR(40) DEFAULT 'emoflow-csv',
  updated_at TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY (semana_inicio, grupo_ciudad)
);

CREATE INDEX IF NOT EXISTS idx_emoflow_actsem_semana ON public.emoflow_actividad_semanal(semana_inicio);

ALTER TABLE public.emoflow_actividad_semanal ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Lectura publica emoflow_actividad_semanal" ON public.emoflow_actividad_semanal;
CREATE POLICY "Lectura publica emoflow_actividad_semanal"
  ON public.emoflow_actividad_semanal FOR SELECT USING (TRUE);
