# Prompt para Claude Code — ejecutar el plan de visualización

> Creado 2026-07-30 (sesión Cowork con Lina). Handoff para la instancia que ejecuta
> `plan-visualizacion-2026-07-30.md`.
> ⚠ Corre **en paralelo** con otra instancia que está arreglando las alertas de Telegram
> (`prompt-fix-alertas-telegram.md`). Las reglas de coordinación de abajo no son opcionales.
> Modelo recomendado: **Sonnet** para las vistas y la GUI; **Opus** si aparece una decisión de
> arquitectura de datos.

---

```
Vas a ejecutar el plan de visualización y operabilidad de la DB de panel-datos-rofe (Fundación
ROFÉ / Jóvenes creaTIvos).

## Lectura obligatoria, en este orden
1. CLAUDE.md — reglas duras del proyecto.
2. docs/procesos/plan-visualizacion-2026-07-30.md — TU PLAN. Las 3 fases, la secuencia y la
   decisión pendiente de 1.3.
3. docs/procesos/diccionario-metricas.md — definiciones canónicas. Ninguna cifra que muestres
   puede contradecir este archivo.
4. docs/convenciones.md — en particular las secciones nuevas: "Un ETL que solo hace upsert
   nunca reconcilia lo que desaparece de la fuente" y "Fuente desordenada: sellar última vez
   visto, no modelar estados".
5. docs/procesos/supabase-estructura.md — esquema, estados por tabla, RLS.
6. docs/procesos/mapa-codigo.md — antes de tocar cualquier script.
7. Las últimas 5 entradas de claude_sessions.md.

## ⚠ NUMERACIÓN DE MIGRACIONES — leer antes de crear cualquier archivo SQL

**Arrancá en 033.** No en 030.

El numerado de los archivos en `docs/migrations/` y el log de migraciones aplicadas de Supabase
**son dos secuencias distintas que divergieron el 2026-07-28**. En el log real de Supabase ya
están aplicadas, todas del 28-jul: `028_identificar_contacto_con_declarados_drop`,
`029_whatsapp_contactos_declarados_tabla`, `030_empresa_patrocinadora_jc`,
`031_mr_microcreditos`, `032_fix_v_programa_stats_por_ciudad`. En el repo esas mismas
migraciones están guardadas con los números 022 a 025.

Consecuencia: las migraciones 026, 027 y 028 del 29-jul y la 029 del 30-jul **reusaron números
que el log ya tenía ocupados con otro contenido**. Y quedaron dos archivos `028` en el repo
(`028_email_bounces_veces_soft`, aplicada 22:31, y `028_v_choques_cohorte`, aplicada 22:57, por
sesiones que no se veían entre sí).

No rompe nada técnico — Supabase versiona por timestamp y el número es una etiqueta — pero deja
el rastro de auditoría ambiguo, que es justo lo que la convención existe para evitar.

**Reglas para vos:**
1. Elegí el próximo número como **máximo entre las dos secuencias + 1**. Hoy eso da **033**.
   Verificalo antes de empezar: `ls docs/migrations/` y `list_migrations` del MCP de Supabase.
2. **No renombres migraciones ya aplicadas.** El archivo miente sobre su número, pero renombrarlo
   mentiría sobre el orden de aplicación, que es peor.
3. Agregá a `docs/migrations/README.md` una nota corta documentando esta divergencia y la regla
   del punto 1, junto al bloque que ya existe sobre el hueco del `004`. Es el mismo tipo de
   trampa y merece estar en el mismo lugar.

## Coordinación con otras sesiones
La instancia que arreglaba las alertas de Telegram **ya terminó** (5 commits, verificado en
vivo el 30-jul: 0 procesos vencidos, 0 alertas de severidad alta). Aun así:

- **NO toques `v_frescura`** ni sus umbrales — se acaban de calibrar (12 h para `cohorte_ingresos`,
  `aprobacion_cursos` y `retiros`; 30 h para el resto). Sí tenés que **leerla**: cada panel debe
  mostrar la fecha del dato.
- **NO toques `n8n-workflows/`** ni los scripts `check_*.py`.
- **Archivos compartidos** (`claude_sessions.md`, `convenciones.md`, `supabase-estructura.md`):
  releelos justo antes de escribir y agregá al final, sin reordenar ni reescribir secciones
  ajenas. `claude_sessions.md` es append-only.
- **`git add` SOLO de tus archivos.** Nunca `git add -A` ni `git commit -a`: el árbol tiene
  cambios de otras sesiones sin commitear y los barrerías.

## Estado verificado en vivo el 2026-07-30 07:31
Si algún número no coincide cuando arranques, PARÁ y reportalo — el sync corre cada 2 h y algo
pudo cambiar.

  cohorte_ingresos 2026 ....... jc: 832 ingresados · 760 activos · 78 retirados
                                mr: 346 ingresados · 338 activas  ·  8 retiradas
  courses 2026 ................ 11 (8 jc + 3 mr)
  v_programa_stats jc 2026 .... 760 participantes · 5.569 matrículas · 93,9% avance
  v_programa_stats mr 2026 .... 347 participantes ·   559 matrículas · 26,7% avance
  suma participantes por ciudad ... 760 exacto
  aprobacion_cursos jc rango ...... 81,1% a 100%
  alertas de severidad alta ....... 0 en v_choques_cursos y v_choques_cohorte

## Hechos que NO podés contradecir (si los ignorás, reintroducís bugs de ayer)

1. **MR activas = 338, derivado de `ingresados − bajas confirmadas en la tabla `retiros``.**
   NO uses `habilitados_unicos` de Q10 para MR: Q10 marca inhabilitada a toda mujer cuyo curso
   cerró, y eso produjo 167 falsas retiradas el 29-jul. JC sí puede usar el habilitados (760,
   verificado por 3 fuentes independientes). Ver la advertencia en diccionario-metricas.md.

2. **JC 2026 = 760 activos. Los 17 "fantasmas" son retirados reales** — verificado: los 17
   están en `retiros`, los 17 con `fecha_retiro`. `enrollments` en crudo tiene filas de más
   porque el ETL no borra, pero todas las vistas ya los excluyen con
   `en_seguimiento_jc IS DISTINCT FROM false`. **No “arregles” esto**: 760 es correcto y el
   777 crudo no lo consume ningún reporte.

3. **Los municipios del área metropolitana son 100% MR y CERO JC.** JC registra toda la
   conurbación como "Bogotá D.C." (35 ciudades distintas para 760 personas; MR tiene 138 para
   347). Un drill-down de ciudad en JC mostraría "Soacha: 0", que es un cero engañoso, no un
   dato. Si mostrás desglose de municipio en JC, tiene que decir explícitamente que la fuente
   de JC no captura el municipio.

4. **El avance de JC bajó de 98,1% a 93,9% y NO es deterioro.** Es el curso "Desarrollo Web
   Front-End - JavaScript - 2026", que arrancó el 30-jul con 2,1% y entró al promedio. Si el
   panel muestra esa caída sin contexto, se lee como un problema que no existe. Considerá
   mostrar el avance por curso además del promedio del programa.

5. **`courses.estado` miente** — el ETL lo escribe hardcodeado como "activo" para todo, y el
   curso MR que cerró sigue marcado activo. Para saber si un curso está vigente usá
   `visto_en_fuente_at`. Hoy hay 2 cursos MR cerrados (`DE LA IDEA A LA ACCIÓN` desde el
   21-jul, `HABILIDADES DEL SER` desde el 29-jul), ambos con datos válidos que se conservan.

6. **Asimetría JC/MR — regla dura del diccionario, el error más fácil de cometer en un
   frontend.** Nunca renderices 0% donde no hay fuente:
     · JC no tiene estrato, vivienda, estado civil ni estudios → "no aplica", no 0%.
     · MR no tiene Emoflow (no desplegado) ni empresa patrocinadora → "no aplica", no 0%.
     · MR no tiene `fecha_retiro` → "no disponible", no NULL mostrado como dato.

7. **Supabase conserva MÁS filas que la fuente viva, a propósito.** MR tiene 559 matrículas en
   Supabase vs 423 en h2test, por los cursos cerrados. No es discrepancia. Cualquier chequeo
   fuente↔panel debe comparar solo lo confirmado en la última corrida (`visto_en_fuente_at`).

## Regla de municipios — YA DECIDIDA, no la vuelvas a preguntar
Decisión de Lina, 2026-07-30. El desglose por municipio de MR toca celdas de 1 a 8 personas
(Soacha 2, Chía 1, Funza 1, Madrid 1, Cajicá 1, Bello 2, Palmira 2, Jamundí 4, Soledad 8) sobre
una población vulnerable, y el panel de Netlify es público. Entonces:

- **Panel público (Netlify, `anon`):** municipio visible solo cuando n ≥ 5. El resto se agrupa
  como **"área metropolitana"**. Bogotá se ve así: *Bogotá 130 · área metropolitana 6*. Nunca
  exponer un municipio con menos de 5 personas, ni siquiera detrás de un click.
- **GUI local (`service_role`, `tools/`):** detalle completo con nombre de municipio y conteo
  exacto, sin supresión. Es una herramienta interna y ahí el detalle se necesita para operar.

Implementá el umbral como constante con nombre (no un `5` suelto en el SQL) y dejá en el
comentario que la regla la decidió Lina el 2026-07-30. Alineado con el k-anonimato ya aplicado
en `v_demografia_grupo` (migración de hardening del 23-jul) — reusá ese patrón, no inventes otro.

## Alcance y orden
Seguí la secuencia de §4 del plan. En concreto:

**Empezá por la Fase 1 (capa de datos).** Es el cuello de botella: ni la GUI ni el panel web
pueden mostrar lo que la DB no expone en la forma correcta, y es lo único que no depende de
accesos que hoy no existen.

**Fase 3 (Netlify) está BLOQUEADA** — el repo `panel-datos-rofe` no está montado. Si no lo
está cuando llegues ahí, pedíselo a Lina en vez de improvisar.

**Fase 2 (GUI): el paso 5 va PRIMERO.** Extraé la lógica de datos a `panel_riesgo_datos.py`
antes de tocar la interfaz. `tools/panel_riesgo_gui.py` tiene 2.317 líneas con datos e interfaz
mezclados; meterle filtros encima sin separar es la forma más probable de romper algo que hoy
funciona. Ojo: `tools/` está gitignoreado y contiene PII — no commitees nada de ahí y no
imprimas PII en chat ni logs.

## Reglas duras técnicas
- Importá `Supa`/`get_todo`/`cargar_env_local` de un script existente (`sync_postulantes_mr.py`
  o `test_integridad_supabase.py`). NUNCA reescribas el paginador: un offset que no avanza es
  un loop infinito silencioso que ya pasó dos veces acá.
- `truststore.inject_into_ssl()` al inicio de todo script Python nuevo.
- Vistas nuevas: `anon` solo puede ver agregados sin PII. Las de nivel individuo son
  `service_role` + `security_invoker = on`, y hay que verificar los GRANT después de crearlas
  (`information_schema.role_table_grants`) — no asumir.
- Después de cualquier cambio a Supabase: `python scripts/panel-datos/test_integridad_supabase.py
  --rapido` y confirmar `estado=exito`.
- Si un número no cuadra: PARÁ y reportalo con la query exacta. No ajustes tolerancias.
- Un commit por entregable, en español, sin PII.

## Al terminar (siempre)
1. Vistas nuevas documentadas en `supabase-estructura.md` con su estado y quién las consume.
2. Patrón reutilizable nuevo → `convenciones.md` (sin tocar las secciones de la otra instancia).
3. Entrada al final de `claude_sessions.md`.
4. Actualizá `plan-visualizacion-2026-07-30.md` marcando qué fases quedaron hechas.

Arrancá confirmando los números del bloque "Estado verificado" con queries reales, y reportá
cualquier diferencia antes de escribir una sola línea.
```
