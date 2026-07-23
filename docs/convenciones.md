# Convenciones Técnicas

> Estándares reutilizables para todas las automatizaciones. Si una decisión técnica se
> repite en 2+ procesos, documéntala aquí y referencia desde la nota del proceso en
> lugar de repetir la explicación completa.
> **Conexiones:** [[00-vision-global]] · [CLAUDE.md](../CLAUDE.md) · [[mapa-codigo]]

## Naming
- Workflows de n8n: `[area]-[accion]` en minúsculas, con guiones.
  Ejemplos: `zoom-asistencia`, `q10-consolidacion`, `meet-creacion`.
- Notas de proceso en `docs/procesos/`: mismo nombre que el workflow, extensión `.md`.
- Scripts Python en `scripts/[nombre-proceso]/`.

## Manejo de errores (estándar mínimo)
Todo workflow en producción debe tener:
- Un camino de error explícito (nodo de notificación, log, o reintento) — nunca dejar que un fallo simplemente detenga el flujo en silencio.
- [Definir aquí cuando se decida: ¿notificación por email? ¿canal de Slack/Teams?
  ¿registro en una hoja de errores?]

## Credenciales reutilizables en n8n

| Credencial                      | Usada en          | Notas                                                               |
| ------------------------------- | ----------------- | ------------------------------------------------------------------- |
| Google Sheets (Service Account) | q10-consolidacion | `q10-automatizacion@n8n-automatizacion-q10.iam.gserviceaccount.com` |
| Telegram Bot                    | q10-consolidacion | ID credencial en n8n: `kGTAfWTTp4FATF66`                            |
| Google Calendar                 | (pendiente)       |                                                                     |
| Zoom (Server-to-Server OAuth)   | zoom-asistencia   | Credenciales en `scripts/zoom-asistencia/.env` (gitignoreado). Scopes: `meeting:read:past_meeting:admin`, `meeting:read:list_past_participants:admin` |
| Supabase `panel-datos-rofe`     | panel-datos-etl   | Proyecto `kbxptoowtnteflhrfwid` (us-east-1), URL `https://kbxptoowtnteflhrfwid.supabase.co`. Keys en `.env.local` raíz (gitignoreado; plantilla en `.env.example`). Anon key = solo lectura de agregados vía RLS. **service_role bypasea RLS — solo n8n/backend, jamás frontend ni Git** |

### Formato de `.env.local` (raíz) — ojo: NO es python-dotenv

Los scripts de `panel-datos/` no usan `python-dotenv`: traen su propio `cargar_env_local()`
(ver `cargar_supabase.py:62`), que hace `k, v = linea.split("=", 1)` +
`os.environ.setdefault(k.strip(), v.strip())`. Toma el valor **crudo**:

```
SUPABASE_SERVICE_ROLE_KEY=sb_secret_...      ← así
```

- **Sin comillas.** `KEY="abc"` deja el valor literalmente como `"abc"` (con comillas) → falla el auth.
- **Sin `export`.** `export KEY=abc` hace que la variable se llame `export KEY`.
- **Sin comentario al final de línea.** `KEY=abc # nota` mete ` # nota` dentro del valor.
  Un `#` en su propia línea sí es un comentario válido.
- `setdefault` → **una variable ya exportada en el entorno le gana al archivo**. Si un script
  "ignora" tu `.env.local`, revisá que no la tengas exportada en la sesión.

Todo script nuevo que lea Supabase debe llamar a `cargar_env_local()` en `main()`. Plantilla de
variables en `.env.example` (único `.env*` versionado; el resto los excluye `.gitignore`).

### Gotcha: secreto commiteado por error

Pasó el 2026-07-14 (ver `docs/archivo/SECURITY-INCIDENT.md`). Si el push protection de GitHub bloquea un push:

1. **Primero averiguar si el secreto ya llegó al remoto:** `git branch -r --contains <commit>`.
   Si no devuelve nada, fue un casi accidente y la reescritura de historia lo resuelve del todo.
   Si sí llegó a un repo público, la reescritura **no lo des-publica** — hay que asumir compromiso
   y **rotar la clave de inmediato**.
2. **Nunca escribir el valor del secreto en la nota del incidente.** Se hizo, y el documento pasó
   a ser la fuga que decía documentar: el push siguió bloqueado por ese archivo. Documentar
   *dónde* estuvo y *qué* se hizo, jamás el valor.
3. **Purgar:** `git filter-repo --replace-text reemplazos.txt --force` (formato:
   `<literal>==>***SECRETO-PURGADO***`; el archivo va fuera del repo). Etiquetar un respaldo antes.
   filter-repo **elimina el remoto `origin`** — re-agregarlo después. Si el secreto solo estaba en
   commits locales, los ya pusheados conservan su SHA y el push queda como fast-forward, sin `--force`.
4. **Verificar sobre todos los objetos**, no solo los commits vivos:
   `git cat-file --batch-all-objects --batch-check` + grep del literal en cada blob.

## SSL corporativo

Esta red tiene un proxy/firewall corporativo que intercepta HTTPS (MITM). Aplica a **todos** los procesos que hagan llamadas HTTP desde Python o n8n.

**En Python** — antes de importar `requests`:
```python
import truststore
truststore.inject_into_ssl()
import requests
```

**En n8n** — variable de entorno en el bat de arranque:
```
set NODE_TLS_REJECT_UNAUTHORIZED=0
```

**En git** — una sola vez por repo, usa el cert store de Windows en vez de OpenSSL:
```bash
git config --local http.sslBackend schannel
```
Si se clona un repo nuevo en esta red, aplicar este comando antes del primer push.

**Tunnel externo:** usar **ngrok con dominio estático** (`ergonomic-absinthe-refract.ngrok-free.dev` → `localhost:5678`). La URL no rota nunca — es la que consumen los webhooks de Zoom y Telegram. Config en `%LOCALAPPDATA%\ngrok\ngrok.yml` (tunnel `n8n`); lo arranca `iniciar_n8n.bat`.

```
ngrok start n8n
```

Requiere agente ngrok **≥ 3.20** y free tier permite **un solo agente** simultáneo. Historial: se usó `cloudflared` (2026-06) porque una versión vieja de ngrok fallaba con `x509` tras el proxy corporativo — con ngrok 3.39.9 ya no ocurre, y cloudflared quedó retirado (2026-07-07) porque su URL efímera rotaba en cada reinicio. Detalle completo (config, arranque, gotchas): [[reference-ngrok-tunel-fijo]].

## Q10 Login multi-paso

Q10 NO tiene un endpoint único de login. El flujo son **7 solicitudes AJAX encadenadas**:
resolución de subdominio → institución → rol → 2FA/verificación → confirmación de sesión.

Usar `requests.Session()` durante toda la cadena. Ya implementado en `scripts/q10-consolidacion/q10_to_sheets.py`. No reescribir desde cero.

## Autodescubrimiento de periodos por año

Q10 asigna a cada periodo académico un **ID incremental** (18, 19, 20…). No están agrupados por
año de forma contigua (ej. IDs 18/19 = 2025, pero 20 = 2026). Nunca hardcodear la lista de IDs:
se desactualiza sola cuando la Fundación abre un curso o cohorte nuevo, y perderlo es silencioso.

**Patrón:** sondear un rango de IDs, leer la columna `Período` de cada Consolidado (se autoetiqueta
con el año, ej. `Logica-Nivel 2-2026`) y conservar **solo los del año en curso**. El año es el último
token tras el guión: `etiqueta.rsplit("-", 1)[-1] == AÑO_OBJETIVO`. Los IDs inexistentes devuelven
`not_results` y se descartan sin costo. Implementado en `descargar_todos_consolidados(session, anio)`.

**No usar "todos los periodos con datos"** como criterio: mezclaría años y duplicaría estudiantes
del mismo curso entre cohortes (verificado: 2025 y 2026 tienen los mismos nombres de curso). El
filtro por año es obligatorio. `AÑO_OBJETIVO` = año en curso por defecto; override con `--anio YYYY`.

## Expresiones en n8n 2.x

Reglas críticas — los errores aquí son silenciosos y difíciles de debuggear:

| Regla | Correcto | Incorrecto |
|---|---|---|
| Activar expresión en un campo | `={{ 'texto ' + $json.var }}` | `{{ 'texto ' + $json.var }}` (no evalúa) |
| Rutas Windows dentro de expresión JS | `C:/Users/foo/bar` | `C:\Users\foo\bar` (backslashes se descartan) |
| Newlines en string JS dentro de JSON | `\\n` en el JSON | `\n` (newline real → SyntaxError en JS) |
| Habilitar nodo Execute Command | `NODES_EXCLUDE=[]` en env | `N8N_ALLOW_EXEC=true` (era n8n 1.x, no existe en 2.x) |

**Webhook con espacios en nombre de nodo:** agregar `"webhookId": "<uuid-v4-fijo>"` al nodo Trigger. Sin él, n8n codifica el nombre con `%20` → Express lo decodifica al recibir → path mismatch → 404.

## Doble encabezado en Google Sheets

Patrón presente en **h2test** y en la pestaña **Avance** del Sheet manual. La Sheets API devuelve el valor de celda fusionada solo en la primera columna del grupo; las siguientes vienen como cadena vacía.

```
Fila 1 (row0): "NOMBRE CURSO"  ""  ""  ""  ""  ""  ""   "OTRO CURSO"  ...
Fila 2 (row1): "Identificacion" "Nombre" "Celular" "Email" "Avance" "" ""   "Identificacion" ...
Fila 3+:        datos
```

**Patrón de detección (`detectar_grupos`):**
1. Escanear `row1` buscando "identificac" o "número id" → cada posición es el inicio de un grupo.
2. El nombre del curso = `row0[col_inicio].strip()` (puede ser vacío si el grupo no tiene nombre).
3. El final del grupo = inicio del siguiente grupo (o fin de `row0`).
4. Dentro del grupo, encontrar el offset del campo de avance/progreso escaneando `row1`.

Ya implementado en `export_stats.py` y `export_avance.py`. Al crear un script para una hoja nueva con este patrón, reutilizar `detectar_grupos()`.

## Fórmulas vía Sheets API en spreadsheets con locale es_ES

Descubierto en zoom-asistencia (spreadsheet `H3Test`, locale `es_ES`). Aplica a **toda**
fórmula enviada por API — tanto `values.update` con `USER_ENTERED` como las
`CUSTOM_FORMULA` de reglas de formato condicional (`batchUpdate` responde 400
`Invalid ConditionValue.userEnteredValue` si el separador está mal):

- Separador de argumentos: `;` (no `,`) — `VLOOKUP(A1;B:C;2;FALSE)`.
- Separador de **columnas** en literales de array `{...}`: `\` (no `,`) — `{A:A\B:B}`.
- Los nombres de función van en inglés igual (la API los acepta en cualquier locale).
- Si la fórmula no usa comas literales dentro de strings, basta un `replace(",", ";")`
  (helper `loc()` en `scripts/zoom-asistencia/setup_zoom_asistance.py`).
- Verificar el locale antes de escribir fórmulas: `sh.fetch_sheet_metadata()['properties']['locale']`.

## Subida a Google Sheets (estándar)

Patrón establecido en q10-consolidacion, reutilizable en otros procesos:
- Lotes de 500 filas con pausa de 1.2s entre lotes (respeta cuota de la API).
- Borrar desde fila 2 antes de subir — nunca tocar fila 1 (headers).
- Todo a string antes de subir (`df.astype(str)`).
- Columna faltante → advertir en consola, no crashear.

## Lectura de Sheets en pipelines (tolerante a fórmulas sueltas)

Nunca usar `get_all_records()` directo en un script de pipeline: exige encabezados únicos y
**una fórmula suelta que un humano ponga en la fila 1** (visto 2026-07-08: `FILTRAR` en
`H1Test!J1` → `#NAME?` → encabezados vacíos duplicados) tumba todo lo que sigue en la cadena.
Usar el patrón `leer_registros(ws)`: `get_all_values()` + conservar solo columnas con encabezado
no vacío y no duplicado (ver `organizador_headless.py`). Regla para humanos: fórmulas de análisis
van en pestañas aparte, nunca en las pestañas que los scripts leen/escriben.

## Timezone en Schedule Triggers de n8n

Sin configuración, n8n interpreta las horas de los Schedule Triggers en **America/New_York**
(su default), no en hora de Colombia. Estándar del proyecto (2026-07-08):
- `GENERIC_TIMEZONE=America/Bogota` y `TZ=America/Bogota` en `iniciar_n8n.bat` (default de instancia).
- `settings.timezone = "America/Bogota"` en cada workflow con schedule (vía API o UI → Workflow Settings).
- Los schedules **no se recuperan** si n8n estaba apagado a la hora del disparo — programar a horas
  en que el PC esté encendido de forma confiable (n8n arranca ~8:45–8:50 con el inicio de sesión).

## Sincronización Form → BD en Sheets (diff por celda)

Patrón establecido en [[mr-actualizacion-datos]], reutilizable para cualquier Google Form que
alimente una BD en Sheets:

- **Llave de cruce = cédula normalizada** (solo dígitos). El correo no sirve de llave: typos,
  mayúsculas y columnas duplicadas.
- **Deduplicar respuestas por llave** antes de cruzar — gana la marca temporal más reciente.
- **Diff por celda, no por fila:** escribir solo celdas cuyo valor normalizado difiere → corridas
  idempotentes (re-ejecutar sin datos nuevos no toca nada ni re-fecha filas).
- **Comparación insensible a tildes** (unaccent NFD): los forms suelen llegar sin acentos;
  sin esto se "actualiza" `Sofía`→`Sofia` degradando datos ya correctos.
- **Vacío nunca sobreescribe** un dato existente.
- **Registros sin match → clasificar antes de agregar** (desde 2026-07-08): si la llave está en la
  pestaña de retiradas/inactivas → no agregar, solo reportar; si hay ≥2 señales de que es la misma
  persona que una fila existente (correo igual, celular igual, nombre exacto/contenido, cédula a
  distancia Levenshtein ≤2, o cédula = su propio celular) → posible typo de llave, no agregar y
  reportar el candidato; solo lo realmente desconocido entra como **fila nueva al final con color
  de fondo** (repeatCell/backgroundColor) para revisión humana. Una sola señal NO basta (hay
  celulares compartidos entre personas distintas).
- **Columna de fecha localizada por header** (no índice fijo) — sobrevive a columnas basura o
  reordenamientos.

## Herramientas web estáticas (GitHub Pages)

Patrón establecido en `docs/pseudonimizador/index.html`, reutilizable en cualquier herramienta de procesamiento en el navegador:

- **Web Worker inline para archivos grandes:** cuando el procesamiento puede superar ~100 MB de RAM (archivos xlsx con muchas pestañas, transformaciones masivas), mover la lógica a un Worker con heap propio. Se construye como Blob URL en runtime para mantener el archivo como HTML único sin dependencias de servidor.
  ```javascript
  const code = [ /* líneas del worker como array de strings */ ].join('\n');
  const url = URL.createObjectURL(new Blob([code], {type:'application/javascript'}));
  const worker = new Worker(url);
  // Al terminar: URL.revokeObjectURL(url); worker = null;
  ```
- **Transferibles vs clones:** `Uint8Array` y `ArrayBuffer` enviados vía `postMessage` sin listar en el tercer argumento se **clonan** (main conserva copia). Listarlos en `[transferables]` los **mueve** sin copia — destructivo para el emisor. Para archivos de 22 MB, clonar es aceptable.
- **Salida de SheetJS en Worker:** usar `XLSX.write(wb, {type:'uint8array', bookType:'xlsx'})` → devuelve `Uint8Array` cuyo `.buffer` es un `ArrayBuffer` transferible sin copia de vuelta al hilo principal.
- **`importScripts` en Blob Workers:** funciona con CDNs que tienen cabeceras CORS (ej. unpkg.com, cdn.jsdelivr.net). No funciona si el CSP corporativo bloquea `worker-src blob:`.

---

## Zoom Server-to-Server OAuth

Patrón establecido en [[zoom-asistencia]], reutilizable en cualquier proceso que consuma la API de Zoom.

- **Credenciales:** Account ID, Client ID, Client Secret — guardar en `.env` dentro de la carpeta del proceso (ej. `scripts/zoom-asistencia/.env`), nunca hardcodeadas. Ya cubierto por el `.gitignore` global (`.env` sin ruta, aplica a cualquier carpeta).
- **Probar credenciales antes de construir el workflow:**
  ```bash
  curl -X POST "https://zoom.us/oauth/token?grant_type=account_credentials&account_id=$ZOOM_ACCOUNT_ID" \
    -H "Authorization: Basic $(printf '%s:%s' "$ZOOM_CLIENT_ID" "$ZOOM_CLIENT_SECRET" | base64 -w0)"
  ```
  HTTP 200 con `access_token` en la respuesta = credenciales válidas.
- **Scopes:** el catálogo granular de Zoom cambió varias veces en 2023-2024 — buscar por el string interno (ej. `past_meeting`), no por palabras sueltas en el buscador del Marketplace. Preferir siempre variantes `:admin` en apps Server-to-Server (no atadas a un usuario específico, necesitan alcance de cuenta completa).
- **Event Subscriptions (webhooks) no es un feature de pago** — está incluido en cualquier app Server-to-Server OAuth. El texto que menciona "Challenge-response check" en esa pantalla es solo la descripción del mecanismo de validación (CRC), no una condición comercial.
- **Publish/Activate ≠ configurar el webhook.** Son pasos independientes: Activate solo habilita las credenciales OAuth; el endpoint del webhook se agrega aparte en Event Subscriptions, y esa pantalla exige que la URL ya esté respondiendo (falla el CRC si no). Construir primero el Webhook Trigger en n8n, después pegar la URL en Zoom.
- **UUID vs Meeting ID:** endpoints tipo `past_meetings/{uuid}` requieren el UUID de la instancia, no el ID numérico. Si el UUID empieza con `/` o contiene `//`, hay que URL-encodearlo dos veces en el path o la API responde 404 sin explicación.

## Patrones de integración con Workspace
*(se documentan aquí decisiones que aplican a cualquier proceso que use Calendar/Sheets,
para no redescubrirlas cada vez)*
- Pendiente: documentar cómo se resuelve el Meeting ID/link desde un evento de Calendar
  una vez que el proceso de Zoom lo resuelva — es candidato a reutilizarse en Meet.

## Decisiones de infraestructura
- n8n 2.8.4 corre directamente (sin Docker) en el PC de Samuel / EstudiantesJC.
- **Arranque automático:** Task Scheduler (`Iniciar n8n ROFE`) corre `iniciar_n8n.bat` al iniciar sesión — sin intervención manual. Registrado sin `RunLevel Highest` (no requiere admin).
- **Arranque manual:** doble clic en `iniciar_n8n.bat` — equivalente, útil si el PC no fue reiniciado.
- Decisión Docker/servidor dedicado: pendiente para cuando la estabilidad 24/7 sea crítica.

## Trigger dual: Schedule + Telegram

Patrón establecido en `q10-consolidacion`, reutilizable en cualquier proceso:

- **Schedule Trigger** (`n8n-nodes-base.scheduleTrigger`, typeVersion 1.2): actualización automática silenciosa. Los errores quedan en el log de ejecuciones de n8n.
- **Telegram Trigger**: actualización on-demand con respuesta confirmando el resultado.
- Los dos caminos son **paralelos e independientes** en el workflow — comparten los mismos scripts pero no se cruzan. Evita referencias a `$('Parsear Comando').json.chat_id` que fallarían en ejecuciones sin chat.
- Si se quiere notificación Telegram también en el schedule: añadir un chat_id de admin fijo en un nodo Set al inicio del camino schedule.

## Editar workflows n8n por API (sin abrir la UI)

Patrón usado para integrar pasos nuevos al workflow de producción (`PUT /api/v1/workflows/{id}`,
credencial en memoria `reference-n8n-api-key`). Reglas aprendidas (2026-07-07 y 2026-07-08):

- El body del PUT solo acepta `name`, `nodes`, `connections`, `settings` — construirlo desde el
  GET previo. Tras el PUT verificar que el workflow siga **activo** (a veces queda inactivo).
- **El JS de los nodos (Telegram/Code) guarda emoji, tildes y flechas como escapes literales
  `\uXXXX`** — no como caracteres. Para editar expresiones por script: usar anclas 100% ASCII
  y construir los escapes con `chr(92)`, nunca pegar el emoji/tilde real.
- Si se inserta un nodo antes de otro que usa `$json`, esas referencias cambian de fuente —
  reemplazarlas por `$('Nombre Del Nodo')` explícito.
- Al terminar: re-exportar el JSON a `n8n-workflows/` (checklist de CLAUDE.md).
- **Verificar contra el workflow EN VIVO (`GET /workflows/{id}`), no solo el JSON exportado.**
  El JSON en `n8n-workflows/` puede desalinearse si un cambio se documentó pero nunca se aplicó
  con el PUT real, o si se editó por API sin re-exportar después (encontrado 2026-07-21:
  `sync_emoflow.py` seguía corriendo en producción pese a que la doc decía que se había
  reemplazado por `sync_emoflow_api.py` el día anterior — el cambio nunca llegó al workflow real).
- **Nunca tipear texto con tildes/¿/ñ directo en un comando PowerShell hacia la API de n8n.**
  Encontrado 2026-07-21: al escribir `¿Normalización OK?` (y otros) literal en un `-Command` de
  PowerShell, la propia consola/parser mutiló los caracteres no-ASCII a `?` **en el dato real
  enviado**, no solo en la pantalla — y la verificación posterior también se hizo mirando
  consola (igual de mutilada), así que pareció "solo visual" y pasó desapercibido varias horas.
  **Fix:** para cualquier payload con acentos, usar un script Python puntual con
  `urllib.request` + `json.dumps(..., ensure_ascii=False)` / lectura de archivo en UTF-8 — Python
  maneja el encoding de forma explícita y no depende de la codepage de la consola. Verificar
  siempre guardando la respuesta a un archivo y leyéndola con una herramienta de lectura de
  archivos, nunca confiando en lo que se ve impreso en la terminal de PowerShell.
- **Gotcha de PowerShell — `ConvertTo-Json` colapsa arrays de un solo elemento a escalar.**
  `connections.<nodo>.main` de n8n espera `[[ {node...} ]]` (array de ramas, cada rama un array
  de conexiones) — si una rama tiene un solo output, `@(@{...})` se aplana y n8n responde
  `"object is not iterable"` al hacer PUT. **Fix:** forzar el array con el operador coma unario:
  `main = ,@(@{ node='X'; type='main'; index=0 })` en vez de `main = @(@(@{...}))`. Con dos ramas
  (nodo `IF`) el `@(@(...), @(...))` normal sí funciona porque el array externo ya tiene 2
  elementos y no colapsa — el problema es específico de arrays de longitud 1.

## Exclusión de usuarios de prueba en exporters

Q10 tiene perfiles de prueba matriculados como estudiantes reales ("Jovenes Prueba",
"Pruebas Estudiantes JC", "Pruebas Soporte IT", "Mujeres Prueba") que inflan cohortes,
KPIs y hasta retirados. La lista canónica vive en **`tools/exclusiones_prueba.json`**
(gitignoreado — contiene cédulas/emails):

```json
{ "perfiles": [ { "nombre": "...", "cedula": "...", "email": "..." } ] }
```

- Todo exporter que produzca JSON público debe cargarla y filtrar **antes de agregar**
  (por cédula normalizada a solo dígitos; en fuentes con email, también por email).
- Si el archivo no existe o es ilegible → advertir y no excluir nada (no romper el pipeline).
- Aplicada en `export_aprobacion.py`, `export_stats.py`, `export_retirados.py` (2026-07-08).
- Si aparece un perfil de prueba nuevo, agregarlo al JSON — no hardcodear en los scripts.

## Handoff de datos con PII entre exporters (tools/ gitignoreado)

Cuando un exporter necesita un conjunto autoritativo que otro ya calculó (y que contiene
PII, así que no puede ir al JSON público), el productor lo **persiste en `tools/`** y el
consumidor lo lee, en vez de re-consultar la fuente lenta (Q10).

- Ejemplo: `export_aprobacion.py` escribe `tools/cohorte_2026.json` (cohorte y retirados
  únicos por programa, con cédulas) al final de su corrida; `export_retirados.py` lo lee para
  filtrar la pestaña Retirados a 2026 sin re-loguear en Q10 (2026-07-09).
- El productor debe correr **antes** que el consumidor (ya es el orden en el workflow n8n:
  `export_aprobacion` → … → `export_retirados` corre antes, pero el archivo persiste entre
  corridas, así que usa la cohorte de la corrida anterior — aceptable, cambia poco en 4 h).
- El consumidor **degrada con gracia** si el archivo falta o es ilegible (advertir + camino
  alterno), nunca romper el pipeline.
- El archivo lleva `_nota` recordando que es PII y que `tools/` está gitignoreado.

## ⚠️ Supabase: una VISTA con PII se expone a `anon` aunque nunca le des GRANT

**Regla: toda vista o tabla nueva con PII necesita `REVOKE` EXPLÍCITO de `anon`. No basta con
"no dar GRANT".** Y la verificación se hace **con el anon key**, nunca con SQL de admin.

Dos mecanismos se combinan y el resultado sorprende:

1. Supabase concede `SELECT` a `anon` **por defecto** en el schema `public` (privilegios por
   defecto del rol). Crear un objeto ya lo deja legible.
2. Una **vista corre con los privilegios de su DUEÑO**, no del que consulta → **ignora el RLS**
   de las tablas que consulta. (Es la otra cara del gotcha ya conocido de `participa_en()`.)

Resultado real (incidente 2026-07-14): `emoflow_ingresos` es una tabla **con RLS** y devolvía
**0 filas** a anon — todo bien. Pero `v_puntaje_estudiante`, una **vista sobre ella**, devolvía
los **777 nombres + correos** a cualquiera con el anon key… que es **público**: va compilado
dentro del bundle de Netlify. Se detectó el mismo día que se creó. En el mismo barrido apareció
`asistencia_promedio` con una policy `allow_read` permisiva que exponía **490 correos**.

```sql
-- Al crear cualquier objeto con PII:
revoke all on public.<objeto> from anon, authenticated;
```

**Chequeo obligatorio** (el mismo que destapó la fuga) — pegarle a PostgREST con el `anon key` y
exigir 0 filas / 401:

```
GET /rest/v1/<objeto>?select=nombre,email&limit=100   con apikey = SUPABASE_ANON_KEY
```

Corolario: el panel público **solo** consume vistas de agregados (`v_emoflow_*`, `v_curso_*`, …).
Los datos por persona salen por script con `service_role` a `tools/` (gitignoreado), nunca por la
cara pública. Ver [[panel-datos-etl]].

**Seguimiento 2026-07-23 — la regla no se había aplicado a todo lo antiguo.** Un barrido de anon
key sobre las 24 tablas de `public` (a raíz de crear `postulantes_mr`/`postulantes_jc` con
`REVOKE` desde el día uno) encontró que `participants`, `emoflow_ingresos`, `email_optout`,
`email_bounces` y `participants_snapshots` **nunca tuvieron el `REVOKE`** — solo "RLS sin
policy" (deniega filas por defecto, pero sin la red de seguridad del `REVOKE`). Cero filas
expuestas hoy, pero a una policy permisiva de distancia de repetir el incidente. Aplicado el
`REVOKE` a las 5. **Moraleja: el checklist de "tabla/vista PII nueva" no cubre las tablas
viejas — vale la pena repetir el barrido completo de vez en cuando, no solo al crear algo.**

**Gotcha nuevo: revocar el GRANT de una tabla puede romper silenciamente las RLS policies de
OTRAS tablas que le hacen subquery.** Al revocar `participants`, las policies públicas
`enrollments_publico_lectura` y `metrics_publico_lectura` (pensadas para exponer datos de
participantes con `is_public=true`) dejaron de poder evaluar su propio `USING (participant_id
IN (SELECT id FROM participants WHERE is_public = true))` — de "0 filas silenciosamente" pasó a
error 401 real (`permission denied for table participants`), aunque el 100% de esas dos tablas
seguían sin depender de ningún row real hoy (`is_public=true` = 0 casos). Fix: función
`SECURITY DEFINER` (`es_publico(p_id uuid)`, mismo patrón ya aceptado de `participa_en()`) que
las policies llaman en vez de tocar `participants` directo. **Antes de un `REVOKE` amplio,
buscar en `pg_policies` (`qual`/`with_check`) cualquier policy de OTRA tabla que mencione la
tabla a revocar.**

## La pestaña "Seguimiento" es fuente esencial de la DB, no un dato secundario "porque es un Excel"

Decisión de Samuel (2026-07-23), de cara a la futura plataforma que automatice la recolección
y administración de estos datos: **la pestaña `Seguimiento` del Sheet BD Seguimiento de
Monitorias JC debe tratarse como fuente de verdad de primer nivel, al mismo rango que Q10** —
no como un respaldo manual de segunda categoría solo porque vive en una hoja de cálculo.

**Evidencia que respalda esto (mismo día):** al construir `en_seguimiento_jc` (presencia en
esa pestaña) y compararlo contra el pipeline oficial de Q10 una vez sincronizado
correctamente, los números casi coinciden exacto — **759 (Seguimiento) vs. 760
(Q10-`aprobacion_cursos` fresco)**, una diferencia de 1 persona sobre 777. La pestaña, operada
a mano por el equipo, resultó ser tan confiable como el pipeline automatizado de Q10 — y en el
momento en que se comparó, más ACTUALIZADA que la foto que tenía Supabase (`cohorte_ingresos`
llevaba desde las 9:45 sin resincronizar contra una corrida más fresca de las 12:04).

**Implicación para cualquier plataforma nueva:** al diseñar la automatización de recolección,
`Seguimiento` no debe quedar como un import manual ocasional — necesita el mismo tratamiento
de primera clase que Q10 (sync programado, monitoreo de frescura, alertas si deja de
actualizarse). Ver [[supabase-estructura]] para el detalle completo de `en_seguimiento_jc`,
`v_retiro_probable_jc` y el hallazgo del 2026-07-23.

## Heurística de etapa con el ledger de avances

Para "¿en qué punto de la ruta perdimos a un estudiante?" cuando **no hay una fecha fiable**:
usar `tools/aprobacion_ledger.json` (máximo avance por estudiante×curso). La etapa = último
curso de la ruta (en orden cronológico, const `RUTA_2026`) con avance ≥ 100. Es una heurística
de **secuencia**, no temporal: infiere el progreso alcanzado, no cuándo dejó de estudiar.
Documentarlo así en la UI para no sobre-prometer precisión. Usado en `export_retirados.py`
(`etapa_de_retiro`) y el funnel del Tab Tendencia (2026-07-09).

## Supabase `participants` = solo matriculados en Q10 (nunca crear desde fuentes secundarias)

`participants` es la tabla central de Supabase y alimenta ~15 vistas agregadas
(`cohorte_ingresos`, `v_programa_stats`, `v_cohorte_estudiantes`, etc.) que asumen que **cada
fila tiene una matrícula real** en Q10. Regla repetida y deliberada en todo el proyecto: Q10 es
la única fuente de verdad de "quién existe". Por eso ningún script secundario crea filas nuevas
ahí — solo enriquece las que ya existen:

- `sync_emoflow_api.py`: correos de Emoflow sin match quedan con `participant_id = NULL`, no
  crean `participants`.
- `sync_sociodemograficos_mr.py`: mujeres de la BD-Mujeres ROFÉ sin matrícula MR en Q10 se
  reportan (`sin_match_supabase`), no se cargan.

**Si una fuente nueva trae un universo más grande que "matriculados"** (ej. postulantes,
candidatas, leads de un formulario), no forzarla dentro de `participants` — crear una tabla
paralela con `participant_id uuid NULL FK` como puente opcional. Meter esos registros en
`participants` infla/rompe los agregados canónicos (ej. "Ingresados 832") sin ningún beneficio,
porque las vistas que los consumen no distinguen "matriculado" de "solo postulante". Ver
[[postulantes-mr-supabase]] para el primer caso real de este patrón (universo Sheet
BD-Mujeres ROFÉ: 5.126 postulantes vs 282 matriculadas en Supabase).

## Gotcha recurrente: cédula float → string agrega un cero espurio

Cuando una cédula viene de una fuente que la guarda como número (Excel/openpyxl con
`1041774123.0`, o BSON/Mongo con `documentNumber` como `double` — ej. `11086478896.0`),
convertir directo con `str(valor)` dado un float dejar `.0` al final; el strip de caracteres
no-dígitos (`re.sub(r"\D", "", ...)`) borra el punto pero **conserva el `0` de la parte
decimal**, agregando un cero espurio a la cédula real. Patrón correcto, usarlo en TODO
`norm_id()` nuevo:

```python
def norm_id(valor) -> str:
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    return re.sub(r"\D", "", str(valor or ""))
```

Encontrado y corregido 3 veces en el mismo proyecto (`sync_sociodemograficos_mr.py` original;
`extraer_mongo_jc_historico.py`, 2026-07-22 — 3 personas reales con cédula corrompida ya
cargada en `postulantes_jc`, detectado por un chequeo de "longitud atípica" y corregido con
`DELETE` + re-extracción; `extraer_mongo_mr_historico.py`, mismo día, defensivo — ese Mongo
sí guarda `documentNumber` como string, verificado, pero no cuesta nada el guard). **Cualquier
fuente que entregue IDs numéricos (Mongo, Excel, APIs con tipos JSON laxos) necesita este
guard — no asumir que el campo ya viene como texto.**

## Paginación PostgREST: un `offset` que no avanza es un loop infinito silencioso

Patrón `Supa.get_todo()` (usado por `sync_sociodemograficos_mr.py`, `sync_postulantes_mr.py`
y similares): pagina con `limit`/`offset` hasta que `len(lote) < page`. Si el `offset += page`
se omite por error, el loop vuelve a pedir `offset=0` para siempre — cada request individual
responde rápido (<1s) así que **no hay ninguna excepción ni timeout que lo delate**: se ve
exactamente igual que un cuelgue de red intermitente (encontrado 2026-07-22, costó ~30 min de
diagnóstico sospechando el proxy corporativo MITM antes de aislarlo con logging por iteración).
El RSS crece sin límite porque `filas.extend(lote)` acumula duplicados indefinidamente.
**Si un script con este patrón "se cuelga" sin traceback: loggear el `offset` en cada vuelta
antes de sospechar de la red.**

**Reincidencia el mismo día (2026-07-22, `cargar_mongo_mr_historico.py`):** el mismo bug volvió a
aparecer al escribir un `Supa.get_todo()` nuevo desde memoria en vez de copiar el existente —
esta vez llevó a sospechar (~20 min, incorrectamente) un conflicto entre `pymongo` y
`urllib`/`truststore` corriendo en el mismo proceso, antes de aislarlo con el mismo truco de
loggear el `offset`. Ver [[panel-datos-etl#Exploración de MongoDB]]. **Regla reforzada: nunca
reescribir `Supa`/`get_todo` de memoria — copiar el de un script existente (`sync_postulantes_mr.py`
es la versión de referencia) o factorizarlo a un módulo común.**

## Nunca slicear una lista grande (`items[i+1:]`) dentro de su propio loop externo

Cualquier comparación por pares sobre una lista de tamaño n (ej. detección de duplicados)
tentada a escribir `for i, x in enumerate(items): for y in items[i+1:]: ...` — esa slice se
recrea en cada vuelta del loop externo, O(n²) en tiempo **y** memoria transitoria (no solo el
número de comparaciones). Con ~5.300 filas esto llegó a 2 GB de RSS (`sync_postulantes_mr.py`,
2026-07-22) antes de reemplazarse por **bloqueo**: agrupar candidatos por una llave barata que
comparta al menos una señal real (mismo correo/celular exacto, mismo conjunto de tokens de
nombre, vecindad numérica si la lista está ordenada) y solo aplicar la comparación cara dentro
de cada bloque pequeño. Iterar con índices (`range(i+1, len(items))`) en vez de slicear evita
al menos la explosión de memoria, pero el bloqueo es la solución real de fondo.

## Detección de typos de cédula por señales cruzadas (≥2 de correo/celular/nombre)

Cuando la llave de cruce (cédula) puede tener errores de digitación y no hay otro ID único
confiable: una sola señal compartida (ej. mismo celular) NO basta para declarar "misma persona,
cédula con typo" — puede ser coincidencia familiar. Exigir **≥2 señales** (correo, celular,
nombre, cédula parecida) antes de tratarlo como duplicado. Implementado en
`scripts/mr-actualizacion-datos/actualizar_bd_mr.py` (`senales_match()`,
`clasificar_sin_match()`) para el intake del formulario MR; reutilizable en cualquier proceso
que deba conciliar identidades entre fuentes con cédula potencialmente mal digitada (ver
[[postulantes-mr-supabase]]).

## Campañas de correo: reenvío al mismo grupo en días distintos → un ID por día

`enviar_campana.py --enviar` (scripts/mujeres-rofe-correos/) usa `enviados_<ID>.csv` para saltar
correos ya `OK` de ese ID — es lo que permite reanudar un envío cortado. Pero eso mismo hace que
un recordatorio diario a las MISMAS personas con el mismo ID no envíe nada del 2º día en
adelante (0 pendientes). Solución: un `ID` de campaña distinto por día (`evento_dia1`,
`evento_dia2`, ...), cada uno con su propia copia de `lista_<ID>.csv`. Detalle y caso real en
`scripts/mujeres-rofe-correos/README.md` (sección Gotcha) — campaña `encuentro_bogota_2026_*`
(2026-07-22).
