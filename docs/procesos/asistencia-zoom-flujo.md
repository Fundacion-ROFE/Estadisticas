# Proceso: Asistencia Zoom → Panel de Riesgo

## Descripción general

Automatización que:
1. Recopila asistencia Zoom en Google Sheets (`ZOOM-ASISTANCE`)
2. Sincroniza los registros crudos a Supabase (`asistencia_zoom`)
3. Calcula promedios por estudiante y por curso
4. Almacena en Supabase (`asistencia_promedio`)
5. Muestra en Panel de Riesgo en tiempo real (aproximado)

## Flujo de datos

```
Zoom (eventos en vivo)
    ↓ [webhook]
n8n (procesa eventos)
    ↓ [escribe registros]
Google Sheets: ZOOM-ASISTANCE
    ↓ [cron n8n 00:00 diario]
Script Python: sync_asistencia_supabase.py
    ↓ [upsert registros crudos]
Supabase: asistencia_zoom
    ↓ [solo si el paso anterior fue exitoso]
Script Python: calcular_asistencia_promedio.py
    ↓ [calcula promedios]
Supabase: asistencia_promedio
    ↓ [consulta REST]
Panel de Riesgo (GUI)
    ↓ [visualización]
Usuario ve: "Asistencia %" en todas las vistas
```

## Componentes

### 1. Google Sheets: ZOOM-ASISTANCE
**Ubicación:** `1VyXOYsnpD9ksKcJFHiiRR6fr4UUCea4WmGG96NV0WP0`

**Estructura:**
| Nombre | Apellido | Correo electrónico | Identificacion | Instancias | Curso | Fecha | % Asistencia |
|--------|----------|-------------------|---|---|---|---|---|
| Juan | Pérez | juan@mail.com | 123 | 2/3 | Desarrollo Web | 2026-07-01 | 85% |

**Actualización:** n8n webhook (a configurar) cada vez que hay evento Zoom

### 2. Script Python: `sync_asistencia_supabase.py`

**Función:** lee `ZOOM-ASISTANCE`, excluye cursos de staff/pruebas (`CURSOS_EXCLUIDOS`: "Prueba -
Asistencia", "Reunión con Katze", "Mi reunión", "Entrevista NOVA"), trunca `fecha` a solo el día
(la columna Supabase es `date`, no `timestamp`), deduplica por (email, curso, fecha) conservando
el **mayor % de asistencia** (no la última fila del Sheet) → upsert por lotes de 100 en
`asistencia_zoom` (`Prefer: resolution=merge-duplicates` + `?on_conflict=email,curso,fecha`,
requerido porque la PK real de la tabla es `id`, no esas 3 columnas).

**Uso manual:**
```bash
python scripts/panel-datos/sync_asistencia_supabase.py [--dry-run]
```

**Credenciales:** `.env.local` raíz (`SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY`).

### 3. Script Python: `calcular_asistencia_promedio.py`

**Función:**
```
Lee ZOOM-ASISTANCE
  ↓
Agrupa por email
  ↓
Calcula: promedio = suma(%) / cantidad_clases
  ↓
Calcula: promedios por curso
  ↓
Inserta en asistencia_promedio (Supabase)
```

**Uso manual:**
```bash
python scripts/panel-datos/calcular_asistencia_promedio.py
```

**Salida:** 490+ estudiantes con promedios en Supabase

### 4. Supabase: Tabla `asistencia_zoom`

**Estructura:** `id (PK)` · `email` · `curso` · `fecha (date)` · `nombre` · `apellido` ·
`correo_electronico` · `instancias` · `porcentaje_asistencia` · `created_at`. Único real:
`asistencia_zoom_email_curso_fecha_key` sobre `(email, curso, fecha)` — no es la PK, por eso
el upsert necesita `?on_conflict=email,curso,fecha` explícito.

### 5. Supabase: Tabla `asistencia_promedio`

**Estructura:**
```sql
asistencia_promedio
├── id (PK)
├── email (UNIQUE) — estudiante
├── promedio_general (FLOAT) — % promedio de todas las clases
├── n_registros (INT) — cuántas clases tiene registradas
├── cursos (JSONB) — {"Curso A": 85.5, "Curso B": 92.0}
├── actualizado_en (TIMESTAMP) — última actualización
└── created_at (TIMESTAMP)
```

### 6. Panel de Riesgo: `tools/panel_riesgo_gui.py`

**Función:**
- Lee de `asistencia_promedio` cada vez que se actualiza
- Muestra "Asistencia %" en:
  - Tab **Jóvenes creaTIvos** → vista **"En Q10"**
  - Tab **Jóvenes creaTIvos** → vista **"match"**
  - Tab **Jóvenes creaTIvos** → vista **"atencion"**
  - Tab **Mujeres ROFÉ** → vista **"mujeres"**
  - Tab **Diferencias** → vista **"ambas"**

**Formato:**
- Si hay datos: `"85.5%"`
- Si no hay datos: `"aún no disponible"`

## Ejecución manual

```bash
# 1. Sincronizar registros crudos
python scripts/panel-datos/sync_asistencia_supabase.py [--dry-run]

# 2. Calcular promedios (solo si el paso 1 fue exitoso)
python scripts/panel-datos/calcular_asistencia_promedio.py

# 3. Abrir panel
python tools/panel_riesgo_gui.py
```

## Automatización (n8n) — ACTIVA (2026-07-14)

**Workflow:** `asistencia-zoom-diario` (id `qKBCgp1zFa3qeZAB`) — `n8n-workflows/asistencia-zoom-diario.json`

```
Schedule Trigger (00:00 diario)
    ↓
Execute Command: sync_asistencia_supabase.py
    ↓
¿Sync OK? (IF: stdout contiene "[OK] Sincronizacion completa")
    ├─ true  → Execute Command: calcular_asistencia_promedio.py
    │             ↓
    │         ¿Cálculo OK? (IF: stdout contiene "[OK] Sincronización completada")
    │             ├─ true  → OK (noOp)
    │             └─ false → Telegram "Error Calculo" (bot Q10, chat_id fijo de Samuel)
    └─ false → Telegram "Error Sync" (bot Q10, chat_id fijo de Samuel)
```

**Configuración:**
- **Trigger:** Schedule Trigger, medianoche (00:00), diario.
- **Acción:** Execute Command, mismo patrón que `q10-sync-supabase` (comando `cd ... && python ...`).
- **Camino de error:** cada IF revisa el `stdout` del script anterior; si no contiene el marcador de
  éxito, notifica por Telegram (mismo bot/credencial `Telegram Q10 Bot` de `q10-consolidacion`,
  `chat_id` fijo — no dinámico, porque este workflow no viene de un mensaje de Telegram).
- **Prueba manual (2026-07-14):** ejecución `id 170`, `status: success`, ~106s, los 6 nodos
  terminaron en el camino `OK` (sin disparar ningún error Telegram).

**Gotcha (API pública de n8n):** no existe endpoint para disparar una ejecución manual
("run now") de un workflow con Schedule Trigger — solo la UI (login de sesión) puede. La API
pública (`X-N8N-API-KEY`) tampoco expone `unarchive`; un workflow archivado no se puede
actualizar (`400 Cannot update an archived workflow`), solo borrar y recrear.

## Preguntas frecuentes

**P: ¿Por qué los promedios se calculan fuera de Supabase?**
A: Los datos en ZOOM-ASISTANCE están por evento/clase individual. Es más eficiente calcular promedios una vez por día en Python que cada vez que se consulta.

**P: ¿Qué pasa si un estudiante no tiene registros?**
A: No aparece en `asistencia_promedio`, y en el panel se muestra "aún no disponible".

**P: ¿Puedo actualizar manualmente?**
A: Sí, ejecuta el script Python en cualquier momento. Usa UPSERT, así que sobrescribe valores antiguos.

**P: ¿Dónde están los datos históricos?**
A: En Google Sheets (ZOOM-ASISTANCE). Supabase solo guarda los promedios actuales. Para histórico, consulta el Sheet.

## Gotchas

- ⚠️ **Emails en minúsculas:** El script convierte todos a minúsculas. Asegúrate que Q10/Avance usen el mismo formato.
- ⚠️ **Duplicados en Sheet:** El script deduplica por (email, curso, fecha). Eventos duplicados se contrarrestan automáticamente.
- ⚠️ **Cursos con nombres variados:** "Desarrollo Web" ≠ "desarrollo web". Los promedios por curso respetan la capitalización exacta.
- ⚠️ **Timestamps del mismo día colisionan tras el cast a `date` (2026-07-14):** la columna `Fecha`
  del Sheet trae fecha+hora (ej. `"2026-07-03 15:11"`), pero `asistencia_zoom.fecha` es tipo
  `date` (sin hora). Dos sesiones del mismo día con el mismo email+curso pero horas distintas
  colapsan a la misma fecha en Postgres → si ambas van en el mismo lote de upsert, Postgres
  responde `500` (`21000 ON CONFLICT DO UPDATE command cannot affect row a second time`) aunque
  Python no las vea como duplicadas (las cadenas de texto son distintas). Fix en
  `sync_asistencia_supabase.py`: truncar `fecha` a solo el día ANTES de deduplicar, y quedarse con
  el **mayor % de asistencia** (no la última fila) al colapsar dos sesiones reales del mismo día.
- ⚠️ **Basura de staff/pruebas en `ZOOM-ASISTANCE`:** cursos como "Prueba - Asistencia" y
  "Reunión con Katze" no son asistencia real de estudiantes (mismo hallazgo que el Gotcha de
  `reporte_puntaje.py` en `mapa-codigo.md`). `sync_asistencia_supabase.py` los excluye vía la
  constante `CURSOS_EXCLUIDOS`; `calcular_asistencia_promedio.py` **no** los excluye todavía (ver
  el ejemplo de `jovenescreativos@tocaunavida.org` con "Mi reunión"/"Entrevista NOVA" en sus
  cursos) — pendiente si se quiere limpiar también ahí.
- ⚠️ **`Prefer: resolution=upsert` no es válido en PostgREST** (era el bug que rompía el sync
  antes del fix de 2026-07-14) — los valores válidos son `resolution=merge-duplicates` /
  `resolution=ignore-duplicates`. Con `merge-duplicates` además hace falta `?on_conflict=...`
  si el conflicto no es sobre la PK de la tabla.

## Próximos pasos

1. ✅ Tabla creada en Supabase
2. ✅ Script de cálculo funcional
3. ✅ Panel actualizado para leer promedios
4. ✅ Sync de registros crudos a `asistencia_zoom` (`sync_asistencia_supabase.py`, 2026-07-14)
5. ✅ Cron n8n diario 00:00 activo (`asistencia-zoom-diario`, 2026-07-14)
6. ⏳ Configurar webhook Zoom en n8n para escritura en vivo a `ZOOM-ASISTANCE` (aparte del sync diario)
7. ⏳ Evaluar excluir `CURSOS_EXCLUIDOS` también en `calcular_asistencia_promedio.py`
8. ⏳ Limpiar las ~2 filas de staff que quedaron en `asistencia_zoom` de antes del fix (opcional)
