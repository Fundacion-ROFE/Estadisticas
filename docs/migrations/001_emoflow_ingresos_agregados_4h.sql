-- Tabla: emoflow_ingresos_agregados_4h
-- Descripción: Snapshots agregados de Emoflow cada 4 horas
-- Métricas: % participación, distribución de ingresos, velocidad intra-día
-- Reemplaza: historial_emoflow (datos redundantes, acumulativos)

CREATE TABLE IF NOT EXISTS public.emoflow_ingresos_agregados_4h (
  id BIGSERIAL PRIMARY KEY,
  fecha DATE NOT NULL,
  hora_snapshot TIMESTAMP NOT NULL,
  grupo_ciudad VARCHAR(10) NOT NULL DEFAULT 'NACIONAL',

  -- Emociones
  pct_participacion_emociones DECIMAL(5,2),
  nuevos_ingresos_emociones INT DEFAULT 0,
  velocidad_ingresos_emociones DECIMAL(5,2),

  -- Bienestar
  pct_participacion_bienestar DECIMAL(5,2),
  nuevos_ingresos_bienestar INT DEFAULT 0,
  velocidad_ingresos_bienestar DECIMAL(5,2),

  -- Totales y distribución
  nuevos_ingresos_4h INT DEFAULT 0,
  velocidad_ingresos_4h DECIMAL(5,2),

  -- Distribución (% en cada rango)
  pct_sin_ingresos DECIMAL(5,2),
  pct_rango_1_5 DECIMAL(5,2),
  pct_rango_6_15 DECIMAL(5,2),
  pct_rango_16_30 DECIMAL(5,2),
  pct_rango_31_60 DECIMAL(5,2),
  pct_rango_61plus DECIMAL(5,2),

  fuente VARCHAR(50) DEFAULT 'emoflow-api-4h',
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Índice único: una sola entrada por fecha/hora/ciudad
CREATE UNIQUE INDEX IF NOT EXISTS idx_emoflow_agg_4h
  ON public.emoflow_ingresos_agregados_4h(fecha, hora_snapshot, grupo_ciudad);

-- Índice para búsquedas por fecha
CREATE INDEX IF NOT EXISTS idx_emoflow_agg_4h_fecha
  ON public.emoflow_ingresos_agregados_4h(fecha DESC);

-- Índice para búsquedas por ciudad
CREATE INDEX IF NOT EXISTS idx_emoflow_agg_4h_ciudad
  ON public.emoflow_ingresos_agregados_4h(grupo_ciudad);

-- RLS: tabla pública (lectura anon-key)
ALTER TABLE public.emoflow_ingresos_agregados_4h ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Lectura pública para emoflow_ingresos_agregados_4h"
  ON public.emoflow_ingresos_agregados_4h
  FOR SELECT USING (TRUE);

CREATE POLICY "Escritura solo con service-role-key"
  ON public.emoflow_ingresos_agregados_4h
  FOR INSERT WITH CHECK (auth.role() = 'service_role');

CREATE POLICY "Update solo con service-role-key"
  ON public.emoflow_ingresos_agregados_4h
  FOR UPDATE USING (auth.role() = 'service_role');

-- Comentarios para documentación
COMMENT ON TABLE public.emoflow_ingresos_agregados_4h IS 'Snapshots agregados de Emoflow cada 4 horas: % participación, velocidad, distribución';
COMMENT ON COLUMN public.emoflow_ingresos_agregados_4h.pct_participacion_emociones IS '% del cohorte que ingresó a Emociones';
COMMENT ON COLUMN public.emoflow_ingresos_agregados_4h.velocidad_ingresos_4h IS 'Ingresos/hora durante las últimas 4 horas';
COMMENT ON COLUMN public.emoflow_ingresos_agregados_4h.grupo_ciudad IS 'BAQ, BOG, CAL, CTG, MED, GYL, QTO, PAN, UY, o NACIONAL (agregado)';
