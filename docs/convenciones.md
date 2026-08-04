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

### Gotcha: git debe quedar 100% no-interactivo para que n8n no se cuelgue

Un `git push` de un exporter corriendo dentro de un nodo `executeCommand` de n8n que dispara un
prompt de credencial (por ejemplo, cache de credential-manager vencido) **cuelga el nodo para
siempre** — nada lo mata, el workflow nunca termina ni reporta error. Endurecido (Track A, Ola 1,
2026-07-24) con tres capas independientes:

1. `git config --global credential.interactive never` — Git nunca pide credenciales de forma
   interactiva, en ninguna sesión de esta máquina.
2. En `iniciar_n8n.bat`, junto al resto de `set` de entorno: `set GCM_INTERACTIVE=never` y
   `set GIT_TERMINAL_PROMPT=0` — refuerzo a nivel de proceso hijo de n8n (por si algún día corre
   con un `HOME`/perfil distinto al de la sesión interactiva de Samuel, donde la config global no
   aplicaría).
3. `git config --local credential.helper manager` fijado también a nivel de repo (no depender
   solo de la config global, que no está versionada ni es obvia de reproducir en otra máquina).

Con las tres capas, un fallo real de autenticación sale como error inmediato (`git push` retorna
≠0 en segundos) en vez de colgarse — lo que activa el patrón de "fin del éxito silencioso"
(ver `git_commit_y_push()` en cualquier `export_*.py`: `timeout=180` por comando + `return False`
en fallo + `estado=error` + `sys.exit(1)` en `main()`). Probar con
`git push --dry-run origin main` desde una terminal sin sesión de credenciales activa — debe
salir sin prompt.

### Gotcha: `git commit` sin pathspec se lleva todo lo que esté staged, no solo lo tuyo

Pasó el 2026-08-03/04: una sesión de Claude Code dejó `usuarios-ia/` con un `git rm -r`
staged (sin commitear todavía, a propósito, para no pushear contenido sensible a este repo
público). El siguiente `export_supabase_json.py` automático de n8n corrió su `git add
docs/datos` (correctamente acotado) seguido de `git commit -m "..."` **sin pathspec** — y
`git commit` sin pathspec commitea el índice completo, no solo lo que el script acaba de
agregar. Resultado: el `git rm` ajeno viajó pegado al commit automático y se pusheó sin que
nadie lo pidiera, dejando esa carpeta pública ~16h hasta que se notó.

**Todo `git_commit_y_push()` de este proyecto (los 6 `export_*.py` + `commit_y_push.py` en
`comunicaciones-ai/Contexts`) debe pasar `-- <rutas>` al `git commit`, nunca solo `-m
mensaje`:**

```python
["git", "commit", "-m", mensaje, "--", *rutas]   # ✓ acotado, inmune a lo demás staged
["git", "commit", "-m", mensaje]                  # ✗ commitea TODO el índice
```

Aplica a cualquier script nuevo que haga commit automático sobre un repo donde también se
trabaja interactivamente — el índice es compartido, no hay aislamiento entre una sesión de
Claude Code y un cron de n8n corriendo en la misma máquina sobre el mismo working tree.

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

## Gotcha: un script que auto-crea pestañas necesita la SA como Editor, no solo Viewer

Un patrón cada vez más común en el proyecto es que un sync escriba a un Sheet "dedicado" que
él mismo crea/puebla (`add_worksheet` si la pestaña no existe) en vez de exigir que un humano
la prepare a mano de antemano. Ese patrón **falla en silencio de forma engañosa** si la Service
Account (`q10-automatizacion@n8n-automatizacion-q10.iam.gserviceaccount.com`) solo tiene
permiso **Viewer** en el Sheet destino: puede leer, la ejecución no truena en el login, pero el
`add_worksheet`/la escritura revienta con `APIError 403`. Caso real cerrado 2026-07-24:
`sync_supabase_to_sheets.py` apuntaba al Sheet AUTO dedicado
`1eO73hL9Bq_X8T11g3aPAEkq6QkKfMRNykru7to8GDdo` con la SA solo como Viewer — la reescritura de
código del 2026-07-23 (single-tab `AUTO_Emoflow_Uso` autocreada) se dio por resuelta sin
verificar el permiso real, y siguió fallando un día más hasta que se compartió el Sheet como
**Editor**.

**Regla:** cualquier Sheet que un script vaya a crear/escribir pestañas en él (no solo
actualizar celdas de una pestaña ya existente) necesita la SA compartida como **Editor**
explícitamente — Viewer no alcanza, y el error (403 al crear la pestaña) no siempre es obvio
en los logs si el script no lo propaga con detalle. Verificar el permiso ANTES de dar por
cerrada cualquier deuda de "ya está resuelto" que dependa de un Sheet nuevo.

⚠️ Excepción importante en sentido contrario: la BD Seguimiento
(`1ggzoJeZR3fS6AwRCLoGeYA5HEp_B7zvOwFGlGwny0l8`, el Sheet gigante de Avance/Emoflow/H1-H3
viejos) es **destino de escritura PROHIBIDO** para scripts nuevos — es la fuente humana
canónica de varios procesos, no un scratchpad de sync. El fix de 2026-07-24 fue mover el
destino a un Sheet AUTO **dedicado y separado**, no dar más permisos sobre la BD Seguimiento.

## Lectura de Sheets en pipelines (tolerante a fórmulas sueltas)

Nunca usar `get_all_records()` directo en un script de pipeline: exige encabezados únicos y
**una fórmula suelta que un humano ponga en la fila 1** (visto 2026-07-08: `FILTRAR` en
`H1Test!J1` → `#NAME?` → encabezados vacíos duplicados) tumba todo lo que sigue en la cadena.
Usar el patrón `leer_registros(ws)`: `get_all_values()` + conservar solo columnas con encabezado
no vacío y no duplicado (ver `organizador_headless.py`). Regla para humanos: fórmulas de análisis
van en pestañas aparte, nunca en las pestañas que los scripts leen/escriben.

## ✅ Normalización de ciudades (resuelto 2026-07-24)

**Estado:** Resuelto a nivel de base de datos. Ya no es responsabilidad de cada script
reinventar la detección de variantes.

**Cómo se descubrió:** un script ad-hoc (`generar_lista_y_enviar.py`, ya archivado en
`_obsoletos/`) filtraba con `if 'BOGOTA' in ciudad.upper():` — `.upper()` en Python NO
quita tildes, así que `'BOGOTA' in 'BOGOTÁ D.C.'.upper()` da `False`. Resultado: de 512
personas de Bogotá en `postulantes_mr`, el filtro solo encontró 24. Análisis completo en
`claude_sessions.md` (2026-07-24).

**Solución implementada:**

1. **`normalizar_ciudad(text)`** — función SQL `IMMUTABLE` (quita tildes/mayúsculas/
   puntuación: `translate` + `regexp_replace` + `upper`). Ver
   `docs/migrations/013_normalizar_ciudad.sql`.
2. **Columna generada `ciudad_norm`** en `participants`, `postulantes_mr` y
   `postulantes_jc` — `GENERATED ALWAYS AS (normalizar_ciudad(ciudad)) STORED`,
   indexada. Se recalcula sola en cada insert/update, **no requiere backfill ni
   mantenimiento**. Filtrar SIEMPRE por esta columna, nunca por `ciudad` crudo.
3. **Tabla `ciudad_alias`** (`clave_norm` PK -> `ciudad_canonica`) — fusiona nombres
   administrativos distintos del MISMO municipio que `normalizar_ciudad()` no puede
   resolver solo (son palabras distintas, no solo tildes): `BOGOTA DC`/`BGT` -> `BOGOTA`,
   `CARTAGENA DE INDIAS` -> `CARTAGENA`, `CIUDAD DE PANAMA` -> `PANAMA`. Fuente única de
   verdad — agregar filas ahí, no hardcodear el mapeo en cada script.
4. **`scripts/panel-datos/ciudad_utils.py`** (copiar/importar vía `sys.path.insert`,
   patrón ya usado en `importar_historico_q10.py`) — `normalizar_ciudad()` en Python
   (réplica exacta de la función SQL) + `claves_para(ciudad, supa)`, que dada una ciudad
   en lenguaje natural devuelve la lista de `ciudad_norm` a usar en un filtro PostgREST
   `ciudad_norm=in.(...)` (ya incluye la expansión de alias). **Ojo con el REST:** los
   valores de `ciudad_norm` pueden traer espacios (`"BOGOTA DC"`) — hay que
   URL-encodearlos (`Supa.get_todo` en `ciudad_utils.py` ya lo hace).

**Verificado tras aplicar:** `postulantes_mr` con `ciudad_norm IN ('BOGOTA','BOGOTA DC')`
= 508 filas ≈ 504 del Excel "Base Mr Bogotá.xlsx" que se creía que faltaba migrar (no
faltaba — el problema era el filtro, no los datos).

**Ejemplo de uso en un script nuevo:**
```python
sys.path.insert(0, os.path.join(PROYECTO_ROOT, "scripts", "panel-datos"))
from ciudad_utils import Supa, cargar_alias, claves_para

supa = Supa(url, key)
claves = claves_para("Bogotá", supa)          # -> ['BGT', 'BOGOTA', 'BOGOTA DC']
filtro = ",".join(claves)
filas = supa.get_todo(f"/postulantes_mr?ciudad_norm=in.({filtro})&select=*")
```

Referencia de uso real: `scripts/mujeres-rofe-correos/extraer_lista_ciudad_mr.py`
(reemplaza los scripts archivados en `_obsoletos/`).

**Pendiente (menor, no bloqueante):** `extraer_lista_cundinamarca.py` sigue consultando
`participants` (matriculadas) en vez de `postulantes_mr` (universo completo) — su lógica
de "¿qué municipios son Cundinamarca?" es un problema distinto (agrupación por
departamento, no normalización de nombre) y no se tocó en este cierre.

### Auditoría de coherencia de toda la DB (2026-07-24) — qué más se revisó y qué se arregló

Tras el fix de `ciudad`, Samuel pidió revisar el resto de la DB por el mismo tipo de
problema (mismo valor, distinta grafía, dañando análisis en silencio). Resultado:

- **`participants.grupo_ciudad` (código operativo JC — BOG/BAQ/CTG/CAL/MED/GYL/QTO/PAN/UY,
  NO es lo mismo que `ciudad_canonica`, a veces agrupa varias ciudades en un código de
  país/región):** 74% de `participants` sin asignar. **Grave:** `v_demografia_grupo`,
  `v_curso_completion_por_ciudad` y `v_programa_stats_por_ciudad` filtran
  `WHERE grupo_ciudad IS NOT NULL` — sin este campo, el participante desaparece del
  reporte (ni siquiera cae en "SIN_CIUDAD"). Backfill aplicado (`014_backfill_grupo_ciudad.sql`)
  para los 246 casos donde la ciudad ya tenía un código establecido y sin ambigüedad
  (verificado antes de tocar nada: ningún `ciudad_canonica` mapeaba a 2 códigos distintos).
  De las 285 restantes, Samuel confirmó fusionar los municipios satélite/conurbación al
  hub más cercano (`016_grupo_ciudad_municipios_satelite.sql`): Soledad→BAQ,
  Jamundí/Palmira/Yumbo/Candelaria/Dagua→CAL, Bello/Itagüí→MED, Soacha/sabana de
  Bogotá→BOG (+58). Los ~120 municipios restantes sin hub cercano (Santa Marta, Quibdó,
  Villavicencio, Cúcuta, Carmen del Darién, mayoría con 1-3 personas) se unificaron bajo
  `grupo_ciudad = 'OTROS'` (`017_grupo_ciudad_otros.sql`, +222) — decisión explícita para
  que las tomas de datos grandes (dashboards por grupo) no pierdan a esas 222 personas sin
  tener que inventar un código por municipio; `ciudad`/`ciudad_norm` (intactos) siguen
  disponibles si algún día hace falta analizar un municipio puntual. **`grupo_ciudad`
  ahora tiene 3 estados posibles a distinguir en cualquier reporte:** un código de hub real
  (BOG/BAQ/CTG/CAL/MED/GYL/QTO/PAN/UY), `'OTROS'` (municipio conocido, sin hub asignado) o
  `NULL` (sin ciudad registrada en absoluto — 1.621 filas, no es lo mismo que "otros").

### Auditoría "a fondo" con advisors de Supabase (2026-07-24)

Corrida de `mcp__Supabase__get_advisors` (security + performance) + `test_integridad_supabase.py`
(47/47 PASS, sin cambios) + revisión manual. Resultado:

**Corregido (real):**
- `campanas_enviadas` tenía RLS activado pero SIN política — anon obtenía `200` con `[]`
  en vez de `401` (mismo patrón del "incidente 2026-07-14"/2026-07-21, esta tabla se quedó
  fuera de esa pasada). `REVOKE ALL ... FROM anon, authenticated` (`018_torpezas_seguridad_advisors.sql`).
- `search_path` mutable en `normalizar_ciudad`/`ciudad_canonica` (funciones creadas hoy
  mismo, migración 013) — corregido con `SET search_path`.

**Investigado y descartado (falsa alarma, NO tocar):**
- **20 vistas `SECURITY DEFINER` marcadas "ERROR" por el linter** (`v_demografia_grupo`,
  `v_mr_demografia`, `v_curso_completion*`, etc.) — revisadas una por una: todas son
  agregados puros (`COUNT`/`AVG`/`GROUP BY`), ninguna expone `nombre`/`email`/`cedula`/
  `celular` de una persona individual. `SECURITY DEFINER` aquí es necesario (así pueden
  calcular el agregado leyendo filas que RLS le bloquearía a `anon` directamente) y seguro
  (solo el número agregado sale). Coincide con el patrón ya usado en `v_demografia_grupo`
  de suprimir buckets con `< 5` personas. No cambiar a `SECURITY INVOKER` — rompería los
  dashboards públicos.
- **`participa_en(uuid, programa_type)` ejecutable por `anon` vía RPC** — se intentó
  revocar (parecía exceso de permiso) y **rompió en vivo** `v_demografia_grupo`/
  `v_emprendimiento_situacion` para `anon` (401). Revertido en el mismo turno. Lección:
  una vista da acceso "como el dueño" a las TABLAS que usa, pero NO extiende ese acceso a
  las FUNCIONES que llama — el rol que consulta necesita su propio `EXECUTE`, sin importar
  si la función o la vista son `SECURITY DEFINER`. Ver detalle en
  `018_torpezas_seguridad_advisors.sql`.
- **3 tablas "sin primary key"** (`historial_emoflow`, `historial_emoflow_ciudad`,
  `emoflow_participacion_semanal`) — las 3 tienen un índice `UNIQUE` que cumple la misma
  función (el upsert de `sync_emoflow_api.py` depende de él y funciona bien, 0 duplicados
  verificados). El linter solo distingue "primary key" de "unique index" a nivel de
  catálogo; no es un bug real.
- **1 registro de prueba real encontrado:** `participants` tiene "Prueba Carlitos" /
  `prueba1@prueba.com` — parece dato de prueba de desarrollo, no una persona real. No se
  borró (acción destructiva, no es mi decisión) — queda para que Samuel confirme y borre
  si corresponde. Otros correos con "test/prueba/xxx/asdf" en el texto (`leimarxxx7@`,
  `liyenpruebas@`, `yinaasdfd@`) están atados a nombres colombianos reales — son personas
  reales con correos informales, no datos de prueba.

**Reportado, sin tocar (bajo impacto, no urgente):**
- `auth_rls_initplan` (WARN, performance): varias políticas RLS (`admin_full_access_*`)
  re-evalúan `auth.<fn>()`/`current_setting()` por fila en vez de una vez por query
  (patrón `(select auth.<fn>())`). Tablas de bajo volumen de consultas (admin-only) — no
  urgente.
- `multiple_permissive_policies` (WARN, performance): varias tablas tienen 2 políticas
  permisivas para el mismo rol/acción (`admin_full_access_X` + `X_publico`) — funcionalmente
  correcto (se OR-ean), solo evalúa de más. No urgente.
- `unused_index` (INFO): 5 índices sin uso registrado — normal en un proyecto con poco
  volumen de queries todavía, no ameritan borrarse ahora.

### Gotcha: basura en `ciudad` (source_system='q10', sin resolver)

Al backfillear `grupo_ciudad` se encontraron 5 filas donde `ciudad` claramente NO es una
ciudad — parece una respuesta de OTRA pregunta del formulario que quedó mal mapeada a esta
columna: `"hijos"` (x2), `"Menor a 1 SMLV"`, `"Colombia"`, `"Galapa soy una mujer"` (esta
última sí contiene un municipio real, "Galapa" — área de Barranquilla — pero concatenado
con texto de otra respuesta). Las 5 son `source_system='q10'` — el bug está en algún punto
del pipeline Q10 (`normalize_q10_data.py`/`cargar_supabase.py` o el formulario/Sheet fuente
antes de eso), no en la Sheet BD Seguimiento. **No se tocó** — adivinar la ciudad real
(sobre todo en "Galapa soy una mujer") sería inventar dato; quedaron con
`grupo_ciudad = NULL` a propósito (ni "OTROS" ni un código real). Quien toque el pipeline
Q10 debería revisar si hay una columna corrida en el import de origen — candidato a
próximo propietario de esta deuda.
- **`postulantes_mr.estado`:** `'retirada'` (3) vs `'Retirada'` (30) — unificado
  (`015_fix_case_estado_postulantes_mr.sql`).
- **Revisado y limpio, sin cambios:** `emoflow_ingresos` y todas sus tablas/vistas
  derivadas (Emoflow usa un dropdown cerrado de 9 áreas, no texto libre — 0 nulos/variantes);
  `participants.genero`, `postulantes_mr.genero`, `participants.source_system`,
  `postulantes_jc.fuente`/`rol`, `postulantes_mr.fuente_pestana` (vocabularios controlados
  por script de carga, sin fragmentación).

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
- **Gotcha inverso (2026-07-26) — un array de más NO falla al guardar, falla al ejecutar.**
  El error opuesto al anterior: sobre-anidar `conditions` de un `IF`
  (`conditions: [[{…}]]` en vez de `[{…}]`) o `rule.interval` de un Schedule. El PUT responde
  **200 y el workflow queda `active: true`**, así que parece correcto; pero al ejecutarse el IF
  revienta con `Cannot read properties of undefined (reading 'rightType')` — n8n lee el array
  interno como si fuera un objeto condición. Encontrado en `sociodemograficos-semanal`: el IF
  roto cortaba la cadena **antes** de `sync_sociodemograficos_mr.py`, que por eso nunca corrió
  (era su único punto de ejecución) — 44 personas MR sin datos sociodemográficos durante
  semanas, sin ninguna señal de alarma. **Fix:** aplanar con
  `[c for grupo in conds for c in grupo]`. **Regla:** tras crear/editar un workflow por API,
  no basta con verificar `active: true` — hay que mirar la **primera ejecución real**
  (`GET /executions?workflowId=…`) antes de darlo por bueno.
- **Gotcha (2026-07-29) — el nodo `IF` (typeVersion 2.2) rutea la rama `true` al índice 0 de
  `connections.main`, no al índice que "suena" correcto por el orden en que se escriben las
  ramas.** Al clonar `alerta-frescura-vencida` para construir `alerta-choques-cursos`, se copió
  el orden `main: [[OK], [Notificar]]` tal cual estaba en la plantilla, asumiendo que la primera
  rama del array era la que correspondía al caso "todo bien" solo porque se había puesto ahí.
  Prueba empírica (forzar el `IF` a verdadero con datos de test): con ese orden, la condición
  verdadera ("hay alerta") enrutaba a `OK` y la falsa a `Notificar` — **exactamente al revés**
  de la intención. Fix: `main: [[Notificar], [OK]]`. **Regla: el índice 0 SIEMPRE es la rama
  verdadera; no asumir el orden por cómo quedó en un workflow que se está clonando — probarlo
  forzando ambos casos antes de confiar en la plantilla copiada.**
  **Confirmado el mismo día: `alerta-frescura-vencida` (la plantilla original) tenía el mismo
  defecto — 45/45 ejecuciones desde que se activó (2026-07-28) tuvieron `estado=alerta` y las
  45 enrutaron a `OK` en silencio. Nunca llegó una sola alerta real, incluyendo un proceso
  (`asistencia_promedio`, zoom) que llevaba ~4 días vencido. Corregido. Al corregir el `IF`
  aparecieron los otros 2 gotchas de esta misma lista (Markdown/Telegram y `\n` embebido) que
  habían estado dormidos porque el mensaje nunca llegaba a intentarse enviar — moraleja: un bug
  que "cancela" a otro puede esconderlo indefinidamente; al arreglar uno, probar de punta a
  punta antes de dar el conjunto por resuelto.**
- **Gotcha (2026-07-29) — Telegram (parse_mode Markdown, aplicado por default aunque no se
  fije `additionalFields.parseMode` explícito) se come `_`/`[`/`*` del texto sin avisar ni
  fallar.** Un mensaje con `no_visto_en_fuente` llegó como `novistoenfuente` (guiones bajos
  desaparecidos) y con `[tipo]` sin corchetes — sin error, `ok: true`, nada que indicara el
  problema salvo comparar visualmente el texto enviado. Intentar `additionalFields.parseMode:
  "none"` no tuvo efecto (el valor se guarda pero Telegram sigue aplicando Markdown). **Fix
  real:** escapar en el script que arma el mensaje (no en la expresión de n8n) los caracteres
  `_ * \` [` con `\` antes de enviarlos — ver `_md_seguro()` en `check_choques_cursos.py`.
  Cualquier mensaje a Telegram que incluya texto crudo de una fuente (nombre de curso, tipo de
  señal, identificador con guion bajo) necesita este escape.
- **Gotcha (2026-07-29) — construir el JSON de un workflow con un script (Python/PowerShell)
  en vez de escribirlo a mano hace fácil perder la cuenta de capas de escape y violar la regla
  ya documentada de "`\\n` en el JSON, nunca `\n` real" (ver tabla de expresiones n8n arriba).**
  Un `\\n` escrito en el código fuente de un heredoc terminó llegando a n8n como un salto de
  línea real (cada capa — parámetro de herramienta, heredoc, parser de Python, `json.dumps` —
  reduce sin avisar), y el nodo Telegram falló con `invalid syntax` al evaluar la expresión JS.
  **Patrón robusto que evita el problema de raíz (no solo lo parcha): que el script que corre
  en `executeCommand` imprima el mensaje COMPLETO y final por stdout (con sus propios saltos de
  línea reales de Python), y que la expresión de n8n solo referencie
  `$('Nodo').item.json.stdout` sin concatenar ni construir strings con `\n` embebido.** Es el
  mismo patrón que ya usaba `alerta-desercion-semanal` — evitarlo (concatenar en la expresión,
  como se hizo primero en `alerta-choques-cursos`) fue lo que introdujo el bug.
- **Gotcha (2026-07-30) — cambiar el cron de un `Schedule Trigger` por `PUT` en un workflow
  que YA está `active: true` guarda el valor nuevo (se ve correcto en un `GET` posterior) pero
  el trigger en memoria del proceso n8n sigue corriendo con el cron viejo — no dispara en la
  hora nueva.** Encontrado probando `asistencia-zoom-diario` en caliente: se adelantó el cron
  de `45 17 * * *` a un par de minutos en el futuro, el `PUT` respondió 200 y el `GET` mostraba
  el cron nuevo, pero pasó la hora objetivo sin ninguna ejecución nueva en
  `GET /executions`. **Fix:** tras el `PUT`, forzar siempre
  `POST /workflows/{id}/deactivate` → `POST /workflows/{id}/activate` — eso obliga a n8n a
  re-registrar el `Schedule Trigger` con la definición actual. Con eso el disparo llegó exacto
  al segundo. **Patrón útil para probar un workflow con Schedule Trigger sin esperar al tick
  real:** adelantar el cron unos minutos + forzar el ciclo deactivate/activate, confirmar la
  ejecución en `GET /executions` (o por `v_frescura`/tabla destino), y **revertir el cron al
  valor original con el mismo ciclo** en cuanto se confirme — no dejar el cron de prueba puesto.

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

## Auto-sanación: reiniciar n8n al reanudar de suspensión (schtasks ONEVENT)

**Causa raíz de un apagón real (2026-07-24):** el portátil de Samuel se suspendió durante la
ventana de crons nocturnos (17:00–07:30) y n8n dejó de correr sin que nadie se enterara hasta
la mañana siguiente. Forense: el evento `Microsoft-Windows-Power-Troubleshooter` EventID=1
(resume) en el log `System` coincidió con el corte (~03:14 COT).

**Mitigación aplicada:** tarea programada de Windows que dispara `iniciar_n8n.bat` (ruta
absoluta del repo) cada vez que el sistema se reanuda de suspensión. El `.bat` ya mata la
instancia vieja de `n8n.cmd` antes de arrancar una nueva (líneas 67-69), así que el trigger es
idempotente aunque n8n ya estuviera corriendo.

```
schtasks /Create /TN "n8n-auto-heal-resume" ^
  /TR "C:\Users\EstudiantesJC\downloads\admin-usable\iniciar_n8n.bat" ^
  /SC ONEVENT /EC System ^
  /MO "*[System[Provider[@Name='Microsoft-Windows-Power-Troubleshooter'] and EventID=1]]" /F
```

**Gotcha — `/RL HIGHEST` da "Acceso denegado":** requiere una sesión elevada (token de
Administrador sin filtrar por UAC); en una sesión normal `schtasks /Create` con `/SC ONEVENT`
sí funciona SIN `/RL HIGHEST` — solo omitirlo si da acceso denegado, no forzar elevación.

**Gotcha — la tarea no corre en batería por defecto:** `schtasks /Create` deja
"Detener en modo Batería / No iniciar en Batería" activado, justo el escenario que se busca
cubrir (portátil sin cargador). Corregir después de crear la tarea con el módulo
`ScheduledTasks` de PowerShell (no hay flag equivalente en `schtasks.exe`):

```powershell
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
  -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero)
Set-ScheduledTask -TaskName "n8n-auto-heal-resume" -Settings $settings
```

Verificar con `schtasks /Query /TN "n8n-auto-heal-resume" /V /FO LIST`. Ver también
[[migracion-n8n-digitalocean]] — este gotcha es el argumento más fuerte para migrar del portátil
a un servidor: "un portátil a batería no es un servidor", la ventana de crons coincide
exactamente con cuándo un portátil suele suspenderse.

## Consejo de 4 personajes para decisiones (ligero / medio / profundo)

Para evaluar una idea o decisión (no un bug, sino "¿deberíamos hacer esto?") antes de comprometer
tiempo, tres skills en `.claude/skills/` simulan un consejo con 4 roles fijos: 🟢 optimista
(fortalezas), 🔴 escéptico (ataca sin diplomacia — errores, sesgos, supuestos sin validar), 💰
economista (costo/beneficio con números) y ⚖️ juez (sintetiza y decide: adelante / con ajustes /
no adelante). El patrón se repite en 3 niveles según cuánta independencia real necesitan las
voces:

| Nivel | Skill | Aislamiento | Costo | Cuándo |
|---|---|---|---|---|
| Ligero | `/consejo-ligero` | 0 subagentes — todo simulado en un turno | Bajo | Decisiones de bajo riesgo, sanity-check rápido |
| Medio | `/consejo-medio` | 1 subagente real (solo el escéptico, aislado) | Medio | Cuando importa que el ataque no se suavice por haber "sentido" el resto |
| Profundo | `/consejo-profundo` | 3 subagentes en paralelo, aislamiento total | Alto | Decisiones de alto riesgo o difíciles de revertir |

**Por qué el escéptico es el primero en aislarse:** en una simulación de un solo turno, todas las
voces comparten el mismo contexto — el escéptico "ve" el tono optimista recién escrito y tiende a
suavizarse (anclaje). Aislarlo en un subagente sin memoria de la conversación es la forma más
barata de recuperar una crítica genuinamente adversarial antes de pagar el costo de aislar también
al optimista y al economista (nivel profundo, 3 spawns).

Reutilizable para cualquier decisión futura del proyecto (arquitectura, migraciones, alcance de un
proceso nuevo) — no está atado a ningún dominio de datos específico.

## Grupos de filas/columnas colapsables por API de Sheets (`addDimensionGroup`)

Gotchas encontrados construyendo el bloque colapsable por sesión de `validar_asistencia.py`
(ver `docs/procesos/zoom-asistencia.md`, 2026-07-30):

- **Dos grupos hermanos (mismo nivel/depth) que quedan adyacentes sin ninguna fila suelta
  entre ellos se FUSIONAN en un solo grupo grande**, en vez de quedar como 2 cajas
  independientes con su propio `+`/`-`. Fix: dejar siempre al menos 1 fila sin agrupar
  entre 2 grupos consecutivos (en este caso, una fila "divisoria" con el resumen de la
  sesión, que de paso da visibilidad sin abrir el detalle).
- **`addDimensionGroup` para varios grupos en el mismo `batchUpdate` los crea colapsados
  por defecto**, no expandidos como se esperaría. Fix: después de crearlos, mandar una
  segunda tanda de `updateDimensionGroup` (`fields: "collapsed"`, `collapsed: false`) —
  tiene que ir en una llamada `batch_update` aparte, posterior a la que los crea (el grupo
  tiene que existir antes de poder actualizarlo).
- **`deleteDimensionGroup` borra la definición del grupo pero NO vuelve a mostrar las filas
  que quedaron ocultas** si alguien colapsó ese grupo a mano antes de borrarlo — quedan
  ocultas "huérfanas", y el grupo que se cree encima en la siguiente corrida hereda esa
  ocultación. Fix: antes de recrear grupos (o al limpiar los viejos), mandar
  `updateDimensionProperties` (`hiddenByUser: false`) sobre todo el rango relevante.

## Nunca usar `row_count`/`gridProperties` de Google Sheets como proxy de volumen de datos

`worksheet.row_count` (o el `row_count`/`col_count` que trae la metadata del grid) cuenta el
tamaño **formateado** de la hoja, no las filas con datos reales — puede inflar por cientos o
miles de filas vacías. Gotcha real (2026-07-28): se comparó `HerpowerED` (6.677 `row_count`)
contra `General` (5.127 filas reales) y se concluyó que `HerpowerED` tenía "~1.500 filas más" y
una columna exclusiva — ambas conclusiones eran falsas. Al recontar valores reales de la columna
llave (`values_batch_get` + filtrar filas con celda de cédula no vacía), `HerpowerED` resultó
tener 5.109 filas reales, 99.98% solapadas con `General` (la limpieza de la Fase 0 original,
"HerpowerED es copia, se descarta", era correcta desde el principio). **Regla:** para saber
cuántos datos reales tiene una pestaña, siempre contar valores no vacíos en la columna
identificadora (cédula/ID), nunca `row_count`/`gridProperties`.

## Un POST a PostgREST sin `?on_conflict=` no es un upsert — es un insert que falla en silencio

`Prefer: resolution=merge-duplicates` **no alcanza por sí solo**: PostgREST necesita
`?on_conflict=<columna_unique>` en la URL para saber contra qué constraint resolver el
choque. Sin ese parámetro, cada fila que ya existe responde `409 Conflict` — y si el código
captura ese `409` y lo cuenta como "actualizado" (un patrón tentador: "ya existía, entonces
ya está bien"), el resultado es un ETL que **reporta éxito todos los días sin escribir un solo
dato nuevo**. Caso real (`calcular_asistencia_promedio.py`, descubierto 2026-07-29 al auditar
por qué `v_frescura` marcaba `asistencia_promedio` vencido): el script llevaba desde el
**2026-07-25** corriendo diario, imprimiendo "547 registros actualizados", con `except
HTTPError as e: if e.code == 409: actualizados += 1` — cuatro días de "éxito" que en realidad
eran 409 silenciosos. Fix: agregar `?on_conflict=email` (la columna con el `UNIQUE` real,
verificado con `pg_get_constraintdef`) a la URL del POST. **Regla: cualquier upsert nuevo a
PostgREST vía POST se prueba verificando que una columna `actualizado_en`/`updated_at` de una
fila YA EXISTENTE avance de verdad tras correrlo — "el script no truena" no es lo mismo que
"escribió algo".**

## Un ETL que solo hace upsert nunca reconcilia lo que desaparece de la fuente

**La causa raíz más productiva encontrada hasta ahora** (2026-07-29). Todos los `sync_*` y
`cargar_supabase.py` del proyecto insertan y actualizan, pero **ninguno detecta que una fila
dejó de existir en la fuente**. Eso produce cuatro síntomas que parecen problemas distintos y
son el mismo:

| Síntoma observado | Qué era en realidad |
|---|---|
| 17 matrículas "fantasma" en 6 cursos JC, congeladas desde el 23-jul | 17 personas dadas de baja que salieron de h2test; sus filas quedaron |
| Curso duplicado tras un rename (777 matrículas congeladas) | El nombre viejo salió de la fuente; su fila quedó |
| Fila espuria en `aprobacion_cursos` con 66.8% | El nombre viejo salió de `data.json` en un sync anterior; la fila quedó |
| Serie de tiempo bifurcada en `historial_cursos` | Dos nombres del mismo curso conviviendo 6 días |

**Regla:** al auditar coherencia fuente↔Supabase, un conteo que no cuadra casi nunca significa
"falta cargar algo" — con un ETL upsert-only lo más probable es que **sobre** algo que la fuente
ya no tiene. Revisar primero por exceso, no por defecto.

**Regla de comparación:** nunca comparar `count(*)` de una tabla contra el conteo de la fuente
viva. Comparar solo las filas que la fuente confirmó en la última corrida (ver
`visto_en_fuente_at` abajo). Supabase conserva historia a propósito y va a tener más filas que
la fuente — eso no es una discrepancia, y tratarlo como tal genera una falsa alarma en cada
corrida, para siempre.

## Fuente desordenada: sellar "última vez visto", no modelar estados

Cuando la fuente es administrada de forma impredecible, **no modelar su ciclo de vida** — el
modelo va a mentir. Caso real: se propuso agregar `estado activo/cerrado` + `fecha_cierre` a
`courses`, y Lina confirmó que Q10 **no tiene fechas de cierre** y que a veces se permite
seguir actividades en cursos ya terminados. Una columna de estado binario habría sido falsa en
los dos sentidos: un curso "cerrado" puede revivir, y uno "activo" puede llevar semanas muerto.
Evidencia de que ese camino ya se había recorrido mal: `courses.estado` **ya existía**, el ETL
lo escribe hardcodeado como `"activo"` para todo, y el curso MR que sí cerró clases sigue
marcado `activo`. **No usar `courses.estado` para saber si un curso está vigente.**

Patrón que sí funciona (migraciones 026/027):

1. **`visto_en_fuente_at`** en la tabla — la fuente lo refresca en cada corrida para todo lo
   que trae. Es un hecho verificable ("hace 8 días no lo vemos") en vez de una interpretación
   ("cerró"). Si algo revive, revive solo, sin intervención humana ni migración.
2. **Tabla de alias** (`cursos_alias`) — el único punto donde **una persona** confirma que dos
   nombres son la misma cosa. Los ETLs la consultan y absorben el renombre antes de escribir,
   en vez de crear una entidad nueva. Sirve para varias tablas a la vez si se compara
   normalizado (`upper(btrim(...))`): `courses` guarda MAYÚSCULAS y `aprobacion_cursos` guarda
   Title Case, y el mismo alias resuelve las dos.
3. **Vista de vigilancia** (`v_choques_cursos`) — no impide el desorden, avisa cuándo ocurre.
   La señal más barata y confiable de todas: **una métrica monótona que retrocede**. El avance
   de un curso no puede bajar; si baja, hay choque de información, sin falsos positivos
   posibles. Buscar invariantes así en cada dominio nuevo antes de escribir alertas de umbral.
4. **Nada se borra** — lo que sale de una tabla viva va a `datos_archivados` (jsonb + motivo),
   reversible con `jsonb_populate_record`.

**Calibrar los detectores con datos reales, no a ojo.** El umbral de similitud de nombres se
midió antes de fijarlo: el rename real daba 0.854, dos cursos genuinamente distintos daban
0.471, y el umbral inicial de 0.45 habría generado una alerta de severidad alta falsa. Quedó en
0.60. Un detector sin calibrar medida es un generador de ruido que la gente aprende a ignorar.

## Rename o cierre de curso en Q10 = fila duplicada, no un update

Cuando una tabla tiene `UNIQUE(nombre, cohorte)` (o cualquier UNIQUE que dependa de un nombre
que viene de la fuente, no de un ID estable), un rename en la fuente **crea una fila nueva** en
vez de actualizar la existente — el upsert por nombre no tiene forma de saber que
"Desarrollo Web Front-End - HTML - 2026" y "...HTML Y CSS - 2026" son el mismo curso. Gotcha
real (loop de coherencia, 2026-07-29): 777 matrículas JC quedaron congeladas bajo el nombre
viejo del curso cuando Q10 lo renombró entre el 24 y el 29 de julio; mismo síntoma en un curso
MR que dejó de aparecer en la fuente (136 matrículas congeladas), sin evidencia de rename —
posible cierre de periodo. **Cómo detectarlo:** comparar el `updated_at` más reciente de cada
fila contra la corrida de hoy — una fila con `nombre` similar (mismo prefijo, distinto sufijo)
pero `updated_at` de días atrás es la señal. **Regla:** al auditar coherencia de una tabla con
UNIQUE por nombre, siempre revisar `max(updated_at)` agrupado por esa clave, no solo el conteo
total — el conteo total puede cuadrar por casualidad mientras dos filas están fragmentando el
mismo curso real.

## El umbral de una alerta de frescura tiene que ser mayor al hueco de diseño del cron que alimenta el proceso

Encontrado auditando el canal de Telegram (2026-07-30): `v_frescura` marcaba `vencido=true` para
`cohorte_ingresos`/`aprobacion_cursos`/`retiros` todos los días de 13:30 a 17:30, con el pipeline
funcionando perfectamente — `q10-sync-supabase` corre en ventana nocturna
(`30 17,19,21,23,1,3,5,7 * * *`) y el hueco entre la última corrida del día (07:30) y la primera
de la tarde (17:30) es **de diseño**, 10h. Un umbral de 6h < 10h dispara todos los días a la
misma hora — y como la alerta corre cada 30 min, son 8 mensajes falsos diarios que entrenan a la
gente a ignorar el canal. Ya había pasado una vez (migración 021, `emoflow_ingresos_diario`
6h→30h) y volvió a pasar en los 3 procesos que comparten el mismo cron de origen (migración 029,
6h→12h).

**Fórmula:** `umbral > hueco máximo de diseño entre corridas consecutivas + una corrida de
tolerancia` (para detectar una corrida real perdida en un tiempo razonable, no solo evitar el
falso positivo). No sobrecorregir con un umbral gigante "por si acaso" — eso tapa fallas reales
durante toda una ventana (ej. 30h en un proceso que corre 8 veces por noche dejaría pasar una
noche entera sin avisar). Calcular el umbral desde el cron real del proceso que alimenta el
dato, no a ojo.

## `Get-Content -Encoding UTF8` no basta para que un log con acentos/emoji llegue intacto a Telegram

Un `executeCommand` que hace `python script.py > log.txt 2>&1 & powershell ... Get-Content log.txt
-Tail N` puede seguir mutilando caracteres no-ASCII (`•`, `⚠`, tildes, ñ) **incluso con
`-Encoding UTF8` en el `Get-Content`**. Ese flag solo corrige cómo PowerShell 5.1 *lee* el
archivo — pero al reenviar la cadena a stdout para que n8n la capture, PowerShell la
**re-codifica con el codepage de consola/OEM del proceso**, que no sabe representar esos
caracteres. Confirmado con los bytes crudos (2026-07-30): sin el fix completo, un bullet `•`
correctamente leído sale como `0x07` (ni siquiera el mojibake típico de 3 bytes) — la lectura
fue perfecta, la reemisión no.

**Fix completo:** anteponer `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8;` al
`Get-Content` dentro del mismo `-Command` de PowerShell:

```
powershell -NoProfile -Command "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; Get-Content 'ruta/log.txt' -Tail 15 -Encoding UTF8"
```

Aplicado en `alerta-frescura-vencida` y `panel-verificacion-diaria` — los únicos 2 workflows del
proyecto con este patrón. Cualquier workflow nuevo que capture stdout de un script Python vía
archivo + `Get-Content` necesita las dos partes del fix, no solo `-Encoding UTF8`.

## `security_invoker = on` en una vista pública rompe el acceso de `anon` si las tablas base tienen REVOKE de PII

Encontrado construyendo `v_pub_geografia`/`v_pub_cohorte`/`v_pub_avance` (plan-visualizacion,
2026-07-30). `security_invoker=on` hace que la vista corra con los privilegios de quien
**consulta**, no del dueño — es la mitigación correcta para el gotcha ya documentado arriba
("una vista con PII se expone a anon aunque nunca le des GRANT", porque por defecto una vista
corre como su dueño e ignora el RLS/GRANT de las tablas que toca). Pero en este proyecto varias
tablas base (`participants`, `ciudad_alias`, …) tienen **REVOKE ALL explícito de anon** a
propósito, precisamente para proteger PII — y con `security_invoker=on` la vista deja de poder
compensar eso: `anon` necesitaría GRANT directo en esas tablas, que nunca va a tener. Resultado
real: `SET ROLE anon; select * from v_pub_geografia;` → `permission denied for table
participants`. **Regla:** `security_invoker=on` es correcto para vistas de **nivel individuo
consumidas solo por `service_role`** (bypasea RLS/GRANTs de todas formas, así que el flag no
tiene costo y da defensa en profundidad) — nunca para vistas de **agregados públicos** que
necesitan leer tablas con PII protegida por REVOKE. Las vistas públicas de este proyecto usan a
propósito el patrón owner-privilege (sin `security_invoker`), ya aceptado y documentado para
`v_demografia_grupo` y hermanas. **Probarlo siempre con `SET ROLE anon` antes de dar por buena
una vista nueva** — `information_schema.role_table_grants` solo confirma el GRANT sobre la
vista misma, no si la consulta real revienta más abajo.
