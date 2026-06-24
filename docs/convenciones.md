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
| Zoom (Server-to-Server OAuth)   | zoom-asistencia   | Scopes: pendiente confirmar                                         |

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

**Tunnel externo:** usar `cloudflared` (Cloudflare Tunnel) en vez de ngrok. ngrok falla con `x509: certificate signed by unknown authority` porque el proxy intercepta su TLS. cloudflared usa QUIC/UDP, bypasea el proxy HTTP.

```
cloudflared tunnel --url http://localhost:5678 --no-autoupdate
```

## Q10 Login multi-paso

Q10 NO tiene un endpoint único de login. El flujo son **7 solicitudes AJAX encadenadas**:
resolución de subdominio → institución → rol → 2FA/verificación → confirmación de sesión.

Usar `requests.Session()` durante toda la cadena. Ya implementado en `scripts/q10-consolidacion/q10_to_sheets.py`. No reescribir desde cero.

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

## Subida a Google Sheets (estándar)

Patrón establecido en q10-consolidacion, reutilizable en otros procesos:
- Lotes de 500 filas con pausa de 1.2s entre lotes (respeta cuota de la API).
- Borrar desde fila 2 antes de subir — nunca tocar fila 1 (headers).
- Todo a string antes de subir (`df.astype(str)`).
- Columna faltante → advertir en consola, no crashear.

## Patrones de integración con Workspace
*(se documentan aquí decisiones que aplican a cualquier proceso que use Calendar/Sheets,
para no redescubrirlas cada vez)*
- Pendiente: documentar cómo se resuelve el Meeting ID/link desde un evento de Calendar
  una vez que el proceso de Zoom lo resuelva — es candidato a reutilizarse en Meet.

## Decisiones de infraestructura
- n8n 2.8.4 corre directamente (sin Docker) en el PC de Samuel / EstudiantesJC.
- Arranque: `iniciar_n8n.bat` en el PC de Samuel — levanta cloudflared + n8n, captura la URL del tunnel automáticamente.
- Decisión Docker/servidor dedicado: pendiente para cuando la estabilidad 24/7 sea crítica.
