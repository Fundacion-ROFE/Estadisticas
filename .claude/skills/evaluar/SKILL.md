---
name: evaluar
description: Lee una tarea, estima su complejidad y recomienda qué modelo usar (Haiku/Sonnet/Opus) + el comando para cambiarlo + un prompt de inicio afinado. NO ejecuta la tarea, solo aconseja. Invocar con /evaluar <descripción de la tarea>.
user-invocable: true
---

# Skill: /evaluar

Asesor de modelo. Toma una tarea en lenguaje natural, la clasifica por complejidad y recomienda el
modelo adecuado **antes** de empezar, para que el modelo más caro no gaste en lo trivial y lo
trivial no se quede corto en lo difícil. **No ejecuta la tarea** — solo evalúa y aconseja.

Tarea a evaluar: **$ARGUMENTS**

> Si `$ARGUMENTS` viene vacío, evalúa la **última tarea pendiente de la conversación**. Si tampoco
> hay contexto claro, pide en UNA línea la descripción de la tarea y detente.

---

## Criterio de routing (mapa fijo — pedido de Samuel)

| Modelo | ID | Para qué | Señales típicas |
|---|---|---|---|
| **Haiku** | `claude-haiku-4-5` | **Labores mecánicas** | Renombrar/mover, extraer o reformatear datos, ediciones repetitivas, búsquedas simples, boilerplate, cambios de 1–2 líneas, camino único y bajo riesgo |
| **Sonnet** | `claude-sonnet-5` | **Correcciones breves** | Bug acotado con causa clara, refactor pequeño, edición multi-archivo simple, revisión corta, tarea de complejidad media con contexto suficiente |
| **Opus** | `claude-opus-4-8` | **Análisis y plan de acción** | Arquitectura, diseño de proceso nuevo, debugging ambiguo/difícil, decisiones con trade-offs, tarea multi-paso con incertidumbre, seguridad, algo que si sale mal cuesta rehacer |

**Escala de complejidad → modelo:**

- **1–2 (mecánica / determinista)** → Haiku
- **3 (media, contexto claro)** → Sonnet
- **4–5 (razonamiento, ambigüedad o riesgo alto)** → Opus

**Regla de desempate — el costo del error manda:** si dudas entre dos niveles, mira qué pasa si el
modelo se queda corto. Una tarea barata mal hecha se rehace gratis (baja un nivel sin miedo). Una
tarea de alto riesgo o difícil de rehacer justifica subir a Opus aunque parezca "media". No subas
por si acaso en lo mecánico; no ahorres en lo que cuesta rehacer.

---

## Cómo evaluar (pasos)

1. **Lee la tarea** y clasifícala mentalmente con estas 4 dimensiones:
   - **Ambigüedad:** ¿el objetivo y los pasos están claros, o hay que descubrirlos?
   - **Razonamiento:** ¿es aplicar un patrón conocido, o requiere diseñar/decidir?
   - **Alcance:** ¿un punto único, o varios archivos/sistemas encadenados?
   - **Riesgo:** ¿reversible y barato, o difícil/costoso de rehacer (datos, seguridad, prod)?
2. **Asigna complejidad 1–5** combinando las 4 dimensiones (domina la más alta cuando hay riesgo).
3. **Mapea a modelo** con la tabla de arriba.
4. **Redacta un "prompt de inicio"** afinado: reescribe la petición de Samuel en un prompt claro,
   con el objetivo, el contexto relevante del repo si aplica, y qué entregar. Este es el prompt que
   Samuel pegaría al arrancar la tarea (ya sea en esta sesión tras cambiar de modelo, o en una nueva).

## Formato de salida (exacto — tabla compacta, sin relleno)

```
Complejidad: N/5  ·  Modelo recomendado: <Haiku|Sonnet|Opus>
Por qué: <1 línea, la dimensión que decidió>
Cambiar modelo:  /model <haiku|sonnet|opus>
```

Y debajo, en un bloque aparte:

```
Prompt de inicio sugerido:
<el prompt reescrito y afinado, listo para pegar>
```

- Si la tarea es **mixta** (ej. "analiza y luego aplica 20 ediciones repetitivas"), recomiéndalo
  **por fases**: Opus/Sonnet para el análisis, y baja a Haiku para la parte mecánica — dilo en una
  línea (ej. "Fase 1 análisis → Opus; Fase 2 aplicar cambios → Haiku").
- No des un párrafo de justificación. Una línea de "por qué" basta.

---

## Qué NO hacer

- **No ejecutes la tarea.** Este skill solo aconseja; parar después de dar la recomendación.
- **No cambies el modelo tú** — Claude Code no cambia de modelo por su cuenta; entrega el comando
  `/model …` para que Samuel lo corra (o siga en el modelo actual si ya es el adecuado).
- **No infles la recomendación** "por si acaso": el objetivo explícito es que Opus no haga lo
  mecánico. Ante la duda en tareas baratas/reversibles, baja de nivel.
- **No inventes contexto** en el prompt de inicio: si algo falta para arrancar bien, márcalo como
  `[completar: …]` en el prompt en vez de rellenarlo.

## Nota (opcional, si más adelante se quiere abaratar aún más)

Este skill corre en el modelo activo de la sesión. Si Samuel quiere que la *evaluación* misma
siempre la haga Haiku (aunque la sesión esté en Opus), la versión con script llamaría a
`claude-haiku-4-5` vía la API como clasificador. No se implementó por ahora: una sola clasificación
es barata y no justifica montar API key + manejo de errores. Ver [[claude-api]] si se retoma.
