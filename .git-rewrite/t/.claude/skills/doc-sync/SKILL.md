---
name: doc-sync
description: Checklist de cierre de sesión — verifica que toda la documentación esté sincronizada con el trabajo hecho. Invocar con /doc-sync antes de cerrar cualquier sesión de trabajo.
user-invocable: true
---

## Estado actual del proyecto
- Última sesión registrada: !`powershell -Command "Get-Content claude_sessions.md -Tail 40"`
- Procesos documentados: !`powershell -Command "Get-ChildItem docs\procesos -Name"`
- Estado global: !`powershell -Command "Get-Content docs\00-vision-global.md"`
- Runbooks existentes: !`powershell -Command "if (Test-Path runbooks) { Get-ChildItem runbooks -Name } else { 'carpeta runbooks no existe aún' }"`

## Checklist de cierre

Para cada punto responder ✓ ok o ✗ pendiente → [acción concreta]:

1. ¿Existe nota en `docs/procesos/` para CADA proceso trabajado hoy?
2. ¿La(s) nota(s) reflejan el estado ACTUAL (no el estado anterior a esta sesión)?
3. ¿Se detectó algún patrón reutilizable? Si sí → ¿ya está en `docs/convenciones.md`?
4. ¿Cambió algún workflow de n8n? Si sí → ¿JSON exportado a `n8n-workflows/`?
5. ¿`docs/00-vision-global.md` tiene el estado correcto para los procesos tocados?
6. ¿Falta agregar entrada a `claude_sessions.md`? (solo se agrega, nunca se borra)
7. ¿Algún proceso tiene operadores no técnicos que lo usan? Si sí → ¿existe `runbooks/<nombre>.md`?

Para cada ✗: ejecutar la acción antes de dar la sesión por cerrada.
Si todos son ✓: la sesión puede cerrarse limpiamente.
