# Auditoría de resiliencia n8n (hosting local) — 2026-08-13

> **Conexiones:** [[00-vision-global]] · [[panel-datos-etl]] · [[migracion-n8n-digitalocean]] ·
> [[supabase-estructura]] · `runbooks/recuperacion-frescura.md` · `iniciar_n8n.bat`
>
> **Motivo:** Samuel pidió cerciorar la solidez de la arquitectura para **~1 mes más de hosting
> local** antes de migrar a la nube. Dos dolores concretos: **(A) "se mueren muy fácil"** y
> **(B) "nos damos cuenta a los días del fallo"**.

---

## 1. Inventario de resiliencia ACTUAL (lo que ya existe y funciona)

| Capa | Mecanismo | Estado verificado 2026-08-13 |
|---|---|---|
| Energía | Suspensión por inactividad **desactivada** (CA y CC = 0/nunca) | ✅ correcto |
| Arranque | Tarea `Iniciar n8n ROFE` (LogonTrigger → `start /min iniciar_n8n.bat`) | ✅ última corrida OK |
| Watchdog interno | Loop del `.bat` cada 60s: healthz + relanza ngrok + reactiva bot | ✅ corriendo (mejorado, ver §4) |
| Auto-heal resume | Tarea `n8n-auto-heal-resume` (evento Power-Troubleshooter Id=1 → .bat) | ⚠️ estaba ROTA (result=1) → **arreglada** §4 |
| Watchdog colgadas | Tarea `n8n-watchdog-ejecuciones-colgadas` cada 15 min (`watchdog_ejecuciones_colgadas.ps1`): detecta ejecución "running" >20 min → reinicia n8n | ✅ corriendo OK (result=0) |
| Concurrencia | `N8N_CONCURRENCY_PRODUCTION_LIMIT=2` + `lock_cli.py` en workflows pesados | ✅ configurado |
| Memoria | `NODE_OPTIONS=--max-old-space-size=2048` | ✅ configurado |
| Alertas (local) | `alerta-frescura-vencida` (30 min), `alerta-fallo-workflow`, `panel-verificacion-diaria`, `alerta-choques-*`, `alerta-desercion-semanal` | ✅ 20/20 workflows activos |
| Alertas (nube) | Rutina Claude `frescura-pipeline-rofe` (8:30 COT, **independiente del portátil**) | ⚠️ NO verificable desde aquí — **confirmar** (§5) |

**Conclusión del inventario:** la arquitectura NO está desnuda — tiene 3 capas de auto-recuperación
(watchdog .bat, auto-heal resume, watchdog colgadas) y una capa de alertas amplia. El problema no es
ausencia de mecanismos, sino **2 puntos ciegos específicos** (§3).

---

## 2. Testing realizado

- **Inventario de workflows en n8n vivo** (API): 20/20 activos.
- **Config de energía** (`powercfg`): suspensión CA/CC = 0.
- **Tareas programadas**: 3 (arranque, auto-heal, watchdog colgadas) — se leyó acción, trigger y última corrida de cada una.
- **Ejecuciones con error** (API): se revisaron las últimas 15 → 2 fuentes reales de fallo (§3).
- **Dispatcher** (`rerun-pipeline`): `ping` → `estado=exito` (camino de re-disparo remoto vivo).
- **healthz**: responde 200.

---

## 3. Hallazgos (ranqueados por impacto)

### 🔴 H1 — El único detector independiente del portátil es la rutina en la nube (dolor B)
**Todas** las alertas locales (`alerta-frescura-vencida`, `alerta-fallo-workflow`, etc.) viven en el
n8n del portátil. Si el portátil se **apaga** (el incidente de 62h de jul fue "portátil apagado", no
suspensión), esas alertas **mueren con él** → nadie se entera hasta que alguien mira el panel. El
único que sobrevive es la rutina Claude en la nube `frescura-pipeline-rofe` (lee `v_frescura` por
curl y avisa por Telegram). **Acción:** confirmar que esa rutina sigue activa y llega a Telegram
(ver §5). Sin ella, el dolor B no tiene solución mientras el hosting sea local.

### 🟠 H2 — `healthz` miente en el estado "vivo pero conexiones muertas" (dolor A)
Tras suspender/despertar, n8n responde `healthz=200` pero sus conexiones (executeCommand, DB) están
muertas → los syncs fallan en silencio. El watchdog del `.bat` (que solo mira `healthz`) **no lo
detecta**. Mitigación existente que SÍ lo cubre: `watchdog_ejecuciones_colgadas.ps1` (cada 15 min,
detecta ejecución colgada >20 min → reinicia). Ventana de detección: ~35 min. Aceptable, pero
depende de que haya una ejecución corriendo para detectarlo.

### 🟠 H3 — `n8n-auto-heal-resume` estaba ROTA (result=1)
La tarea de curación al despertar ejecutaba `iniciar_n8n.bat` **directo** (el .bat tiene un loop
infinito → la tarea se colgaba/mataba → result=1). La de logon sí usa `start /min`. **Arreglado**
(§4). Además, el evento Power-Troubleshooter Id=1 **no siempre se dispara** (documentado: la noche
del 24-jul no saltó) — por eso el watchdog de colgadas (H2) es el respaldo real.

### 🟡 H4 — `q10-sync-supabase` marca "error" por su ÚLTIMO nodo aunque Supabase sí se actualizó — ✅ ARREGLADO
El fallo del 06:30 fue en `sync_supabase_to_sheets.py` (push a la hoja del equipo, último nodo), un
traceback probablemente transitorio de Google Sheets. Como es el último nodo, **no** afecta la
frescura de Supabase (los nodos previos ya escribieron), pero **sí** dispara `alerta-fallo-workflow`
(ruido) y, si el push a Sheets es crónico, conviene aislarlo en su propio workflow con reintento.

### 🟡 H5 — `Zoom - Asistencia` falla recurrente en "Reenviar a Grabaciones" ("Invalid JSON in response body") — ✅ ARREGLADO
~11 errores el 08-12 (webhook). El nodo recibe una respuesta no-JSON. No afecta datos del panel,
pero ensucia el log de errores y puede estar perdiendo reenvíos de grabaciones. Revisar el endpoint
destino / agregar manejo de respuesta no-JSON.

### 🟢 H6 — El watchdog del `.bat` solo re-verifica 1 workflow (el bot)
Los otros 19 persisten activos entre reinicios (n8n los guarda en su DB), así que no necesitan
reactivación explícita; solo los webhook (Telegram/Zoom) se re-registran al arrancar. Impacto bajo.

---

## 4. Fixes aplicados en esta auditoría (2026-08-13)

1. **`n8n-auto-heal-resume` arreglada** (H3): acción cambiada de `iniciar_n8n.bat` (directo) a
   `cmd.exe /c start /min "..." "iniciar_n8n.bat"` (fire-and-forget, patrón del task de logon) →
   completa limpio y realmente reinicia n8n al despertar.
2. **`iniciar_n8n.bat` watchdog ahora AUTO-SANA** (H2/dolor A): antes, si `healthz` fallaba en el
   loop, hacía `pause; exit /b 1` (se rendía y moría el watchdog). Ahora **reinicia n8n solo**
   (kill node → `n8n start` → espera 70s → reactiva bot) y sigue vigilando. Ya no hay que reiniciar
   el script a mano si n8n muere.
3. **H4 arreglado** — `sync_supabase_to_sheets.py` gana `con_reintento()`: reintenta `open_by_key`
   y la escritura de la pestaña ante errores TRANSITORIOS de Google (429/5xx, red) con backoff
   (4 intentos, 5/10/15s). Antes `open_by_key` estaba fuera del try/except → traceback → toda la
   cadena q10-sync marcada error. Verificado: corrida limpia (826 filas, `estado=exito`).
4. **H5 arreglado** — nodo "Reenviar a Grabaciones" (workflow Zoom): `responseFormat: "text"` (ya
   no parsea la respuesta como JSON — el POST se envía igual, solo se leía mal el body) +
   `retryOnFail` (3 intentos, 3s). El "Invalid JSON in response body" era al LEER la respuesta, no
   al enviar. Workflow sigue activo; JSON re-exportado a `n8n-workflows/zoom-asistencia.json`.

---

## 5. Recomendaciones pendientes (requieren decisión/acción)

- **[Crítico, dolor B] — ✅ REFORZADO con GitHub Actions.** Se agregó
  `.github/workflows/alerta-frescura-nube.yml`: corre en la infra de GitHub (NO en el portátil ni
  en una sesión de Claude) cada 4h, lee `v_frescura` con la anon key pública y avisa por Telegram
  si hay vencidos o si Supabase no responde. Verificado end-to-end 2026-08-13: lectura anon OK +
  envío Telegram OK (mensaje de prueba recibido). **Falta 1 paso del usuario:** agregar los secrets
  `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` en el repo (Settings → Secrets → Actions). La rutina
  Claude `frescura-pipeline-rofe` (8:30 COT) queda como red redundante — confirmar que siga viva.
- **[Alto] Cargador de noche = requisito #1** (ya documentado en [[project_n8n_suspend_resume]]): la
  mayoría de incidentes son "portátil apagado/sin batería". Ningún auto-heal funciona con el equipo
  apagado.
- **[Medio] Aislar `sync_supabase_to_sheets`** (H4) en su propio workflow con reintento, para que su
  fallo transitorio no marque toda la cadena q10-sync como error.
- **[Medio] Arreglar el reenvío de grabaciones de Zoom** (H5): manejar respuesta no-JSON.
- **[Bajo] Migración a la nube** ([[migracion-n8n-digitalocean]]): sigue siendo el arreglo
  estructural. Esta auditoría compra el mes de transición, no lo reemplaza.

---

## 6. Veredicto de solidez

**Para ~1 mes de hosting local: sólido CON las 2 correcciones aplicadas + confirmar la alerta en la
nube.** Las 3 capas de auto-recuperación local ya cubren los cuelgues por suspensión (detección
~35 min vía watchdog de colgadas, ahora reforzada por el auto-heal arreglado y el watchdog
auto-sanador). El punto verdaderamente irresoluble en local es el **portátil apagado**: ahí solo la
rutina en la nube avisa, y solo un cargador permanente lo previene. Nada de esto sustituye la
migración; la hace menos urgente por ~1 mes.
