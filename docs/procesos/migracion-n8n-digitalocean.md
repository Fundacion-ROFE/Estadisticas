# Migración n8n → DigitalOcean

**Estado:** Planificación. **Destino en revisión 2026-08-10:** por restricción de presupuesto se
decide intentar **Oracle Cloud Free Tier** (con mitigaciones) en lugar de DigitalOcean. Ver adenda
2026-08-10 al final — el "descartado" de Oracle del 2026-08-04 queda revertido por el cambio de
prioridad (costo ahora sí es restricción). Sin fecha de ejecución.
**Última actualización:** 2026-08-10
**Procesos relacionados:** [[mr-website]] (ya tiene droplet DigitalOcean + `rofe-composal`, candidato a reutilizar) · [[panel-datos-etl]] (su propia migración pendiente Netlify→DO es una decisión separada) · [[q10-consolidacion]] · todos los procesos con workflow n8n (ver tabla de abajo)

**Disparador 2026-08-04:** el portátil de Samuel se va a transportar físicamente varias veces
(riesgo de continuidad de los schedules) y se autorizó investigar proveedores alternativos a
DigitalOcean antes de comprometerse. Ver "Evaluación de proveedores" más abajo — conclusión:
**DigitalOcean se confirma como destino**, no cambia el plan de fases, solo se descartan
alternativas.

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

## Auditoría en vivo — 2026-08-04

Re-auditado contra `GET /api/v1/workflows` (18 resultados) + detalle de cada uno, según la
convención de esta nota. Han pasado ~13 días desde la auditoría anterior y el sistema creció.

### Workflows: 12 → 18 activos

Los 6 nuevos que no existían el 2026-07-22:

| Workflow | Script que invoca | Notas |
|---|---|---|
| `alerta-choques-cursos` | `scripts/panel-datos/check_choques_cursos.py` | Ya vive en `scripts/panel-datos/`, carpeta ya contemplada en el plan |
| `alerta-frescura-vencida` | `scripts/panel-datos/check_frescura.py` | Ídem |
| `alerta-choques-cohorte` | `scripts/panel-datos/check_choques_cohorte.py` | Ídem |
| `panel-verificacion-diaria` | `scripts/panel-datos/test_integridad_supabase.py --rapido` | Ídem |
| `datos-respaldo-diario` | `scripts/panel-datos/respaldo_supabase.py` | Ídem |
| `alerta-fallo-workflow` | Ninguno — Error Trigger + nodo Telegram | No toca el pipeline Python |

**Sin fricción adicional real:** los 5 que ejecutan script ya están en la misma carpeta que el
plan ya iba a portar; ninguno agrega Selenium/Chrome ni dependencias nuevas (confirmado por
grep). Solo crece la superficie del mismo tipo de trabajo, no su naturaleza.

### Nodos por tipo (18 workflows, total)

`executeCommand`=45 (antes 35 — creció con los workflows nuevos, no cambió de tipo),
`if`=35, `telegram`=27, `scheduleTrigger`=15, `noOp`=12, `stopAndError`=10,
`respondToWebhook`=8, `googleSheets`=8, `code`=7, `httpRequest`=6, `crypto`=4, `webhook`=3,
`wait`=2, `errorTrigger`=1, `set`=1, `switch`=1, `telegramTrigger`=1.

### Credenciales: sin cambios

Los mismos 4 tipos ya documentados (`googleApi`, `telegramApi`, `httpBasicAuth`, `crypto`).
Ninguna credencial nueva (nada de OAuth de usuario ni API keys adicionales). La conclusión de
"cero fricción de credenciales" sigue vigente.

### `git push`: sin cambios

Grep sobre los 5 scripts nuevos que sí se ejecutan → ningún match. Sigue acotado a los 7
scripts ya documentados (exporters del dashboard).

### Gotcha nuevo

`alerta-fallo-workflow` depende de que cada uno de los otros 17 workflows tenga configurado su
`Error Workflow` (setting a nivel de workflow en n8n, no un nodo) apuntando a él. **Ese setting
no viaja solo** al importar los JSON a una instancia n8n nueva en el droplet — hay que
re-vincularlo workflow por workflow tras la importación, o los fallos dejan de notificarse en
silencio (justo lo que este workflow existe para evitar).

### Nota 2026-08-05 — 3 crons cambiados por optimización de egress Supabase (no invalida el plan)

`q10-sync-supabase` cada 2h→4h, `Bot Q10 - Actualizar Grupos` cada 4h→8h,
`datos-respaldo-diario` diario→cada 3 días. Cambio hecho en vivo vía API + JSON sincronizados.
No afecta nada de esta migración (mismos nodos `executeCommand`, mismo tipo de trigger) — solo
para que la próxima auditoría en vivo no encuentre estos horarios como "drift" sin explicación.
Detalle completo en [[panel-datos-etl]].

## Evaluación de proveedores — 2026-08-04

Investigación solicitada para no comprometerse con DigitalOcean sin mirar alternativas, dado
que el pipeline real depende de 45 nodos `executeCommand` ejecutando Python (acceso a shell
obligatorio — descarta de raíz cualquier PaaS/SaaS sin shell).

| Opción | Costo/mes aprox. | ¿Soporta `executeCommand` arbitrario? | Veredicto |
|---|---|---|---|
| **DigitalOcean** (ya en uso para mr-website) | $6-12 | Sí — VPS con root | **Confirmado.** Único con familiaridad operativa real ya probada (droplet vivo, GitHub Actions, patrón `rofe-composal`) |
| **n8n Cloud** (oficial, hospedado) | $24 (Starter) | **No** — infraestructura compartida, Execute Command no existe en el producto por diseño de seguridad | Descartado de raíz — no correría el pipeline actual, sin excepción |
| **Hetzner Cloud** | ~€4-8 (más barato que DO en specs iguales) | Sí — VPS con root | Descartado — sin datacenter en LatAm (más latencia que DO) y con subidas de precio recientes en 2026; el ahorro no justifica aprender infra nueva |
| **Oracle Cloud Free Tier** | $0 (Always Free, ARM) | Sí — VPS con root | Descartado — Oracle reclama instancias con <20% CPU sostenido en ventanas de 7 días; un n8n con schedules esporádicos calificaría como "idle" y podría perderse la instancia sin aviso. Inaceptable para workflows de alertas/correos |
| **Railway / Render** (PaaS) | ~$5-14 | Técnicamente sí (Docker), pero requiere imagen custom horneada en build, no "SSH y copio archivos" | Descartado — no calza con el patrón actual de editar/copiar 45 scripts y mover `tools/` (PII) puntualmente |

**Conclusión: se mantiene DigitalOcean.** No cambia ninguna fase del plan de ejecución de abajo.

## Investigación de costos + programas non-profit — 2026-08-10

Solicitada para armar una propuesta de presupuesto de la migración. Hallazgo que reencuadra el
problema: **el costo mensual de correr esto es trivial; lo que importa es qué crédito non-profit
capturar y el ajuste operativo, no el precio de lista.**

### Costo real de infraestructura (sin créditos)

n8n + el pipeline Python (pandas en varios scripts) necesita ~2 GB de RAM para ir cómodo. En
DigitalOcean eso es un droplet **Basic 2 GB / 1 vCPU ≈ USD 12/mes** (regular SSD). Facturación
por segundo desde 2026-01-01, con tope mensual al precio de lista.

| Concepto | USD/mes | USD/año | COP/año aprox. (~4.000 COP/USD) |
|---|---|---|---|
| Droplet Basic 2 GB (recomendado) | 12 | 144 | ~576.000 |
| Droplet Basic 1 GB (mínimo, riesgo OOM con pandas) | 6 | 72 | ~288.000 |
| Backups DO (opcional, +20 %) | +2,4 | +29 | ~115.000 |
| Reserva de IP / dominio (ya se tiene `tocaunavida.org`) | 0 | 0 | 0 |

Techo realista con backups: **~USD 175/año ≈ 700.000 COP/año.** Es decir, el presupuesto no es
la restricción — la decisión es de **encaje operativo + qué programa de crédito solicitar.**

### Programas non-profit disponibles (todos con Colombia elegible)

Todos exigen validación previa de la fundación (501(c)(3) o su equivalente colombiano) por un
partner: **Percent** (DigitalOcean), **Goodstack** (Google/Microsoft) o **TechSoup** (AWS). Ese
trámite toma tiempo → es el primer paso, no el último.

| Programa | Monto | Tipo | Cubre la migración | Notas |
|---|---|---|---|---|
| **DigitalOcean for Nonprofits** (vía Percent) | **USD 2.500** | Una sola vez, válido 1 año | Sí, sobradamente (gasta ~USD 144 de 2.500) | **Mejor encaje**: misma infra ya conocida (droplet vivo, GitHub Actions, `rofe-composal`). Año 1 gratis; luego ~USD 144/año, despreciable. Crédito de sobra desperdiciado por ser one-time, pero da igual: cubre todo |
| **Microsoft Azure for Nonprofits** | **USD 2.000/año** | **Renovable cada año** | Sí (VM Azure = root, corre el pipeline) | Cubriría el costo *para siempre* si se renueva. Pero infra desconocida, VM base más cara/mes que DO, más complejidad. No vale cambiar por ahorrar ~USD 144/año |
| **AWS Nonprofit Credit** (vía TechSoup) | **USD 1.000–2.000/año** | Renovable (año fiscal jul–jun) | Sí (EC2 = root) | Igual que Azure: renovable pero infra nueva. Fallback |
| **Google for Nonprofits / Cloud** | hasta USD 10.000/año* | Anual | Parcial | *El grueso son créditos de Maps/Earth/Workspace, no de Compute Engine general. Útil aparte (Workspace gratis), no como host del pipeline |

### Recomendación

1. **Host: DigitalOcean** — ya decidido técnicamente; el crédito non-profit lo confirma también
   por costo. El costo de aprender un hyperscaler (Azure/AWS) supera con creces los ~USD 144/año
   que se ahorrarían con su crédito renovable. Ganancia de familiaridad > ahorro marginal.
2. **Capturar el crédito DigitalOcean de USD 2.500** (solicitud vía Percent) → **año 1 gratis**,
   luego ~USD 12/mes (~576.000 COP/año) a cargo de la fundación. Trivial.
3. **Guardar Azure ($2.000/año renovable) como respaldo documentado** — si algún día el costo DO
   dejara de ser aceptable, es la única alternativa renovable que corre el pipeline sin rehacer
   la arquitectura. No accionar ahora.
4. **Acción bloqueante y lenta: validar a la Fundación ROFÉ como non-profit** ante Percent (y de
   paso Goodstack para Google Workspace). Empezar ya aunque la migración no tenga fecha — el
   crédito no se puede pedir sin la verificación aprobada, y esta puede tardar semanas.

**No cambia ninguna fase del plan de ejecución de abajo** — solo agrega, antes de la Fase 2
(decidir droplet), el paso de solicitar el crédito una vez aprobada la verificación non-profit.

### Fuentes

- DigitalOcean for Nonprofits (USD 2.500 vía Percent): https://www.digitalocean.com/blog/driving-impact-do-for-nonprofits-social-enterprises
- Azure for Nonprofits (USD 2.000/año renovable): https://www.microsoft.com/en-us/nonprofits/azure
- AWS Nonprofit Credit vía TechSoup: https://www.techsoup.org/support/articles-and-how-tos/aws-nonprofit-credit-program-faq
- Google for Nonprofits — países LatAm (incl. Colombia): https://support.google.com/nonprofits/answer/7342714
- DigitalOcean pricing 2026: https://www.digitalocean.com/pricing/droplets

### Adenda 2026-08-10 — reevaluación de Oracle Free Tier (pregunta directa)

Se preguntó de nuevo si una instancia gratuita de Oracle serviría. Reevaluado con datos frescos;
matiza (no invalida) el "descartado" del 2026-08-04:

- **Sí es técnicamente viable:** VPS con root, corre el pipeline. El ARM A1, aun tras el recorte
  de junio 2026 (4→2 OCPU / 24→12 GB), deja **12 GB de RAM** — más que el droplet DO de USD 12
  recomendado. De sobra para n8n + pandas.
- **La objeción de "idle reclamation" era demasiado absoluta.** La política real (confirmada, doc
  Oracle jun-2026) es CPU <20 % percentil-95 en 7 días, y **solo aplica a cuentas 100 % Always
  Free**. Se neutraliza con *upgrade a Pay As You Go* (sigue en USD 0 dentro de límites free) o un
  cron keep-alive. Ese punto solo NO descalifica.
- **Lo que sí descalifica (y empeoró en 2026):** Oracle **recortó a la mitad el ARM free en
  junio 2026 sin aviso** (sin blog ni correo previo) y **termina las instancias sobre el límite
  nuevo el 18-ago-2026**; además "out of host capacity" crónico para crear A1 en varias regiones.
  Es cambiar el riesgo "el portátil se apaga sin avisar" por "Oracle recorta/termina la instancia
  sin avisar" — riesgo externo, no controlable, sobre el sistema de alertas/correos. Contradice el
  objetivo mismo de la migración.
- **Costo ya no favorece a Oracle:** solo ahorra ~USD 144/año vs DO, y el crédito non-profit de DO
  deja el año 1 en USD 0 de todos modos. No vale la reliability.
- **Uso legítimo de Oracle Free:** entorno de pruebas gratis para la **Fase 1** (congelar
  `requirements.txt` en Linux ARM limpio) o standby frío, donde su inestabilidad no afecta
  producción.

**Veredicto: se mantiene DigitalOcean para producción.** Oracle Free queda como posible sandbox
de Fase 1, no como host de los workflows.

Fuentes adenda: reclamación idle (20 %, doc Oracle jun-2026) https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm · recorte ARM jun-2026 https://www.infoq.com/news/2026/07/oracle-cloud-free-tier-limits/

### Adenda 2026-08-10 (b) — CAMBIO DE DECISIÓN: se intentará Oracle Free (con mitigaciones)

Nuevo dato del usuario: **el costo del droplet DO se considera elevado** para la fundación, y se
decide **usar la capacidad de cómputo gratuita de Oracle**. Esto revierte el "descartado" de
Oracle (que se había escrito bajo el supuesto de que el costo era trivial). Con el costo como
restricción real, Oracle deja de ser capricho arriesgado y pasa a ser opción razonable —
**siempre que se mitiguen sus riesgos de entrada.** Encaje técnico a favor: ARM A1 free
**2 OCPU / 12 GB** tiene *más* RAM que el droplet DO de USD 12 recomendado, y cuesta USD 0.

**Perfil de recursos que hay que cubrir** (medido sobre el código, no supuesto): n8n es solo
orquestador (Node+SQLite persistente ~250-450 MB); los scripts Python son ráfagas cortas de I/O
(sin numpy pesado, sin Selenium/Chrome, sin multiprocessing; pandas/openpyxl sobre cientos-2.500
filas ≈ 100-300 MB pico por proceso). CPU casi irrelevante (I/O-bound). El driver de disco/ancho
de banda son los **videos de Zoom→YouTube/Drive** en tránsito. → 12 GB RAM sobran; 2 OCPU sobran.

**Mitigaciones obligatorias (sin esto, sí es mala idea):**
1. **Upgrade a Pay As You Go** (sigue en USD 0 dentro de límites free) → elimina la reclamación
   por idle, que solo aplica a cuentas 100 % Always Free. + cron keep-alive redundante.
2. **Provisionar desde el inicio en 2 OCPU / 12 GB** (el límite nuevo post-jun-2026) → no ser
   blanco de las terminaciones por exceso (las del 18-ago-2026 son a quienes seguían en 4 OCPU).
3. **Monitor de uptime EXTERNO** (UptimeRobot / healthchecks.io → `/healthz` de n8n). Crítico:
   `alerta-fallo-workflow` corre dentro de la instancia; si Oracle la apaga, esa alerta muere con
   ella — la red de seguridad tiene que ser externa.
4. **Estado respaldado + reconstrucción rápida:** backup del SQLite `~/.n8n` (además del export
   JSON de workflows que ya existe) + Docker Compose para rebuild en ~20 min. Útil igual porque
   los flujos se actualizarán continuamente.
5. **Región con capacidad** (Frankfurt/Singapur suelen provisionar en minutos) para sortear el
   "out of host capacity" del ARM; el dolor es al crear, no después. Latencia extra a LatAm
   irrelevante para batch nocturno.

**Secuencia de corte de bajo riesgo:** correr Oracle **en paralelo con el portátil unas semanas**
(mismos workflows, comparando salidas) antes de apagar el local. Si Oracle demuestra estabilidad,
se apaga el portátil con confianza; si da problemas de capacidad/reclamación, no se perdió nada.

**Pendiente de esta decisión:** todas las "Decisiones abiertas" siguen vigentes (auth git, dominio,
webhooks, `tools/` PII), solo cambia el host destino de DO → Oracle. DigitalOcean queda como
fallback si Oracle resulta inestable en el periodo de paralelo.

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

## Plan de ejecución — Oracle Cloud Free Tier (2026-08-10)

**Este es el plan vigente.** Supersede el borrador genérico "Fases propuestas" de abajo (que
quedaba escrito para DigitalOcean). El destino ahora es Oracle Free ARM (ver adenda 2026-08-10 (b)
para el porqué). DigitalOcean queda como fallback documentado.

**Objetivo del corte:** los 18 workflows corriendo 24/7 en una instancia Oracle ARM A1
(2 OCPU / 12 GB, USD 0), con webhooks públicos propios, `git push` no-interactivo, y monitoreo
externo — sin dependencia del portátil de Samuel.

**Runbook de ejecución cronometrado:** `runbooks/migracion-oracle-runbook.md` — detalla el "cómo"
con comandos y tiempos, dividido en Bloque A (pre-montaje sin downtime), Bloque B (corte 30-45 min)
y Bloque C (rollback). Este plan de fases es el "qué"; el runbook es el "cómo" paso a paso.

**Principio rector:** nada se apaga en el portátil hasta que Oracle demuestre estabilidad en un
periodo de paralelo. Rollback siempre disponible = reactivar `iniciar_n8n.bat` local.

### Fase 0 — Preparación local (NO requiere la instancia; empezar ya)

- [ ] **0.1 Congelar dependencias.** Generar `requirements.txt` real por carpeta que hoy no lo
  tiene (`scripts/panel-datos/`, `scripts/zoom-youtube/`, `scripts/zoom-asistencia/`,
  `scripts/mujeres-rofe-correos/`), corriendo cada script en un venv limpio. **Probar en ARM64**
  (no solo x86): usar WSL con emulación o un contenedor `arm64v8/python` — pandas/openpyxl/google
  libs tienen wheels aarch64, pero conviene confirmarlo antes, no en el droplet.
- [ ] **0.2 Escribir `docker-compose.yml`** (n8n + Caddy reverse proxy) y un `Dockerfile` para el
  runner Python (base `python:3.x-slim` arm64 + los `requirements.txt` consolidados + git + tzdata
  `America/Bogota`). n8n y el runner comparten volumen con el repo montado.
- [ ] **0.3 Inventariar los 45 `executeCommand`** y su reescritura `cmd.exe → bash`
  (`cd /d C:\... → cd /ruta && python3 ...`). Producir un mapeo nodo→comando-nuevo antes de tocar
  n8n. Es el ítem de mayor trabajo manual del plan.
- [ ] **0.4 Verificar la app OAuth de Google** (`subir_yt_grabacion.py`) esté en estado
  "In production" en Google Cloud Console — si sigue en "Testing", el refresh token expira a los
  7 días independientemente del host (riesgo preexistente, no de la migración).

### Fase 1 — Provisionar Oracle (con las mitigaciones de la adenda)

- [ ] **1.1 Crear cuenta Oracle Cloud** + **upgrade a Pay As You Go** de inmediato (sigue en USD 0
  dentro de límites free; elimina la reclamación por idle).
- [ ] **1.2 Provisionar instancia ARM A1 = `VM.Standard.A1.Flex`, 2 OCPU / 12 GB**, imagen
  **Ubuntu 22.04 LTS (aarch64)**, en región con capacidad (Frankfurt/Singapur si el home region da
  "out of host capacity"). Reservar **IP pública efímera→reservada** para que no cambie.
- [ ] **1.3 Abrir puertos** en DOS capas (gotcha Oracle):
  (a) **Security List / NSG** de la VCN: ingress 80 y 443 desde 0.0.0.0/0;
  (b) **firewall del SO** — las imágenes Ubuntu de Oracle traen `iptables` restrictivo por defecto;
  abrir 80/443 con `iptables`/`netfilter-persistent` o el problema es invisible ("todo bien en la
  consola pero no responde").
- [ ] **1.4 Instalar Docker + Docker Compose** (arm64) y clonar el repo.

### Fase 2 — Dominio, SSL y auth no-interactiva

- [ ] **2.1 Subdominio** (ej. `n8n.tocaunavida.org`) → A record a la IP reservada de Oracle.
- [ ] **2.2 Caddy** como reverse proxy → SSL automático Let's Encrypt (sin fricción).
- [ ] **2.3 Proteger el editor n8n** expuesto a internet: activar **n8n user management** (login)
  o basic auth. Hoy solo estaba tras túnel + red local; en Oracle queda público.
- [ ] **2.4 Deploy key SSH para git:** generar par en la instancia, cargar la pública como deploy
  key **con escritura** en `github.com/Fundacion-ROFE/Estadisticas`, y cambiar el remoto de los 7
  exporters a `git@github.com:...` (hoy usan `credential.helper=manager` de Windows + schannel,
  **ninguno existe en Linux**). Configurar `user.name/user.email` del bot y quitar
  `http.sslBackend=schannel` de los scripts (o condicionarlo a Windows).

### Fase 3 — Credenciales, PII y datos internos

- [ ] **3.1 Copiar las 4 credenciales n8n** (`googleApi` = JSON del service account, `telegramApi`
  = token, `httpBasicAuth` = Zoom S2S, `crypto` = HMAC Zoom). Todas portables, sin redirect URI.
- [ ] **3.2 Copiar los `.env` dispersos** de los scripts (SMTP MR/JC, refresh token OAuth Google
  de `subir_yt_grabacion.py`, Supabase service_role, Emoflow, etc.) — nunca por git.
- [ ] **3.3 Transferir `tools/` (PII)** por `scp`/`rsync` puntual (gitignoreado, nunca viajó por
  git). Confirmar permisos restrictivos en el destino.
- [ ] **3.4 Revisar `NODE_TLS_REJECT_UNAUTHORIZED=0` y `truststore.inject_into_ssl()`** — existían
  solo por el proxy MITM corporativo; **quitar** en Oracle (dejarlos sería regresión de seguridad).
  Mantener `NODES_EXCLUDE=[]` (reactiva `executeCommand`) y `GENERIC_TIMEZONE/TZ=America/Bogota`.

### Fase 4 — Levantar n8n e importar workflows (INACTIVOS)

- [ ] **4.1 `docker compose up`** — n8n vivo tras Caddy con SSL.
- [ ] **4.2 Importar los 18 workflows** vía API (`POST /workflows`) desde `n8n-workflows/`.
- [ ] **4.3 Aplicar la reescritura de los 45 `executeCommand`** (mapeo de Fase 0.3).
- [ ] **4.4 Re-vincular el `Error Workflow`** de los 17 workflows → `alerta-fallo-workflow`
  (setting a nivel de workflow que **NO viaja** al importar el JSON; sin esto los fallos dejan de
  notificarse en silencio).
- [ ] **4.5 Dejar TODO inactivo.** Aún no se registran webhooks ni se activan schedules.

### Fase 5 — Monitoreo externo (mitigación crítica, antes del paralelo)

- [ ] **5.1 Monitor de uptime externo** (UptimeRobot / healthchecks.io) al `/healthz` de n8n.
  Imprescindible: `alerta-fallo-workflow` corre dentro de la instancia; si Oracle la apaga, esa
  alerta muere con ella — la red de seguridad debe ser externa.
- [ ] **5.2 Cron keep-alive** redundante (además del PAYG) para no calificar como idle.
- [ ] **5.3 Backup del estado n8n:** volcado periódico de `~/.n8n` (SQLite) además del export JSON
  de workflows que ya existe.

### Fase 6 — Correr en paralelo (semanas, no días)

- [ ] **6.1 Activar en Oracle** los schedules **desfasados** respecto al portátil (o en un Sheet/
  tabla de staging) para **comparar salidas** sin doble-escritura en producción.
- [ ] **6.2 Validar los caminos peligrosos:** `git push` real (deploy key), subida de video a
  YouTube/Drive (disco/ancho de banda en tránsito), correos MR/JC (SMTP), sync Supabase.
- [ ] **6.3 Vigilar estabilidad de Oracle** en la ventana: ninguna reclamación, sin "out of
  capacity" al reiniciar, RAM/disco sanos. Si algo falla, se corrige sin apagar el local.

### Fase 7 — Corte (día D)

- [ ] **7.1 Re-registrar webhooks** al dominio nuevo el **mismo día**: Zoom Event Subscriptions y
  Telegram `setWebhook` (hoy ambos apuntan a la URL ngrok). El viejo debe seguir sirviendo hasta
  este momento, no antes.
- [ ] **7.2 Activar los 18 workflows** en Oracle con sus horarios reales.
- [ ] **7.3 Apagar el local:** desactivar Task Scheduler + `iniciar_n8n.bat`.
- [ ] **7.4 Rollback si hace falta:** reactivar `iniciar_n8n.bat` + re-apuntar webhooks a ngrok.

### Fase 8 — Cierre

- [ ] **8.1 Retirar ngrok** una vez confirmado que nada depende de la URL vieja.
- [ ] **8.2 Actualizar** [[convenciones]], [[mapa-codigo]] y `00-vision-global.md` con la nueva
  realidad (host, dominio, auth git), y el evento espejo en [[agenda-calendar-n8n]] si cambian
  horarios.
- [ ] **8.3 Documentar el runbook de reconstrucción** (rebuild ~20 min desde compose) por si
  Oracle reclama la instancia — es la contraparte operativa de "sin SLA".

### Riesgos Oracle-específicos y su dueño en el plan

| Riesgo | Mitigado en |
|---|---|
| Reclamación por idle | Fase 1.1 (PAYG) + 5.2 (keep-alive) |
| Recorte/terminación de límites sin aviso | Fase 1.2 (nacer en 2 OCPU/12 GB, compliant) |
| "Out of host capacity" al crear/reiniciar | Fase 1.2 (región con capacidad) |
| Pérdida silenciosa de la instancia | Fase 5.1 (uptime externo) + 8.3 (rebuild rápido) |
| Dependencias que no compilan en ARM64 | Fase 0.1 (probar en aarch64 antes) |
| Puertos "abiertos" en consola pero SO bloquea | Fase 1.3 (doble capa: NSG + iptables) |

---

## Fases propuestas (borrador, sin fecha — SUPERSEDIDO por el plan Oracle de arriba)

> Conservado como referencia histórica del plan genérico DigitalOcean. El plan vigente es el de
> Oracle (sección anterior).

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

## Mitigación mientras no hay fecha de ejecución (riesgo de transporte físico)

El disparador de 2026-08-04 es operativo, no solo de investigación: mientras el plan completo
no tenga fecha, el portátil de Samuel viajando físicamente varias veces es un riesgo real de
continuidad (si se apaga o pierde red durante el transporte, los 18 workflows dejan de correr
sin que nadie lo note salvo por `alerta-fallo-workflow`, que depende del propio portátil).
**No existe un atajo de "copiar n8n a la nube por un rato"** sin hacer el trabajo real de portar
los 45 `executeCommand` a Linux — no es un mitigante de una tarde. Opciones reales mientras se
decide fecha:
- Corto plazo: reforzar lo ya mitigado en [[n8n_suspend_resume]] (powercfg + tarea auto-heal) y
  asegurarse de que el cargador viaje con el portátil (ya documentado como requisito #1).
- Medio plazo: adelantar la Fase 1 (congelar `requirements.txt` por carpeta, probar en venv
  Linux/WSL) — es la única fase que **no depende de tener el droplet listo** y reduce el
  trabajo real de la migración sea cual sea la fecha de corte.

## Pendiente / Próximos pasos

- [ ] Responder las "Decisiones abiertas" de arriba (empezar por: ¿droplet compartido con
  mr-website o nuevo?).
- [ ] Congelar `requirements.txt` faltantes.
- [ ] Volver a correr la auditoría en vivo si pasan >2-3 semanas o se agregan workflows nuevos
  antes de escribir el plan de ejecución definitivo.
- [x] Evaluar proveedores alternativos a DigitalOcean (Hetzner, n8n Cloud, Oracle Free Tier,
  Railway/Render) — hecho 2026-08-04, DigitalOcean confirmado, ver sección arriba.

## Adenda 2026-08-10 — evidencia dura de indisponibilidad (incidente real)

Un incidente real cuantificó por primera vez el costo de depender del portátil. El pipeline
llevaba **~62h de datos vencidos** (las 8 tablas de `v_frescura`). Diagnóstico en vivo contra
`GET /api/v1/executions`:

- **NO fue OOM.** La etiqueta `WorkflowCrashedError: possible out-of-memory issue` que emite n8n
  es **genérica** para cualquier muerte del proceso a mitad de ejecución. Se descartó memoria por
  datos: la tabla más grande es `participants_snapshots` con 21 filas / 8.4 MB; ninguna llega a
  decenas de MB; los helpers de paginación (`get_todo`, `offset += page` + break) están sanos; los
  scripts imprimen resúmenes, no vuelcan datos a stdout. El único `crashed` (Ago 10 13:32Z) fue el
  **reinicio de n8n matando la ejecución en curso** (el `.bat` mata la instancia previa al arrancar).
- **La causa fue disponibilidad.** El timeline de ejecuciones muestra huecos donde n8n no ejecutó
  NADA: **Ago 9 de 01:00Z a 23:28Z (~22h)** y **Ago 10 de 02:00Z a 13:32Z (~11.5h)**. La ventana
  nocturna de `q10-sync-supabase` (COT 17-07h) cayó dentro de esos huecos → nunca se disparó. Último
  éxito real: Ago 8 23:26Z. También se vio una "ejecución" del 08-07 15:29Z que terminó 08-08 14:58Z
  (**23.5h colgada** = suspend/resume a mitad de corrida, el gotcha de [[n8n_suspend_resume]]).
- **Powercfg ya está al máximo.** Standby idle = `0x0` (NUNCA) en AC y DC; tareas
  `n8n-auto-heal-resume` (corriendo) e `Iniciar n8n ROFE` activas. El hueco de 22h del Ago 9 fue el
  equipo **físicamente apagado / de viaje**, que ninguna config local resuelve. **No queda nada por
  ajustar en el portátil** → la migración es la única solución de fondo.

**Acción tomada:** se destrancó el dato corriendo los 10 scripts a mano (los 8 de `q10-sync` +
`extract_emoflow_ingresos_diario.py` + `calcular_asistencia_promedio.py`) → `v_frescura` en
`vencidos=0/8`. Y se creó una **rutina de monitoreo en la nube** (`frescura-pipeline-rofe`,
independiente del portátil) que cada mañana lee `v_frescura` y avisa por Telegram con el veredicto
clasificado; incluye reintento remoto para fallos aislados vía el workflow `rerun-dispatcher`
(webhook autenticado). Ver [[panel-datos-etl]] y la memoria de la rutina.

**Implicación para el plan:** este incidente eleva la prioridad. Mientras no haya migración, el
riesgo no es hipotético — ya se materializó (62h sin dato). La rutina en la nube es un mitigante de
**detección**, no de **continuidad**: avisa, pero no hace correr los workflows si el portátil está
apagado.
