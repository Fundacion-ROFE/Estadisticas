-- ============================================================================
-- SCHEMA COMPLETO: Panel de Datos ROFÉ - Supabase PostgreSQL
-- Proyecto: panel-datos-rofe · ID: kbxptoowtnteflhrfwid · Región: us-east-1
-- URL: https://kbxptoowtnteflhrfwid.supabase.co
-- APLICADO el 2026-07-09 vía migraciones MCP:
--   1. schema_base_panel_datos        (este archivo, PASOS 1-6)
--   2. snapshots_diarios_participants (PASO 7, abajo)
-- Verificado: 6 tablas con RLS, advisor de seguridad sin hallazgos, smoke test
--   REST con anon key OK (agregados legibles, PII bloqueada, escritura bloqueada).
-- Fecha: 2026-07-09 (revisado: uuid_generate_v4 → gen_random_uuid, nativo de
--   Postgres 13+, no requiere la extensión uuid-ossp que nunca se creaba)
-- ============================================================================

-- PASO 1: Crear tipos ENUM
-- ============================================================================
CREATE TYPE vivienda_type AS ENUM ('arrendado', 'familiar', 'propia', 'otro');
CREATE TYPE estado_civil_type AS ENUM ('soltero', 'casado', 'divorciado', 'unión_libre', 'otro');
CREATE TYPE nivel_estudio_type AS ENUM ('primaria', 'secundaria', 'técnico', 'profesional', 'postgrado');
CREATE TYPE curso_estado_type AS ENUM ('planeado', 'activo', 'completado');
CREATE TYPE enrollment_estado_type AS ENUM ('inscrito', 'en_progreso', 'completado', 'abandonado');

-- PASO 2: Crear tablas
-- ============================================================================

-- Tabla: participants (Datos demográficos)
CREATE TABLE IF NOT EXISTS participants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  q10_id VARCHAR UNIQUE,
  nombre VARCHAR NOT NULL,
  email VARCHAR,
  ciudad VARCHAR,
  tipo_vivienda vivienda_type,
  estrato INT CHECK (estrato >= 1 AND estrato <= 6),
  edad INT,
  estado_civil estado_civil_type,
  nivel_estudio nivel_estudio_type,
  tiene_emprendimiento BOOLEAN DEFAULT FALSE,
  nombre_emprendimiento VARCHAR,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP,
  is_public BOOLEAN DEFAULT FALSE,
  source_system VARCHAR DEFAULT 'q10'
);

COMMENT ON TABLE participants IS 'Datos demográficos de participantes en programas ROFÉ y Jóvenes creaTIvos';
COMMENT ON COLUMN participants.q10_id IS 'ID externo en plataforma Q10 para reconciliación';
COMMENT ON COLUMN participants.is_public IS 'Si true, datos agregados visibles públicamente en dashboard';

-- Tabla: courses (Catálogo de cursos)
CREATE TABLE IF NOT EXISTS courses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  nombre VARCHAR NOT NULL,
  cohorte VARCHAR NOT NULL,
  fecha_inicio DATE,
  fecha_fin DATE,
  estado curso_estado_type DEFAULT 'planeado',
  created_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE courses IS 'Catálogo de cursos por cohorte (ej: 2024-H1, 2024-H2)';
COMMENT ON COLUMN courses.cohorte IS 'Identificador de cohorte (ej: 2024-H1 = primer semestre 2024)';

-- Tabla: enrollments (Inscripciones)
CREATE TABLE IF NOT EXISTS enrollments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  participant_id UUID NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
  course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
  fecha_inscripcion DATE,
  porcentaje_avance INT CHECK (porcentaje_avance >= 0 AND porcentaje_avance <= 100),
  estado enrollment_estado_type DEFAULT 'inscrito',
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP,
  UNIQUE(participant_id, course_id)
);

COMMENT ON TABLE enrollments IS 'Inscripción de participantes a cursos con seguimiento de progreso';
COMMENT ON COLUMN enrollments.porcentaje_avance IS 'Progreso 0-100% en el curso';
COMMENT ON COLUMN enrollments.estado IS 'Estado actual de la inscripción';

-- Tabla: participant_metrics (Agregados por participante)
CREATE TABLE IF NOT EXISTS participant_metrics (
  participant_id UUID PRIMARY KEY REFERENCES participants(id) ON DELETE CASCADE,
  total_cursos_inscrito INT DEFAULT 0,
  total_cursos_completado INT DEFAULT 0,
  porcentaje_promedio DECIMAL(5,2),
  computed_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE participant_metrics IS 'Métricas agregadas por participante (pre-computadas para performance)';

-- Tabla: cohorte_stats (Estadísticas por cohorte)
CREATE TABLE IF NOT EXISTS cohorte_stats (
  cohorte VARCHAR PRIMARY KEY,
  total_participantes INT DEFAULT 0,
  con_emprendimiento INT DEFAULT 0,
  sin_emprendimiento INT DEFAULT 0,
  porcentaje_con_emprendimiento DECIMAL(5,2),
  edad_promedio DECIMAL(5,2),
  computed_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE cohorte_stats IS 'Estadísticas agregadas por cohorte (pre-computadas)';

-- PASO 3: Crear índices para performance
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_participants_ciudad ON participants(ciudad);
CREATE INDEX IF NOT EXISTS idx_participants_estrato ON participants(estrato);
CREATE INDEX IF NOT EXISTS idx_participants_edad ON participants(edad);
CREATE INDEX IF NOT EXISTS idx_participants_q10_id ON participants(q10_id);
CREATE INDEX IF NOT EXISTS idx_participants_tiene_emprendimiento ON participants(tiene_emprendimiento);

CREATE INDEX IF NOT EXISTS idx_enrollments_participant_id ON enrollments(participant_id);
CREATE INDEX IF NOT EXISTS idx_enrollments_course_id ON enrollments(course_id);
CREATE INDEX IF NOT EXISTS idx_enrollments_estado ON enrollments(estado);
CREATE INDEX IF NOT EXISTS idx_enrollments_porcentaje_avance ON enrollments(porcentaje_avance);

CREATE INDEX IF NOT EXISTS idx_courses_cohorte ON courses(cohorte);
CREATE INDEX IF NOT EXISTS idx_courses_estado ON courses(estado);

-- PASO 4: Habilitar Row Level Security (RLS)
-- ============================================================================

ALTER TABLE participants ENABLE ROW LEVEL SECURITY;
ALTER TABLE courses ENABLE ROW LEVEL SECURITY;
ALTER TABLE enrollments ENABLE ROW LEVEL SECURITY;
ALTER TABLE participant_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE cohorte_stats ENABLE ROW LEVEL SECURITY;

-- PASO 5: Crear políticas RLS - Lectura pública
-- ============================================================================

-- Política: Datos públicos visible a todos (anónimo)
CREATE POLICY "datos_publicos_lectura"
  ON participants FOR SELECT
  USING (is_public = true);

-- Política: Estadísticas por cohorte visible a todos
CREATE POLICY "cohorte_stats_publico"
  ON cohorte_stats FOR SELECT
  USING (true);

-- Política: Catálogo de cursos visible a todos
CREATE POLICY "courses_publico"
  ON courses FOR SELECT
  USING (true);

-- Política: Enrollments públicos (participantes con is_public=true)
CREATE POLICY "enrollments_publico_lectura"
  ON enrollments FOR SELECT
  USING (
    participant_id IN (
      SELECT id FROM participants WHERE is_public = true
    )
  );

-- Política: Métricas públicas (participantes con is_public=true)
CREATE POLICY "metrics_publico_lectura"
  ON participant_metrics FOR SELECT
  USING (
    participant_id IN (
      SELECT id FROM participants WHERE is_public = true
    )
  );

-- PASO 6: Crear políticas RLS - Acceso admin
-- ============================================================================

-- Política: Admin acceso completo a participants
CREATE POLICY "admin_full_access_participants"
  ON participants FOR ALL
  USING (auth.jwt() ->> 'role' = 'admin')
  WITH CHECK (auth.jwt() ->> 'role' = 'admin');

-- Política: Admin acceso completo a courses
CREATE POLICY "admin_full_access_courses"
  ON courses FOR ALL
  USING (auth.jwt() ->> 'role' = 'admin')
  WITH CHECK (auth.jwt() ->> 'role' = 'admin');

-- Política: Admin acceso completo a enrollments
CREATE POLICY "admin_full_access_enrollments"
  ON enrollments FOR ALL
  USING (auth.jwt() ->> 'role' = 'admin')
  WITH CHECK (auth.jwt() ->> 'role' = 'admin');

-- Política: Admin acceso completo a participant_metrics
CREATE POLICY "admin_full_access_metrics"
  ON participant_metrics FOR ALL
  USING (auth.jwt() ->> 'role' = 'admin')
  WITH CHECK (auth.jwt() ->> 'role' = 'admin');

-- Política: Admin acceso completo a cohorte_stats
CREATE POLICY "admin_full_access_cohorte_stats"
  ON cohorte_stats FOR ALL
  USING (auth.jwt() ->> 'role' = 'admin')
  WITH CHECK (auth.jwt() ->> 'role' = 'admin');

-- PASO 7: Snapshots diarios (Decisión 2 escalonada: Type 1 + snapshot barato)
-- Migración: snapshots_diarios_participants
-- ============================================================================

-- El workflow n8n guarda aquí un volcado JSONB de participants ANTES de cada
-- upsert. Cubre auditoría básica y rollback; migrar a SCD Type 2 en Fase 2.
CREATE TABLE IF NOT EXISTS participants_snapshots (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  snapshot_date DATE NOT NULL DEFAULT CURRENT_DATE UNIQUE,
  row_count INT NOT NULL,
  data JSONB NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE participants_snapshots IS 'Snapshot diario de participants previo al upsert n8n (rollback + auditoría básica). UNIQUE(snapshot_date) = idempotente.';

-- RLS: tabla PRIVADA — contiene PII histórica. Sin política pública:
-- solo service_role (n8n) puede leer/escribir.
ALTER TABLE participants_snapshots ENABLE ROW LEVEL SECURITY;

CREATE POLICY "admin_full_access_snapshots"
  ON participants_snapshots FOR ALL
  USING (auth.jwt() ->> 'role' = 'admin')
  WITH CHECK (auth.jwt() ->> 'role' = 'admin');

-- ============================================================================
-- FIN SETUP SCHEMA
-- ============================================================================
-- Verificación:
-- SELECT COUNT(*) FROM participants;  -- debe retornar 0 (tabla vacía)
-- SELECT COUNT(*) FROM courses;
-- SELECT COUNT(*) FROM enrollments;
-- SELECT COUNT(*) FROM participant_metrics;
-- SELECT COUNT(*) FROM cohorte_stats;
-- SELECT COUNT(*) FROM participants_snapshots;
-- ============================================================================
