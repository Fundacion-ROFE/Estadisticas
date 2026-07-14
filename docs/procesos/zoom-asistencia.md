# Asistencia Zoom

**Estado:** Funcional — probado extremo a extremo con reunión real (ejecución #37) y con el
`meeting.ended` real de una clase de 51 estudiantes (#46). Desde 2026-07-02 el workflow
escribe en la pestaña **`ZOOM-ASISTANCE`** (mismo spreadsheet H3Test), con formato
condicional <70% y pestañas `CUPOS` + `ZOOM-STATS` (estadísticas por sesión y por semana,
denominadores "X de Y" desde la BD de Monitorias). Quedan pendientes las pruebas de casos
límite (reunión ≤20 min, participante sin correo) y la decisión del Sheet de producción.
**Última actualización:** 2026-07-13
**Procesos relacionados:** —

## Qué hace
Automatiza la toma de asistencia de clases virtuales en Zoom (2 salas, plan Business,
100 usuarios c/u). Registra a **todos** los que se conectaron (sin descartar a nadie) y
además calcula cuántos de los 3 momentos dorados de la clase (minuto 10, mitad, 10 min
antes del fin) cumplió cada uno, como dato crudo adicional — la penalización/acción sobre
ese dato es un proceso posterior, no de esta automatización.

## Disparador (Trigger) — REVISADO 2026-07-01
Ya no se usa Google Calendar (desfases de horario). Trigger real: **Webhook de Zoom**
suscrito al evento `meeting.ended` (Event Subscriptions de la app Server-to-Server OAuth).
Requiere manejar el handshake `endpoint.url_validation` (CRC) y validar la firma
`x-zm-signature` en cada request.

## Flujo resumido (diseño revisado 2026-07-01)
1. Webhook recibe `meeting.ended` → responde 200 de inmediato (Zoom reintenta si tarda).
2. `Wait` ~90s de margen + `Retry On Fail` en las llamadas HTTP (no hay garantía de
   disponibilidad instantánea, aunque este endpoint es mucho más rápido que el de Reports).
3. `GET /past_meetings/{uuid}` → horas **reales** de inicio/duración (no las programadas).
4. `GET /past_meetings/{uuid}/participants` (paginado) → arreglos de `join_time`/`leave_time`
   por sesión de cada participante. **Ya no se usa** `/report/meetings/{id}/participants`
   (API de reportes consolidados) porque no trae timestamps individuales y puede tardar
   en generarse.
5. Nodo Code calcula los 3 checkpoints (`inicio+10min`, `inicio+duracion/2`,
   `inicio+duracion-10min`), verifica por participante si cada checkpoint cae dentro de
   alguna de sus sesiones join→leave, parsea Nombre/Apellido/Correo/Identificación (texto
   libre manual, ver Gotchas), arma la columna `Instancias` ("0/3".."3/3") y calcula
   `% Asistencia`: fusiona los intervalos join→leave solapados/contiguos del participante
   (las sesiones de reconexión pueden solaparse — no se suma doble), recorta cada intervalo
   a `[inicio, finReal]`, suma los minutos conectados, divide por la duración real de la
   reunión y redondea a entero (`"NN%"`).
6. Escribir **todos** los participantes a Google Sheets — no se filtra a nadie, la
   columna `Instancias` es el dato crudo que un proceso posterior usará para decidir
   acción/penalización.

## Flujo secundario — control temprano (minuto 10) · trigger `meeting.started` (2026-07-04)
Rama paralela del **mismo** webhook para tener control de la clase temprano, sin esperar al
cierre. El webhook ahora es de **trigger dual**: tras validar firma, un IF `Evento
meeting.started?` bifurca:
- **`meeting.ended`** → rama completa de siempre (Esperar 90s → % + momentos dorados →
  `ZOOM-ASISTANCE`). **Intacta.**
- **`meeting.started`** → `Esperar 10 min` → `Obtener Token Zoom 2` → `Participantes en Vivo`
  → `Presentes @10min` (Code) → `Escribir ASISTENCIA-10MIN`.

Detalles de diseño:
- **Participantes en vivo ≠ `past_meetings`.** Con la reunión en curso, `past_meetings` aún no
  existe; se usa la **Dashboard API**: `GET /metrics/meetings/{uuid}/participants?type=live`
  (uuid con doble `encodeURIComponent`, igual que la rama completa). Requiere plan Business
  (ya lo tienen) + scope **`dashboard_meetings:read:admin`**.
- El nodo Code `Presentes @10min` (copia en `scripts/zoom-asistencia/nodo-presentes-10min.js`)
  **no calcula %**: solo lista una fila por persona (dedup por email/nombre) con `Curso` y
  `Fecha` reales tomados del **payload del webhook** (`payload.object.topic`/`start_time`),
  reusando `extraerContacto()`/`fechaBogota()` de la rama completa.
- Destino: pestaña **`ASISTENCIA-10MIN`** (mismo spreadsheet H3Test), headers `Nombre |
  Apellido | Correo electrónico | Identificacion | Curso | Fecha | Hora ingreso`, **append**.
  Se crea con `python setup_zoom_asistance.py --solo-10min` (no toca las pestañas de producción).

**Pendiente de Samuel (en Zoom Marketplace, no automatizable):**
1. Agregar el evento **`meeting.started`** a las Event Subscriptions de la app S2S OAuth
   (misma URL `/webhook/zoom-asistencia`).
2. Agregar el scope **`dashboard_meetings:read:admin`** y re-activar la app.
   Hasta que esto se haga, **la rama nueva queda inerte** (Zoom no envía `meeting.started`),
   por lo que la rama completa sigue operando sin riesgo.

## Fuentes de datos / APIs usadas
- Zoom API — Server-to-Server OAuth. Endpoints: `GET /past_meetings/{uuid}`,
  `GET /past_meetings/{uuid}/participants`. Scopes identificados (ver `docs/convenciones.md`):
  `meeting:read:past_meeting:admin` y `meeting:read:list_past_participants:admin`.
- Zoom Webhook (Event Subscriptions) — evento `meeting.ended`. **No es un feature de pago**
  — incluido en cualquier app Server-to-Server OAuth, confundible con el texto genérico de
  la pantalla que menciona el Challenge-response check (CRC).
- Google Sheets (escritura).
- ~~Google Calendar~~ — descartado como trigger.

## Destino de los datos
**Desde 2026-07-02:** pestaña **`ZOOM-ASISTANCE`** del spreadsheet `H3Test` — ID
`1VyXOYsnpD9ksKcJFHiiRR6fr4UUCea4WmGG96NV0WP0`. Headers en fila 1: `Nombre | Apellido |
Correo electrónico | Identificacion | Instancias | Curso | Fecha | % Asistencia`
(idénticos a la antigua pestaña `H3Test`, que queda congelada como histórico de pruebas —
sus 104 filas se migraron a `ZOOM-ASISTANCE`). Objetivo: reemplazar la lógica manual de la
pestaña `Asistencia` de la BD Seguimiento de Monitorias (bloques horizontales por clase,
4-6 columnas por sesión, columna `Validar` manual).

**Indicadores de color (formato condicional, automático):**
- Fila completa en **rojo** cuando `% Asistencia < 70%` — el estudiante no tomó bien la clase.
- Celda del % en **verde** cuando `>= 70%`.
- El umbral (70) es una constante `UMBRAL` en `scripts/zoom-asistencia/setup_zoom_asistance.py`.

**Pestañas complementarias (mismo spreadsheet):**
- **`CUPOS`** — 89 clases con su cantidad de inscritos (denominador del "X de Y
  estudiantes conectados"), extraída de la BD de Monitorias pseudonimizada con
  `tools/analizar_cupos_bd.py` → `tools/cupos_clases.json` (777 estudiantes activos:
  15-16 grupos por área en HTML/Lógica/IA/Emprendimiento/HE, 6 de Hackea, 5 de
  Bienvenida; cupos de 32 a 63). Columnas E:F `Día`/`Hora` parseadas del nombre de la
  clase (la primera hora es siempre COL/ECU/PAN). Columna D `Alias Zoom` editable
  (preservada al regenerar) y tabla H:I `Palabra clave → Área` editable para inferir
  el área desde el topic de la reunión.
- **`ZOOM-STATS`** — solo fórmulas, se actualiza sola con cada toma de asistencia:
  - *Por sesión* (cols A:J): Semana ISO, Curso, Fecha, Conectados, Cupo, "X de Y
    estudiantes", % del cupo, Promedio % estancia, Alumnos <70%, Match cupo. Rojo si
    % del cupo o promedio de estancia <70%, naranja si hay alumnos <70%.
  - **Resolución del cupo ("cantidad que debería haber"), en cascada (2026-07-02):**
    1. topic de Zoom == nombre exacto de clase en `CUPOS`;
    2. topic == `Alias Zoom` (columna D);
    3. **por horario**: área inferida del topic con las palabras clave de `CUPOS!H:I`
       + día de la semana y hora de la `Fecha` real del evento (tolerancia ±45 min)
       → SUMA de inscritos de las clases de esa área en esa franja. Con esto el
       "51 de 51" salió solo para "Desarrollo Web - GIT, HTML y CSS" (jueves 9:54 →
       HTML - Jueves 10:00 A.M.) sin tocar alias. La columna `Match cupo` indica cuál
       de los 3 niveles resolvió (o "sin match").
    ⚠ Si varios grupos de la misma área comparten franja (ej. "Sábado 8:00 - Uno/Dos/
    Avanzado"), el cupo por horario los **suma** — si en la práctica cada grupo tiene
    su propia reunión Zoom, usar `Alias Zoom` para separar los denominadores.
  - **Exclusión de cuentas staff (2026-07-03):** los conteos de Conectados, promedio de
    estancia y alumnos <70% **excluyen** a los participantes cuyo email contenga alguno
    de los textos de la lista `CUPOS!G` (default: `tocaunavida.org` — preservada al
    regenerar). Motivo: auditoría del "51 de 51" reveló que incluía cuentas de la
    fundación (`comunicaciones@`, `soporte.it@`, `jovenescreativos@`) — el valor real
    era 50 de 51. Las filas staff siguen quedando en `ZOOM-ASISTANCE` (registro crudo),
    solo se excluyen de las estadísticas.
  - **Límite conocido:** "Conectados = Cupo" compara *cantidades*, no *personas* — la
    verificación de que los conectados sean exactamente los inscritos (columna `Validar`
    contra `Seguimiento`) requiere el Sheet de producción con correos reales; con la BD
    pseudonimizada local no se puede cruzar por email.
  - **Corroboración persona por persona disponible hoy (2026-07-03):**
    `tools/corroborar_asistencia_h3test.py` cruza los correos de los asistentes contra
    `h2test` (Q10, correos reales, refresco 4h). Resultado con las 2 clases reales:
    **90% y 84% de los asistentes verificados como estudiantes matriculados**; los no
    encontrados fueron una mezcla de bot notetaker (`fred@fireflies.ai` — agregado a la
    lista de exclusión `CUPOS!G`), typos evidentes del correo al entrar a Zoom
    (`vbuesaquilloo@` con doble o) y estudiantes que probablemente usan un correo
    distinto al registrado en Q10. Decisión: cupos por horario siguen saliendo de la
    BD de Monitorias (único origen con grupos de horario) pero quedan marcados como
    provisionales hasta el Sheet de producción; la validación de *identidad* se hace
    contra Q10.
  - *Por semana* (cols K:O): clases dictadas, conexiones totales, promedio de conectados
    por clase, promedio % estancia.
  - Columnas helper ocultas R:U aplanan `ZOOM-ASISTANCE` (con % normalizado a número y
    semana ISO); todas las tablas se derivan de ahí con COUNTIFS/AVERAGEIFS.

El destino final de producción (con `Validar` + hoja `Seguimiento` reales) sigue pendiente —
cuando se decida, `setup_zoom_asistance.py` puede reconstruir las 3 pestañas en ese
spreadsheet cambiando `SHEET_ID`.

## Integración con Supabase (propuesta 2026-07-13)

**Caso de uso:** Consulta SQL única que retorne asistencia + aprobación de un estudiante por email.

**Tabla propuesta: `asistencia_zoom`**
```sql
CREATE TABLE asistencia_zoom (
  id BIGSERIAL PRIMARY KEY,
  email TEXT NOT NULL,  -- FK a participants.email
  curso TEXT NOT NULL,
  fecha DATE NOT NULL,  -- YYYY-MM-DD
  nombre TEXT,
  apellido TEXT,
  correo_electrónico TEXT,  -- valor crudo del webhook Zoom
  instancias TEXT,  -- formato "N/3"
  porcentaje_asistencia TEXT,  -- formato "NN%"
  created_at TIMESTAMP DEFAULT now(),
  UNIQUE (email, curso, fecha)  -- upsert rápido post-clase
);
CREATE INDEX idx_asistencia_email_curso ON asistencia_zoom(email, curso, fecha);
```

**Flujo de sincronización (post-implementación):**
1. Workflow n8n escribe en `ZOOM-ASISTANCE` (Sheets) — intacto
2. Script nuevo `sync_asistencia_supabase.py` (patrón similar a `sync_aprobacion_supabase.py`)
   lee la pestaña y hace upsert en `asistencia_zoom` por (email, curso, fecha)
3. Ejecución: post-clase automático o schedule cada 2h
4. RLS: `select` si `auth.email = email` O rol admin/docente

**Consulta combinada (frontend/reportes):**
```sql
SELECT 
  p.email, p.nombre,
  a.curso, a.fecha, a.instancias, a.porcentaje_asistencia,
  ap.resultado, ap.fecha_aprobacion
FROM participants p
LEFT JOIN asistencia_zoom a ON p.email = a.email
LEFT JOIN aprobacion_cursos ap ON p.email = ap.email AND a.curso = ap.curso
WHERE p.email = 'juan@example.com'
ORDER BY a.fecha DESC;
```

**Estado:** Tabla documentada, pendiente de crear en Supabase y script de sync. No bloquea producción
de asistencia en H3Test — es una optimización posterior para reportes integrados.

## Panel de Riesgo + Asistencia Zoom (actualizado 2026-07-13)

**Integración en `tools/panel_riesgo_gui.py`:**
- Nueva función `leer_asistencia_zoom()` extrae datos de ZOOM-ASISTANCE
- Calcula promedio de asistencia por estudiante + lista de faltas (porcentaje <70% O instancias <3/3)
- Tabla "ATENCIÓN" agregó columna **"Asistencia %"** — promedio general del estudiante
- Doble clic en estudiante abre reporte completo con:
  - Promedio manual (Q10)
  - Promedio asistencia Zoom
  - Cursos Q10 con avance
  - **Sección "Faltas de Asistencia"** listando cada clase donde asistencia <70% O <3/3 momentos
    (fecha, porcentaje, instancias cumplidas)
  
**Scripts auxiliares:**
- `scripts/zoom-asistencia/consultar_asistencia.py` — lectura directa de ZOOM-ASISTANCE,
  calcula promedios por estudiante, show sample de 3+ estudiantes + estadísticas generales.
  Uso: `python scripts/zoom-asistencia/consultar_asistencia.py`

**Datos verificados (2026-07-13):**
- 490 estudiantes únicos con registros de asistencia
- 704 registros totales (sesiones de clase)
- Promedio general: 71.9%
- 161 estudiantes con <70% de promedio

**Coordinación con las clases (agregado 2026-07-01):** como cada clase se programa una a una
en Zoom con el nombre del curso como tema, el nodo Code agrega a cada fila:
- `Curso` = topic de la reunión (de `Info Reunion`, fallback al payload del webhook).
- `Fecha` = fecha/hora de inicio **real** en hora Colombia (UTC-5 fijo, formato
  `YYYY-MM-DD HH:MM`).
Así las filas de cursos distintos (o del mismo curso en fechas distintas) quedan
distinguibles aunque caigan en la misma hoja. **Regla operativa:** quien programe las salas
debe nombrar la reunión con el nombre del curso de forma consistente — el valor de `Curso`
sale literal de ahí. Si en el futuro se cambia a reuniones recurrentes por curso, evaluar
mapeo por Meeting ID (más robusto que el topic).

Diseño final esperado en producción: Nombre, Apellido, Correo electrónico, Identificación,
**Instancias** (formato `"N/3"`), Validar. La columna "Validar" usaría fórmula existente que
compara contra hoja `Seguimiento` (columnas E:F = Correo e Identificación de la lista maestra
de inscritos). La automatización NO necesita calcular "Validar" — solo alimentar las 4
columnas crudas + `Instancias`. Se escribe una fila por participante único, sin filtrar por
cuántos momentos cumplió.

## Decisiones de diseño clave
- Server-to-Server OAuth elegido sobre OAuth clásico para evitar flujo de consentimiento
  de usuario (proceso desatendido). [Confirmar al implementar]
- **2026-07-01 — Trigger:** Webhook `meeting.ended` en vez de Google Calendar. Motivo:
  Calendar introducía desfases de horario y dependía de que el link/Meeting ID quedara
  siempre en la descripción del evento (no garantizado).
- **2026-07-01 — Endpoint de participantes:** `past_meetings/{uuid}/participants` en vez de
  `report/meetings/{id}/participants`. Motivo: el endpoint de reportes consolida asistencia
  total pero no expone `join_time`/`leave_time` por sesión individual, que es lo que se
  necesita para verificar los 3 momentos dorados. `past_meetings` sí los expone y está
  disponible mucho más rápido tras el fin de la reunión.
- **2026-07-01 — Requisito de 3 instancias:** un alumno solo cuenta como presente si estuvo
  conectado en minuto 10, mitad de la clase y 10 min antes del fin — no basta con
  aparecer en el reporte consolidado. Cálculo hecho en un nodo Code (ver script en sesión
  2026-07-01), horas basadas en `start_time`/`duration` **reales** de `/past_meetings/{uuid}`
  (no en los programados que trae el webhook).
- **2026-07-01 — Sin filtrado, columna Instancias:** se registran todos los participantes
  conectados, sin excepción. En vez de descartar a quien no cumple los 3 momentos, se
  agrega la columna `Instancias` con el conteo (`"0/3"`..`"3/3"`). La decisión de qué
  hacer con asistencias parciales queda para un proceso posterior, no esta automatización.
- **2026-07-01 — Separación Nombre/Apellido:** heurística simple — primer espacio del
  nombre completo separa Nombre de Apellido (todo lo demás va a Apellido). No se
  complica más porque la validación fuerte del Sheet corre por Correo/Identificación,
  no por el nombre.
- **2026-07-02 — Pestaña `ZOOM-ASISTANCE` + `CUPOS` + `ZOOM-STATS`:** el destino de escritura
  pasó de `H3Test` a `ZOOM-ASISTANCE` (nodo renombrado a `Escribir Asistencia ZOOM-ASISTANCE`
  vía API). Las estadísticas se hacen con **fórmulas en el propio Sheet** (no script Python +
  JSON como el dashboard) para que se actualicen solas con cada asistencia sin depender de
  ejecutar nada — el equipo las ve donde ya trabaja. Los cupos por clase salen del análisis
  local de la BD pseudonimizada (sin PII: solo nombre de clase + conteo). El match
  topic-Zoom → clase-BD es por nombre exacto o por la columna `Alias Zoom` de `CUPOS`
  (editable a mano) — mapeo por Meeting ID sigue como alternativa futura.
- **2026-07-02 — Columna `% Asistencia`:** porcentaje de la clase que el estudiante estuvo
  conectado, como dato crudo adicional a `Instancias`. Cálculo en el mismo nodo Code
  (`porcentajeAsistencia()`): ordenar intervalos por join, fusionar solapados/contiguos
  (`join <= leave` del anterior), recortar cada intervalo fusionado a `[inicio, finReal]`
  (esto además garantiza que nunca supere 100%), sumar ms conectados / duración real,
  `Math.round`, formato `"NN%"`. El nodo Sheets no requirió cambios (auto-map por nombre
  de columna) — solo se agregó el header `% Asistencia` en `H1` vía gspread.

## Implementación en n8n (sesión 2026-07-01)

Workflow `Zoom - Asistencia` (ID `jkNaE51PKQ4TQzNq`), activo. JSON exportado a
`n8n-workflows/zoom-asistencia.json`.

**Nodos (14):**
`Webhook Trigger` → `Es validacion CRC?` (IF) →
- rama TRUE (CRC): `Hash CRC` (Crypto/Hmac) → `Responder CRC` (Respond to Webhook, JSON con
  `plainToken`+`encryptedToken`)
- rama FALSE (evento real): `Hash Firma Zoom` (Crypto/Hmac sobre
  `v0:{timestamp}:{JSON.stringify(body)}`, igual al ejemplo oficial de Zoom) → `Firma valida?`
  (IF, compara `"v0=" + hash` contra header `x-zm-signature`) →
  - TRUE: fan-out a dos ramas paralelas desde el mismo nodo — `Responder OK` (ack 200
    inmediato, sin esperar el resto) **y** `Esperar 90s` (Wait) → `Obtener Token Zoom`
    (HTTP POST a `zoom.us/oauth/token`, Basic Auth con client_id/secret, query
    `grant_type=account_credentials&account_id=...`) → `Info Reunion` → `Participantes`
    (paginado nativo del nodo HTTP Request, parámetro `next_page_token`) →
    `Calcular Momentos Dorados` (Code, mismo archivo que
    `scripts/zoom-asistencia/nodo-calcular-momentos-dorados.js`) → `Escribir Asistencia
    ZOOM-ASISTANCE` (Google Sheets Append, auto-map por nombre de columna; hasta el
    2026-07-02 se llamaba `Escribir Asistencia H3Test` y escribía en la pestaña `H3Test`)
  - FALSE: `Responder Firma Invalida` (401)

**Credenciales creadas en n8n (vía API, no vía UI):**
- `Zoom S2S Basic Auth` (httpBasicAuth) — client_id/client_secret de Zoom, usada solo por
  `Obtener Token Zoom`.
- `Zoom Webhook HMAC Secret (real)` (tipo `crypto`) — **Secret Token real** de Zoom
  (`3c9DF8ArSpiKeQLj15l8lQ`), configurado 2026-07-01. Reemplazó a la credencial placeholder
  original: como la API pública de n8n no permite editar credenciales existentes, se creó una
  credencial nueva vía API y se reapuntaron los nodos `Hash CRC` y `Hash Firma Zoom` a ella
  (también vía API, actualizando el JSON del workflow) — la credencial placeholder vieja se
  borró. Verificado con una prueba CRC sintética: el hash calculado coincide exactamente con
  el valor esperado usando el secreto real.
- `Q10 Automatizacion Service Account` (tipo `googleApi`) — reutiliza el mismo Service Account
  de `credenciales_service_account.json` que ya usan los scripts Python de Q10. Confirmado con
  acceso de escritura a `H3Test` antes de construir el nodo.

**Decisión de diseño — por qué NO se usó el flujo OAuth2 "Client Credentials" nativo de n8n
para Zoom:** Zoom exige `grant_type=account_credentials` (propietario, no estándar), mientras
que el flujo Client Credentials genérico de n8n fuerza `grant_type=client_credentials` en el
body. En vez de pelear con esa incompatibilidad, se usa un nodo HTTP Request manual
(`Obtener Token Zoom`) con Basic Auth + query params explícitos — mismo patrón que ya se había
probado con `curl` en la sesión anterior. Los nodos siguientes leen
`$('Obtener Token Zoom').item.json.access_token` vía expresión.

**Pruebas realizadas (payloads sintéticos, sin tocar una reunión Zoom real):**
1. CRC (`endpoint.url_validation`) — HMAC calculado por el nodo coincidió byte a byte con el
   valor calculado independientemente en Python. ✅
2. `meeting.ended` con firma válida — ack en ~40ms (antes de que corriera el resto), y la
   ejecución en segundo plano confirmó: `Esperar 90s` pausó y resumió correctamente, el fan-out
   desde `Firma valida?` a dos ramas en paralelo funciona, `Obtener Token Zoom` obtuvo un
   `access_token` real y válido (Zoom lo aceptó), `Info Reunion` construyó la URL con doble
   `encodeURIComponent` y devolvió un 404 **legítimo de la API real** de Zoom
   (`"Meeting does not exist: fake-uuid-test-123"`) — confirma que la cadena de auth y
   construcción de URL es correcta; solo falló por ser un UUID inventado. ✅ hasta ese punto.
3. **Prueba real completa (2026-07-01, reunión de 36 min con 2 participantes):** ejecución
   #37 exitosa en todos los nodos. Hallazgos que validan el diseño:
   - **Agrupación por reconexión funcionó:** un participante se desconectó y reconectó
     (2 sesiones de Zoom con 1 segundo de diferencia) y quedó como **una sola fila** con sus
     intervalos combinados — exactamente el comportamiento diseñado para el gotcha de
     `user_id` cambiante.
   - **Momentos dorados correctos:** reunión 21:14:56Z + 36 min → checkpoints en min 10,
     mitad y min 26; ambos participantes conectados todo el tiempo → `3/3`. ✅
   - **Doble URL-encode del UUID confirmado:** el UUID real terminaba en `==` y la API lo
     aceptó con el doble encode que usa el workflow (no devolvió 404).
   - **La primera ejecución real (#36) falló en `Obtener Token Zoom`** con `invalid_client`:
     la credencial Basic Auth en n8n quedó corrupta tras una edición manual en la UI (el
     Secret Token del webhook se guardó encima del client secret). Se recreó como
     `Zoom S2S Basic Auth v2` vía API y se reintentó **reenviando el mismo `meeting.ended`
     firmado localmente con el Secret Token y el UUID real** — patrón útil: no hace falta
     repetir la reunión para reintentar, Zoom conserva los datos del meeting terminado.
   - Limitación de esta prueba: ambos participantes tenían cuenta Zoom con sesión iniciada
     (por eso `user_email` vino lleno y no hubo que parsear del nombre). El escenario real de
     estudiantes invitados que escriben "Nombre correo cédula" en texto libre queda por
     probar (Prueba 4 del plan).
4. **Validación de `% Asistencia` (2026-07-02, ejecución #44):** se reenvió el mismo
   `meeting.ended` firmado localmente (UUID real de la reunión de prueba — Zoom conserva
   los datos del meeting terminado). Filas escritas con `98%` y `96%`, coherentes con la
   reunión de 36 min; el participante con reconexión no sumó doble ni superó 100%. Se
   eliminaron del Sheet las filas viejas duplicadas de esa reunión de prueba. ✅
   Nota: la clase real "Desarrollo Web - GIT, HTML y CSS" del 2026-07-01 (51 filas,
   ejecución #40) corrió *antes* de agregar la columna y sus filas quedaron con
   `% Asistencia` vacío. Se rellenaron retroactivamente el 2026-07-02 con un script
   puntual: UUID sacado de los datos de la ejecución #40
   (`GET /api/v1/executions/40?includeData=true`), participantes re-consultados a
   `past_meetings/{uuid}/participants` (Zoom conserva los datos) y misma lógica de
   fusión de intervalos del nodo Code; match por correo contra las filas del Sheet —
   51/51 emparejadas. Patrón reutilizable si vuelve a faltar un dato retroactivo.

## Gotchas / Limitaciones conocidas
- **Crítico, sin resolver:** Email e Identificación se capturan como texto libre manual
  por el estudiante al unirse (no vía formulario de registro de Zoom estructurado).
  Esto implica parseo de texto sucio, alto riesgo de error de formato humano.
  Escenarios posibles: (A) todo en el campo "nombre", (B) campos de registro de Zoom
  estructurados, (C) fuente separada (Form/chat). Aún sin confirmar cuál aplica.
- **Correlación de sesiones por participante:** Zoom asigna un `id`/`user_id` nuevo cada
  vez que un invitado sin login se reconecta, por lo que no sirve como clave de
  agrupación entre reingresos. El diseño agrupa por email extraído (si aparece) o por
  nombre normalizado como fallback — impreciso si el estudiante escribe su nombre
  distinto entre reingresos.
- Meeting IDs no son fijos — hay que resolverlos dinámicamente, no se puede hardcodear.
  Para `past_meetings` se necesita además el **UUID** (no el ID numérico), y si el UUID
  empieza con `/` o contiene `//` hay que URL-encodearlo **dos veces** en el path o la
  API responde 404 sin explicación.
- El reporte de participantes de Zoom puede no estar disponible inmediatamente al
  terminar la reunión — mitigado con `Wait` 90s + `Retry On Fail` en las llamadas HTTP,
  no hay garantía absoluta de tiempos.
- Clases muy cortas (duración ≤ 20 min) hacen que los 3 checkpoints colapsen o se
  inviertan en el cálculo — caso límite sin manejo especial todavía.
- **Control temprano (rama `meeting.started`) — gotchas anticipadas (2026-07-04):**
  (a) *Lag del Dashboard en vivo:* los datos `type=live` de Zoom pueden atrasarse 1-2 min;
  a los 10 min deberían estar completos, pero si el snapshot sale corto, subir el `Wait` a
  12-13 min. (b) *`meeting.started` dispara para CUALQUIER reunión* (pruebas, reuniones
  no-clase) — mismo problema de filtrado que la rama completa, aún sin filtro por topic/host.
  (c) *El `Wait` de 10 min mantiene viva la ejecución:* si el PC/n8n se reinicia o cae el túnel
  durante esos 10 min, se pierde ese snapshot temprano (la toma completa al `meeting.ended` no
  se afecta). (d) *Correo vacío en invitados sin login:* el endpoint live a veces no trae email
  — mismo parseo tolerante desde el `name`. (e) *Reinicios de reunión* → varios
  `meeting.started` → varios snapshots, diferenciados por `Curso`+`Fecha`.
- **BLOQUEANTE confirmado 2026-07-06 — la Dashboard API exige habilitar la "Dashboard feature"
  a nivel de cuenta, NO basta el scope ni el plan Business.** Primera prueba real de la rama
  `meeting.started` (ejecución #85, reunión "TEST TOMA TEMPRANA AUTOMATICA N 1"): el flujo corrió
  perfecto de punta a punta — recibió el evento, `Esperar 10 min` completó exacto (webhook 14:50Z
  → llamada 15:00Z), `Obtener Token Zoom 2` obtuvo token, doble-encode del UUID correcto — y solo
  falló el nodo `Participantes en Vivo` con **HTTP 400, body `{"code":200,"message":"This API is
  only available for ZMP and Business or higher accounts that have enabled the Dashboard
  feature."}`**. Diagnóstico independiente: se reprodujo la llamada `GET
  /metrics/meetings/{uuid}/participants` con `type=live` **y** `type=past` (token con el scope
  correcto) y **ambas** dieron el mismo error → no es scope (los errores de scope son `code 4711`),
  no es código, no es timing de la reunión en vivo. Es un **feature flag de cuenta de Zoom**.
  **Fix (pendiente de Samuel, admin/owner en zoom.us):** (1) verificar que **Admin → Dashboard /
  Analytics** aparezca y muestre datos; (2) **User Management → Roles → [rol] → Role Settings →
  Dashboard → View**; (3) si sigue fallando, pedir a **soporte de Zoom** que habilite la Dashboard
  feature / Dashboard API para la cuenta (varios hilos del dev forum terminan en soporte).
  **Re-prueba rápida cuando se habilite:** no hay que esperar otros 10 min — con una reunión viva,
  llamar directo `GET /metrics/meetings/{uuid}/participants?type=live` con un token fresco; era el
  único nodo que fallaba. **Scope confirmado correcto (2026-07-06):** el granular es
  `dashboard:read:list_meeting_participants:admin` (NO el clásico `dashboard_meetings:read:admin`
  tentativo); verificado leyendo el campo `scope` de un token S2S recién pedido.
  **Desenlace del ticket (2026-07-07):** Zoom Support **cerró el caso sin habilitar nada** —
  respuesta oficial: el issue es "configuration-related", fuera del alcance del Developer Support
  Plan gratuito; derivan al Developer Forum o a planes de soporte developer de pago. Es decir:
  Zoom NO va a activar el flag por esta vía. Alternativa elegida para desbloquear la rama de
  10 min **sin Dashboard API**: eventos webhook `meeting.participant_joined` /
  `meeting.participant_left` (incluidos gratis en la misma app S2S, misma URL/CRC/firma) —
  presencia al minuto 10 = joined − left acumulados. Ventaja extra: elimina la dependencia del
  flag también para la futura cuenta soporte (habría que pedirlo dos veces).
- **Confirmado 2026-07-02 (clase de las 10, caso real):** el webhook no se disparó porque la
  reunión seguía técnicamente abierta — un participante quedó conectado (se durmió) sin salir
  ni ser removido, y el host no cerró con "Finalizar reunión para todos". `meeting.ended` solo
  llega cuando la sala queda realmente vacía o el host la fuerza a terminar; una clase que
  "ya terminó" en la práctica pero sigue con alguien conectado no genera el evento, y por lo
  tanto no se registra asistencia hasta que alguien cierre la reunión de verdad. Sin mitigación
  automática todavía — a evaluar si conviene una alerta operativa o límite de tiempo.
  **Desenlace (mismo día):** la sala se cerró a las 12:24 y el `meeting.ended` real llegó solo
  — ejecución #46 escribió las 51 filas correctamente (duración real registrada: 148 min para
  una clase de ~2h). El evento llega tarde, pero llega; no hubo que reenviar nada.
- **Locale del spreadsheet es `es_ES`:** toda fórmula escrita vía API (values USER_ENTERED
  **y** `CUSTOM_FORMULA` de formato condicional) debe usar `;` como separador de argumentos
  y `\` como separador de columnas dentro de literales de array `{...}` — con `,` la API
  responde 400 (`Invalid ConditionValue.userEnteredValue`) o la fórmula queda rota. Los
  nombres de función sí van en inglés. Ver helper `loc()` en `setup_zoom_asistance.py`.
- **Al validar por polling de ejecuciones, no asumir que la primera "success" reciente es la
  tuya:** durante la prueba del cambio de pestaña, el evento real tardío de la clase de las 10
  (#46) llegó en paralelo con el reenvío sintético (#48) y confundió la verificación — además
  las ejecuciones en `Wait` no aparecen en la lista hasta resolverse. Confirmar por el body
  del Webhook Trigger o por el conteo de items, no por timestamp.
- **% muy bajo (o 0/3) con presencia real = desconexión del lado del participante, NO bug del
  cálculo.** Confirmado 2026-07-03 (reunión "Prueba - Asistencia" 15:11, ejecución #54):
  Cristian (soporte.it@) salió con 1% y 0/3 aunque, según él, estuvo toda la clase. Al inspeccionar
  los datos crudos que devolvió Zoom (`GET past_meetings/{uuid}/participants`), Zoom solo lo
  reportó conectado ~50 s en dos micro-sesiones contiguas (15:12:57→15:13:18 y 15:13:18→15:13:47,
  `duration` 21 s y 29 s que calcula el propio Zoom) y **ningún registro después**. No fue paginación
  (`total_records: 4`, `page_count: 1`, sin `next_page_token`). 50 s / 3600 s = 1% y los 3 checkpoints
  caen después de su última salida → 0/3. **El cálculo es fiel a lo que Zoom vio.** Causa real:
  la app local puede seguir mostrando la reunión mientras el servidor ya soltó al participante
  (desconexión silenciosa); los dos micro-cortes iniciales delatan mala conexión. **Cómo verificar
  sin adivinar:** portal de Zoom → Reports → Usage → esa reunión → Participants (misma fuente que la
  API) o bajar los `join_time`/`leave_time` crudos de la ejecución vía
  `GET /api/v1/executions/{id}?includeData=true`. Si un reingreso hubiera usado otra identidad/correo,
  aparecería como registro extra (fila separada por la clave de agrupación) — aquí no lo hubo.
- Zoom cambió el catálogo de scopes granulares varias veces en 2023-2024 — confirmados
  `meeting:read:past_meeting:admin` y `meeting:read:list_past_participants:admin` cruzando
  doc oficial + hilo de Zoom Community (no verificado 100% contra la pantalla real del
  Marketplace, la doc de Zoom es una SPA que no se puede scrapear directo).
- **La URL pública de cloudflared es efímera** — cambia cada vez que se reinicia el túnel
  (y `iniciar_n8n.bat` lo reinicia solo si detecta que cayó). Si esto pasa después de
  configurar el Event Subscription en Zoom, el CRC deja de validar hasta que se actualice
  la URL manualmente en el Marketplace. Evaluar túnel nombrado (no efímero) antes de
  producción real.
  **Incidente real (2026-07-02/03):** el quick tunnel murió en silencio (probablemente al
  dormirse el PC en la tarde) — el registro DNS del hostname desapareció de Cloudflare
  aunque el proceso cloudflared local seguía "conectado" según sus métricas, y n8n además
  dejó de disparar sus schedules. Resultado: los `meeting.ended` de al menos 2 reuniones
  ("Entrevista Nova", "Mi vida sí importa") rebotaron y no se registró asistencia. Zoom
  reintenta pocas veces y desiste, pero **conserva los datos**: la asistencia es
  recuperable con el patrón de reenvío sintético si se consigue el Meeting ID/UUID (portal
  de Zoom → Reports, o agregar scopes `user:read:list_users:admin` +
  `meeting:read:list_meetings:admin` para listarlas por API). Diagnóstico útil: comparar
  el hostname de `http://127.0.0.1:20241/quicktunnel` contra DNS real (`Resolve-DnsName
  ... -Server 1.1.1.1`) y revisar si el Schedule 4h de Q10 se saltó ticks. **Cada logon de
  Windows re-corre `iniciar_n8n.bat` (Task Scheduler) → URL nueva → hay que actualizar el
  Marketplace de Zoom cada vez** — el túnel nombrado dejó de ser opcional, es urgente.
  **Rotación 2026-07-03:** túnel nuevo `https://based-disco-yale-traveller.trycloudflare.com`
  (webhook Zoom → `.../webhook/zoom-asistencia`). Ruteo público verificado con POST dummy
  (n8n respondió 401 por firma inválida = enrutó bien). Aclaración importante sobre el
  procedimiento de rotación: **el nodo n8n NO guarda la URL** — `iniciar_n8n.bat` fija
  `WEBHOOK_URL=<túnel>` y mata la instancia vieja, así que tanto el Webhook de Zoom como el
  Telegram Trigger heredan la URL nueva solos al reiniciar. Lo único que NO es automático y
  NO se puede hacer por la API pública de n8n es la **URL del Event Subscription en el Zoom
  Marketplace** (editar a mano). Para el Telegram Trigger, si se quiere forzar el re-registro
  (`setWebhook`) sin reiniciar todo, basta desactivar+activar el workflow `Bot Q10` por API
  (`POST /workflows/{id}/deactivate` → `/activate`); el `activate` en 200 confirma que
  Telegram aceptó la URL nueva. Hecho hoy tras la rotación.
  **Rotación 2026-07-06 (tras reinicio de PC):** al arrancar, el `cloudflared` del logon había
  muerto en silencio otra vez — el proceso seguía vivo y `http://127.0.0.1:20241/quicktunnel`
  reportaba el hostname viejo (`based-disco-yale-traveller`), pero ese hostname ya **no resolvía en
  DNS** (`Non-existent domain`) y un POST público daba `HTTP 000`. Se levantó túnel nuevo
  `https://automotive-cluster-amp-shared.trycloudflare.com`, se reinició n8n con ese `WEBHOOK_URL`
  (matando el node viejo) y se re-activó Bot Q10 (Telegram aceptó la URL nueva). Ruteo verificado
  con el **handshake CRC completo**: se envió un `endpoint.url_validation` y el `encryptedToken`
  devuelto coincidió byte a byte con el HMAC calculado con el Secret Token real → prueba de que la
  validación de URL de Zoom pasará. Se pegó la URL nueva en el Event Subscription del Marketplace.
  **Decisión tomada 2026-07-06:** montar túnel **nombrado + servicio de Windows** (URL fija que no
  rota) es ya prioridad; se evaluó usar un subdominio de `tocaunavida.org` **delegado** a Cloudflare
  (NO mover todo el dominio: el correo de la fundación vive ahí — mover los nameservers del apex
  arriesga los MX). **Resuelto con ngrok (2026-07-06):** como la URL del webhook solo la consume Zoom
  (máquina a máquina, nadie la escribe), se descartó el enredo del DNS/Cloudflare y se optó por un
  **dominio estático gratuito de ngrok**: `ergonomic-absinthe-refract.ngrok-free.dev` (URL webhook
  `.../webhook/zoom-asistencia`). Ver detalle y estado en la memoria [[reference-ngrok-tunel-fijo]].
  Gotchas: (a) el agente ngrok debe ser **≥ 3.20** (la cuenta rechaza viejos — se actualizó a 3.39.9);
  (b) `ngrok service install` pide **admin** (falló con "Acceso denegado") → se arranca por
  `iniciar_n8n.bat` en el logon, igual que n8n; (c) free tier = **un solo agente** simultáneo. Tras
  reiniciar n8n con `WEBHOOK_URL` = dominio fijo, el Telegram Trigger se re-registró solo contra ngrok
  (visto tráfico `91.108.*` en el log). **Migración cerrada 2026-07-07:** `iniciar_n8n.bat` ya arranca
  `ngrok start n8n` con `WEBHOOK_URL` hardcodeada al dominio fijo (verifica el túnel vía la API local
  `:4040` y el watchdog lo revive si cae); cloudflared retirado del arranque. Verificado end-to-end:
  healthz público 200 por la URL fija y handshake CRC de Zoom OK (`endpoint.url_validation` devolvió
  `encryptedToken`). **Falta solo:** Samuel repega la URL fija en el Event Subscription de Zoom
  comunicaciones y pulsa Validate.
- **`iniciar_n8n.bat` no corre desatendido:** `timeout /t` falla con "No es compatible la
  redirección de entradas" cuando el bat corre sin consola interactiva (WMI, background) —
  las esperas se vuelven no-ops y el watchdog queda en loop apretado. Para arranques
  desatendidos usar esperas con `powershell -Command "Start-Sleep N"`.
- Activar Event Subscriptions no pide la URL del webhook durante el Publish/Activate de
  la app — son pasos independientes. Publish solo habilita las credenciales OAuth; el
  webhook se configura aparte en el tab Feature → Event Subscriptions, y esa pantalla
  necesita una URL que ya esté respondiendo (o falla el CRC) — por eso hay que construir
  el workflow de n8n con el Webhook Trigger *antes* de pegar la URL en Zoom.
- Infraestructura: n8n corre local en PC de Samuel (EstudiantesJC) + ngrok dominio fijo para tunnel (cloudflared retirado 2026-07-07); decisión pendiente sobre mover a máquina dedicada para estabilidad en horario laboral.
- **Nodo Crypto (v2) exige credencial dedicada para Hmac:** a diferencia de otros nodos, el
  secreto no va como parámetro de texto plano en el nodo — n8n obliga a crear una credencial
  de tipo `crypto` (campo `hmacSecret`) y asociarla. Como la API pública de n8n no permite
  editar credenciales existentes, actualizar el Secret Token real de Zoom requiere entrar a la
  UI (Credentials → `Zoom Webhook HMAC Secret` → editar `hmacSecret`) — no se puede hacer con
  un curl más.
- **`iniciar_n8n.bat` ahora también carga `scripts/zoom-asistencia/.env`** como variables de
  entorno del proceso n8n (antes solo cargaba el `.env` de q10-consolidacion). No se usó para
  el Secret Token final (se optó por credencial `crypto` en vez de `$env` en un Code node),
  pero queda disponible por si se necesita en el futuro. Requiere reiniciar n8n para tomar
  cambios del `.env`.
- **El endpoint de ejecuciones de n8n no muestra ejecuciones en estado "esperando"
  inmediatamente** en `GET /api/v1/executions` (ni con `status=waiting`) — solo aparecen una
  vez que se resuelven (tras el `Wait` de 90s). Para verificar una ejecución en curso hay que
  consultar `GET /api/v1/executions/{id}` directo si se conoce el ID, o esperar a que termine.

## Contingencia manual

Proceso en diseño — no hay contingencia definida aún. Al implementar, documentar aquí:
el paso manual equivalente si n8n falla durante una sesión Zoom.

## Conexiones del sistema

- [[mapa-codigo]] — al implementar, los scripts asociados quedarán documentados ahí
- [[convenciones]] — Server-to-Server OAuth (Zoom), SSL corporativo
- [[q10-consolidacion]] — patrón de trigger Telegram + n8n reutilizable
- [[dashboard-web]] — si se decide publicar estadísticas de asistencia, este proceso alimentaría un tab adicional
- [[zoom-youtube]] — proceso hermano (documentado, sin implementar): reusa esta misma app
  Zoom Server-to-Server OAuth, el webhook, el patrón CRC + firma y el túnel cloudflared;
  solo agrega el scope de cloud recording y el evento `recording.completed`

## Cobertura multi-cuenta — HALLAZGO 2026-07-06 (crítico)
La operación usa **dos cuentas Zoom Business independientes** (las "2 salas"), en data centers
distintos: **comunicaciones** (`us06web.zoom.us`, owner/host `comunicaciones@`) y **soporte**
(`us02web.zoom.us`, host `soporte@tocaunavida.org`). Cada clase se dicta en una u otra según el
horario, y hoy la asistencia se baja **a mano** del reporte xlsx de **ambos** portales.
**El app S2S + webhook viven SOLO en la cuenta comunicaciones** (`account_id`
`u08qlWbRTR2VBSs0bRwZPQ`). Verificado empíricamente cruzando las **38 ejecuciones** del workflow:
todos los eventos reales traen `account_id = u08qlWbRTR2VBSs0bRwZPQ`; **ninguno** de los meeting
IDs de soporte (ej. clases del 04/07 con 49-52 estudiantes: `84494282122`, `81862716235`,
`85042920015`, `89270387162`) aparece en n8n. Los 2 `host_id` que sí vemos
(`5Ehn8O03Q6y4lRRGpV8c9w`, `UUQqk6BdSYuNzHL0YFOqfg`) son **dos usuarios dentro de comunicaciones**,
no dos cuentas. **Conclusión: la mitad de las clases (las de soporte) NO se están capturando
automáticamente** — ni `meeting.ended` ni el de 10 min.
**Para cubrir soporte** hace falta: (1) un **2º app S2S** en la cuenta soporte (mismos scopes) con
sus eventos suscritos a la **misma URL** del webhook; (2) ajustar el workflow para multi-cuenta,
porque el **Secret Token del webhook es distinto por cuenta** → `Firma valida?` debe elegir el
secreto por `payload.account_id`, y el **token de API** debe pedirse con las **credenciales de la
cuenta dueña** de la reunión (el token de comunicaciones no lee reuniones de soporte) → `Obtener
Token Zoom` debe elegir credencial por `account_id`. El resto (cálculo, escritura a Sheets) ya es
genérico. La **Dashboard API** (feature de 10 min) habrá que habilitarla por soporte de Zoom en
**ambas** cuentas.

## Pendiente / Próximos pasos
- [ ] **Integración Supabase asistencia (2026-07-13):** crear tabla `asistencia_zoom` en
  proyecto Supabase `panel-datos-rofe`, script `sync_asistencia_supabase.py` con patrón
  similar a `sync_aprobacion_supabase.py`, upsert post-clase. Permite consultas combinadas
  (asistencia + aprobación por estudiante). Ver sección "Integración con Supabase" arriba.
  Posterior a producción de Sheets — no bloquea.
- [ ] **Crear pestañas LIVE-LOG + ASISTENCIA-10MIN (2026-07-13)** — ✅ hecho:
  `python setup_zoom_asistance.py --solo-livelog` y `--solo-10min`. Ambas listas para
  recibir datos de la rama `meeting.participant_joined/_left` y control temprano.
- [ ] **Túnel fijo ngrok — último paso:** Samuel repega la URL fija
  (`https://ergonomic-absinthe-refract.ngrok-free.dev/webhook/zoom-asistencia`) en el Event
  Subscription de Zoom comunicaciones y valida. Lo demás ya quedó (2026-07-07): `iniciar_n8n.bat`
  arranca ngrok, cloudflared retirado, CRC verificado. Ver [[reference-ngrok-tunel-fijo]].
- [ ] **Cobertura cuenta soporte (us02web) — BLOQUEADO en acceso:** la cuenta Zoom de soporte la
  **facilita Colegio Colombia 2020** (owner `colegiocolombia2020@gmail.com`); Samuel no puede crear el
  app S2S ahí (no tiene el permiso de desarrollador). **Se redactó una solicitud formal** (carta HTML
  con membrete ROFÉ + borrador de correo en el Gmail de Samuel, dirigido a `soportejunior@`) pidiendo:
  Opción A (recomendada) que le den el permiso "Aplicación de OAuth de servidor a servidor" a
  `soportejunior@tocaunavida.org`, u Opción B que ellos creen el app y compartan los 4 valores.
  Cuando concedan acceso → clonar el workflow como flujo aislado con path `…/webhook/zoom-asistencia-soporte`
  (su propio crypto/secret y Basic Auth; comunicaciones no se toca). Ver "Cobertura multi-cuenta" arriba.
- [x] ~~Ticket a soporte de Zoom — habilitar Dashboard API (métricas)~~ — **CERRADO SIN ACCIÓN
  por Zoom (2026-07-07):** "configuration-related, not within the scope of your account's
  Developer Support Plan"; derivan al Developer Forum o soporte developer de pago. Ver
  desenlace completo en el gotcha "BLOQUEANTE confirmado 2026-07-06".
- [ ] **Rediseñar la rama de 10 min sin Dashboard API:** suscribir `meeting.participant_joined`
  y `meeting.participant_left` en la misma app S2S (misma URL webhook, gratis, sin flag de
  cuenta), acumular joins/leaves (pestaña helper o static data de n8n) y al minuto 10 calcular
  presentes = joined − left. Opcional en paralelo: post en el Zoom Developer Forum por si un
  staff activa el flag (gratis, sin bloquear el rediseño).
- [x] Crear app Server-to-Server OAuth en Zoom Marketplace y publicarla/activarla —
  credenciales guardadas en `scripts/zoom-asistencia/.env` (gitignoreado), probadas con
  `curl` contra `zoom.us/oauth/token` → HTTP 200, token obtenido correctamente (2026-07-01).
- [x] Confirmar en la pantalla real de Scopes que `meeting:read:past_meeting:admin` y
  `meeting:read:list_past_participants:admin` existen tal cual y marcarlos — confirmado por
  Samuel (2026-07-01).
- [ ] Confirmar cómo se captura hoy Email/ID en la sesión real (revisar un CSV de
  asistencia exportado de una clase pasada).
- [x] ID del Google Sheet destino (de pruebas) — `H3Test`,
  `1VyXOYsnpD9ksKcJFHiiRR6fr4UUCea4WmGG96NV0WP0`. El destino de producción con
  `Validar`/`Seguimiento` sigue pendiente de decidir.
- [x] Implementar el workflow en n8n — hecho vía API (`n8n-workflows/zoom-asistencia.json`),
  workflow `Zoom - Asistencia` activo. Ver sección "Implementación en n8n" arriba.
- [x] Event Subscriptions configurado en Zoom Marketplace, Secret Token real obtenido
  (`3c9DF8ArSpiKeQLj15l8lQ`) y aplicado en `scripts/zoom-asistencia/.env` +
  credencial `Zoom Webhook HMAC Secret (real)` en n8n (2026-07-01). Verificado con CRC
  sintético. **Gotcha aprendido:** el Secret Token de Zoom se genera al activar Event
  Subscriptions, *antes* de guardar la URL — hay que copiarlo primero, si no la validación
  de la URL falla con "URL validation failed. Try again later." aunque el endpoint esté
  respondiendo bien (firma con secreto equivocado, no problema de red).
- [x] Validación de URL en Zoom Marketplace pasó en verde y `meeting.ended` suscrito
  (2026-07-01). **Gotcha adicional:** la URL correcta es
  `https://<cloudflared>/webhook/zoom-asistencia` — un primer intento falló por pegar la URL
  del editor (`/workflow/<id>`), que no recibe eventos.
- [x] Prueba 1 (camino feliz con reunión real) — exitosa, ejecución #37. Ver sección de
  pruebas arriba. La Prueba 3 (salir y reentrar) quedó validada de paso en la misma reunión.
- [ ] Decidir filtro para reuniones que NO son clase (por prefijo del nombre de la reunión
  o por lista de cursos válidos) antes de producción — hoy el workflow escribe asistencia
  de *cualquier* reunión que termine en la cuenta.
- [ ] Prueba 2 del plan: reunión corta (≤20 min) para observar el caso límite de checkpoints
  colapsados/invertidos.
- [ ] Prueba 4 del plan: participante invitado sin sesión Zoom que escriba
  "Nombre correo cédula" en el campo de nombre — valida el parseo de texto libre
  (`RE_EMAIL`/`RE_CEDULA` del nodo Code), aún no ejercitado con datos reales.
- [ ] Probar con una reunión Zoom real (`meeting.ended` real) para validar `Participantes`,
  el nodo Code y la escritura en `Escribir Asistencia H3Test` — solo se probó hasta
  `Info Reunion` con datos sintéticos.
- [x] ~~Llenar `Alias Zoom` para el "X de Y"~~ — resuelto con el match por horario
  (área + día + hora del evento, 2026-07-02). El alias queda como override manual para
  casos ambiguos (grupos de la misma área que comparten franja horaria).
- [ ] Verificar con el equipo si grupos "Uno/Dos/Avanzado" de una misma franja se dictan
  en reuniones Zoom separadas — si es así, el cupo por horario los suma de más y hay que
  usar `Alias Zoom` para separar.
- [ ] Cuando se decida el Sheet de producción: re-ejecutar `setup_zoom_asistance.py` con el
  `SHEET_ID` nuevo (reconstruye ZOOM-ASISTANCE/CUPOS/ZOOM-STATS) y reapuntar el nodo del
  workflow.
- [ ] Decidir infraestructura final (portátil vs Raspberry Pi).
- [ ] Definir manejo de errores (ver `docs/convenciones.md`).
- [ ] Recordar rotar `ZOOM_CLIENT_SECRET` si se considera necesario — se pegó una vez en
  texto plano en el chat de una sesión de Claude Code (2026-07-01); no se subió a git,
  pero es buena práctica regenerarlo antes de ir a producción.
