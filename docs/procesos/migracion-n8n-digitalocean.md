# Migración n8n → DigitalOcean

**Estado:** Planificación (auditoría inicial completa, sin fecha de ejecución)
**Última actualización:** 2026-07-22
**Procesos relacionados:** [[mr-website]] (ya tiene droplet DigitalOcean + `rofe-composal`, candidato a reutilizar) · [[panel-datos-etl]] (su propia migración pendiente Netlify→DO es una decisión separada) · [[q10-consolidacion]] · todos los procesos con workflow n8n (ver tabla de abajo)

> **Nota de uso de esta nota:** a diferencia de otras notas de proceso, esta se actualiza en
> cada sesión que toque el tema — aunque no se ejecute nada — porque el usuario anticipa
> cambios en el sistema (nuevos workflows, nuevos scripts) antes de decidirse a migrar. Cada
> sesión nueva debe: (1) re-auditar en vivo contra `GET /api/v1/workflows` si pasó tiempo desde
> la última auditoría, (2) agregar a "Decisiones abiertas" o "Gotchas" lo que se descubra, (3)
> NO reescribir el historial de auditorías — apendizar con fecha.

## Qué hace / por qué

Sacar n8n (y el pipeline Python que orquesta) de la dependencia del PC de Samuel encendido +
Task Scheduler + túnel ngrok, y ponerlo en un droplet DigitalOcean con IP/dominio propio,
corriendo 24/7 sin intervención manual.

**Esto NO es solo "instalar n8n en un droplet".** La auditoría en vivo (abajo) confirma que la
automatización real vive en 35 nodos `executeCommand` que llaman scripts Python por **ruta
absoluta de Windows** (`cd /d C:\Users\EstudiantesJC\...`). Migrar de verdad implica portar ese
pipeline Python completo a Linux, no solo mover el contenedor de n8n.

## Auditoría en vivo — 2026-07-22

Hecha contra la instancia real (`GET /api/v1/workflows` + detalle de cada uno), no contra los
JSON exportados en `n8n-workflows/` (que pueden desalinearse — ver gotcha ya documentado en
[[convenciones]]).

### Workflows activos (12)

| ID | Nombre | Trigger |
|---|---|---|
| `Rblg81qifVshsRae` | Bot Q10 - Actualizar Grupos | Schedule 4h + Telegram |
| `LgkDbNPERYgKMrYj` | mr-actualizacion-datos | Schedule diario 9:30 |
| `jkNaE51PKQ4TQzNq` | Zoom - Asistencia | Webhook (Zoom) |
| `uSizw3dNzpb6n53H` | q10-sync-supabase | Schedule diario 9:45 |
| `qKBCgp1zFa3qeZAB` | asistencia-zoom-diario | Schedule diario 00:00 |
| `g0zmkQB70FHXPPLN` | alerta-desercion-semanal | Schedule semanal lun 7:00 |
| `hO64Z1SOg2A6z88K` | sociodemograficos-semanal | Schedule semanal lun 6:00 |
| `N7ouRIdgbomCGNxa` | correos-rebotes-diario | Schedule diario |
| `DFPiF1RtD58FhGoZ` | emoflow-ingresos-diario | Schedule diario 21:30 |
| `bmKg2YhNRM3mlI19` | zoom-yt-grabaciones | Webhook (Zoom) |
| `HEz0dGunvdGckdEr` | zoom-yt-backfill | Schedule (backfill diario) |
| `JimOlAsAF0jAXcWj` | zoom-crear-reunion | Webhook (on-demand) |

### Credenciales guardadas EN n8n (nodo → tipo)

Solo 4 tipos, ninguno es OAuth de usuario con redirect URI:

| Tipo n8n | Nombre credencial | Fricción de migración |
|---|---|---|
| `googleApi` | Q10 Automatizacion Service Account | Ninguna — copiar el JSON de service account |
| `telegramApi` | Telegram Q10 Bot | Ninguna — solo token, sin redirect URI |
| `httpBasicAuth` | Zoom S2S Basic Auth v2 | Ninguna — client credentials, sin redirect URI |
| `crypto` | Zoom Webhook HMAC Secret (real) | Ninguna — solo secreto simétrico |

**Ningún nodo n8n usa Google Drive/YouTube OAuth de usuario.** Ese OAuth vive DENTRO del script
`scripts/zoom-youtube/subir_yt_grabacion.py`, como `refresh_token` + `client_secret` guardados en
un `.env` (no un `token.json` atado a `localhost`). Los refresh tokens de Google para apps tipo
"installed app" **no están atados a IP/dominio** — copiar el `.env` basta, no hace falta
re-consentimiento. (Único riesgo preexistente, no de la migración: si la app OAuth en Google
Cloud Console sigue en estado "Testing", el refresh token expira solo a los 7 días — verificar
que esté en "In production" antes de migrar, o la caída sería inmediata e independiente del
droplet.)

**Conclusión clave:** el cuello de botella de la migración NO son las credenciales de n8n. Es:
1. El pipeline Python (rutas Windows, dependencias, `.env` dispersos).
2. `git push` real (ver abajo).
3. Los webhooks públicos (Zoom, Telegram) apuntando hoy al túnel ngrok.
4. Los datos PII locales en `tools/` (gitignoreado, nunca viajó por git).

### Nodos por tipo (12 workflows)

`executeCommand` (35) es, por lejos, el tipo dominante — confirma que n8n es solo el
orquestador/scheduler; toda la lógica vive en scripts Python invocados por shell. También hay
`googleSheets` (4, nativos de n8n, no por script) y `httpRequest` (6). **No hay Selenium,
Playwright ni chromedriver en ningún script** (confirmado por grep) — el login de Q10 es puro
`requests.Session()` (ver [[convenciones]]), así que no hace falta Chrome headless en el
droplet. Esto simplifica mucho la imagen Docker.

### Mecanismo real de publicación del dashboard (`git push`)

7 scripts (`export_stats.py`, `export_avance.py`, `export_retirados.py`, `export_aprobacion.py`,
`export_asistencia.py`, `export_supabase_json.py`, `bootstrap_history.py`) hacen
`subprocess.run(["git", "push", "origin", "main"])` directo contra
`https://github.com/Fundacion-ROFE/Estadisticas.git`, usando `credential.helper=manager`
(Windows Credential Manager) + `http.sslBackend=schannel`. **Ninguno de los dos existe en
Linux.** En el droplet hay que resolver auth git no-interactiva:
- Opción recomendada: **deploy key SSH** con el remoto en formato `git@github.com:...` (scope
  de escritura solo a ese repo, revocable sin tocar otras credenciales).
- Alternativa: PAT fino con `credential.helper=store` — requiere rotación manual al expirar.

### Config actual que hay que replicar (de `iniciar_n8n.bat`)

```
NODES_EXCLUDE=[]                        ← reactiva executeCommand (n8n 2.x lo desactiva por defecto)
NODE_TLS_REJECT_UNAUTHORIZED=0          ← SOLO por el proxy corporativo MITM local — en DO no aplica, revisar si se puede quitar
N8N_DIAGNOSTICS_ENABLED=false
GENERIC_TIMEZONE=America/Bogota / TZ=America/Bogota
```
El `NODE_TLS_REJECT_UNAUTHORIZED=0` es candidato a **eliminarse** en DO (sin proxy corporativo,
desactivar la verificación SSL sería un downgrade de seguridad injustificado). Igual para
`truststore.inject_into_ssl()` en los scripts Python — seguirá funcionando sin el MITM presente,
solo deja de ser necesario (no hace daño dejarlo).

### Dependencias Python dispersas

Solo 3 `requirements.txt` en todo el repo (`q10-consolidacion/`, `organizador/`,
`mujeres-rofe-correos/certificados/`) — **no hay uno consolidado** para `scripts/panel-datos/`,
`scripts/zoom-youtube/`, `scripts/zoom-asistencia/`, `scripts/mujeres-rofe-correos/`. Antes de
migrar hay que congelar un `requirements.txt` real corriendo cada script en un venv limpio (no
asumir que lo que hay hoy en el PC es exactamente lo mínimo necesario).

## Decisiones abiertas (para resolver antes de escribir el plan de ejecución)

- [ ] **¿Reutilizar el droplet de [[mr-website]]?** Ya existe un droplet DigitalOcean corriendo
  Docker Compose (`~/rofe-composal`, deploy vía GitHub Actions + `appleboy/ssh-action`) para
  `mujeresrofe.com`. Añadir un servicio `n8n` a ese mismo compose evita crear cuenta/droplet
  nuevo y reutiliza el patrón de deploy ya probado — pero mezcla el blast radius de dos
  proyectos distintos en una sola máquina. Alternativa: droplet nuevo dedicado, más aislado,
  más barato empezar ($6-12/mes) pero infraestructura duplicada.
- [ ] Dominio para n8n (subdominio propio, ej. `n8n.tocaunavida.org` o similar) + reverse proxy
  (Caddy, para SSL automático vía Let's Encrypt sin fricción).
- [ ] Autenticación del editor n8n expuesto a internet (hoy solo accesible por túnel + red local;
  en DO queda expuesto salvo que se ponga detrás de VPN/basic auth/n8n user management).
- [ ] Método de auth git no-interactiva (deploy key SSH vs PAT — ver arriba).
- [ ] Cómo llegan los archivos de `tools/` (PII, gitignoreado, nunca estuvo en git) al droplet —
  necesita transferencia manual fuera de git (scp/rsync puntual), no un flujo automatizado.
- [ ] Re-registro de webhooks públicos: Zoom (Event Subscriptions apunta hoy a la URL ngrok) y
  Telegram (`setWebhook` apunta a la misma URL) — deben repararse a la URL/dominio nuevo el
  mismo día del corte, no antes (el viejo debe seguir sirviendo hasta el corte).
- [ ] Estrategia de corte: ¿correr n8n en DO en paralelo unos días (mismos workflows,
  inactivos) antes de apagar el local? ¿o corte directo con rollback = reactivar
  `iniciar_n8n.bat` local?
- [ ] Backup/versionado de los datos internos de n8n (SQLite/`~/.n8n` o Postgres si se
  configura) — hoy no hay backup del estado interno de n8n, solo de los workflows vía JSON
  exportado.

## Fases propuestas (borrador, sin fecha)

1. **Congelar dependencias:** generar `requirements.txt` real por carpeta de scripts, probarlos
   en un venv Linux limpio (puede hacerse ya, sin droplet, con WSL o un contenedor local).
2. **Decidir droplet** (nuevo vs compartir con mr-website) + dominio + reverse proxy.
3. **Preparar auth no-interactiva:** deploy key SSH para git, copiar credenciales googleApi/
   telegramApi/httpBasicAuth/crypto (son portables, solo copiar valores a `.env`/n8n credentials
   store nuevo).
4. **Migrar `tools/` (PII)** por canal fuera de git.
5. **Levantar n8n en Docker Compose** en el droplet, importar los 12 workflows vía API
   (`POST /workflows`), dejarlos **inactivos**.
6. **Correr en paralelo** unos días: activar en DO con schedules desfasados o en modo prueba,
   comparar salidas contra el local antes de apagar nada.
7. **Corte:** re-registrar webhooks Zoom/Telegram al dominio nuevo, activar workflows en DO,
   desactivar Task Scheduler local + `iniciar_n8n.bat`.
8. **Retirar ngrok** una vez confirmado que nada depende de la URL vieja.

## Gotchas encontrados en la auditoría de hoy

- Los 35 `executeCommand` usan `cd /d C:\...` o `cd "C:\..."` con backslashes — sintaxis
  puramente `cmd.exe`. En Linux serán `cd /ruta && python3 ...`, requiere reescribir **cada
  nodo**, no solo variables de entorno.
- El `git push` real no está en n8n, está escondido dentro de 7 scripts Python distintos — fácil
  de pasar por alto si alguien audita solo los nodos de n8n y no el código Python que llaman.
- `NODE_TLS_REJECT_UNAUTHORIZED=0` y `truststore.inject_into_ssl()` existen únicamente por el
  proxy corporativo MITM de la red actual — no son necesarios en DO y dejarlos sería una
  regresión de seguridad sin justificación una vez fuera de esa red.
- No hay Selenium/Playwright/chromedriver en ningún script (confirmado por grep) — el login Q10
  es 100% `requests`, así que el droplet no necesita Chrome headless ni sus dependencias de
  sistema pesadas.

## Pendiente / Próximos pasos

- [ ] Responder las "Decisiones abiertas" de arriba (empezar por: ¿droplet compartido con
  mr-website o nuevo?).
- [ ] Congelar `requirements.txt` faltantes.
- [ ] Volver a correr la auditoría en vivo si pasan >2-3 semanas o se agregan workflows nuevos
  antes de escribir el plan de ejecución definitivo.
