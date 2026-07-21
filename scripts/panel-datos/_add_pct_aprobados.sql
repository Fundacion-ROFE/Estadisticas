-- Agregar columna pct_aprobados a cohorte_ingresos
ALTER TABLE cohorte_ingresos 
ADD COLUMN IF NOT EXISTS pct_aprobados numeric(5, 1);

-- Comentario
COMMENT ON COLUMN cohorte_ingresos.pct_aprobados IS 
'Porcentaje de estudiantes aprobados (avance >= 80%) sobre la cohorte completa (cursaron). 
Incluye activos y retirados que aprobaron. Calculado desde aprobacion_cursos.';

-- Dar lectura a anon (es agregado, no PII)
GRANT SELECT ON cohorte_ingresos TO anon;
