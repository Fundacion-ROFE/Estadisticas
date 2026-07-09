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

Requiere agente ngrok **≥ 3.20** y free tier permite **un solo agente** simultáneo. Historial: se usó `cloudflared` (2026-06) porque una versión vieja de ngrok fallaba con `x509` tras el proxy corporativo — con ngrok 3.39.9 ya no ocurre, y cloudflared quedó retirado (2026-07-07) porque su URL efímera rotaba en cada reinicio.

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
credencial en memoria `reference-n8n-api`). Reglas aprendidas (2026-07-07 y 2026-07-08):

- El body del PUT solo acepta `name`, `nodes`, `connections`, `settings` — construirlo desde el
  GET previo. Tras el PUT verificar que el workflow siga **activo** (a veces queda inactivo).
- **El JS de los nodos (Telegram/Code) guarda emoji, tildes y flechas como escapes literales
  `\uXXXX`** — no como caracteres. Para editar expresiones por script: usar anclas 100% ASCII
  y construir los escapes con `chr(92)`, nunca pegar el emoji/tilde real.
- Si se inserta un nodo antes de otro que usa `$json`, esas referencias cambian de fuente —
  reemplazarlas por `$('Nombre Del Nodo')` explícito.
- Al terminar: re-exportar el JSON a `n8n-workflows/` (checklist de CLAUDE.md).

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

## Heurística de etapa con el ledger de avances

Para "¿en qué punto de la ruta perdimos a un estudiante?" cuando **no hay una fecha fiable**:
usar `tools/aprobacion_ledger.json` (máximo avance por estudiante×curso). La etapa = último
curso de la ruta (en orden cronológico, const `RUTA_2026`) con avance ≥ 100. Es una heurística
de **secuencia**, no temporal: infiere el progreso alcanzado, no cuándo dejó de estudiar.
Documentarlo así en la UI para no sobre-prometer precisión. Usado en `export_retirados.py`
(`etapa_de_retiro`) y el funnel del Tab Tendencia (2026-07-09).
