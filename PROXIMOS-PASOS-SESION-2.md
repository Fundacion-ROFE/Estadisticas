# Próximos Pasos: Sesión 2 (Ejecución)
**Después de que Samuel complete matriz de decisiones**

---

## 🎯 Objectivo Sesión 2

Comenzar **Fase 0 (Setup Supabase)** con prompts optimizados, listos para Claude Code.

---

## ✅ Checklist PRE-SESIÓN 2

Antes de que Samuel inicie sesión 2, debe tener listos:

### 1. **Tabla de Decisiones Completada**
- Archivo: `MATRIZ-DECISIONES-PENDIENTES.md`
- Estado: Todas 6 decisiones completadas ✅
- Acción: Copiar/pegar respuesta en chat de sesión 2

### 2. **Cuenta Supabase Funcionando**
> ⚠️ **Estado real verificado (2026-07-09):** el project ID `sqmrnirbakcrbhdlfxxz` que referencia
> `schema-supabase-completo.sql` NO existe en la cuenta de Samuel. Los únicos proyectos son
> "samueldavidhhuhuhhuhuh's Project" y "DRAFT", **ambos INACTIVE** (pausados por free tier).
- [ ] Reactivar uno de los proyectos existentes O crear proyecto nuevo con nombre serio
      (ej. `panel-datos-rofe`)
- [ ] Actualizar el Proyecto ID en `schema-supabase-completo.sql`
- [ ] URL y keys listadas (ejemplo):
  ```
  SUPABASE_URL=https://xyzabc.supabase.co
  SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIs...
  ```
- [ ] Test de conexión: Supabase UI abre sin errores

### 3. **n8n Corriendo Localmente**
- [ ] Instancia n8n en PC de Samuel funciona
- [ ] Accesible en `http://localhost:5678`
- [ ] Credenciales Google Sheets conectadas y testeadas

### 4. **Repositorio Preparado**
- [ ] Rama `feature/datos-panel` creada y switcheada
- [ ] Estructura de carpetas: `/docs`, `/scripts`, `/n8n-workflows`
- [ ] `.gitignore` actualizado para `tools/`, `.env.local`, `logs/`

### 5. **Documentación Leída**
- [ ] `PLAN-DATOS-ANALISIS-PROFUNDO.md` (entendida la arquitectura)
- [ ] `CLAUDE-CODE-PROMPTS-POR-FASE.md` (conocer qué viene)
- [ ] `MATRIZ-DECISIONES-PENDIENTES.md` (llenar antes de sesión 2)

---

## 📋 AGENDA SESIÓN 2

### Pre-trabajo (5 minutos)
1. Samuel paste tabla decisiones completada
2. Claude valida decisiones, señala gaps si hay
3. Claude actualiza prompts según decisiones

### FASE 0: Setup Supabase (30-45 minutos)
**Objetivo:** BD lista con schema base

**Pasos:**
1. [ ] Copy Prompt 0.1 → paste en Claude Code
   - Output: `schema.sql`, `indexes.sql`, `policies.sql`
2. [ ] Ejecutar SQL en Supabase
   - Validar: 5 tablas creadas sin errores
3. [ ] Copy Prompt 0.2 → paste en Claude Code
   - Output: `.env.example`, README setup
4. [ ] Validar conexión: Script Python test-query
5. [ ] Commit: `git add docs/sql/ .env.example && git commit`

**Resultado esperado:** Supabase con schema + credenciales configuradas ✅

---

### FASE 1a: Validación Python (1-2 horas)
**Objetivo:** Script de normalización de datos

**Pasos:**
1. [ ] Copy Prompt 1.1 → paste en Claude Code
   - Especificar: ¿De dónde vienen los datos Q10 actualmente?
   - Output: `scripts/q10-consolidacion/normalize_q10_data.py`
2. [ ] Adaptar script según estructura actual de Google Sheets
3. [ ] Test con muestra de 100 registros reales
   - Validar: Reporte de errores correcto
   - Validar: Datos limpios en output JSON
4. [ ] Commit: `git add scripts/q10-consolidacion/normalize_q10_data.py`

**Resultado esperado:** Script robusto de normalización probado ✅

---

### FASE 1b: n8n Workflow (1.5 horas)
**Objetivo:** Automatización ingesta diaria

**Pasos:**
1. [ ] Copy Prompt 1.2 → paste en Claude Code
   - Especificar: URLs exactas de Google Sheets (tabs names)
   - Output: Diagrama n8n workflow (JSON exportable)
2. [ ] Crear workflow en n8n UI manualmente o import JSON
3. [ ] Conectar credenciales:
   - Google Sheets API
   - Supabase Service Role Key
   - Email (para error handling)
4. [ ] Test: Correr workflow manualmente
   - Monitorear: Logs del workflow
   - Validar: Registros en Supabase (SELECT COUNT(*) FROM participants)
   - Validar: Email de error si introduce data corrupta
5. [ ] Programar: Cron 04:00 UTC
6. [ ] Exportar: JSON a `n8n-workflows/q10-sync-supabase.json`
7. [ ] Commit: `git add n8n-workflows/`

**Resultado esperado:** Workflow n8n automático testeado ✅

---

### Post-Sesión 2 (Documentación)
**Acción:** Ejecutar skill `/doc-sync`

1. Actualizar `docs/procesos/panel-datos-etl.md`:
   - Resumen Fase 0-1b
   - Links a prompts usados
   - Gotchas encontrados
   - Próximas fases

2. Actualizar `claude_sessions.md`:
   - Resumen 5-10 líneas
   - Decisiones tomadas
   - Estado repo

3. Actualizar `docs/00-vision-global.md`:
   - Estado "panel-datos": "En progreso - Fase 1b completada"
   - Próximo: "Fase 2: Backend API"

---

## 🛠️ HERRAMIENTAS NECESARIAS

| Herramienta | Versión Mínima | Instalado? |
|---|---|---|
| Python | 3.8+ | ☐ |
| n8n | Latest | ☐ |
| git | 2.30+ | ☐ |
| Node.js (para Netlify después) | 18+ | ☐ |

---

## 📊 CRONOGRAMA ESTIMADO

| Fase | Sesión | Duración Est. | Completitud |
|------|--------|--------------|---|
| 0 Setup | 2 | 45 min | 🟦 |
| 1a Validación | 2 | 1.5h | 🟦 |
| 1b n8n | 2 | 1.5h | 🟦 |
| **Total Sesión 2** | **2** | **~3.5h** | ✅ |
|   |   |   |   |
| 2.1 API Docs | 3 | 4h | ⬜ |
| 2.2 Materialized Views | 3 | 8h | ⬜ |
| 3.1 Next.js Setup | 3-4 | 1d | ⬜ |
| 3.2 Vistas Principales | 4 | 2-3d | ⬜ |
| 3.3 Deploy Netlify | 5 | 4h | ⬜ |
| 4 Testing | 5 | 1d | ⬜ |
| **Total Proyecto** | **2-5** | **~10d** | ❓ |

**Nota:** Sesión 2 es critical path. Fases 1-4 pueden paralelizarse parcialmente.

---

## ⚠️ RIESGOS A MONITOREAR

### Risk 1: Cambios en schema Q10
**Mitigación:** Script validation semanal en n8n, alertas si campos faltantes

### Risk 2: Data duplication en ingesta
**Mitigación:** UNIQUE(q10_id) constraint, tests antes de upsert

### Risk 3: Supabase quota exceeded
**Mitigación:** Monitor usage, cache API responses en frontend

### Risk 4: Credenciales expuestas en Git
**Mitigación:** `.gitignore` checklist, pre-commit hook

### Risk 5: Free tier de Supabase pausa el proyecto (agregado en revisión)
Free tier pausa proyectos tras ~1 semana sin actividad → dashboard público muere en silencio.
**Mitigación:** El sync diario n8n lo mantiene vivo SI el PC está encendido; monitorear estado
del proyecto; evaluar plan Pro (~$25/mes, incluye además backups diarios que free tier NO tiene).

### Risk 6: Cifras divergentes vs. dashboard actual (agregado en revisión)
El dashboard GitHub Pages ya publica cifras verificadas (identidad 832 = 775 activos + 57
retirados). Si el panel nuevo calcula distinto (otra definición de retirado, desertores incluidos),
los stakeholders verán dos verdades.
**Mitigación:** Correr ambos en paralelo; test de cuadre obligatorio (Fase 4) contra los JSON de
`docs/dashboard|aprobacion|retirados` antes de reemplazar nada.

---

## 💾 ARCHIVOS CREADOS EN SESIÓN 1

| Archivo | Propósito | Revisar? |
|---------|-----------|----------|
| `PLAN-DATOS-ANALISIS-PROFUNDO.md` | Análisis + arquitectura | ✅ Sí |
| `CLAUDE-CODE-PROMPTS-POR-FASE.md` | Prompts copy-paste | ✅ Sí |
| `MATRIZ-DECISIONES-PENDIENTES.md` | Decisiones pending | ✅ OBLIGATORIO |
| `PROXIMOS-PASOS-SESION-2.md` | Este archivo | Referencia |

---

## 🚀 QUICK START SESIÓN 2

### Línea 1: Completar decisiones
```
📄 Abre: MATRIZ-DECISIONES-PENDIENTES.md
✍️ Completa la tabla (6 decisiones)
📤 Paste resultado en chat
```

### Línea 2: Fase 0 Setup
```
📄 Abre: CLAUDE-CODE-PROMPTS-POR-FASE.md
📋 Ve a Sección "FASE 0: SETUP SUPABASE"
📋 Prompt 0.1: Crear Schema
📋 Prompt 0.2: Credenciales
🔗 Copy → Paste en Claude Code → Ejecuta
```

### Línea 3: Fase 1a Validación
```
📋 Prompt 1.1: Normalización Python
🔗 Copy → Paste en Claude Code
⚙️ Adaptar: Paths de datos actuales
🧪 Test: 100 registros reales
✅ Validar reporte de errores
```

### Línea 4: Fase 1b n8n
```
📋 Prompt 1.2: n8n Workflow
🔗 Copy → Paste en Claude Code
⚙️ Adaptar: URLs Google Sheets, emails
🔌 Conectar credenciales en n8n UI
🧪 Test manual: verificar datos en Supabase
🕐 Programar cron
```

### Línea 5: Documentación
```
✅ Ejecutar: /doc-sync
📝 Actualizar: procesos/panel-datos-etl.md
📝 Actualizar: claude_sessions.md
📝 Actualizar: 00-vision-global.md
🔗 git push
```

---

## ❓ PREGUNTAS COMUNES

**P: ¿Qué pasa si Q10 no tiene API?**
A: Q10 NO tiene API — la extracción real ya es scraping → Google Sheets (bot existente,
`q10_to_sheets.py`). Sheets es el proxy: si Q10 → Sheets funciona ahora, sigue funcionando.

**P: ¿De dónde salen los datos sociodemográficos (vivienda, estrato, estado civil)?**
A: ⚠️ SIN CONFIRMAR — no están en las pestañas actuales (h2test/Avance/Retirados). Candidatas:
BD-Mujeres ROFÉ (form MR2024) y BD Seguimiento de Monitorías. Resolver antes de Fase 1a.

**P: ¿Puedo hacer Fase 1 sin completar Fase 0?**
A: No. Supabase schema es prerequisito para ETL.

**P: ¿Debo hacer todo en una sesión?**
A: No. Sesión 2 = Fases 0-1b (3.5h). Sesión 3+ = Fases 2-4.

**P: ¿Qué si decision matriz tiene conflictos?**
A: Claude señala en sesión 2. Decide en el momento. Documente en `CLAUDE.md`.

---

## 📞 COMUNICACIÓN SESIÓN 2

**Inicio:**
```
"Completé la matriz de decisiones. Aquí está:
[PASTE TABLA]

Estoy listo para Fase 0. Variables de entorno:
SUPABASE_URL=...
SUPABASE_ANON_KEY=...
"
```

**Si hay bloqueador:**
```
"En el paso X, encontré Y. ¿Alternativa?"
```

**Al terminar:**
```
"Fase 0-1b completada. Estado actual:
- Schema en Supabase: ✅
- Normalización Python: ✅
- n8n workflow: ✅
- [Bloqueadores detectados]: [listar]
"
```

---

## 📚 REFERENCIAS EN SESIÓN 2

- [Supabase Docs](https://supabase.com/docs)
- [n8n Workflows](https://n8n.io/docs/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- Convenciones proyecto: `CLAUDE.md` + `docs/convenciones.md`

---

**Documento preparado:** 2026-07-09
**Revisado por Claude Code:** 2026-07-09 — verificado estado real de Supabase (project ID del
schema no existe; 2 proyectos INACTIVE), agregados riesgos 5-6, corregida FAQ de API Q10 y
agregada la pregunta abierta de datos sociodemográficos. Ver notas ⚠️ en los otros 4 documentos.
**Válido hasta:** Post-decisiones Samuel
**Próxima revisión:** Sesión 2 inicio

---

## 🎬 ACCIONES FINALES SESIÓN 1

- [x] Crear análisis profundo (PLAN)
- [x] Crear prompts optimizados (CLAUDE-CODE-PROMPTS)
- [x] Crear matriz decisiones (MATRIZ)
- [x] Crear este documento (NEXT-STEPS)
- [ ] **Samuel**: Completar matriz
- [ ] **Samuel**: Revisar documentos
- [ ] **Claude (Sesión 2)**: Validar decisiones y refinar prompts
- [ ] **Claude (Sesión 2)**: Iniciar Fase 0
