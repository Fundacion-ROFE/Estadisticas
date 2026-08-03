---
name: consejo-medio
description: Consejo de 4 personajes con el escéptico aislado en un subagente real (1 spawn) para que ataque la idea sin contaminarse con el resto — optimista y economista se hacen en línea, el juez sintetiza. Invocar con /consejo-medio <idea o decisión>.
user-invocable: true
---

# Skill: /consejo-medio

Consejo de 4 personajes — nivel **medio** (1 subagente). El punto más frágil de la versión ligera
([[consejo-ligero]]) es que el escéptico ve la idea después de haber "sentido" el tono optimista del
mismo hilo. Aquí se aísla justo esa pieza: el escéptico corre en un subagente aparte, ciego a
cualquier otro análisis, y ataca la idea en frío. Optimista y economista se redactan en línea (no
son adversariales entre sí, así que el aislamiento aporta poco ahí). El juez sintetiza los tres.

Idea a evaluar: **$ARGUMENTS**

> Si `$ARGUMENTS` viene vacío, evalúa la **última idea o decisión pendiente de la conversación**. Si
> tampoco hay contexto claro, pide en UNA línea qué idea evaluar y detente.

---

## Paso 1 — Lanzar al escéptico (subagente aislado)

Lanza un `Agent` (subagent_type: general-purpose, **run_in_background: false** — necesitas el
resultado antes de seguir) con un prompt autocontenido que incluya:

- La idea completa y el contexto relevante (nada de "basado en lo que hablamos antes" — el
  subagente no tiene memoria de esta conversación).
- El encargo: actuar como revisor **adversarial**. Buscar debilidades, errores de razonamiento,
  sesgos no declarados, supuestos sin validar, precedentes de fracaso en ideas similares. Sin
  diplomacia. No busca equilibrio, busca fallas.
- Límite: reportar en menos de 200 palabras.

## Paso 2 — Optimista y economista (en línea, este mismo turno)

Redáctalos tú directamente, sin esperar ni apoyarte en el informe del escéptico:

- **🟢 Optimista**: fortalezas, logros alcanzables, precedentes a favor.
- **💰 Economista**: costo/beneficio a fondo — tiempo, recursos, mantenimiento, costo de oportunidad
  frente a no hacerlo o hacer otra cosa.

## Paso 3 — Juez

Con los tres informes ya sobre la mesa (optimista, escéptico del subagente, economista), sintetiza
un veredicto. Pondera el peso real de cada argumento — no repartas la decisión en partes iguales.

## Formato de salida (exacto, sin relleno)

```
## 🟢 Optimista
<3-5 líneas>

## 🔴 Escéptico (subagente aislado)
<informe del subagente, resumido si hace falta a 3-5 líneas>

## 💰 Economista
<3-5 líneas>

## ⚖️ Veredicto del juez
Decisión: <Adelante | Adelante con ajustes | No adelante>
Por qué: <1-2 líneas>
Condiciones (si aplica): <lista corta>
```

## Qué NO hacer

- No redactes tú mismo el informe del escéptico "para ahorrar el spawn" — el aislamiento es el
  punto entero de este nivel.
- No dejes que el resumen del informe del subagente pierda sus ataques más fuertes por acortarlo.
- Si la idea es de alto riesgo o muy difícil de revertir, sube a [[consejo-profundo]] (aísla también
  al optimista y al economista).
