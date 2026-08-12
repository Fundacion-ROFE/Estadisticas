# Plan — Etapa final de alimentación de la DB (enriquecimiento histórico 100%)

**Fecha:** 2026-08-12 · **Estado:** análisis de brechas listo, subagentes por desplegar (pendiente confirmación del target Power BI y del alcance).

Fuente: `C:\Users\EstudiantesJC\Downloads\COMPLETE-ORDEN-INFORMATION` (66 archivos, JC 2019–2025 + Mujeres ROFÉ).
Catálogo navegable generado por `scripts/panel-datos/catalogar_fuentes_historicas.py` en `tools/catalogo_complete_orden/` (INDICE.md + catalogo.json + 66 .md; PII, gitignoreado).

---

## 1. Lo que YA tenemos por estudiante (Supabase `participants` + `v_persona_360`)

Identidad (cédula, nombre, email, celular), sociodemografía básica (género, edad, fecha_nac, ciudad/grupo_ciudad, estrato, estado_civil, nivel_estudio, tipo_vivienda), emprendimiento (tiene/nombre/situación), matrícula/avance/cursos (Q10), seguimiento JC, Emoflow (ingresos), asistencia (Zoom reciente), retiros (2023→), microcréditos (MR).

## 2. Dimensiones NUEVAS detectadas en el corpus (NO están en Supabase)

| Dimensión | Campos | Fuentes principales |
|---|---|---|
| **Socioeconómico ampliado** | institución educativa, grado, promedio (nota colegio), nivel de inglés, ingreso del hogar, nº personas núcleo, acceso internet/computador | `Jóvenes Creativos única tabla`, `Fase #1 … (respuestas)` 2023/2025, `BD Aplicantes` 2021/2022 |
| **Empleabilidad** | intención de empleo, ¿vinculado laboralmente?, empresa | `empleabilidad 22-23`, `Empleabilidad JC2020/2021/2022/2023`, `Listado Empleabilidad` |
| **Resultados / proyecto final** | presentó proyecto (sí/no), puntaje jurado/técnico, nota final | `PUNTUACION FINALISTAS 2019`, `Presentación de Proyectos Finales` 2021/2023/2024, `Encuesta Final JC2022` |
| **Avance histórico real (monitorías)** | avance por curso mantenido por monitores — **posible recuperación del avance de retirados que Q10 purgó** | `BD Seguimiento de Monitorias` 2023/2024/2025 |
| **Retiros históricos detallados** | motivo, fecha, etapa (pre-2023) | `Retiros JC` 2020/2021/2022/2023 |
| **Convocatoria / embudo** | postuló vs seleccionado, estado (SELECCIONADO/…) | `BD CONVOCATORIA 2023`, `BD Aplicantes …`, columna `estado` de la única tabla |
| **MR extendido** | dirección, departamento, grupo étnico, discapacidad, sostenimiento, canal de adquisición ("¿por dónde conociste?"), presentación personal, hobbies, ingresos familiares, personas del núcleo | `BD-Mujeres ROFÉ 2026 - General.csv` (63 col) |

## 3. Target "100% por estudiante" (propuesto)

Núcleo por cédula: [lo que ya tenemos] + [las 7 dimensiones nuevas], con `fuente` y `fecha` por dato para trazabilidad. Tablas nuevas candidatas (a confirmar): `estudiante_socioeconomico`, `empleabilidad`, `resultados_proyecto`, `avance_monitorias_historico`, y ampliación de `postulantes_jc`/`postulantes_mr`/`retiros`.

> **PENDIENTE CLAVE:** la lista exacta de campos del **Power BI** que el equipo ya usa y que nosotros no tenemos. Eso define el target autoritativo; sin esa lista trabajo sobre el superconjunto inferido del corpus.

## 4. Clústeres de subagentes (extracción, 1 spec preciso c/u)

Cada subagente: lee los digests `.md` del clúster → localiza archivo/hoja/columnas clave por **cédula** (fallback correo) → extrae y normaliza → escribe payload JSON en `tools/enriquecimiento/<clúster>.json` con `{cedula, campo, valor, fuente, anio}`. NO escribe a Supabase (eso lo hace un cargador idempotente después, con las reglas del sync).

- **A · Socioeconómico + convocatoria** (única tabla, Fase#1 respuestas, BD Aplicantes/Convocatoria)
- **B · Empleabilidad** (todos los `empleabilidad*` + `Listado Empleabilidad`)
- **C · Resultados/proyecto final** (PUNTUACION FINALISTAS, Presentación proyectos, Encuesta Final)
- **D · Avance monitorías histórico** (BD Seguimiento Monitorias 2023/2024/2025) — prioridad: verificar recuperación de avance de retirados 2024
- **E · Retiros históricos** (Retiros JC 2020–2023)
- **F · MR extendido** (BD-Mujeres ROFÉ General.csv)

## 4b. Resultado PILOTO D (2026-08-12)

Subagente sobre `BD Seguimiento de Monitorias JC2024` (ambos archivos). **Recuperación de avance de retirados: 24 de 139 (17%), solo curso HB** (media 91.2, 13 al 100%). Las 139 sí están en el archivo pero solo en rosters demográficos (`Global`, `Retirados`, `Retirados con ingresos y avance` — este último sin avance real). Conclusión: **las monitorías NO conservan de forma amplia el avance de los retirados**; el avance individual de retirados 2024 sigue siendo mayormente irrecuperable (confirma lo dicho sobre Q10, con recuperación parcial menor). Payloads en `tools/enriquecimiento/`. Script reutilizable: `scripts/panel-datos/extraer_avance_monitorias_2024.py`.

**Implicación para el plan:** el clúster D (avance) es de BAJO valor para retirados; los clústeres de valor real son las **dimensiones nuevas** (A socioeconómico, B empleabilidad, C proyecto final, F MR extendido), que aportan datos que hoy NO existen en ningún lado. La maquinaria de extracción quedó validada (script + payload + manejo PII correctos).

## 4c. Resultado CAMINO B — clústeres A/B/C/F desplegados (2026-08-12)

Helper de mejor match: `scripts/panel-datos/enriquecimiento_helper.py` (Matcher cédula>correo>nombre contra roster `tools/enriquecimiento/roster_objetivo.json`: 8.373 cédulas / 8.283 correos / 8.518 nombres, de `participants`+`postulantes_jc`+`postulantes_mr`).

| Clúster | Registros | Personas | Match | Hallazgos clave |
|---|---|---|---|---|
| **A** socioeconómico+convocatoria | 332.643 | 3.158 | 79%+ cédula, resto correo/nombre | institución/grado/promedio/inglés/ingreso_hogar/personas_núcleo/acceso_internet-pc/dirección/barrio + `estado_convocatoria`. Corrigió corrimiento de columnas en BD Inscritos Barranquilla con validadores de plausibilidad. |
| **B** empleabilidad | 960 | 278 | 70% cédula / 29% correo / 1% nombre | Solo INTENCIÓN/candidatura (`aplica_empleabilidad`, `intencion_empleo`, `proyecto_final`). `vinculado_laboralmente`/`empresa`/`cargo` NO existen en ninguna fuente — no se inventaron. |
| **C** resultados/proyecto final | 2.641 | 996 | 79,6% cédula / 8,1% correo / 12,3% nombre (riesgo homónimos documentado, `nombre_crudo` guardado) | `presento_proyecto` (678 sí/81 no), `nota_final` (453, solo 2024 TOTAL 0-60). `nombre_proyecto` y puntajes jurado/técnico separados NO existen. La fuente 2019 "PUNTUACION FINALISTAS" resultó ser de selección, no de proyecto final → separada como `puntaje_seleccion_fase2`. |
| **F** MR extendido | 43.735 | 5.126 | **100% cédula** | dirección/departamento/sostenimiento/canal_adquisicion/presentación_personal ~99,5%; hobbies 58%; grupo_étnico 52% (incl. "ninguna" genuino); discapacidad real 16 casos. |
| **TOTAL** | **379.979** | ~9.500 (con solape JC entre A/B/C) | — | — |

Payloads en `tools/enriquecimiento/*.json` (gitignoreados). Scripts reutilizables en `scripts/panel-datos/extraer_cluster_{A,B,C,F}_*.py` + `extraer_avance_monitorias_2024.py` (D).

**PENDIENTE:** (1) lista de campos del Power BI del usuario, para validar el target; (2) diseño del cargador idempotente payloads→Supabase (tablas nuevas por dimensión) + exponer en el panel privado.

## 6. Adaptar ambos paneles a las cohortes nuevas (2026-08-12) — JC hecho, MR BLOQUEADO

Petición: adaptar panel privado (`panel_control_gui.py`) y público (Vercel `panel-datos-rofe`)
para reflejar "toda la info desde 2019". Se verificó la premisa contra Supabase ANTES de tocar
UI — resultado: **cierta para JC, falsa para MR**.

### JC — premisa confirmada, cambios hechos y desplegados
- Cobertura real: agregado nacional 2019-2025 en `cohorte_historico`/`v_pub_cohorte` (sin
  desglose por ciudad/género — Q10 no existía, dato no recuperable); nivel-persona completo
  2023-2026 (`enrollments`/`courses`).
- Ambos paneles calculaban su selector de cohorte SOLO desde matrícula (`v_gui_personas` /
  `datos.cursos`), por lo que 2019-2022 nunca eran alcanzables aunque el canon ya existiera
  y las tarjetas de cohorte-cerrada ya tuvieran el fallback a `v_pub_cohorte` construido
  (§7.20 de panel-control-jc-mr.md / `ingresosProg` en `page.tsx`).
- **Fix (no regresivo, verificado):** selector = unión matrícula ∪ canon.
  - Privado: `panel_control_gui.py::_on_datos_listos` — cohortes_persona ∪ cohortes_canon.
  - Público: `page.tsx::cohortes` — además se filtró por `programa` (bug de paso: antes MR
    mostraba pestañas 2023/2024 que nunca tuvo). `npx tsc --noEmit` limpio, commit `66e0ec7`
    pusheado a `comunicaciones/main` (Vercel redeploy automático).
  - Al elegir un año solo-canon (ej. JC 2019), la arquitectura YA soportaba 0 personas
    (`_kpis_cohorte_cerrada` con `filas=[]` → "En la base: 0"; no crashea) — no fue necesario
    tocar esa lógica, solo hacerla alcanzable.

### MR — premisa FALSA, requiere decisión antes de continuar
Verificado en Supabase (2026-08-12):
1. **Sin ningún dato antes de 2025** — ni persona ni canon. `courses.programa='mr'` solo
   tiene cohortes 2025/2026. `cohorte_historico` no tiene NINGUNA fila `mr` (a diferencia de
   JC, nunca se hizo el trabajo de anclar años cerrados de MR a un consolidado oficial).
2. **MR 2025 (cerrada) tiene 1.016 personas a nivel individuo pero CERO representación en el
   canon** — no está en `cohorte_historico` ni en `cohorte_ingresos` (esa tabla solo guarda
   la cohorte viva). Los paneles no pueden mostrarle tarjetas de cohorte-cerrada como a JC.
3. **Ese "1.016" está marcado como bug conocido y sin resolver**
   (`docs/procesos/prompt-loop-coherencia-fuentes.md`: *"MR 2025 = 1.016 en v_programa_stats
   (debería ser 302)"*), con un fix ya escrito (`018_fix_programa_2025.sql`) pero nunca
   aplicado — pendiente de OK explícito del usuario, documentado como P0 desde 2026-07-2x.
4. **`retiros` de MR está roto estructuralmente**: 2026 = 0/343 cruzan por cédula; 2025 = 25
   registros de los que solo 5 resuelven a un `participant_id` real (el cuadre 25≈25 contra
   `cohorte_ingresos` documentado como coincidencia de metodologías, no las mismas personas).

### Decisión del usuario (2026-08-12) y trabajo hecho tras la pregunta

1. **¿MR corrió cohortes antes de 2025?** El usuario confirma: **MR no se maneja por
   cohortes** de selección anual como JC — las mujeres ingresan/salen sin ciclo anual fijo.
   Esto CIERRA la pregunta: no hay "cohortes 2019-2024 de MR" que migrar, es una diferencia
   estructural del programa, no un gap de datos. Pidió en su lugar un apartado que
   diferencie por AÑO (no cohorte) — hecho, ver punto 3.
2. **Fix 1.016→302:** aplicado en producción. Ver detalle completo en
   `docs/procesos/panel-control-jc-mr.md` §7.22 y `docs/procesos/prompt-loop-coherencia-fuentes.md`
   (sección "RE-VERIFICADO 2026-08-12"). Resumen: 2 cursos JC mal etiquetados como `mr` en
   `courses` (bug del importador histórico, override "por periodo" en vez de "por curso");
   corregidos en datos (`UPDATE` + `recompute_aggregates()`) y en código
   (`importar_historico_q10.py` + `normalize_q10_data.py`). `v_programa_stats`/`cohorte_stats`
   MR 2025 ya dan 302 (antes 1.016).
3c. **Rastreo riguroso MR vs Q10 + todas las mujeres al panel de control (2026-08-12).** El
   usuario dudó (con razón) del "sin Q10" hecho solo por cédula. `rastrear_mujeres_mr_q10.py`:
   match multi-campo (cédula→correo→nombre) año por año + verificación cruzada con H1Test.
   **Resultado: 588/5.158 (11,4%) están en Q10/participants** — el match multi-campo solo sumó
   19 sobre las 569 por cédula (no era un bug de cédula). Tabla por año: 2022=4,7% · 2023=3,8%
   · 2024=13,5% · 2025=28,6% · 2026=44,9% (sube hacia años recientes porque el seguimiento MR
   en Q10 arrancó en 2025). **H1Test cruzado: 176 mujeres del CSV están ahí y las 176 YA están
   en participants → 0 huecos de sync**, confirma que participants es espejo fiel de Q10. La
   baja tasa es REAL: la "Plataforma MR" es el universo de TODAS las registradas (candidatas),
   Q10 solo tiene a las que se matricularon (~600). Las 4.570 no encontradas → xlsx en
   Downloads (`mujeres_mr_sin_q10_<fecha>.xlsx`). Se enlazaron las 18 por correo en
   `postulantes_mr.participant_id` (la 1 por nombre se dejó afuera, riesgo de homónimo).
   **Panel de control:** el equipo analiza a las mujeres por VARIABLES (emprendimiento/impacto
   financiero/crédito), no por cohorte-curso como JC. Se puso a TODAS las mujeres en el panel
   de control: las ~588 con Q10 en «Explorar» (v_gui_personas), las ~4.752 sin Q10 en
   «Postulantes sin matrícula» — ahora con columna "Año" al frente, ordenadas por año desc, +
   7 columnas ricas (dirección/ingresos/sostenimiento/etnia/canal/núcleo/presentación),
   filtrables por la barra de búsqueda del componente. Los campos que Q10 aportaría quedan NULL
   para las que no lo tienen (pedido explícito).

3b. **Extensión del historial MR completo (2026-08-12, pedido explícito del usuario):** el
   backfill de `fecha_creacion` (punto 5) fue solo el primer paso. El usuario pidió llenar
   TODO el historial de esa fuente: "para las que tengan Q10 añádele la info y las que no
   agrégalas en la DB, y pon en null los valores que no posean". Migración 046: 7 columnas
   nuevas en `postulantes_mr` (direccion, presentacion_personal, personas_nucleo,
   ingresos_familiares, canal_adquisicion, grupo_etnico, sostenimiento — TEXT, mismo
   vocabulario que `enriquecimiento_mr_extendido`). `cargar_plataforma_mr_completa.py`
   reescrito para 3 rutas simultáneas: (1) `postulantes_mr` completo — 5.157/5.157 filas
   enviadas, backfill NO destructivo (solo si estaba NULL); cobertura dirección 97%
   (5.148/5.318), sostenimiento 89% (4.724/5.318). (2) `participants.{estado_civil,
   nivel_estudio,tipo_vivienda,estrato,edad}` — backfill NULL-only para las 569 mujeres con
   `participant_id` real (solo 7 tenían algo vacío que llenar — la mayoría ya estaba
   completa por `sync_sociodemograficos_mr.py`). (3) `enriquecimiento_mr_extendido` — 2.804
   filas nuevas (los 7 campos que `participants` no tiene, para esas 569 mujeres). Suite
   `test_integridad_supabase.py` 53/53 PASS; RLS de `postulantes_mr` intacto pese a las
   columnas nuevas. GUI: "Postulantes sin matrícula" (MR) ganó 7 columnas nuevas.

4. **JC 2019-2022 cargado a nivel-persona (2026-08-12, con OK del usuario tras ver "En la
   base: 0" y CSV vacío).** Fuente: "Jóvenes Creativos única tabla.xlsx" (mismo consolidado
   oficial que ancló `cohorte_historico`), filtrado a estado∈{SELECCIONADO,RETIRADO} (excluye
   NO SELECCIONADO/REVOCADO a propósito, mismo criterio de privacidad). Script
   `cargar_historico_2019_2022_jc.py`: SELECCIONADO → participant + enrollment en un "curso
   sello" del año (mismo patrón ya aprobado 2026-08-04 en `cargar_bd2023_jc.py`); RETIRADO →
   participant + fila en `retiros` (sin enrollment, recogido por la reconciliación de la
   migración 043). **512 personas cargadas** (25/98/90/299 por año — 3 menos que el canon
   515/25-100-90-300 por filas sin cédula en la fuente). Bug real encontrado y corregido en
   caliente: `tipo_vivienda` es un ENUM en Supabase, se mandaba el texto crudo → 89 fallos en
   la primera corrida (todos 2021), arreglado con mapeo explícito y reintentado (idempotente,
   0 fallos en la segunda corrida). Verificado: `v_gui_personas` ya muestra 25/98/90/299 con
   avance_promedio NULL para los retirados (correcto, ese dato nunca existió).
5. **MR: contraste y carga de "BD-Mujeres ROFÉ 2026 - Plataforma MR.csv"** (aportado por el
   usuario, 5.158 filas, año real 2022-2026 — cierra exactamente la limitante de "sin
   seccionamiento por año" documentada arriba). Contraste: **5.157/5.157 ya estaban en
   `postulantes_mr`** (99,8% de solape — confirma que es el mismo universo, con mejor fecha) —
   solo 8 genuinamente nuevas. Estrategia NO destructiva (`cargar_plataforma_mr_completa.py`,
   agrupando por conjunto-de-columnas antes de subir en lote, mismo patrón que
   `sync_postulantes_mr.py`): inserta las 8 nuevas completas; para las existentes, SOLO
   backfillea `fecha_creacion` donde estaba vacía (nunca toca otros campos). Resultado:
   cobertura de fecha_creacion en `postulantes_mr` pasó de **1.934/5.310 (36%) a
   5.162/5.318 (97%)**. Bug real encontrado y corregido: `INSERT ... ON CONFLICT DO UPDATE`
   valida las columnas NOT NULL de la fila candidata ANTES de decidir si actualiza —
   `fuente_pestana` (NOT NULL, sin default) reventaba en cualquier backfill que no la
   incluyera, aunque la fila ya existiera y el UPDATE nunca la fuera a tocar; arreglado
   mandando de vuelta su valor actual sin cambiarlo. Suite `test_integridad_supabase.py`
   53/53 PASS tras ambas cargas (JC + MR); RLS intacto.

3. **Retiros MR:** investigado a fondo — el diagnóstico de 2026-07-27 ("roto
   estructuralmente") NO reproduce. La columna correcta ("Año-retiro") ya se leía bien; el
   bajo cruce por cédula es porque 25/33 retiros MR son candidatas que se dieron de baja
   ANTES de matricular (existen en `postulantes_mr`, nunca en `participants` — diseño
   correcto, no bug). Se construyó `leer_retiros_por_anio()` + pestaña nueva "📅 Retiros por
   año" en el panel privado para hacer visible ese universo completo (antes invisible por
   depender toda la UI de `v_gui_personas`). Incluye en pantalla la limitación de fuente:
   la base MR entregada no viene seccionada por año de origen (a diferencia de JC), así que
   el desglose no puede ser más fino sin pedir al equipo bases MR separadas por año.

## 5. Herramientas de lectura (hechas)

- `catalogar_fuentes_historicas.py` — Excel/CSV gigante → .md + catalogo.json (streaming, memoria plana). Reutilizable para cualquier corpus futuro.
- Pendiente: `extraer_por_cedula.py` (helper común que los subagentes invocan para leer una hoja concreta y volcar filas por cédula, evitando que cada agente reimplemente lectura de xlsx).
