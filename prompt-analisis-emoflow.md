# Prompt para Claude Code (Fable) — Auditoría y análisis Emoflow

Copia desde aquí hacia abajo:

---

Actúa como analista de datos senior. Misión en dos partes sobre la base Supabase `panel-datos-rofe`:

**A.** Auditar a fondo la estructura y calidad de datos para diagnosticar si permiten análisis estadístico riguroso del comportamiento de Emoflow por ciudad.
**B.** Ejecutar el análisis que la auditoría avale: identificar los casos de mayor uso y determinar si el uso de Emoflow está asociado con los resultados académicos (aprobación / retiro).

Al cierre, la documentación debe dejar la base lista para funcionar como **única fuente de verdad** de la organización.

## Fase 0 — Contexto (obligatoria antes de tocar nada)

1. Lee `docs/00-vision-global.md`, `docs/convenciones.md`, `docs/procesos/mapa-codigo.md` y las últimas 5 entradas de `claude_sessions.md`.
2. Revisa la nota del proceso panel-datos-etl y los scripts `scripts/panel-datos/sync_emoflow*.py` y `extract_emoflow_ingresos_diario.py` para entender cómo se pobló cada tabla.
3. Variables de resultado asumidas: aprobación (`aprobacion_cursos`, cohorte 832) y retiro. Si encuentras una variable de resultado mejor, decláralo antes de la Fase 4.

## Fase 1 — Inventario de esquema

Para TODAS las tablas, con énfasis en `emoflow_ingresos`, `emoflow_ingresos_diario`, `historial_emoflow`, `historial_emoflow_ciudad`, `emoflow_participacion_semanal`, `participants`, `postulantes_jc`, `postulantes_mr`, `cohorte_ingresos`, `aprobacion_cursos`:

- Columnas, tipos, PK/FK, constraints, índices, RLS.
- Conteo de filas, rango de fechas cubierto, granularidad (individuo / ciudad / día / semana).
- Llaves de cruce entre tablas (¿email normalizado? ¿id?) y su **tasa real de match** medida con queries, no asumida.

Entregable: diccionario de datos completo.

## Fase 2 — Auditoría de calidad por fuente

Para cada tabla emoflow y cada fuente (API Emoflow, Sheets, Q10, Mongo):

- Nulls, duplicados, huérfanos, formatos inconsistentes (variantes de nombre de ciudad, emails con mayúsculas/espacios).
- Coherencia cruzada: totales de `emoflow_ingresos_diario` agregados vs `emoflow_ingresos` vs `historial_emoflow_ciudad` vs `emoflow_participacion_semanal` — cuantifica cada discrepancia.
- Gaps temporales y solapamiento entre el pipeline deprecado (`sync_emoflow.py`, corte 2026-07-20) y el actual (`sync_emoflow_api.py`): ¿doble conteo o huecos alrededor del corte?
- Valida contra una segunda vía cuando exista (`test_cuadre_dashboard.py`, data.json públicos del dashboard).

Regla: cada afirmación del diagnóstico debe estar respaldada por una query ejecutada; incluye las queries en el reporte.

## Fase 3 — Suficiencia estadística

Responde explícitamente sí/no con evidencia:

1. ¿Se puede comparar comportamiento entre ciudades? (n por ciudad, cobertura temporal, granularidad, normalización por tamaño de cohorte)
2. ¿Se pueden identificar casos individuales de mayor uso, o solo existe agregado por ciudad?
3. ¿Se puede cruzar uso con resultados académicos? (tasa de match de llaves, sesgo de los no-matcheados)

Para cada "no": especifica exactamente qué columna/tabla/dato falta y cómo obtenerlo.

## Fase 4 — Análisis estadístico (solo lo que la Fase 3 avale)

- Comportamiento por ciudad: tendencias, estacionalidad, comparaciones normalizadas.
- Ranking de mayor uso (individuos si hay datos; si no, ciudades), con criterio de corte definido.
- Asociación uso ↔ resultado: correlación, chi-cuadrado y regresión logística controlando por sociodemográficos disponibles (género, edad, ciudad, estrato). Reporta tamaños de efecto e IC 95%, no solo p-valores.
- Deja explícito que asociación ≠ causalidad y qué diseño haría falta para afirmar "factor determinante".

## Fase 5 — Verificación

Re-ejecuta los conteos clave por una vía independiente, revisa outliers manualmente y marca cualquier hallazgo no reproducible antes de reportarlo.

## Fase 6 — Entregables y cierre

1. **`docs/procesos/supabase-estructura.md`** (nueva): diccionario de datos — tabla, columna, tipo, script de origen, frecuencia de actualización, llaves, estado (🟢 confiable / 🟡 con observaciones / 🔴 no usar). Enlázala desde mapa-codigo y la nota del proceso.
2. **Diagnóstico de funcionalidad** en la nota del proceso: qué sirve, qué está roto o redundante, riesgos.
3. **Plan priorizado "única fuente de verdad"**: FK/constraints faltantes, deduplicación, normalización de ciudades y emails, tablas a deprecar, monitoreo.
4. **Reporte de análisis**: hallazgos por ciudad + conclusión sobre el uso como factor. Agregados publicables en `docs/`; cualquier dato individual solo en `tools/`.
5. Cierre estándar de CLAUDE.md: mapa-codigo si creaste scripts, entrada en `claude_sessions.md`, actualizar `00-vision-global.md`.

## Restricciones

- Supabase **SOLO LECTURA**: ninguna migración, DDL ni escritura sin mi aprobación explícita.
- PII nunca a GitHub: scripts o salidas con datos individuales van en `tools/` (gitignoreado).
- Scripts nuevos: `truststore.inject_into_ssl()` al inicio; reutiliza los patrones de conexión de `scripts/panel-datos/`.
- No extrapoles: si un dato no está, dilo. Prefiere "no se puede concluir con estos datos" a una conclusión débil.
