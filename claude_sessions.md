# Bitácora de Sesiones — Claude Code

> Diario cronológico de trabajo. Se agrega una entrada al FINAL de cada sesión.
> Nunca se borra ni reescribe el historial. Formato fijo para que sea fácil de
> escanear rápido al iniciar una sesión nueva.

---

## Cómo usar este archivo (instrucciones para Claude)

Al final de cada sesión de trabajo, agrega una entrada nueva usando esta plantilla:

```
## YYYY-MM-DD — [Proceso] Título corto de lo que se hizo

**Estado:** En progreso / Completado / Bloqueado
**Proceso relacionado:** [[nombre-del-proceso]]

- Qué se hizo (2-4 líneas, lo esencial)
- Decisiones clave tomadas
- Pendiente para la próxima sesión
- Bloqueos (si aplica): qué falta y de quién depende
```

Al iniciar una sesión nueva, lee al menos las últimas 3-5 entradas antes de continuar.

---

## 2026-06-22 — [Setup] Estructura inicial del proyecto

**Estado:** Completado
**Proceso relacionado:** [[00-vision-global]]

- Se creó la estructura de carpetas base: `docs/`, `n8n-workflows/`, `skills/`.
- Se definió `CLAUDE.md` como guía de documentación automática por tarea.
- Se definió este archivo (`claude_sessions.md`) como bitácora cronológica.
- Pendiente: documentar el primer proceso real (Q10) usando esta estructura.

---

## 2026-06-23 — [Q10] Migración del proyecto BOT-Q10 a esta estructura

**Estado:** Completado
**Proceso relacionado:** [[q10-consolidacion]]

- Se migró el proyecto BOT-Q10 (ya operativo en producción desde 2026-06-22) a esta estructura centralizada.
- Archivos creados: `scripts/q10-consolidacion/` con `q10_to_sheets.py`, `setup_headers.py`, `requirements.txt`, `.gitignore`.
- Workflow exportado a `n8n-workflows/q10-consolidacion.json` con ruta del comando actualizada al nuevo path.
- `docs/procesos/q10-consolidacion.md` completada con toda la información real (flujo, endpoints, decisiones, gotchas).
- `docs/convenciones.md` actualizada con 3 patrones nuevos: SSL corporativo, Q10 login multi-paso, expresiones n8n 2.x.
- `docs/00-vision-global.md` actualizada: Q10 movido a completados, stack corregido (n8n local + cloudflared, no Docker).
- Pendiente para próxima sesión: copiar `credenciales_service_account.json` y `.env` a `scripts/q10-consolidacion/`, reimportar workflow en n8n con la ruta nueva, y escribir headers fila 1 con `setup_headers.py --confirmar`.

---

## 2026-06-23 — [Sistema] Upgrade del sistema de documentación y skills

**Estado:** Completado
**Proceso relacionado:** transversal (afecta todos los procesos)

- Evaluación de la documentación: 6.5/10 escalabilidad, 2/10 para guiar operadores (H2Test inexistente, Power BI ausente).
- Creadas 3 skills invocables: `/compact` (modo keyword, ahorra tokens), `/proceso-nuevo`, `/doc-sync`.
- Creados 2 hooks hookify: protección de `.env`/credenciales (bloqueo) y recordatorio de documentación al cerrar.
- Creado `runbooks/q10-actualizar.md` — guía para operadores no técnicos del proceso Q10.
- Creada memoria persistente del proyecto (4 archivos en `.claude/projects/.../memory/`).
- CLAUDE.md ampliado con mapa de arquitectura real y tabla de skills.
- Pendiente: configurar H2Test en `MAPEO_GRUPOS` de `q10_to_sheets.py` y documentar conexión con Power BI.

---

## 2026-06-24 — [Q10] h2test operativa + evaluación Looker Studio

**Estado:** Completado
**Proceso relacionado:** [[q10-consolidacion]]

- h2test confirmada operativa: datos de Q10 subiendo correctamente a la pestaña `h2test` del Sheet de Fundación ROFÉ.
- Setup h2test completado: Service Account con acceso Editor, headers fila 1 escritos, `/actualizar h2test` funcional.
- Decisión de visualización: se evalúa Looker Studio (datastudio.google.com) como alternativa a Power BI — sin código extra, conector nativo Google Sheets.
- Documentados pasos de conexión y visualizaciones sugeridas en `docs/procesos/q10-consolidacion.md`.
- Pendiente: armar el informe en Looker Studio y regenerar token del bot con BotFather.

---

## 2026-06-24 — [Q10] Decisión de visualización: dashboard web GitHub Pages

**Estado:** Completado (decisión) / En construcción (implementación)
**Proceso relacionado:** [[q10-consolidacion]]

- Descartadas opciones Looker Studio y Power BI como visualizadores.
- Decisión: Python lee h2test → genera `data.json` → commit a GitHub → GitHub Pages muestra el dashboard.
- Ventaja clave: credenciales nunca salen del PC, JSON solo tiene datos agregados (sin datos personales).
- Contenido definido: tabla POR CURSO (8 cursos) + 3 scorecards de anomalías.
- Pendiente próxima sesión: crear `export_stats.py`, repo GitHub Pages, y sitio HTML con Chart.js.
