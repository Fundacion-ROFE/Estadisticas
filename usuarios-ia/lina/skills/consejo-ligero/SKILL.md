---
name: consejo-ligero
description: Simula un consejo de 4 personajes (optimista, escéptico, economista, juez) en un solo turno, sin lanzar subagentes — barato y rápido para decisiones de bajo riesgo. Invocar con /consejo-ligero <idea o decisión>.
user-invocable: true
---

# Skill: /consejo-ligero

Consejo de 4 personajes — nivel **ligero** (0 subagentes). Evalúa una idea o decisión simulando
cuatro voces con sesgos opuestos en el mismo turno, sin aislamiento real entre ellas. Es el nivel
más barato y rápido de la familia — ver también [[consejo-medio]] (1 subagente, aísla al escéptico)
y [[consejo-profundo]] (3 subagentes, aislamiento total) para decisiones de mayor riesgo.

Idea a evaluar: **$ARGUMENTS**

> Si `$ARGUMENTS` viene vacío, evalúa la **última idea o decisión pendiente de la conversación**. Si
> tampoco hay contexto claro, pide en UNA línea qué idea evaluar y detente.

---

## Los 4 personajes

1. **🟢 Optimista** — busca fortalezas, logros alcanzados o alcanzables, precedentes a favor. No
   minimiza riesgos, pero su trabajo es argumentar el mejor caso posible.
2. **🔴 Escéptico** — busca debilidades, errores de razonamiento, sesgos no declarados, supuestos
   sin validar. Ataca cada punto débil de la idea sin diplomacia. Su trabajo NO es ser justo, es
   encontrar por qué esto podría fallar.
3. **💰 Economista** — analiza costo/beneficio a fondo: tiempo, recursos, mantenimiento, costo de
   oportunidad frente a no hacerlo o hacer otra cosa. Piensa en números, no en intuición.
4. **⚖️ Juez** — no es un personaje más, es la síntesis. Lee los tres informes anteriores y decide:
   ¿se sigue, se sigue con ajustes, o no se sigue? Pondera el peso real de cada argumento, no reparte
   el veredicto en partes iguales.

## Cómo ejecutar (importante: orden y aislamiento simulado)

Aunque todo ocurre en el mismo turno, redacta los tres primeros informes **en orden y sin releer
los anteriores al escribir el siguiente** — no dejes que el argumento del optimista suavice al
escéptico, ni que el escéptico contamine al economista. Escribe cada uno como si fuera la primera
vez que ve la idea. Solo el juez tiene permiso de leer los tres.

## Formato de salida (exacto, sin relleno)

```
## 🟢 Optimista
<3-5 líneas>

## 🔴 Escéptico
<3-5 líneas>

## 💰 Economista
<3-5 líneas: costo/beneficio, alternativa de no hacerlo>

## ⚖️ Veredicto del juez
Decisión: <Adelante | Adelante con ajustes | No adelante>
Por qué: <1-2 líneas — el argumento que inclinó la balanza>
Condiciones (si aplica): <lista corta, solo si "con ajustes">
```

## Qué NO hacer

- No conviertas al escéptico en un optimista moderado — su valor está en ser genuinamente
  adversarial.
- No repartas el veredicto salomónicamente ("un poco de cada uno") si la evidencia no lo justifica.
- No uses este nivel para decisiones de alto riesgo o difíciles de revertir — para eso está
  [[consejo-medio]] o [[consejo-profundo]], que aíslan de verdad a los personajes en subagentes.
