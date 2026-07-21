# Plan de Datos: Análisis Profundo + Refinamiento
**Fecha:** 2026-07-09 | **Autor:** Claude + Samuel | **Estado:** Documentación Ejecutable

---

## 🎯 Objetivo Final
Reemplazar Power BI por un **panel profesional de visualización de datos** alimentado por **PostgreSQL (Supabase) + Netlify**, permitiendo que cualquier persona (estudiantes, profesores, contadores, programadores) acceda a insights limpios y actualizados sobre participantes de ROFÉ y Jóvenes creaTIvos.

---

## 📋 ANÁLISIS CRÍTICO DEL PLAN ORIGINAL

### ✅ Fortalezas
- **Arquitectura modular existente:** n8n + Google Workspace ya integrados
- **Privacidad resuelta:** PII en `tools/` gitignoreado, públicos en `docs/`
- **Documentación clara:** CLAUDE.md establece convenciones sólidas
- **Incrementalismo:** "un proceso a la vez" evita overload

### ⚠️ Gaps e Incompletitudes Detectadas

#### 1. **Confusión sobre la BD de origen**
- **Problema:** Se menciona "MySQL" pero Q10 es una plataforma de terceros
- **Clarificación necesaria:** ¿De dónde viene la "BD limpia" si actualmente extraemos de Q10 con Google Sheets?
- **Solución propuesta:** Crear BD limpia en Supabase (PostgreSQL) como fuente única de verdad

#### 2. **Falta de schema de datos definido**
- **Problema:** Se piden métricas (% cursos, emprendimiento, perfil sociodemográfico) sin definir estructura
- **Gap:** Sin esquema ERD, es imposible diseñar queries y transformaciones
- **Impacto en Claude Code:** Los scripts no sabrán qué tablas/campos crear

#### 3. **Migracion de datos no planificada**
- **Problema:** "Rehacemos la BD" suena simple pero implica ETL complejo
- **Riesgos:** Pérdida de datos históricos, inconsistencias durante transición, downtime
- **Decisión pendiente:** ¿Migración big-bang o gradual por cohorte?

#### 4. **Falta de pipeline ETL claro**
- **Problema:** ¿Cómo flujo Q10 → Supabase → Netlify dashboard?
- **Hoy:** Q10 → Google Sheets → export JSON → GitHub → GitHub Pages
- **Futuro:** Q10 → [??? ETL ???] → Supabase → [??? API ???] → Netlify
- **Gap:** No hay especificación de transformaciones intermedias

#### 5. **Herramienta BI no decidida**
- **Problema:** Dices "reemplazar Power BI" pero ¿con qué?
- **Opciones descartadas/consideradas:** (ver sección herramientas recomendadas)
- **Decisión pendiente:** ¿Dashboard custom (React + Charts.js)? ¿Metabase? ¿Apache Superset?

#### 6. **Responsabilidades de "cualquier persona" indefinidas**
- **Problema:** "estudiantes, profesores, contadores, programadores" usan el panel ≠ todos lo actualizan
- **Clarificación:** ¿Quién edita datos? ¿Quién genera reportes? ¿Permisos por rol?
- **Impacto:** Afecta Row Level Security (RLS) en Supabase

#### 7. **Ausencia de especificación visual**
- **Problema:** Se nombran 8-10 tipos de gráficos pero sin wireframes
- **Gap:** Claude Code necesitará mockups o descripción visual estructurada
- **Ejemplo:** "relación visual fuerte entre emprendimiento y cursos" → ¿scatter plot? ¿heatmap? ¿bubble chart?

#### 8. **Origen de datos sociodemográficos sin confirmar** ⚠️ (agregado en revisión)
- **Problema:** El schema pide `tipo_vivienda`, `estrato`, `estado_civil`, `nivel_estudio`, pero las
  pestañas reales del Sheet de Q10 son `h2test`, `Avance`, `Retirados`, `asistencias` — ninguna
  "Perfil Sociodemográfico" confirmada.
- **Fuentes candidatas:** BD-Mujeres ROFÉ (form MR2024, ver [[mr-actualizacion-datos]]) y la
  BD Seguimiento de Monitorías (ver [[bd-seguimiento-monitorias]], pestañas Diagnostico/Nivelación).
- **Acción:** Confirmar fuente ANTES de Fase 1a — el script de normalización no puede escribirse sin esto.

#### 9. **Definición de "retirado" ya existe y difiere de la propuesta** ⚠️ (agregado en revisión)
- **Problema:** Este plan propone churn = "0% avance + 3 meses sin actividad", pero el proyecto YA tiene
  una definición canónica: pestaña Retirados de Q10, con desertores excluidos de todas las estadísticas
  e identidad verificada `832 = 775 activos + 57 retirados` (ver claude_sessions.md 2026-07-09).
- **Riesgo:** Dos dashboards mostrando números distintos de retirados destruye la confianza en los datos.
- **Acción:** El panel nuevo DEBE consumir/replicar la lógica de `export_aprobacion.py` / `export_retirados.py`,
  no inventar una heurística paralela.

---

## 🏗️ ARQUITECTURA TÉCNICA REFINADA

### Flujo Datos (Propuesta)

```
Q10 API / Google Sheets
    ↓
  [n8n Workflow: q10-sync-supabase]
    ↓
Supabase PostgreSQL (Fuente Única de Verdad)
    ├── Raw Tables (datos crudos con timestamp)
    ├── Cleaned Tables (datos limpios, deduplicados)
    └── Aggregated Tables (métricas pre-computadas)
    ↓
  [n8n Workflow: export-dashboard-json]
    ↓
Supabase Edge Functions / API REST
    ↓
  [Netlify Functions / Next.js SSR]
    ↓
Netlify Deployed Dashboard (React + Recharts)
    ↓
    Usuarios finales (estudiantes, profesores, etc.)
```

### Capas Propuestas

#### Capa 1: Ingesta (n8n)
- **Responsabilidad:** Traer datos de Q10 / Google Sheets → Supabase
- **Frecuencia:** Diaria (04:00 UTC)
- **Validación:** No duplicados, tipos correctos, fecha actualización
- **Rollback:** Snapshot diario en `_backup` table

#### Capa 2: Almacenamiento (Supabase PostgreSQL)
- **Responsabilidad:** Fuente única de verdad, RLS, auditoría
- **Estructura:** Raw → Cleaned → Aggregated (3-layer)
- **Backups:** ⚠️ los backups diarios automáticos son solo del plan Pro (~USD 25/mes).
  En free tier NO hay backups → snapshot diario propio vía n8n (`pg_dump` o export JSON).
  Free tier además **pausa el proyecto tras ~1 semana sin actividad** — el sync diario lo
  mantiene vivo, pero si el PC de n8n queda apagado una semana, el dashboard público muere.
- **Query optimization:** Índices en campos filtrados, materialized views para agregados

#### Capa 3: API (Supabase REST / Edge Functions)
- **Responsabilidad:** Exponer datos via REST JSON
- **Auth:** Service account (lectura pública), JWT (escritura si es necesario)
- **Caching:** CDN + Cache-Control headers (max-age=3600)
- **Rate limiting:** ⚠️ Supabase NO ofrece rate limiting por IP en la REST API (solo en Auth).
  Mitigación real: caching agresivo en CDN y, si hiciera falta, proxy vía Netlify Functions.

#### Capa 4: Frontend (Netlify + React)
- **Responsabilidad:** Renderizar dashboard + filtros interactivos
- **Framework:** Next.js (SSR) para SEO + performance
- **State:** React Query (SWR) para fetch + caching
- **Visualización:** Recharts (built-in, no deps externas)

---

## 📊 SCHEMA DE DATOS PROPUESTO

### Tablas Core (PostgreSQL en Supabase)

> ⚠️ **Nota de revisión:** PostgreSQL NO soporta `ENUM(...)` inline (eso es sintaxis MySQL) —
> requiere `CREATE TYPE ... AS ENUM` previo. El schema **canónico y ejecutable** vive en
> `schema-supabase-completo.sql` (raíz del repo); este bloque es solo referencia conceptual.
> Nota semántica: en este proyecto la **cohorte es del participante** (ej. "cohorte 2026" con su
> ruta de cursos), no del curso tipo "2024-H1" — validar el modelo antes de cargar datos.

```sql
-- Raw (sin transformación)
participants (
  id UUID PRIMARY KEY,
  q10_id VARCHAR UNIQUE,  -- ID en Q10 para reconciliación
  nombre VARCHAR,
  email VARCHAR,
  ciudad VARCHAR,
  tipo_vivienda ENUM('arrendado', 'familiar', 'propia', 'otro'),
  estrato INT,
  edad INT,
  estado_civil ENUM('soltero', 'casado', 'divorciado', 'unión_libre', 'otro'),
  nivel_estudio ENUM('primaria', 'secundaria', 'técnico', 'profesional', 'postgrado'),
  tiene_emprendimiento BOOLEAN,
  nombre_emprendimiento VARCHAR,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP,
  source_system VARCHAR DEFAULT 'q10'  -- Para auditoría
);

courses (
  id UUID PRIMARY KEY,
  nombre VARCHAR,
  cohorte VARCHAR,  -- "2024-H1", "2024-H2", etc.
  fecha_inicio DATE,
  fecha_fin DATE,
  estado ENUM('planeado', 'activo', 'completado'),
  created_at TIMESTAMP
);

enrollments (
  id UUID PRIMARY KEY,
  participant_id UUID REFERENCES participants,
  course_id UUID REFERENCES courses,
  fecha_inscripcion DATE,
  porcentaje_avance INT,  -- 0-100
  estado ENUM('inscrito', 'en_progreso', 'completado', 'abandonado'),
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);

-- Aggregated (pre-computed)
participant_metrics (
  participant_id UUID PRIMARY KEY REFERENCES participants,
  total_cursos_inscrito INT,
  total_cursos_completado INT,
  porcentaje_promedio DECIMAL,
  ultima_actualizacion TIMESTAMP,
  computed_at TIMESTAMP DEFAULT NOW()
);

cohorte_stats (
  cohorte VARCHAR PRIMARY KEY,
  total_participantes INT,
  con_emprendimiento INT,
  sin_emprendimiento INT,
  porcentaje_con_emprendimiento DECIMAL,
  edad_promedio DECIMAL,
  computed_at TIMESTAMP DEFAULT NOW()
);
```

---

## 📈 VARIABLES Y MÉTRICAS ANÁLISIS

### Dimensiones Principales

#### **Dimensión 1: Participación en Cursos**
```
- Total inscritos por cohorte
- Inscritos con ≥1 curso completado (%)
- Promedio cursos completados por participante
- Distribución por % avance (0%, 1-50%, 51-99%, 100%)
```

#### **Dimensión 2: Emprendimiento**
```
- % con emprendimiento registrado
- Correlación: emprendimiento ↔ cursos completados
- Evolución temporal: emprendimientos por cohorte
- Industrias más frecuentes (si datos disponibles)
```

#### **Dimensión 3: Perfil Sociodemográfico**
```
Vivienda:    arrendado / familiar / propia / otro
Estrato:     1-6 (distribución por estrato)
Ciudad:      Top 10 ciudades (rest = "Otra")
Edad:        Promedio, mediana, rango (box plot)
Edo Civil:   soltero / casado / divorciado / u.libre / otro
Nivel Est:   primaria / secundaria / técnico / prof / postgrado
```

#### **Dimensión 4: Retirados (Churn)**
```
- USAR la definición canónica existente: pestaña Retirados de Q10,
  desertores excluidos (Tipo=Desertor / "Decisión de la Institución"),
  identidad 832 = 775 activos + 57 retirados (export_aprobacion.py)
- Tipo y causa de retiro (ya disponibles en Q10)
- Etapa de retiro en la ruta (heurística ya implementada en export_retirados)
- NO inventar heurística paralela (0% avance + 3 meses) — generaría
  números distintos a los del dashboard público actual
```

---

## 🛠️ HERRAMIENTAS RECOMENDADAS

### Decisión: Dashboard Custom vs. BI Tool

#### **Opción A: Dashboard Custom (React + Recharts)**
**Pros:**
- Control total de UX/UI
- Bajo costo (hosting Netlify gratis para tier básico)
- Fácil de personalizar por stakeholder
- Reutilizar componentes existentes

**Contras:**
- Requiere desarrollo inicial (Claude Code)
- Menos funcionalidad analítica avanzada
- Mantenimiento continuo

**Recomendación:** ✅ **START HERE** (Fase 1)

#### **Opción B: Metabase (Open Source BI)**
**Pros:**
- Zero-code dashboard builder
- Soporta Supabase nativo
- SQL Lab para usuarios avanzados
- Permisos y RLS

**Contras:**
- Otro servicio a self-host o pagar
- UI menos personalizable
- Overhead operacional

**Recomendación:** 🟡 **Evaluar para Fase 2** (si necesitan SQL Ad-Hoc)

#### **Opción C: Apache Superset**
**Pros:**
- Más robusto que Metabase
- Diseño profesional de dashboards

**Contras:**
- Curva aprendizaje más pronunciada
- Overkill para este caso

**Recomendación:** ❌ **Descartar por ahora**

### Solución Propuesta
**Fase 1 (MVP):** Dashboard custom React + Recharts en Netlify
**Fase 2 (si es necesario):** Integrar Metabase para reportes adhoc

---

## 🔐 CONSIDERACIONES DE PRIVACIDAD Y SEGURIDAD

### Row Level Security (RLS) en Supabase
```sql
-- Política: datos públicos son visibles a todos
ALTER TABLE participants ENABLE ROW LEVEL SECURITY;

CREATE POLICY "datos_publicos_visible"
  ON participants FOR SELECT
  USING (is_public = true);
```
> ⚠️ Nota de revisión: se eliminó el ejemplo con `assigned_profesor_id` — esa columna no existe
> en el schema. Si algún día se implementa la Opción B de permisos (Decisión 3), habrá que
> agregarla primero. Las políticas reales están en `schema-supabase-completo.sql`.
> Importante: n8n escribirá con el **service_role key, que BYPASEA RLS por diseño** — las
> políticas protegen solo el acceso vía anon key (dashboard público).

### PII Handling
- ✅ **Público:** Métricas agregadas, no individuales
- ✅ **Local (`tools/`):** Exports con PII para análisis interno
- ✅ **GitHub:** Solo JSON con agregados
- ❌ **Nunca:** Nombres + emails en panel público

---

## 📅 TIMELINE Y DEPENDENCIAS

### Fase 0: Setup (1-2 horas)
- [ ] Crear BD Supabase con schema propuesto
- [ ] Definir credenciales + RLS
- [ ] Documentar en CLAUDE.md

### Fase 1: ETL (2-3 días)
- [ ] Script Python: extraer Q10 → dataframe
- [ ] Script Python: normalizar + validar
- [ ] n8n workflow: orchestrar ingesta diaria
- [ ] Pruebas: 100 registros, validar integridad

### Fase 2: Backend API (1-2 días)
- [ ] Supabase Edge Functions OR REST API (ya incluido)
- [ ] Query optimization + índices
- [ ] Documentar endpoints (OpenAPI)

### Fase 3: Frontend Dashboard (3-5 días)
- [ ] Crear Next.js + Tailwind + Recharts
- [ ] Implementar 5 vistas (stats, emprendimiento, demo, retirados, etc.)
- [ ] Filtros interactivos
- [ ] Deploy a Netlify

### Fase 4: Validación (1-2 días)
- [ ] Testing en datos reales Q10
- [ ] UAT con stakeholders
- [ ] Documentación runbook

**Total: ~7-14 días de desarrollo (depende de parallelización)**

---

## ⚠️ RIESGOS Y MITIGACIÓN

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|--------|-----------|
| Datos incompletos en Q10 | Alta | Alto | Validación estricta, logs de errors |
| Pérdida datos durante migración | Media | Crítico | Backup snapshots cada hora, reversión rollback plan |
| API Q10 downtime | Media | Medio | Cache SWR, fallback datos últimos conocidos |
| RLS misconfiguration expone PII | Baja | Crítico | Auditoría de políticas, tests de seguridad |
| Queries lentas en PostgreSQL | Baja | Medio | Materialized views, índices, monitoring |
| Cambios en Q10 schema | Media | Medio | Mapping table, versioning de transformaciones |

---

## 🎯 DECISIONES PENDIENTES (PARA SAMUEL)

1. **¿Quién alimenta la BD limpia?**
   - ¿Manual via Airtable/admin panel?
   - ¿Auto sync Q10 daily?
   - ¿Hybrid (daily sync + manual corrections)?

2. **¿Qué nivel de histórico mantener?**
   - ¿Todas las versiones de registros (SCD Type 2)?
   - ¿Solo última versión?

3. **¿Quién tiene permisos de escritura?**
   - ¿Solo admins (via n8n)?
   - ¿Profesores pueden corregir datos de sus alumnos?

4. **¿Reportes públicos o privados?**
   - ¿Dashboard visible a anonimos?
   - ¿Requiere login?

5. **¿Cuándo activar?**
   - ¿MVP antes del próximo trimestre?
   - ¿Full-featured antes de fin de año?

---

## 📚 Referencias e Investigación

### Herramientas Validadas (2026)
- [Supabase Data Visualization Guide](https://supabase.com/blog/visualizing-supabase-data-using-metabase)
- [Netlify Docs - Frameworks API](https://docs.netlify.com/build/frameworks/frameworks-api/)
- [n8n Self-Hosting Best Practices](https://n8nlab.io/blog/self-hosted-n8n-best-practices-setup-checklist)
- [Apache Superset + Open Source BI](https://www.domo.com/learn/article/open-source-bi-tools)

### Próximos Pasos
- Validar schema con equipo ROFÉ
- Crear wireframes dashboard
- Iniciar Fase 1 con Claude Code

---

**Documento actualizado:** 2026-07-09
**Revisado por Claude Code:** 2026-07-09 — corregido MySQL→PostgreSQL, backups/rate-limiting de
Supabase, ejemplo RLS con columna inexistente, definición de retirados alineada con la canónica,
y agregados gaps #8 (fuente sociodemográfica) y #9 (retirados).
**Próxima revisión:** Post-Phase 0 validation
