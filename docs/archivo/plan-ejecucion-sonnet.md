# Plan de Ejecución — versión para Sonnet

**Fuente:** [[plan-agentes-automatizacion]] (contexto completo y justificación)
**Última actualización:** 2026-07-14
**Instrucciones para el modelo que ejecute esto:** trabaja UNA tarea a la vez, en el orden
listado. Cada tarea es autocontenida: dice qué leer, qué hacer, y cómo verificar. No leas
más archivos de los indicados. No avances a la siguiente tarea sin cumplir el criterio de
aceptación. Si algo no coincide con lo descrito, DETENTE y pregunta a Samuel.

## Reglas globales (aplican a TODAS las tareas)

1. **Nunca imprimas, loguees ni guardes `SMTP_PASSWORD` ni ninguna clave.** Las claves se
   piden con `getpass` en el momento (ver patrón en `scripts/mujeres-rofe-correos/run_piloto.py`).
2. **PII nunca sale de `tools/`** (carpeta gitignoreada). A GitHub solo van agregados.
3. **Nunca ejecutes `--enviar` (envío masivo) sin que Samuel lo confirme explícitamente
   en la conversación.** `--preview` y `--piloto` sí puedes correrlos.
4. Todo script Python nuevo empieza con `truststore.inject_into_ssl()` (SSL corporativo).
5. Al terminar cada tarea: agrega una entrada corta al final de `claude_sessions.md` y
   marca la tarea como hecha en la sección "Checklist" de este archivo.
6. Credenciales Supabase: están en `.env.local` (leer con `python-dotenv`, patrón ya usado
   en `scripts/panel-datos/cargar_supabase.py`). OJO: la `SERVICE_ROLE_KEY` actual da 401 —
   usa la anon key salvo que la tarea diga lo contrario.

---

## TAREA 1 — Enviar campaña MR pendiente (solo operación, sin código)

**Qué es:** hay una campaña de correos lista para 2.693 destinatarias que nunca se ejecutó.

**Leer primero:** `scripts/mujeres-rofe-correos/README.md` (completo).

**Pasos:**
1. Verifica que existe la lista en `tools/` (el README dice el nombre exacto del CSV,
   `lista_mr_ultimos_3_anios` o similar). Si no existe, regenerarla con
   `extraer_lista_mr_ultimos3anios.py`.
2. Corre el modo `--preview` y muestra a Samuel el HTML resultante (`preview.html`).
3. Con OK de Samuel, corre `run_piloto.py` (envía solo a Samuel).
4. Con segundo OK explícito de Samuel, corre `enviar_campana.py --enviar`. El script pide
   escribir "ENVIAR N" — eso lo confirma Samuel, no tú.
5. Reporta: cuántos enviados, cuántos fallidos, dónde quedó el CSV de registro.

**Criterio de aceptación:** campaña enviada y registro CSV en `tools/` actualizado, o
bloqueo reportado a Samuel con el error exacto.

**NO hacer:** modificar `enviar_campana.py`; enviar sin doble confirmación.

---

## TAREA 2 — Cron n8n para asistencia Zoom (00:00 diario)

**Qué es:** el script de sync de asistencia ya funciona; solo falta que n8n lo corra solo
cada noche.

**Leer primero:**
- `docs/procesos/asistencia-zoom-flujo.md`
- `docs/reference-n8n-api-key.md` (cómo hablar con la API de n8n en `localhost:5678`)
- `n8n-workflows/asistencia-zoom-diario.json` (puede que el workflow ya exista — revisar
  primero si ya está creado en n8n antes de crear otro)

**Pasos:**
1. Identifica cuál script de sync es el vigente. Candidatos en `scripts/panel-datos/`:
   `sync_asistencia_upsert.py`, `sync_asistencia_directo.py`, `sync_asistencia_simple.py`,
   `sync_asistencia_supabase.py`. El doc de proceso dice cuál es el bueno; si no lo dice,
   pregunta a Samuel — NO adivines.
2. En n8n (API local): crea o activa un workflow `asistencia-zoom-diario` con Schedule
   Trigger a las 00:00 que ejecute el script vía Execute Command.
3. Agrega camino de error explícito (convención del repo: nunca fallar en silencio) —
   nodo de error que notifique por Telegram igual que `q10-consolidacion`.
4. Exporta el JSON final a `n8n-workflows/asistencia-zoom-diario.json`.
5. Actualiza `docs/procesos/asistencia-zoom-flujo.md` con el estado nuevo.

**Criterio de aceptación:** workflow activo en n8n, ejecución manual de prueba exitosa,
JSON exportado, doc actualizado.

---

## TAREA 3 — Skill `/enviar-correo` (agente de correos, Fase B)

**Qué es:** una skill de Claude que convierte una petición en lenguaje natural ("mándale
recordatorio a las de Bogotá que no completaron el curso") en una campaña ejecutada con
los scripts existentes. NO reimplementa el envío — solo orquesta.

**Leer primero:**
- `scripts/mujeres-rofe-correos/README.md` y `enviar_campana.py` (para conocer el formato
  exacto del JSON de campaña y sus flags)
- Un ejemplo de skill existente en `.claude/skills/` (copiar su estructura de carpeta y
  frontmatter)

**Pasos:**
1. Crea `.claude/skills/enviar-correo/SKILL.md` con este flujo obligatorio (escríbelo en
   el skill como pasos numerados):
   a. Interpretar la petición → definir filtros de lista (programa, ciudad, estado curso).
   b. Generar/filtrar la lista consultando Supabase (vistas existentes) o reutilizando
      `extraer_lista_mr_ultimos3anios.py`. Lista siempre a `tools/`, nunca a `docs/`.
   c. Armar el JSON de campaña (mismo esquema que usa `enviar_campana.py` — copiar un
      JSON de campaña existente como plantilla, no inventar campos).
   d. Correr `--preview` y mostrar el HTML a Samuel.
   e. Con OK, correr piloto (solo a Samuel).
   f. Solo con segundo OK explícito, `--enviar`.
2. El skill debe incluir las Reglas globales 1 y 3 de este documento, textuales.
3. Prueba el skill end-to-end en modo preview+piloto con una campaña ficticia pequeña.

**Criterio de aceptación:** `/enviar-correo` llega hasta piloto sin editar JSON a mano.
El envío masivo real NO es parte del criterio — eso lo dispara Samuel cuando quiera.

**NO hacer:** duplicar lógica de envío dentro del skill; tocar `enviar_campana.py`.

---

## TAREA 4 — Alerta de deserción automática

**Qué es:** `tools/panel_riesgo.py` ya cruza Avance × asistencia y detecta riesgo, pero
solo corre a mano. Convertirlo en alerta periódica.

**Depende de:** Tarea 2 (asistencia fresca diaria) y Tarea 3 (motor de notificación).

**Leer primero:** `tools/panel_riesgo.py` y `docs/procesos/mapa-codigo.md` (entrada de
panel_riesgo).

**Pasos:**
1. Crea `scripts/panel-datos/alerta_desercion.py`: misma lógica de cruce que
   `panel_riesgo.py` pero leyendo de Supabase (no de archivos locales). Salida: lista de
   participantes en riesgo con motivo.
2. La notificación reutiliza el motor de correos (Tarea 3) o Telegram (más simple —
   preferir Telegram si el bot de q10-consolidacion ya existe; el resultado son pocos
   nombres, no un correo masivo).
3. Cron n8n semanal (no diario) que ejecute el script y notifique.
4. Documenta en `docs/procesos/` (crear nota nueva `alerta-desercion.md` con la plantilla
   `docs/plantillas/plantilla-proceso.md`).

**Criterio de aceptación:** una corrida manual produce la lista de riesgo correcta
(validar contra una corrida de `panel_riesgo.py` local: mismos nombres) y la notificación
llega a Telegram/correo de Samuel.

---

## TAREA 5 — Tabla `email_optout` + log agregado de campañas en Supabase

**Qué es:** deuda técnica antes de escalar envíos. Dos tablas chicas.

**Leer primero:** `scripts/panel-datos/cargar_supabase.py` (patrón de conexión) y el
esquema actual de Supabase (`list_tables` vía MCP o `test_conexion_supabase.py`).

**Pasos:**
1. Migración Supabase con dos tablas:
   - `email_optout(email text primary key, fecha timestamptz default now(), motivo text)`
   - `campanas_enviadas(id serial pk, campana text, fecha timestamptz, enviados int,
     fallidos int, programa text)` — SOLO agregados, sin direcciones de correo.
2. Modifica `extraer_lista_mr_ultimos3anios.py`: al final, excluir emails presentes en
   `email_optout` (una consulta + un filtro; cambio mínimo).
3. Modifica `enviar_campana.py`: al terminar un envío, insertar UNA fila resumen en
   `campanas_enviadas`. No subir emails individuales.
4. Actualiza `scripts/mujeres-rofe-correos/README.md` con las dos tablas nuevas.

**Criterio de aceptación:** insertar un email de prueba en `email_optout` y verificar que
la extracción de lista lo excluye; una corrida `--piloto` inserta su fila resumen.

---

## TAREA 6 — Creación automática de reuniones Zoom (sin IA)

**Qué es:** hoy 2 personas crean reuniones a mano. La app Server-to-Server de Zoom ya
existe (la usa asistencia-zoom).

**Leer primero:** `docs/procesos/zoom-asistencia.md` (dónde están las credenciales de la
app Zoom y cómo se autentica).

**Pasos:**
1. Workflow n8n `zoom-crear-reunion`: trigger manual o webhook, input = título, fecha,
   hora, duración; llama a la API de Zoom `POST /users/me/meetings` con OAuth
   server-to-server ya configurado.
2. Devuelve el link de la reunión (respuesta del webhook o mensaje Telegram).
3. Camino de error explícito. Exportar JSON a `n8n-workflows/`.
4. Documentar en `docs/procesos/` (nota nueva o sección en zoom-asistencia).

**Criterio de aceptación:** una invocación de prueba crea una reunión real visible en la
cuenta Zoom y devuelve el link.

---

## TAREA 7 — Captura de rebotes (bounces) → suppression list

**Qué es:** hoy `enviar_campana.py` solo registra la ACEPTACIÓN SMTP, no la entrega. Los
rebotes **asíncronos** (buzón inválido/lleno) vuelven como DSN (Delivery Status Notification)
al buzón remitente `mujeres.rofe@tocaunavida.org` y **nadie los lee** → no alimentan
`email_optout`. Este hueco lo detectó Samuel (2026-07-15). Cerrar el ciclo: leer rebotes →
suppression list → excluirlos de la próxima lista.

**Depende de:** Tarea 5 (`email_optout` ya existe).

**Leer primero:**
- `scripts/mujeres-rofe-correos/enviar_campana.py` (cómo se registra el envío hoy)
- `scripts/mujeres-rofe-correos/README.md` (sección "Opt-out y log de campañas")
- Esquema Supabase (`email_optout` / `campanas_enviadas`)

**Pasos:**
1. Script nuevo `capturar_rebotes.py`: lee el buzón remitente (Gmail API o IMAP con app-password
   de la misma cuenta, credencial en `.env.local`) filtrando los DSN de `mailer-daemon` /
   `Content-Type: multipart/report`.
2. Parsear las direcciones que rebotaron; clasificar **hard** (5.1.1 "no existe") vs **soft**
   (buzón lleno / temporal). Solo los hard van a la suppression list.
3. **Decisión pendiente con Samuel:** ¿reusar `email_optout` con `motivo='hard_bounce'` o crear
   una tabla `email_bounces` dedicada (para distinguir baja voluntaria de rebote técnico)?
4. Cron n8n (semanal, después de campañas) o correr a mano tras cada envío grande.
5. Actualizar el README.

**Criterio de aceptación:** una corrida sobre el buzón detecta los DSN recientes, extrae las
direcciones y las inserta en la suppression list; la siguiente extracción de lista las excluye.

**NO hacer:** borrar correos del buzón; subir direcciones (PII) a git — van solo a Supabase.

---

## Checklist de avance

- [x] Tarea 1 — Campaña MR pendiente
- [x] Tarea 2 — Cron asistencia Zoom
- [x] Tarea 3 — Skill /enviar-correo
- [x] Tarea 4 — Alerta de deserción
- [x] Tarea 5 — email_optout + log campañas
- [x] Tarea 6 — Crear reuniones Zoom
- [x] Tarea 7 — Captura de rebotes → suppression list

## Fuera de alcance (NO empezar sin instrucción explícita de Samuel)

Reportes a financiadores, lectura de CVs, asistente WhatsApp, análisis predictivo,
generalización de correos a JC. Justificación en [[plan-agentes-automatizacion]].

**Pendiente registrado (2026-07-15) — adaptar `/enviar-correo` a JC y otros correos:** hoy el skill
y `enviar_campana.py` son solo Mujeres ROFÉ. Para generalizar a JC (u otro programa) faltan 3
piezas: (a) un extractor de lista JC por cohorte (espejo de `extraer_lista_mr_ultimos3anios.py`,
consultando Supabase `courses?programa=eq.jc` filtrado por `cohorte` → `enrollments` →
`participants.email`, salida a `tools/lista_jc_<cohorte>.csv`); (b) hacer configurables por campaña
el remitente (`FROM_NAME` está hardcodeado "Equipo Mujeres ROFÉ" en `enviar_campana.py:42`) y la
cuenta SMTP (`SMTP_USER_2`/`SMTP_PASSWORD_2` ya existen en `.env.local`); (c) plantilla/banner/firma
de marca JC. Enfoque recomendado: generalizar `enviar_campana.py` para que el JSON de campaña
declare `programa`, `FROM_NAME`, cuenta y plantilla — un solo motor MR+JC, sin clonar en
`scripts/jc-correos/`. NO empezar sin OK explícito de Samuel (necesita: qué cuenta JC remitente y
qué plantilla/marca).
