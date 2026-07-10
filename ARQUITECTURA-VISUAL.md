# Arquitectura Visual: Panel de Datos ROFÉ
**Diagrama ejecutivo del flujo de datos y componentes**

---

## 🏗️ FLUJO DE DATOS (End-to-End)

```
┌─────────────────────────────────────────────────────────────────┐
│                     SOURCES (Datos Crudos)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Q10 Platform              Google Sheets         Manual Input     │
│  (API/export)              (cache)               (admin)          │
│       │                         │                    │           │
│       └─────────────┬───────────┘                    │           │
│                     │                                │           │
└─────────────────────┼────────────────────────────────┼───────────┘
                      │                                │
                      ▼                                ▼
        ┌──────────────────────────────┐    ┌────────────────────┐
        │  n8n (Orchestrator - Local)  │    │  (Future: Admin UI)│
        ├──────────────────────────────┤    └────────────────────┘
        │ • Extract Q10/Sheets         │
        │ • Call normalize_q10_data.py │
        │ • Run daily 04:00 UTC        │
        │ • Error handling + logs      │
        └──────────────────────────────┘
                      │
                      ▼
   ┌──────────────────────────────────────┐
   │  Python Scripts (Normalización)      │
   ├──────────────────────────────────────┤
   │ • normalize_q10_data.py              │
   │ • Validación + deduplicación         │
   │ • Mapeo de valores                   │
   │ • Reporte de errores                 │
   └──────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                SUPABASE PostgreSQL (Fuente Única)               │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────────┐ │
│  │   Raw Tables    │  │ Cleaned Tables  │  │   Aggregates     │ │
│  ├─────────────────┤  ├─────────────────┤  ├──────────────────┤ │
│  │ participants    │  │ (validados)     │  │ participant_     │ │
│  │ courses         │  │                 │  │   metrics        │ │
│  │ enrollments     │  │                 │  │ cohorte_stats    │ │
│  │                 │  │                 │  │ (pre-computed)   │ │
│  └─────────────────┘  └─────────────────┘  └──────────────────┘ │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  Materialized Views (para performance)                     │ │
│  │  • view_emprendimiento_cursos                              │ │
│  │  • view_demografics_por_ciudad                             │ │
│  │  • view_retirados                                          │ │
│  │  • view_cohorte_completion                                 │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  RLS (Row Level Security)                                  │ │
│  │  • Datos públicos: is_public=true                          │ │
│  │  • Datos privados: solo admin + assigned role              │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                      │
                      ▼
   ┌──────────────────────────────────────┐
   │   REST API / Edge Functions          │
   ├──────────────────────────────────────┤
   │ • Supabase auto-generated REST       │
   │ • Cache: CDN + Cache-Control headers │
   │ • Auth: Service role para n8n       │
   │   (bypasea RLS — jamás en frontend) │
   │ • Rate limit: no nativo → cache CDN │
   └──────────────────────────────────────┘
                      │
                      ▼
   ┌──────────────────────────────────────┐
   │   Netlify Functions (Optional)       │
   ├──────────────────────────────────────┤
   │ • CSV export                         │
   │ • PDF generation                     │
   │ • Cache revalidation (ISR)          │
   └──────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│            Next.js Frontend (React + Recharts)                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              Navigation / Header                           │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─────────────────────────┐  ┌──────────────────────────────┐  │
│  │   Filter Panel          │  │   Dashboard (5 Vistas)       │  │
│  ├─────────────────────────┤  ├──────────────────────────────┤  │
│  │ • Cohorte               │  │ 1. Overview                  │  │
│  │ • Ciudad                │  │    • KPIs                    │  │
│  │ • Estrato               │  │    • Trend line              │  │
│  │ • Fecha rango           │  │                              │  │
│  │ • Emprendimiento        │  │ 2. Emprendimiento           │  │
│  │                         │  │    • Scatter: cursos vs emp  │  │
│  │ [Apply] [Reset]         │  │    • Top emprendimientos    │  │
│  │                         │  │                              │  │
│  │                         │  │ 3. Perfil Sociodemográfico  │  │
│  │                         │  │    • Vivienda (bar)          │  │
│  │                         │  │    • Estrato (bar)           │  │
│  │                         │  │    • Ciudad (bar)            │  │
│  │                         │  │    • Edad (box plot)         │  │
│  │                         │  │    • Edo Civil (pie)         │  │
│  │                         │  │    • Nivel Estudio (bar)     │  │
│  │                         │  │                              │  │
│  │                         │  │ 4. Retirados (Churn)         │  │
│  │                         │  │    • Tabla detalle           │  │
│  │                         │  │    • Gráfico motivos         │  │
│  │                         │  │    • [Export CSV]            │  │
│  │                         │  │                              │  │
│  │                         │  │ 5. Comparativo Cohortes      │  │
│  │                         │  │    • Heatmap: cohorte x stat │  │
│  │                         │  │    • Tendencia               │  │
│  └─────────────────────────┘  └──────────────────────────────┘  │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                      │
                      ▼
   ┌──────────────────────────────────────┐
   │   Netlify CDN & Hosting              │
   ├──────────────────────────────────────┤
   │ • https://panel-rofe.netlify.app    │
   │ • Auto-deploy on push main          │
   │ • Edge functions + Caching          │
   └──────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                   END USERS (Lectura)                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  👨‍🎓 Estudiantes    👨‍🏫 Profesores    📊 Contadores   💻 Dev Team    │
│  (view metrics)  (see progress)  (reports)   (debug)            │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 COMPONENTES TÉCNICOS

### Layer 1: Data Ingestion (n8n Local)
```
┌─────────────────────────────────────────────┐
│  n8n Workflow: q10-sync-supabase            │
├─────────────────────────────────────────────┤
│                                              │
│  ⏰ TRIGGER                                  │
│  └─ Cron: 04:00 UTC daily                  │
│                                              │
│  🔗 FETCH (Google Sheets)                   │
│  ├─ h2test (raw data)                      │
│  ├─ Avance (course progress)               │
│  └─ Perfil Sociodemográfico (demographics) │
│                                              │
│  ⚙️ TRANSFORM (Python)                      │
│  ├─ Call: normalize_q10_data.py            │
│  ├─ Validations & deduplication             │
│  └─ Error report                            │
│                                              │
│  💾 LOAD (Supabase)                         │
│  ├─ UPSERT participants (by q10_id)        │
│  ├─ INSERT enrollments                      │
│  └─ REFRESH aggregated tables               │
│                                              │
│  ✉️ NOTIFY                                  │
│  ├─ Success: log count metrics              │
│  └─ Error: email to Samuel                  │
│                                              │
│  📦 AUDIT                                   │
│  └─ Save JSON export for git                │
│                                              │
└─────────────────────────────────────────────┘
```

### Layer 2: Database Schema
```
┌────────────────────────────────────────────────────────┐
│              PostgreSQL (Supabase)                     │
├────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────────────────────────────────────┐  │
│  │ PARTICIPANTS (Dimensión Persona)               │  │
│  │ ┌─────────────────────────────────────────────┐ │  │
│  │ │ id | q10_id | nombre | email | ciudad | ... │ │  │
│  │ │ edad | estrato | vivienda | estado_civil   │ │  │
│  │ │ nivel_estudio | tiene_emprendimiento       │ │  │
│  │ │ created_at | updated_at                    │ │  │
│  │ └─────────────────────────────────────────────┘ │  │
│  └─────────────────────────────────────────────────┘  │
│           ↓              ↓              ↓              │
│           │              │              │              │
│  ┌─────────┴───────┐ ┌───┴─────────┐ ┌──┴──────────┐ │
│  │    COURSES      │ │ ENROLLMENTS │ │   METRICS   │ │
│  ├─────────────────┤ ├─────────────┤ ├─────────────┤ │
│  │ id              │ │ id          │ │ participant │ │
│  │ nombre          │ │ participant │ │ _id         │ │
│  │ cohorte         │ │ course      │ │ total_      │ │
│  │ fecha_inicio    │ │ porcentaje_ │ │ cursos_     │ │
│  │ fecha_fin       │ │ avance      │ │ inscrito   │ │
│  │ estado          │ │ estado      │ │ total_      │ │
│  │                 │ │ created_at  │ │ cursos_     │ │
│  │                 │ │ updated_at  │ │ completado │ │
│  │                 │ │             │ │ computed_at│ │
│  └─────────────────┘ └─────────────┘ └─────────────┘ │
│                                                         │
│  ┌────────────────────────────────────────────────┐   │
│  │ COHORTE_STATS (Agregados por Cohorte)         │   │
│  │ cohorte | total_part | con_emp | sin_emp |... │   │
│  └────────────────────────────────────────────────┘   │
│                                                         │
│  ┌────────────────────────────────────────────────┐   │
│  │ MATERIALIZED VIEWS (Optimizadas para lectura)  │   │
│  │ • view_emprendimiento_cursos                   │   │
│  │ • view_demografics_por_ciudad                  │   │
│  │ • view_retirados                               │   │
│  │ • view_cohorte_completion                      │   │
│  └────────────────────────────────────────────────┘   │
│                                                         │
│  ┌────────────────────────────────────────────────┐   │
│  │ INDEXES (Performance)                          │   │
│  │ • participants(ciudad, estrato, edad)         │   │
│  │ • enrollments(participant_id, course_id)      │   │
│  │ • enrollments(estado)                          │   │
│  └────────────────────────────────────────────────┘   │
│                                                         │
│  ┌────────────────────────────────────────────────┐   │
│  │ POLICIES (RLS - Row Level Security)            │   │
│  │ • Pública: is_public=true → anyone can read   │   │
│  │ • Privada: auth.uid=admin only                 │   │
│  └────────────────────────────────────────────────┘   │
│                                                         │
└────────────────────────────────────────────────────────┘
```

### Layer 3: Frontend Components
```
┌────────────────────────────────────────────────────────┐
│              Next.js (React Components)                │
├────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │ LAYOUT (Shared)                                 │  │
│  │ ├─ Header (Logo, Title, About)                 │  │
│  │ ├─ Sidebar Navigation (5 tabs)                 │  │
│  │ └─ Footer (Last Updated, etc.)                 │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │ FILTER PANEL (Shared)                           │  │
│  │ ├─ <SelectCohorte />                            │  │
│  │ ├─ <SelectCiudad />                             │  │
│  │ ├─ <SelectEstrato />                            │  │
│  │ ├─ <DateRangePicker />                          │  │
│  │ ├─ <ToggleEmprendimiento />                     │  │
│  │ └─ <Button>Apply</Button>                       │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │ CHARTS (Reusable)                               │  │
│  │ ├─ <BarChart />      (Recharts)                 │  │
│  │ ├─ <PieChart />      (Recharts)                 │  │
│  │ ├─ <LineChart />     (Recharts)                 │  │
│  │ ├─ <ScatterChart />  (Recharts)                 │  │
│  │ └─ <BoxPlot />       (Custom)                   │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │ PAGES (Vistas Específicas)                      │  │
│  │ ├─ /                 (Overview KPIs)            │  │
│  │ ├─ /emprendimiento   (Startup Analysis)         │  │
│  │ ├─ /demograficos     (Sociodemographics)        │  │
│  │ ├─ /retirados        (Churn Analysis)           │  │
│  │ └─ /cohortes         (Comparison)               │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │ UTILITIES                                        │  │
│  │ ├─ hooks/useSupabase() (data fetching)          │  │
│  │ ├─ lib/api.ts (Supabase client)                │  │
│  │ ├─ lib/formatting.ts (number, date formatting)  │  │
│  │ ├─ types/index.ts (TypeScript interfaces)       │  │
│  │ └─ data/mock.json (for development)             │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
└────────────────────────────────────────────────────────┘
```

---

## 🔄 FLUJO DE UNA SOLICITUD

### 1. Usuario abre dashboard
```
1. GET https://panel.rofé.netlify.app/emprendimiento?cohorte=2024-H1
2. Netlify CDN → Next.js server
3. React page monta
4. useEffect() → React Query fetch
```

### 2. React Query busca datos
```
1. check cache (1 hora)
2. if miss → GET https://xyzabc.supabase.co/rest/v1/emprendimiento_view
              ?cohorte=eq.2024-H1
3. Supabase RLS: aplica políticas
4. DB query: Materialized view
5. return JSON
```

### 3. Frontend renderiza
```
1. Datos en estado React
2. Recharts render gráficos
3. User interactúa con filtros
4. Query string actualiza
5. React Query refetch (cache invalidation)
```

### 4. Comportamiento en error
```
1. API error (timeout)
   → Supabase fallback
   → Show last cached data
   → Error notification

2. Network error
   → Offline mode
   → Show mock data
   → Suggest retry
```

---

## 📈 ESCALABILIDAD

### Fase 1 (MVP: Hoy)
```
• Participants: 0-10k registros
• Queries: < 500ms (materialized views)
• Concurrent users: 10-50
• Cost: $0 (free tier, sin backups y con pausa por inactividad)
        o ~$25/mes (Supabase Pro: backups diarios, sin pausa)
```

### Fase 2 (Scaling: 6 meses)
```
• Participants: 10k-100k registros
• Add read replicas (Supabase)
• Add Metabase para SQL adhoc
• Cost: ~$100/mes
```

### Fase 3 (Enterprise: 1 año)
```
• Participants: 100k+ registros
• Add data warehouse (BigQuery)
• Add real-time subscriptions
• Cost: ~$500+/mes
```

---

## 🔒 SEGURIDAD

```
┌──────────────────────────────────────┐
│         SECURITY LAYERS              │
├──────────────────────────────────────┤
│                                      │
│ 1. Transport: HTTPS (Netlify TLS)    │
│                                      │
│ 2. API Auth: Supabase RLS            │
│    • is_public=true → public read    │
│    • admin role → full access        │
│                                      │
│ 3. PII Protection:                   │
│    • No nombres/emails en dashboard  │
│    • Solo agregados públicos         │
│    • Detalles privados en admin UI   │
│                                      │
│ 4. Secrets Management:               │
│    • .env.local (git ignored)        │
│    • Netlify env vars (UI)           │
│    • Service account key (Supabase)  │
│                                      │
│ 5. Data Backup:                      │
│    • ⚠️ Backups diarios Supabase =   │
│      solo plan Pro (~$25/mes).       │
│      Free tier: snapshot propio      │
│      diario vía n8n (pg_dump/JSON)   │
│      y pausa tras ~1 sem inactivo    │
│    • n8n execution logs archived     │
│    • Git version control             │
│                                      │
└──────────────────────────────────────┘
```

---

## 📊 MONITOREO

```
┌────────────────────────────────────────┐
│         MONITORING POINTS              │
├────────────────────────────────────────┤
│                                        │
│ 1. Data Quality                        │
│    ✓ n8n logs validation errors        │
│    ✓ Supabase row counts alerts        │
│    ✓ Data freshness (last update)      │
│                                        │
│ 2. Performance                         │
│    ✓ API response times (< 500ms)      │
│    ✓ Frontend load time (< 2s)         │
│    ✓ Netlify build time (< 2min)       │
│                                        │
│ 3. Uptime                              │
│    ✓ Supabase health checks            │
│    ✓ Netlify deploy status             │
│    ✓ n8n workflow execution            │
│                                        │
│ 4. Cost                                │
│    ✓ Supabase usage (rows, compute)    │
│    ✓ Netlify bandwidth                 │
│    ✓ Monthly spend                     │
│                                        │
└────────────────────────────────────────┘
```

---

---

## ⚠️ NOTAS DE REVISIÓN (2026-07-09, Claude Code)

1. **Capas Raw/Cleaned/Aggregated:** el diagrama muestra 3 capas, pero el schema real
   (`schema-supabase-completo.sql`) implementa UNA capa core (participants/courses/enrollments,
   ya limpia — la limpieza ocurre en Python antes de cargar) + agregados. La caja "Cleaned Tables
   (validados)" está vacía porque no existe como capa separada. Si se quiere staging raw, hay que
   agregar tablas `raw_*` al schema; si no, simplificar el diagrama. Decidir en Fase 0.
2. **`view_retirados`:** debe usar la definición canónica del proyecto (pestaña Retirados Q10,
   desertores excluidos, identidad 832 = 775 + 57), NO "0% avance + 3 meses" — ver corrección
   en CLAUDE-CODE-PROMPTS-POR-FASE.md Prompt 2.2.
3. **Fuente sociodemográfica:** vivienda/estrato/estado_civil/nivel_estudio no están en las
   pestañas confirmadas del Sheet Q10 (h2test/Avance/Retirados) — confirmar origen
   (BD-Mujeres ROFÉ / BD monitorias) antes de Fase 1.
4. **Convivencia con el dashboard actual (GitHub Pages):** correr AMBOS en paralelo y validar
   cuadre de cifras (aprobación/retirados) antes de reemplazar — no big-bang.

**Diagrama actualizado:** 2026-07-09
**Próxima revisión:** Post-Fase 1 validación
