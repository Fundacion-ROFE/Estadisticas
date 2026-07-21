---
name: proceso-nuevo
description: Guía end-to-end para iniciar un proceso nuevo de automatización. Invocar al comienzo de cualquier proceso nuevo con el nombre del proceso como argumento.
user-invocable: true
---

## Contexto cargado del proyecto
- Procesos existentes: !`powershell -Command "Get-ChildItem docs\procesos -Name"`
- Estado global: !`powershell -Command "Get-Content docs\00-vision-global.md"`
- Convenciones vigentes: !`powershell -Command "Get-Content docs\convenciones.md"`

## Proceso nuevo: $ARGUMENTS

### PASO 1 — Pre-trabajo (antes de escribir una línea de código)
- [ ] Revisar `docs/procesos/` — ¿existe algo similar reutilizable?
- [ ] Revisar `docs/convenciones.md` — credenciales ya configuradas, patrones probados
- [ ] Crear nota borrador `docs/procesos/<nombre>.md` usando `docs/plantillas/plantilla-proceso.md`
- [ ] Agregar entrada en `docs/00-vision-global.md` sección "En progreso"

### PASO 2 — Durante el desarrollo
- [ ] Documentar decisiones de diseño en la nota del proceso MIENTRAS se toman (no al final)
- [ ] Documentar gotchas APENAS aparezcan — un gotcha no documentado es deuda técnica inmediata

### PASO 3 — Cierre (sin excepción)
- [ ] Actualizar `docs/procesos/<nombre>.md` con estado final real
- [ ] Si hay patrón reutilizable → agregarlo a `docs/convenciones.md`
- [ ] Si hay workflow n8n → exportar JSON a `n8n-workflows/<nombre>.json`
- [ ] Mover proceso en `docs/00-vision-global.md` a "completado" o "en progreso"
- [ ] Agregar entrada al final de `claude_sessions.md`
- [ ] Si el proceso tiene operadores no técnicos → crear `runbooks/<nombre>.md`

Invocar `/doc-sync` al terminar para verificar el checklist completo.
