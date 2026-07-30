> **Estado (2026-07-30, tarde):** Fase 1 completa (vistas + guardas, migraciones 033-035).
> Fase 2 paso 5 hecho (extracción de `panel_riesgo_datos.py`); paso 1 evaluado y NO ejecutado
> por conflicto de grano real con 3 piezas de la UI existente (ver detalle en §2 abajo y en
> `claude_sessions.md`, entrada "Fase 1 de plan-visualizacion-2026-07-30.md"). Fase 3 sigue
> **bloqueada** — el repo `panel-datos-rofe` no está montado en ninguna sesión todavía.

# Plan de visualización y operabilidad de la DB (2026-07-30)

> Pedido de Lina: poder ver toda la información actual de la DB, con filtros, en el panel de
> datos **y** en la GUI, y que las estadísticas generales varíen según los filtros aplicados.
> Incluye desglose de ciudad con municipios del área metropolitana (Bogotá → Bogotá + Soacha).
>
> Contexto: corte comprometido con dirección el **11 de agosto**. Este plan asume que la
> prioridad es que la DB sea consultable y correcta para esa fecha, no que el panel quede
> bonito.

---

## 0. Lo que ya está resuelto (no rehacer)

| Verificado el 30-jul | Resultado |
|---|---|
| Los 17 "fantasmas" de JC | **No son un problema.** Los 17 están en `retiros`, los 17 con `fecha_retiro`. Se retiraron de verdad (confirmado por Lina). 760 es el número correcto y las filas sobrantes de `enrollments` no las consume ningún reporte — el `data.json` público no contiene "777" en ninguna parte. |
| MR activas | Corregido y en producción: 346 ingresadas · 338 activas · 8 retiradas. |
| Vigilancia | `v_choques_cursos` + `v_choques_cohorte` en cero alertas altas. |
| Ninguna persona doble-contada | 0 personas en JC y MR a la vez; 1 fila por persona en `participants`, sin ciudades duplicadas. |

**Marca de agua de cursos terminados:** el umbral existente (`UMBRAL_PROMEDIO_FIN = 90.0`)
tiene un punto ciego demostrado — el curso MR cerró con 41,9% de avance y nunca se habría
marcado como finalizado. Complementarlo con `visto_en_fuente_at` es parte de la Fase 1.

---

## 1. Fase 1 — Capa de datos compartida (el cuello de botella real)

Ni la GUI ni el panel web pueden mostrar lo que la DB no expone en la forma correcta. Esta
fase es la que desbloquea las otras dos y es la única que se puede hacer sin acceso al repo
del panel. **Hacerla primero.**

### 1.1 Vista de personas para la GUI (nivel individuo, con PII) — ✅ HECHO 2026-07-30

`v_gui_personas` — `service_role` solamente, para consumo local de la GUI.

Una fila por persona con todo lo que hoy está repartido: identificación, programa, cohorte,
ciudad, municipio, `grupo_ciudad`, cursos matriculados, cursos aprobados, avance promedio,
si está al día, retiro (fecha y motivo si aplica), empresa patrocinadora (JC), uso de Emoflow
(JC), sociodemográficos (MR), microcrédito (MR).

Reemplaza los cruces que la GUI hace hoy a mano leyendo Sheets + Supabase por separado.

### 1.2 Vistas agregadas para el panel público (sin PII) — ✅ HECHO 2026-07-30

`anon` solo debe ver agregados. Tres vistas, cada una al grano de un eje de filtro, para que
el frontend combine y sume:

- `v_pub_cohorte` — programa × cohorte: ingresados, activos, retirados, % aprobación.
- `v_pub_geografia` — programa × cohorte × `grupo_ciudad` × municipio: personas, avance
  promedio, aprobados. **Es la que habilita el drill-down de área metropolitana.**
- `v_pub_avance` — programa × cohorte × cursos_aprobados (0,1,2,3…): personas. Es la que
  responde "quiénes van al día y quiénes llevan un solo curso".

### 1.3 Decisión pendiente — celdas chicas en el desglose por municipio — ✅ IMPLEMENTADO 2026-07-30

Los municipios satélite son **100% de MR y cero de JC** (JC registra toda la conurbación como
"Bogotá D.C."), y las celdas son de 1 a 8 personas: Soacha 2, Chía 1, Funza 1, Madrid 1,
Cajicá 1, Bello 2, Palmira 2, Jamundí 4, Soledad 8.

**Recomendación:** en el panel **público**, mostrar el municipio solo cuando n ≥ 5 y agrupar
el resto como "área metropolitana". Bogotá se vería así: *Bogotá 130 · área metropolitana 6*.
Conserva la información que interesa (el alcance pasa el límite urbano) sin publicar celdas
identificables de una población vulnerable. En la **GUI** (local, no pública) mostrar el
detalle completo con nombres de municipio, sin supresión.

Si preferís el detalle también en público, es un cambio de una línea en la vista — pero
conviene que quede escrito quién lo decidió.

### 1.4 Guardas — ✅ HECHO 2026-07-30

- Test en `test_integridad_supabase.py` que fije JC 2026 = 760 con el filtro de
  `en_seguimiento_jc`. Hoy los números por curso dependen de esa columna, que es de **alerta**
  operativa haciendo el trabajo de una columna de **estado**: si alguien cambia su significado,
  todos los conteos se mueven en silencio y nada lo detecta.
- Complementar `UMBRAL_PROMEDIO_FIN` con `visto_en_fuente_at` para que un curso que cierra con
  avance bajo también se marque como terminado y deje de arrastrar promedios.

---

## 2. Fase 2 — GUI local (`tools/panel_riesgo_gui.py`)

Estado actual: 2.317 líneas, CustomTkinter, ya tiene un widget de tabla con búsqueda, filtro
por columna y ordenamiento (`_filtrar`, `_ordenar`, `_col_filtro`). Lee h2test de Supabase y
avance/retirados/asistencia de Sheets, cruzando a mano.

Cambios, en orden:

1. **Apuntar a `v_gui_personas`** en vez de cruzar fuentes a mano. Elimina la mayor parte de
   `leer_avance` / `leer_retirados` / `cruzar` y con eso desaparece una clase entera de
   desincronización.
   ⚠ **Evaluado 2026-07-30, NO ejecutado.** `v_gui_personas` agrega a nivel persona
   (participant×programa×cohorte); 3 piezas de la UI actual necesitan grano persona×**curso**
   que la vista no tiene: la tabla "EN Q10 JC" (una columna por curso), el tab Admin (lista de
   cursos individuales para clasificar JC/MR/Stand-by) y los popups de detalle de Atención/
   Avance-0 (avance por curso). Forzar el swap habría roto las tres. `leer_h2test()` se dejó sin
   cambios. Si se quiere completar este paso, la vía real es extender `v_gui_personas` (o
   agregar una vista hermana) con grano persona×curso — no un swap directo. `v_gui_personas` sí
   quedó lista y es el grano correcto para el paso 4 (ficha 360).
2. **Barra de filtros arriba:** programa · cohorte · ciudad/municipio · rango de avance ·
   estado (activo / retirado). Todos combinables.
3. **Encabezado de estadísticas que recalcula con el filtro aplicado** — es el pedido
   explícito de Lina. Contadores de personas, avance promedio, % aprobación y retiros, siempre
   sobre la selección vigente, con la leyenda de cuántas personas quedaron seleccionadas.
4. **Doble clic en una persona → ficha 360** (ya existe `v_persona_360`, hoy sin consumidor).
5. **Extracción previa obligatoria — ✅ HECHO 2026-07-30.** Separada la lógica de datos a
   `panel_riesgo_datos.py` (512 líneas, sin Tkinter) antes de tocar la interfaz.
   `panel_riesgo_gui.py` quedó en 1.842 líneas, solo interfaz, importando del módulo de datos.
   Verificado con `ast.parse` + import real de ambos módulos.

---

## 3. Fase 3 — Panel de datos (Netlify, Next.js)

⚠ **Bloqueado:** el repo `panel-datos-rofe` no está montado en la sesión. Hay que conectarlo
antes de poder trabajarlo.

Una vez conectado:

1. **Selector de cohorte y programa** global, que afecte todos los paneles de la página.
2. **Estadísticas de cabecera que recalculan** según los filtros, leyendo `v_pub_cohorte`.
3. **Ciudad con drill-down:** click en un grupo (BOG) despliega sus municipios desde
   `v_pub_geografia`, con la regla de supresión de 1.3.
4. **Vista de avance** desde `v_pub_avance`: distribución de personas por cantidad de cursos
   aprobados, para responder de un vistazo quiénes van al día y quiénes llevan uno solo.
5. **Etiquetar siempre la asimetría JC/MR.** Estrato y vivienda solo existen en MR; Emoflow y
   empresa patrocinadora solo en JC. El panel tiene que decir "no aplica", nunca mostrar 0% —
   es la regla dura del diccionario y el error más fácil de cometer en un frontend.
6. **Fecha del dato visible** en cada panel (`v_frescura`). Un número correcto sin fecha
   engaña igual que uno equivocado.

---

## 4. Secuencia recomendada frente al 11 de agosto

| Orden | Qué | Por qué así |
|---|---|---|
| 1 | Fase 1 completa (vistas + guardas) | Desbloquea todo lo demás y es lo único que no depende de accesos que hoy no tengo |
| 2 | Fase 2 pasos 5 y 1 (extraer datos + apuntar a la vista) | Baja el riesgo de la GUI antes de agregarle interfaz |
| 3 | Fase 3 pasos 1-3 (cohorte, cabecera, ciudad) | Es lo que se va a mostrar el 11-ago |
| 4 | Fase 2 pasos 2-4 (filtros y ficha en la GUI) | Uso interno, puede seguir después del corte |
| 5 | Fase 3 pasos 4-6 | Refinamiento |

**Lo que NO entra antes del 11-ago:** el track histórico 2019-2025 (tiene su propio plan con
puertas), asistencia Zoom (en beta, `asistencia/data.json` congelado desde el 24 de junio), y
ManyChat.

---

## 5. Conexiones

[[plan-maestro-2026-07-29]] · [[diccionario-metricas]] · [[supabase-estructura]] ·
[[dashboard-web]] · [[panel-datos-etl]]
