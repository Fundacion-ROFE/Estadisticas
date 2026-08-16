# Guion de demo — Hito P0 ante la CEO (2026-08-11)

**Uso:** tenerlo en un 2º screen. Son preguntas para hacerle a Claude en vivo; las respuestas ya
están verificadas contra la DB (set de Seguimiento N=751, fecha 2026-08-11).
**Regla de oro de la demo:** para 2026, todo sale del mismo conjunto de **751 activos de
Seguimiento** → cada desglose suma 751, sin descuadres.

---

## Apertura (30 seg)
> "La base de datos de Jóvenes creaTIvos y Mujeres ROFÉ ya responde cualquier pregunta en lenguaje
> natural. Les muestro en vivo. Hoy entrega JC y MR consultables; Zoom y asistencia en tiempo real
> vienen en la siguiente fase."

## Preguntas para hacer en vivo (en orden)

1. **"¿Cuántos jóvenes activos hay en JC 2026?"**
   → 751 activos, de 832 que ingresaron (81 han salido). *El número operativo real es Seguimiento.*

2. **"¿Cómo está el balance de género?"**
   → 374 mujeres y 372 hombres (+5 otras/sin dato). Suman 751. *Casi paritario — dato fuerte para patrocinadores.*

3. **"¿Cuál es el curso más difícil?"**
   → JavaScript, 43,6% de aprobación, muy por debajo del resto (90%+). *Cuello de botella claro.*

4. **"¿En qué ciudades y países estamos?"**
   → 6 países. Top: Barranquilla 131, Bogotá 128, Cartagena 97, Medellín 93, Cali 90, Guayaquil 79.

5. **"¿Cuántas mujeres de MR tienen emprendimiento?"**
   → 119 de 179 activas (66%). En JC es al revés (92 de 751). *Dos programas, dos perfiles.*

6. **"¿Cuántos microcréditos se han desembolsado en MR?"**
   → 64. *Impacto financiero real.*

7. **"¿Cuánta gente usa Emoflow?"**
   → 826 registros, 759 (91,8%) cruzan con matrícula.

8. **"¿Cuánta gente pasó por el embudo, no solo matriculadas?"**
   → 7.866 postulantes (2.556 JC + 5.310 MR).

---

## Si preguntan lo difícil (respuestas preparadas)

- **"¿Por qué 751 y no 754?"**
  → 751 es el roster que el equipo mantiene a mano en Seguimiento (el punto de verdad del presente).
  Q10 da 754 porque va 3 atrás: son retiros que el equipo ya registró y Q10 aún no. 832 = 751 + 81,
  todo cuadra. *Es la definición correcta de "activo", no un error.*

- **"¿Y los años anteriores / los consolidados por año?"**
  → La DB tiene JC 2023–2026 y MR 2025–2026. Los totales históricos los estamos firmando
  cohorte-por-cohorte contra el consolidado oficial esta semana; el motor ya reconstruye 2024 exacto
  (433 culminantes = 433 oficial). No es dato perdido, es afinar de dónde cuenta el panel.

- **"¿Es confiable?"**
  → Suite de integridad automatizada, cuadres triangulados, PII protegida (solo agregados públicos).

---

## Enlaces
- Reporte visual (compartible): https://claude.ai/code/artifact/7727bd31-d37e-4297-b854-c1a0b00347d2
- Plan de cierre: `docs/procesos/plan-coherencia-cohortes-2026-08-11.md`

## Panel público (Vercel; era Netlify+Vercel al momento de esta demo, Netlify de baja desde 2026-08-11) — YA COHERENTE (2026-08-11)
- Se aplicó a producción: el card de cohorte ahora muestra **JC 2026 = 832 / 751 / 81** y el
  histórico 2019–2025 desde el consolidado oficial (2024 = 608/433/175, etc.). Suite 53/53 PASS.
- **Sí se puede mostrar** el card por año. Único detalle: el **drill-down geográfico histórico**
  (mapa por ciudad de años pasados) todavía cuenta por matrícula — si entran ahí, aclarar que la
  geografía histórica se está afinando. El card y 2026 están 100% coherentes.
