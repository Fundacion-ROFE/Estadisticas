# Consolidación Q10

**Estado:** Completado
**Última actualización:** 2026-06-24
**Procesos relacionados:** —

## Qué hace

Extrae automáticamente los datos de estudiantes y progreso de cursos desde la API interna de Q10, hace un JOIN por email y sube el resultado crudo (una fila por estudiante × curso) a Google Sheets. Dos pestañas operativas:

- **H1Test** — revisión interna del equipo, fórmulas/filtros en el mismo Sheet.
- **h2test** — fuente para visualización externa en Looker Studio (datastudio.google.com).

Se ejecuta vía bot de Telegram (`/actualizar <grupo>`) desde n8n corriendo en el PC de Samuel.

## Disparador (Trigger)

Bot de Telegram — comando `/actualizar <grupo>`. El equipo decide cuándo ejecutar.
No hay Schedule; la actualización es manual/bajo demanda.

Grupos disponibles: `h1test` (revisión interna), `h2test` (fuente Power BI). Para agregar nuevos grupos: editar `MAPEO_GRUPOS`, `MAPEO_SHEET_IDS` en `q10_to_sheets.py` y `SHEET_IDS_POR_PESTANA`, `HEADERS_POR_PESTANA` en `setup_headers.py`.

## Flujo resumido

1. Login Q10 multi-paso (7 solicitudes AJAX encadenadas — ver [[convenciones#Q10 Login multi-paso]])
2. POST endpoint Estudiantes → URL Azure Blob → GET Excel inmediato → `df_estudiantes` (4,559 registros)
3. POST endpoint Consolidado para cada periodo `[21, 22, 23, 1]` → GET Excel → DataFrame por periodo
4. Concatenar periodos → `df_consolidado` (5,402 filas)
5. LEFT JOIN por email (`df_estudiantes.Correo ↔ df_consolidado.Email`) → 8,818 filas
6. Renombrar y ordenar columnas: `Identificacion, Nombre, Celular, Email, Curso, Avance`
7. Limpiar H1Test desde fila 2 (sin tocar fila 1) y subir en lotes de 500 con pausa 1.2s
8. Imprimir línea parseable `RESUMEN: grupo=h1test filas=8818 estado=exito` → n8n la extrae para responder por Telegram

**Tiempo estimado de ejecución:** ~1.5 a 2 minutos.

## Fuentes de datos / APIs usadas

Q10 no es una API pública — son endpoints internos de la webapp (`site6.q10.com`):

| Endpoint | Método | Devuelve |
|---|---|---|
| `/Reportes/Excel/Comunidad/Estudiantes` | POST | Código de matrícula, Nombre, Email, Celular |
| `/Reportes/Excel/ExcelReporte/EducacionVirtual/ConsolidadoEducacionVirtual` | POST | Nombre asignatura, Porcentaje progreso |

Ambos devuelven `{"url": "https://q10storage.blob.core.windows.net/...xlsx?..."}` — URL de Azure Blob que **expira en ~3 min**. Descargar inmediatamente.

Periodos con datos confirmados: `21, 22, 23`. Periodo `1` incluido sin garantía. Periodo `20` siempre `not_results` (omitido).

## Destino de los datos

| Grupo (bot) | Sheet ID | Pestaña | Uso |
|---|---|---|---|
| `h1test` | `1d3S41J9nlVI3qCy-WF_D3ZezTwRCW17vnL7u284XDG0` | `H1Test` | Revisión interna del equipo |
| `h2test` | `1q4VNn4ltqVEMsOjo-c2ZbsbW3VIt-XomPgXeLSN_LTs` | `h2test` | Fuente para Power BI |

- **Service Account:** `q10-automatizacion@n8n-automatizacion-q10.iam.gserviceaccount.com`
- **Columnas (A→F, ambas pestañas):** `Identificacion | Nombre | Celular | Email | Curso | Avance`
- **Fila 1:** Headers — escribir con `setup_headers.py --pestaña <nombre> --confirmar`
- **Desde fila 2:** datos crudos, una fila por estudiante × curso

## Decisiones de diseño clave

- **JOIN por Email, no por código.** El Consolidado no exporta el Código de matrícula.
- **LEFT JOIN intencional.** Estudiantes sin cursos aparecen con Curso/Avance vacíos — significa matriculado en Q10 sin actividad virtual, o email no coincide entre sistemas.
- **Datos crudos, sin agrupación.** Una fila por estudiante × curso. El equipo reorganiza con fórmulas en Sheets.
- **Borrar-y-resubir, no actualización por clave.** Válido mientras H1Test tenga solo las 6 columnas propias. Si el equipo agrega columnas a la derecha (fórmulas, notas), migrar a actualización por clave.
- **Script parametrizable `--grupo`.** Escalable a nuevas pestañas sin código nuevo.
- **Trigger Telegram, no Schedule.** El equipo controla cuándo actualizar.

## Gotchas / Limitaciones conocidas

- **Login NO es un simple POST.** Son 7 AJAX encadenados. Ver [[convenciones#Q10 Login multi-paso]].
- **SSL corporativo.** Ver [[convenciones#SSL corporativo]] — aplica a Python y a n8n.
- **URLs Azure Blob expiran en ~3 min.** Descargar inmediatamente tras recibir la URL.
- **Periodo 20 siempre vacío.** Q10 devuelve `not_results` — se omite sin error.
- **Token del bot de Telegram estuvo expuesto** en un chat de desarrollo. Regenerar con BotFather antes de uso en producción real.
- **Si se agregan columnas propias a H1Test o h2test** a la derecha de F, la lógica borrar-y-resubir las destruiría.
- **Nombre de pestaña h2test es minúsculas intencional.** Así está creada en Google Sheets. No cambiar a `H2Test` ni en el código ni en Sheets — rompería la conexión. `H1Test` usa CamelCase porque se creó primero con ese nombre; son convenciones distintas por origen histórico.

## Reglas de Anomalías

El equipo clasifica los registros bajo 4 categorías tras la carga:

| Categoría | Condición | Causa esperada |
|---|---|---|
| **SIN CURSO** | Columna Curso vacía | Estudiante registrado pero sin matrícula en ningún curso virtual |
| **AVANCE 0%** | Curso presente, Avance = 0 | Matriculado pero nunca abrió el contenido |
| **EMAIL SIN MATCH** | Email de Estudiantes sin correspondencia en Consolidado | Typo o email alternativo entre sistemas |
| **AVANCE IRREGULAR** | Avance > 100% | Error de sincronización de progreso en Q10 (registra hasta 101%) |

## Archivos del proceso

| Archivo | Ubicación | Descripción |
|---|---|---|
| `q10_to_sheets.py` | `scripts/q10-consolidacion/` | Script principal — acepta `--grupo` |
| `export_stats.py` | `scripts/q10-consolidacion/` | Lee pestaña `estadísticas` → genera `docs/dashboard/data.json` |
| `setup_headers.py` | `scripts/q10-consolidacion/` | Escribe headers fila 1 (uso único) |
| `requirements.txt` | `scripts/q10-consolidacion/` | Dependencias Python |
| `q10-consolidacion.json` | `n8n-workflows/` | Workflow n8n (ID en producción: `Rblg81qifVshsRae`) |
| `credenciales_service_account.json` | `scripts/q10-consolidacion/` | NO subir a git |
| `.env` | `scripts/q10-consolidacion/` | `TELEGRAM_BOT_TOKEN`, `N8N_API_KEY` — NO subir a git |
| `docs/dashboard/index.html` | `docs/dashboard/` | Sitio GitHub Pages (diseño pendiente con 21.dev) |
| `docs/dashboard/data.json` | `docs/dashboard/` | Generado por `export_stats.py` — no editar a mano |

**Para reiniciar el sistema:** doble clic en `iniciar_n8n.bat` (en el PC de Samuel). cloudflared + n8n activos en ~45 segundos.

## Pendiente / Próximos pasos

### Setup h2test — completado (2026-06-24)
- [x] Service Account con acceso de Editor al Sheet de h2test (`1q4VNn4ltqVEMsOjo-c2ZbsbW3VIt-XomPgXeLSN_LTs`)
- [x] Headers fila 1 escritos en h2test: `python setup_headers.py --pestaña h2test --confirmar`
- [x] h2test operativa: se actualiza vía `/actualizar h2test` — datos subiendo correctamente
- [ ] Regenerar token del bot con BotFather (estaba expuesto — hacer antes de prod real)

### Conexión h2test → Dashboard web

El flujo es: Q10 → h2test (Google Sheets) → JSON estático → GitHub Pages.

**Por qué este approach:**
- Las credenciales nunca salen del PC de Samuel (Service Account solo se usa localmente)
- El JSON publicado contiene solo datos agregados (sin nombres, emails ni cédulas)
- GitHub versiona el historial de actualizaciones del JSON gratis
- El sitio no depende de cuentas Google para verse

**Flujo de actualización:**
1. `/actualizar h2test` en Telegram → actualiza la pestaña `h2test` en Sheets
2. `python export_stats.py` → lee h2test directamente → agrega en Python → genera `data.json`
3. `git commit + push` → GitHub Pages publica automáticamente el JSON actualizado

**Contenido del dashboard:**
- Tabla POR CURSO: Curso, Estudiantes, Promedio %, Mín %, Máx %
- Scorecards ANOMALÍAS: SIN MATCH, AVANCE 0%, AVANCE IRREGULAR

**Decisión técnica clave — lectura directa de h2test:**
`export_stats.py` lee la pestaña `h2test` (datos crudos, 8,818 filas) y computa todas las
estadísticas en Python. No depende de una pestaña `estadísticas` intermediaria con fórmulas
en Sheets. Más robusto: una sola fuente de verdad, sin setup manual en Sheets.

**Nota sobre SIN MATCH:** agrupa filas con Curso vacío que resultan del LEFT JOIN.
Incluye tanto "sin matrícula virtual" como "email sin correspondencia" — son
indistinguibles en h2test. Número esperado: ~3,415.

**Setup GitHub Pages (una vez):**
1. Ir a Settings → Pages del repositorio en GitHub
2. Source: Deploy from a branch → main → /docs
3. Guardar → sitio en `https://<usuario>.github.io/<repo>/dashboard/`

**Estado:** Completado (2026-06-24) — `export_stats.py` y `index.html` funcionales.

### Escalabilidad futura
- [ ] Agregar nuevas pestañas/grupos: editar `MAPEO_GRUPOS` + `MAPEO_SHEET_IDS` en `q10_to_sheets.py` y `SHEET_IDS_POR_PESTANA` + `HEADERS_POR_PESTANA` en `setup_headers.py`
