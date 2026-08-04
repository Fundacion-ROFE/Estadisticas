# Plan — encadenar `validar_asistencia.py` en `asistencia-zoom-diario`

> Preparado en sesión Cowork el 2026-07-30. **El JSON del workflow ya quedó modificado y
> auto-verificado**; lo único que falta es la corrida en seco del script y el `PUT` a la API
> de n8n, que requieren el PC de Samuel (esta sesión no alcanza `localhost:5678` ni las APIs
> de Google). Proceso: [[zoom-asistencia]] · Script: [[mapa-codigo]]

## Qué ya está hecho

- `scripts/zoom-asistencia/validar_asistencia.py` — escrito y probado en seco (13/13 casos de
  la cascada de match, 9 temas reales de Zoom mapeados a curso). Imprime la línea sentinela
  `[OK] Validacion completa: N registros, M para revision manual, K datos corregidos`
  (también en `--dry-run`), mismo patrón que `[OK] Sincronizacion completa` de
  `sync_asistencia_supabase.py`.
- `n8n-workflows/asistencia-zoom-diario.json` — ya contiene los 3 nodos nuevos y las
  conexiones reescritas. Verificado por script: 11 nodos, sin nombres/ids duplicados, sin
  nodos inalcanzables desde el trigger, `conditions` del IF plano, tildes intactas.

**Cadena resultante** (el validador corre **antes** del sync, así el panel nunca se
actualiza con una corrida en la que la validación falló):

```
Schedule 17:45
  └─ Ejecutar validar_asistencia
       └─ ¿Validación OK?   (stdout contains "[OK] Validacion completa")
            ├─ [0] true  → Ejecutar sync_asistencia_supabase → ¿Sync OK? → …(cadena existente)
            └─ [1] false → Error Validacion (Telegram)
```

---

## Prompt para Claude Code

```
Contexto: en la sesión Cowork del 2026-07-30 se creó
scripts/zoom-asistencia/validar_asistencia.py (valida identidad de asistentes Zoom contra
Supabase y escribe la pestaña ASISTENCIA-VALIDADA en H3Test) y se dejó
n8n-workflows/asistencia-zoom-diario.json ya modificado para encadenarlo antes del sync.
Falta ejecutar el script una primera vez y aplicar el JSON al workflow en vivo.
Lee docs/procesos/plan-encadenar-validacion-zoom-2026-07-30.md y ejecuta los pasos 1 a 4.
No toques la lógica de match sin avisar: sus umbrales están calibrados con datos medidos.
```

---

## Paso 1 — Corrida en seco del script (antes de tocar n8n)

```
python scripts/zoom-asistencia/validar_asistencia.py --dry-run
```

Confirmar en la salida:

- [ ] Se leyeron `ZOOM-ASISTANCE` y `ASISTENCIA-10MIN` sin error de headers.
- [ ] El universo cargó: debe imprimir ~760 personas activas de 2026 y 9 cursos.
- [ ] Aparece la línea `[OK] Validacion completa: …` (es la que lee el IF de n8n).
- [ ] El resumen por tipo de match es coherente con la línea base medida en Supabase:
      **~82% correo exacto, ~17 typos corregibles, el resto a revisión**. Si `sin_match`
      sale muy por encima de ~90 correos distintos, parar: probablemente el universo se
      cargó incompleto (revisar `SUPABASE_SERVICE_ROLE_KEY` en `.env.local`).

**Dato que hay que medir en esta misma corrida** (decide si el camino "ID correcto → corrige
correo" sirve de algo): qué porcentaje de las filas trae la columna `Identificacion` llena.
Contar los `id_exacto_corrige_correo` + los `correo_exacto` con cédula distinta; si la
columna viene casi siempre vacía, el hallazgo hay que llevarlo al equipo — el formulario de
Zoom no está capturando la identificación y ningún algoritmo lo arregla.

Si el dry-run se ve bien, correr sin bandera para escribir de verdad:

```
python scripts/zoom-asistencia/validar_asistencia.py
```

y revisar a ojo en el Sheet: pestaña `ASISTENCIA-VALIDADA` creada, correcciones en verde,
filas amarillas/rojas por `Estado`, y en `ZOOM-ASISTANCE` los correos malos tachados en rojo.

## Paso 2 — Aplicar el JSON al workflow en vivo

Workflow `asistencia-zoom-diario`, id **`qKBCgp1zFa3qeZAB`**.

Usar un script Python puntual con `urllib.request` leyendo el JSON desde archivo en UTF-8 —
**no PowerShell**: `ConvertTo-Json` colapsa los arrays de un elemento de `connections.main`
y la consola mutila las tildes de `¿Validación OK?` en el dato real enviado (ambos gotchas
documentados en [[convenciones#Editar workflows n8n por API (sin abrir la UI)]]).

- El body del `PUT /api/v1/workflows/{id}` solo acepta `name`, `nodes`, `connections`,
  `settings` — tomar esas 4 claves del JSON del archivo.
- API key: memoria `reference-n8n-api-key`.

## Paso 3 — Verificar contra el workflow EN VIVO (no contra el archivo)

```
GET /api/v1/workflows/qKBCgp1zFa3qeZAB
```

- [ ] `active: true` (a veces el PUT lo deja inactivo → reactivar).
- [ ] Los 11 nodos están y `¿Validación OK?` conserva la tilde y el `¿` (comparar byte a byte
      con el archivo, leyendo la respuesta desde un archivo, no desde la consola).
- [ ] `connections["¿Validación OK?"].main[0][0].node == "Ejecutar sync_asistencia_supabase"`
      y `main[1][0].node == "Error Validacion"` — índice 0 es SIEMPRE la rama true.
- [ ] `conditions` del IF es una lista de dicts, no de listas.

## Paso 4 — Primera ejecución real (obligatorio)

`active: true` no prueba nada: un IF sobre-anidado guarda 200 y revienta al ejecutarse. Correr
el workflow a mano desde la UI o esperar el tick de las 17:45 y revisar:

```
GET /api/v1/executions?workflowId=qKBCgp1zFa3qeZAB&limit=3
```

- [ ] La ejecución llegó hasta `¿Cálculo OK?` → `OK` (los 3 scripts corrieron en cadena).
- [ ] No llegó ningún mensaje de error a Telegram.
- [ ] `v_frescura` en Supabase sigue marcando `asistencia_promedio (zoom)` como no vencido.

## Al cerrar

1. Re-exportar el JSON en vivo a `n8n-workflows/asistencia-zoom-diario.json` (por si el PUT
   normalizó algo).
2. Actualizar [[zoom-asistencia]]: mover la validación de "script listo, sin primera corrida"
   a automatizada, con los números reales de la primera corrida.
3. Actualizar la fila correspondiente en `docs/00-vision-global.md`.
4. Entrada en `claude_sessions.md` con la tasa real de llenado de `Identificacion` — es el
   dato que decide el siguiente paso del proceso.

## Pendiente que este plan NO cubre

`sync_asistencia_supabase.py` sigue subiendo el **correo crudo** a `asistencia_zoom`, así que
`asistencia_promedio` reparte la asistencia de una misma persona entre 2 correos cuando hubo
typo. Arreglarlo es un cambio aparte (leer `ASISTENCIA-VALIDADA` en vez de `ZOOM-ASISTANCE`,
o aplicar el mismo módulo de match dentro del sync) y conviene decidirlo **después** de ver
los números de la primera corrida.
