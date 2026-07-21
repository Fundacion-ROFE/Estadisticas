# Grabaciones Zoom → YouTube (MR) / Drive (NOVA)

**Estado:** Activo. Dos destinos según topic: clases **MR → YouTube** (unlisted) y sesiones
**NOVA → carpeta de Drive** (MP4 + transcripción, rama agregada 2026-07-16). Backfill diario
`zoom-yt-backfill` activo como red de seguridad. **Bloqueado para el test end-to-end:**
re-consentimiento OAuth con scope de Drive (comando abajo) + suscribir el evento
`recording.transcript_completed` en el Marketplace.
**Última actualización:** 2026-07-16
**Procesos relacionados:** [[zoom-asistencia]] (misma app Zoom Server-to-Server OAuth)

## Qué hace
Automatiza la publicación de las grabaciones de clases/reuniones de Zoom en el canal de
YouTube de la Fundación. Hoy es un proceso manual (descargar el video de Zoom y subirlo a
mano). El objetivo: en cuanto Zoom termina de procesar una grabación en la nube, n8n la
descarga y la sube a YouTube sin intervención humana.

## Disparador (Trigger)
**Webhook de Zoom** suscrito al evento **`recording.completed`** (Event Subscriptions de la
misma app Server-to-Server OAuth que ya usa [[zoom-asistencia]]). Este evento se dispara
cuando la grabación **en la nube** terminó de procesarse y está lista para descargar — es
distinto de `meeting.ended` (ese marca el fin de la reunión, no la disponibilidad del video).

> Requiere **grabación en la nube** (Zoom Pro/Business o superior). La grabación local no
> genera este webhook — quedaría como archivo en el PC y habría que vigilar la carpeta.
> Confirmado que la cuenta es de pago → se usa la nube.

## Flujo resumido
1. Webhook recibe `recording.completed` → responde 200 de inmediato (mismo patrón CRC +
   validación de firma `x-zm-signature` que [[zoom-asistencia]]).
2. Obtener token Zoom (nodo HTTP `grant_type=account_credentials`, ya resuelto en zoom-asistencia).
3. Del payload se extrae la lista `recording_files`: elegir el archivo de tipo `MP4`
   (`recording_type` = `shared_screen_with_speaker_view` u otro según preferencia) y su
   `download_url`.
4. Descargar el MP4 desde `download_url`. La descarga necesita el `access_token` (o el
   `download_token` que Zoom incluye en el payload del webhook) — Zoom devuelve el binario.
5. Subir a YouTube con `videos.insert` (YouTube Data API v3): título = topic de la reunión
   + fecha, descripción/tags a definir, **privacidad configurable** (público según decisión).
6. [Opcional] Notificar por Telegram con el link del video publicado.
7. [Opcional] Registrar en un Sheet: reunión, fecha, URL de YouTube (trazabilidad).

## Fuentes de datos / APIs usadas
- **Zoom** — Server-to-Server OAuth (misma app de [[zoom-asistencia]]).
  - Webhook: evento `recording.completed`.
  - Scope adicional necesario: `cloud_recording:read:list_recording_files:admin` (o
    equivalente granular vigente — el catálogo cambia, ver nota en [[convenciones]]).
  - Descarga: `download_url` del payload + token (Bearer o `download_token`).
- **YouTube Data API v3** — `videos.insert` (upload resumable).
  - Requiere **OAuth 2.0 de usuario** (autorización del dueño del canal), **no** Service
    Account: YouTube no permite subir con Service Account a un canal normal. Hay que hacer
    el consentimiento una vez y guardar el `refresh_token`.
- n8n como orquestador (nodo YouTube nativo o HTTP Request resumable).

## Destino de los datos
Canal de YouTube de la Fundación ROFÉ / Jóvenes creaTIvos. Visibilidad: **pública** (decisión
de negocio 2026-07-03, con autorización previa de la Fundación por video). El default técnico
seguro sería `unlisted`; se usa `public` por decisión explícita.

## Decisiones de diseño clave
- **2026-07-03 — Viabilidad confirmada.** Es un caso estándar de n8n; reusa toda la
  infraestructura de Zoom S2S OAuth + webhook + túnel ngrok fijo de [[zoom-asistencia]].
- **2026-07-03 — Grabación en la nube, no local.** La cuenta es de pago → `recording.completed`
  dispara el flujo sin depender de que el PC esté encendido ni de vigilar carpetas.
- **2026-07-03 — Videos públicos con autorización.** El equipo autoriza cada publicación
  (proceso humano previo). Técnicamente se sube como `public`; a evaluar si conviene subir
  siempre como `unlisted` y que un humano lo pase a público tras revisar (barrera anti-error
  y anti-PII), dado que las grabaciones muestran rostros/nombres de jóvenes.
- **[Pendiente] Autenticación YouTube.** OAuth de usuario obligatorio (Service Account no
  sirve para canales normales). Guardar `refresh_token` de forma segura como el resto de
  credenciales.

## Gotchas / Limitaciones conocidas (anticipadas — sin implementar aún)
- **Cuota de YouTube API:** `videos.insert` cuesta **1.600 unidades** por subida y la cuota
  diaria por defecto es **10.000** → ~**6 subidas/día**. Si hay más clases grabadas al día,
  hay que solicitar ampliación de cuota a Google (formulario, tarda días en aprobarse).
- **OAuth de YouTube caduca / se revoca:** el `refresh_token` puede invalidarse (cambio de
  contraseña, revocación, inactividad prolongada de apps en modo *testing*). Publicar la app
  de OAuth (no dejarla en *testing*) para que el token no expire cada 7 días.
- **Privacidad / PII:** las grabaciones muestran rostros y nombres de menores/jóvenes.
  Publicarlas como públicas es una decisión sensible — el criterio de PII del proyecto (nada
  individual a público) aquí lo **anula una autorización explícita de la Fundación**, que debe
  quedar registrada. Considerar el patrón `unlisted` → revisión humana → `public`.
- **Tamaño y duración de la descarga:** una clase de 2 h en MP4 puede pesar cientos de MB —
  la descarga desde Zoom + la subida resumable a YouTube pueden tardar y consumir ancho de
  banda del PC de Samuel. Evaluar timeouts y reintentos.
- **~~Túnel efímero de cloudflared~~ — RESUELTO 2026-07-07:** [[zoom-asistencia]] migró a un
  dominio estático de ngrok (`ergonomic-absinthe-refract.ngrok-free.dev`) que no rota nunca;
  este proceso lo hereda gratis — la URL del Event Subscription se pega una sola vez.
- **`recording.completed` puede tardar:** Zoom procesa el video después de terminar la
  reunión; el webhook puede llegar minutos u horas después. No asumir inmediatez.
- **Retención de grabaciones en la nube:** Zoom borra las grabaciones en la nube según la
  política de retención de la cuenta — el flujo debe correr antes de que expiren (otra razón
  para automatizar y no depender de subida manual tardía).

## Conexiones del sistema
- [[zoom-asistencia]] — comparte la app Zoom Server-to-Server OAuth, el webhook, el patrón
  CRC + firma y el túnel ngrok fijo. Al implementar, reusar esa credencial y solo agregar el
  scope de cloud recording + suscribir el evento `recording.completed`.
- [[convenciones]] — Zoom Server-to-Server OAuth, SSL corporativo, túnel ngrok fijo.
- [[dashboard-web]] — a futuro, los links de YouTube podrían enlazarse desde algún panel.

## Pendiente / Próximos pasos
- [ ] **Decidir visibilidad final:** subir directo como `public`, o `unlisted` + pase manual a
      público tras revisión (recomendado por PII). Registrar la autorización de la Fundación.
- [ ] Confirmar el plan exacto de Zoom y que la **grabación en la nube** esté activada por
      defecto en las reuniones que se quieren publicar.
- [ ] Crear el proyecto/OAuth Client en Google Cloud para YouTube Data API v3; hacer el
      consentimiento una vez y guardar el `refresh_token`. Publicar la app (no *testing*).
- [ ] Solicitar ampliación de cuota de YouTube si se esperan >6 subidas/día.
- [ ] Agregar el scope de cloud recording a la app Zoom y suscribir `recording.completed`.
- [ ] Definir plantilla de metadatos del video: título (topic + fecha), descripción, tags,
      playlist destino.
- [ ] Definir manejo de errores (ver [[convenciones#Manejo de errores]]): reintento de
      descarga/subida, notificación si falla.
- [ ] Filtro de qué reuniones se publican (no toda grabación debe ir a YouTube) — por prefijo
      del topic o lista blanca, análogo al filtro pendiente de [[zoom-asistencia]].
- [ ] Contingencia manual documentada (el proceso actual: descarga + subida a mano).

---

## Plan de acción — Clases Mujeres ROFÉ → YouTube (2026-07-15)

**Objetivo:** en cuanto Zoom termina de procesar la grabación de una clase MR, descargarla y
subirla al canal de YouTube al que se accede con **comunicaciones@tocaunavida.org**.

### Verificaciones hechas (2026-07-15, read-only contra APIs reales)

- **Token S2S OK, pero SIN scope de grabaciones:** `GET /users/comunicaciones@.../recordings`
  respondió `4711 — does not contain scopes: [cloud_recording:read:list_user_recordings(:admin)]`.
  Scopes actuales del app: meeting read/write/delete, dashboard read, webinar read. Falta todo
  lo de cloud recording (y `user:read:list_users:admin`, útil para descubrir hosts).
- **Ninguna clase MR ha pasado por la cuenta comunicaciones desde 2026-07-01:** `asistencia_zoom`
  (que registra TODO `meeting.ended` de esa cuenta) solo tiene "Desarrollo Web - GIT, HTML y CSS"
  (+salas) y reuniones de prueba.
- **Nombres reales de cursos MR** (Supabase `courses`, programa=mr, 8 cursos): "De la idea a la
  acción, tu guía para emprender con éxito" (2 variantes de mayúsculas), "Empoderamiento en
  Ventas…", "Finanzas Inteligentes, gestión para emprendedoras", "Habilidades del Ser para
  emprendedoras…", "Transforma tu negocio con estrategias digitales", "Fundamentos Lógica de
  Programación - 2026", "Emprendimiento: Idea de Negocio JC". Naming inconsistente ⇒ el filtro
  debe ser por **palabras clave editables**, no match exacto.

### Fase 0 — Confirmaciones — RESUELTO 2026-07-15
**Corrección de Samuel:** las clases (todas, JC y MR) se dictan con el host
`comunicaciones@tocaunavida.org` — es la misma cuenta que ya usan [[zoom-asistencia]] y
[[zoom-crear-reunion]], y ahí se alojan las grabaciones que hay que enviar a YouTube. No se
agrega ningún host nuevo (se descarta la idea de mover MR a `mujeres.rofe@tocaunavida.org`
como host de Zoom — ese correo solo sigue siendo el remitente de campañas de correo).

**Consecuencia para el diseño:** como JC y MR comparten el mismo `host_email`, **no se puede
filtrar por host** — hay que volver al filtro por **tema/topic** de la reunión (palabras clave),
igual que se planteó originalmente. Ver Fase 3.

Confirmado por Samuel: se graba en la nube ✅, comunicaciones@ es owner del canal YouTube ✅,
cadencia baja (**máx. 2 clases MR/día**, muy por debajo de la cuota de 6 subidas/día) ✅.
Brand Account: no crítico — se resuelve solo en el selector de canal durante el consentimiento
OAuth de la Fase 2 (una cuenta de YouTube puede administrar varios "canales de marca"; solo hay
que elegir el correcto una vez).

**Nota abierta (no bloqueante):** al 2026-07-15 ningún topic con nombre de curso MR aparece
todavía en `asistencia_zoom` (que registra TODO `meeting.ended` de la cuenta comunicaciones
desde 2026-07-01) — probablemente porque las clases MR grabadas en esta cuenta son recientes o
aún no han corrido en el periodo observado. Se resuelve solo cuando corra la primera clase MR
real tras implementar el filtro; no requiere acción previa.

Visibilidad recomendada: `unlisted` al subir + humano lo pasa a público tras revisar (rostros/
nombres de participantes). Registrar la autorización de la Fundación.

### Fase 1 — Zoom Marketplace — HECHO 2026-07-15
- ✅ Scopes agregados y **verificados en vivo con un token real**: `cloud_recording:read:
  list_user_recordings:admin` y `cloud_recording:read:list_recording_files:admin`. Confirmado:
  `GET /users/comunicaciones@tocaunavida.org/recordings` pasó de `4711` a **200**, devolviendo
  11 grabaciones reales de los últimos 15 días con `download_url`/`file_size` por archivo
  (incluye el MP4 `shared_screen_with_speaker_view` que el script va a descargar). Todas son de
  "Desarrollo Web - GIT, HTML y CSS" (JC) o pruebas — ninguna con topic MR todavía (ver nota
  abierta arriba, no bloqueante).
- ✅ **Event Subscription agregada y validada (2026-07-15):** evento `recording.completed` →
  URL `https://ergonomic-absinthe-refract.ngrok-free.dev/webhook/zoom-grabaciones` (path nuevo,
  separado del de asistencia; mismo Secret Token del app). Zoom validó la URL en verde.
  **Verificado además con CRC sintético** (mismo patrón usado para zoom-asistencia): se envió
  un `endpoint.url_validation` firmado localmente y el `encryptedToken` devuelto coincidió byte
  a byte con el HMAC calculado independientemente — confirma que el webhook real de Zoom
  también validará sin problema.

### Fase 2 — YouTube OAuth (una vez) — HECHA 2026-07-15
- ✅ YouTube Data API v3 habilitada.
- ✅ **OAuth Client tipo "Desktop app"** creado (`26706368091-2nitjr8...`), guardado en
  `scripts/zoom-youtube/.env` (`YT_OAUTH_CLIENT_ID` / `YT_OAUTH_CLIENT_SECRET`, gitignoreado).
  **Gotcha:** el primer intento se hizo con un cliente tipo **"Web application"** y falló con
  `Error 400: redirect_uri_mismatch` — el flujo de consentimiento local (`google-auth-oauthlib`
  `InstalledAppFlow.run_local_server`) usa `http://localhost:<puerto aleatorio>` como
  redirect_uri, que **solo** Google acepta automáticamente para clientes tipo **Desktop app**
  (los Web application exigen redirect_uris exactas pre-registradas). Se creó un segundo
  cliente tipo Desktop app y funcionó a la primera.
- ✅ **Consentimiento real hecho** con `comunicaciones@tocaunavida.org` (script
  `scripts/zoom-youtube/obtener_refresh_token.py`, scopes `youtube.upload` + `youtube`).
  `refresh_token` guardado en `scripts/zoom-youtube/.env` (`YT_REFRESH_TOKEN`).
- ✅ **Verificado en vivo:** `channels().list(mine=True)` autenticó correctamente contra el
  canal **"Fundación ROFÉ - Toca una Vida"** (`UCnb0QeYM_z_91NcTkjjm3SQ`, 157 videos existentes)
  — confirma que el token real apunta al canal correcto de la Fundación, no a una cuenta
  personal. **Gotcha de scopes:** declarar solo `youtube.upload` en las `Credentials` locales
  hace que Google "down-scopee" el access_token al refrescar (manda un `scope` más chico) —
  rompe llamadas que necesiten el scope `youtube` completo (ej. agregar a playlist más
  adelante). `construir_youtube_client()` en el script ya declara ambos scopes.
- [ ] Confirmar que la app OAuth esté **"In production"** en la pantalla de consentimiento (no
  "Testing" → si no, el `refresh_token` puede invalidarse a los 7 días). Pendiente de revisar.
- Service Account NO sirve para YouTube — es OAuth de usuario obligatorio (ya resuelto arriba).

### Fase 3 — Implementación (patrón Execute Command, como q10-sync-supabase) — CÓDIGO LISTO, ACTIVO 2026-07-15
- ✅ **Script `scripts/zoom-youtube/subir_yt_grabacion.py` escrito.** Recibe el payload del
  webhook (por `--payload-b64`, base64 del body — evita problemas de escapado de comillas en
  el shell de Windows; también soporta `--payload-file` y `--meeting-uuid` para backfill),
  filtra por palabras clave del topic (`MR_KEYWORDS`, constante v1), elige el MP4
  (`shared_screen_with_speaker_view` o el de mayor `file_size`), descarga por streaming,
  sube a YouTube (`videos.insert`, `privacyStatus=unlisted`), registra en la pestaña
  **`YT-GRABACIONES-LOG`** del spreadsheet H3Test (idempotente por Meeting UUID), borra el
  temporal. Motivo Python y no nodos n8n: confirmado hoy con datos reales — ver prueba abajo.
- ✅ **Prueba real de la descarga (2026-07-15):** se descargó por streaming un MP4 real de
  **435 MB** (clase de 141 min) desde Zoom usando la lógica del script, y se limpió el
  temporal correctamente — valida el caso de "clases de 2h = cientos de MB" que era una
  preocupación del plan original.
- ✅ **Workflow n8n `zoom-yt-grabaciones` creado y ACTIVO** (id `bmKg2YhNRM3mlI19`, vía API).
  JSON en `n8n-workflows/zoom-yt-grabaciones.json`. Reusa la credencial crypto `Zoom Webhook
  HMAC Secret (real)` (mismo Secret Token del app, mismo patrón CRC+firma que zoom-asistencia).
  Flujo: Webhook → CRC/firma → Responder OK (ack inmediato) + Execute Command
  `subir_yt_grabacion.py --payload-b64 <body en base64>` → IF `[OK]` en stdout → Telegram
  éxito/error (mismo bot/chat_id que asistencia-zoom-diario).
- ✅ **Handshake CRC real de Zoom pasó** al validar la URL en el Marketplace (ver Fase 1);
  reconfirmado con CRC sintético (ver arriba). El workflow está listo para recibir el primer
  `recording.completed` real.
- **Filtro MR editable:** como JC y MR comparten el mismo host (`comunicaciones@tocaunavida.org`),
  el filtro es por **palabras clave del topic** (emprend, ventas, finanzas, negocio, habilidades
  del ser, estrategias digitales, mujeres rofé…), hardcodeadas en `MR_KEYWORDS` del script para
  v1 (candidato a mover a Sheet editable si el naming da problemas). Regla operativa ya vigente:
  el topic de la reunión = nombre del curso (mismo patrón que usa `ZOOM-STATS`).
- ✅ **Backfill / red de seguridad — HECHO 2026-07-16:** `backfill_grabaciones.py` lista las
  grabaciones de los últimos 2 días y pasa cada una por `procesar()` (idempotente en ambas
  ramas). Workflow n8n **`zoom-yt-backfill`** (id `HEz0dGunvdGckdEr`) ACTIVO, diario 20:00
  Bogotá, Telegram éxito/error. Cubre: PC apagado, túnel caído, transcripción tardía.
- [ ] **Falta agregar playlist MR** al `videos.insert` (opcional, no bloqueante) — no se
  implementó todavía en el script.

### Rama NOVA → Google Drive (2026-07-16)

**Requerimiento de Samuel:** las sesiones NOVA no van a YouTube — cada sesión se guarda con su
**transcripción** en una subcarpeta `NOVA-DD-MM-YYYY` dentro de la carpeta de Drive de testing
(`18eu7pveWJmvTb_rLPHGVmPZ41PE-zUGV`, "TEST-16-07-2026"), y hay que garantizar al 100% que
grabación + transcripción lleguen para **todas** las NOVA.

- **Enrutamiento por topic** en `subir_yt_grabacion.py`: `"nova"` en el topic (case-insensitive,
  `NOVA_KEYWORDS`) → Drive; si no, aplica el filtro MR → YouTube; si tampoco, se descarta.
- **Qué se sube:** el MP4 principal (mismo criterio que YouTube: `shared_screen_with_speaker_view`
  o el más grande) + todo archivo `TRANSCRIPT` (VTT). Verificado 2026-07-16 que el Audio
  Transcript está activado en la cuenta: todas las clases reales recientes traen `TRANSCRIPT`.
- **Transcripción tardía:** Zoom termina la transcripción DESPUÉS del video → suscribir también
  **`recording.transcript_completed`** en el Event Subscription del Marketplace (mismo endpoint).
  El script lo maneja: idempotencia NOVA por **nombre de archivo ya en Drive** (no por UUID),
  así el segundo evento agrega solo la transcripción. Para MR ese evento se descarta.
- **Gotcha crítico — service account NO puede subir a My Drive:** verificado en vivo
  (`403 storageQuotaExceeded: Service Accounts do not have storage quota`). Aunque la carpeta
  esté compartida como editor, la SA no tiene cuota en carpetas de My Drive. Solución: la subida
  a Drive usa el **mismo OAuth de comunicaciones@** que YouTube, agregando el scope
  `https://www.googleapis.com/auth/drive` → **requiere re-correr `obtener_refresh_token.py`**
  (los archivos quedan como propiedad de comunicaciones@, cuota de Workspace).
- **Garantía 100%:** webhook (camino rápido) + `zoom-yt-backfill` diario (red de seguridad,
  idempotente) + Telegram en éxito y error de ambos workflows. Log en pestaña
  `NOVA-GRABACIONES-LOG` del spreadsheet H3Test.

### Test E2E NOVA — PASÓ 2026-07-16 ✅
Desbloqueado el mismo día: Samuel re-corrió el consentimiento OAuth (scope drive), habilitó la
**Drive API** en el proyecto de Google Cloud (gotcha: el consentimiento otorga el scope pero la
API hay que habilitarla aparte — `403 accessNotConfigured` hasta hacerlo), y agregó el evento
`recording.transcript_completed` en el Marketplace (también activó `cloud_storage_usage_updated`,
inofensivo).

- **Prueba real:** grabación de Zoom de 121 MB + transcripción VTT, procesada con topic NOVA
  sintético → subcarpeta `NOVA-16-07-2026` creada, ambos archivos subidos, fila en
  `NOVA-GRABACIONES-LOG`. **Idempotencia verificada:** segundo run con el mismo `start_time`
  → "todos los archivos ya estaban", no resube.
- **Rama SKIP silenciosa en n8n (2026-07-16):** los `[SKIP]` (clases JC, eventos sin grabación
  como `cloud_storage_usage_updated`) van a un IF "Es SKIP?" → NoOp; Telegram solo suena con
  subidas reales o errores reales. JSON re-exportado.
- **Token nuevo verificado para ambos destinos:** Drive (carpeta visible/escribible) y YouTube
  (canal Fundación ROFÉ, 157 videos) — el re-consentimiento no rompió la rama YouTube.
- La app S2S **no tiene** `meeting:read:list_meetings` → no se puede verificar por API el topic
  ni el auto_recording de reuniones futuras; el chequeo pre-sesión NOVA es manual (topic con
  "nova" + grabar EN LA NUBE).

### Primera sesión NOVA real + 3 bugs cazados y corregidos (2026-07-16 tarde)

La primera reunión NOVA real (12:52, "Entrevista NOVA - prueba webhook", creada por API con
`auto_recording=cloud` + `join_before_host`) destapó tres fallas reales; las tres quedaron
corregidas y verificadas re-inyectando el evento REAL de Zoom (firmado con el
`ZOOM_WEBHOOK_SECRET_TOKEN` del `.env`) por la URL pública:

1. **Zoom entrega los `recording.*` a la suscripción de ASISTENCIA**, no a la de grabaciones
   (los eventos quedaron marcados en esa suscripción del Marketplace). Fix estructural: el
   workflow `Zoom - Asistencia` ahora tiene una 4ª salida en el switch (`recording.` startsWith)
   → nodo **"Reenviar a Grabaciones"** (HTTP POST a `localhost:5678/webhook/zoom-grabaciones`
   reenviando body + headers de firma; mismo secret ⇒ la firma revalida). Con esto da igual en
   cuál suscripción del Marketplace queden los eventos — con idempotencia no hay duplicados ni
   siquiera si quedan en ambas.
2. **El workflow de asistencia tenía nodos DUPLICADOS** (3 copias de "Ruteo Evento Zoom" +
   nodos LIVE-LOG, mismos nombres y hasta mismos ids — artefactos de ediciones por API).
   n8n ejecuta la ÚLTIMA copia (probado: la copia viva tenía `useAppend:true`), así que editar
   "la primera" no sirve. Se deduplicó (30→22 nodos) conservando la última de cada nombre.
3. **`--payload-b64` resolvía VACÍO en Execute Command** (la expresión con `Buffer.from(...)`
   nunca se había probado con un evento real; además el payload real de 5 archivos + JWT
   arriesgaba el límite de ~8k chars de cmd). Fix: el comando ahora pasa solo
   `--meeting-uuid "{{ ...object.uuid }}"` y el script consulta los archivos a la API de Zoom
   (mismo camino del backfill, ya probado). Nuevo IF "Evento con grabacion?" deja pasar solo
   `recording.completed`/`recording.transcript_completed` al script; el resto (p.ej.
   `recording.cloud_storage_usage_updated`) muere en NoOp sin alertar.

Además: el video + transcripción de la sesión real llegaron a Drive vía **backfill manual**
(primera corrida real del backfill: 2 archivos subidos, clase JC ignorada, sin fallos), y el
replay final del evento real terminó en **Telegram Exito** con "todos los archivos ya estaban".

### Cambio de alcance: se sube TODO a YouTube (2026-07-16, decisión de Samuel)

**Ya no hay filtro MR** — se graba todo y toda grabación no-NOVA va a YouTube `unlisted`.
`MR_KEYWORDS` pasó de filtro a **etiqueta**: columna nueva **"Programa"** en
`YT-GRABACIONES-LOG` ("Mujeres ROFE" / "Jovenes creaTIvos", también en la descripción del
video). El encabezado del tab se actualiza solo (`asegurar_tab_log` re-escribe la fila 1 si
cambió). Rama YouTube probada E2E el mismo día: video real de 2 MB subido `unlisted` al canal
con topic de prueba y borrado tras verificación.

**"Carpetas" = playlists por curso (2026-07-16):** cada video subido se agrega
automáticamente a una playlist `unlisted` con el nombre del curso (`normalizar_curso(topic)`:
quita el sufijo " - Sala N" para que las breakout rooms caigan en la playlist del curso
madre). La playlist se crea sola si no existe; columna "Playlist" en el log. Si la playlist
falla, el video ya subido NO se marca como error (solo `[WARN]`). **Gotcha:**
`playlistItems.insert` falla a veces con **409 SERVICE_UNAVAILABLE transitorio** (típico
recién creada la playlist) → `agregar_a_playlist()` reintenta 4 veces con espera creciente
(verificado en vivo: el primer intento falló con 409 y el reintento pasó).

**"TODO" aplica a partir de 2026-07-16 (~15:15):** las grabaciones previas al cambio (las 2
clases JC del 14/07 y 16/07 am) quedaron pre-marcadas en `YT-GRABACIONES-LOG` como
`OMITIDO (anterior al cambio de alcance 2026-07-16)` para que el backfill no las suba
retroactivamente (la idempotencia por UUID las salta). Para re-incluir alguna: borrar su fila
del log y correr `backfill_grabaciones.py --dias N`.

**Consecuencias a vigilar:**
- **Cuota YouTube (6 subidas/día)**: ahora cuentan TODAS las clases + salas breakout (cada
  sala genera su propia grabación). Si un día hay >6, las que sobren fallarán → llegarán por
  el backfill del día siguiente solo si la cuota lo permite; considerar pedir ampliación.
  (Cada subida ~1.600 unidades + ~100 de playlist sobre cuota diaria de 10.000.)

### Pendiente
- Próxima sesión NOVA real 100% desatendida (toda la cadena ya validada pieza por pieza).
- Primera clase real → YouTube vía webhook (rama ya probada con subida real manual).
- Opcional: en el Marketplace, mover los eventos `recording.*` a la suscripción de
  `/webhook/zoom-grabaciones` (ya no es necesario — el reenvío cubre ambos casos).
- Playlist por programa (opcional) · confirmar app OAuth "In production" · evaluar ampliación
  de cuota YouTube si el volumen diario de grabaciones supera ~6.

### Fase 4 — Pruebas
1. Reunión corta real con topic de curso MR, grabada a la nube → verificar webhook → descarga →
   video `unlisted` en el canal → borrar video de prueba.
2. Probar camino de error (simular fallo de subida) → Telegram.
3. Probar el backfill con una grabación no procesada por webhook.

### Riesgos ya identificados (hereda los Gotchas de arriba)
- Cuota YouTube 6 subidas/día (ampliable por formulario, tarda días).
- `recording.completed` puede llegar horas después de la clase.
- Retención de grabaciones en la nube de Zoom — el backfill diario mitiga.
- PC de Samuel apagado = webhook perdido — backfill mitiga.
- PII/menores: subir `unlisted` primero; pase a público con revisión humana.
