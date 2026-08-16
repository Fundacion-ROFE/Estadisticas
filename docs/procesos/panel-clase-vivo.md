# Panel de clase en vivo + Stats desde ASISTENCIA-VALIDADA

**Estado:** Fase 1 y Fase 2 CONSTRUIDAS. Primera clase real de principio a fin con monitor
mirando el panel: 2026-08-06 — se encontraron y corrigieron **2 bugs nuevos en vivo** (UUID
reciclado de sala recurrente, mismo topic Zoom compartido por 2 horarios distintos) y se agregó
resumen de conteo rápido + indicador de actividad viva (ver sección propia abajo). Ciclo de
correos alternos EJECUTADO el mismo día (tabla Supabase + panel con match/color nuevo,
probados con datos sintéticos) — solo falta crear el Forms manualmente para que el flujo
reciba casos reales (ver "Plan: correos alternos").
**Última actualización:** 2026-08-06
**Procesos relacionados:** [[zoom-asistencia]] (fuente de todos los datos: `ZOOM-ASISTANCE`,
`ASISTENCIA-10MIN`, `LIVE-LOG`, `ASISTENCIA-VALIDADA`) · [[supabase-estructura]] (esquema de
`participants`/`postulantes_jc`/`postulantes_mr` — relevante para el plan de correos alternos)

## Qué es (2 herramientas, no 1)

Lina propuso una sola idea que en realidad son dos herramientas con necesidades de
frescura de datos opuestas — separarlas es la primera decisión de diseño:

| | Fase 1 — Stats validadas | Fase 2 — Panel en vivo |
|---|---|---|
| **Qué muestra** | Estadísticas por clase/curso (como `ZOOM-STATS` hoy) pero sobre datos ya identificados (solo estudiantes reales, sin typos, sin mentores/staff) | Durante una clase en curso: quién de los matriculados **ya entró** vs. **quién falta**, en rojo, para que el monitor lo llame |
| **Frescura necesaria** | Una vez al día (17:45, cuando corre `validar_asistencia.py`) | Segundos — mientras la clase está pasando |
| **Fuente** | `ASISTENCIA-VALIDADA` | `LIVE-LOG` (ya vivo) + roster de matriculados con correo (nuevo, desde Supabase) |
| **Dificultad relativa** | Baja — mismo patrón que `ZOOM-STATS`, solo cambia la pestaña de origen | Media — reusa piezas que ya existen, pero necesita 2 piezas nuevas (ver abajo) |

**No se pueden fusionar en una sola hoja**: si el panel en vivo leyera de
`ASISTENCIA-VALIDADA`, solo se actualizaría una vez al día y nunca serviría durante la
clase — perdería exactamente lo que lo hace útil.

---

## Fase 1 — `ZOOM-STATS` pero desde `ASISTENCIA-VALIDADA`

**Estado: CONSTRUIDA (2026-08-03).** Pestaña `ZOOM-STATS-VALIDADO` creada en H3Test —
`construir_zoom_stats_validado()` en `scripts/zoom-asistencia/setup_zoom_asistance.py`
(`python setup_zoom_asistance.py --solo-validado`, no toca `ZOOM-ASISTANCE`/`CUPOS`/
`ZOOM-STATS`). Corre en paralelo a `ZOOM-STATS`, como estaba planeado — no la reemplaza
todavía. Verificado con datos reales: sesiones de ruido ("Mi reunión", "TEST
AUTOMATIZACION...") que sí aparecían en `ZOOM-STATS` con 0 conectados ya no existen en la
versión validada (`ASISTENCIA-VALIDADA` las excluye desde el origen); conteos de
"Conectados" bajan 1 en varias sesiones por mentores Sofka que `ZOOM-STATS` no filtraba
(solo excluye por dominio de correo `tocaunavida.org`, no por la hoja de mentores).

**Columna añadida sobre el diseño original de este documento:** "Identidad por
confirmar" — cuenta cuántos registros de la sesión quedaron en `REVISAR`/`EXAMINAR`/
`MANUAL` (identidad no resuelta con certeza), sin restar del número de "Conectados"
(ese sigue contando a todos los no-`EXCLUIR`, igual que antes). Da visibilidad de calidad
del dato por clase sin tocar el número principal.

### Qué hace
Mismo tipo de estadísticas que `ZOOM-STATS` (conectados vs. cupo, promedio de estancia,
alumnos <70%, por sesión y por semana) pero calculadas sobre `ASISTENCIA-VALIDADA` en vez
de `ZOOM-ASISTANCE` crudo.

### Por qué es mejor que la fuente actual
- **Sin ruido**: `ASISTENCIA-VALIDADA` ya excluye staff, mentores de Sofka y reuniones que
  no son clase (`EXCLUIR`, ver [[zoom-asistencia]]) — hoy `ZOOM-STATS` filtra staff a mano
  por dominio (`CUPOS!G`) pero no filtra mentores ni reuniones de prueba.
- **Sin duplicados por typo**: una persona que escribió mal su correo hoy cuenta como 2
  personas distintas en `ZOOM-STATS` (`ZOOM-ASISTANCE` tiene el dato crudo). En
  `ASISTENCIA-VALIDADA` ya está resuelta al correo/nombre real.
- **Solo estudiantes reales**: cada fila ya tiene `Nombre en la base` y `Programa`
  (JC/MR) resueltos contra Supabase — se puede cortar por programa sin adivinar.

### Trade-off que hay que aceptar
Deja de ser instantánea. Una clase de las 6pm no aparece en las stats hasta el
`validar_asistencia.py` del día siguiente (17:45). Para el caso de uso "ver cómo nos fue
hoy en la tarde", esto es peor que `ZOOM-STATS` actual.

### Diseño propuesto
- Nueva pestaña `ZOOM-STATS-VALIDADO` (no reemplaza a `ZOOM-STATS`, corre en paralelo — la
  decisión de cuál es la fuente de verdad queda para después de comparar ambas un tiempo).
- Mismas columnas/lógica que `ZOOM-STATS` (`docs/procesos/zoom-asistencia.md`, sección
  `ZOOM-STATS`), pero las fórmulas apuntan a `ASISTENCIA-VALIDADA` en vez de
  `ZOOM-ASISTANCE`.
- Cuidado con las filas divisorias de sesión (agregadas 2026-07-30, ver
  [[zoom-asistencia]]): tienen texto en la columna `Origen` (`"SESION -- ..."`) en vez de
  `ZOOM-ASISTANCE`/`ASISTENCIA-10MIN` — los `COUNTIFS`/`AVERAGEIFS` deben filtrar por
  `Origen = "ZOOM-ASISTANCE"` (o distinto de vacío/`SESION --`) para no contarlas como
  registros.
- El cupo por horario (misma lógica de `CUPOS!H:I` + día/hora) se reutiliza tal cual — no
  depende de la fuente de asistencia.

### Esfuerzo estimado
Bajo. Es re-apuntar fórmulas existentes a una pestaña con casi la misma forma
(headers distintos, misma idea de columnas). Un par de horas, no un rediseño.

---

## Fase 2 — Panel en vivo: quién falta por entrar

**Estado: CONSTRUIDA (2026-08-03), probada con eventos sintéticos.** Motivado por el hallazgo de hoy: el
promedio de tiempo conectado en clase es ~65% — los monitores necesitan ver en vivo quién
se salió, no solo quién nunca entró. Decidido: **Sheets, no Excel** (ver conversación
2026-08-03 — toda la escritura en vivo ya está construida sobre Sheets + Service Account;
migrar a Excel significaría una integración nueva con Microsoft Graph desde cero).

**Corrección importante sobre el diseño original de este documento (2026-07-30):** decía
que el roster de matriculados saldría de Supabase (`courses`+`enrollments`). **Eso no
sirve para esta herramienta.** Se comprobó hoy mismo (al resolver el caso Sala 1/Sala 2 de
`CUPOS`) que Supabase/Q10 **no distingue los subgrupos de horario** (Uno/Dos/Avanzado) —
matricula a nivel de curso completo (HTML, ~700+ personas), no por franja horaria
específica. Si el panel comparara contra ese universo, un salón real de 44 estudiantes
mostraría a cientos de "matriculados en HTML" en rojo por error. **El roster correcto por
sala tiene que salir de la BD Seguimiento** (columnas `Horario HTML`/`Horario Lógica`/etc.,
`E-mail`) — la misma fuente y el mismo archivo que ya lee `tools/analizar_cupos_bd.py` para
`CUPOS`. Consecuencia aceptada: el roster del panel hereda la misma limitación de
`CUPOS` — es tan fresco como la última vez que alguien descargue la BD Seguimiento y
corra el script. No es una limitación nueva, es la misma que ya conocíamos.

### La pregunta de Lina: "¿cuán viable es en Sheets?"

**Viable, con 2 piezas nuevas que hoy no existen.** Sheets ya demuestra que puede hacer la
parte difícil (formulas que se recalculan solas cuando n8n escribe filas nuevas por API —
exactamente lo que hace `ZOOM-STATS` hoy contra `ZOOM-ASISTANCE` en vivo). Lo que falta no
es "¿Sheets puede hacer esto?" sino "¿de dónde sale el roster con correos?" y "¿cómo sabe
la hoja que hay una clase corriendo ahora mismo?".

### Cómo quedó construido (3 piezas)

#### Paso 1 — `MATRICULADOS-VIVO`: roster real por horario, desde la BD Seguimiento
**Archivos:** `tools/analizar_cupos_bd.py` (extendido, no un script nuevo) +
`construir_matriculados_vivo()` en `scripts/zoom-asistencia/setup_zoom_asistance.py`.
- `analizar_cupos_bd.py` ahora también emite `roster_por_horario` en
  `tools/cupos_clases.json`: por cada columna `Horario *`, además de contar, guarda
  `{horario: [{nombre, correo}, ...]}` (columnas `Nombres`/`Apellidos`/`E-mail` del
  workbook). Corrida real (2026-08-03, BD Seguimiento del 2026-07-27): **5.319
  asignaciones horario-estudiante, 89 horarios distintos**.
- `python setup_zoom_asistance.py --solo-matriculados-vivo` lee esa clave y escribe
  `MATRICULADOS-VIVO` (`Horario | Nombre | Correo`). Verificado: los 3 horarios de HTML
  Sábado 2pm (Uno/Dos/Avanzado) salen con 44/45/48 personas — coincide con el cruce de
  correos reales hecho hoy contra Zoom (Sala 1=Uno, Sala 2=Dos).
- No usa Supabase (ver corrección más abajo).

#### Paso 2 — `REUNIONES-ACTIVAS`: qué sala está en vivo ahora mismo
**Archivos:** `construir_reuniones_activas()` en `setup_zoom_asistance.py` (pestaña vacía,
columnas `UUID | Topic | Host | Apertura | Activo`) + 4 nodos nuevos en el workflow n8n
`Zoom - Asistencia` (id `jkNaE51PKQ4TQzNq`).
- **Abrir** — `Detectar Apertura Reunion` (Code, cuelga de `Registrar LIVE-LOG`) +
  `Abrir en REUNIONES-ACTIVAS` (Google Sheets `appendOrUpdate`, upsert por `UUID`). El
  Code usa `$getWorkflowStaticData('global')` para saber si el UUID ya se abrió **sin
  leer/escribir Sheets en cada evento** `participant_joined/_left` (una clase genera
  decenas por minuto — ya se agotó la cuota de la API de Sheets 2 veces en sesiones
  anteriores por esto). Probado: 2 `participant_joined` seguidos del mismo UUID →
  1 sola fila, sin duplicar.
- **Cerrar** — `Cerrar Reunion Activa` (Code) + `Cerrar en REUNIONES-ACTIVAS` (Sheets
  `appendOrUpdate`, mismo upsert), **insertados EN LÍNEA** entre `Ruteo Evento Zoom`
  (salida `ended`) y `Esperar 90s` — no en paralelo. Ver gotcha abajo sobre por qué.
  `Activo` pasa a `FALSE` (booleano, no un string `"cerrada"`) sin borrar la fila — evita
  tener que acertar el número de fila exacto para un delete, y deja historial gratis.
- **No se aplica aquí** el refinamiento de "10 participantes distintos" (eso es para
  decidir CUÁNDO tomar la foto automática de `ASISTENCIA-10MIN`, un problema distinto —
  ver [[zoom-asistencia#Espera anclada a horario oficial]]). Para saber si una sala está
  "en vivo" el panel no necesita esperar ningún umbral — mostrar presencia real desde el
  primer `joined` es mejor, no peor.

#### Paso 3 — `PANEL-EN-VIVO`: la vista que ve el monitor
**Archivo:** `construir_panel_en_vivo()` en `setup_zoom_asistance.py`, mismo patrón que
`construir_zoom_stats_validado()`: `recrear()`, fórmulas con `USER_ENTERED`, `loc_filas()`
(separador `;` del locale `es_ES`), `regla_formula()` para el color condicional.
- **2 bloques fijos** (Sala A / Sala B, no 4 — coincide con la operación real de "2
  salas"; cada uno toma la 1ª/2ª fila de `FILTER(REUNIONES-ACTIVAS!A:A, Activo=TRUE)` vía
  `INDEX`, vacío si no hay esa reunión activa).
- **Resolución del horario** reusa la cascada de `CUPOS` — a propósito **sin** el 3er paso
  (suma por área+día+hora): si el topic no tiene nombre exacto ni `Alias Zoom`, el bloque
  muestra `"SIN ALIAS -- agregar Alias Zoom en CUPOS para este topic"` en vez de un roster
  inventado. Con el alias de Sala 1/Sala 2 puesto hoy, esas 2 salas ya resuelven bien.
- **Presencia — 3 estados (ampliado 2026-08-04, antes era binario PRESENTE/NO HA ENTRADO):**
  `NUNCA ENTRÓ` (cero `joined` en `LIVE-LOG`) · `PRESENTE` (`joined` > `left`) · `ENTRÓ Y
  SALIÓ` (tuvo al menos 1 `joined` pero `left` ≥ `joined`) — pedido explícito para que
  cualquier persona (no solo quien construyó el panel) distinga de un vistazo quién nunca
  llegó de quién sí entró y se fue, en vez de mezclar ambos casos en una sola etiqueta.
  Formato condicional: verde (`PRESENTE`), rojo (`NUNCA ENTRÓ`), ámbar (`ENTRÓ Y SALIÓ`).
  Probado con datos sintéticos (los 3 estados salieron correctos) y con un correo real que
  sí entró (`julianaguzman1404@gmail.com`) → `PRESENTE`.
- **Roster completo de la clase, no solo los que faltan:** cada bloque siempre lista a
  TODOS los matriculados del horario resuelto (vía `FILTER` sobre `MATRICULADOS-VIVO`),
  con su estado — no se filtra a solo los ausentes, para que el panel también sirva como
  vista general de la clase.
- Formato condicional verde/rojo por fila; `Abierta desde`/`Última hora` con formato de
  fecha (llegan como serial desde Sheets, no como texto).
- **Auto-limpieza real:** al cerrar la reunión sintética de prueba, el bloque quedó vacío
  solo — sin ningún script de limpieza.

Como todo esto son fórmulas leyendo pestañas que n8n ya escribe en tiempo real vía API,
**se actualiza solo, sin refrescar nada** — mismo mecanismo que ya funciona hoy en
`ZOOM-STATS`.

### Gotcha real encontrado al construirlo (2026-08-03) — el fan-out no siempre dispara

Al conectar `Cerrar Reunion Activa` como un 2°/3er nodo colgado de la MISMA salida de
`Ruteo Evento Zoom` (el Switch) o de `Firma valida?` (el IF) — el patrón de fan-out que
YA usan otros pares de nodos en este mismo workflow (`Responder OK` + `Ruteo Evento Zoom`
desde `Firma valida?`) — el nodo nuevo **nunca se disparaba**, con 5 pruebas sintéticas
seguidas (Switch con 2 nodos, IF con 3 nodos, en distinto orden). La causa real: el
`deactivate`→`activate` que recarga el grafo en memoria (necesario tras cualquier PUT a un
workflow ya activo, ver `docs/convenciones.md`) **tarda más de lo que parece** — con ~10s
de margen seguía fallando, con **30s+ de margen funcionó a la primera**. El fan-out en sí
no tiene ningún límite de nodos; simplemente las pruebas anteriores nunca le dieron tiempo
real al reload antes de disparar el evento sintético.

**Se mantuvo la solución igual (inserción en línea, no en paralelo)** aunque la causa real
resultó ser timing y no un límite de fan-out: es más simple de razonar (no depende de que
2 ramas corran "en paralelo" de verdad) y ya quedó probado funcionando. Documentado igual
por si alguien más se topa con "mi nodo nuevo no corre" después de un PUT — antes de
sospechar de la lógica, esperar 30s+ tras el `activate` y reintentar.

### Limitación real que hay que aceptar (no una limitación de Sheets — de los datos)
El cruce es por **correo**. Si un estudiante entra a Zoom con un correo distinto al
registrado (el mismo problema que resuelve `validar_asistencia.py` con typos y nombre),
el panel en vivo lo va a marcar en rojo aunque sí esté conectado — porque en vivo, con
solo fórmulas de Sheets, no es viable correr la cascada de match completa (typo/nombre)
que sí corre `validar_asistencia.py` en Python una vez al día. **Mitigación v1:** aceptar
el margen de error (consistente con la línea base medida: ~84% correo exacto), el monitor
de todas formas verifica a ojo antes de llamar a alguien. **v2 posible más adelante:**
correr un match más simple (solo nombre) como columna adicional de apoyo, no bloqueante
para este documento.

### Esfuerzo estimado
Medio. Ningún paso es difícil por sí solo (extender un script que ya existe, 2 nodos n8n
del mismo patrón que ya hay 3 veces en este workflow, una función de setup más en un
archivo que ya tiene 2 casi iguales) — la coordinación entre los 3 pasos y la prueba con
una clase real de 2 salas simultáneas es lo que toma tiempo, no la dificultad técnica de
cada pieza.

---

## Sesión 2026-08-15 (sábado) — roster de Sala 1/Sala 2 sin alias 10am + n8n con la cola trabada

Usuario reportó: "el excel esta desactualizado hay clases a las 10:00am y esta con las de las
2:00PM". Dos causas reales, una mucho más grave que la otra.

### Causa 1 — alias de Sala 1/Sala 2 solo apuntaba a las 2pm
`CUPOS` tenía `Alias Zoom` = `"Desarrollo Web - GIT, HTML y CSS - Sala 1"`/`"...Sala 2"` SOLO
en las filas de **2pm** (`f14`/`f15`, puestas ahí el 2026-08-03 cuando se armó Sala1=Uno/
Sala2=Dos para esa franja). Nadie agregó el alias para las 10am porque nunca antes se había
reusado esa sala fija a las 10am. Con 1 sola fila coincidiendo por topic, el score-based
tiebreak del 2026-08-12 ni se activaba (la rama de conteo=1 gana directo) — resolvía siempre
a 2pm sin importar el día real.

**Fix:** roster de "HTML - Sábado 10:00 A.M." (56 personas, sin split Uno/Dos a diferencia de
2pm) — agregado el alias `Sala 1` a `CUPOS!D5` (fila ya existente) y una fila NUEVA (`A92`)
con el mismo texto de Clase que `f5` pero alias `Sala 2`, para que ambas resuelvan a la misma
foto de roster. Confirmado con el fix de puntaje de día+hora: ambas salas ahora resuelven
correctamente a sábado 10am.

**Apareció una 3ª sala en vivo durante el diagnóstico** (`2npJoNcXRVy5nyW34RlnrA==`, topic
PLANO `"Desarrollo Web - GIT, HTML y CSS"` — el mismo link recurrente de miércoles/jueves
10am, reusado hoy como sala extra). Como ese topic ya tenía alias en miércoles Y jueves pero
NINGUNA fila sábado, el score-tiebreak cayó en un empate (mismo puntaje +1000 para ambos, hora
igual) y ganó Jueves por orden de fila — **primer caso real de "0 filas con el día correcto
entre las que comparten topic"**, un hueco que el fix de puntaje del 2026-08-12 no cubría
(solo desambiguaba ENTRE candidatos existentes, no avisaba si ninguno era del día real).
Mitigado agregando también el alias sábado para ese topic (`CUPOS!A93`, mismo roster de 56).
**Pendiente de diseño (no arreglado, es de fondo):** la fórmula debería avisar explícitamente
("SIN HORARIO PARA ESTE DÍA") en vez de degradar a un empate silencioso cuando NINGÚN
candidato coincide con el día real — hoy solo se mitigó agregando la fila que faltaba, caso
por caso, no se cerró la clase de bug en general.

**Limitación estructural descubierta (sin resolver, doc para decidir después):** hoy hubo 3
salas de Zoom simultáneas para el mismo horario de las 10am, pero el panel fija 1 bloque POR
CUENTA (comunicaciones/jovenescreativos = 2 slots). Con 2 salas bajo la MISMA cuenta
(`comunicaciones`: Sala 1 + la sala nueva), el diseño "más reciente gana el slot" deja una de
las 2 invisible en el panel — aunque ambas compartan el mismo roster correcto, no se puede ver
QUIÉN específico está en cada una desde el panel (sí queda en `LIVE-LOG` para reportes). No se
tocó en caliente durante la clase — decisión de rediseño pendiente si esto se repite.

### Causa 2 — MUCHO más grave: n8n con la cola de ejecuciones trabada ~2h

Al investigar, `LIVE-LOG` no tenía nada nuevo desde las 8:26am (eran las 10:36 al notarlo).
`GET /executions` mostraba **TODAS** las ejecuciones recientes (webhook Y schedule trigger,
de CUALQUIER workflow) con `status:"new"` y `startedAt:null` — la cola de ejecución de la
instancia completa de n8n estaba trabada, no solo el workflow de Zoom. `healthz` seguía
respondiendo `{"status":"ok"}` todo este tiempo — **el watchdog automático de
`iniciar_n8n.bat` no puede detectar esta falla** porque solo verifica `healthz`, nunca el
estado real de la cola. Mismo patrón que el gotcha ya documentado ("n8n suspend/resume") pero
nunca antes confirmado con evidencia de ejecuciones "new" — ahora sí queda documentado con
prueba dura.

**Impacto real, sin poder recuperarse:** `jovenescreativos` (Sala 2) sin actividad desde las
**9:24am** — esa asistencia real de ~1h20 de clase probablemente no se capturó. Irrecuperable.

**Reinicio manual — bug nuevo encontrado en `iniciar_n8n.bat` (2026-08-15):** al lanzar el
`.bat` desde una consola no interactiva (sin TTY real), `timeout /t N` y `start /B` fallan con
`"ERROR: No es compatible la redirección de entradas, saliendo inmediatamente del proceso."`
— consistentemente, en cada invocación. Como `timeout /t 60` en el loop del watchdog (línea
`:loop`) falla y retorna AL INSTANTE en vez de esperar 60s, el watchdog "auto-heal" se disparó
cada ~8 segundos en vez de cada 60s, matando **cualquier proceso `node.exe` con "n8n" en su
línea de comando** en cada vuelta — lo que además mataba mis propios intentos de reinicio
manual antes de que llegaran a levantar. **El `.bat` en sí sigue sirviendo perfecto desde una
ventana normal/interactiva** (así lo usa el equipo siempre) — el bug es específico de
lanzarlo vía automatización sin consola real. **Mitigación aplicada:** reinicio manual
reemplazando `start /B`/`timeout` por `Start-Process`/`Start-Sleep` (equivalentes que sí
funcionan sin consola) — replicando a mano las mismas variables de entorno que el `.bat` lee
de `scripts/q10-consolidacion/.env` + `scripts/zoom-asistencia/.env`. Verificado: `healthz`
OK, los 5 workflows activos siguen `active:true` tras el reinicio (atributo persistido, no se
pierde), y las ejecuciones nuevas ya muestran `status:"success"` reales cada 30-45s.
**Sin watchdog corriendo para el resto del día** (2pm/4pm) — no se dejó ningún proceso
vigilando tras el reinicio manual, a diferencia de correr el `.bat` completo (que si hubiera
funcionado, deja el loop `:loop` corriendo). Pendiente: si vuelve a pasar, alguien con acceso
físico a la PC debería correr `iniciar_n8n.bat` desde una ventana normal (ahí sí funciona el
watchdog completo).

## Decisión de diseño — ¿Sheets, WordPress, o una app real? (2026-08-12, sin ejecutar)

Pregunta del usuario: ¿es Sheets la vista óptima, o más simple un sitio en WordPress alojado
en `tocaunavida.org`? Respuesta: **ninguna de las dos como destino final.**

- **Sheets fue la elección correcta para la fase de testeo** (2026-08-03 en adelante) — cero
  infra nueva, ciclo de iteración de minutos (demostrado hoy: ~6 recreaciones del panel en un
  día). Pero ya muestra el techo: la MISMA lógica vive duplicada en 2-3 sitios (fórmula del
  panel / `resolver_horario()` Python / columnas de `monitor_panel_vivo.py`) y se desincroniza
  en silencio con cada cambio de layout — pasó 2 veces el mismo 2026-08-12. Además
  naranja/gris/celular/ciudad dependen de un cron de 5 min (Camino B), no de verdad en vivo, y
  se copia PII de Supabase HACIA Sheets por un puente — arquitectura al revés.
- **WordPress/`tocaunavida.org` NO es el destino correcto** — es un sitio PÚBLICO (marketing,
  Elementor); meter ahí una herramienta con PII de estudiantes (correo/celular/ciudad) choca
  directo con la regla ya existente del proyecto ("PII nunca a GitHub/público"). Es además un
  CMS, no un framework de app — pelearía contra caché de páginas y necesitaría auth desde cero.
- **El destino correcto, cuando el diseño se estabilice:** una vista nueva de
  `panel-datos-rofe` (Next.js + Supabase, ya en producción, ya resolvió auth/acceso, ya es la
  fuente real de celular/ciudad) — no un sitio aparte. Ver [[panel-datos-etl]].
- **No migrar todavía:** falta terminar de validar el diseño con clases reales (el test de las
  6pm de hoy es parte de eso) — migrar antes de estabilizar el diseño trasladaría la
  incertidumbre a un stack más caro de iterar, perdiendo justo la ventaja que Sheets sí dio hoy.

## Decisiones de diseño clave
- **Separar en 2 fases** en vez de una sola hoja — tienen requisitos de frescura opuestos
  e incompatibles (diario vs. segundos).
- **`CUPOS` no es el roster, y Supabase tampoco** (corregido 2026-08-03) — Supabase solo
  matricula a nivel de curso completo, no por horario/subgrupo. El roster real por sala
  sale de la BD Seguimiento (`Horario *` + `E-mail`), el mismo archivo que ya lee
  `analizar_cupos_bd.py` para `CUPOS` — mismo dato, mismo script, una columna más.
- **Detectar "clase en vivo" sin depender de `meeting.started`** — ese evento hoy no llega
  de forma confiable (ver incidente 2026-07-30 en [[zoom-asistencia]]); usar el primer
  `participant_joined` de un UUID nuevo como señal de apertura es más robusto porque ese
  evento sí se ha visto llegar consistentemente.
- **Marcar `REUNIONES-ACTIVAS` como cerrada, no borrarla** — evita depender de ubicar el
  número de fila exacto para un `delete`; el `FILTER` del panel ya la ignora igual.
- **Reusar la cascada de resolución de `CUPOS`** (nombre exacto → alias → horario) para
  decidir el roster de cada bloque del panel — ya existe, ya está probada hoy con el caso
  real de Sala 1/Sala 2, no hace falta una segunda lógica de negocio.
- **El panel en vivo no reemplaza a `ASISTENCIA-VALIDADA`** — es un vistazo rápido y
  aproximado durante la clase; la fuente de verdad para reportes y Supabase sigue siendo
  la validación diaria.

## Pendiente / Próximos pasos
- [x] Fase 1: construir `ZOOM-STATS-VALIDADO` (2026-08-03) — falta correrla en paralelo a
  `ZOOM-STATS` un tiempo antes de decidir si la reemplaza.
- [x] Fase 2, paso 1: `tools/analizar_cupos_bd.py` extendido + `MATRICULADOS-VIVO`
  construida (2026-08-03) — 5.319 asignaciones horario-estudiante, 89 horarios.
- [x] Fase 2, paso 2: 4 nodos nuevos en el workflow `Zoom - Asistencia`
  (`Detectar Apertura Reunion`, `Abrir en REUNIONES-ACTIVAS`, `Cerrar Reunion Activa`,
  `Cerrar en REUNIONES-ACTIVAS`) — probados con eventos sintéticos, abre/cierra/dedup OK.
- [x] Fase 2, paso 3: `construir_panel_en_vivo()` en `setup_zoom_asistance.py` — hoja
  `PANEL-EN-VIVO` con 2 bloques (Sala A/B), fórmulas de cruce + formato condicional,
  probada con datos sintéticos y un correo real.
- [x] Probar la Fase 2 con clases reales (2026-08-05) — a diferencia del intento del
  2026-08-03, hoy sí llegó tráfico real del webhook (`LIVE-LOG`/`REUNIONES-ACTIVAS` con
  nombres/correos reales). Ver bug encontrado y corregido abajo. Sigue pendiente confirmar
  con Lina/monitores que vieron el panel correcto durante una clase completa.
- [x] Limpieza automática de `LIVE-LOG` (2026-08-04): `limpiar_live_log.py` corrido
  manualmente (801 filas borradas) + agendado en n8n (`Diario 21:00 -- Limpiar LIVE-LOG`
  → `Limpiar LIVE-LOG`, cron `0 21 * * *`) — ver sección abajo. **`MATRICULADOS-VIVO` NO
  se toca** — es un snapshot estático (5.319 filas, todo el roster de los 89 horarios), no
  un log que crece.

### Bug corregido — reunión sin cerrar bloqueaba el panel para siempre (2026-08-05)

**Encontrado** al verificar el panel en vivo contra una clase real de hoy: `PANEL-EN-VIVO`
tomaba la **1ª/2ª fila** de `REUNIONES-ACTIVAS` con `Activo=TRUE` en orden de aparición en
la hoja (`INDEX(FILTER(...), 1/2)`), no por recencia. Una reunión del 2026-08-04 18:18
nunca recibió el evento de cierre (mismo gotcha ya documentado: `meeting.ended` no llega si
alguien queda conectado sin salir) y se quedó con `Activo=TRUE` indefinidamente. Como era la
fila más antigua con `Activo=TRUE`, ocupaba el slot "SALA A" **para siempre**, mostrando
`SIN ALIAS -- agregar Alias Zoom en CUPOS` y sin roster — mientras 2 clases reales de hoy
(comunicaciones 10:00, jovenescreativos 11:47) quedaban invisibles para los monitores.

**Corrección:** `bloque_sala()` en `construir_panel_en_vivo()` (`setup_zoom_asistance.py`)
ahora ordena las reuniones activas por `Apertura` **descendente** antes de tomar la 1ª/2ª
(`SORT(FILTER(REUNIONES-ACTIVAS!$A:$D, Activo=TRUE), 4, FALSE)` en vez de `FILTER` sin
ordenar). Confirmado que `Apertura` se guarda como serial de fecha real (no texto), así que
el `SORT` numérico ordena correctamente incluso con horas sin cero a la izquierda
("9:49" vs "10:00"). Aplicado en 2 lugares: el código fuente (para toda futura recreación
del panel) y directamente sobre las 8 celdas de fórmula en vivo (`B2:B5` Sala A, `B235:B238`
Sala B) — **sin** recrear `REUNIONES-ACTIVAS` ni `PANEL-EN-VIVO` (`recrear()` borra la
pestaña completa; hacerlo mientras hay una clase real escribiendo en vivo habría perdido
esas filas). Verificado: la reunión zombie desapareció del panel, que ahora muestra las 2
reuniones más recientes.

**Limitación que queda (no es un bug, es el límite de diseño ya documentado):** el panel
sigue asumiendo máximo 2 reuniones simultáneas. Si hay más de 2 filas con `Activo=TRUE` al
mismo tiempo (una clase real + una reunión de staff que tampoco cerró + una reunión de
prueba nueva, visto en vivo el mismo 2026-08-05), las 2 más recientes ganan el slot aunque
no sean clases reales — una reunión de prueba ("TEEEEEEEEEEEEEEEEEST") desplazó a una clase
real del panel minutos después de aplicar el fix. Mitigación futura posible: excluir del
`FILTER` los topics que no resuelven a ningún horario de `CUPOS` (ya se distinguen con
"Horario resuelto" = "SIN ALIAS...") antes de ordenar, para que ruido/pruebas no compitan
por el slot con una clase real. No implementado todavía — no se pidió, y cambia el
comportamiento cuando SÍ hay una clase real sin alias configurado (hoy eso también avisa en
vez de fallar en silencio).

### Rediseño — bloques fijos por cuenta, no "Sala A/B" genérico (2026-08-05)

**Pedido de Lina:** dejar visibles a la vez el panel de `comunicaciones` y el de
`jovenescreativos`, cada uno con colores que los distinga fácilmente.

**Por qué esto también resuelve el problema real detectado antes de este cambio:**
"SALA A/B" tomaba las 2 reuniones `Activo=TRUE` más recientes **sin mirar el host** — una
reunión de prueba o de staff en cualquiera de las 2 cuentas podía desplazar a una clase real
del panel (visto en vivo el mismo día: "Mi reunión" y "TEEEEEEEEEEEEEEEEEST" ocuparon los 2
slots mientras la clase real de `comunicaciones` seguía abierta). Un bloque **fijo por
cuenta** elimina esa competencia: cada cuenta siempre muestra su propia reunión más reciente,
sin que le importe lo que pase en la otra.

**Cambio:** `construir_panel_en_vivo()` ahora arma 2 bloques fijos —
`🟡 COMUNICACIONES` y `🔵 JÓVENES CREATIVOS` — cada uno con
`SORT(FILTER(REUNIONES-ACTIVAS!$A:$D, Activo=TRUE, Host="<cuenta>"), 4, FALSE)` (agrega el
filtro por `Host` a la fórmula de recencia del fix anterior). Colores reusados de
`colorear_por_host.py` (amarillo `#FFE599`/texto café para comunicaciones, azul `#9FC5E8`/
texto azul oscuro para jovenescreativos) — misma convención que ya existe en la columna
`Host` de `ZOOM-ASISTANCE`/`ASISTENCIA-10MIN`, para que se reconozca de inmediato. La franja
de color cubre el título + las 5 filas de metadata (UUID/Topic/Host/Abierta desde/Horario
resuelto) + el header de la tabla — el cuerpo del roster se deja sin tintar, para no competir
con el color de presencia (verde/rojo/ámbar) que es lo que importa ahí.

**Aplicado:** recreando `PANEL-EN-VIVO` directamente con `construir_panel_en_vivo(sh)` — a
diferencia de `REUNIONES-ACTIVAS`/`LIVE-LOG`, esta pestaña es 100% fórmulas derivadas (no
tiene ningún dato propio), así que recrearla no pierde nada aunque haya una clase real
corriendo. Verificado con la API que el color de fondo quedó aplicado (amarillo en A1, azul
en A234) y que cada bloque muestra la reunión correcta de su cuenta.

**Layout horizontal (2026-08-05, mismo día, pedido de Lina):** los 2 bloques pasaron de
estar uno debajo del otro (comunicaciones en filas 1-233, jóvenes en 234-461) a estar
**lado a lado en la misma fila 1** — comunicaciones en columnas A:D, jóvenes creativos en
F:I, con la columna E como separador angosto (20px). Motivo: ver ambas cuentas sin
scrollear 461 filas hacia abajo. `bloque_host()` cambió su parámetro de "fila donde
arranca" a "columna donde arranca" (`col_letra()` nuevo, convierte índice 1-based a letra
de columna); toda referencia de celda dentro del bloque (`$B{fila}` → `${cV}{fila}`, etc.)
se generalizó a la letra de columna que le toque a cada bloque. Se agregó
`frozenRowCount: 8` (título + metadata + header de tabla quedan fijos al hacer scroll por
el roster de 220 filas). Sheet ahora es ~235 filas x 10 columnas en vez de ~461 x 4.

**Bug de "Mi reunión" no capturada — causa real (2026-08-05):** no era un bug del panel ni
del workflow — fue un efecto secundario de una limpieza manual anterior en la misma
sesión: se había marcado `Activo=FALSE` en `REUNIONES-ACTIVAS` para la fila de "Mi
reunión" (UUID `g9GTFh75QhKBN9knfXK73Q==`) pensando que era ruido de una prueba aislada,
sin saber que se seguiría usando esa misma sala. Como `Detectar Apertura Reunion` solo
escribe **una vez por UUID en toda la vida del proceso** (usa
`$getWorkflowStaticData('global')` para no gastar cuota de Sheets en cada
`participant_joined/_left`), un cierre manual de una sesión que sigue viva **no se
autocorrige** — nada en el flujo la va a reabrir. Fix: reabrir la fila a mano
(`Activo=TRUE`) para ese UUID específico. **Lección para no repetirlo:** antes de marcar
una fila de `REUNIONES-ACTIVAS` como cerrada "por ruido", revisar primero si `LIVE-LOG`
tiene actividad reciente en ese UUID.

**Prueba de roster en vivo con "Mi reunión" (2026-08-05) — validado y limitación real
documentada.** Para que Lina pudiera ver el mecanismo completo (roster → verde al entrar),
se puso un Alias Zoom **temporal** en `CUPOS` fila 13 (`"Mi reunión"` → `HTML - Miércoles
6:00 P.M.`, 51 inscritos) — quitado al terminar la prueba, `CUPOS!D13` vacío de nuevo.
Durante la prueba se confirmó una limitación real, no un bug: al unirse a Zoom **como
invitado sin cuenta**, la pantalla solo pide **nombre**, no correo — y el cruce del panel
es estrictamente por correo (`LIVE-LOG!Correo` contra `MATRICULADOS-VIVO!Correo`), a
propósito, para no inventar coincidencias por nombre parecido (ver "Limitación que hay que
aceptar" más arriba). Un invitado sin correo (como los intentos de esta prueba,
`Correo` vacío) **nunca** va a marcar una fila del roster como presente, sin importar el
nombre que escriba. Para validar el cruce en vivo end-to-end haría falta: (a) entrar
logueado con una cuenta de Zoom cuyo correo esté en el roster real, o (b) activar
"Requerir registro" en la reunión (pide correo también). Se optó por **no** hacer ninguna
de las 2 y confiar en la evidencia ya real de hoy: decenas de estudiantes reales entraron
hoy a "Desarrollo Web - GIT, HTML y CSS" con su correo real capturado correctamente en
`LIVE-LOG` — el cruce por correo ya está demostrado funcionando en producción.

### Auto-cierre de reuniones inactivas (2026-08-05) — resuelve el "zombie" de raíz

El fix de recencia (SORT por Apertura) y el de bloques-por-cuenta reducen el impacto de una
reunión sin cerrar, pero no lo eliminan: **si es la ÚNICA reunión activa de su cuenta**, sigue
ganando el slot aunque tenga horas de silencio — pasó 2 veces el mismo día (la reunión
zombie original del 2026-08-04, y otra vez con la sala de `comunicaciones` de las 10:00am
que seguía `Activo=TRUE` a las 5pm con solo 2 eventos sueltos de las 10:04am). Cada vez
requería cierre manual mío.

**Solución de fondo:** `scripts/zoom-asistencia/cerrar_reuniones_inactivas.py` — recorre
`REUNIONES-ACTIVAS`, calcula para cada fila `Activo=TRUE` la hora del último evento real en
`LIVE-LOG` (columna `HoraMs`, epoch ms — no depende del locale/timezone de la columna de
texto), y marca `Activo=FALSE` si pasaron más de `--umbral-horas` (default 3h) sin
actividad. Respaldo si `LIVE-LOG` ya no tiene el historial de esa reunión (p.ej. lo borró
`Limpiar LIVE-LOG` a las 21:00): usa `Apertura` en su lugar. Soporta `--dry-run`.

**Agendado en n8n (2026-08-05):** 2 nodos nuevos en el workflow `Zoom - Asistencia`
(`jkNaE51PKQ4TQzNq`, ahora 33 nodos) — `Cada hora -- Cerrar reuniones inactivas`
(`scheduleTrigger`, cron `0 * * * *`) → `Cerrar reuniones inactivas` (`executeCommand`),
mismo patrón que `Diario 21:00 -- Limpiar LIVE-LOG`/`Limpiar LIVE-LOG`. A diferencia de la
limpieza de `LIVE-LOG` (que solo corre de noche porque no afecta nada durante el día), este
corre **cada hora** porque el problema sí afecta el panel en vivo mientras hay clases reales
en curso. Aplicado por API siguiendo el patrón de `docs/convenciones.md` (PUT con solo
`name/nodes/connections/settings`, luego `deactivate`→`activate` obligatorio para que el
Schedule Trigger nuevo quede registrado) — verificado `active: true` y los 2 nodos
presentes en el workflow en vivo tras el ciclo. Probado antes de agendar: `--dry-run` sobre
una fila zombie simulada (la del 2026-08-04) la detectó correctamente (22.1h sin actividad),
luego corrido real para confirmar que sí escribe.

### Crecimiento sin límite de `LIVE-LOG` (encontrado 2026-08-04)

`LIVE-LOG` sí crece sin control — una sola reunión de ~1.5h con ~60 personas generó 801
filas de `joined`/`left`. No es un problema de `MATRICULADOS-VIVO` (ese es un snapshot fijo
de 5.319 filas — el roster completo de los 89 horarios, reconstruido solo cuando alguien
corre `analizar_cupos_bd.py` de nuevo, no crece con el tráfico de clases). El buffer que sí
hay que vaciar a diario es `LIVE-LOG`: no se necesita después de que cierra la clase (el
dato permanente ya quedó en `ZOOM-ASISTANCE`/`ASISTENCIA-10MIN` por otro camino), y
`PANEL-EN-VIVO` solo consulta contra el UUID de la reunión activa del momento, así que
vaciarlo a diario no rompe nada. Script listo:
`scripts/zoom-asistencia/limpiar_live_log.py` (mismo patrón de conexión que los demás
scripts de esta carpeta, `ws.batch_clear()` conservando el encabezado) — probado
manualmente el 2026-08-04 (borró los 801 registros del día anterior sin tocar el
encabezado). **Agendado 2026-08-04:** nodos `Diario 21:00 -- Limpiar LIVE-LOG`
(`scheduleTrigger`, cron `0 21 * * *`) → `Limpiar LIVE-LOG` (`executeCommand`) agregados
al workflow `Zoom - Asistencia`, mismo patrón que `asistencia-zoom-diario`, verificado en
vivo tras el ciclo deactivate/activate (31 nodos, `active: true`).

### Intento de prueba real (2026-08-03, sin resultado útil) — causa confirmada

Se lanzó un monitoreo en segundo plano para la clase real de las 7pm ("Hackea tu
cerebro", lunes). Resultado: **no llegó ningún evento webhook** entre las 18:29 del
2026-08-03 y las 08:55 del 2026-08-04 (confirmado revisando `LIVE-LOG` y
`GET /api/v1/executions` de n8n directamente). Además el script de monitoreo tenía un bug
de encoding (no podía imprimir el emoji 🟢 del panel en la consola de Windows) que lo hizo
morir antes de la hora de clase — pero esto es secundario, no la causa real.

**Causa real (confirmada 2026-08-04): el portátil probablemente se suspendió esa noche.**
Mismo gotcha ya documentado antes de esta sesión (ver nota "n8n suspend/resume" y
`docs/convenciones.md`): al suspenderse, n8n queda vivo en memoria y `healthz` sigue
respondiendo 200, pero pierde las conexiones de red — el túnel del webhook muere sin que
nada se note hasta que se intenta usarlo. `Get-CimInstance Win32_OperatingSystem` mostró
`LastBootUpTime` de hace 6+ días (sin apagado/reinicio real), consistente con suspensión
más que con apagado total. **Sigue sin validarse con una clase real** — para el próximo
intento, confirmar ANTES de la clase que el portátil está enchufado y sin suspensión
programada (requisito #1 ya documentado), no solo que n8n responda `healthz`.

---

## Sesión 2026-08-06 — primera clase real con monitor en vivo: 2 bugs nuevos + resumen + plan de correos alternos

Primera vez que alguien miró el panel durante una clase real (comunicaciones, HTML jueves
10am) esperando llamar estudiantes con él. Apareció en blanco al abrir — investigado en vivo,
sin interrumpir la clase.

### Bug 1 — UUID reciclado de sala recurrente nunca reabre `Activo`

**Causa:** `Detectar Apertura Reunion` (Code, workflow `Zoom - Asistencia`) usa
`$getWorkflowStaticData('global')` para marcar `reunionesAbiertas[uuid] = true` **una sola vez
en toda la vida del proceso** (para no gastar cuota de Sheets en cada `participant_joined`).
Zoom **reutiliza el mismo UUID** para la sala fija de `comunicaciones` cada semana. La sala se
abrió y cerró bien el 2026-08-05 (`Activo=FALSE` correcto al cerrar). Hoy 2026-08-06 llegaron
`joined` reales nuevos para ese mismo UUID, pero como la bandera en memoria ya estaba en
`true` desde ayer, el nodo nunca volvió a escribir `Activo=TRUE` — el panel seguía viendo esa
sala como "cerrada" mientras había ~35 personas conectadas.

**Fix aplicado (manual, en caliente):** `Activo` puesto a mano en `TRUE` para esa fila de
`REUNIONES-ACTIVAS`. Mismo síntoma raíz que el caso "Mi reunión" del 2026-08-05 (ver arriba),
pero disparador distinto (reutilización semanal de UUID, no un cierre manual erróneo).

**Fix de fondo — pendiente, no aplicado:** la bandera debería expirar por día (clave
`${uuid}:${fecha}` en vez de `${uuid}` a secas) para que una sala recurrente se re-marque
activa cada vez que Zoom la reabre, sin intervención manual. Se decidió NO tocar el workflow
de n8n mientras la clase seguía en vivo — queda para la próxima sesión de mantenimiento.

### Bug 2 — mismo topic de Zoom compartido por 2 horarios distintos, sin alias diferenciado

**Causa:** en `CUPOS`, el `Alias Zoom` `"Desarrollo Web - GIT, HTML y CSS"` estaba fijo a la
fila de **miércoles 10am** (fila 16). La fila de **jueves 10am** (fila 12, 47 matriculados) usa
la misma sala/link de Zoom pero tenía `Alias Zoom` vacío. La cascada de resolución del panel
busca el topic **solo por nombre/alias** (a propósito, sin día+hora — ver diseño arriba), así
que siempre resolvía a miércoles sin importar qué día fuera en realidad. Hoy jueves, el panel
mostraba el roster de miércoles (40 matriculados) contra estudiantes reales del roster de
jueves → 0 coincidencias → **todo el bloque en rojo** a pesar de que la clase sí estaba llena.

**Diagnóstico confirmado con datos reales** (cruce `LIVE-LOG` × `MATRICULADOS-VIVO`, no
supuesto): de los correos conectados hoy, 0 coincidían con el roster de miércoles y 25
coincidían con el roster de jueves.

**Fix aplicado (temporal, ⚠️ hay que revertir antes de la próxima clase de miércoles):**
`Alias Zoom` movido de la fila de miércoles a la fila de jueves en `CUPOS`
(`scripts/zoom-asistencia/...` no tocado, cambio hecho directo en la hoja). **Pendiente real:**
`CUPOS` solo admite un `Alias Zoom` por topic — como este salón se reutiliza para 2 días
distintos, hace falta una forma de que la resolución del panel considere también el día/hora
del evento entrante (`Apertura` de `REUNIONES-ACTIVAS`) contra `CUPOS!Día`/`CUPOS!Hora`, no
solo el nombre del topic. No implementado — diseño a definir en la próxima sesión de
mantenimiento (probablemente junto con el fix de Bug 1, mismo viaje al código).

### Rediseño — resumen de conteo rápido + indicador de actividad viva (aplicado 2026-08-06)

Pedido explícito: un conteo rápido de Presentes/Nunca entró/Entró y salió al lado de cada
tabla, sin tener que contar filas a ojo, y una forma de confirmar que el panel sigue vivo (no
congelado) sin esperar a que alguien note que un número no se mueve.

**Cambio en `construir_panel_en_vivo()` (`setup_zoom_asistance.py`):** cada bloque pasó de 4
columnas (roster) + 1 de separación a 4 (roster) + 2 (resumen) + 2 (separación) = 8 — el efecto
neto es que `jovenescreativos` quedó **3 columnas más a la derecha** que antes (de la columna F
a la I), que además resuelve el pedido explícito de que dejara de chocar visualmente con
`comunicaciones` (nombres largos del roster desbordaban sobre el gutter angosto de antes).

Resumen por bloque (fórmulas, mismo mecanismo de recálculo automático que el resto del panel):
- 🟢 Presentes / 🟠 Entró y salió / 🔴 Nunca entró — `COUNTIF` sobre la columna Estado del
  roster.
- Total matriculados — `COUNTA` sobre la columna Correo del roster (excluye la fila de aviso
  "sin roster" cuando no hay horario resuelto).
- 🕐 **Última actividad** — el evento más reciente (`joined`/`left`) de `LIVE-LOG` para el UUID
  activo de esa cuenta. Es el indicador de "esto sigue vivo": si esa hora no avanza mientras
  hay gente conectada, hay algo roto (webhook caído, n8n suspendido) antes de que alguien se
  dé cuenta por otra vía.

Aplicado con `construir_panel_en_vivo(sh)` llamado directo (no vía `--solo-panel-vivo`, que
también recrea `REUNIONES-ACTIVAS` y habría perdido el estado de la clase en curso). Verificado
en vivo con la clase real: comunicaciones mostró 26 Presentes / 1 Entró y salió / 20 Nunca
entró / 47 Total matriculados / última actividad avanzando minuto a minuto.

### Discrepancia "matriculados": 42 (equipo) vs 47 (panel) — explicada, no es un bug

`MATRICULADOS-VIVO` es una foto fija de la BD Seguimiento tomada el **2026-08-03**. En los 3
días entre esa foto y la clase de hoy, es esperable que 5 personas hayan sido retiradas o
cambiadas de horario — de ahí el 47→42. Es la misma limitación ya aceptada desde que se
construyó esta pieza ("tan fresco como la última vez que alguien corrió
`analizar_cupos_bd.py`"), simplemente hoy se sintió por primera vez con un número concreto en
frente. Fix: volver a correr `tools/analizar_cupos_bd.py` con una BD Seguimiento fresca +
`setup_zoom_asistance.py --solo-matriculados-vivo` cuando haya una copia actualizada a mano —
no se hizo hoy porque no había una BD Seguimiento nueva disponible en el momento.

### Discrepancia "presentes": 26 (panel) vs 36 (Zoom en vivo) — cuantificada con datos reales

Cruce `LIVE-LOG` × `MATRICULADOS-VIVO` en el momento:

| | Cantidad |
|---|---|
| Conectados según Zoom | 36 |
| Correos únicos que `LIVE-LOG` alcanzó a capturar | 32 |
| De esos, coinciden con el roster (= "26 Presentes" del panel) | 26 |
| Conectados sin match en el roster | 6 (1 es la cuenta institucional, correcta al excluirse;
5 son casi seguro estudiantes reales con correo distinto al registrado) |

Confirma en producción, con números reales, la limitación ya documentada arriba ("el cruce es
por correo... ~84% correo exacto medido antes") — hoy dio 26/32 = 81%, consistente. El resto
del gap (36 Zoom vs 32 capturados por `LIVE-LOG`) es probablemente rezago de webhook o
duplicado por dispositivo, no pérdida de datos real.

### `/consejo-medio` — identificar correos no coincidentes en vivo ("ponerlos en rosado")

Propuesta evaluada: detectar en el panel a quien está conectado sin match de correo, marcarlo
con un color nuevo para que el monitor le pida cambiar el correo en vivo, y si no es posible,
que llene un Forms con su info de Q10 para investigar el caso y decidir si ese correo alterno
debe tenerse en cuenta en futuras clases y en los análisis de base de datos.

**Veredicto: Adelante con ajustes — no aplicar todavía.** El riesgo más señalado por el
escéptico (subagente aislado) fue tocar el panel en vivo, recién estabilizado ese mismo día,
para agregar una lógica de detección inversa (buscar quién NO está en el roster sobre una
lista que crece en tiempo real) — mismo tipo de fragilidad que ya causó los bugs 1 y 2 de
hoy. El segundo riesgo, más determinante: **un Forms sin un lugar definido donde aterrizar la
respuesta es trabajo que se pierde** — el mismo estudiante volvería a salir sin match la
próxima clase. Condiciones antes de aplicar (ver plan abajo): no tocar el color del panel en
vivo durante una clase real; definir primero el destino en Supabase del correo alterno y el
script que lo ingiere; Forms con acceso restringido (PII de menores/jóvenes — datos de Q10);
preguntar la causa en el Forms en vez de asumir "typo" como única explicación.

### Plan: correos alternos — EJECUTADO 2026-08-06 (pasos 1, 3, 4; paso 2 manual pendiente; paso 5 incremental)

Autorizado a ejecutar el mismo día ("aún es una herramienta en testeo, no hay problema") —
sin esperar a una clase real para probar cada pieza.

**Duda respondida primero (bloqueaba diseñar el resto): ¿la base de datos ya está adaptada a
correos secundarios?** No, verificado contra el esquema real de Supabase antes de construir
nada: `participants.email`, `postulantes_jc.email`, `postulantes_mr.email` eran una sola
columna `character varying`, sin tabla equivalente a `ciudad_alias` para correos. Cerrado con
el paso 1.

**1. Tabla `correo_alias` en Supabase — APLICADA.**
`docs/migrations/041_correo_alias_APLICADA.sql`: tabla `correo_alias` (`correo_norm` PK,
`participant_id` FK → `participants.id`, `fuente`, `nota`, `creado_en`) + funciones
`normalizar_correo()` y `correo_a_participante()` (mismo patrón que
`normalizar_ciudad()`/`ciudad_canonica()`). RLS activo, sin policy — solo `service_role`,
igual que `email_bounces`/`email_optout`. Verificado tras aplicar: `relrowsecurity=true`,
`0` policies, `correo_a_participante()` responde `NULL` para un correo desconocido.

**2. Forms de identificación de caso — PENDIENTE, creación manual** (sin herramienta de API
de Google Forms disponible en este entorno). Texto exacto a copiar/pegar al crearlo — ver
sección "Forms — texto exacto para crear" más abajo. Al crearlo, Google Forms genera
automáticamente un Sheet de respuestas — su ID va en `SHEET_ID_FORMS` de
`sync_correo_alias.py` (paso 3) antes de poder correrlo.

**3. Script de ingesta — LISTO, sin poder correr aún** (depende del paso 2).
`scripts/panel-datos/sync_correo_alias.py`: lee las respuestas del Forms, resuelve
**cédula → `participants.q10_id`** (no nombre parecido — mismo criterio que el resto de la
base), upsert a `correo_alias` por `correo_norm` (idempotente), y al terminar refresca
`CORREO-ALIAS` en el panel automáticamente (llama a
`setup_zoom_asistance.py --solo-correo-alias`). Cédulas sin match se reportan aparte, nunca se
adivinan. Falla rápido y claro si `SHEET_ID_FORMS` sigue vacío (probado: exit 1 con mensaje).
Módulo compañero `scripts/panel-datos/correo_utils.py` (mismo patrón que `ciudad_utils.py`)
para cualquier otro script que necesite resolver un correo alterno sin repetir el cliente REST.

**4. Panel en vivo — APLICADO y probado con datos sintéticos.**
- `construir_correo_alias()` nueva en `setup_zoom_asistance.py` (`--solo-correo-alias`):
  lee `correo_alias` + `participants.email` de Supabase, escribe la pestaña `CORREO-ALIAS`
  (`CorreoAlterno | CorreoOficial | Nombre | Nota`) — el puente que sí pueden leer las
  fórmulas del panel (no pueden llamar a Supabase directo). Vacía mientras nadie ha llenado
  el Forms — eso es el estado normal ahora mismo, no un error.
- `construir_panel_en_vivo()` extendido: el cruce de cada fila del roster ahora acepta
  también un match vía `CORREO-ALIAS` (`ARRAYFORMULA(IFERROR(VLOOKUP(...)))` dentro de
  `SUMPRODUCT`/`FILTER`, degrada exactamente al comportamiento anterior si `CORREO-ALIAS`
  está vacía). Estado nuevo: `PRESENTE (correo alterno)` / `ENTRÓ Y SALIÓ (correo alterno)`
  — **solo** cuando no hay ningún evento con el correo exacto del roster, para no relabelear
  presencia normal. Color 🩷 rosado (`#f3d1e0`) nuevo en la conditional formatting. Resumen
  con una fila más: "🩷 Vía correo alterno".
- **Probado end-to-end con datos 100% sintéticos** (no con una coincidencia real por nombre
  parecido — eso es justo lo que este diseño evita): fila de prueba en `CORREO-ALIAS`
  + evento `joined` de prueba en `LIVE-LOG` con un correo inventado → la fila de un
  estudiante del roster pasó de `NUNCA ENTRÓ` a `PRESENTE (correo alterno)`, con el fondo
  rosado confirmado vía API (`effectiveFormat.backgroundColor` = `#f3d1e0`) y el contador
  del resumen subiendo a 1. Datos de prueba eliminados de `CORREO-ALIAS` y `LIVE-LOG`
  inmediatamente después — el estado real volvió a 0 correos alternos.

**5. Retroalimentación a los demás análisis de BD — incremental, no de una sola vez.**
`correo_utils.py` (paso 3) ya es reusable desde cualquier script; conectar cada análisis que
cruza por correo (`sync_emoflow_api.py`, validación de asistencia diaria, etc.) contra
`correo_alias` se hace uno a la vez, a medida que se toque ese script — mismo criterio con el
que `ciudad_alias` se fue adoptando en la base, no un cambio simultáneo a todo.

#### Forms — texto exacto para crear (paso 2, manual)

**Título:** Correo distinto en clase — identificación de caso
**Acceso:** restringido (NO "cualquiera con el enlace" — limitar a cuentas del dominio de la
organización o a quienes reciban el enlace directo del monitor).
**Preguntas (usar este texto EXACTO — `sync_correo_alias.py` lee por el nombre literal de la
pregunta):**
1. *Cédula/documento de identidad (el mismo con el que te inscribiste)* — respuesta corta,
   obligatoria.
2. *Nombre completo* — respuesta corta, obligatoria (solo para verificación visual, no la usa
   el script).
3. *Correo con el que entraste a esta clase de Zoom* — respuesta corta, obligatoria.
4. *¿Por qué entraste con este correo y no con el que tienes registrado?* — párrafo,
   obligatoria (evita asumir "typo" como única causa — cuenta compartida, correo de un
   familiar, etc. quedan registrados en texto libre para revisión humana).

Al crear el Forms, abrir la pestaña "Respuestas" → ícono de Sheets → "Crear hoja de cálculo" →
copiar el ID de esa nueva hoja (de la URL) y pegarlo en `SHEET_ID_FORMS` de
`scripts/panel-datos/sync_correo_alias.py`.

---

## Sesión 2026-08-12 — "no identifica nada" en vivo: Bug 2 reincidente + feature naranja/gris (Camino B)

Reportado en testeo: "no se está actualizando ni identificando nada". Diagnóstico en vivo
mientras había una clase real corriendo (miércoles 10am, `jovenescreativos`).

### Diagnóstico — la infraestructura NO era el problema
n8n `healthz` OK, ngrok con 50 conexiones, workflow `jkNaE51PKQ4TQzNq` activo (33 nodos) con
ejecuciones `success` por webhook cada 1-2 min, `LIVE-LOG` creciendo con correos reales
(tatiana555rojas@, juandrubiom@, …). La captura funcionaba; el fallo estaba 100% en la
resolución del roster.

### Causa 1 — Bug 2 REINCIDENTE (topic compartido mié/jue, resolución solo por nombre)
El topic `"Desarrollo Web - GIT, HTML y CSS"` lo comparten **miércoles 10am** (`CUPOS` fila 16)
y **jueves 10am** (`CUPOS` fila 12). `CUPOS` solo admite un `Alias Zoom` por topic, y la
cascada de resolución del panel busca **solo por nombre/alias, sin día** → el miércoles cargaba
el roster del **jueves** → 0 coincidencias → todo `NUNCA ENTRÓ`. Mismo bug del 2026-08-06, que
nunca tuvo arreglo de fondo (queda como pendiente: resolución por día+hora).

**Hotfix aplicado (idéntico patrón al 2026-08-06):** mover el `Alias Zoom` de `CUPOS!D12`
(jueves) a `CUPOS!D16` (miércoles). El panel re-resolvió solo a "HTML - Miércoles 10:00 A.M." y
pasó de **0 → 11 presentes** identificados. ⚠️ **Hay que revertir a `D12` antes de la clase de
jueves** o esa clase se rompe (el whack-a-mole semanal que el arreglo de fondo eliminaría).

### Causa 2 — bloque comunicaciones en blanco
Su reunión de las 10:01 (`In+vGxL/...`) quedó `Activo=FALSE` con último evento ~10:04; a esa
hora no había una clase de comunicaciones activa, así que el bloque en blanco era **correcto**,
no siempre un bug. (Si más adelante entra tráfico y sigue `Activo=FALSE`, ahí sí sería Bug 1 —
UUID reutilizado que la bandera en memoria no re-marca; sigue pendiente su fix de fondo.)

### Feature nueva — naranja (nombre) / gris (sin identificar), Camino B
Pedido: a quien **identifiquemos por nombre pero entró con correo equivocado** marcarlo
**naranja** (acción: pedir el correo de Q10 o llenar el Forms); a quien **no identifiquemos ni
por nombre ni por correo** marcarlo **gris oscuro** (contactar ya). Y — clave — **agregar al
panel a quienes ingresaron y no están en el roster** (hoy son invisibles).

**Decisión: Camino B (helper Python).** El match por nombre laxo (normalizar acentos/mayúsculas
+ solapamiento de ≥2 tokens de ≥3 letras: "Crystal Contreras" ≈ "Crystal Dariana Contreras
Diaz") **no es viable en fórmulas puras de Sheets**. Trade-off aceptado: no es instantáneo —
corre cada X min, no en cada evento. El resto del panel (verde/rojo/rosado) sigue en vivo por
fórmula; solo naranja/gris dependen de la corrida del helper.

**Piezas:**
1. `scripts/zoom-asistencia/clasificar_no_identificados.py` — SOLO lee
   `REUNIONES-ACTIVAS`/`LIVE-LOG`/`MATRICULADOS-VIVO`/`CUPOS`/`CORREO-ALIAS`; clasifica a los
   presentes (joined>left, excluye `@tocaunavida.org`) que no matchean por correo exacto ni por
   `CORREO-ALIAS`, y SOLO escribe 2 pestañas puente:
   - `CORREO-DETECTADO` (`CorreoAlterno | CorreoOficial | NombreRoster | NombreZoom | Host`) —
     **mismo layout `A:B` que `CORREO-ALIAS`** para que el panel lo resuelva por VLOOKUP igual
     que el rosado. Es el puente del **naranja**.
   - `NO-IDENTIFICADOS` (`Host | UUID | NombreZoom | Correo | UltimaHora`) — lista del **gris**.
2. `construir_panel_en_vivo()` ampliado (mismo archivo `setup_zoom_asistance.py`):
   - Estado de **3 niveles de match** (cada uno superconjunto del anterior): exacto →
     `PRESENTE`; vía `CORREO-ALIAS` → `PRESENTE (correo alterno)` 🩷; vía `CORREO-DETECTADO` →
     `PRESENTE (nombre detectado)` 🟠 (y sus variantes `ENTRÓ Y SALIÓ (...)`). `cond_detect` es
     un `ARRAYFORMULA(VLOOKUP(...))` igual que `cond_alias`; degrada a `""` si la pestaña está
     vacía (comportamiento idéntico al anterior).
   - Formato condicional **naranja `#ffb74d`** (busca `"nombre detectado"`; disjunto del ámbar
     de `ENTRÓ Y SALIÓ` que es igualdad exacta, y del rosado que busca `"correo alterno"`).
   - Resumen: fila nueva `🟧 Vía nombre detectado` (`COUNTIF *nombre detectado*`).
   - Sección **GRIS `#434343`** por bloque: título "⬛ SIN IDENTIFICAR — contactar ya" + conteo,
     y un `FILTER(NO-IDENTIFICADOS!C:D, UUID = UUID activo del bloque)` con las filas extra.
     Formato: título estático oscuro; lista con regla condicional (solo tinta filas con
     contenido, para no dejar un bloque gris con celdas vacías).

**Validado en vivo (clase real de hoy):** Crystal Dariana Contreras Diaz (entró como
`crystal24110126@`, roster tiene `patryhijas@`) → `PRESENTE (nombre detectado)`, fondo
verificado por API = `#ffb74d`. Jhan Carlos Martinez Ceballos (`jcmartinez@uniquindio.edu.co`,
sin match por nombre ni correo) → sección gris, fondo `#434343`. Cuadre: 11 verde + 1 naranja +
1 ámbar + 27 rojo = 40 total.

**Gotcha reencontrado:** las 2 fórmulas nuevas de la sección gris daban `#ERROR!` por no pasar
por `loc_filas()` (locale `es_ES` usa `;` no `,` como separador de argumentos). **Toda fórmula
escrita a este Sheet debe envolverse en `loc_filas()`/`loc()`** — regla ya conocida, fácil de
olvidar en un `ws.update` suelto.

### Pendientes tras esta sesión
- [x] **Arreglo de fondo Bug 2 — RESUELTO (2026-08-12).** `construir_panel_en_vivo()` ahora
  desambigua por día: la resolución cuenta cuántas filas de `CUPOS` coinciden con el topic
  (por `Clase` o `Alias Zoom`); si es 1 usa esa (comportamiento idéntico al anterior, blast
  radius cero para horarios sin colisión), si son 2+ elige la que además empate
  `CHOOSE(WEEKDAY(Apertura,2),…)` con `CUPOS!Día`. **El alias se puso en AMBAS filas**
  (`CUPOS!D12` jueves + `D16` miércoles) — ya no hay que moverlo cada semana. Verificado:
  miércoles→roster miércoles, jueves→roster jueves. **Esto reemplaza el "revertir alias"**: el
  estado correcto ahora es "alias en ambas filas", no en una. Gotcha de la fórmula:
  `MATCH(1, <bool_array>, 0)` da `#N/A` — hay que coercer con `*1` (`MATCH(1, arr*1, 0)`).
- [x] **Clasificador agendado en n8n — RESUELTO (2026-08-12).** Workflow NUEVO e independiente
  `panel-clasificar-no-identificados` (id `kbCOAdyMLvzLyFIQ`, 2 nodos, `active:true`):
  `scheduleTrigger` cron `*/5 6-23 * * *` → `executeCommand`
  `python scripts\zoom-asistencia\clasificar_no_identificados.py`. Se creó APARTE (no dentro
  de `Zoom - Asistencia`) a propósito: agregarlo al workflow de captura obligaría a un
  `deactivate`/`activate` que dropea webhooks de una clase en vivo. Exportado a
  `n8n-workflows/panel-clasificar-no-identificados.json`. (Sin rama de error explícita — mismo
  patrón que `Limpiar LIVE-LOG`/`Cerrar reuniones inactivas`; posible mejora: nodo Telegram
  on-fail.)
- Herramienta de diagnóstico reusable: `scripts/zoom-asistencia/monitor_panel_vivo.py` (muestrea
  `REUNIONES-ACTIVAS`/`LIVE-LOG`/`PANEL-EN-VIVO` cada N min, marca transiciones y el flag
  `<<< ROSTER EQUIVOCADO?`; ASCII puro — el intento de monitoreo del 2026-08-03 murió por no
  poder imprimir emojis en la consola cp1252 de Windows).

### Enriquecimiento — Celular + Ciudad en el roster (2026-08-12, sin cédula)

Pedido: analizar cruzar con la DB para mostrar más datos del estudiante (cédula, teléfono,
ciudad) y su costo de egress. **Esquema real verificado en Supabase** (no teórico): cédula y
celular viven en `postulantes_jc`/`postulantes_mr` (NO en `participants`), cruzables por
`email`, cobertura 98-100% (2.556/2.556 JC, 5.203-5.310/5.310 MR).

**Egress — la conclusión clave: no depende de cuánta gente mire el panel** (es un Sheet, no
lee Supabase por vista; solo el helper Python lo hace, por tandas). Estimado: bridge diario del
universo completo (~7.900 filas) ≈ 26 MB/mes; solo roster activo cada 5 min ≈ 48 MB/mes — ambos
triviales sobre el free tier de 5 GB. **El riesgo real sería refetchear el universo completo
cada pocos minutos** (~7,5 GB/mes, mismo tipo de error que el runaway de paginación de
[[reference_supabase_egress_panel]]) — evitado a propósito con este diseño.

**Decisión del usuario sobre alcance de PII:** teléfono + ciudad, **sin cédula** (documento de
identidad se consideró demasiado sensible para el roster completo); refresco = **solo el
roster de la(s) clase(s) activa(s)**, cada 5 min (enganchado al mismo cron del clasificador,
no un proceso nuevo).

**Implementación:** `clasificar_no_identificados.py` extendido — además de naranja/gris, junta
los correos del roster de las clases activas y hace `email=in.(...)` contra
`postulantes_jc`+`postulantes_mr` (best-effort: si Supabase falla, sigue escribiendo
naranja/gris igual). Escribe `DATOS-ESTUDIANTE` (`Correo | Celular | Ciudad`). Panel: 2 columnas
nuevas al FINAL del roster (`Nombre|Correo|Estado|Última hora|Celular|Ciudad`) vía `VLOOKUP` por
el correo OFICIAL del roster — funciona igual para presentes, ausentes y correo alterno/
detectado. Colocadas al final (no insertadas en medio) a propósito: cero riesgo para las
columnas Estado/Última hora ya probadas. `ANCHO_BLOQUE` pasó de 4 a 6 — todo lo demás
(resumen, gutter, franja de color, sección gris) ya estaba parametrizado con esa constante y se
corrió solo; solo 2 rangos con offset fijo (`c0+5`/`c0+4`) había que actualizar a mano.

**Gotcha real encontrado al poner el alias en ambas filas del Bug 2:** `resolver_horario()` del
**clasificador Python** es una implementación separada de la fórmula del panel — actualizar
solo la fórmula del panel y no el script rompió el clasificador (volvió a resolver a jueves,
la primera fila con el alias, para la clase real de miércoles) → naranja pasó a 0 y gris subió
a 13 (personas con correo exacto que dejaron de matchear porque el roster cargado era el
equivocado). **Lección:** la resolución de horario vive en 2 lugares (fórmula Sheets +
`resolver_horario()` en Python) — cualquier cambio a la cascada de `CUPOS` va en AMBOS.

**Validado en vivo:** Crystal Dariana (naranja) → `3135300994 | Barranquilla`, color de fondo
`#ffb74d` confirmado por API también sobre las 2 columnas nuevas. Cuadre: 10 verde + 3 ámbar +
26 rojo + 1 naranja = 40 total.

### Gotcha esperado — el HOST nunca aparece en el panel (ni verde, ni rojo, ni gris)

Soporte entró a la clase real usando las credenciales de la cuenta host (`jovenescreativos`) y
preguntó por qué no salía en gris ("sin identificar"). Diagnóstico confirmado revisando el
payload crudo de las ejecuciones de n8n (no solo si llegó a Sheets): **cero rastro** — ninguna
ejecución reciente trae su nombre/correo. **Causa: Zoom NO manda `meeting.participant_joined`/
`participant_left` para la sesión del propio host** (ni para quien reclama host con el host
key) — ese webhook solo existe para invitados que entran a una sala ya abierta por otra
sesión. Como TODO el pipeline de identificación (verde/rojo/rosado/naranja/gris) depende al
100% de que exista un evento en `LIVE-LOG`, el host es estructuralmente invisible para el
panel — no es un bug, es una limitación de la API de Zoom (coherente con el resto del diseño:
`REUNIONES-ACTIVAS`/`Apertura` ya asume que el host es quien abre la sala, nunca alguien a
identificar). **No hace falta arreglar nada** — si algún día se necesita rastrear también al
host/monitor, tocaría un mecanismo distinto (`meeting.started`/`meeting.ended`, que sí sí
llegan), no `participant_joined`.

### Resultado del monitoreo 10:27→12:06 + bug real en el propio monitor (2026-08-12)

`monitor_panel_vivo.py` corrió toda la sesión (`tools/monitor_panel_vivo_2026-08-12.log`,
362 líneas). Timeline real reconstruido comparando el log contra verificaciones directas:

| Ventana | Estado real | Causa |
|---|---|---|
| 10:27–10:33 | roster **jueves**, Present=0 | Bug 2, antes del hotfix |
| 10:33–10:36 | transición (fórmulas recalculando tras el hotfix) | normal, recalculo de Sheets no es instantáneo |
| 10:36–11:28 | roster **miércoles** correcto, Present 10-12, sin_match=2 estable | funcionando bien |
| 11:09:48 (1 ciclo) | `horario='#N/A'` momentáneo | blip transitorio durante un `recrear()` del panel en vivo — se autocorrigió solo en el siguiente ciclo (3 min después) |
| 11:28–11:31 | último dato bueno antes del cambio de layout | — |
| **11:31–12:01** | **"BLOQUE EN BLANCO" reportado — FALSO.** El panel seguía funcionando (verificado por fuera del monitor: naranja/gris/celular/ciudad todos correctos en ese rango) | **Bug en el monitor, no en el panel** — ver abajo |
| 12:06 | "BLOQUE EN BLANCO" — real | la clase (miércoles 10-12) ya cerró, 0 reuniones `Activo=TRUE` |

**Causa del falso "BLOQUE EN BLANCO":** `monitor_panel_vivo.py` tenía su **propia copia
hardcodeada** de en qué columna cae cada bloque (`BLOQUES = {"jovenescreativos": {"col_val":
9, ...}}`). Al agregar Celular/Ciudad al panel (`ANCHO_BLOQUE` 4→6), el bloque de
`jovenescreativos` se corrió de la columna J a la L — el monitor seguía leyendo J (ahora vacía)
y reportó "sin UUID en el slot" en falso durante ~30 min, mientras el panel real (verificado
aparte con las columnas correctas) mostraba datos correctos.

**Mismo patrón de bug que el de `resolver_horario()` duplicado (ver arriba) — 2ª vez el mismo
día:** cualquier cosa que dependa de la estructura de columnas de `PANEL-EN-VIVO` pero viva
FUERA de `construir_panel_en_vivo()` se desincroniza en silencio si el layout cambia. **Fix de
raíz aplicado:** `ANCHO_BLOQUE`/`STATS_ANCHO`/`GUTTER`/`BLOQUE_TOTAL` se subieron a constantes
de MÓDULO en `setup_zoom_asistance.py` (antes vivían dentro de la función); `monitor_panel_vivo.py`
ahora las **importa** y calcula `BLOQUES` desde `HOSTS_PANEL`/`BLOQUE_TOTAL` en vez de
hardcodear columnas — un futuro cambio de layout se propaga solo. Verificado tras el fix:
`BLOQUES` calculó `jovenescreativos` en columna 11 (correcto) y el snapshot ya no da falsos
blancos.

**Lección general para toda esta sesión:** el panel tiene 3 implementaciones independientes de
su propia estructura (fórmulas en `construir_panel_en_vivo()`, resolución de horario en
`clasificar_no_identificados.py`, y ahora columnas en `monitor_panel_vivo.py`) — cualquier
cambio de layout/resolución debe revisar las 3, no solo la que se está editando.

## Sesión 2026-08-12 (tarde) — Bug 1 arreglo de fondo + búsqueda ampliada en DB, antes del test de las 6pm

Usuario reportó un bug recurrente ("muchas veces está presente"): el panel a veces no toma la
llegada de los estudiantes. Diagnóstico: es **Bug 1**, documentado desde 2026-08-06 y nunca
arreglado de fondo — `Detectar Apertura Reunion` marca `reunionesAbiertas[uuid]=true` en
static data **para siempre**; si Zoom reutiliza el mismo UUID la semana siguiente (sala fija
recurrente) y `meeting.ended` no llegó la vez anterior (gotcha ya conocido), el flag nunca se
limpia y el nodo nunca vuelve a escribir `Activo=TRUE` — el panel sigue viendo la sala
"cerrada" con estudiantes reales conectados.

### Fix aplicado — clave con fecha, no solo UUID

`Detectar Apertura Reunion` y `Cerrar Reunion Activa` (código de referencia nuevo:
`nodo-detectar-apertura-reunion.js` / `nodo-cerrar-reunion-activa.js`, no existían copias
locales antes) cambiaron la clave de `reunionesAbiertas` de `uuid` a `` `${uuid}:${fecha}` ``.
Una sala recurrente se re-marca activa cada vez que Zoom la reabre en un día nuevo, sin
intervención manual; dentro del mismo día sigue sin re-escribir (mismo ahorro de cuota de
Sheets). Desplegado por API (PUT solo con `name/nodes/connections/settings`, `deactivate` →
esperar 35s → `activate`, patrón obligatorio ya documentado) — verificado `active:true` y el
código nuevo presente en ambos nodos tras el ciclo. Exportado a `n8n-workflows/zoom-asistencia.json`.

### Probado end-to-end con eventos Zoom SINTÉTICOS pero FIRMADOS de verdad

Sin esperar a la clase de las 6pm: se firmó HMAC-SHA256 (`ZOOM_WEBHOOK_SECRET_TOKEN` local,
mismo esquema que valida el nodo `Firma valida?`) y se mandó una secuencia real al webhook
`/webhook/zoom-asistencia` con un UUID de prueba (`TEST-BUG1-FIX-...`): `joined` ×2 (mismo
UUID) → `left` → `meeting.ended` → `joined` otra vez. Resultado: **1 sola fila** en
`REUNIONES-ACTIVAS` (no duplicó), **4 filas** reales en `LIVE-LOG` (nunca se perdió una
llegada, ni siquiera después del `ended`), y **reabrió a `Activo=TRUE`** tras el cierre —
confirma que todo el pipeline (firma → ruteo → normalizar → `LIVE-LOG` → detectar apertura →
`REUNIONES-ACTIVAS`) sigue sano tras el cambio. Datos de prueba borrados de ambas pestañas
inmediatamente después (`REUNIONES-ACTIVAS` fila 25, `LIVE-LOG` 4 filas) para no interferir
con la clase real de las 6pm.

**Honestidad sobre qué prueba esto y qué no:** este test confirma que el mecanismo
abrir→deduplicar→cerrar→reabrir sigue funcionando sin regresión, y que reabrir el MISMO día
tras un cierre ya funcionaba incluso con el código viejo (`Cerrar Reunion Activa` limpia el
flag al recibir `meeting.ended`). Lo que el fix real soluciona — reabrir tras un `meeting.ended`
que NUNCA llegó, en un DÍA/SEMANA distinto — es correcto **por construcción** (la clave incluye
la fecha real del servidor, así que un flag de una semana anterior es estructuralmente
imposible que bloquee hoy) y no es algo que se pueda demostrar con un test sintético sin
falsear la fecha del servidor. Se validará de verdad la próxima vez que una sala semanal
recurrente se reutilice tras un cierre fallido — que es exactamente el escenario reportado.

**Bonus no planeado:** durante las pruebas, la sala real de `jovenescreativos` (misma clase de
hoy, ya cerrada) se reabrió sola (`Apertura` se actualizó a `12:23`) con estudiantes reales
haciendo `joined`, y se volvió a cerrar — confirma el mecanismo funcionando con tráfico real,
aunque ese caso puntual es "mismo día" (no ejercita la parte nueva del fix).

### Búsqueda en DB — auditoría del caso gris de hoy + mejora aditiva

Pedido: mejorar la eficacia de la búsqueda en la DB, porque en pruebas anteriores el usuario
encontró a mano en la DB/Seguimiento a estudiantes que la herramienta no identificaba.

**Auditado con el único caso gris real de hoy** (Jhan Carlos Martinez Ceballos,
`jcmartinez@uniquindio.edu.co`): búsqueda exhaustiva en Supabase (`participants`,
`postulantes_jc`, `postulantes_mr`) por correo exacto Y por nombre (`ilike`) — **no existe en
ninguna tabla**. El gris de hoy era correcto, no un fallo de búsqueda.

**Causa más probable del patrón general reportado:** `MATRICULADOS-VIVO` es una foto fija de
la BD Seguimiento del **2026-08-03** (9 días de antigüedad al momento de esta sesión). Un
estudiante matriculado o cambiado de horario después de esa fecha es invisible para el
matching automático (ni por correo ni por nombre), sin importar qué tan buena sea la lógica de
match — simplemente no está en el snapshot. **No se pudo refrescar hoy** — no había una BD
Seguimiento más nueva descargada localmente (requiere descarga manual + `analizar_cupos_bd.py`
+ `setup_zoom_asistance.py --solo-matriculados-vivo`).

**Mejora aditiva aplicada (sin tocar el panel):** `clasificar_no_identificados.py`, para cada
caso gris, ahora busca por nombre en `postulantes_jc`/`postulantes_mr` **completas** (no solo
el roster de esa clase específica) vía `ilike` con los tokens más largos del nombre — pista
para el monitor de "esta persona SÍ está en el sistema como fulano@..., solo no en este
roster/horario". Columna nueva `CandidatoDB` en `NO-IDENTIFICADOS` (5ª columna; el panel sigue
leyendo solo `C:D` así que esto NO tocó el layout ya frágil por los cambios de hoy). Probado
con 3 casos: nombre real conocido → encuentra el candidato correcto; Jhan Carlos → vacío
(correcto, no existe); nombre inventado → vacío (no alucina matches falsos).

**Pendiente real para cerrar el tema de fondo:** conseguir una BD Seguimiento fresca y correr
`analizar_cupos_bd.py` + `--solo-matriculados-vivo` antes de que el roster acumule más
desactualización — la búsqueda ampliada en DB es una mitigación, no reemplaza tener el roster
al día.

### Roster refrescado + `analizar_cupos_bd.py` ahora lee la hoja VIVA (2026-08-12, mismo día)

El usuario pasó el link de la BD Seguimiento real (`BD Seguimiento de Monitorias - JC2026`,
Google Sheets, no un `.xlsx`). La Service Account YA tenía acceso (compartida). En vez de
descargar un `.xlsx` a mano (el paso manual que causaba la desactualización), se reescribió
`tools/analizar_cupos_bd.py` para leer la pestaña `Seguimiento` **directo por API** (mismo
patrón Service Account que el resto del repo) — correr el script siempre trae el dato más
fresco posible, sin descarga manual nunca más. Headers verificados idénticos (`Nombres`/
`Apellidos`/`E-mail`/columnas `Horario *`) — cero cambios de esquema. **Bug encontrado y
corregido de paso:** `fecha_analisis` estaba hardcodeado a `"2026-08-03"` en el código, sin
importar cuándo se corriera de verdad — ahora usa `datetime.now()`.

**Resultado del refresco:** 5.974 asignaciones horario-estudiante en 106 horarios (antes:
5.319 en 89) — confirma que el roster viejo (9 días de antigüedad) sí estaba perdiendo gente
real. `HTML - Miércoles 10:00 A.M.` se mantuvo en 40 (estable); `HTML - Jueves 10:00 A.M.`
bajó a 45 (era 47 — retiros/cambios reales). `MATRICULADOS-VIVO` reescrita con el dato fresco.

### Desambiguación de horario extendida a HORA, no solo día (mismo día, antes del test 6pm)

Al confirmar que la clase de las 6pm de hoy es **HTML** (`CUPOS` fila 13, `Miércoles 6:00
P.M.`, sin `Alias Zoom` todavía), surgió una duda real: si esa sala reutiliza el MISMO topic
de Zoom que la de las 10am (`"Desarrollo Web - GIT, HTML y CSS"`, como ya pasa entre
miércoles/jueves 10am), la desambiguación por SOLO DÍA (el fix de esta mañana) no alcanzaría
para distinguir miércoles 10am de miércoles 6pm — ambas caerían el mismo día.

**Fix aplicado (reemplaza el de solo-día, en `construir_panel_en_vivo()` Y
`resolver_horario()` — ambos archivos, sincronizados):** cada fila de `CUPOS` que coincide
con el topic recibe un puntaje — día distinto pesa `+1000` (nunca gana sobre el día correcto),
dentro del mismo día gana la `Hora` más cercana a la apertura real. **A propósito NO exige
hora exacta**: la gente entra unos minutos antes de la hora oficial (hoy mismo, 9:44 para una
clase de 10am — exigir igualdad hubiera fallado con el propio caso real de hoy). Con 1 sola
fila coincidiendo (caso normal, sin colisión), el puntaje es irrelevante — mismo resultado que
siempre.

**Gotcha real al probar la fórmula de Sheets (no del negocio, del test):** el primer intento
de probar la fórmula en una pestaña scratch dio el mismo resultado equivocado en los 4 casos
— causa: el propio script de prueba escribió `[[TOPIC], [apertura]]` a un rango `A1:B2` (2
filas x 1 columna) en vez de `[[TOPIC, apertura]]` a `A1:B1` (1 fila x 2 columnas) — la fecha
nunca llegó a la celda que la fórmula leía. Corregido el test, no la fórmula real.

**Validado con la colisión de 3 vías simulada** (alias temporal agregado a `CUPOS!D13` solo
para la prueba, quitado inmediatamente después) — en pestaña scratch (fórmula real de Sheets)
y en Python (`resolver_horario()`) por separado, ambos coinciden:
- miércoles 9:44 → Miércoles 10am ✅ (no jueves, no miércoles 6pm)
- miércoles 17:55 y 18:03 → Miércoles 6pm ✅ (entrar antes O después de la hora oficial, ambos)
- jueves 9:44 → Jueves 10am ✅ (el mismatch de día sigue dominando)

Panel recreado con la fórmula nueva (seguro, sin clase en vivo). `CUPOS!D13` confirmado vacío
de nuevo tras la prueba.

**Pendiente real para esta noche:** `CUPOS!D13` (HTML miércoles 6pm) sigue SIN `Alias Zoom` —
no se puede adivinar el topic real de Zoom sin verlo en vivo. Apenas abra la reunión, revisar
`REUNIONES-ACTIVAS`/`LIVE-LOG` por el topic real y setear el alias correspondiente (mismo
patrón rápido de hoy en la mañana, 1 celda, sin recrear nada) — con el fix de puntaje ya
puesto, esta vez no hace falta preocuparse por si ese topic también lo usa el horario de 10am:
la hora lo va a desambiguar sola.

## Pivote a website con login (2026-08-15, tarde) — Sheets ya tocó techo

Tras el incidente de la cola trabada + el gotcha de `Sala 1`/`Sala 2` (secciones arriba),
usuario preguntó directamente si construir un sitio con login para que los monitores vean esto
sería mejor que seguir parchando Sheets. Se decidió que sí, con la arquitectura ya prevista en
la sección "Decisión de diseño — ¿Sheets, WordPress, o una app real?" (2026-08-12): una vista
nueva dentro de `panel-datos-rofe` (Next.js + Supabase, ya en producción, ya resuelve
auth/acceso), NO un sitio aparte ni WordPress.

**Fase 1 — vista web autenticada leyendo la MISMA data (construida y probada 2026-08-15):**
- `app/panel-vivo/page.tsx` en `panel-datos-rofe` — login con Google OAuth vía Supabase Auth,
  restringido a `@tocaunavida.org` (chequeo client-side además del consent screen de Google,
  defensa en profundidad); tras login, gate de clave de API guardada en `localStorage` (nunca
  en el bundle, mismo patrón que `BotonActualizar.tsx`); luego polling cada 25s (conservador
  "por lo de hoy con la concurrencia") contra un backend.
- `app/panel-vivo/demo/page.tsx` — vista de prueba con datos sintéticos, sin login, para
  validar el diseño visual antes de conectar datos reales.
- **Backend: NO n8n.** El primer intento (workflow n8n `panel-vivo-api`, id `Gir4uQz6N24RMScn`)
  causó **5 caídas reales de captura en vivo** el mismo día — cualquier webhook basado en
  `executeCommand` que tarde >segundos compite por los únicos 2 cupos de
  `N8N_CONCURRENCY_PRODUCTION_LIMIT` con la captura de Zoom en vivo. Reemplazado por
  `servidor_panel_vivo.py`: servidor HTTP standalone (proceso propio, `ThreadingHTTPServer`,
  puerto 8765), con un hilo de fondo que refresca un caché cada 15s llamando a
  `api_panel_vivo.generar_panel_vivo()` — el cliente siempre recibe el caché al instante
  (~0.2s), nunca espera el cómputo. Expuesto a internet vía Cloudflare Tunnel (`cloudflared`,
  túnel "quick"/efímero — ngrok free solo permite 1 túnel simultáneo, ya usado por n8n).
  Workflow `panel-vivo-api` dejado DESACTIVADO (no borrado) en n8n.
- Este backend YA es "lógica en un solo lugar" reforzado: `generar_panel_vivo()` en
  `api_panel_vivo.py` reusa `panel_logic.py` (mismo módulo que ya usaba
  `clasificar_no_identificados.py`) para `resolver_horario()`/`match_por_nombre()` — cero
  lógica de resolución duplicada nueva.
- Login + backend confirmados funcionando por el usuario (llegó hasta la pantalla de clave de
  API durante la clase de 2pm de hoy).

**Bug real encontrado usando el panel en vivo (2026-08-15, mismo día):** usuario reportó ver
solo ~6 conectados cuando un CSV de registro de Zoom mostraba 30+. Causa: `REUNIONES-ACTIVAS`
puede tener VARIOS UUIDs distintos para la MISMA sala física (reconexiones — Zoom no siempre
reusa el UUID), más 1 UUID corrompido a texto literal `#ERROR!` (bug de escritura en Sheets,
probable causa: un UUID de Zoom que empieza con `+` mal interpretado como fórmula en modo
`USER_ENTERED`; NO arreglado — requiere tocar el workflow en vivo, diferido a fuera de horario
de clase). Filtrar por 1 solo UUID fragmentaba la asistencia real en varias "salas" separadas.
**Fix (lado lectura, sin tocar n8n):** agrupar por `(host, topic)` en vez de por UUID
individual; `panel_logic.presentes_por_uuids()` (nuevo, recibe un CONJUNTO de UUIDs) fusiona
la asistencia de todos los UUIDs del grupo — de paso recupera también los eventos con el UUID
corrompido a `#ERROR!`, porque el agrupamiento es por texto de topic, no por UUID. Confirmado:
pasó de 7 "salas" fragmentadas a 3 correctamente consolidadas con conteos mucho más altos
(correctos).

**Pregunta de confiabilidad del usuario** ("es seguro y confiable... me parece surreal que no
encontremos a esos estudiantes"): investigado con un script dedicado que cruza cada email "sin
identificar" contra `tools/cupos_clases.json` (roster completo por horario) — confirmó que la
mayoría eran estudiantes REALES cruzando de horario (68% de una muestra de 78 pertenecía al
roster del bloque de 8am pero asistía al de 2pm), no un bug de búsqueda/matching. No es
necesario agregarlos al roster de la sala en la que en realidad están (decisión del usuario),
pero confirma que el "sin identificar" del panel es dato real, no ruido.

**Fase 2 — Supabase como fuente en vivo en vez de Sheets (preparación en curso 2026-08-15,
SIN conectar todavía — decisión explícita del usuario: avanzar la preparación mientras la clase
sigue activa, conectar el workflow en vivo solo cuando termine):**
- Migración `045_zoom_live_tables` aplicada — `zoom_reuniones_activas` +
  `zoom_live_log`, RLS habilitado sin política + `REVOKE ALL FROM anon, authenticated`
  (mismo patrón que toda tabla con PII del proyecto; solo `service_role`).
- `api_panel_vivo.py`: `leer_reuniones_activas_supabase()` / `leer_live_log_supabase()` (leen
  las tablas nuevas con la MISMA forma que `worksheet.get_all_values()`, para que
  `generar_panel_vivo()` no note la diferencia) + variable de entorno `PANEL_VIVO_FUENTE`
  (`sheets` default / `supabase`) para elegir la fuente sin tocar `panel_logic.py`.
- **Bug real encontrado y corregido en esta misma preparación** (probado con filas sintéticas
  vía SQL directo a Supabase, sin tocar n8n — exactamente el tipo de prueba que esta fase
  "segura" busca hacer): PostgREST devuelve `timestamptz` como ISO8601 en UTC
  (`"2026-08-15T19:00:00+00:00"`), pero `resolver_horario()` (compartida, sin tocar) solo
  reconoce el formato que ya escribe Sheets (`"YYYY-MM-DD HH:MM"`, hora Bogotá, sin `T` ni
  offset) — el parseo fallaba en silencio (`except ValueError: continue`) y
  `resolver_horario()` caía en su respaldo de "sin fecha parseable" (1ª fila que coincide, sin
  el puntaje día+hora), dando un horario equivocado y 0 presentes aunque el estudiante de
  prueba sí estuviera en el roster correcto. **Fix:** `_iso_a_bogota_texto()` nueva en
  `api_panel_vivo.py` — convierte el ISO8601/UTC de Supabase a Bogotá (`UTC-5`) y al formato
  de texto que el resto del código ya espera; se arregló en el ADAPTADOR de lectura, no en
  `resolver_horario()`, para que la lógica de resolución siga siendo una sola implementación
  sin importar la fuente. Confirmado con la misma fila sintética: horario correcto
  (`...2:00 P.M... - Uno`) y el estudiante de prueba (`diego247camargo@gmail.com`, real, del
  roster de esa sala) sale `presente_exacto`. Filas sintéticas (`TEST-FASE2-UUID`) borradas de
  ambas tablas tras validar. Modo `sheets` (producción real, clase en vivo) confirmado sin
  cambios tras el fix.
- **Pendiente, explícitamente diferido hasta que termine la clase:** escribir + desplegar 3
  nodos HTTP Request nuevos en el workflow EN VIVO `Zoom - Asistencia` (id `jkNaE51PKQ4TQzNq`)
  que escriban en paralelo a `zoom_reuniones_activas`/`zoom_live_log` (además de, no en vez de,
  los nodos de Sheets existentes — no se retira Sheets hasta validar Supabase con datos
  reales); requiere reiniciar el PROCESO de n8n (no solo reactivar el workflow) para que tome
  `SUPABASE_URL`/`SUPABASE_SERVICE_ROLE_KEY` de `scripts/zoom-asistencia/.env` (agregadas hoy).
  Una vez validado con datos reales, cambiar `servidor_panel_vivo.py` a
  `PANEL_VIVO_FUENTE=supabase`.
- **Pendiente, sin fecha:** arreglar el bug de escritura `#ERROR!` (UUID mal interpretado como
  fórmula en Sheets) — mismo motivo, requiere tocar el workflow en vivo; obtener un túnel
  Cloudflare permanente/con nombre (requiere login del usuario a su cuenta, no lo puedo hacer
  yo) para reemplazar la URL efímera `trycloudflare.com`; desplegar la Fase 1 a Vercel
  producción (Netlify de baja 2026-08-11, no es opción; hoy solo corre en `npm run dev` local,
  puerto 3001); decidir si borrar o dejar
  desactivado el workflow `panel-vivo-api` ya superado por `servidor_panel_vivo.py`.
