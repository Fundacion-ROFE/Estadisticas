# Matriz de Decisiones Pendientes
**Para que Samuel tome decisiones informadas antes de empezar Fase 0**

---

## 📊 DECISIÓN 1: Fuente Única de Verdad

### Pregunta
¿De dónde viene la "BD limpia" y quién la alimenta?

### Opciones

#### **Opción A: Sync automático diario Q10 → Supabase** (RECOMENDADO ⭐)
**Cómo:** n8n corre diariamente (04:00 UTC = 23:00 Colombia), extrae de Google Sheets (proxy de Q10), normaliza, carga Supabase
- **Pros:** Zero manual work, siempre actualizado, auditable
- **Contras:** Q10 NO tiene API — la extracción real es scraping → Sheets (bot existente); depende de que el PC de Samuel esté encendido a esa hora; requiere normalización robusta
- **Costo:** Computacional bajo (< 5 min/día), Supabase gratis tier (⚠️ free tier pausa el proyecto tras ~1 semana sin actividad y no incluye backups automáticos)

#### **Opción B: Hybrid manual + sync**
**Cómo:** Admins pueden hacer corrections manuales en Airtable, sync diario valida
- **Pros:** Flexibilidad, correcciones rápidas de errores
- **Contras:** Complejidad de merge (manual vs. auto), mayor overhead
- **Costo:** Airtable free tier + Supabase

#### **Opción C: Manual completamente (Supabase UI)**
**Cómo:** Operadores actualizan datos directamente en Supabase admin panel
- **Pros:** Control total, no automated faults
- **Contras:** Manual tedioso, error-prone, no escalable, requiere training
- **Costo:** Solo Supabase

### 🎯 Recomendación
**Opción A** (Sync automático). Razón: Proyecto ya tiene n8n + Google Sheets. Usar el mismo patrón.

---

## 📊 DECISIÓN 2: Histórico de Datos

### Pregunta
¿Qué nivel de histórico mantener? ¿Rastrear cambios en el tiempo?

### Opciones

#### **Opción A: Solo estado actual (SCD Type 1)**
**Cómo:** Actualizar registros en lugar, sin histórico
- **Pros:** Simple, base datos pequeña
- **Contras:** Imposible ver evolución, auditoría limitada
- **Ejemplo:** Si participante cambia ciudad, se sobrescribe (perdemos histórico)

#### **Opción B: Full histórico (SCD Type 2 con timestamps)** (RECOMENDADO ⭐)
**Cómo:** Agregar columna `valid_from` y `valid_to`, mantener filas antiguas
- **Pros:** Auditoría completa, reportes históricos, reconciliación
- **Contras:** Base datos crece 2-3x, queries más complejas
- **Ejemplo:**
  ```
  participant_id | ciudad | valid_from | valid_to
  1              | Bogotá | 2024-01-01 | 2024-06-01
  1              | Medellín | 2024-06-01 | NULL
  ```

#### **Opción C: Hybrid (snapshot mensual + current state)**
**Cómo:** Tabla `participants` actual + tabla `participants_snapshots` (monthly backup)
- **Pros:** Histórico a nivel de mes, consultas rápidas
- **Contras:** Granularidad limitada (no puedo ver cambio exacto)

### 🎯 Recomendación
**Escalonada (corregida en revisión):** Opción A + snapshots en Fase 1 → Opción B en Fase 2.

⚠️ **Inconsistencia detectada en el plan original:** se recomendaba B (SCD Type 2), pero el schema
actual (`schema-supabase-completo.sql`) no tiene `valid_from`/`valid_to` y el workflow n8n hace
UPSERT — eso es Type 1. Además el MVP recomendado en Decisión 6 (Opción B, 2 semanas) excluye
histórico explícitamente. Elegir 2-B tal cual obligaría a rediseñar schema y ETL antes del MVP.

**Camino coherente:**
1. **Fase 1 (MVP):** Type 1 (upsert) + tabla `_snapshots` diaria (backup barato, cubre auditoría básica)
2. **Fase 2:** migrar a SCD Type 2 si se confirma la necesidad de:
   - Auditoría fina (quién cambió qué, cuándo)
   - Análisis de evolución de participantes
   - Reconciliación Q10 (detectar cambios)

---

## 📊 DECISIÓN 3: Permisos y Escritura

### Pregunta
¿Quién tiene permiso de escribir/actualizar datos en Supabase?

### Opciones

#### **Opción A: Solo Admin (recomendado ⭐)**
**Quién puede escribir:** Nadie manualmente; solo n8n + scripts
- **Pros:** Integridad garantizada, audit trail claro, sin inconsistencias
- **Contras:** Correcciones manuales requieren script custom

#### **Opción B: Admin + Profesores (en sus datos)**
**Quién puede escribir:** Admin + profesores pueden corregir datos de sus estudiantes
- **Pros:** Operadores pueden fix errores menores rápido
- **Contras:** RLS compleja, riesgo de cambios accidentales, auditoría difícil

#### **Opción C: Público (crowdsource corrections)**
**Quién puede escribir:** Participantes pueden actualizar su perfil
- **Pros:** Datos más frescos, participación
- **Contras:** Validación pesada, spam risk, PII exposure

### 🎯 Recomendación
**Opción A + escalable**. Implementar así:
1. Fase 1: Solo admin (n8n write)
2. Fase 2: Agregar UI de admin para corrections manuales (con audit log)
3. Fase 3+: Si demanda, considerar Opción B (Profesores limitado)

---

## 📊 DECISIÓN 4: Visibilidad de Datos

### Pregunta
¿Es el dashboard público o requiere login? ¿Qué datos son públicos?

### Opciones

#### **Opción A: Completamente Pública** (RECOMENDADO ⭐)
**Acceso:** Anónimo, no requiere login, datos agregados + filtrable
- **Pros:** Máxima visibilidad, no overhead de auth, embebible (iFrame)
- **Contras:** Mínima privacidad, los datos están expuestos
- **Implementación:** `is_public=true` en tablas agregadas, RLS policy por defecto

#### **Opción B: Login Requerido**
**Acceso:** Google/email login, diferentes niveles por rol
- **Pros:** Control de acceso, auditoría de quién ve qué
- **Contras:** Overhead de auth, menor alcance
- **Implementación:** Supabase Auth + Next.js middleware

#### **Opción C: Hybrid (Agregados públicos, detalles con login)**
**Acceso:** KPIs y gráficos públicos, pero click-through requiere login
- **Pros:** Balance entre visibilidad y privacidad
- **Contras:** UX más complejo, 2 capas de auth

### 🎯 Recomendación
**Opción A** (Pública). Razón:
- Datos ya son agregados (sin PII)
- ROFÉ es fundación con misión de visibilidad
- Menores costos operacionales

**But:** Asegurar RLS policy (corregida — `cohorte_stats` NO tiene columna `is_public`;
es tabla de agregados sin PII, lectura abierta como ya define `schema-supabase-completo.sql`):
```sql
-- Agregados por cohorte: lectura pública (sin PII)
CREATE POLICY "cohorte_stats_publico"
  ON cohorte_stats FOR SELECT
  USING (true);

-- Filas individuales (participants): SOLO con is_public = true,
-- y aun así el dashboard público debe consumir únicamente vistas agregadas
CREATE POLICY "datos_publicos_lectura"
  ON participants FOR SELECT
  USING (is_public = true);
```

---

## 📊 DECISIÓN 5: Reemplazo de Power BI (Tool)

### Pregunta
¿Dashboard custom vs. herramienta BI? ¿Qué features necesitan?

### Features Requeridas
- ✅ Filtros interactivos (ciudad, cohorte, estrato)
- ✅ Múltiples tipos de gráficos (bar, pie, scatter, box)
- ✅ Datos actualizados diariamente
- ✅ Exportar a CSV/PDF
- ❓ SQL Ad-Hoc queries por usuarios finales (si sí → BI tool)
- ❓ Permisos granulares por rol (si sí → BI tool)

### Opciones

#### **Opción A: Dashboard Custom (React + Recharts)** (RECOMENDADO ⭐)
**Cómo:** Build en Next.js, host en Netlify
- **Pros:** Control total, bajo costo, UX personalizado, integración fácil
- **Contras:** Mantenimiento continuo, menos features avanzadas
- **Timeline:** 3-5 días
- **Costo:** Free (Netlify)

#### **Opción B: Metabase (Open Source BI)**
**Cómo:** Self-host en Docker, conectar a Supabase
- **Pros:** Zero-code, SQL Lab para power users, dashboards complejos
- **Contras:** Overhead operacional (otro servicio), curva aprendizaje
- **Timeline:** 2-3 días setup
- **Costo:** Free (self-hosted) + compute

#### **Opción C: Apache Superset**
**Cómo:** Self-host en Docker, diseño profesional
- **Pros:** Muy profesional, muchas features
- **Contras:** Overkill para MVP, curva aprendizaje pronunciada
- **Timeline:** 3-4 días setup
- **Costo:** Free (self-hosted) + compute

#### **Opción D: Hybrid (Custom dashboard + Metabase backend)**
**Cómo:** Dashboard custom (usuarios normales) + Metabase (poder users)
- **Pros:** Lo mejor de ambos
- **Contras:** Más mantenimiento, más complejidad
- **Timeline:** 5-7 días total

### 🎯 Recomendación
**Opción A (MVP) + Opción B (Fase 2)**

**Fase 1:** Dashboard custom Next.js
- Suficiente para 95% de casos de uso
- Rápido de iterar
- Bajo costo

**Fase 2:** Si usuarios piden SQL adhoc → agregar Metabase como companion tool

---

## 📊 DECISIÓN 6: Timeline y MVP

### Pregunta
¿Cuándo activar? ¿MVP mínimo vs. feature-complete?

### Opciones

#### **Opción A: MVP en 1 semana**
**Scope:**
- ✅ 1 tabla (cohorte_stats) en Supabase
- ✅ Dashboard básico: 3 gráficos
- ✅ Filtro: cohorte solamente
- ❌ Histórico, exportar, RLS complejo

**Ventaja:** Feedback rápido, deployment antes de agosto
**Riesgo:** Incompleto, puede necesitar refactor

#### **Opción B: MVP en 2 semanas (RECOMENDADO ⭐)**
**Scope:**
- ✅ Schema completo (participants, courses, enrollments, metrics)
- ✅ ETL robusto (validación, error handling)
- ✅ Dashboard 5 vistas
- ✅ Filtros: cohorte, ciudad, estrato
- ✅ RLS básico
- ✅ Deploy en Netlify

**Ventaja:** Feature-complete, listo para uso real
**Timeline:** Según cronograma promedio

#### **Opción C: Full-featured en 4 semanas**
**Scope:** Todo Option B +
- ✅ Histórico (SCD Type 2)
- ✅ Exportar CSV/PDF
- ✅ Admin UI para corrections
- ✅ Metabase companion
- ✅ Tests exhaustivos

**Ventaja:** Producción-ready desde día 1
**Riesgo:** Scope creep, puede tomar más

### 🎯 Recomendación
**Opción B** (MVP 2 semanas). Razón:
- Schema completo desde el inicio (no refactor después)
- Suficiente para stakeholders
- Flexible para agregar features después
- Timeline realista

---

## 🎬 PLAN DE DECISIONES POR SAMUEL

### ✅ MATRIZ COMPLETADA (2026-07-09 — opciones recomendadas, aprobadas por Samuel)

| Decisión | Opción Elegida | Notas | Confirmación |
|----------|---|---|---|
| 1. Fuente de verdad | **A** | Sync n8n diario — mismo patrón que ya usa el proyecto (Q10→Sheets→export). PC debe estar encendido a las 23:00 COT | ✅ |
| 2. Histórico | **Escalonada (A+snapshots → B)** | Fase 1: Type 1 (upsert) + tabla `participants_snapshots` diaria (ya creada). Fase 2: SCD Type 2 si se confirma necesidad | ✅ |
| 3. Permisos | **A** | Solo n8n/service_role escribe. Admin UI con audit log en Fase 2 si hace falta | ✅ |
| 4. Visibilidad | **A** | Dashboard público, pero consume SOLO agregados (cohorte_stats, views) — nunca filas individuales. RLS verificada con smoke test | ✅ |
| 5. BI Tool | **A** | Dashboard custom Next.js + Recharts en Netlify. Metabase solo si en Fase 2 piden SQL ad-hoc | ✅ |
| 6. Timeline | **B** | MVP 2 semanas con schema completo — evita refactor posterior | ✅ |

### Una vez completada:
1. Copiar tabla en respuesta a Claude
2. Claude actualiza:
   - `PLAN-DATOS-ANALISIS-PROFUNDO.md` (Decisiones Finales)
   - `CLAUDE-CODE-PROMPTS-POR-FASE.md` (adaptado a decisiones)
   - Timeline y orden de ejecución

---

## 📝 Ejemplo de Respuesta (Samuel)

```
| Decisión | Opción Elegida | Notas | Confirmación |
|----------|---|---|---|
| 1. Fuente de verdad | A | n8n diario es lo que ya tenemos | ✅ |
| 2. Histórico | B | Necesitamos auditoría para ROFÉ | ✅ |
| 3. Permisos | A | Solo admin por ahora, escalamos después | ✅ |
| 4. Visibilidad | A | Dashboard público, ROFÉ es transparente | ✅ |
| 5. BI Tool | A | Custom dashboard primero, Metabase si escalamos | ✅ |
| 6. Timeline | B | 2 semanas MVP, realista | ✅ |
```

---

**Próximo paso:** Samuel completa matriz → Claude refina prompts → Inicia Fase 0

**Revisado por Claude Code (2026-07-09):** corregida la contradicción Decisión 2↔6 (histórico
recomendado pero no implementado en schema/ETL → recomendación escalonada), la policy de ejemplo
sobre `cohorte_stats` (usaba columna `is_public` inexistente) y la mención a "API Q10" (no existe;
es scraping → Sheets).
