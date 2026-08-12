# Prompt de arranque — Loop de coherencia fuentes ↔ Supabase (Sonnet)

> Creado 2026-07-29 por pedido de Lina. Objetivo: que la información de cada Sheet/fuente
> sea coherente con Supabase de manera **individual** (fuente por fuente) y **conjunta**
> (cruces entre fuentes), conservando siempre el dato más actualizado, coherente y realista.
> Modelo recomendado: Sonnet. Copiar todo el bloque de abajo como primer mensaje de la sesión.

---

```
Vas a ejecutar un LOOP DE COHERENCIA DE DATOS para panel-datos-rofe (Fundación ROFÉ /
Jóvenes creaTIvos). Tu trabajo es verificar, fuente por fuente y luego en conjunto, que
Supabase refleje la información más actualizada, coherente y realista de las fuentes.

## Lectura obligatoria ANTES de tocar nada (en este orden)
1. CLAUDE.md — reglas duras del proyecto (SSL truststore, PII, convenciones).
2. docs/procesos/plan-maestro-2026-07-29.md — estado real, P0/P1/P2, decisiones cerradas.
3. docs/procesos/diccionario-metricas.md — definiciones canónicas (activo, retirado,
   % aprobación). NUNCA inventes una métrica distinta a las de ahí.
4. docs/procesos/supabase-estructura.md — esquema, estados 🟢🟡🔴 por tabla, RLS.
5. docs/procesos/mapa-codigo.md — scripts existentes. NO reescribas helpers que ya
   existen (importa Supa/get_todo/cargar_env_local de sync_postulantes_mr.py o
   test_integridad_supabase.py — el paginador reescrito ya causó 2 loops infinitos).
6. Últimas 5 entradas de claude_sessions.md — contexto reciente.

## Alcance
- Fuentes EN alcance: Q10 (h2test/consolidado), BD Seguimiento Monitorias JC,
  BD-Mujeres ROFÉ (todas las pestañas ya ETL'd: General, postulantes, Icredit|Microcredito,
  Inactivas), Emoflow (API), Sheets de retiros (Retirados JC / Inactivas MR),
  docs/aprobacion/data.json. Cohortes 2025-2026 según exista pipeline.
- FUERA de alcance: asistencia Zoom (beta, prioridad baja) y el track histórico
  2019-2026 de plan-consolidacion-datos-2026-07-27.md (tiene su propio plan con puertas
  — no lo toques salvo pedido explícito).

## Estructura del loop — una vuelta por fuente, luego una vuelta conjunta

Por cada fuente, en este orden (de más estable a más volátil):
  A. Q10 → participants/courses/enrollments/participant_metrics
  B. BD Seguimiento Monitorias JC → participants (sociodemográficos JC, empresa
     patrocinadora, en_seguimiento_jc)
  C. BD-Mujeres ROFÉ → participants MR, postulantes_mr, mr_microcreditos
  D. Sheets de retiros → retiros, cohorte_ingresos
  E. Emoflow API → emoflow_ingresos(_diario), historial_emoflow(_ciudad)
  F. aprobacion/data.json → cohorte_ingresos, aprobacion_cursos

Pasos de cada vuelta:
1. FRESCURA: consulta v_frescura para el proceso; si vencido=true, primero determina si
   el sync correspondiente debe correr (propónlo, no lo corras sin aprobación).
2. CONTEO: filas/llaves en la fuente (usando la función real de extracción del script
   sync_* correspondiente, no metadata de Sheets — row_count de grid ya dio un falso
   hallazgo el 28-jul) vs filas en Supabase. Reporta el delta exacto.
3. CONTENIDO: muestreo de campos clave (cédula, estado, fechas, campos sociodemográficos)
   fuente vs Supabase. Detecta filas nuevas no cargadas, filas huérfanas en Supabase, y
   valores que difieren.
4. CLASIFICA cada discrepancia:
   - YA EXPLICADA (ver lista de abajo) → no la re-reportes, solo confirma que sigue igual.
   - RESOLUBLE CON SYNC EXISTENTE → propón el comando exacto (con --dry-run si existe).
   - CONFLICTO ENTRE FUENTES → va a la cola de arbitraje (ver protocolo).
   - BUG/ESTRUCTURAL → descríbelo con la query exacta que lo demuestra; propón fix, no lo apliques.
5. CIERRA la vuelta con un mini-informe: fuente, frescura, deltas, discrepancias por clase.

Vuelta CONJUNTA (al final): cruces entre dominios ya definidos —
  - cohorte_ingresos vs enrollments vs Seguimiento (los 3 conteos del diccionario).
  - retiros vs cohorte_ingresos.retirados (personas vs eventos; gap de 7 en JC es P1#2).
  - postulantes_mr/jc vs participants (universo vs matriculados).
  - emoflow vs participants activos (742 canónico).
  - test de integridad completo: python scripts/panel-datos/test_integridad_supabase.py

## Protocolo de arbitraje con Lina (fuentes que difieren)
NO te detengas en cada discrepancia. Acumúlalas durante la vuelta y AL FINAL de cada
vuelta presenta UNA tabla:
  | # | Dato | Fuente A (valor) | Fuente B (valor) | Supabase (valor) | Magnitud | Hipótesis |
Lina decide cuál fuente manda en cada fila. Registra cada decisión en una sección
"Jerarquía de fiabilidad acordada" al final de tu informe — las vueltas siguientes
reutilizan esas decisiones sin volver a preguntar lo ya decidido.
Diferencias mínimas esperables (tildes, espacios, formato de celular/cédula ya
documentado en P4 del plan maestro) se reportan agrupadas, no fila por fila.

## Régimen de escritura — TODO cambio requiere aprobación explícita
- Estás en modo "corregir todo con aprobación": puedes proponer re-correr syncs,
  aplicar fixes e incluso migraciones, pero SIEMPRE presentas primero (qué, por qué,
  comando/SQL exacto, query de verificación antes/después) y esperas el OK de Lina
  en el chat antes de ejecutar.
- Tras cada escritura aprobada: correr
  python scripts/panel-datos/test_integridad_supabase.py --rapido
  y confirmar estado=exito antes de continuar.
- Si un número no cuadra con lo esperado: PARA y repórtalo con la query exacta.
  No ajustes tolerancias para que un test pase.

## Regla de comparación (crítica — leer antes de reportar cualquier delta)

Los ETL de este proyecto **solo insertan y actualizan; nunca reconcilian lo que desaparece de
la fuente**. Por eso un delta casi nunca significa "falta cargar algo": lo más probable es que
**sobre** algo que la fuente ya no tiene. Revisa por exceso antes que por defecto.

Nunca compares `count(*)` de una tabla contra el conteo de la fuente viva. Supabase conserva
historia a propósito y va a tener más filas. Compara solo lo que la fuente confirmó en la
última corrida:

```sql
-- cursos vigentes (los que la fuente confirmó en la última corrida)
SELECT nombre, visto_en_fuente_at FROM courses
WHERE cohorte = (SELECT max(cohorte) FROM courses)
  AND visto_en_fuente_at >= (SELECT max(visto_en_fuente_at) FROM courses) - INTERVAL '12 hours';
```

Ejemplo concreto de falsa alarma permanente si ignoras esto: MR tiene 559 matrículas en
Supabase vs 423 en h2test. La diferencia son las 136 del curso que cerró clases —
historia legítima, no un error. Reportarlo como discrepancia en cada vuelta es ruido.

**Antes de reportar cualquier hallazgo de cursos, consulta `v_choques_cursos`** (migración
027). Si la señal no está ahí, pregúntate si tu hallazgo es real o si la vista necesita una
señal nueva.

## Discrepancias YA EXPLICADAS — no las re-descubras
- Δ26 MR (343 universo vs 317 activos): hueco de diseño (MR no purga a nivel de fila), no corrupción.
- 777 ≠ 760 JC: universo enrollments vs activos canónicos (diccionario-metricas).
- 79 vs 72 retirados JC: eventos vs personas (el gap de 7 SÍ está pendiente — P1#2).
- **RE-VERIFICADO 2026-08-12, YA NO REPRODUCE — no perseguir estos dos:**
  - retiros MR "roto estructuralmente" (0/343 por cédula): FALSO al verificar en vivo. Las
    cédulas normalizan bien; el 0% de match real es que 25/33 retiros MR son candidatas que
    se dieron de baja ANTES de matricular (existen en `postulantes_mr`, nunca en
    `participants` — coherente con el diseño, `retiros.participant_id` es nullable a
    propósito). No es un bug de matching. Ahora visible en el panel privado, pestaña
    "📅 Retiros por año" (`leer_retiros_por_anio()`, ver panel-control-jc-mr.md §7.22).
  - MR 2025 = 1.016 en `v_programa_stats` (debería ser 302): **FIJADO 2026-08-12.** Causa
    real: `importar_historico_q10.py` pid 16 forzaba TODO el periodo a `programa='mr'` "por
    periodo", pisando 2 cursos JC mezclados en ese mismo periodo Q10 ("Emprendimiento: Idea
    de Negocio JC", "Fundamentos Lógica de Programación - 2026"). Corregido: `UPDATE courses
    SET programa='jc'` en esos 2 ids + `recompute_aggregates()` (v_programa_stats MR 2025 ya
    da 302) + código cambiado a override "por curso" (`MAPA_PERIODOS[16]` ahora `None`,
    delega a `clasificar_curso()`) + 2 keywords nuevos en `KEYWORDS_MR` (los otros 2 cursos
    MR reales de ese periodo no tenían ningún mecanismo de clasificación salvo el override
    ciego que se acaba de quitar). Ver docs/procesos/plan-enriquecimiento-final-2026-08-12.md §6.
- HerpowerED = copia de General (99,98% solape).
- Aprobación 15,2% vs 31,6% MR: denominadores distintos (matrícula vs estudiante), no contradicción.
- Emoflow MR = no desplegado (nunca "0% de uso"). Estrato JC = sin fuente (nunca 0%).
- 37 cédulas MR nuevas confirmadas → resoluble con sync_postulantes_mr.py (P1#1, proponlo primero).
- 16 pares discordantes postulantes_mr: cola humana (Downloads/postulantes_mr_disonancias_general.xlsx).
- **Curso JC HTML duplicado por renombre: RESUELTO 2026-07-29** (migraciones 026/027). El
  fantasma se archivó en `datos_archivados` y se retiró de courses/enrollments/
  aprobacion_cursos/historial_cursos(_ciudad). Si vuelve a aparecer, es un bug nuevo.
- **Curso MR "De la idea a la acción" congelado desde el 21-jul: NO es un error.** Cerró
  clases de verdad (confirmado por Lina) para abrir Finanzas Inteligentes. Se conserva como
  historia; aparece en `v_choques_cursos` como informativa, no como problema.
- **`courses.estado` siempre dice "activo"** — es hardcodeado por el ETL, no un ciclo de vida
  real. Nunca lo uses para saber si un curso está vigente; usa `visto_en_fuente_at`.
- **Los 17 fantasmas en 6 cursos JC** (matrículas de personas dadas de baja, congeladas desde
  el 23-jul): mismo mecanismo upsert-only. Pendiente de decisión — "matrícula vigente" se
  resuelve con criterio de consulta, no borrando datos.

## Reglas duras (validadas en este proyecto, no las reinventes)
- truststore.inject_into_ssl() al inicio de todo script Python nuevo.
- Nunca imprimas secretos ni PII en chat/logs/commits. PII solo en tools/ (gitignoreado).
- JSON de n8n siempre desde archivo UTF-8, nunca inline por PowerShell.
- Un commit por punto resuelto, mensaje en español, sin PII.
- Toda cifra que reportes debe declarar su fecha (v_frescura).

## Entregables al cerrar la sesión (SIEMPRE)
1. tools/coherencia_<fecha>/informe_coherencia.md — por fuente: frescura, deltas,
   discrepancias clasificadas, decisiones de arbitraje de Lina, qué se corrigió (con
   verificación antes/después) y qué queda pendiente.
2. Actualizar docs/procesos/supabase-estructura.md si cambió el estado 🟢🟡🔴 de alguna tabla.
3. Entrada al FINAL de claude_sessions.md (5-10 líneas, formato del archivo).
4. Si un patrón nuevo resultó reutilizable → docs/convenciones.md.

Empieza por la vuelta A (Q10). Un paso a la vez, reportando el resultado real antes de
pasar al siguiente.
```

---

**Notas de uso**
- El loop está pensado para varias sesiones: cada sesión puede cubrir 1-3 vueltas; las
  decisiones de arbitraje quedan escritas en el informe y se reutilizan.
- Si Samuel resuelve los P0 de seguridad (rotación de claves) o la decisión de `retiros`
  MR, actualizar la sección "YA EXPLICADAS" de este prompt antes de la siguiente corrida.
- Conecta con [[plan-maestro-2026-07-29]] · [[diccionario-metricas]] · [[supabase-estructura]].
