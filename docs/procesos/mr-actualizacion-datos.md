# MR — Actualización de datos (BD-Mujeres ROFÉ 2026)

**Estado:** Completado
**Última actualización:** 2026-07-08
**Procesos relacionados:** [[q10-consolidacion]] (mismo Service Account y patrón de subida) · [[mr-website]] (misma población MR; el website usa MongoDB propio, no sincronizado con esta BD) · [[panel-datos-etl]] (desde 2026-07-10 `sync_sociodemograficos_mr.py` lee el export xlsx de esta BD — pestañas `General` + `Inactivas` — hacia Supabase; es la única fuente de vivienda/estrato/estado_civil/nivel_estudio) · [[postulantes-mr-supabase]] (plan para llevar el universo completo de postulantes de esta BD a Supabase, no solo las matriculadas)

## Qué hace
Sincroniza la pestaña `General` de **BD-Mujeres ROFÉ 2026** con las respuestas del formulario
**"Actualización de datos MR2024"** (Google Form donde las mujeres actualizan su información de
contacto). Cruza por cédula, actualiza los campos que trae el formulario, agrega al final las
personas que no existen en la BD (con color para identificarlas) y deja una columna
`Fecha Actualización` con la fecha de la corrida en cada fila tocada.

## Disparador (Trigger)
Schedule diario en n8n (workflow `mr-actualizacion-datos`) → Execute Command → script Python.
**Desde 2026-07-08: diario 9:30 am America/Bogota** (antes 7:30 sin timezone = 6:30 Colombia en
default New York — nunca llegó a disparar porque n8n arranca ~8:45 con el inicio de sesión del PC;
n8n no recupera disparos perdidos).

## Flujo resumido
1. Lee `Respuestas de formulario 1` del Sheet fuente; deduplica por cédula (gana la respuesta con marca temporal más reciente).
2. Lee la pestaña `General` de la BD destino; indexa por cédula normalizada (solo dígitos).
3. Por cada respuesta con match: compara campo a campo (normalizado) y escribe **solo las celdas que cambian**; si la fila cambió, escribe la fecha de la corrida en `Fecha Actualización`.
4. Respuestas sin match en General → se **clasifican** antes de agregar (desde 2026-07-08):
   - Cédula en la pestaña `Inactivas` → **RETIRADA**: no se agrega, solo se reporta.
   - Match fuerte con otra fila de General/Inactivas (≥2 señales entre correo igual, celular igual,
     nombre exacto/contenido, cédula a distancia Levenshtein ≤2) o cédula = su propio celular →
     **POSIBLE TYPO** de cédula: no se agrega, se reporta el candidato para revisión humana.
   - Sin candidata → fila nueva al final con fondo naranja claro (realmente nueva).
5. Imprime `RESUMEN: ...` parseable para n8n (incluye `retiradas=` y `posibles_typos=`).

## Fuentes de datos / APIs usadas
- Google Sheets API (Service Account `q10-automatizacion@...`):
  - **Fuente (read):** `13a32oExVw64Scpo2YgnMjytXsIIMVNi07NvYoD8QYH0` · pestaña `Respuestas de formulario 1` (gid 252655091)
  - **Destino (write):** `1ZsC4WyY26aOCEMrnZ_l8Tn-l69DB_0ADs5lnecaoEP8` · pestaña `General` (gid 0)

## Destino de los datos
Pestaña `General` de BD-Mujeres ROFÉ 2026. Mapeo de columnas (form → General):

| Formulario                       | General                                                                                 |
| -------------------------------- | --------------------------------------------------------------------------------------- |
| Nombres + Apellidos              | D `Nombre Completo`                                                                     |
| Correo electrónico               | E `Correo` y H `Correo` (la BD tiene 2 columnas de correo)                              |
| Tipo de documento                | F (normalizado: `Cédula de Ciudadanía`→`cc`, `Cédula de extranjería`→`ce`, `Ppt`→`ppt`) |
| Número de Identificación         | G — **llave de cruce**, nunca se sobreescribe                                           |
| Celular                          | J `Celular` y K `Celular +57` (`57` + 10 dígitos)                                       |
| Ciudad                           | M `Ciudad`                                                                              |
| Departamento                     | N `departamento con cc`                                                                 |
| ¿Tienes emprendimiento? + ¿Cuál? | S `Emprendimiento` (`No` → `N/A`)                                                       |
| ¿Cuáles son tus redes sociales?  | — sin columna destino en General, se ignora                                             |
| (fila tocada en la corrida)      | AL `Fecha Actualización` (dd/mm/yyyy, fecha de la corrida)                              |

## Decisiones de diseño clave
- **Llave de cruce = cédula** (col G): 5,109 únicas de 5,110 filas en General; el correo no sirve (hay 2 columnas y typos).
- **Se actualiza todo lo que trae el form** (decisión de Samuel 2026-07-07), incluidos nombre y tipo de documento.
- **Fecha = fecha de la corrida** (no la marca temporal del form) — decisión de Samuel.
- **Sin match → fila nueva al final con color** naranja claro (decisión de Samuel), pero **solo si es realmente nueva** (decisión de Samuel 2026-07-08): las retiradas (pestaña `Inactivas`) y los posibles typos de cédula no se agregan — solo se reportan en la salida. Una sola señal (p.ej. celular compartido) NO basta para declarar typo: se exigen ≥2 señales.
- **Los posibles typos no se corrigen automáticamente**: a veces el typo está en el form (Darinka `1048488951` vs BD `1047488951`) y a veces en la BD (Paula Bolaños: BD tiene `11433751119`, 11 dígitos — inválida; el form trae la de 10). Decide un humano.
- **Idempotente:** solo escribe celdas cuyo valor normalizado difiere; una segunda corrida sin respuestas nuevas no toca nada (y no re-fecha filas).
- Valores nuevos vacíos **nunca** sobreescriben un dato existente.

## Gotchas / Limitaciones conocidas
- La fila 1 de General tiene una celda basura en AK (`5110`, parece un conteo) — la columna de fecha se escribe en AL y se localiza por su header, no por índice fijo.
- 18 mujeres respondieron el form más de una vez → gana la más reciente por marca temporal.
- ~38 respuestas del form no traen cédula válida → se reportan como omitidas.
- La pestaña `HerpowerED` de la BD parece copia de `General` — este proceso NO la toca.
- **Comparación insensible a tildes:** el form llega sin acentos; sin esto, la 1ª corrida "actualizaba" 937 celdas reemplazando `Sofía`→`Sofia` (degradación, no información). Con la comparación unaccent bajó a 813 celdas reales.
- Los typos de cédula del form ya se detectan automáticamente (ver flujo paso 4), pero la detección exige ≥2 señales: un homónimo sin correo/celular coincidente entraría como fila nueva.
- La pestaña `Inactivas` tiene la cédula en col E (`Numero de identificacion`), nombre en col C (`Completo`), celular en F y correo en G — estructura distinta a General.

## Corrida inicial (backfill 2026-07-07)
`RESUMEN: respuestas=387 unicas=332 filas_actualizadas=286 sin_cambios=23 nuevas=24 omitidas=37 estado=exito`
Filas nuevas 5112–5135 con fondo naranja. Re-corrida inmediata verificada: 0 cambios (idempotente).

## Limpieza y clasificación (2026-07-08)
Análisis de las 24 filas naranjas del backfill: **7 retiradas** (en `Inactivas`) — filas eliminadas
de General —, **13 posibles typos de cédula** (mismo nombre + correo/celular igual que una fila
existente) y **4 realmente nuevas**. El script ahora clasifica esto solo; dry-run verificado:
`RESUMEN: ... nuevas=0 retiradas=7 posibles_typos=0 omitidas=37 estado=dry-run` (los typos siguen
naranjas en el Sheet hasta revisión humana, por eso no aparecen como typos en la corrida).
Detalle de los 13 typos en la salida de la sesión 2026-07-08 de `claude_sessions.md`.

## Workflow n8n
- **Nombre/ID:** `mr-actualizacion-datos` / `LgkDbNPERYgKMrYj` — **activo**, schedule diario 9:30 am America/Bogota.
- Nodos: Schedule → Execute Command (script) → IF `estado=exito` → OK / Stop-and-Error (camino de error explícito).
- Export: `n8n-workflows/mr-actualizacion-datos.json`.

## Pendiente / Próximos pasos
- Revisión humana de las 13 filas naranjas de **posible typo de cédula** que siguen en General
  (corregir la cédula en la fila original y borrar la naranja, o al revés si el typo está en la BD).
- Las 4 filas naranjas restantes son mujeres realmente nuevas — confirmar si deben quedarse.
- Si el equipo quiere aviso de errores por Telegram, añadir chat_id de admin al camino de error.
