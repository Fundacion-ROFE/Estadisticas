# Crear reuniones Zoom (automático)

**Estado:** Funcional — probado end-to-end (crea reunión real + devuelve link; camino de error OK)
**Workflow n8n:** `zoom-crear-reunion` (id `JimOlAsAF0jAXcWj`, activo)
**Última actualización:** 2026-07-15
**Procesos relacionados:** [[zoom-asistencia]]

## Qué hace
Automatiza la creación de reuniones Zoom (hoy 2 personas las crean a mano). Recibe título,
fecha, hora y duración, crea la reunión en la cuenta **comunicaciones** vía la API de Zoom y
devuelve el link de unión. Reusa la misma app Server-to-Server OAuth de [[zoom-asistencia]].

## Disparador (Trigger)
**Webhook** n8n (`POST /webhook/zoom-crear-reunion`). Body JSON:
```json
{ "titulo": "Clase HTML - Grupo 3", "fecha": "2026-07-20", "hora": "10:00",
  "duracion": 60, "host": "comunicaciones@tocaunavida.org" }
```
`host` es opcional (default `comunicaciones@tocaunavida.org`).

## Flujo resumido
1. Webhook recibe título/fecha/hora/duración.
2. `Preparar datos` (Set) arma `start_time = fecha + "T" + hora + ":00"` (tz America/Bogota).
3. `Obtener Token Zoom` (HTTP, Basic Auth `Zoom S2S Basic Auth v2`, `grant_type=account_credentials`).
4. `Crear Reunion`: `POST https://api.zoom.us/v2/users/{host}/meetings` (Bearer token), body
   `{topic, type:2 (programada), start_time, duration, timezone, settings}`.
5. `Responder OK` devuelve `{ ok, meeting_id, topic, join_url, start_time }`.
6. **Camino de error explícito:** `onError: continueErrorOutput` en los nodos HTTP → `Responder
   Error` (HTTP 500 con el mensaje de Zoom). Verificado con host inválido (Zoom 1001 "User does
   not exist" → 500, sin crear reunión).

## Fuentes de datos / APIs usadas
- Zoom API S2S OAuth — `POST /oauth/token` + `POST /users/{userId}/meetings`.
- Scope requerido: **`meeting:write:meeting:admin`** (agregado por Samuel 2026-07-15; antes el app
  solo tenía scopes de lectura). El host se pasa por email → no hizo falta scope `user:read`.

## Destino de los datos
La reunión queda creada en la cuenta Zoom **comunicaciones** (`account_id u08qlWbRTR2VBSs0bRwZPQ`,
`us06web.zoom.us`). El link se devuelve en la respuesta del webhook.

## Decisiones de diseño clave
- **Reusa la app S2S de asistencia** (misma credencial `Zoom S2S Basic Auth v2`, mismo patrón de
  token que `Obtener Token Zoom` del workflow de asistencia) — no se creó app nueva.
- **Host por email, no "me":** los tokens S2S son a nivel de cuenta, no tienen usuario "me"; se
  usa `/users/{email}/meetings` con el correo del host (funciona sin scope `user:read`).
- **Trigger webhook** (no manual): permite invocarlo desde cualquier cliente (curl, otro workflow,
  bot). Ver Pendiente para una UX más amable (Form Trigger).

## Gotchas / Limitaciones conocidas
- **Solo cuenta comunicaciones:** el app S2S vive solo ahí. Las reuniones de la cuenta *soporte*
  (us02web) no se pueden crear con este workflow (mismo hueco multi-cuenta de [[zoom-asistencia]]).
- **Borrado disponible (2026-07-15):** el app ya tiene `meeting:delete:meeting:admin` (se usó para
  limpiar las reuniones de prueba). Este workflow solo CREA; un flujo de "cancelar reunión"
  (`DELETE /meetings/{id}`) es factible sin más cambios de scope si se quiere agregar.
- **El webhook es local:** responde en `localhost:5678` (y por el túnel ngrok fijo si se expone).
  Para uso desde fuera del PC habría que enrutarlo por ngrok igual que el de asistencia.

## Pendiente / Próximos pasos
- [ ] **UX para operadores:** cambiar el trigger a un **Form Trigger** de n8n (formulario web con
      título/fecha/hora/duración) o un comando de Telegram del bot q10, para que las 2 personas que
      crean reuniones no tengan que hacer un POST a mano.
- [ ] (Opcional) Flujo de **cancelar reunión** (`DELETE /meetings/{id}`) — el scope
      `meeting:delete:meeting:admin` ya está habilitado (2026-07-15).
- [ ] (Opcional) Cobertura de la cuenta *soporte* (requiere su propia app S2S — ver [[zoom-asistencia]]
      "Cobertura multi-cuenta").
- [x] ~~Borrar las 2 reuniones de prueba~~ — hechas (204) el 2026-07-15.
