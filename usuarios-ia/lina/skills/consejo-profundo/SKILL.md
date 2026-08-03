---
name: consejo-profundo
description: Consejo de 4 personajes con optimista, escéptico y economista corriendo como 3 subagentes reales en paralelo, totalmente aislados entre sí — el juez solo sintetiza. Máxima independencia de criterio, mayor costo. Invocar con /consejo-profundo <idea o decisión>, para decisiones de alto riesgo o difíciles de revertir.
user-invocable: true
---

# Skill: /consejo-profundo

Consejo de 4 personajes — nivel **profundo** (3 subagentes en paralelo). Los tres analistas
(optimista, escéptico, economista) corren en subagentes totalmente independientes, cada uno ciego a
los otros dos. Nadie se contamina con el tono de nadie. Tú actúas **solo** como juez: no redactas
ningún análisis, solo lees los tres informes y sintetizas un veredicto. Es el nivel más caro de la
familia ([[consejo-ligero]] = 0 subagentes, [[consejo-medio]] = 1) — resérvalo para decisiones de
alto riesgo o difíciles de revertir.

Idea a evaluar: **$ARGUMENTS**

> Si `$ARGUMENTS` viene vacío, evalúa la **última idea o decisión pendiente de la conversación**. Si
> tampoco hay contexto claro, pide en UNA línea qué idea evaluar y detente.

---

## Paso 1 — Lanzar los 3 subagentes EN PARALELO (un solo mensaje, 3 tool calls)

Cada `Agent` debe ir con `subagent_type: general-purpose` y **run_in_background: false** (necesitas
los tres resultados antes de poder sintetizar). Los tres prompts deben ser autocontenidos — el
subagente no ve esta conversación, así que cada uno necesita la idea completa y el contexto
relevante repetidos íntegros. No los lances secuencialmente: van en la misma respuesta (misma
llamada con 3 tool calls) para que corran en paralelo.

1. **🟢 Optimista** — "Argumenta el mejor caso posible para esta idea: fortalezas, logros
   alcanzables, precedentes a favor. No es tu trabajo ser objetivo, es encontrar la mejor versión
   del argumento a favor." Reportar en <200 palabras.
2. **🔴 Escéptico** — "Actúa como revisor adversarial. Busca debilidades, errores de razonamiento,
   sesgos no declarados, supuestos sin validar, precedentes de fracaso en ideas similares. Sin
   diplomacia, sin buscar equilibrio." Reportar en <200 palabras.
3. **💰 Economista** — "Analiza costo/beneficio a fondo: tiempo, recursos, mantenimiento, costo de
   oportunidad frente a no hacerlo o hacer otra cosa. Números y supuestos explícitos, no intuición."
   Reportar en <200 palabras.

## Paso 2 — Juez (tú, después de que los 3 regresen)

No agregues un cuarto análisis propio. Lee los tres informes y falla:

- ¿Cuál argumento pesa más y por qué?
- ¿Hay algo en lo que el escéptico y el economista coincidan que el optimista no puede refutar?
- Decisión final, con condiciones si aplica.

## Formato de salida (exacto, sin relleno)

```
## 🟢 Optimista (subagente)
<resumen fiel, 3-5 líneas>

## 🔴 Escéptico (subagente)
<resumen fiel, 3-5 líneas>

## 💰 Economista (subagente)
<resumen fiel, 3-5 líneas>

## ⚖️ Veredicto del juez
Decisión: <Adelante | Adelante con ajustes | No adelante>
Por qué: <1-2 líneas — el argumento que inclinó la balanza>
Condiciones (si aplica): <lista corta>
```

## Qué NO hacer

- No lances los 3 subagentes secuencialmente — pierdes el paralelismo y el aislamiento no mejora,
  solo tarda más.
- No escribas tú mismo ninguno de los 3 análisis "para ahorrar tiempo" — en ese caso usa
  [[consejo-ligero]] o [[consejo-medio]], no este nivel.
- No resumas tan agresivamente que se pierdan los ataques más fuertes del escéptico o los números
  del economista.
- No uses este nivel para decisiones triviales o baratas de rehacer — 3 spawns de agente tienen
  costo real. Para eso está [[consejo-ligero]].
