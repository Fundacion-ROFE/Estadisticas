# Plan de producción — DB Supabase, paneles y flujos (2026-07-24)

> Plan ejecutable escrito para ser operado por **Claude Sonnet** con subagentes en paralelo.
> Basado en 4 auditorías de código/documentación reales corridas el 2026-07-24 (no en suposiciones).
> Conexiones: [[supabase-estructura]] · [[panel-datos-etl]] · [[panel-riesgo-mejora]] · [[q10-consolidacion]] · [[migracion-n8n-digitalocean]] · [[00-vision-global]]
>
> Autor: Samuel Rojas (con Claude Fable). Estado: **PENDIENTE DE EJECUCIÓN**.

---

## 0. Cómo ejecutar este plan con Sonnet — LÉEME PRIMERO

### 0.1 Reglas duras para la sesión ejecutora (no negociables)

1. **Lee antes de tocar nada:** `CLAUDE.md`, este plan completo, y la sección relevante de
   `docs/procesos/mapa-codigo.md` para cada script que vayas a modificar.
2. **Nunca imprimas valores de secretos** (keys, tokens, contraseñas) en chat, logs ni commits.
   Si un archivo contiene un secreto, referéncialo como `[REDACTADO]` + archivo:línea.
3. **Nunca subas a git:** `.env*`, `tools/`, `credenciales_service_account.json`, ni ningún
   dato individual de estudiantes. `docs/` es GitHub Pages **público**.
4. **Después de CUALQUIER cambio que toque Supabase o un script del pipeline:** corre
   `python scripts/panel-datos/test_integridad_supabase.py` y verifica `estado=exito`.
   Guarda el conteo (hoy la línea base es ~39-44 PASS; crece con los datos).
5. **No confíes en los JSON de `n8n-workflows/`** — pueden estar desalineados con la
   instancia viva (gotcha documentado en `convenciones.md`). Verifica siempre contra
   `GET http://localhost:5678/api/v1/workflows` con header `X-N8N-API-KEY` (la key está en
   `scripts/q10-consolidacion/.env`). Tras editar un workflow, re-exporta el JSON al repo.
6. **Al editar workflows por API:** JAMÁS pegues JSON con tildes/ñ/¿ por PowerShell inline
   (los muele — gotcha en `convenciones.md#Editar workflows`). Escribe el JSON a un archivo
   con encoding UTF-8 y súbelo desde archivo.
7. **Una ola a la vez.** Dentro de una ola, lanza los tracks como subagentes paralelos
   (Task tool, un track por subagente, prompts listos en el Anexo A). Un subagente NO toca
   archivos de otro track. Al terminar la ola, tú (sesión principal) corres la verificación
   de cierre de ola antes de abrir la siguiente.
8. **Puertas de decisión 🙋 SAMUEL:** detente y pregunta. No decidas por él.
9. **Commits pequeños por track**, mensajes `fix:`/`feat:`/`chore:` en español, sin PII.
10. **Ventana de trabajo segura: 08:00–17:00 COT.** Los crons corren 17:00–07:30. Todo
    cambio de scripts del pipeline debe estar commiteado y probado a mano antes de las 17:00.
    Si no alcanzas, desactiva temporalmente el workflow afectado vía API y reactívalo al terminar.
11. Cada script modificado se **prueba a mano una vez** (o con `--dry-run` si existe) antes
    de confiar en que n8n lo corra solo de noche.

### 0.2 Limitaciones conocidas de Sonnet que este plan compensa

- No improvisa bien esquemas: por eso cada cambio trae columnas, llaves y comandos exactos.
- Tiende a marcar tareas como completas sin verificar: por eso cada track tiene criterios
  de aceptación medibles y la ola no cierra sin ellos.
- Puede perder contexto en sesiones largas: por eso los subagentes reciben prompts
  autocontenidos (Anexo A) que citan la sección del plan que les toca.

### 0.3 Cronograma realista

| Bloque | Cuándo | Contenido |
|---|---|---|
| **P0 Seguridad** | HOY, primera hora | Rotar credenciales expuestas + sacar secretos del código |
| **Ola 0** | HOY, ~45 min | Salvaguardas: baseline, respaldo, verificación n8n en vivo |
| **Ola 1** | HOY, tracks A–D en paralelo (~3-4 h) | Reparaciones: git desatendido, sync_retiros, higiene ETL, monitoreo+backups |
| **Ola 2** | HOY, antes de 17:00 + chequeo mañana 08:00 | Gate de verificación DB |
| **Ola 3a** | HOY si queda tiempo / mañana | GUI: migración de fuentes + fixes |
| **Ola 3b** | +1 a 2 días | GUI: rediseño funcional (tabs nuevos) |
| **Ola 4** | +1 a 2 días | Panel Netlify: etiquetas, sección retiros, verificación visual |
| **Ola 5** | Al cierre de cada ola | Documentación y reglas de mantenibilidad |

**La DB queda "apta para producción" al cerrar P0 + Olas 0–2 con la noche verde.** Las olas
3–4 son consumidores de la DB, no requisitos de la DB.

---

## 1. Estado real verificado hoy (resumen de las 4 auditorías)

Lo que cambia el diagnóstico previo:

1. 🔴 **NUEVO — Secretos en repo público:** `scripts/q10-consolidacion/q10_to_sheets.py:34-35`
   tiene usuario+contraseña de Q10 en texto plano, y `scripts/panel-datos/emoflow_api_test.py:19-20`
   tiene usuario+contraseña de Emoflow. **Ambos archivos están trackeados en git** con remoto
   `https://github.com/Fundacion-ROFE/Estadisticas.git` (verificado con `git ls-files`), el
   repo que sirve GitHub Pages — casi con certeza público, y el archivo está desde el commit
   inicial. Q10 contiene la PII de todos los estudiantes. → **P0**.
2. 🟢 **`sync_supabase_to_sheets.py` probablemente YA está arreglado** (reescrito 2026-07-23:
   ya no escribe H1/H2/H3Test; escribe una sola pestaña `AUTO_Emoflow_Uso` que se autocrea,
   `sync_supabase_to_sheets.py:310-315`). Falta solo confirmar en el historial de ejecuciones
   de n8n que la corrida más reciente salió verde. Las funciones H1/H3 viejas son código
   muerto desactivado.
3. 🔴 **Éxito silencioso en los 5 exporters con git push:** `git_commit_y_push()` en
   `export_stats.py`, `export_avance.py`, `export_retirados.py`, `export_aprobacion.py` y
   `export_supabase_json.py` captura cualquier fallo del push, lo loguea como ADVERTENCIA y
   el script igual imprime `estado=exito`. Si el push falla, GitHub Pages queda viejo sin
   que nadie se entere. Además ningún `subprocess.run` de git tiene `timeout=` → un prompt
   de credencial colgaría el nodo n8n para siempre.
4. 🔴 **La rama `Sched:` de "Bot Q10"** (corre 01:00 y 05:00) encadena 9 executeCommand,
   4 de ellos con git push, **sin un solo IF, stopAndError ni Telegram**. Cero visibilidad.
5. 🟡 **Bug de expresión n8n:** `q10-sync-supabase.json:407` tiene `={{ .stdout }}` (falta
   `$json`) en el IF "Sociodem OK?" — riesgo de falso fallo/comportamiento indefinido.
6. 🟡 **`export_supabase_json.py`** exporta 23 tablas configuradas de las cuales 6 son PII
   que siempre vuelven vacías (correcto por RLS, pero ruido), 1 no existe
   (`v_aprobacion_cohorte_stats`) y 1 está deprecada (`emoflow_participacion_semanal`);
   siempre reporta `estado=exito`; sigue sin consumidor confirmado.
7. 🟡 **Tabla `retiros` (migración 007) aplicada pero vacía** — falta `sync_retiros.py`.
   Es el hueco #1 de datos (retiro individual, la variable de resultado más valiosa).
8. 🟡 **GUI `panel_riesgo_gui.py`:** `leer_asistencia_zoom()` usa una key hardcodeada de
   nivel público contra `asistencia_promedio` — tabla cuyo acceso público fue revocado tras
   el incidente 2026-07-14 — con `except Exception: return {}` silencioso. **Es posible que
   la columna Asistencia % lleve días vacía sin que nadie lo note.** Retirados sigue leyendo
   Sheets; Avance manual seguirá en Sheets por diseño (es dato humano).
9. 🟡 **Sin backups** (free tier): la estrategia es reconstrucción desde fuentes, pero las
   series `historial_*` y snapshots no son reconstruibles.
10. 🟡 Deuda menor verificada: migraciones 006/007 con sufijo `_PROPUESTA` pero ya aplicadas;
    `sync_emoflow.py` deprecado fuera de `_obsoletos/`; `calcular_asistencia_promedio.py`
    retorna 0 aunque fallen todos los registros; fila huérfana recurrente en `emoflow_ingresos`;
    CLAUDE.md/mapa-codigo/panel-datos-etl desactualizados (23 nodos reales vs 20 documentados,
    cadencia real `30 17,19,21,23,1,3,5,7 * * *` vs "9:45" documentado); mojibake en nombres
    de nodos; `correos-rebotes-diario.json` con conexión de trigger aparentemente rota (verificar
    en vivo); `zoom-asistencia` sin ningún camino de error; 16 pares discordantes `postulantes_mr`
    en cola humana; frontend Next.js vive en repo hermano `C:\Users\EstudiantesJC\Downloads\panel-datos-rofe`
    (GitHub `comunicaciones-ai/Panel-De-Datos`, deploy Netlify on-push, fetch runtime con anon key).

---

## 2. Definición de "DB lista para producción" (Go/No-Go)

Se declara lista cuando TODO esto sea cierto:

- [ ] P0 cerrado: credenciales Q10 y Emoflow rotadas, código leyéndolas de `.env`, historia purgada.
- [ ] `test_integridad_supabase.py` → `estado=exito` con los tests nuevos incluidos (retiros).
- [ ] `retiros` poblada y cuadrando con `cohorte_ingresos.retirados` (tolerancia ≤3 por cohorte).
- [ ] Un fallo de `git push` produce `estado=error` + exit≠0 + alerta Telegram (probado con simulacro).
- [ ] Rama `Sched:` de Bot Q10 con validación y alerta de error.
- [ ] Bug `={{ .stdout }}` corregido y workflows re-exportados al repo.
- [ ] Respaldo automático corriendo (primer dump existente en `tools/backups/`).
- [ ] Workflow `panel-verificacion-diaria` activo (suite → Telegram si falla).
- [ ] Noche siguiente: las 8 corridas de `q10-sync-supabase` + las 2 nocturnas de Bot Q10 verdes.
- [ ] 🙋 SAMUEL decidió: plan Pro Supabase sí/no; futuro de `export_supabase_json` (consumidor o fecha de retiro).

---

## P0 — SEGURIDAD: secretos expuestos en repo público (hacer AHORA, secuencial)

**Contexto:** protocolo propio ya documentado en `convenciones.md#Gotcha: secreto commiteado`.
Una vez el secreto llegó al remoto, **rotar es lo único que des-expone**; la reescritura de
historia es higiene complementaria.

1. **Confirmar visibilidad del repo** `Fundacion-ROFE/Estadisticas` en GitHub (Settings →
   General → Danger Zone). GitHub Pages en org free ⇒ repo público casi seguro.
2. **Rotar la contraseña de Q10** (usuario de `q10_to_sheets.py:34`) desde la administración
   de Q10. Anotar la nueva SOLO en `scripts/q10-consolidacion/.env`.
3. **Rotar la contraseña de Emoflow** (la de `emoflow_api_test.py:19-20`). OJO: verificar si
   es la misma cuenta que usan `EMOFLOW_USER/EMOFLOW_PASSWORD` de `.env.local` — si sí, tras
   rotar hay que actualizar también `.env.local` o `sync_emoflow_api.py` y
   `extract_emoflow_ingresos_diario.py` fallarán esta noche.
4. **Sacar los secretos del código:**
   - `q10_to_sheets.py`: reemplazar las constantes por
     `Q10_USUARIO = os.environ["Q10_USUARIO"]` / `Q10_PASSWORD = os.environ["Q10_PASSWORD"]`
     cargando `scripts/q10-consolidacion/.env` con el patrón `cargar_env_local()` ya usado en
     `scripts/panel-datos/*` (ese `.env` ya lo carga `iniciar_n8n.bat`, así que los procesos
     hijos de n8n NO lo heredan automáticamente — el script debe leer el archivo él mismo).
     Agregar las 2 variables al `.env` y a `.env.example` (solo nombres).
   - `emoflow_api_test.py`: script exploratorio sin rol en producción → mover a
     `scripts/panel-datos/_obsoletos/` y de paso quitarle las credenciales (leer de env).
   - Los 5 scripts de diagnóstico con URL+key publishable hardcodeada
     (`debug_zoom_asistance.py`, `verificar_asistencia_estudiante.py`,
     `verificar_relacion_asistencia_q10.py`, `check_asistencia_supabase.py`,
     `check_supabase_status.py`): la anon/publishable key es pública por diseño (RLS protege),
     severidad baja — mover a `_obsoletos/` y normalizar a env en el mismo movimiento.
5. **Probar el bot con la credencial nueva ANTES de la corrida de las 17:00:** disparar
   `/actualizar q10` por Telegram (o ejecutar `q10_to_sheets.py --grupo h2test` a mano) y
   confirmar login exitoso a Q10.
6. **Purgar la historia** con `git filter-repo --replace-text` siguiendo EXACTAMENTE el
   protocolo de `convenciones.md:50-66` (verificación con `git cat-file --batch-all-objects`,
   re-agregar `origin`, forzar push). Coordinar con Samuel el momento (reescribe main).
7. **Criterio de aceptación:** `git grep` de fragmentos de los secretos viejos → 0 resultados
   en TODOS los objetos; bot Q10 y sync Emoflow corren verdes con credenciales nuevas.

🙋 SAMUEL: pasos 2, 3 y 6 los ejecuta/autoriza él (acceso admin a Q10/Emoflow y force push).

---

## OLA 0 — Salvaguardas (secuencial, ~45 min)

**0.1 Verificación n8n EN VIVO** (API local, no los JSON del repo):
   - Estado real de los 12 workflows (`active` true/false). En particular:
     `emoflow-ingresos-diario` (el export dice `active:false` — si de verdad está apagado,
     ¿quién alimenta `emoflow_ingresos_diario`/`emoflow_actividad_semanal`? Los tests de
     frescura lo dirán) y `correos-rebotes-diario` (conexión de trigger aparentemente rota
     en el export: la clave de `connections` no coincide con el nombre del nodo).
   - Últimas 3 ejecuciones de `q10-sync-supabase`: ¿el nodo "Ejecutar sync_supabase_to_sheets"
     ya sale verde con el código nuevo del 07-23? Si sí → el ítem "roto hace días" se cierra
     solo y se documenta.
   - Anotar resultados en un archivo temporal de sesión para el reporte final.

**0.2 Línea base de integridad:**
```bash
python scripts/panel-datos/test_integridad_supabase.py
```
Debe dar `estado=exito`. Guardar el total (línea `RESUMEN: total=N pass=X fail=Y`).
Si algo falla AQUÍ, investigar antes de cualquier otro cambio.

**0.3 Respaldo completo previo** (antes de tocar nada):
   - Crear `scripts/panel-datos/respaldo_supabase.py`: recorre TODAS las tablas base (las 24
     de `supabase-estructura.md`; NO las vistas) con `SUPABASE_SERVICE_ROLE_KEY` usando el
     patrón `get_todo()` paginado ya existente (copiar de `cargar_supabase.py`), y escribe
     `tools/backups/supabase_YYYYMMDD_HHMM/<tabla>.json` + un `_resumen.json` con conteos.
     Retención: borrar carpetas de más de 14 días. `tools/` está gitignoreado — la PII nunca
     sale del PC.
   - Correrlo una vez y verificar que los conteos coinciden con los documentados
     (`participants` ≈ 2.919, `enrollments` ≈ 18.196, `postulantes_mr` ≈ 5.310, etc.).
   - Este mismo script se agenda en el Track D.

**0.4 Snapshot git:** árbol limpio, anotar HEAD actual (`git log -1 --oneline`) como punto
de rollback de código.

---

## OLA 1 — Reparaciones críticas (4 tracks EN PARALELO, subagentes)

### Track A — Git 100% desatendido + fin del éxito silencioso
*(la petición explícita: "los flujos ya no necesiten confirmación de GitHub, permiso completo")*

**A1. Parchar `git_commit_y_push()` en los 5 scripts activos** (`export_stats.py:499-525`,
`export_avance.py:223-238`, `export_retirados.py:278-296`, `export_aprobacion.py:576-591`,
`export_supabase_json.py:117-144`) — misma corrección idéntica en los 5 (el estilo de la casa
es duplicar, no compartir módulo; mantenerlo así simplifica el patch):
   - Antes de commitear: si `git status --porcelain -- <rutas objetivo>` está vacío →
     log "sin cambios, no hay nada que publicar" y **retornar True** (no es fallo).
   - Cada `subprocess.run` de git con `timeout=180`. `TimeoutExpired` → fallo.
   - Si `add`/`commit`/`push` retorna ≠0 → log del stderr y **retornar False**.
   - En `main()` de cada script: si la función retorna False → imprimir
     `RESUMEN: ... estado=error detalle=git_push_fallido` y `sys.exit(1)`. El marcador
     `estado=exito` SOLO se imprime si el push terminó bien o no había nada que subir.
   - Los IF existentes de n8n ya buscan `estado=exito` / `exitCode==0` — con esto detectan
     el fallo sin tocarlos.

**A2. Git no interactivo a nivel sistema** (Opción A de la auditoría — mínimo riesgo, no
cambia el transporte HTTPS+schannel que ya funciona con el proxy MITM):
   - `git config --global credential.interactive never`
   - En `iniciar_n8n.bat`, junto a las otras `set`: `set GCM_INTERACTIVE=never` y
     `set GIT_TERMINAL_PROMPT=0`.
   - Fijar también a nivel repo lo que hoy depende de config global no versionada:
     `git config --local credential.helper manager` (documentar en `convenciones.md`).
   - Prueba: `git push --dry-run origin main` desde una terminal SIN sesión interactiva
     de credenciales (y vía un executeCommand manual en n8n) → debe salir sin prompt.
   - 🙋 SAMUEL (hardening opcional, semana próxima): PAT fine-grained solo-repo con
     `credential.helper store` como respaldo + recordatorio de rotación anual. SSH queda
     para la migración a DigitalOcean (decisión ya tomada en [[migracion-n8n-digitalocean]]).

**A3. Reparar los workflows (vía API, luego re-exportar):**
   - `q10-sync-supabase`: corregir `={{ .stdout }}` → `={{ $json.stdout }}` en el IF
     "Sociodem OK?" (línea 407 del export). Aprovechar y renombrar el trigger
     "Schedule Diario 9:45" → "Schedule 2h (17:30–07:30)" para que el nombre no mienta.
   - `q10-consolidacion` (Bot Q10), rama `Sched:`: agregar al final de la cadena un nodo
     Code/IF que revise `exitCode` de los 9 nodos `Sched:` + un Telegram "Corrida nocturna:
     ✅/⚠️ por paso" (mismo patrón del resumen de la rama manual, nodo "Responder OK").
     Con A1, un push fallido ahora produce exitCode≠0 y se ve ahí.
   - Simulacro de fallo (criterio de aceptación del track): romper temporalmente el remote
     (`git remote set-url origin https://github.com/Fundacion-ROFE/NOEXISTE.git`), correr
     `export_stats.py` a mano → debe imprimir `estado=error` y salir ≠0 en segundos (sin
     colgarse); restaurar remote; correr de nuevo → `estado=exito`.

**A4. Deuda registrada, no bloqueante hoy** (dejar anotada en [[migracion-n8n-digitalocean]]):
`zoom-asistencia` sin camino de error; `errorWorkflow` global para los 12; mojibake de
nombres de nodos (corregirlos vía API con archivo UTF-8 cuando se toque cada workflow).

### Track B — `sync_retiros.py`: poblar la tabla `retiros`

**Fuente JC:** pestaña `Retirados` del Sheet `1q4VNn4ltqVEMsOjo-c2ZbsbW3VIt-XomPgXeLSN_LTs`
(columnas exactas: `Identificacion, Nombre, TipoDocumento, Telefono, Programa, Sede,
FechaCancelacion, Causa, Descripcion, Tipo` — sin email ni curso; `Tipo` ∈ Cancelado/
Desertor/Aplazado). Leer con `get_all_records()` tolerante (patrón de `export_retirados.py:300-312`).

**Fuente MR:** pestaña `Inactivas` del Sheet `1ZsC4WyY26aOCEMrnZ_l8Tn-l69DB_0ADs5lnecaoEP8`
(~33 filas usables con `Motivos`, `Estado`, `Año-retiro` — mapear índices de columna a mano,
hoy ningún script los captura; `sync_postulantes_mr.py:224-226` muestra cómo se lee la pestaña).

**Mapeo a `retiros`** (esquema ya aplicado, `007`; upsert `on_conflict=cedula,cohorte,programa`):

| Columna | JC | MR |
|---|---|---|
| `cedula` | `Identificacion` normalizada (solo dígitos) | cédula normalizada |
| `participant_id` | lookup `participants.q10_id` (puede ser NULL — retirados viejos no cargados) | ídem |
| `programa` | `'JC'` | `'MR'` |
| `cohorte` | si cédula ∈ `tools/cohorte_2026.json` → `'2026'`; si no → año de `FechaCancelacion` (best-effort, documentar) | `Año-retiro` con cautela (el doc advierte que puede ser año de registro, no cohorte) — usar y marcar en `motivo` si ambiguo |
| `fecha_retiro` | `FechaCancelacion` parseada | vacío si no hay |
| `anio_retiro` | año de la fecha | `Año-retiro` |
| `motivo` | `Causa — Descripcion` (truncar 300) | `Motivos` |
| `etapa` | reutilizar `etapa_de_retiro()` de `export_retirados.py:116-125` contra `tools/aprobacion_ledger.json` | NULL |
| `fuente` | `'sheet_retirados_q10'` | `'inactivas_mr'` |

**Requisitos del script:** `truststore.inject_into_ssl()`, `cargar_env_local()`,
service_role, User-Agent `panel-datos-etl/1.0`, `--dry-run`, resumen final
`RESUMEN: ... estado=exito|error` (contrato n8n), errores que LANZAN (nunca silencio).

**n8n:** insertar nodo "Ejecutar sync_retiros" + IF + stopAndError en `q10-sync-supabase`
**después de "Ejecutar sync_aprobacion"** (así `aprobacion_ledger.json` y la pestaña
Retirados — refrescada por Bot Q10 30 min antes en el diseño de dos velocidades — están
frescos). Re-exportar JSON.

**Tests nuevos en `test_integridad_supabase.py`:** (1) cuadre
`|retiros(cohorte 2026, JC) − cohorte_ingresos.retirados(2026, JC)| ≤ 3` (ya redactado en
`007:51`); (2) unicidad de `(cedula,cohorte,programa)`; (3) `retiros` con >0 filas (frescura).

**Criterio de aceptación:** corrida real → ~82+ filas JC 2026 + históricas + ~25-33 MR;
suite completa verde; segunda corrida idéntica (idempotencia) → 0 filas nuevas.

### Track C — Higiene del ETL y documentación operativa

1. **`export_supabase_json.py`:** quitar de la lista las 6 tablas PII (siempre vacías por
   RLS), la vista inexistente `v_aprobacion_cohorte_stats` y la deprecada
   `emoflow_participacion_semanal`; generar `manifest.json` desde lo realmente exportado
   (no hardcodeado); `estado=exito` solo si TODAS las configuradas exportaron (si una da
   error o 0 filas inesperadas → `estado=error` + exit 1). 🙋 SAMUEL: este export sigue sin
   consumidor confirmado — ¿se mantiene (futuro consumidor), o se le pone fecha de retiro?
   Mientras decide: se mantiene, ya limpio.
2. **Confirmar cierre de `sync_supabase_to_sheets`** (con lo visto en Ola 0.1) y actualizar
   [[supabase-estructura]] y [[panel-datos-etl]] (la "deuda detectada" del 07-23 quedó
   resuelta por la reescritura del mismo día). 🙋 SAMUEL: ¿alguien del equipo usaba las
   hojas H1/H2/H3 viejas? Default: NO se reconstruyen (el código muerto H1/H3 se borra).
3. **`calcular_asistencia_promedio.py`:** si `errores > 0` → `return 1` y quitar el
   `[OK]` del stdout (el IF de n8n ya busca ese marcador — alinear).
4. **Fila huérfana `emoflow_ingresos`:** agregar a `sync_emoflow_api.py` un paso final que
   detecte emails en tabla ausentes del CSV del día y los reporte en el resumen (y si
   `--purgar-huerfanos` está presente, los borre). Borrar la huérfana actual.
5. **Limpieza de repo:** mover `sync_emoflow.py` a `_obsoletos/`; renombrar
   `006_seguridad_hardening_PROPUESTA.sql` → `006_seguridad_hardening_APLICADA_PARCIAL.sql`
   y `007_retiros_PROPUESTA.sql` → `007_retiros_APLICADA.sql` (su contenido ya dice que
   están aplicadas; el nombre miente); dejar nota del hueco `004` (no existe, numeración
   saltada) en un README de `docs/migrations/`.
6. **Deprecación `emoflow_participacion_semanal`:** exportar CSV de respaldo a
   `tools/backups/`, luego migración `012_drop_emoflow_participacion_semanal.sql`
   (🙋 SAMUEL aprueba el DROP; el frontend ya no la consume según auditoría 07-23).
7. **Docs desactualizados (actualizar en el mismo track):** `CLAUDE.md` (quitar
   `sync_emoflow_participacion.py` como activo; agregar `docs/aprobacion/`,
   `docs/mujeres-rofe/`, `docs/datos/` al árbol; agregar `sync_retiros.py` y
   `respaldo_supabase.py` a la tabla); `mapa-codigo.md` (tabs reales de la GUI);
   `panel-datos-etl.md` (23 nodos, cadencia real, checklist final marcado);
   `supabase-estructura.md` (retiros 🟢 al poblarse, H9 con fix).
8. **16 pares discordantes `postulantes_mr`:** no es tarea de Sonnet — dejar en el reporte
   final el recordatorio a Samuel con la ruta `Downloads/postulantes_mr_disonancias_general.xlsx`.

### Track D — Monitoreo continuo + respaldos automáticos

1. **Workflow nuevo `panel-verificacion-diaria`** (diseño ya propuesto en
   [[supabase-estructura]], ajustado a la cadencia real): cron `0 8 * * *` COT (después de
   la última corrida nocturna de las 07:30) → executeCommand
   `python scripts/panel-datos/test_integridad_supabase.py --rapido` → IF
   `estado=exito` → noOp / rama error → Telegram a Samuel con el tail del stdout.
   Nombre según convención `[area]-[accion]`. Exportar JSON al repo.
2. **Respaldo agendado:** nodo/workflow `datos-respaldo-diario` cron `15 8 * * *` →
   `python scripts/panel-datos/respaldo_supabase.py` (creado en Ola 0.3) → IF + Telegram
   en error. Verificar que la retención de 14 días borra bien.
3. **🙋 SAMUEL — decisión de infraestructura:** plan Pro de Supabase ($25/mes) para backups
   PITR reales. Recomendación del plan: sí cuando haya presupuesto; mientras tanto el
   respaldo local diario cubre lo no-reconstruible (`historial_*`, snapshots).
4. **`errorWorkflow` global:** crear workflow `alerta-fallo-workflow` (Error Trigger →
   Telegram "workflow {{name}} falló: {{error}}") y asignarlo como `errorWorkflow` en
   settings de los 4 críticos: `q10-sync-supabase`, `q10-consolidacion`,
   `asistencia-zoom-diario`, `mr-actualizacion-datos`.

### Cierre de Ola 1 (sesión principal, secuencial)

1. Suite completa → verde (con los tests nuevos de retiros).
2. Corrida manual completa de `q10-sync-supabase` (ejecución manual en n8n, en horario
   diurno) → los 8-9 pasos verdes, incluido el nuevo sync_retiros.
3. Simulacro de push fallido (A3) pasado.
4. `git log` limpio, JSONs de workflows re-exportados, commit.

---

## OLA 2 — Gate de verificación de la DB

- [ ] `test_integridad_supabase.py` completo (sin `--rapido`) → `estado=exito`.
- [ ] Cuadres canónicos a mano (vía `verificar_supabase_panel_riesgo.py` o queries REST):
      JC 2026 activos = 760 (canónico Seguimiento), `v_retiro_probable_jc` = 17,
      `cohorte_ingresos` JC 2026 = 760/74, MR 2026 = 283 estudiantes / 9 cursos.
- [ ] `retiros`: total JC 2026 ≈ 82 únicos (cifra del panel de retirados), Δ vs
      `cohorte_ingresos.retirados` ≤ 3, y 74 confirmados como subconjunto coherente.
- [ ] `git push --dry-run` sin prompt; último commit automático del día visible en GitHub.
- [ ] **Mañana 08:00-08:30:** revisar en n8n las corridas nocturnas (17:00, 17:30, 19:30,
      21:00, 21:30, 23:30, 01:00, 01:30, 03:30, 05:00, 05:30, 07:30) + el Telegram de la
      rama Sched: + el `panel-verificacion-diaria` de las 08:00. Todo verde → **DB EN PRODUCCIÓN**.
- [ ] Si algo falla de noche: el rollback por track está en la sección "Riesgos y rollback".

---

## OLA 3 — GUI `panel_riesgo_gui.py`: de panel de riesgo a panel integral

**Decisiones que se mantienen** (ya tomadas, no reabrir): Tkinter local por PII;
`service_role`; vistas curadas, no query-builder libre; hoja `Avance` sigue en Sheets
(dato manual humano, no tiene fuente sistema).

### 3a — Migración de fuentes y fixes (HOY/mañana, ~2-3 h)

1. **Extraer capa de datos** a `tools/panel_riesgo_datos.py` (líneas ~140-540 actuales:
   config, `_Supa`, `conectar*`, `leer_*`, `cruzar`) — corte mecánico ya probado
   (`verificar_supabase_panel_riesgo.py` importa el módulo sin Tkinter). La GUI importa de ahí.
2. **Arreglar `leer_asistencia_zoom()`** (hoy: key pública hardcodeada + sin paginación +
   `except: return {}` silencioso, y probablemente rota desde el endurecimiento del 07-14):
   reescribir sobre `_Supa`/service_role con `get_todo()` paginado y log de error visible.
   Verificar que la columna Asistencia % vuelve a mostrar datos (490 estudiantes).
3. **Tab Retirados → Supabase:** `leer_retirados()` pasa a leer tabla `retiros`
   (post Track B) con las columnas nuevas (`etapa`, `fuente`, `programa`), manteniendo
   fallback al Sheet si la tabla responde vacía (transición segura). KPIs iguales + KPI
   nuevo por `etapa`.
4. **Cédula de fuente única:** en las vistas cruzadas JC (match/atención/avance0/ok) la
   cédula sale hoy de la hoja Avance; cambiar a `participants.q10_id` (ya viene en
   `leer_h2test`).
5. Borrar constantes muertas `ZOOM_ASISTANCE_SHEET_ID/TAB`; mover `tools/panel_riesgo.py`
   (CLI 100% Sheets, reemplazado por `alerta_desercion.py`) a un `_obsoletos/` de tools.
6. **Criterio de aceptación 3a:** la GUI abre, "Actualizar datos" puebla los 5 tabs con
   los MISMOS conteos canónicos de la Ola 2 (760/283/9 cursos), Asistencia % con datos,
   tab Retirados mostrando las filas de Supabase.

### 3b — Rediseño funcional (1-2 días): estructura objetivo de tabs

| # | Tab | Utilidad (para quién/qué decisión) | Fuente Supabase | Funcionalidades |
|---|---|---|---|---|
| 0 | 🎓 JC | Seguimiento operativo cohorte JC | `enrollments`+`participants`+`courses`, `asistencia_promedio` | Como hoy + cédula unificada |
| 1 | 💡 MR | Ídem MR | ídem | Como hoy |
| 2 | 🧭 Decisiones **(NUEVO — Fase 2 ya especificada)** | Coordinación: "¿a quién llamo hoy?" | `v_puntaje_estudiante`, `emoflow_ingresos` LEFT JOIN `participants`, `asistencia_promedio`(<70%), `aprobacion_cursos`(banda 0-25), `retiros` recientes, filtro `grupo_ciudad` | 6 botones = 6 `consulta_xxx()` sobre `TablaFiltrable`; semáforo verde/ámbar/rojo con umbrales existentes (70% asistencia, banda 0-25, sin Emoflow); export CSV |
| 3 | 🚪 Retiros | Análisis de deserción real | `retiros` (+ `v_retiro_probable_jc` como sección "pendientes de confirmar") | Por etapa/causa/mes/programa; distinción retiro oficial vs probable |
| 4 | 🔎 Persona 360 **(NUEVO)** | Trazabilidad total de UNA persona (la petición "toda la información del programa") | `v_persona_360` por cédula (`GET /rest/v1/v_persona_360?cedula=eq.<c>`, solo service_role) | Buscador por cédula/nombre; ficha: postulación → matrícula → avance por curso → Emoflow → asistencia → retiro. El doble clic de CUALQUIER otro tab abre esta ficha (Fase 3) |
| 5 | 📥 Embudo/Postulantes **(NUEVO)** | Convocatorias y conversión (insumo P5) | `postulantes_jc` (2.556), `postulantes_mr` (5.310), cruce a `participants` | KPIs: postulantes vs matriculados por programa/cohorte/ciudad; tasa de conversión; lista de no-convertidos exportable |
| 6 | 🔀 Diferencias | Control de calidad Q10 vs hoja manual | igual que hoy | Sin cambios |
| 7 | ⚙ Admin | Config + salud del sistema | `course_config.json` + tests de frescura por tabla | Como hoy + panel "salud de datos": última fecha por tabla clave y botón "correr suite de integridad" |

Mejoras transversales 3b: fetches en paralelo (`ThreadPoolExecutor`) para bajar el tiempo de
"Actualizar datos" (hoy 7-9 llamadas secuenciales); refresco perezoso por tab; factorizar
`_build_kpi_tab()` (hoy ~100 líneas duplicadas ×4); ficha 360 como popup compartido.

**Criterio de aceptación 3b:** cada tab nuevo muestra conteos verificables contra queries
directas (anotar 3 cifras de control por tab en el commit); tiempo de carga total ≤ el actual.

---

## OLA 4 — Panel de datos Netlify (repo hermano)

⚠️ El repo vive FUERA de esta carpeta: `C:\Users\EstudiantesJC\Downloads\panel-datos-rofe`
(GitHub `comunicaciones-ai/Panel-De-Datos`, Netlify auto-deploy on push,
`https://venerable-truffle-331f3c.netlify.app`). La sesión ejecutora debe abrir esa carpeta.

1. **Etiquetar las métricas de aprobación en TODA la UI:** donde se muestre un %, el label
   dice explícitamente "por matrícula" (15,2% MR / 92,8% JC — `aprobacion_cursos`) o
   "por estudiante" (31,6% MR / 88,3% JC — `cohorte_ingresos.pct_aprobados`). Es la
   condición para que Ana/Lina/Astrid puedan citar cifras sin malinterpretarlas.
2. **Sección Retiros (agregada, sin PII):** migración `013_v_retiros_stats.sql` — vista
   `v_retiros_stats` (conteos por programa × cohorte × etapa × causa × mes, con supresión
   k-anonimato n<5 → NULL como `v_demografia_grupo`), `GRANT SELECT` a anon + test en la
   suite (anon → 200 solo agregados). Nueva fuente en `lib/api.ts` (usar `leerPaginado()`)
   + sección en la página, al lado de `v_retiro_probable_jc`.
3. **Verificación visual pendiente del 07-23:** toggle "Solo estudiantes actuales/Todos"
   y tabla de verificación cruzada en `localhost:3000` (quedó sin confirmar visualmente).
   De paso confirmar que las celdas NULL de k-anonimato no rompen la demografía (H10).
4. **Cerrar la pregunta del consumidor:** buscar en el repo Netlify cualquier referencia a
   `docs/datos/*.json` → confirmar que nadie los lee → alimentar la decisión 🙋 de C1.
5. **Criterio de aceptación:** deploy verde en Netlify; las cifras del panel = cuadres de
   Ola 2; ninguna vista nueva expone email/nombre/cédula con anon key (probar con curl).

---

## OLA 5 — Flujo de datos sostenible (se ejecuta al cierre de cada ola)

**Arquitectura objetivo (documentarla en [[00-vision-global]]):**

```
FUENTES                     VERDAD ÚNICA                CONSUMIDORES
Q10 ──(bot 4x/día)──► Sheets h2test ─┐
BD Seguimiento (Sheet, humano) ──────┤
BD-Mujeres ROFÉ (Sheet, humano) ─────┼─► SUPABASE ──► GUI local (service_role, PII)
Emoflow API ─────────────────────────┤   panel-datos  ──► Panel Netlify (anon, agregados)
Zoom webhook ──► ZOOM-ASISTANCE ─────┘   -rofe        ──► Reportes/alertas (n8n+Telegram)
                                          │
docs/*/data.json + git push ◄─ exporters ─┘ (legado GitHub Pages: se mantiene
                                             hasta migrar dashboards al panel)
```

**Reglas de mantenibilidad (agregar a `convenciones.md`):**
1. Toda fuente nueva entra con: script `sync_*` idempotente (upsert con `on_conflict`
   explícito) + contrato `RESUMEN: estado=exito|error` + nodo n8n con IF+stopAndError +
   tests en la suite (integridad + frescura + anon 401 si PII) + fila en
   [[supabase-estructura]].
2. Ningún script imprime `estado=exito` sin verificar sus efectos (regla nacida del bug
   de git push silencioso).
3. Deprecación formal = respaldo CSV a `tools/backups/` + DROP por migración numerada +
   retiro de TODAS las referencias (grep) + nota en el diccionario.
4. Los JSON de `n8n-workflows/` se re-exportan en el MISMO commit que cambia el workflow.
5. Secretos SOLO en `.env*` (gitignoreados); `git grep -iE "password|api_key" -- '*.py'`
   como chequeo previo a cada push manual.

**Cierre documental (checklist doc-sync):** actualizar [[supabase-estructura]],
[[panel-datos-etl]], [[panel-riesgo-mejora]] (Fases 2-3 → hechas cuando toque),
[[q10-consolidacion]], [[mapa-codigo]], `CLAUDE.md`, entrada en `claude_sessions.md`,
mover filas en [[00-vision-global]].

---

## Riesgos y rollback

| Riesgo | Mitigación / rollback |
|---|---|
| Rotación Q10 rompe el bot a las 17:00 | Probar login manual ANTES de las 17:00 (P0.5); si falla, revertir temporalmente la contraseña en Q10 (no en código) |
| Patch de git rompe un exporter | Commits por script; `git revert` del commit puntual; los exporters son independientes entre sí |
| `sync_retiros` carga datos malos | `--dry-run` primero; la tabla es nueva (sin consumidores aún) → `DELETE FROM retiros` + recargar es seguro; respaldo de Ola 0.3 existe |
| Edición por API corrompe un workflow | Export previo del JSON vivo ANTES de editar (rollback = re-import); nunca editar los 12 a la vez |
| DROP de `emoflow_participacion_semanal` rompe algo no visto | CSV de respaldo previo + el DROP va en migración reversible (CREATE + reimport del CSV) |
| filter-repo reescribe main y algo diverge | Hacerlo al final del día con árbol limpio; clon espejo local previo como respaldo |
| GUI 3a rompe el panel que el equipo usa | `panel_riesgo_gui.py` se copia a `tools/_backup_gui_20260724.py` antes de tocar; rollback = restaurar archivo |

---

## Anexo A — Prompts listos para los subagentes de Sonnet

> Uso: la sesión principal (Sonnet) lanza estos prompts con el Task tool, en paralelo por
> ola. Cada prompt es autocontenido pero exige leer la sección del plan correspondiente.

**A.0 (P0 — sesión principal, NO subagente; requiere a Samuel):** seguir la sección P0 del
plan paso a paso. No paralelizar.

**A.1 Track A:**
```
Lee docs/procesos/plan-produccion-datos-2026-07-24.md, sección "Track A", y CLAUDE.md.
Tarea: (1) aplica el patch de git_commit_y_push() descrito en A1 a los 5 scripts listados
(idéntico en los 5, con timeout=180, detección de "sin cambios", return False en fallo, y
estado=error + sys.exit(1) en main si el push falla); (2) ejecuta los comandos de A2;
(3) haz las 2 reparaciones de workflows de A3 VÍA API de n8n (X-N8N-API-KEY en
scripts/q10-consolidacion/.env, JSON desde archivo UTF-8, nunca inline por PowerShell),
re-exporta los JSON a n8n-workflows/; (4) corre el simulacro de push fallido de A3 y
pega la evidencia (stdout con estado=error y luego estado=exito al restaurar).
Prohibido: imprimir secretos; tocar archivos de otros tracks; commitear .env o tools/.
Al final: reporte con diffs resumidos + resultado del simulacro.
```

**A.2 Track B:**
```
Lee docs/procesos/plan-produccion-datos-2026-07-24.md, sección "Track B", y
docs/procesos/mapa-codigo.md (entradas de export_retirados.py y sync_postulantes_mr.py).
Tarea: escribe scripts/panel-datos/sync_retiros.py EXACTAMENTE con el mapeo de la tabla
del plan (JC: pestaña Retirados del Sheet 1q4VNn...; MR: pestaña Inactivas del Sheet
1ZsC4...; upsert on_conflict=cedula,cohorte,programa; --dry-run; RESUMEN estado=exito).
Córrelo con --dry-run, muestra 5 filas de ejemplo SIN nombres reales (enmascara), corre
real, agrega los 3 tests nuevos a test_integridad_supabase.py (sección D y F), corre la
suite completa y reporta el RESUMEN. Luego inserta el nodo en q10-sync-supabase vía API
según el plan y re-exporta el JSON. Prohibido: tocar otros scripts; imprimir PII.
```

**A.3 Track C:**
```
Lee docs/procesos/plan-produccion-datos-2026-07-24.md, sección "Track C".
Ejecuta los puntos 1-7 en orden (el 6 requiere aprobación previa de Samuel para el DROP —
si no la tienes, deja la migración 012 escrita pero NO aplicada). Para el punto 2 usa el
resultado de la Ola 0.1 que te pasará la sesión principal. Cada punto = un commit.
Al final corre test_integridad_supabase.py y reporta.
```

**A.4 Track D:**
```
Lee docs/procesos/plan-produccion-datos-2026-07-24.md, sección "Track D".
Crea los 2 workflows nuevos y el errorWorkflow global vía API de n8n (nombres en
convención area-accion, JSON desde archivo UTF-8), actívalos, ejecuta cada uno
manualmente una vez y pega el resultado. Exporta los 3 JSON a n8n-workflows/.
Verifica que scripts/panel-datos/respaldo_supabase.py (creado en Ola 0) corre bien
desde n8n y que tools/backups/ tiene el dump del día.
```

**A.5 Ola 3a (GUI)** y **A.6 Ola 4 (Netlify):** usar las secciones respectivas como prompt,
con la misma cabecera de reglas (leer plan + CLAUDE.md, no secretos, no PII, criterios de
aceptación al final). Para Ola 4, abrir la carpeta `Downloads\panel-datos-rofe`.

---

## Anexo B — Comandos de verificación rápida

```bash
# Suite de integridad (línea base y cierre de cada ola)
python scripts/panel-datos/test_integridad_supabase.py

# Cuadre canónico GUI vs Supabase
python tools/verificar_supabase_panel_riesgo.py

# ¿Quedó algún secreto en el código trackeado?
git grep -iE "(password|passwd|api_key|secret)\s*=\s*[\"']" -- "*.py"

# Estado real de workflows (no confiar en los JSON del repo)
curl -H "X-N8N-API-KEY: %N8N_API_KEY%" http://localhost:5678/api/v1/workflows

# Push no interactivo
git push --dry-run origin main

# Conteo retiros vs canónico (tras Track B)
# GET /rest/v1/retiros?select=count  y  /rest/v1/cohorte_ingresos?select=cohorte,programa,retirados
```
