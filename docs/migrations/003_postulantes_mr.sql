-- Tabla: postulantes_mr
-- Universo completo de postulantes/candidatas de Mujeres ROFÉ, tabla PARALELA a
-- `participants` (que solo cubre matriculadas en Q10). Fuente: Sheet BD-Mujeres ROFÉ
-- (id 1ZsC4WyY26aOCEMrnZ_l8Tn-l69DB_0ADs5lnecaoEP8), pestañas General/Inactivas
-- (fuente primaria de demografía) + Cursos/Cursos%/Plataforma MR (aportan 193
-- cédulas que no están en General∪Inactivas, confirmado en auditoría Fase 0
-- 2026-07-22, ver docs/procesos/postulantes-mr-supabase.md).
--
-- NO se mete en `participants`: esa tabla alimenta ~15 vistas agregadas que asumen
-- matrícula real (cohorte_ingresos, v_programa_stats, etc). Puente opcional vía
-- participant_id NULL, mismo patrón que emoflow_ingresos.

CREATE TABLE IF NOT EXISTS public.postulantes_mr (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  cedula                VARCHAR(20) NOT NULL UNIQUE,
  nombre                VARCHAR(200),
  email                 VARCHAR(200),
  celular               VARCHAR(20),
  ciudad                VARCHAR(100),
  estado                VARCHAR(100),         -- texto crudo de la columna "Estado" del Sheet (General/Inactivas)
  fecha_creacion        VARCHAR(30),          -- texto crudo (formatos inconsistentes entre pestañas); no castear a DATE
  edad                  INT CHECK (edad >= 14 AND edad <= 90),
  nivel_estudio         nivel_estudio_type,
  estrato               INT CHECK (estrato >= 1 AND estrato <= 6),
  estado_civil          estado_civil_type,
  tipo_vivienda         vivienda_type,
  nombre_emprendimiento VARCHAR(200),
  tiene_emprendimiento  BOOLEAN,
  genero                VARCHAR(20) DEFAULT 'Femenino',
  fuente_pestana        VARCHAR(40) NOT NULL, -- general | inactivas | cursos | cursos_pct | plataforma_mr
                                               -- (ampliado 2026-07-22: fusiones registran "general+<origen>")
  participant_id        UUID REFERENCES public.participants(id),
  created_at            TIMESTAMP DEFAULT NOW(),
  updated_at            TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_postulantes_mr_participant ON public.postulantes_mr(participant_id);
CREATE INDEX IF NOT EXISTS idx_postulantes_mr_email        ON public.postulantes_mr(email);

COMMENT ON TABLE public.postulantes_mr IS
  'Universo completo de postulantes/candidatas Mujeres ROFÉ (Sheet BD-Mujeres ROFÉ, todas las pestañas con cédula). PII -> RLS sin acceso anon. participant_id NULL = no llegó a matricularse en Q10 (mayoría esperada). No confundir con participants (solo matriculadas).';

ALTER TABLE public.postulantes_mr ENABLE ROW LEVEL SECURITY;

-- PII sin lectura anónima (mismo criterio que emoflow_ingresos/email_bounces):
-- no basta con "no dar GRANT" — Supabase concede SELECT a anon por defecto en public.
REVOKE ALL ON public.postulantes_mr FROM anon, authenticated;
