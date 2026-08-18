# Plan — Puntaje "Calidad de estudiante" v2 (columna nueva de riesgo)

**Fecha:** 2026-08-18 · **Estado:** SIN LUZ VERDE — documentado solo para no perder el diseño. Bloqueado por el cumplimiento de **P2** ([[prioridades-automatizacion-ia]]). Se ejecutará junto con la implementación del correo `soporte@tocaunavida.org` (trabajo combinado en una sola sesión larga, aún sin fecha).

> Planteamiento corre "a la par de" [[zoom-youtube]]/P4 — son dos iniciativas independientes que
> se quieren agrupar en el tiempo, no una depende técnicamente de la otra.

---

## 0. Por qué existe esta nota

Objetivo de negocio: una columna nueva por estudiante actual que resuma "calidad de estudiante"
en una escala 1-100, para detectar casos de riesgo con más facilidad que revisando señales
sueltas. **Esto ya existe en v1** (ver abajo) — este documento es la especificación de una
**fórmula v2** que Samuel quiere dejar visible antes de decidir si reemplaza a v1.

## 1. Ya existe: v1 en producción (no tocar sin decisión explícita)

- Vista Supabase `v_puntaje_estudiante` + script `scripts/panel-datos/reporte_puntaje.py`.
- Fórmula v1: **Emoflow (ingresos) 60% + avance Q10 40% + asistencia Zoom 0%**, todo sobre
  **percentiles** dentro de la cohorte (no valores crudos — el avance crudo no discrimina).
- Regla de negocio v1: **Emoflow es obligatorio** — sin registro de ingresos, el estudiante
  queda excluido del ranking (no "cuenta").
- Asistencia arrancó en peso 0 por señal inmadura (un solo curso, ~1.4 sesiones/persona);
  pensada para subir de peso cuando madure — **v2 es, en la práctica, esa maduración llevada
  al extremo (50%)**.
- Consumidores: `panel_riesgo` / ficha 360 del [[panel-control-jc-mr]] lo mencionan como mejora
  futura de baja prioridad (`v_puntaje_estudiante` no está aún en `v_persona_360`).

## 2. Fórmula v2 (propuesta, NO implementada)

Escala final: **1 a 100**.

| Componente | Peso | Regla de conteo |
|---|---|---|
| **Asistencia (Zoom)** | 50% | Una sesión solo cuenta como "asistida" si el estudiante superó **70 min** de clase (umbral ≈ 50% de una clase de referencia de ~140 min). El score de este componente es el % de sesiones que cumplen el umbral sobre el total. |
| **Avance Q10** | 25% | Valor de avance tal como lo reporta Q10 (a definir si crudo o percentil — v1 usa percentil por la razón documentada arriba; recomendado mantener esa decisión en v2 para no repetir el problema de "faltar dato premia"). |
| **Presencial + recurrencia Emoflow** | 25% | Combina (a) asistencia a sesiones presenciales y (b) presencia **recurrente** en Emoflow — no un solo ingreso, sino continuidad. Falta definir la mezcla exacta entre las dos sub-señales dentro de este 25%. |

### Multiplicadores (encima del puntaje base 1-100)

- **Estrella del mes** → multiplicador fijo **×1.05**. Categoría "mínima" (afecta poco, es un
  incentivo simbólico).
- **Proyecto final** → multiplica o **divide** el puntaje según si el estudiante lo presentó o
  no. Los criterios de evaluación del proyecto (qué cuenta como "hecho", umbral de calidad,
  etc.) **aún no están definidos** y son importantes porque determinan si el multiplicador es
  favorable o penaliza fuerte. **No se activa todavía** — faltaba ~1 mes para que el proyecto
  final fuera relevante en la cohorte actual (proyección desde 2026-08-18).

```
puntaje_base = 0.50·score_asistencia + 0.25·score_avance_q10 + 0.25·score_presencial_emoflow
puntaje_final = puntaje_base × mult_estrella_mes × mult_proyecto_final
                 (mult_estrella_mes = 1.05 si aplica, si no 1.0)
                 (mult_proyecto_final: fórmula y umbral SIN DEFINIR — pendiente)
```

## 3. Decisiones abiertas (para cuando se retome)

1. **¿v2 reemplaza a v1 o convive?** Si conviven, definir cuál alimenta qué vista/consumidor
   (panel de riesgo, ficha 360, Excel de ranking).
2. Avance Q10: ¿percentil (como v1) o valor crudo? Recomendado percentil, misma razón que v1
   (avance crudo casi no discrimina y faltar el dato premiaría).
3. Mezcla interna del 25% "presencial + recurrencia Emoflow": ¿cuánto pesa cada sub-señal?
4. Criterios del proyecto final (multiplicador/divisor) — depende de coordinación/Lina, no es
   decisión técnica.
5. ¿El umbral de 70 min aplica igual a todos los cursos/duraciones de clase, o varía según la
   duración real de cada sesión (hoy asumido ~140 min de referencia)?
6. Fuente de "recurrencia Emoflow": ¿cuántos ingresos en cuánta ventana de tiempo cuentan como
   "recurrente"? (hoy `emoflow_ingresos`/`historial_emoflow` ya existen en Supabase, ver
   [[supabase-estructura]]).

## 4. Gate de ejecución

- **No implementar sin luz verde explícita de Samuel** (a la fecha de esta nota, no dada).
- Condición para desbloquear: cumplimiento de **P2** — ver [[prioridades-automatizacion-ia]].
- Cuando se desbloquee, agrupar esta implementación con el trabajo de `soporte@tocaunavida.org`
  (una sola sesión larga) en vez de hacerlos por separado.

## Ver también

- [[panel-datos-etl]] — dónde vive `v_puntaje_estudiante` y las tablas Emoflow/asistencia.
- [[panel-control-jc-mr]] — consumidor potencial (ficha 360 aún no incluye puntaje).
- [[prioridades-automatizacion-ia]] — definición de P2/P4.
