-- Tabla: postulantes_jc
-- Análogo a postulantes_mr, pero la fuente aquí es el backend Mongo de la app
-- Jóvenes creaTIvos (jovenes-creativos.User + Applicant), no un Sheet. Auditoría
-- 2026-07-22 encontró 463 personas reales (tras excluir 3 cuentas admin) sin match
-- en `participants` ni en el Sheet BD Seguimiento de Monitorias — 378 alumnas/os
-- egresados de 2023 nunca cruzados con Q10, + 85 postulantes 2026 recientes.
-- Ver docs/procesos/panel-datos-etl.md#Auditoría Mongo JC.
--
-- NO se mete en `participants` (misma regla que postulantes_mr): esa tabla asume
-- matrícula real en Q10. Puente opcional vía participant_id NULL.

CREATE TABLE IF NOT EXISTS public.postulantes_jc (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  cedula         VARCHAR(20) NOT NULL UNIQUE,
  nombre         VARCHAR(200),
  email          VARCHAR(200),
  celular        VARCHAR(20),
  ciudad         VARCHAR(100),
  promo_year     VARCHAR(10),          -- año de promoción/graduación reportado por la app
  rol            VARCHAR(20),          -- EGRESADO | ACTUAL (rol dentro de la app Mongo)
  fecha_creacion VARCHAR(30),          -- texto crudo (creationDate de Mongo)
  fuente         VARCHAR(20) NOT NULL, -- mongo_user | mongo_applicant — de qué colección Mongo salió
  participant_id UUID REFERENCES public.participants(id),
  created_at     TIMESTAMP DEFAULT NOW(),
  updated_at     TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_postulantes_jc_participant ON public.postulantes_jc(participant_id);
CREATE INDEX IF NOT EXISTS idx_postulantes_jc_email        ON public.postulantes_jc(email);

COMMENT ON TABLE public.postulantes_jc IS
  'Personas del backend Mongo de la app Jóvenes creaTIvos (jovenes-creativos.User/Applicant) sin match en participants ni en el Sheet BD Seguimiento. PII -> RLS sin acceso anon. participant_id NULL = no matriculada en Q10. Análogo a postulantes_mr pero con fuente=Mongo, no Sheet.';

ALTER TABLE public.postulantes_jc ENABLE ROW LEVEL SECURITY;

-- PII sin lectura anónima (mismo criterio que postulantes_mr/emoflow_ingresos).
REVOKE ALL ON public.postulantes_jc FROM anon, authenticated;
