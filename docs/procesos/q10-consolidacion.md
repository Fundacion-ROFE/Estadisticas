# Consolidación Q10

**Estado:** Completado
**Última actualización:** 2026-07-21
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

**Timezone (desde 2026-07-08):** el workflow tiene `settings.timezone = America/Bogota` y el bat exporta
`GENERIC_TIMEZONE=America/Bogota`. Sin esto n8n usa America/New_York y el ciclo de 4 h corre a
horas corridas respecto a Colombia. El grid del Schedule 4h en Bogotá: 0:00, 4:00, 8:00, 12:00,
16:00, 20:00. n8n **no recupera** disparos perdidos mientras estuvo apagado.

| Comando Telegram | Qué hace |
|---|---|
| `/Actualizar Q10` | Pipeline completo: Q10 → H1Test → organizar → h2test → GitHub Pages |

Para agregar nuevos grupos: editar `MAPEO_GRUPOS`, `MAPEO_SHEET_IDS` en `q10_to_sheets.py`.

## Flujo resumido

**Fase 1 — Extracción Q10 → H1Test** (`q10_to_sheets.py --grupo h1test`):

1. Login Q10 multi-paso (7 solicitudes AJAX encadenadas — ver [[convenciones#Q10 Login multi-paso]])
2. **Autodescubrir periodos del año en curso**: sondear `RANGO_PERIODOS` (18–40), leer la columna `Período` de cada uno y conservar solo los del `AÑO_OBJETIVO` → GET Excel → DataFrame por periodo (ver [[convenciones#Autodescubrimiento de periodos por año]])
3. Concatenar los DataFrames del año → `df_consolidado` (el Consolidado ya incluye ID, nombre, celular, email del estudiante)
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
20. `export_retirados.py`: agrega por tipo/causa/programa/mes → `docs/retirados/data.json` (sin PII) → git push → panel `docs/retirados/index.html`. **Depende de `tools/cohorte_2026.json` + `tools/aprobacion_ledger.json` que genera la Fase 5** → en el workflow corre DESPUÉS de `export_aprobacion` (ver nota de orden abajo).

**Fase 5 — Aprobación (2026-07-07, ledger 2026-07-08):** `export_aprobacion.py` loguea directo en
Q10, cruza 3 reportes por cédula (cohorte completa incl. inhabilitados) → `docs/aprobacion/data.json`
→ git push → panel público de aprobación. Como Q10 inhabilita todas las matrículas del estudiante
(y su avance desaparece del Consolidado), un **ledger local** (`tools/aprobacion_ledger.json`, PII,
keepMax por estudiante×curso, sembrado desde la hoja manual con `tools/seed_ledger_avance.py`)
clasifica a cada inhabilitado en "aprobó y se retiró" (4° segmento azul en los paneles) o "se retiró
sin aprobar" — el % aprobó ya no castiga cursos que el estudiante ganó antes de inhabilitarse.
Ver detalle en [[mapa-codigo#export_aprobacion.py]].

**Fase 6 — Toma Sin Completar (2026-07-08, histórico + semáforo + balance 2026-07-21):**
`tools/exportar_sin_completar.py` cruza h2test (avance < 100, solo JC) × BD Seguimiento de
Monitorias (Grupo = ciudad) por cédula → Sheet privado `SinCompletar` con bloques horizontales
por ciudad (cursos apilados dentro), para gestión con el encargado de cada ciudad. Desde
2026-07-21 la misma corrida también actualiza tres pestañas más:
- `Historico` — snapshot semanal de esa cohorte, marca de agua por semana ISO.
- `Semaforo` — contraste semana pasada vs. actual **por estudiante**: verde 100% / amarillo
  45-99.9% / rojo <45%, más columna de tendencia con el Δ%. Útil para identificar A QUIÉN
  contactar.
- `Balance` — panel de resumen **ciudad × materia** (sin individuo), conteo de sin-completar
  semana pasada vs. actual con semáforo de tendencia por celda, más una 3ª columna **% avance
  promedio** por Supabase (no de las Sheets — ver Gotcha en mapa-codigo.md) y una tabla resumen
  por ciudad al final. Pensado para que cada monitor de ciudad lea el estado en segundos —
  reemplaza en función a la pestaña manual `Balace` que ya llevaba el equipo (validado: coinciden
  los números de la semana actual).

La ubicación (ciudad/Grupo) se resuelve contra el Sheet vivo `BD Seguimiento de Monitorias`
(pestaña `Seguimiento` como hub, con fallback a las 9 pestañas por ciudad del mismo Sheet para
quien el monitor aún no sincronizó al hub) — ya no depende de ningún xlsx local.

Ver [[mapa-codigo#tools/exportar_sin_completar.py (local, gitignoreado)]].

Ambas fases corren al final de las dos ramas del workflow (Schedule 4h y comando Telegram).

**Orden de ejecución real en el workflow (corregido 2026-07-09):** aunque las fases están numeradas
Retirados (4) antes de Aprobación (5), en el workflow `export_aprobacion` corre **ANTES** de
`export_retirados` porque este último consume `cohorte_2026.json` y `aprobacion_ledger.json` que
aquél genera. Cadena real: `q10 retirados → retirados_headless → export_aprobacion → export_retirados
→ export_sin_completar`. Antes iban al revés y el panel de retirados usaba la cohorte del ciclo
anterior (atraso de 4h). `export_aprobacion` loguea directo en Q10 (no depende de la pestaña
Retirados), por eso puede ir primero.

**Verificado en vivo (2026-07-21):** `GET /api/v1/workflows/Rblg81qifVshsRae` confirma el workflow
`active: true` y la cadena de nodos real bajo `Schedule 4h` termina en
`Ejecutar export_retirados → Ejecutar export_sin_completar → Responder OK` (mismo orden en la rama
`Sched:` que corre por Telegram). `exportar_sin_completar.py` sigue corriendo cada 4h, sin cambios
desde 2026-07-08 — no quedó huérfano ni desconectado. Ver [[feedback-verificar-n8n-en-vivo]].

**Tiempo estimado total (`/actualizar h2test`):** ~4-5 minutos.

## Fuentes de datos / APIs usadas

Q10 no es una API pública — son endpoints internos de la webapp (`site6.q10.com`):

| Endpoint | Método | Devuelve |
|---|---|---|
| `/Reportes/Excel/ExcelReporte/EducacionVirtual/ConsolidadoEducacionVirtual` | POST | ID estudiante, Nombres, Apellidos, Celular, Email, Nombre asignatura, Porcentaje progreso |
| `/Reportes/Excel/ExcelReporte/GestionAcademica/EstudiantesCancelados` | POST | Nombre completo, Tipo documento, Nº identificación, Teléfono, Programa, Sede, Fecha cancelación, Causa, Descripción, Tipo (Cancelado/Desertor/Aplazado). **Sin Email ni Curso.** Payload: `Tipo=...ServicioReporteEstudiantesCancelados`, `sedeJornada`, `programa`, `rangoFechas.InitialDate/FinalDate` (vacíos = todo el histórico) |

Devuelve `{"url": "https://q10storage.blob.core.windows.net/...xlsx?..."}` — URL de Azure Blob que **expira en ~3 min**. Descargar inmediatamente.

Periodos 2026 con datos (verificado 2026-07-05): `20` (Desarrollo-Nivel 3), `21` (Logica-Nivel 2), `22` (Habilidades-Nivel 1), `23` (Unico MR), `24` (Desarrollo-Avanzado). Los IDs `18`/`19` son **2025** (se descartan por año); `25`–`40` devuelven `not_results`. **Corrección:** la versión previa de esta nota afirmaba que `20` y `24` daban `not_results` — es falso: contienen el curso **Desarrollo Web Front-End - HTML** (502 + 275 = 777 estudiantes, cédulas disjuntas). El endpoint `/Estudiantes` ya no se usa — el Consolidado contiene toda la información del estudiante.

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
- **Desertores excluidos de TODAS las estadísticas (2026-07-09).** Los retiros `Tipo=Desertor` (causa "Decisión de la Institución") son estudiantes que la institución retiró — no son resultados genuinos del programa. Se tratan igual que los perfiles de prueba: se eliminan de cohorte, activos, retirados y ledger (no solo se dejan de contar como retirados). Implementado en `export_aprobacion.py` con `TIPOS_RETIRO_EXCLUIDOS = {"desertor"}` unido a `cargar_exclusiones()` antes de `aplicar_exclusiones()`. Como es la fuente de verdad (escribe `cohorte_2026.json`), el efecto propaga solo a los dos paneles (aprobación y retirados). Efecto verificado 2026-07-09: cohorte JC 857→832, retirados únicos 82→57 (55 cancelados + 2 sin registro); identidad `832 = 775 activos + 57 retirados`. Para excluir otro tipo a futuro, agregarlo al set (minúsculas).

## Gotchas / Limitaciones conocidas

- **Login NO es un simple POST.** Son 7 AJAX encadenados. Ver [[convenciones#Q10 Login multi-paso]].
- **SSL corporativo.** Ver [[convenciones#SSL corporativo]] — aplica a Python y a n8n.
- **URLs Azure Blob expiran en ~3 min.** Descargar inmediatamente tras recibir la URL.
- **No hay lista fija de periodos (desde 2026-07-05).** El script autodescubre por año: sondea `RANGO_PERIODOS` (18–40) y conserva solo los del `AÑO_OBJETIVO`. Si Q10 crea IDs > 40, ampliar `RANGO_PERIODOS`. Un curso/cohorte nuevo del año entra solo; años previos (ej. 2025: IDs 18, 19) se descartan automáticamente para no duplicar.
- **El año lo da la columna `Período`** (`Logica-Nivel 2-2026` → `2026`), no el ID. Los IDs NO están agrupados por año de forma contigua (18/19 = 2025, pero 20 = 2026).
- **Cuidado con "bajar todos los periodos con datos".** Sería incorrecto: mezclaría 2025 con 2026 y duplicaría estudiantes de Lógica/Habilidades. El filtro por año es obligatorio.
- **Dedup debe ser por Email, no Identificacion.** El mismo estudiante tiene `Codigo de matricula` diferente en cada período, pero siempre el mismo email.
- **`ws_h2.clear()` vs `values_clear("A1:Z1000")`.** h2test tiene 9 bloques × 8 cols = 72 cols, y el bloque SIN CURSO puede tener 3400+ filas. El rango Z1000 solo cubre 26 cols × 1000 filas — datos viejos más allá de esos límites persisten y corrompen export_stats. Usar siempre `ws_h2.clear()`.
- **Token del bot de Telegram estuvo expuesto** en un chat de desarrollo. Regenerar con BotFather antes de uso en producción real.
- **`wmic` colgado en Windows 11.** `iniciar_n8n.bat` usaba `wmic process` para matar el n8n anterior — en Windows 11 `wmic` está deprecated y puede colgar indefinidamente. Reemplazado por `Get-CimInstance Win32_Process` vía PowerShell (2026-06-26). Síntoma: bat imprime [2/4] y no avanza.
- **WEBHOOK_URL se inyecta al arrancar n8n.** Desde 2026-07-07 es fija (`https://ergonomic-absinthe-refract.ngrok-free.dev`, hardcodeada en `iniciar_n8n.bat`), así que ya no hay rotación de URL. Sigue aplicando: si n8n arranca sin esa variable (p. ej. `n8n start` a mano), el registro del webhook con Telegram queda mal — siempre reiniciar con el bat completo.
- **Workflow quedó inactivo tras PUT de actualización.** Al actualizar el workflow vía API con el workflow activo se producía error; se desactivó, se actualizó, pero no se reactivó. El bat ya tiene loop que detecta esto y reactiva solo. Verificar con `GET /api/v1/workflows/Rblg81qifVshsRae` si se sospecha inactividad.
- **Si se agregan columnas propias a H1Test o h2test** a la derecha de las columnas propias, la lógica borrar-y-resubir las destruiría.
- **Nombre de pestaña h2test es minúsculas intencional.** Así está creada en Google Sheets. No cambiar a `H2Test` ni en el código ni en Sheets — rompería la conexión. `H1Test` usa CamelCase porque se creó primero con ese nombre; son convenciones distintas por origen histórico.
- **El reporte Estudiantes cancelados NO trae Email ni Curso** — solo identificación, teléfono y datos del retiro. No se puede cruzar por email con h2test/Avance (el cruce estándar del proyecto). El análisis de retirados es sobre sus propios campos (tipo, causa, fecha, programa).
- **El Consolidado no tiene columna de estado de matrícula** — verificado 2026-07-02 con `archivado=true/false`: mismas filas y columnas. Los retirados solo existen en el reporte `EstudiantesCancelados`.
- **Dos `/actualizar` simultáneos chocan en Q10 (HTTP 444).** Visto 2026-07-07: dos personas pidieron `/actualizar Q10` con 35 s de diferencia; ambas ejecuciones entraron a Q10 con la misma cuenta y Q10 cortó la segunda con `444 Client Error` al descargar el Consolidado. La primera ejecución completa sin problema — el fallo de la duplicada es inofensivo, no hay que reintentar. Mitigación pendiente: candado anti-concurrencia en el workflow (ver Pendientes).
- **Corridas programadas pueden fallar en la madrugada** con "The server closed the connection unexpectedly" (vistas 03:00 y 07:00 del 2026-07-07; la de 23:00 pasó bien). Posible red inestable o mantenimiento de Q10. Si se vuelve patrón, investigar; una falla aislada se autocorrige en el siguiente ciclo de 4 h.
- **Una fórmula manual en H1Test tumbó todo el pipeline (2026-07-08).** Alguien puso un `FILTRAR(...)` en `J1` de H1Test; quedó en `#NAME?` y dejó H1/I1 como encabezados vacíos duplicados → `get_all_records()` lanza `GSpreadException` en el organizador y **nada de lo que sigue corre** (dashboard congelado, el q10_to_sheets previo sí pasa). Fix doble: (a) fórmula removida de J1 (guardada en la bitácora), (b) lectura tolerante `leer_registros()` que ignora columnas con encabezado vacío/duplicado, aplicada en `organizador_headless.py`, `retirados_headless.py`, `export_retirados.py` y `organizador_Q10.py` (el `.exe` de operadores necesita rebuild para heredar el fix). Regla para humanos: fórmulas de análisis van en una pestaña aparte, nunca en las pestañas del pipeline.
- **Excluir cédulas de la cohorte exige rebaselinar `maximos.json` (2026-07-09).** La marca de agua (`aplicar_maximos`) guarda el máximo histórico de `cursaron` por curso y **nunca decae**: si el `cursaron` vivo baja respecto al máximo, el déficit se re-suma como retirados (`deficit_cursaron > 0 → c["retirados"] += deficit`). Al excluir desertores la cohorte baja (857→832), así que el watermark viejo (857) los **resucitaría como retirados** anulando la exclusión. Fix: resetear en `maximos.json` las entradas de los cursos afectados (solo JC — los desertores son todos de Jóvenes creaTIvos; las 2 entradas de Mujeres ROFÉ se conservan) para que la corrida las regenere sobre la cohorte nueva. Mismo patrón que usó el fix fantasma revertido. Aplica a cualquier exclusión futura que reduzca la cohorte.
- **Crash OOM del Execute Command deja el Schedule Trigger sin re-registrarse, con el workflow igual `active: true` (2026-07-22).** El 2026-07-18 05:00 la ejecución del Schedule 4h crasheó en el nodo `Sched: q10_to_sheets` con `NodeCrashedError` / "Workflow did not finish, possible out-of-memory issue" (n8n, no el script Python — el mismo `q10_to_sheets.py` corrió perfecto por terminal después). Tras el crash, el workflow **no volvió a dispararse ni una sola vez en 4 días** (verificado con `GET /executions?workflowId=...`: última ejecución 2026-07-18, ninguna hasta 2026-07-22) aunque `GET /workflows/{id}` seguía devolviendo `active: true` — el bug es que el proceso de n8n sigue vivo (otros workflows del mismo n8n sí ejecutaron con normalidad en esos días) pero el Schedule Trigger de *este* workflow queda huérfano internamente sin desactivar el workflow, así que la mitigación existente del bat (que solo reactiva workflows que aparecen `inactive` al arrancar n8n) no lo detecta. **Fix aplicado:** `POST /workflows/{id}/deactivate` + `POST /workflows/{id}/activate` por API fuerza el re-registro del cron y resolvió el problema; luego se corrió manualmente toda la cadena (`q10_to_sheets --grupo h1test` → `organizador_headless` → `export_stats`/`export_avance` → `export_aprobacion` → `q10_to_sheets --grupo retirados` → `retirados_headless` → `export_retirados` → `exportar_sin_completar`) para ponerse al día de inmediato. **Detección recomendada a futuro:** no basta con `GET /workflows/{id}` (siempre mostrará `active: true`); hay que revisar `GET /executions?workflowId=...&limit=5` y comparar `startedAt` del más reciente contra la hora actual — si pasaron más de ~4-8h sin ejecución nueva con el Schedule activo, el trigger quedó huérfano y toca el ciclo deactivate/activate. Ver [[feedback-verificar-n8n-en-vivo]].
- **Los Schedule Triggers corrían en timezone de New York.** Sin `GENERIC_TIMEZONE` ni `settings.timezone`, n8n interpreta las horas en America/New_York. Corregido 2026-07-08: timezone `America/Bogota` en ambos workflows (vía API) + `GENERIC_TIMEZONE` en `iniciar_n8n.bat` (aplica al reiniciar). Ver [[convenciones]].

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
| `export_aprobacion.py` | `scripts/q10-consolidacion/` | Fase 5 — 3 reportes Q10 → `docs/aprobacion/data.json` → git push |
| `exportar_sin_completar.py` | `tools/` (gitignoreado) | Fase 6 — h2test × BD Seguimiento → Sheet privado SinCompletar (por ciudad) |
| `setup_headers.py` | `scripts/q10-consolidacion/` | Escribe headers fila 1 en H1Test/h2test (uso único) |
| `requirements.txt` | `scripts/q10-consolidacion/` | Dependencias Python |
| `q10-consolidacion.json` | `n8n-workflows/` | Workflow n8n (ID en producción: `Rblg81qifVshsRae`) |
| `credenciales_service_account.json` | `scripts/q10-consolidacion/` | NO subir a git |
| `.env` | `scripts/q10-consolidacion/` | `TELEGRAM_BOT_TOKEN`, `N8N_API_KEY` — NO subir a git |
| `docs/dashboard/index.html` | `docs/dashboard/` | Sitio GitHub Pages — Tab 1 (Stats Q10) |
| `docs/dashboard/data.json` | `docs/dashboard/` | Generado por `export_stats.py` — no editar a mano |

**Para reiniciar el sistema:** doble clic en `iniciar_n8n.bat` (en el PC de Samuel). ngrok (dominio fijo) + n8n activos en ~45 segundos.

## Pendiente / Próximos pasos

### Par fantasma "inhabilitados sin cancelación" — decisión pendiente (2026-07-09)
Dos estudiantes JC 2026 — **Samuel Murcia (1034662377)** y **Vicenzo Vecchio (58464721)** —
están inhabilitados en Q10 **sin cancelación formal** y con el programa prácticamente completo
(avance > 80 hasta el curso 6 de la ruta; etapa de retiro 6). Caen como `sin_registro_hoja`
(2) dentro de los retirados: ni activos-en-progreso ni desertores reales.

- **Hoy (sin aplicar):** cuentan como retirados → cohorte 832 = 775 activos + 57 retirados (55 cancelados + **2 fantasma**).
- **Fix listo, NO aplicado:** descartarlos vía `tools/exclusiones_prueba.json` (motivo=normalizado) + rebaselinar `maximos.json` → retirados 57→55, cohorte 832→830, identidad `830 = 775 + 55`. Es lo que hacía el commit revertido `7936664`.
- **Bloqueo:** falta que la coordinación confirme si **siguen activos** (Q10 los reactiva) o si **se retiraron definitivamente**. Según la respuesta se aplica el fix o se dejan como cancelados normales. No aplicar hasta esa confirmación.

### Setup h2test — completado (2026-06-24)
- [x] Service Account con acceso de Editor al Sheet de h2test (`1q4VNn4ltqVEMsOjo-c2ZbsbW3VIt-XomPgXeLSN_LTs`)
- [x] Headers fila 1 escritos en h2test: `python setup_headers.py --pestaña h2test --confirmar`
- [x] h2test operativa: se actualiza vía `/Actualizar Q10` — datos subiendo correctamente
- [x] Schedule **4h** agregado al workflow (2026-06-25) — actualización automática sin intervención
- [x] Task Scheduler configurado (2026-06-25) — n8n arranca al iniciar sesión de EstudiantesJC
- [ ] Regenerar token del bot con BotFather (estaba expuesto — hacer antes de prod real).
  Nota 2026-07-07: el `.env` ya quedó sincronizado con el token vigente de la credencial de n8n
  (daba 401 por desactualizado); al regenerar, actualizar credencial n8n + `.env` + reactivar workflow.
- [ ] Candado anti-concurrencia en el workflow: si ya hay una ejecución de q10_to_sheets en curso,
  responder "ya hay una actualización corriendo" en vez de lanzar una segunda sesión contra Q10
  (choca con HTTP 444 — ver Gotchas 2026-07-07)

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
