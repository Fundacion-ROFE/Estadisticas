# Proyecto: Automatizaciones de Empresa (n8n + Workspace + Zoom)

## Arquitectura del proyecto

```
automatizaciones-empresa/
├── CLAUDE.md                        # Este archivo — instrucciones para Claude
├── claude_sessions.md               # Bitácora histórica (solo append, nunca borrar)
├── docs/
│   ├── 00-vision-global.md          # Mapa de estado de todos los procesos
│   ├── convenciones.md              # Estándares técnicos reutilizables (SSL, n8n, Sheets)
│   ├── plantillas/plantilla-proceso.md
│   └── procesos/                    # Una nota por proceso (editable, no histórica)
│       ├── q10-consolidacion.md     # COMPLETADO — bot Telegram → H1Test
│       └── zoom-asistencia.md       # EN PROGRESO — bloqueado
├── runbooks/                        # Guías para operadores no técnicos
│   └── q10-actualizar.md
├── scripts/
│   └── q10-consolidacion/
│       ├── q10_to_sheets.py         # Script principal (acepta --grupo)
│       ├── setup_headers.py         # Uso único: escribe fila 1
│       └── organizador/             # App standalone .exe para el equipo
├── n8n-workflows/                   # JSONs exportados de n8n (ID prod: Rblg81qifVshsRae)
├── skills/n8n-standards/SKILL.md    # Estándares para workflows de n8n
└── .claude/
    ├── skills/compact/              # /compact — modo respuesta mínima (ahorra tokens)
    ├── skills/proceso-nuevo/        # /proceso-nuevo <nombre> — guía new process
    ├── skills/doc-sync/             # /doc-sync — checklist de cierre de sesión
    ├── hookify.protect-creds.local.md  # Bloquea edición de .env y credenciales
    └── hookify.doc-reminder.local.md   # Recordatorio de documentación al cerrar
```

## Skills disponibles

| Skill | Invocar | Cuándo |
|---|---|---|
| compact | `/compact` | Para respuestas cortas y ahorrar tokens — activa modo keyword |
| proceso-nuevo | `/proceso-nuevo <nombre>` | Al iniciar cualquier proceso nuevo |
| doc-sync | `/doc-sync` | Al cerrar cualquier sesión de trabajo |
| n8n-standards | automático | Al trabajar con workflows de n8n |

## Qué es este proyecto
Automatización progresiva de procesos manuales de la empresa usando n8n (self-hosted,
local en PC de Samuel) como orquestador, integrado con Google Workspace (Calendar,
Sheets, Drive) y APIs externas (Zoom, Meet, Q10). Un proceso a la vez; al final se
unifican evitando redundancia.

## Antes de empezar CUALQUIER tarea nueva

1. Lee `docs/00-vision-global.md` para entender qué existe y qué está pendiente.
2. Lee `docs/convenciones.md` para no reinventar estándares ya definidos.
3. Revisa `docs/procesos/` — si el proceso nuevo se parece a uno existente, reutiliza
   nodos, lógica de errores, o estructura ya probada en lugar de crear desde cero.
4. Revisa `claude_sessions.md` (últimas 3-5 entradas) para recordar el contexto reciente.

## Durante la tarea

- Si tomas una decisión de diseño importante (ej: "usamos Server-to-Server OAuth en vez
  de OAuth clásico porque..."), anótala inmediatamente en la nota del proceso
  correspondiente en `docs/procesos/`. No esperes al final.
- Si encuentras un "gotcha" (algo que no funcionó como se esperaba, una limitación de
  la API, un dato sucio, etc.), documéntalo en la sección "Gotchas" de la nota del
  proceso. Esto evita que el problema se repita en la próxima automatización similar.

## Al terminar la tarea (SIEMPRE, sin excepción)

1. Actualiza o crea la nota correspondiente en `docs/procesos/<nombre-proceso>.md`
   usando la plantilla en `docs/plantillas/plantilla-proceso.md`. Si el proceso ya
   tenía nota, ACTUALIZA, no dupliques.
2. Si el proceso terminado revela un patrón reutilizable (ej: "todas las automatizaciones
   con Sheets necesitan este mismo manejo de errores"), agrégalo a `docs/convenciones.md`.
3. Si el flujo de n8n cambió, exporta el JSON actualizado a `n8n-workflows/`.
4. Agrega una entrada nueva al FINAL de `claude_sessions.md` con el formato definido
   en ese archivo. Sé conciso: 5-10 líneas, no un ensayo.
5. Si el proceso conecta o afecta otro proceso ya documentado, agrega un enlace
   `[[nombre-del-otro-proceso]]` en ambas notas para mantener las conexiones visibles
   en Obsidian.
6. Actualiza `docs/00-vision-global.md` moviendo el proceso de "pendiente" a
   "completado" o "en progreso", según corresponda.

## Estilo de documentación

- Español, directo, sin relleno. Listas y tablas antes que párrafos largos.
- Cada nota de proceso debe poder leerse en menos de 2 minutos y dar suficiente
  contexto para retomar el trabajo sin tener que leer el código del workflow.
- Nunca borres información histórica de `claude_sessions.md` — solo se agrega al final.
- Las notas en `docs/procesos/` SÍ se reescriben/actualizan (no son históricas, son
  el estado actual).

## Convenciones técnicas rápidas
Ver `docs/convenciones.md` para el detalle completo. Resumen:
- Nombres de workflows en n8n: `[area]-[accion]` en minúsculas con guiones
  (ej: `zoom-asistencia`, `q10-consolidacion`).
- Toda automatización debe tener manejo explícito de error (nodo de notificación o log
  ante fallo), no solo el camino feliz.
- Credenciales reutilizables se documentan en `docs/convenciones.md`, nunca se duplican
  manualmente en cada workflow si ya existe una conexión configurada.
