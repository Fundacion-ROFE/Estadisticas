---
name: doc-reminder
enabled: true
event: stop
pattern: .*
---

Antes de cerrar esta sesión, verificar el checklist de documentación:

- [ ] ¿Se actualizó `docs/procesos/<nombre>.md` si hubo trabajo en un proceso?
- [ ] ¿Se agregó entrada nueva al final de `claude_sessions.md`?
- [ ] ¿Se actualizó `docs/00-vision-global.md` con el estado correcto?

Si alguno está pendiente, invocar `/doc-sync` para el checklist completo antes de terminar.
