# Consolidación Q10

**Estado:** Completado
**Última actualización:** 2026-06-24
**Procesos relacionados:** [[dashboard-web]]

## Qué hace

Extrae automáticamente los datos de estudiantes y progreso de cursos desde la API interna de Q10, hace un JOIN por email y sube el resultado crudo (una fila por estudiante × curso) a Google Sheets. Dos pestañas operativas:

- **H1Test** — revisión interna del equipo, fórmulas/filtros en el mismo Sheet.
- **h2test** — fuente para el dashboard en GitHub Pages (via `export_stats.py`).

Se ejecuta vía bot de Telegram (`/actualizar h2test`) desde n8n corriendo en el PC de Samuel.

## Disparador (Trigger)

Dos triggers en paralelo — ver patrón en [[convenciones#Trigger dual: Schedule + Telegram]].

| Trigger | Cuándo corre | Notifica |
|---|---|---|
| **Schedule 4h** | Automático cada 4 horas (si n8n está corriendo) | No — errores visibles en log de n8n |
| **Telegram `/Actualizar Q10`** | On-demand por el equipo | Sí — respuesta con resumen en el chat |

n8n arranca automáticamente al iniciar sesión en el PC de Samuel (Task Scheduler → `iniciar_n8n.bat`).

| Comando Telegram | Qué hace |
|---|---|
| `/Actualizar Q10` | Pipeline completo: Q10 → H1Test → organizar → h2test → GitHub Pages |

Para agregar nuevos grupos: editar `MAPEO_GRUPOS`, `MAPEO_SHEET_IDS` en `q10_to_sheets.py`.

## Flujo resumido

**Fase 1 — Extracción Q10 → H1Test** (`q10_to_sheets.py --grupo h1test`):

1. Login Q10 multi-paso (7 solicitudes AJAX encadenadas — ver [[convenciones#Q10 Login multi-paso]])
2. POST endpoint Consolidado para cada periodo `[21, 22, 23]` → GET Excel → DataFrame por periodo
3. Concatenar los 3 DataFrames → `df_consolidado` (el Consolidado ya incluye ID, nombre, celular, email del estudiante)
4. `mapear_columnas()`: extrae `Número identificación estudiante`, `Nombres/Apellidos estudiante`, `Celular`, `Email`, `Nombre asignatura`, `Porcentaje progreso` → formato H1Test
5. Columnas finales: `Identificacion, Nombre, Celular, Email, Curso, Avance, Estado` (Estado="A" siempre — `archivado=false` filtra inactivos)
6. Limpiar H1Test desde fila 2 y subir en lotes de 500 con pausa 1.2s
7. Imprimir `RESUMEN: grupo=h1test filas=N estado=exito`

**Fase 2 — Organizar H1Test → h2test** (`organizador_headless.py`): *(solo para `/actualizar h2test`)*

10. Leer H1Test (formato plano: una fila por estudiante × curso)
11. Deduplicar por `(Email, Curso)` keepMax(Avance) — el mismo estudiante tiene diferente Identificacion entre períodos, pero siempre el mismo Email
12. Eliminar filas `Curso=''` de emails que también tienen Curso real (histórico + 2026 en mismo Sheet)
13. Detectar cursos, ordenar estudiantes por Nombre dentro de cada curso
14. Construir bloques horizontales: 6 cols por curso (`Identificacion, Nombre, Celular, Email, Avance, Estado`) + 2 cols separador
15. Limpiar h2test completo con `ws_h2.clear()` antes de escribir (CRÍTICO: `values_clear("A1:Z1000")` solo cubre 26 cols × 1000 filas — insuficiente para 72+ cols × 3400+ filas)
16. Escribir h2test (fila 1 = nombres de cursos, fila 2 = sub-headers, filas 3+ = datos)
17. Calcular y escribir pestaña Observaciones (SIN MATCH, SIN CURSO, AVANCE 0%, AVANCE IRREGULAR, NO HABILITADO)
18. Calcular y escribir pestaña Estadisticas (resumen por curso + totales + total_habilitados)

**Fase 3 — Publicar al dashboard** (`export_stats.py` + `export_avance.py`): *(solo para `/actualizar h2test`)*

16. `export_stats.py`: lee h2test → agrega en Python → escribe `docs/dashboard/data.json` → git push
17. `export_avance.py`: lee pestaña Avance (Sheet manual) → agrega → escribe `docs/avance/data.json` → git push

**Fase 4 — Retirados (2026-07-02):** mismo patrón crudo → organizado → publicado:

18. `q10_to_sheets.py --grupo retirados`: reporte `Estudiantes cancelados` (GestionAcademica) → pestaña `Retirados` (Sheet de h2test). Incluye los 3 tipos: Cancelado, Desertor, Aplazado. Histórico completo (sin filtro de fechas).
19. `organizador/retirados_headless.py`: Retirados → `Retirados-complete` (bloques horizontales por Tipo + bloque RESUMEN).
20. `export_retirados.py`: agrega por tipo/causa/programa/mes → `docs/retirados/data.json` (sin PII) → git push → panel `docs/retirados/index.html`.

**Tiempo estimado total (`/actualizar h2test`):** ~4-5 minutos.

## Fuentes de datos / APIs usadas

Q10 no es una API pública — son endpoints internos de la webapp (`site6.q10.com`):

| Endpoint | Método | Devuelve |
|---|---|---|
| `/Reportes/Excel/ExcelReporte/EducacionVirtual/ConsolidadoEducacionVirtual` | POST | ID estudiante, Nombres, Apellidos, Celular, Email, Nombre asignatura, Porcentaje progreso |
| `/Reportes/Excel/ExcelReporte/GestionAcademica/EstudiantesCancelados` | POST | Nombre completo, Tipo documento, Nº identificación, Teléfono, Programa, Sede, Fecha cancelación, Causa, Descripción, Tipo (Cancelado/Desertor/Aplazado). **Sin Email ni Curso.** Payload: `Tipo=...ServicioReporteEstudiantesCancelados`, `sedeJornada`, `programa`, `rangoFechas.InitialDate/FinalDate` (vacíos = todo el histórico) |

Devuelve `{"url": "https://q10storage.blob.core.windows.net/...xlsx?..."}` — URL de Azure Blob que **expira en ~3 min**. Descargar inmediatamente.

Periodos con datos confirmados: `21` (Logica-Nivel 2-2026), `22` (Habilidades-Nivel 1-2026), `23` (Unico MR-2026). Periodos `20` y `24` siempre `not_results` (omitidos). El endpoint `/Estudiantes` ya no se usa — el Consolidado contiene toda la información del estudiante.

## Destino de los datos

| Grupo (bot) | Sheet ID | Pestaña | Uso |
|---|---|---|---|
| `h1test` | `1d3S41J9nlVI3qCy-WF_D3ZezTwRCW17vnL7u284XDG0` | `H1Test` | Revisión interna del equipo |
| `h2test` | `1q4VNn4ltqVEMsOjo-c2ZbsbW3VIt-XomPgXeLSN_LTs` | `h2test` | Fuente para dashboard GitHub Pages |
| `retirados` | `1q4VNn4ltqVEMsOjo-c2ZbsbW3VIt-XomPgXeLSN_LTs` | `Retirados` (cruda) → `Retirados-complete` (organizada) | Retirados de Q10 (Cancelado/Desertor/Aplazado) → panel público de retirados |

- **Service Account:** `q10-automatizacion@n8n-automatizacion-q10.iam.gserviceaccount.com`
- **Columnas (A→F, ambas pestañas):** `Identificacion | Nombre | Celular | Email | Curso | Avance`
- **Fila 1:** Headers — escribir con `setup_headers.py --pestaña <nombre> --confirmar`
- **Desde fila 2:** datos crudos, una fila por estudiante × curso

## Decisiones de diseño clave

- **Consolidado como única fuente.** El endpoint `/ConsolidadoEducacionVirtual` incluye toda la información del estudiante (ID, nombres, apellidos, celular, email) además del progreso — no se necesita el endpoint `/Estudiantes`. Simplifica el flujo y elimina la fragilidad del LEFT JOIN por email.
- **Sin JOIN.** Al usar solo el Consolidado, cada fila es directamente un registro estudiante × asignatura, sin necesidad de cruzar fuentes.
- **`archivado=false` reemplaza el filtro `Estado=A`.** La exclusión de archivados ocurre en el payload del POST, no en pandas. Estado se fija en "A" en `mapear_columnas()`.
- **Datos crudos, sin agrupación.** Una fila por estudiante × curso. El equipo reorganiza con fórmulas en Sheets.
- **Borrar-y-resubir, no actualización por clave.** Válido mientras H1Test tenga solo las 7 columnas propias. Si el equipo agrega columnas a la derecha (fórmulas, notas), migrar a actualización por clave.
- **Script parametrizable `--grupo`.** Escalable a nuevas pestañas sin código nuevo.
- **Trigger dual Schedule + Telegram.** Schedule para actualizaciones silenciosas; Telegram para forzar on-demand.

## Gotchas / Limitaciones conocidas

- **Login NO es un simple POST.** Son 7 AJAX encadenados. Ver [[convenciones#Q10 Login multi-paso]].
- **SSL corporativo.** Ver [[convenciones#SSL corporativo]] — aplica a Python y a n8n.
- **URLs Azure Blob expiran en ~3 min.** Descargar inmediatamente tras recibir la URL.
- **Periodo 20 siempre vacío.** Q10 devuelve `not_results` — se omite sin error.
- **Periodos 2026 confirmados:** IDs 21 (`Logica-Nivel 2-2026`), 22 (`Habilidades-Nivel 1-2026`), 23 (`Unico MR-2026`). Periodo 1 no tiene datos — no incluir en `PERIODOS`.
- **Dedup debe ser por Email, no Identificacion.** El mismo estudiante tiene `Codigo de matricula` diferente en cada período, pero siempre el mismo email.
- **`ws_h2.clear()` vs `values_clear("A1:Z1000")`.** h2test tiene 9 bloques × 8 cols = 72 cols, y el bloque SIN CURSO puede tener 3400+ filas. El rango Z1000 solo cubre 26 cols × 1000 filas — datos viejos más allá de esos límites persisten y corrompen export_stats. Usar siempre `ws_h2.clear()`.
- **Token del bot de Telegram estuvo expuesto** en un chat de desarrollo. Regenerar con BotFather antes de uso en producción real.
- **`wmic` colgado en Windows 11.** `iniciar_n8n.bat` usaba `wmic process` para matar el n8n anterior — en Windows 11 `wmic` está deprecated y puede colgar indefinidamente. Reemplazado por `Get-CimInstance Win32_Process` vía PowerShell (2026-06-26). Síntoma: bat imprime [2/4] y no avanza.
- **WEBHOOK_URL se inyecta al arrancar n8n.** Si cloudflared se reinicia y genera una URL nueva, n8n debe reiniciarse también para heredarla — de lo contrario el registro del webhook con Telegram falla con "Failed to resolve host". Siempre reiniciar con el bat completo, nunca solo cloudflared.
- **Workflow quedó inactivo tras PUT de actualización.** Al actualizar el workflow vía API con el workflow activo se producía error; se desactivó, se actualizó, pero no se reactivó. El bat ya tiene loop que detecta esto y reactiva solo. Verificar con `GET /api/v1/workflows/Rblg81qifVshsRae` si se sospecha inactividad.
- **Si se agregan columnas propias a H1Test o h2test** a la derecha de las columnas propias, la lógica borrar-y-resubir las destruiría.
- **Nombre de pestaña h2test es minúsculas intencional.** Así está creada en Google Sheets. No cambiar a `H2Test` ni en el código ni en Sheets — rompería la conexión. `H1Test` usa CamelCase porque se creó primero con ese nombre; son convenciones distintas por origen histórico.
- **El reporte Estudiantes cancelados NO trae Email ni Curso** — solo identificación, teléfono y datos del retiro. No se puede cruzar por email con h2test/Avance (el cruce estándar del proyecto). El análisis de retirados es sobre sus propios campos (tipo, causa, fecha, programa).
- **El Consolidado no tiene columna de estado de matrícula** — verificado 2026-07-02 con `archivado=true/false`: mismas filas y columnas. Los retirados solo existen en el reporte `EstudiantesCancelados`.

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
| `q10_to_sheets.py` | `scripts/q10-consolidacion/` | Fase 1 — extracción Q10 → H1Test |
| `organizador_headless.py` | `scripts/q10-consolidacion/organizador/` | Fase 2 — H1Test → h2test + Observaciones + Estadisticas (sin GUI) |
| `organizador_Q10.py` | `scripts/q10-consolidacion/organizador/` | Versión GUI del organizador (revisión manual / .exe) |
| `export_stats.py` | `scripts/q10-consolidacion/` | Fase 3a — h2test → `docs/dashboard/data.json` → git push |
| `export_avance.py` | `scripts/q10-consolidacion/` | Fase 3b — pestaña Avance → `docs/avance/data.json` → git push |
| `retirados_headless.py` | `scripts/q10-consolidacion/organizador/` | Fase 4 — Retirados → Retirados-complete (bloques por Tipo + RESUMEN) |
| `export_retirados.py` | `scripts/q10-consolidacion/` | Fase 4 — Retirados → `docs/retirados/data.json` → git push |
| `setup_headers.py` | `scripts/q10-consolidacion/` | Escribe headers fila 1 en H1Test/h2test (uso único) |
| `requirements.txt` | `scripts/q10-consolidacion/` | Dependencias Python |
| `q10-consolidacion.json` | `n8n-workflows/` | Workflow n8n (ID en producción: `Rblg81qifVshsRae`) |
| `credenciales_service_account.json` | `scripts/q10-consolidacion/` | NO subir a git |
| `.env` | `scripts/q10-consolidacion/` | `TELEGRAM_BOT_TOKEN`, `N8N_API_KEY` — NO subir a git |
| `docs/dashboard/index.html` | `docs/dashboard/` | Sitio GitHub Pages — Tab 1 (Stats Q10) |
| `docs/dashboard/data.json` | `docs/dashboard/` | Generado por `export_stats.py` — no editar a mano |

**Para reiniciar el sistema:** doble clic en `iniciar_n8n.bat` (en el PC de Samuel). cloudflared + n8n activos en ~45 segundos.

## Pendiente / Próximos pasos

### Setup h2test — completado (2026-06-24)
- [x] Service Account con acceso de Editor al Sheet de h2test (`1q4VNn4ltqVEMsOjo-c2ZbsbW3VIt-XomPgXeLSN_LTs`)
- [x] Headers fila 1 escritos en h2test: `python setup_headers.py --pestaña h2test --confirmar`
- [x] h2test operativa: se actualiza vía `/Actualizar Q10` — datos subiendo correctamente
- [x] Schedule **4h** agregado al workflow (2026-06-25) — actualización automática sin intervención
- [x] Task Scheduler configurado (2026-06-25) — n8n arranca al iniciar sesión de EstudiantesJC
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

## Contingencia manual

Si el bot de Telegram falla o n8n no está corriendo:

1. Abrir terminal en el PC de Samuel.
2. Activar el entorno virtual si aplica.
3. Fase 1 — extraer Q10 a H1Test:
   ```bash
   python scripts/q10-consolidacion/q10_to_sheets.py --grupo h1test
   ```
4. Fase 2 — organizar H1Test → h2test (headless):
   ```bash
   python scripts/q10-consolidacion/organizador/organizador_headless.py
   ```
   Alternativa con GUI (si se prefiere revisión visual antes de subir):
   ```bash
   python scripts/q10-consolidacion/organizador/organizador_Q10.py
   ```
5. Fase 3 — publicar al dashboard:
   ```bash
   python scripts/q10-consolidacion/export_stats.py
   python scripts/q10-consolidacion/export_avance.py
   ```
6. Fase 4 — retirados:
   ```bash
   python scripts/q10-consolidacion/q10_to_sheets.py --grupo retirados
   python scripts/q10-consolidacion/organizador/retirados_headless.py
   python scripts/q10-consolidacion/export_retirados.py
   ```
7. Si Q10 da error de login: verificar que credenciales en el script están vigentes y que la red corporativa no bloquea `site6.q10.com`.
8. Si el Sheet no se actualiza: verificar que el Service Account tiene rol Editor en el Sheet destino.

Ver runbook [[q10-actualizar]] para pasos detallados sin terminal (operadores no técnicos).

## Conexiones del sistema

- [[mapa-codigo]] — detalle técnico de `q10_to_sheets.py`, `export_stats.py`, `export_avance.py`
- [[dashboard-web]] — consume la pestaña `h2test` producida por este proceso
- [[convenciones]] — Q10 login multi-paso, SSL corporativo, doble encabezado en Sheets
- Runbook: [q10-actualizar](../../runbooks/q10-actualizar.md)
- Workflow n8n: `n8n-workflows/q10-consolidacion.json` (ID producción: `Rblg81qifVshsRae`)
