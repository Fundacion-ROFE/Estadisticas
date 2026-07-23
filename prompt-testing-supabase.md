# Prompt para Claude Code (Fable) — Plan de testing: Supabase segura y completa

Copia desde aquí hacia abajo:

---

Actúa como ingeniero de datos senior con foco en QA y seguridad. La auditoría y el análisis Emoflow ya se completaron (ver `docs/procesos/supabase-estructura.md` y diagnóstico en la nota panel-datos-etl). Tu misión ahora es **blindar** la base `panel-datos-rofe` (seguridad + integridad + robustez de pipelines) y **cerrar los gaps de cobertura** para que dé un panorama completo de AMBOS programas (JC y MR). Resultado esperado: una suite de tests reproducible, hallazgos triageados y propuestas de migración listas para aprobar.

## Hallazgos ya confirmados (verifica, triagea y resuelve — no re-descubras)

Detectados con los advisors de Supabase y queries en vivo el 2026-07-23:

1. **21 vistas `v_*` con SECURITY DEFINER (nivel ERROR)**: todas las vistas del panel saltan RLS por diseño. El precedente es real: `asistencia_promedio` expuso 490 correos a anon hasta 2026-07-14. Cada vista debe auditarse columna por columna: cero PII, cero posibilidad de reconstruir individuos.
2. **2 funciones SECURITY DEFINER ejecutables por `anon` vía RPC**: `es_publico(uuid)` y `participa_en(uuid, programa)`. Permiten sondear membresía por id. Si solo las usan las policies, revocar EXECUTE a anon/authenticated.
3. **Policy `asistencia_update_admin` en `asistencia_zoom` con `USING (true)` para UPDATE** (WARN): el with_check limita a service_role, pero la policy está mal formada — corregir.
4. **6 tablas PII con RLS habilitado y cero policies** (`postulantes_mr`, `postulantes_jc`, `email_optout`, `email_bounces`, `campanas_enviadas`, `asistencia_promedio`): efecto actual = solo service_role (correcto), pero es implícito. Documentar como decisión intencional o crear policy deny explícita.
5. **Cuadre cohorte JC**: `cohorte_ingresos` dice ingresados=832 pero activos(765) + retirados(69) = 834. Puede ser definicional (desertores institucionales fuera de ingresados) — pin down la definición exacta y déjala como constraint o como test documentado.
6. **Discrepancia 0,7% entre `emoflow_ingresos` (27.408) y `emoflow_ingresos_diario` NACIONAL (27.594)**: causa raíz ya identificada en la auditoría — convertirla en test de cuadre con tolerancia explícita.
7. Nota: el análisis previo reportó n=777 activos pero `cohorte_ingresos` dice activos=765 — reconciliar qué definición de "activo" usa cada fuente y estandarizarla.

## Fase 1 — Seguridad (la base debe ser segura ANTES que útil)

1. **Superficie anon real**: con la anon key (la misma del frontend Netlify), intenta leer TODAS las tablas y TODAS las vistas `v_*`, y ejecutar todas las RPC expuestas. Registra qué devuelve cada una. Criterio: ninguna fila con email, nombre, cédula, fecha de nacimiento ni combinación re-identificable (ciudad+edad+género con n<5).
2. Repite los advisors de Supabase (security y performance) tras cada corrección hasta quedar en verde o con excepciones documentadas.
3. **Repo limpio**: `git ls-files` — confirmar que tools/, payloads y credenciales no están trackeados; revisar que ningún data.json en docs/ contenga datos individuales; buscar claves hardcodeadas en scripts (`service_role`, `eyJ`).
4. **Respaldo**: verificar estado de backups/PITR del proyecto y documentar el procedimiento de restore en un runbook.

## Fase 2 — Suite de integridad (script `scripts/panel-datos/test_integridad_supabase.py`)

Tests automatizados con pass/fail y tolerancias explícitas, ejecutables en un solo comando:

- FKs/huérfanos: enrollments→participants, emoflow_ingresos→participants, snapshots consistentes.
- Unicidad: email normalizado único donde aplique; duplicados en postulantes_*.
- Dominios: ciudades solo del catálogo `grupo_ciudad` (sin variantes), fechas dentro de rango, porcentajes 0-100, edades plausibles.
- Cuadres cruzados: emoflow_ingresos vs diario vs actividad_semanal; cohorte_ingresos vs participants vs aprobacion_cursos; hallazgos #5-#7 de arriba convertidos en tests permanentes.
- Frescura: cada tabla con sync diario debe tener updated_at/fecha de ayer o hoy; si no, FAIL.

## Fase 3 — Robustez de pipelines

- **Idempotencia**: correr cada sync_*.py dos veces seguidas → diff de la base = cero. Documentar cuáles no lo cumplen.
- **Modos de falla**: simular API Emoflow caída/respuesta parcial, Sheet renombrado, columna movida. Convención del proyecto: nunca fallar en silencio — verificar que cada script y el workflow n8n de las 9:45 fallan ruidosamente y dejan rastro (alertas_datos o log).
- Verificar que un fallo parcial no deja la base a medias (¿transaccionalidad o snapshot previo? `participants_snapshots` cubre participants — ¿y el resto?).

## Fase 4 — Cobertura: panorama completo de los programas

1. **Matriz programa × dato**: filas = {inscripción/postulantes, sociodemográficos, uso Emoflow, avance cursos, aprobación, asistencia, retiro}; columnas = {JC, MR}; celdas = existe/granularidad/calidad/fuente. Esta matriz ES el mapa del panorama — publícala en la doc.
2. **Gap #1 — retiro individual**: hoy solo agregado (69 JC / 25 MR). Diseñar tabla `retiros` (participant_id, fecha, motivo, fuente) + script de sync desde la fuente Q10/Sheet correspondiente. Entregar como PROPUESTA de migración SQL — no ejecutar sin aprobación.
3. **Paridad MR**: JC pct_aprobados=88.3 vs MR=31.6 — ¿misma métrica o definiciones distintas? Determinar qué le falta a MR para replicar el análisis uso↔resultado hecho en JC (¿MR tiene Emoflow? ¿avance individual?). Listar gaps concretos.
4. Formalizar deprecación de `emoflow_participacion_semanal` (🔴) y de `sync_emoflow.py`: plan de retiro, no ejecución.

## Fase 5 — Monitoreo continuo

Propuesta de chequeo diario post-sync (candidato a workflow n8n `panel-verificacion-diaria`): correr test_integridad_supabase.py en modo rápido, escribir resultado en `alertas_datos`, y definir quién/cómo se entera cuando falla. Exportar JSON del workflow a n8n-workflows/ si se implementa.

## Fase 6 — Verificación y cierre

- Re-ejecutar la suite completa y los advisors: estado final documentado (verde / excepciones justificadas).
- Actualizar `docs/procesos/supabase-estructura.md` (estados 🟢🟡🔴 por tabla), nota panel-datos-etl, matriz de cobertura, mapa-codigo (scripts nuevos), entrada en `claude_sessions.md`, `00-vision-global.md`.

## Restricciones

- Supabase **SOLO LECTURA** por defecto. Toda corrección (policies, revokes, constraints, tabla retiros) se entrega como archivo de migración SQL con justificación, para que yo la apruebe y apliquemos juntos. Excepción única permitida sin consulta: ninguna.
- PII nunca a GitHub: salidas con datos individuales solo en `tools/`.
- Scripts nuevos: `truststore.inject_into_ssl()`; reutilizar patrones de conexión existentes en `scripts/panel-datos/`.
- Cada hallazgo con severidad (crítico/alto/medio/bajo), evidencia (query o comando) y remediación concreta.
