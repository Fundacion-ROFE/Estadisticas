# n8n Standards

Usa esta skill cuando crees o modifiques cualquier workflow de n8n para este proyecto.

## Naming
- Workflows: `[area]-[accion]` en minúsculas con guiones. Ej: `zoom-asistencia`.
- Nodos: nombres descriptivos en español, no dejar los nombres default
  ("HTTP Request1", "Set2"). Ej: "Llamar Zoom Reports API", "Filtrar 4 columnas".

## Manejo de errores
- Todo workflow debe tener un camino de error explícito (no dejar que falle en silencio).
- Antes de finalizar un workflow nuevo, revisar `docs/convenciones.md` del proyecto
  para el estándar de notificación de errores vigente.

## Antes de crear un workflow nuevo
1. Revisar `docs/procesos/` en busca de un proceso similar ya resuelto.
2. Revisar `docs/convenciones.md` por credenciales ya configuradas reutilizables.
3. Si el patrón es nuevo y reutilizable, documentarlo en `docs/convenciones.md` al
   terminar, no solo en la nota del proceso individual.

## Al terminar
- Exportar el JSON del workflow a `n8n-workflows/[nombre-workflow].json`.
- Seguir el flujo de documentación definido en el `CLAUDE.md` raíz del proyecto.
