---
name: enviar-correo
description: Convierte una petición en lenguaje natural ("mándale un recordatorio a las de Bogotá que no completaron el curso") en una campaña de correos Mujeres ROFÉ, orquestando los scripts existentes (enviar_campana.py) hasta preview y piloto. NO reimplementa el envío. Invocar con /enviar-correo.
user-invocable: true
---

# Skill: /enviar-correo

Orquesta el envío de correos de **Mujeres ROFÉ** a partir de una petición en lenguaje natural.
NO reimplementa nada: llama a `scripts/mujeres-rofe-correos/enviar_campana.py` y compañía. El
proceso completo está en [[correos-mujeres-rofe]] y `scripts/mujeres-rofe-correos/README.md`.

Petición del usuario: **$ARGUMENTS**

---

## Reglas de seguridad (INVIOLABLES — copiadas textuales del plan de ejecución)

> **Regla 1. Nunca imprimas, loguees ni guardes `SMTP_PASSWORD` ni ninguna clave.** Las claves se
> piden con `getpass` en el momento (ver patrón en `scripts/mujeres-rofe-correos/run_piloto.py`).

> **Regla 3. Nunca ejecutes `--enviar` (envío masivo) sin que Samuel lo confirme explícitamente
> en la conversación.** `--preview` y `--piloto` sí puedes correrlos.

### Excepción autorizada por Samuel (2026-07-15)

Samuel autorizó guardar las credenciales SMTP en `.env.local` (raíz, gitignoreado, local) para
agilizar las pruebas, y dio **permiso permanente para que TÚ dispares pilotos a su correo personal
`samueldavidvida@gmail.com`**. Esto supersede la parte de "getpass en el momento" de la Regla 1
SOLO para este uso local. Lo que sigue intacto de la Regla 1: **nunca imprimas el valor de la clave**
(ni `echo`/`cat`/`print` del valor), y **nunca la envíes a git** (`.env.local` está gitignoreado).
El envío masivo (`--enviar`) sigue necesitando el OK explícito de la Regla 3.

Consecuencias prácticas de estas reglas para este skill:

- **El preview lo corres tú** — no toca credenciales ni envía nada.
- **El piloto a `samueldavidvida@gmail.com` lo corres tú** cargando las credenciales de
  `.env.local` al entorno (patrón `cargar_env_local`), sin imprimir el valor. Si el piloto es a
  **otro** correo, o si `.env.local` no tiene `SMTP_PASSWORD`, entrégale el comando a Samuel para
  que lo corra él vía `getpass` (`run_piloto.py`).
- **El envío masivo lo dispara Samuel** tras su segundo OK explícito (Regla 3) — nunca tú por
  iniciativa propia.
- **PII solo en `tools/`** (gitignoreado). Las listas con nombre+correo JAMÁS van a `docs/` ni a
  `scripts/`. Los JSON de campaña (sin PII: asunto, párrafos, enlaces) sí viven en
  `scripts/mujeres-rofe-correos/campanas/`.

---

## Flujo obligatorio (seguir en orden; no saltarse pasos)

### Paso a — Interpretar la petición → filtros de lista

De la petición en lenguaje natural, extrae:

- **Programa:** por ahora este skill cubre **Mujeres ROFÉ** (`programa=mr`). Si la petición es de
  Jóvenes creaTIvos u otro programa, DETENTE y avisa a Samuel — la generalización a JC está
  explícitamente fuera de alcance en el plan.
- **Ciudad** (si la piden): ej. "las de Bogotá" → filtro por ciudad.
- **Estado del curso** (si lo piden): ej. "que no completaron" → avance < 100.
- **Contenido del correo:** asunto, título del evento, cuerpo, fecha/hora, enlace, CTA.

Si algo del contenido es ambiguo o falta (ej. no dan fecha ni enlace del evento), **pregunta a
Samuel antes de continuar** — no inventes datos del evento.

### Paso b — Generar/filtrar la lista → SIEMPRE a `tools/`

La lista final debe quedar en:
`tools/mujeres-rofe-correos/data/lista_<ID>.csv` con columnas `nombre,correo,cohorte`
(donde `<ID>` es el `ID` de la campaña del Paso c). **Nunca en `docs/` ni `scripts/`.**

Dos caminos, según la petición:

1. **Lista completa MR (últimos 3 años), sin filtro de ciudad/estado:**
   ```powershell
   cd scripts/mujeres-rofe-correos
   python extraer_lista_mr_ultimos3anios.py
   ```
   Genera `tools/mujeres-rofe-correos/data/lista_mr_ultimos_3_anios.csv`. Copia/renombra ese CSV a
   `lista_<ID>.csv` si tu campaña usa otro `ID`.

2. **Subconjunto filtrado (ciudad y/o estado del curso):** parte de un CSV existente o consulta
   Supabase con la `SERVICE_ROLE_KEY` de `.env.local` (patrón de la clase `Supa` en
   `extraer_lista_mr_ultimos3anios.py` — reutilízalo, no lo reescribas desde cero). Fuentes de los
   filtros en Supabase: `participants.ciudad` / `participants.grupo_ciudad` (ciudad),
   `enrollments.porcentaje_avance` vía `courses.programa='mr'` (estado del curso). Escribe el
   resultado filtrado a `tools/mujeres-rofe-correos/data/lista_<ID>.csv` con las 3 columnas.

   > NOTA de cobertura: Supabase solo tiene el histórico MR de 2025/2026
   > (ver [[project-supabase-mr-historico-gap]]). Para campañas que deban alcanzar 2024 hacia
   > atrás, la fuente completa es `extraer_lista_mr_ultimos3anios.py` (combina Supabase + Excel).
   > Avísale a Samuel qué cohortes cubre la lista que generaste.

Reporta a Samuel cuántos destinatarios quedaron y de qué fuente/cohortes.

> Recuerda: preview y piloto **no leen** la lista (`--preview` usa datos demo; `--piloto` envía a
> un solo correo). La lista solo se consume en `--enviar`. Aun así, genérala en este paso para que
> el envío masivo posterior de Samuel no requiera trabajo manual.

### Paso c — Armar el JSON de campaña (esquema existente, NO inventar campos)

Copia el esquema de un JSON de campaña existente
(`scripts/mujeres-rofe-correos/campanas/mr_ultimos_3_anios.json`) y escribe uno nuevo en
`scripts/mujeres-rofe-correos/campanas/<ID>.json`. Campos del esquema (todos string; usa EXACTAMENTE
estas claves, no agregues ni renombres):

```json
{
  "ID": "identificador_corto_sin_espacios",
  "ASUNTO": "…",
  "TITULO_EVENTO": "…",
  "PARRAFO_INTRO": "… (admite HTML inline: <strong>, <a href>)",
  "PARRAFO_DESCRIPCION": "…",
  "DATOS_EVENTO": "<strong>Fecha:</strong> … <br><strong>Hora:</strong> … <br>…",
  "PARRAFO_CIERRE": "…",
  "TEXTO_CTA": "…",
  "URL_CTA": "https://…",
  "FIRMA": "Equipo Mujeres ROFÉ"
}
```

- `ID` debe coincidir con el `lista_<ID>.csv` del Paso b (así `enviar_campana.py` los cruza solo).
- `$NOMBRE` se rellena automáticamente por destinataria — no lo pongas en el JSON.
- Genera el JSON con la herramienta de escritura de archivos; **nunca pidas a Samuel que lo edite
  a mano** (ese es justamente el criterio de aceptación del skill).

### Paso d — Preview (LO CORRES TÚ)

```powershell
cd scripts/mujeres-rofe-correos
python enviar_campana.py campanas/<ID>.json --preview
```

Genera `preview.html`. Muéstraselo a Samuel (abre/describe el HTML: header, colores marca ROFÉ
`#d6336c`, botón CTA, cuerpo, footer). Pide su OK antes de seguir.

### Paso e — Piloto (envía UN correo de prueba)

El piloto envía UN correo de prueba a `samueldavidvida@gmail.com`.

**Si el piloto es a `samueldavidvida@gmail.com` (permiso permanente de Samuel):** lo corres tú,
cargando `.env.local` al entorno sin imprimir la clave. Patrón verificado:

```bash
cd scripts/mujeres-rofe-correos
python -c "
import os, sys, subprocess
from pathlib import Path
for line in open(Path('../../.env.local').resolve(), encoding='utf-8'):
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1); os.environ.setdefault(k.strip(), v.strip())
sys.exit(subprocess.call([sys.executable, 'enviar_campana.py', 'campanas/<ID>.json', '--piloto', 'samueldavidvida@gmail.com'], env=os.environ))
"
```

**Si el piloto es a otro correo, o `.env.local` no tiene `SMTP_PASSWORD`:** entrégale el comando a
Samuel para que lo corra él con getpass (nunca tecleas tú la clave):

```powershell
cd scripts/mujeres-rofe-correos
python run_piloto.py campanas/<ID>.json
```

Verifica el resultado leyendo `tools/mujeres-rofe-correos/data/enviados_<ID>.csv` (última fila =
piloto, estado OK). Pide OK de Samuel de que el correo llegó bien antes de seguir.

### Paso f — Envío masivo (SOLO con segundo OK explícito — Regla 3)

**No hagas esto tú.** Solo cuando Samuel lo confirme **explícitamente en la conversación** (segundo
OK, distinto al del piloto), entrégale el comando para que lo corra él:

```powershell
cd scripts/mujeres-rofe-correos
python enviar_campana.py campanas/<ID>.json --enviar
```

El script pide escribir `ENVIAR <N>` como confirmación adicional — eso lo teclea Samuel, no tú.
Cuando termine, resume desde `enviados_<ID>.csv`: cuántos OK, cuántos ERROR/CUOTA, dónde quedó el
registro.

---

## Qué NO hacer

- **No** dupliques la lógica de envío SMTP dentro del skill — siempre a través de
  `enviar_campana.py` / `run_piloto.py`.
- **No** toques `enviar_campana.py`.
- **No** corras `--enviar` por tu cuenta ni manejes la contraseña SMTP (Reglas 1 y 3).
- **No** escribas listas con PII fuera de `tools/`.
- **No** generalices a otros programas (JC) sin instrucción explícita de Samuel.

## Criterio de que el skill funcionó

`/enviar-correo` llegó hasta el piloto (correo de prueba a Samuel) **sin que nadie editara el JSON
de campaña a mano**. El envío masivo real NO es parte del criterio — lo dispara Samuel cuando
quiera.
