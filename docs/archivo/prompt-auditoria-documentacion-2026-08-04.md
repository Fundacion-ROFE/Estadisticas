# Prompt — Auditoría y saneamiento de la documentación (Admin-usable)

> Copiar desde aquí hacia abajo como prompt de arranque de la sesión.

---

## Rol y objetivo

Actúa como auditor de documentación de este repo (Fundación ROFÉ / Jóvenes creaTIvos).
El objetivo NO es solo clasificar archivos: es **comprender la complejidad real de la
documentación** (qué describe cada nota, cómo se conectan entre sí y con el código),
**corregir errores** donde la doc contradiga la realidad, y **alimentar la doc faltante**
(nodos vacíos y procesos sin nota). El resultado final debe ser un contexto limpio y
funcional: que una sesión nueva de Claude pueda orientarse leyendo un conjunto mínimo
de notas, sin ruido.

## Contexto previo (verificado, no lo re-descubras desde cero)

- El vault de Obsidian es todo el repo; `docs/` es además el root de GitHub Pages.
- `CLAUDE.md` define el protocolo de documentación (leer vision-global → convenciones →
  mapa-codigo; actualizar al cerrar; enlaces `[[...]]` bidireccionales).
- Ya existe una convención de archivado en `docs/archivo/README.md` (tabla: archivo /
  qué era / por qué se archivó). **Reutilízala — no inventes otra.**
- Nodos en negro conocidos (archivos de 0 bytes en la raíz): `consejo-profundo.md`,
  `project-emoflow-supabase.md`, `project-panel-datos-supabase.md`,
  `servicio-consultoria-alcance.md`. Puede haber además enlaces `[[...]]` a notas que
  nunca se crearon — verifícalo.
- `claude_sessions.md` pesa ~465 KB (bitácora solo-append). No lo leas entero: últimas
  5 entradas solamente.
- Existe una carpeta `BORRAR/` (candidata obvia, pero confirma antes de tocar).
- Hay notas fuera de `docs/` que aparecen como nodos sueltos en el grafo: raíz del repo,
  `tools/*.md`, `usuarios-ia/`, `runbooks/`, `scripts/*/README.md`.

## Fase 1 — Mapa del grafo (sin leer contenido todavía)

1. Inventaria todos los `.md` del repo (ruta, tamaño, fecha de modificación), excluyendo
   `.git/` y `.obsidian/`.
2. Extrae todos los enlaces `[[wikilink]]` y construye el grafo real:
   - **Nodos negros:** enlaces `[[x]]` cuyo destino no existe, o archivos de 0 bytes.
   - **Nodos huérfanos:** notas que nadie enlaza y que no enlazan a nadie.
   - **Enlaces rotos por renombre:** `[[x]]` que apuntan a una nota archivada o movida.
3. Entrega la tabla del grafo ANTES de seguir, para validar contigo qué ramas leer a fondo.

## Fase 2 — Lectura por niveles (contexto limpio, no lectura total)

- **Nivel 0 (siempre):** `CLAUDE.md`, `docs/00-vision-global.md`, `docs/convenciones.md`,
  últimas 5 entradas de `claude_sessions.md`.
- **Nivel 1 (índices):** `docs/procesos/mapa-codigo.md`, `docs/archivo/README.md`,
  `docs/procesos/gobernanza-contexto-ia.md`.
- **Nivel 2 (por proceso):** cada nota de `docs/procesos/` — leer encabezado, estado,
  "Última actualización" y sección Pendiente; el cuerpo completo solo si hay señales de
  contradicción o desactualización.
- **Nivel 3 (solo bajo sospecha):** `docs/archivo/`, `tools/`, `BORRAR/`, prompts ya
  ejecutados.

## Fase 3 — Clasificación

Clasifica cada nota en exactamente una categoría, con justificación de una línea:

| Categoría | Criterio | Acción propuesta |
|---|---|---|
| **Conservar** | Refleja estado actual, tiene dueño/uso claro | Nada (o corrección menor) |
| **Corregir** | Viva pero contradice el código/Supabase/otra nota | Editar (listar el error concreto) |
| **Unificar** | Solapa >50% con otra nota viva | Fusionar en la nota canónica + redirect |
| **Archivar** | Plan ejecutado, decisión tomada, prompt ya usado | Mover a `docs/archivo/` + fila en su README |
| **Eliminar** | 0 bytes sin propósito, duplicado exacto, `BORRAR/` | Solo con mi aprobación explícita |
| **Crear/Alimentar** | Nodo negro con propósito real, o proceso sin nota | Redactar usando `docs/plantillas/plantilla-proceso.md` |

Para los 4 archivos vacíos: primero determina si son placeholders con intención (¿alguien
los enlaza?, ¿aparecen en vision-global o en sesiones recientes?). Si tienen propósito →
**Crear/Alimentar**; si no → **Eliminar**.

## Fase 4 — Verificación contra la realidad

La doc se corrige contra hechos, no contra otra doc:

- Scripts mencionados en notas vs. los que existen en `scripts/` y en `mapa-codigo.md`.
- Tablas/vistas citadas vs. `schema-supabase-completo.sql` (o Supabase MCP si está conectado).
- Workflows citados vs. JSONs en `n8n-workflows/`.
- Estados en `00-vision-global.md` vs. la sección Estado de cada nota de proceso.

Cada discrepancia va al informe con: nota, afirmación, evidencia real, corrección propuesta.

## Fase 5 — Ejecución y cierre

1. **No borres ni muevas nada sin que yo apruebe la lista completa** (categorías Eliminar
   y Archivar requieren OK explícito; Corregir y Crear puedes ejecutarlas y mostrar el diff).
2. Al archivar: agregar fila a `docs/archivo/README.md` y actualizar los `[[enlaces]]`
   entrantes para que no queden rotos.
3. Al crear notas nuevas: usar la plantilla, enlaces bidireccionales, y registrarlas en
   `00-vision-global.md`.
4. Cierra con el protocolo estándar de `CLAUDE.md`: actualizar `00-vision-global.md` y
   agregar entrada a `claude_sessions.md`.

## Reglas duras

- PII nunca en la doc ni en el informe; `tools/` sigue siendo local/gitignoreado.
- "Vacío nunca sobreescribe": ante la duda, no actuar solo — preguntar.
- No dupliques contenido al unificar: una nota canónica + nota corta de redirección
  (o actualización de enlaces), nunca dos copias vivas.
- `claude_sessions.md` no se edita ni se recorta en esta auditoría; si su tamaño es un
  problema, proponlo como pendiente aparte (ej. particionar por mes con un índice).

## Entregables

1. `docs/archivo/informe-auditoria-doc-<fecha>.md` con: tabla del grafo (negros/huérfanos/
   rotos), tabla de clasificación completa, discrepancias doc-vs-realidad, y acciones
   ejecutadas vs. pendientes de aprobación.
2. **Plan de lectura mínimo** (el "contexto limpio"): lista ordenada de las ≤10 notas que
   una sesión nueva debe leer, propuesto como actualización a la sección "Antes de empezar"
   de `CLAUDE.md`.
3. Las notas nuevas/corregidas ya escritas.

Empieza por la Fase 1 y detente al terminarla para que validemos el mapa juntos.
