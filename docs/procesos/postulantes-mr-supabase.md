# Postulantes Mujeres ROFÉ → Supabase (unificación de fuentes)

**Estado:** Fases 0-3 completadas + fusión de 36/52 duplicados ejecutada (2026-07-22). 16 casos
discordantes (ambas filas de `General`) pendientes de revisión humana. Fases 4-5 pendientes.
**Última actualización:** 2026-07-22
**Procesos relacionados:** [[panel-datos-etl]] · [[mr-actualizacion-datos]] · [[panel-riesgo-mejora]]

## Qué hace (visión)
Hoy Supabase (`participants`) solo contiene a quienes **llegaron a matricularse en Q10**
(regla de oro repetida en todo el proyecto: Q10 es la fuente de verdad de quién existe, ver
[[convenciones#Supabase `participants` = solo matriculados en Q10]]). El universo real de
mujeres que ha pasado por la fundación es mucho más grande: el Sheet **BD-Mujeres ROFÉ**
(id `1ZsC4WyY26aOCEMrnZ_l8Tn-l69DB_0ADs5lnecaoEP8`, pestaña `General`) tiene **5.126 cédulas**
de postulantes/candidatas, de las cuales Supabase solo refleja **282** (las que sí llegaron a
tener un curso). El resto vive únicamente en el Sheet — invisible para cualquier búsqueda
"¿esta persona está en nuestros sistemas?" que solo mire Supabase.

**Objetivo:** una tabla nueva en Supabase (`postulantes_mr`) con el universo completo de
postulantes/candidatas, enlazada opcionalmente a `participants` cuando la cédula sí llegó a
matricularse — para poder responder "¿está en algún sistema nuestro?" con una sola consulta,
sin romper la semántica de matriculados que ya usan todas las vistas del dashboard.

## Por qué ahora
Origen: Sandra pidió verificar si 8 mujeres (lista de un formulario externo) estaban en la
base de datos. Solo 2 estaban matriculadas en Q10/Supabase; 1 más apareció en el Sheet
Mujeres ROFÉ (con typo de cédula/correo desactualizado — mismo celular, cédula off-by-one);
las otras 5 no aparecieron en ningún lado. La búsqueda requirió conectarse manualmente al
Sheet vía gspread porque Supabase, por diseño, no cubre postulantes sin matrícula — evidenció
que este tipo de consulta ("¿la conocemos?") es recurrente y hoy no tiene una sola fuente.

## Decisión de diseño clave — NO tocar `participants`
`participants` alimenta ~15 vistas agregadas (`cohorte_ingresos`, `v_programa_stats`,
`v_cohorte_estudiantes`, etc.) que asumen "cada fila tiene una matrícula real". Meter ahí las
~4.850 postulantes sin curso (5.126 − 282) inflaría/rompería esos agregados canónicos ("Ingresados
832", etc.). En vez de eso: tabla paralela `postulantes_mr`, con `participant_id` nullable
como puente. Mismo principio que ya siguen `emoflow_ingresos` (participant_id NULL si no hay
match) y `sync_sociodemograficos_mr.py` ("no crea participantes: las mujeres sin matrícula se
reportan, no se cargan").

## Plan por fases

### Fase 0 — Decisiones confirmadas (2026-07-22)
- [x] **Auditar Cursos/Cursos%/Plataforma MR antes de decidir alcance.** Resultado: SÍ aportan
      cédulas nuevas — 193 exclusivas (7 en Cursos, 140 en Cursos%, 55 en Plataforma MR, con
      overlap entre ellas) que no están en General∪Inactivas (universo pasa de 5.159 a 5.352
      antes de excluir perfiles de prueba). No es basura: nombres/correos reales, y Plataforma MR
      trae socio-demografía usable (mismo formato español que `sync_sociodemograficos_mr.py`
      mapea). Decisión: **incluir las 5 pestañas** como fuente. `HerpowerED` se descarta (copia
      de General, ver [[mr-actualizacion-datos]]).
- [x] **Import único por ahora**, no encadenado a n8n `sociodemograficos-semanal` todavía
      (queda como Fase 4 pendiente — candidato natural sigue siendo ese workflow).
- [x] **PII sin `anon`** — mismo criterio que `emoflow_ingresos`/`email_bounces`: RLS
      habilitado + `REVOKE ALL FROM anon, authenticated` en el mismo statement de creación,
      verificado con el anon key real (401, 0 filas) tanto antes como después de cargar datos.

### Fase 1 — Esquema ✅ (2026-07-22)
Migración `docs/migrations/003_postulantes_mr.sql`, tabla `postulantes_mr`:
- `id uuid PK`, `cedula varchar unique` (norm_id, solo dígitos), `nombre`, `email`, `celular`,
  `ciudad`, `estado` (texto crudo de la columna `Estado` del Sheet), `fecha_creacion` (texto
  crudo — formatos inconsistentes entre pestañas, no se castea a DATE).
- Campos sociodemográficos reusando los enums ya existentes en `participants`
  (`nivel_estudio_type`, `estado_civil_type`, `vivienda_type`, `estrato int`) — mismo
  mapeo por substring que ya usa `sync_sociodemograficos_mr.py` (`MAPA_NIVEL`, `MAPA_CIVIL`,
  `MAPA_VIVIENDA`).
- `fuente_pestana` (`general`/`inactivas`/`cursos`/`cursos_pct`/`plataforma_mr`) — ampliado
  respecto al plan original tras la auditoría de Fase 0 (ver arriba).
- `participant_id uuid NULL FK → participants.id`.
- `created_at`/`updated_at`.
- RLS: `ENABLE ROW LEVEL SECURITY` + `REVOKE ALL FROM anon, authenticated` en el mismo
  statement que crea la tabla (regla del incidente de julio, ver [[convenciones#⚠️ Supabase:
  una VISTA con PII se expone a `anon` aunque nunca le des GRANT]]). Aplicada vía Supabase MCP
  `apply_migration`.

### Fase 2 — Script ETL (`sync_postulantes_mr.py`) ✅ (2026-07-22)
- Reutiliza la conexión/credenciales de `sync_sociodemograficos_mr.py` (mismo Sheet, mismo
  Service Account, misma ruta de credenciales).
- Lee las 5 pestañas con precedencia General > Inactivas > Plataforma MR > Cursos > Cursos%
  (primera fuente que trae la cédula gana — más completa primero).
- Cruce con `participants.q10_id` para rellenar `participant_id` cuando exista.
- Detección de typos de cédula: **no es la fuerza bruta O(n²) del plan original** — con
  ~5.300 filas eso generaba ~14M comparaciones Y, peor, `items[i+1:]` recreaba una slice de
  lista en cada iteración externa (O(n²) en memoria transitoria, RSS llegó a 2 GB antes de
  corregirlo). Implementación final: bloqueo por correo/celular exacto, por conjunto de
  tokens de nombre, y por vecindad numérica de cédula ordenada (ventana=8) — genera pares
  candidatos baratos, y solo ahí se aplica el criterio completo de ≥2 señales. Reporta a
  `tools/postulantes_mr_report_<fecha>.json` (PII), nunca corrige sola.
- Upsert idempotente por `cedula`, mismo patrón de lotes (`LOTE=500`) que los demás syncs.
- Reutiliza `tools/exclusiones_prueba.json` para descartar perfiles de prueba (1 excluido en
  la corrida real).

### Fase 3 — Verificación ✅ (2026-07-22)
- Cuadre confirmado por SQL: 5.351 filas totales (general=5.125, inactivas=33,
  plataforma_mr=55, cursos=1, cursos_pct=137 tras deduplicar por precedencia), 557 con
  `participant_id`.
- Anon key verificado ANTES y DESPUÉS de cargar datos reales: `401 permission denied`, 0 filas.
- El reporte de posibles typos (52 detectados) **sí marcó el caso real Gina Gleisy**
  (`22519536` / `22519636`, mismo nombre exacto + cédula a distancia Levenshtein 1) — el caso
  que originó todo este proceso.

### Fase 3b — Fusión de duplicados ✅ (2026-07-22, mismo día)
Criterio acordado: la cédula de `General` gana cuando compite contra otra pestaña (más
confiable — es la fuente primaria de demografía). De los 52 pares:
- **36 pares** tenían una fila de `General` y otra de otra pestaña → **fusionados y borrados**:
  se copiaron a la fila de `General` los campos que le faltaban (10 pares aportaron datos
  reales: `participant_id` o `fecha_creacion`) y se borró la fila duplicada. `fuente_pestana`
  de la fila resultante queda como `"general+<origen>"` para trazabilidad. Tabla: 5.351 → 5.315
  filas. Respaldo completo de las filas borradas en
  `tools/postulantes_mr_fusionados_backup_*.json` (PII, gitignoreado) antes de borrar.
- **16 pares** tenían AMBAS filas ya en `General` → **no se tocaron**. Ahí "General gana" no
  aplica (empate de fuente) — quedan en la tabla tal cual, pendientes de que un humano decida
  cuál cédula es la correcta. Detalle completo en `Downloads/postulantes_mr_disonancias_general.xlsx`.
  **Confirmado 2026-07-23 con Samuel: se documentan y se dejan así mientras tanto — no se
  fuerza ninguna decisión automática sobre ellos.** Ambas cédulas de cada par siguen activas
  y consultables (ej. vía `v_persona_360`) hasta que alguien del equipo los revise uno a uno.
- Verificado tras la fusión: cédula sigue siendo única (5.315 filas = 5.315 cédulas distintas),
  anon key sigue en 401.
- Gotcha encontrado: `fuente_pestana` era `VARCHAR(20)`, insuficiente para
  `"general+plataforma_mr"` (21 caracteres) → migración `widen_postulantes_mr_fuente_pestana`
  (ampliada a `VARCHAR(40)`, aditiva y segura). El error interrumpió la fusión a la mitad (15/36
  pares); como el script relee el estado real de la tabla en cada corrida, simplemente se
  volvió a ejecutar y completó los 21 restantes sin duplicar nada.

### Fase 4 — Automatización
- Nuevo nodo en el workflow n8n `sociodemograficos-semanal` (activo, lunes 6:00 COT), después
  del sync existente — reutiliza la misma lectura del Sheet, sin carga extra.
- Camino de error explícito, alerta Telegram no bloqueante (mismo criterio que el resto de MR).

### Fase 5 — Herramienta de búsqueda unificada ✅ (2026-07-23, como vista SQL)
Resuelta con `v_persona_360` (`docs/migrations/008_v_persona_360.sql`) en vez del script
`tools/buscar_persona.py` originalmente planeado — más simple y sin duplicar lógica de cruce
en Python: une por cédula `participants` + `postulantes_mr` + `postulantes_jc` +
`emoflow_ingresos` + `asistencia_promedio` en una sola fila, consultable con
`GET /v_persona_360?cedula=eq.<cedula>` (solo `service_role`). Cubre las 8.100 identidades
conocidas por cualquiera de los 5 sistemas. Detalle en [[supabase-estructura]]. Sigue abierto
integrarla como botón/tab en [[panel-riesgo-mejora]] (haría la llamada REST en vez de repetir
los cruces en Python).

## Gotchas / Limitaciones conocidas
- El correo **no sirve como llave de cruce** para detectar duplicados — ya documentado en
  [[mr-actualizacion-datos]]: hay 2 columnas de correo en el Sheet y typos frecuentes. La única
  llave confiable es la cédula normalizada, con `senales_match` como red de seguridad para
  typos de un dígito.
- El Sheet tiene 14 pestañas en total; auditoría Fase 0 confirmó que `Cursos`/`Cursos%`/
  `Plataforma MR` SÍ aportan 193 cédulas exclusivas (no solapan del todo con General∪Inactivas
  como se sospechaba) — las 5 pestañas quedaron en el alcance final. `HerpowerED` sigue
  descartada (copia de General).
- **`Supa.get_todo()` sin `offset += page` es un loop infinito silencioso, no un cuelgue de
  red.** Cada iteración vuelve a pedir offset=0; la API responde en <1s cada vez (parece que
  "está funcionando") pero nunca cumple `len(lote) < page` y jamás termina — `filas.extend()`
  acumula duplicados para siempre y el RSS crece sin límite (se vio pasar de cientos de MB a
  2 GB). Se manifestó exactamente igual que un cuelgue de proxy corporativo (sin excepción,
  sin traceback, "colgado" indefinidamente) y costó ~30 min de diagnóstico —incluyendo probar
  `socket.setdefaulttimeout()`, revisar conexiones TCP con `Get-NetTCPConnection`, sospechar
  el MITM corporativo— antes de aislar la causa real con logging por iteración dentro del
  método. **Lección para cualquier script con este patrón de paginación:** si "se cuelga" sin
  ningún error, lo primero es loggear el `offset` en cada vuelta, no asumir que es la red.
  Ver detalle también en [[mapa-codigo]].
- **`items[i+1:]` dentro de un `for` sobre una lista grande es O(n²) en tiempo Y memoria** —
  cada iteración externa crea una slice nueva. La primera versión de `detectar_typos()` lo
  hacía sobre ~5.300 filas y también llegó a 2 GB de RSS antes de reemplazarse por bloqueo
  (correo/celular exacto, tokens de nombre, vecindad de cédula ordenada). Nunca slicear una
  lista grande dentro de su propio loop externo.

## Pendiente / Próximos pasos
- [x] Fase 0: resolver las 3 preguntas con Samuel (2026-07-22).
- [x] Fase 1: migración del esquema.
- [x] Fase 2: script `sync_postulantes_mr.py`.
- [x] Fase 3: verificación de cuadre + privacidad.
- [ ] Fase 4: encadenar a n8n `sociodemograficos-semanal` (por ahora corrida manual única).
- [x] Fase 5: herramienta de búsqueda unificada — `v_persona_360` (vista SQL, no script).
