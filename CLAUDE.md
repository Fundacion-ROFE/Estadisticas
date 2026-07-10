# Proyecto: Automatizaciones — Fundación ROFÉ / Jóvenes creaTIvos

Automatización progresiva de procesos manuales usando n8n (self-hosted, local en PC de Samuel)
como orquestador, integrado con Google Workspace y APIs externas (Q10, Zoom). Un proceso a la
vez. Dashboard público en GitHub Pages. Herramientas locales con PII en `tools/` (gitignoreado).

---

## Arquitectura

```
/
├── CLAUDE.md                   ← Este archivo
├── claude_sessions.md          ← Bitácora histórica (solo append)
├── iniciar_n8n.bat             ← Arranca n8n + ngrok dominio fijo (~45 s)
│
├── docs/                       ← Vault de Obsidian + GitHub Pages root
│   ├── 00-vision-global.md     ← MOC / Home de Obsidian
│   ├── convenciones.md         ← Estándares técnicos reutilizables
│   ├── procesos/
│   │   ├── mapa-codigo.md      ← Índice de todos los scripts (leer antes de tocar código)
│   │   ├── q10-consolidacion.md
│   │   ├── dashboard-web.md
│   │   └── zoom-asistencia.md
│   ├── plantillas/
│   │   └── plantilla-proceso.md
│   ├── dashboard/              ← Tab 1: stats Q10 (data.json ← export_stats.py)
│   ├── avance/                 ← Tab 2: avance manual (data.json ← export_avance.py)
│   ├── retirados/              ← Panel retirados (data.json ← export_retirados.py)
│   ├── asistencia/             ← Standalone backup (no en dashboard activo)
│   └── diferencias/            ← Standalone backup (no en dashboard activo)
│
├── scripts/q10-consolidacion/
│   ├── q10_to_sheets.py        ← Extracción Q10 → Google Sheets (bot Telegram)
│   ├── export_stats.py         ← h2test → docs/dashboard/data.json → git push
│   ├── export_avance.py        ← pestaña Avance → docs/avance/data.json → git push
│   ├── export_retirados.py     ← pestaña Retirados → docs/retirados/data.json → git push
│   ├── export_asistencia.py    ← pestaña asistencias → docs/asistencia/data.json (backup)
│   ├── setup_headers.py        ← Inicialización headers fila 1 (uso único)
│   └── organizador/            ← App GUI .exe para operadores no técnicos
│
├── scripts/mr-actualizacion-datos/
│   └── actualizar_bd_mr.py     ← Form MR2024 → BD-Mujeres ROFÉ (General) + Fecha Actualización
│
├── scripts/panel-datos/
│   ├── normalize_q10_data.py   ← h2test → payload normalizado (tools/, PII) — Fase 1a
│   ├── cargar_supabase.py      ← payload → Supabase (snapshot + upserts, idempotente)
│   ├── sync_sociodemograficos.py ← BD monitorias (xlsx) → participants (género/edad/ciudad/emp)
│   └── test_conexion_supabase.py ← Smoke test REST+RLS del proyecto Supabase panel-datos-rofe
│
├── tools/                      ← LOCAL ONLY — gitignoreado — contiene PII
│   └── panel_riesgo.py         ← Cruce Avance × h2test por email → reporte de riesgo
│
├── n8n-workflows/              ← JSONs exportados de n8n
├── runbooks/                   ← Guías para operadores no técnicos
└── .claude/skills/             ← Skills invocables en esta sesión
```

---

## Tabla de componentes

| Script | Proceso | Runbook | Salida pública |
|---|---|---|---|
| `q10_to_sheets.py` | [[q10-consolidacion]] | [[q10-actualizar]] | — |
| `export_stats.py` | [[dashboard-web]] | — | `docs/dashboard/data.json` |
| `export_avance.py` | [[dashboard-web]] | — | `docs/avance/data.json` |
| `export_retirados.py` | [[q10-consolidacion]] · [[dashboard-web]] | — | `docs/retirados/data.json` |
| `retirados_headless.py` | [[q10-consolidacion]] | — | — |
| `panel_riesgo.py` | [[dashboard-web]] | — | Local solamente |
| `setup_headers.py` | [[q10-consolidacion]] | — | — |
| `actualizar_bd_mr.py` | [[mr-actualizacion-datos]] | — | — (escribe en BD-Mujeres ROFÉ) |
| `exportar_sin_completar.py` | [[q10-consolidacion]] | — | — (escribe en Sheet privado SinCompletar) |
| `normalize_q10_data.py` | [[panel-datos-etl]] | — | — (payload PII en tools/) |
| `cargar_supabase.py` | [[panel-datos-etl]] | — | — (escribe en Supabase panel-datos-rofe) |
| `sync_sociodemograficos.py` | [[panel-datos-etl]] | — | — (BD monitorias → Supabase) |
| `test_conexion_supabase.py` | [[panel-datos-etl]] | — | — (verifica RLS de Supabase con anon key) |
| n8n workflow | [[q10-consolidacion]] | [[q10-actualizar]] | — |
| n8n `q10-sync-supabase` | [[panel-datos-etl]] | — | — (sync diario 9:45 → Supabase) |

Ver [[mapa-codigo]] para firma completa de cada script.

---

## Skills disponibles

| Skill | Invocar | Cuándo |
|---|---|---|
| compact | `/compact` | Respuestas cortas — ahorra tokens |
| proceso-nuevo | `/proceso-nuevo <nombre>` | Al iniciar cualquier proceso nuevo |
| doc-sync | `/doc-sync` | Al cerrar cualquier sesión de trabajo |
| n8n-standards | automático | Al trabajar con workflows de n8n |

---

## Antes de empezar CUALQUIER tarea nueva

1. Lee `docs/00-vision-global.md` — estado de todos los procesos de un vistazo.
2. Lee `docs/convenciones.md` — no reinventar estándares ya definidos.
3. Lee `docs/procesos/mapa-codigo.md` — antes de tocar cualquier script.
4. Revisa `docs/procesos/` — si el proceso nuevo se parece a uno existente, reutiliza.
5. Lee las últimas 3-5 entradas de `claude_sessions.md` — contexto reciente.

## Durante la tarea

- Decisión de diseño importante → anotarla inmediatamente en la nota del proceso.
- Gotcha (algo que no funcionó como se esperaba) → documentarlo en sección "Gotchas" del proceso.

## Al terminar (SIEMPRE, sin excepción)

1. Actualiza `docs/procesos/<proceso>.md` (no duplicar — actualizar).
2. Patrón reutilizable nuevo → agregar a `docs/convenciones.md`.
3. Flujo n8n cambiado → exportar JSON a `n8n-workflows/`.
4. Agrega entrada al FINAL de `claude_sessions.md` (5-10 líneas, formato del archivo).
5. Enlace bidireccional si el proceso conecta con otro → `[[nombre-proceso]]` en ambas notas.
6. Actualiza `docs/00-vision-global.md` — mover proceso entre pendiente/en-progreso/completado.

---

## Convenciones técnicas rápidas

Ver `docs/convenciones.md` para detalle completo.

- **Nombres n8n:** `[area]-[accion]` minúsculas con guiones (`zoom-asistencia`, `q10-consolidacion`).
- **Error handling:** todo workflow debe tener camino de error explícito — nunca fallar en silencio.
- **SSL corporativo:** `truststore.inject_into_ssl()` al inicio de todo script Python. Git: `git config http.sslBackend schannel`.
- **Doble encabezado en Sheets:** fila 1 = nombres fusionados (vacíos después del primero). Detectar grupos por sub-header en fila 2. Ver patrón en [[mapa-codigo]].
- **Privacidad:** PII nunca a GitHub. Solo JSON agregados en `docs/`. Datos individuales en `tools/` (gitignoreado).
- **Credenciales:** Service Account `q10-automatizacion@n8n-automatizacion-q10.iam.gserviceaccount.com`. Documentar en [[convenciones]], nunca duplicar por workflow.
