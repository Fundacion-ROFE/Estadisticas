# Claude Code: Prompts Optimizados por Fase
**Objetivo:** Prompts listos para copy-paste en Claude Code sin reiteración innecesaria

---

## FASE 0: SETUP SUPABASE

### Prompt 0.1: Crear Schema Base en Supabase

> ⚠️ **NOTA DE REVISIÓN (2026-07-09):** Este prompt ya produjo output — el schema canónico está en
> `schema-supabase-completo.sql` (raíz del repo), con la sintaxis correcta (`CREATE TYPE ... AS ENUM`;
> el `ENUM(...)` inline que tenía este prompt es sintaxis MySQL y **falla en PostgreSQL**).
> Además: el project ID que referencia ese archivo (`sqmrnirbakcrbhdlfxxz`) **NO existe en la cuenta
> Supabase actual** — los únicos proyectos son "samueldavidhhuhuhhuhuh's Project" y "DRAFT", ambos
> INACTIVE. Antes de ejecutar: crear/reactivar el proyecto correcto y actualizar el ID en el .sql.
> El schema usaba `uuid_generate_v4()` sin crear la extensión `uuid-ossp` — corregido a
> `gen_random_uuid()` (nativo en Postgres 13+).

```
CONTEXTO:
- Proyecto: Panel de datos ROFÉ (Jóvenes creaTIvos + Fundación ROFÉ)
- Herramienta: Supabase PostgreSQL
- Objetivo: Crear BD limpia como fuente única de verdad para dashboard
- Credenciales: [URL Supabase] [API Key] (ya tengo)

TAREA:
1. Ejecutar el schema canónico `schema-supabase-completo.sql` (raíz del repo):
   - 5 tipos ENUM vía CREATE TYPE (vivienda_type, estado_civil_type, nivel_estudio_type,
     curso_estado_type, enrollment_estado_type)
   - 5 tablas: participants, courses, enrollments, participant_metrics, cohorte_stats
   - PKs UUID con gen_random_uuid() (NO uuid_generate_v4(), que requiere extensión uuid-ossp)
   - Nota semántica: "cohorte" en este proyecto es del PARTICIPANTE (ej. cohorte 2026 con su
     ruta de cursos), no del curso ("2024-H1") — validar el modelo con Samuel antes de cargar

2. Crear índices en campos frecuentemente filtrados:
   - participants(ciudad)
   - participants(estrato)
   - participants(edad)
   - enrollments(participant_id, course_id)
   - enrollments(estado)

3. Habilitar RLS (Row Level Security):
   - Política pública: cualquiera puede leer datos_publicos = true
   - Política admin: solo role 'admin' puede leer/escribir todo

4. Entregar:
   - Script SQL completo (para version control)
   - JSON de policies (para auditoría)
   - Screenshot de schema en Supabase UI
   - Instrucciones setup local + testing
```

---

### Prompt 0.2: Configurar Credenciales y Service Account

```
TAREA:
1. Crear Service Account en Supabase (para n8n):
   - Nombre: "q10-sync-bot"
   - Permisos: SELECT, INSERT, UPDATE en todas las tablas
   - Generar API key
   - Guardar en archivo .env (NO en Git)

2. Configurar variables de entorno para desarrollo:
   SUPABASE_URL=https://[project].supabase.co
   SUPABASE_ANON_KEY=eyJh...
   SUPABASE_SERVICE_ROLE_KEY=eyJh...
   Q10_API_KEY=xxx (si es necesario)

3. Documentar en CLAUDE.md:
   - Cómo conectar desde Python
   - Cómo conectar desde n8n
   - Cómo conectar desde Netlify Functions
   - Esquema de permisos por rol (admin, profesor, student)

4. Entregar:
   - .env.example (sin keys reales)
   - Documentación README con instrucciones
   - Script Python minimal para test de conexión
```

---

## FASE 1: ETL (EXTRACCIÓN NORMALIZACIÓN)

### Prompt 1.1: Script Python de Validación y Normalización

```
CONTEXTO:
- Datos vienen de Q10 (via Google Sheets actualmente)
- Necesitamos pipeline robusto: extracción → normalización → validación → Supabase
- Los datos tienen inconsistencias (emails duplicados, edades negativas, etc.)

TAREA:
Crear `scripts/q10-consolidacion/normalize_q10_data.py` que:

1. LEA datos de Google Sheets (usar existing q10_to_sheets.py como referencia)

2. NORMALICE:
   - Nombres: trim(), lowercase para búsqueda, pero preservar original
   - Emails: validar formato, duplicatas
   - Edades: >= 13 y <= 100 (flag si fuera de rango)
   - Ciudades: mapear variantes ("Bogotá", "Bogota", "BOG" → "Bogotá")
   - Estratos: 1-6 solo, null si no está
   - Emprendimiento: "Sí/No/null" → Boolean
   - Fechas: ISO8601 format

3. VALIDE:
   - Reglas de negocio: 
     * Si tiene_emprendimiento=true, nombre_emprendimiento no puede ser null
     * Coherencia edad/nivel_estudio SOLO como WARNING (nunca error): flag si edad < 15 y
       nivel_estudio es profesional/postgrado. NO asumir "primaria implica edad < 20" —
       la población de la fundación incluye adultos cuyo máximo nivel es primaria; eso es válido
   - Referential integrity: all q10_ids deben existir
   - Duplicatas: reportar por email, teléfono, documento ID si existe

4. REPORTE:
   - Total registros: OK / WARNING / ERROR
   - Campos faltantes (% por columna)
   - Outliers (edades extremas, etc.)
   - Registros duplicados (antes de cargar)
   - Guardar reporte en `logs/validation_YYYYMMDD.json`

5. OUTPUT:
   - CSV limpio o JSON para carga a Supabase
   - Registro de cambios (qué se limpió/transformó)
   - Script debe ser idempotente (correr 2x da mismo resultado)

ESTRUCTURA DE CÓDIGO:
- Clase DataValidator con métodos por tipo de dato
- Clase DataNormalizer con reglas de mapeo por campo
- Función main() que orquesta pipeline
- Tests unitarios para cada normalización (pytest)

CRITERIO DE ACEPTACIÓN:
✅ Script ejecutable: `python normalize_q10_data.py --input data.csv --output cleaned.json`
✅ Reporte legible: `validate_YYYYMMDD.json` con errores y advertencias
✅ 100% datos Q10 real cargados sin errores
```

---

### Prompt 1.2: n8n Workflow de Ingesta Diaria

```
CONTEXTO:
- Usamos n8n self-hosted en PC de Samuel (local)
- Necesitamos workflow que corra diariamente (04:00 UTC)
- Error handling explícito (nunca fallar silenciosamente)
- Archivos JSON exportados para auditoría

TAREA:
Crear workflow n8n: `q10-sync-supabase` que:

1. SCHEDULER:
   - Trigger: Cron "0 4 * * *" (04:00 UTC = 23:00 Colombia/COT, UTC-5 fijo — no "ET")
   - ⚠️ n8n corre en el PC local de Samuel: el PC debe estar ENCENDIDO a las 23:00,
     o mover el horario a uno donde sí lo esté (validar con Samuel)
   - Retry: Si falla, reintentar en 15 min (2x máximo)

2. EXTRACCIÓN:
   - Conectar a Google Sheets (usar existing q10_to_sheets config)
   - Descargar pestaña "h2test" (datos crudos)
   - Descargar pestaña "Avance" (progreso cursos)
   - Descargar pestaña "Retirados" (definición canónica de retiros)
   - ⚠️ NO existe pestaña "Perfil Sociodemográfico" confirmada — los campos vivienda/estrato/
     estado_civil/nivel_estudio probablemente vienen de BD-Mujeres ROFÉ (form MR2024) o de la
     BD Seguimiento de Monitorías. CONFIRMAR fuente antes de construir este paso

3. TRANSFORMACIÓN:
   - Llamar script Python: normalize_q10_data.py
   - Pasar datos como JSON, recibir cleaned JSON
   - Validar status code de script

4. CARGA:
   - Insertar en tabla Supabase `participants` (upsert por q10_id)
   - Insertar en tabla Supabase `enrollments` (deduplicar)
   - Update `participant_metrics` (re-compute totales)
   - Update `cohorte_stats` (re-compute agregados)

5. ERROR HANDLING:
   - Nodo "Try-Catch": si cualquier paso falla, enviar email a Samuel
   - Email debe incluir: qué falló, línea de datos que causó, error code
   - No insertar datos parciales (transactional)
   - Guardar payload fallido en `logs/failed_q10_YYYYMMDD_HHmm.json` para debug

6. AUDITORÍA:
   - Log: "Loaded N participants, M courses, K enrollments at TIMESTAMP"
   - Diff: Comparar counts vs. run anterior (alerta si cambio > 20%)
   - Backup: Crear snapshot tabla participants antes de upsert

7. DELIVERY:
   - JSON exportado a `n8n-workflows/q10-sync-supabase.json`
   - Documento README en `docs/procesos/` con diagrama del workflow

CRITERIO DE ACEPTACIÓN:
✅ Workflow ejecutable y testeable
✅ Error handling funcionando (test con data corrupta)
✅ Logs limpios (timestamps, counts, status)
✅ Rollback posible en < 1 hora
```

---

## FASE 2: BACKEND API

### Prompt 2.1: REST API Endpoints (Supabase)

```
CONTEXTO:
- Supabase ya incluye REST API automático
- Necesitamos documentar endpoints que usará el frontend
- Query optimization para evitar N+1 problems
- Caching strategy para performance

TAREA:
1. ENDPOINTS A DOCUMENTAR (OpenAPI 3.0):

   GET /rest/v1/cohorte_stats
   - Query params: cohorte (filter opcional)
   - Response: [{ cohorte, total_participantes, con_emprendimiento, ... }]
   - Cache: 1 hora

   ⚠️ ELIMINADO en revisión: GET /rest/v1/participants (filas individuales) NO debe exponerse
   públicamente. Aunque no incluya nombre/email, edad+estrato+ciudad+estado_civil son
   cuasi-identificadores re-identificables — viola la convención del proyecto (PII nunca pública).
   El dashboard público consume SOLO vistas/tablas agregadas (cohorte_stats, materialized views).
   (Nota: "cache 30 min" no mitiga exposición de PII — un dato expuesto está expuesto.)

   GET /rest/v1/enrollments_view?cohorte=eq.2024-H1
   - View: participants + enrollments + courses (pre-joined)
   - Aggregates: count(*), avg(porcentaje_avance)
   - Cache: 1 hora

   GET /rest/v1/demographics_stats
   - Custom endpoint (puede ser materialized view)
   - Response: edad_dist, estrato_dist, ciudad_dist, estado_civil_dist, etc.
   - Cache: 1 hora

2. SECURITY:
   - Habilitar CORS para Netlify domain
   - Rate limiting: ⚠️ Supabase NO lo ofrece nativo para la REST API (solo Auth) —
     mitigar con caching CDN agresivo o proxy vía Netlify Functions si hiciera falta
   - RLS: datos con is_public=false no retornados (via policy); recordar que el
     service_role key BYPASEA RLS — nunca usarlo en el frontend
   - Auth: opcional (anon key es suficiente para lectura pública de agregados)

3. DOCUMENTACIÓN:
   - Generador automático OpenAPI (supabase-js genera spec)
   - Postman collection (for testing)
   - README con ejemplos cURL

4. ENTREGAR:
   - openapi.json (auto-generated)
   - Postman collection
   - Tests de performance (k6 script para load test)
```

---

### Prompt 2.2: Materialized Views para Agregados

```
CONTEXTO:
- Queries complejas (joins + aggregations) son lentas si se compute cada request
- Solución: Pre-compute agregados en tablas desnormalizadas
- Supabase soporta materialized views + refresh triggers

TAREA:
Crear materialized views para métricas clave:

1. view_emprendimiento_cursos:
   - participant_id, nombre_emprendimiento, total_cursos_completado
   - Usado para scatter plot "relación emprendimiento vs cursos"

2. view_demografics_por_ciudad:
   - ciudad, edad_promedio, estrato_promedio, total_participantes
   - Usado para comparativas entre ciudades

3. view_retirados:
   - ⚠️ CORREGIDO: usar la definición canónica del proyecto (pestaña Retirados de Q10,
     estado='abandonado' en enrollments, desertores EXCLUIDOS), NO la heurística
     "porcentaje_avance = 0 + 3 meses" — daría números distintos a los del dashboard
     público actual (identidad verificada: 832 = 775 activos + 57 retirados)
   - Campos agregados solamente: cohorte, tipo_retiro, causa, etapa_ruta, total
     (sin nombre — la vista alimenta el panel público)
   - Usado para panel "retirados" y alertas

4. view_cohorte_completion:
   - cohorte, total_inscritos, total_completados, % completados
   - Usado para seguimiento por cohorte

AUTOMATIZACIÓN:
- Refresh diario (04:30 UTC, después de ingesta)
- Trigger manual via n8n si es necesario
- Documentar en CLAUDE.md > Convenciones > Materialized Views

CRITERIO:
✅ Queries optimizadas (< 500ms response time)
✅ Volúmenes: soporta 100k+ registros
```

---

## FASE 3: FRONTEND DASHBOARD

### Prompt 3.1: Estructura Next.js + Componentes Base

```
CONTEXTO:
- Framework: Next.js 14+ (App Router)
- Styling: Tailwind CSS
- Visualización: Recharts
- State management: React Query (SWR alternative)
- Hosting: Netlify

TAREA:
Crear estructura Next.js inicial:

proyecto/
├── app/
│   ├── layout.tsx          ← Global layout, header, footer
│   ├── page.tsx            ← Home / Dashboard overview
│   ├── participantes/
│   │   └── page.tsx        ← Listado + filtros
│   ├── emprendimiento/
│   │   └── page.tsx        ← Análisis emprendimiento
│   ├── demograficos/
│   │   └── page.tsx        ← Perfil sociodemográfico
│   ├── retirados/
│   │   └── page.tsx        ← Churn analysis
│   └── api/
│       └── cache/          ← Revalidate endpoints para ISR
│
├── components/
│   ├── charts/
│   │   ├── BarChart.tsx
│   │   ├── LineChart.tsx
│   │   ├── PieChart.tsx
│   │   ├── ScatterChart.tsx
│   │   └── BoxPlot.tsx
│   ├── filters/
│   │   ├── CiudadFilter.tsx
│   │   ├── EstratoFilter.tsx
│   │   ├── CohortFilter.tsx
│   │   └── DateRangeFilter.tsx
│   ├── cards/
│   │   ├── StatCard.tsx    ← KPI: "500 participantes"
│   │   ├── MetricCard.tsx  ← "45% completados"
│   │   └── ChartCard.tsx   ← Wrapper para charts
│   └── common/
│       ├── Header.tsx
│       ├── Footer.tsx
│       ├── LoadingSpinner.tsx
│       └── ErrorBoundary.tsx
│
├── lib/
│   ├── api.ts              ← Wrapper fetch (Supabase REST)
│   ├── hooks/
│   │   ├── useParticipants.ts
│   │   ├── useDemographics.ts
│   │   └── useCohortStats.ts
│   ├── utils/
│   │   ├── formatting.ts   ← Format numbers, dates
│   │   ├── calculations.ts ← Avg, % calcs
│   │   └── colors.ts       ← Paleta consistente
│   └── supabase.ts         ← Supabase client config
│
├── data/
│   └── mock.json           ← Datos para testing sin conectar API
│
├── styles/
│   └── globals.css
│
├── .env.local              ← SUPABASE_URL, SUPABASE_ANON_KEY
├── package.json
├── tsconfig.json
├── tailwind.config.js
└── next.config.js
```

CONFIGURACIÓN:
1. Next.js config:
   - Image optimization (Netlify adapter)
   - API routes middleware para auth
   - ISR (incremental static regeneration): revalidate cada 3600s

2. Dependencias:
   ```json
   {
     "@supabase/supabase-js": "^2.x",
     "@tanstack/react-query": "^5.x",  // "react-query@3" está obsoleto desde 2022; alternativa: swr
     "recharts": "^2.x",
     "tailwindcss": "^3.x",
     "clsx": "^2.x"
   }
   ```

3. TypeScript types:
   - Crear `types/index.ts` con interfaces para Participant, Course, etc.
   - Sync con schema Supabase

CRITERIO:
✅ Proyecto arranca con `npm run dev`
✅ TypeScript: sin errores
✅ Build size < 500KB (main bundle)
```

---

### Prompt 3.2: Implementar 5 Vistas Principales

```
CONTEXTO:
- MVP requiere 5 vistas funcionales
- Cada una muestra métricas distintas del plan
- Datos vienen de Supabase REST API
- Filtros interactivos (ciudad, estrato, cohorte, etc.)

TAREA:

**VISTA 1: Dashboard Overview**
- KPIs: Total participantes | Con emprendimiento | Cursos completados
- Gráfico: Distribución por estado (en progreso, completado, abandonado)
- Gráfico: Evolución de participantes por mes (tendencia)
- Filtros: Cohorte, ciudad (aplican a todo)

**VISTA 2: Emprendimiento**
- Estadística: % con emprendimiento por cohorte
- Scatter plot: X=cursos completados, Y=tiene emprendimiento (bubble chart)
- Tabla: Top emprendimientos por frecuencia (nombre, cantidad participantes)
- Filtros: Cohorte, ciudad

**VISTA 3: Perfil Sociodemográfico**
- Distribución por tipo vivienda (bar chart: arrendado, familiar, propia)
- Distribución por estrato (bar chart: 1-6)
- Distribución por ciudad (top 10, rest="Otra")
- Box plot: Edad (min, Q1, median, Q3, max)
- Distribución estado civil (pie chart)
- Distribución nivel estudio (horizontal bar)
- Filtros: Cohorte

**VISTA 4: Análisis de Retirados (Churn)**
- Tabla: Personas con 0% avance desde hace 3+ meses
- Gráfico: Motivo retiro si está disponible en datos
- Gráfico: Tasa de churn por cohorte
- Acción: Botón "Exportar para seguimiento"
- Filtros: Cohorte, fecha rango

**VISTA 5: Detalle Participante — SOLO ADMIN, NUNCA pública** ⚠️
- Búsqueda por nombre/email = PII → esta vista viola la convención del proyecto si es pública.
  Requiere auth (Supabase Auth) + RLS ANTES de existir; si no hay auth en el MVP, NO construirla.
- Alternativa MVP coherente con Decisión 3/4: reemplazarla por "Vista 5: Comparativo Cohortes"
  (agregados, como ya la define ARQUITECTURA-VISUAL.md — los dos docs eran inconsistentes aquí)
- Card: Datos demográficos + emprendimiento (solo tras login admin)
- Timeline: Cursos e inscripción/completación
- Notas: Admin puede agregar notas privadas

ESPECIFICACIONES POR VISTA:
- Loading state: spinner + skeleton screens
- Error handling: mensajes claros si API falla
- Responsive: mobile-first, funciona en mobile
- Performance: React Query caching, evita refetch innecesarios
- Accesibilidad: labels, aria-labels, colores contrastantes

DATOS MOCKEADOS:
- `data/mock.json` con ejemplos para testing offline
- Componentes aceptan `mock={true}` flag en desarrollo

CRITERIO:
✅ Todas 5 vistas funcionales sin conectar BD
✅ Filtros funcionan (URL params, synced con componentes)
✅ Gráficos renderean sin errores
✅ Performance: < 2s load time en network normal
```

---

### Prompt 3.3: Deploy a Netlify

```
CONTEXTO:
- Hosting: Netlify (gratis tier)
- Build: Next.js con adapter Netlify
- Environment: SUPABASE_URL, SUPABASE_ANON_KEY
- Domain: TBD (puede ser custom o Netlify free)

TAREA:
1. Configurar netlify.toml (⚠️ corregido en revisión — la versión anterior con
   `publish = ".next"` + redirect SPA a /index.html ROMPE el SSR/ISR de Next.js):
   ```toml
   [build]
   command = "npm run build"
   functions = "netlify/functions"
   # NO fijar publish=".next" ni redirects manuales:
   # el plugin oficial maneja SSR, ISR, imágenes y rutas
   [[plugins]]
   package = "@netlify/plugin-nextjs"
   ```

2. Netlify Functions (si es necesario para Edge Logic):
   - `functions/cache-revalidate.ts` - Trigger ISR manual
   - `functions/export-csv.ts` - Download datos como CSV

3. Environment variables en Netlify UI:
   - SUPABASE_URL
   - SUPABASE_ANON_KEY
   - NEXT_PUBLIC_SITE_URL (para links)

4. Deploy:
   - Conectar GitHub repo
   - Automatic deploy on push to main
   - Preview deploys para PRs

5. Monitoreo:
   - Sentry integration para error tracking
   - Analytics básico (Netlify built-in)
   - Performance monitoring (Web Vitals)

6. CI/CD:
   - GitHub Actions: test + build antes de deploy
   - Workflow: on push to main, run tests, build, deploy

CRITERIO:
✅ Dashboard vivo en https://[project].netlify.app
✅ Deploy automático funciona
✅ Environment secrets configurados (no en Git)
✅ HTTPS enabled
```

---

## FASE 4: VALIDACIÓN

### Prompt 4.1: Testing de Integridad de Datos

```
CONTEXTO:
- Antes de marcar como "listo", validar datos end-to-end
- Q10 → Supabase → API → Dashboard: sin pérdida
- Números deben coincidir en todas las capas

TAREA:
Script `tests/data_integrity_test.py`:

1. Validar Supabase:
   - Count participants vs. Q10 original
   - Count enrollments vs. expected
   - Campos nulls < 5% (excepto optional fields)

2. Validar API:
   - GET /cohorte_stats retorna N cohortes esperadas
   - GET /participants con filter=true retorna subset correcto
   - Cache headers presentes (Cache-Control, ETag)

3. Validar Dashboard:
   - Números en KPI cards = datos en Supabase
   - Gráficos se renderean sin errores console
   - Filtros reducen datos correctamente

4. Report:
   - CSV con validaciones (PASS/FAIL por punto)
   - Si FAIL, log detalles para debug

CRITERIO:
✅ 100% validaciones PASS
✅ Dashboard pronto para demo stakeholders
```

---

## 🎯 RESUMEN POR TAREA

| Fase | Prompt | Tiempo Est. | Complejidad | Status |
|------|--------|------------|-------------|--------|
| 0.1 | Schema Supabase | 2h | Media | ⬜ |
| 0.2 | Credenciales & Setup | 1h | Baja | ⬜ |
| 1.1 | Validación Python | 1.5d | Alta | ⬜ |
| 1.2 | n8n Workflow | 1d | Media | ⬜ |
| 2.1 | REST API Docs | 4h | Baja | ⬜ |
| 2.2 | Materialized Views | 8h | Alta | ⬜ |
| 3.1 | Next.js Setup | 1d | Media | ⬜ |
| 3.2 | Vistas Principal | 2-3d | Alta | ⬜ |
| 3.3 | Deploy Netlify | 4h | Baja | ⬜ |
| 4.1 | Testing | 1d | Media | ⬜ |

---

## 📋 USO: COPY-PASTE EN CLAUDE CODE

1. Abre [Claude Code](https://claude.com/code) (o local install)
2. Copia el prompt correspondiente (completo)
3. Paste en chat
4. Claude Code genera código listo para usar
5. Guarda output en repo

**Ejemplo:**
```bash
# Copié Prompt 0.1 completo
# Claude Code outputs:
# - schema.sql
# - setup_indexes.sql
# - policies.sql
# - README.md

git add docs/sql/*
git commit -m "feat: supabase schema phase 0"
```

---

**Próxima actualización:** Post-Phase 1 validation
**Revisado por Claude Code (2026-07-09):** corregidos — ENUM inline (sintaxis MySQL) → CREATE TYPE;
uuid_generate_v4() sin extensión → gen_random_uuid(); regla "primaria ⇒ edad<20" (falsa) → warning
razonable; cron "23:00 ET" → 23:00 COT + riesgo PC apagado; endpoint público de participants
individuales eliminado (PII); rate limiting "nativo" (no existe) → caching; view_retirados alineada
con definición canónica; react-query@3 → @tanstack/react-query@5; netlify.toml roto → plugin oficial;
Vista 5 marcada solo-admin. Project ID de Supabase en schema-supabase-completo.sql no existe en la
cuenta actual — verificar antes de Fase 0.
