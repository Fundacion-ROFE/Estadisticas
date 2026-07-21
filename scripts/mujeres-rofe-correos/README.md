# Correos Mujeres ROFÉ v2 (Seguro + Parametrizado)

**Automatización de envíos masivos para Mujeres ROFÉ (últimos 3 años: 2024–2026)**

- **Seguridad**: credenciales SIEMPRE en variables de entorno (nunca en código)
- **Parametrización**: una plantilla, muchas campañas (JSON)
- **Robustez**: reintentos, registro de enviados, manejo de cuota diaria
- **PII solo en `tools/`**: nunca en `scripts/` (que sí va a git) — ver convención de privacidad en `CLAUDE.md`

---

## Estructura

```
scripts/mujeres-rofe-correos/            ← CÓDIGO (git)
├── enviar_campana.py                    # Envío (preview / piloto / masivo)
├── extraer_lista_mr_ultimos3anios.py    # Extracción Supabase + Excel → CSV
├── templates/email_v2_template.html     # Plantilla parametrizada ($VAR)
├── img/{banner,firma}.png               # Header/footer marca ROFÉ
├── campanas/mr_ultimos_3_anios.json     # Config de la campaña activa
└── run_piloto.py                        # Wrapper con getpass (no expone password)

tools/mujeres-rofe-correos/data/         ← PII (gitignoreado, NUNCA a GitHub)
├── lista_mr_ultimos_3_anios.csv         # 2.693 mujeres (nombre,correo,cohorte,fuente)
└── enviados_mr_ultimos_3_anios.csv      # Se genera al enviar (registro, reanudable)
```

---

## Cuenta remitente

```
Usuario: mujeres.rofe@tocaunavida.org
```

⚠ **No** `envios.mr@tocaunavida.org` — esa cuenta no acepta la contraseña de aplicación
disponible y falla con `535 Username and Password not accepted`.

La contraseña de aplicación (16 caracteres) NUNCA va en el código ni a git. Tres formas de
proveerla, de más a menos efímera:

1. **`run_piloto.py`** — la pide oculta con `getpass` (nada queda guardado). Ideal para envíos que
   corre una persona.
2. **Variables de PowerShell** por sesión:
   ```powershell
   $env:SMTP_USER     = "mujeres.rofe@tocaunavida.org"
   $env:SMTP_PASSWORD = "xxxxxxxxxxxxxxxx"
   $env:SMTP_HOST     = "smtp.gmail.com"
   ```
3. **`.env.local`** (raíz del repo, gitignoreado) — **autorizado por Samuel el 2026-07-15** para
   agilizar pruebas locales y permitir que el skill `/enviar-correo` dispare pilotos a su correo
   sin `getpass`. Claves: `SMTP_USER`/`SMTP_PASSWORD` (cuenta principal) y `SMTP_USER_2`/
   `SMTP_PASSWORD_2` (segunda cuenta). `enviar_campana.py` lee de `os.environ`, así que hay que
   cargar `.env.local` al entorno antes de invocarlo (patrón `cargar_env_local`). Al ser un
   secreto guardado, si la clave se expone (p. ej. se pega en un chat/log) hay que **revocarla y
   regenerarla** en https://myaccount.google.com/apppasswords.

---

## Origen de la lista (`mr_ultimos_3_anios`)

Supabase (`panel-datos-rofe`) **no tiene el histórico completo del programa MR** —
`courses.programa='mr'` solo existe para cohortes 2025 y 2026. Ver memoria
`project-supabase-mr-historico-gap` para el detalle. Por eso la lista se arma combinando:

1. **Supabase** (participants↔enrollments↔courses, programa=mr): 1.270 correos, cohortes reales.
2. **Excel `BD-Mujeres ROFÉ 2026 (2).xlsx`** (pestaña General, "Fecha de Creación"): 1.423
   correos adicionales — cubre 2024, que Supabase no tiene.

**Unión: 2.693 mujeres únicas.** Supabase gana si el correo aparece en ambas fuentes.

Para regenerar la lista (por ejemplo si Supabase ya tiene el histórico completo importado):

```powershell
cd scripts/mujeres-rofe-correos
python extraer_lista_mr_ultimos3anios.py
```

Requiere `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` en `.env.local` (raíz del repo). Si esa
key da `401 Unregistered API key`, está desactualizada tras la rotación post-incidente — pide
una nueva a quien administre el proyecto Supabase.

---

## Opt-out, log de campañas y rebotes (Supabase, desde 2026-07-15)

Tres tablas en `panel-datos-rofe` (Tareas 5 y 7 del plan de ejecución). Todas con **RLS
activada y sin política anon** — contienen/rozan datos sensibles, solo las lee/escribe el
backend con `SUPABASE_SERVICE_ROLE_KEY`; nunca se exponen a la cara pública del panel.

| Tabla | Columnas | Quién la escribe |
|---|---|---|
| `email_optout` | `email` (PK), `fecha`, `motivo` | Manual / futuro flujo de baja. Correos que pidieron **no** recibir campañas. |
| `campanas_enviadas` | `id`, `campana`, `fecha`, `enviados`, `fallidos`, `programa` | `enviar_campana.py` al terminar un envío/piloto. **Solo agregados — sin direcciones de correo.** |
| `email_bounces` | `email` (PK), `tipo`, `codigo`, `fecha`, `motivo` | `capturar_rebotes.py`. Rebotes detectados en el buzón. `tipo=hard` (5.x permanente) / `soft` (4.x temporal). |

- **`extraer_lista_mr_ultimos3anios.py`** ahora, al final, **excluye** de la unión las
  **supresiones**: `email_optout` (baja voluntaria) + `email_bounces` con `tipo=hard` (rebotes
  permanentes). Los `soft` NO se excluyen (buzón lleno / temporal). Aparece como `suprimidos=N`
  en su `RESUMEN`. Para dar de baja a alguien a mano:
  `insert into email_optout(email, motivo) values ('correo@x.com', 'motivo');` y regenerar la lista.
- **`enviar_campana.py`** inserta **una** fila resumen en `campanas_enviadas` al terminar
  (`--piloto` → `<id> (piloto)` con enviados=1; `--enviar` → total OK/fallidos). No sube correos
  individuales. Requiere `SUPABASE_URL`/`SUPABASE_SERVICE_ROLE_KEY` en `.env.local` (los carga
  solo; si faltan, avisa y sigue sin registrar — nunca hace fallar el envío).
- **`capturar_rebotes.py`** — lee por **IMAP** el buzón remitente (misma app-password de
  `.env.local`), busca los DSN de `mailer-daemon` desde una fecha, parsea las direcciones que
  rebotaron + su status SMTP, clasifica hard/soft y hace upsert en `email_bounces`. Además:
  - Vuelca la **foto completa** de rebotes (enriquecida con **nombre**, cruzando la pestaña
    `General` de la BD-Mujeres ROFÉ + `participants`) a la pestaña **`Rebotes`** del Sheet
    BD-Mujeres ROFÉ 2026 (`1ZsC4WyY26aOCEMrnZ_l8Tn-l69DB_0ADs5lnecaoEP8`) — así el equipo ve a
    quién actualizarle el correo. Columnas: Nombre · Correo · Tipo · Codigo · Fecha · Motivo
    (hard primero). Idempotente: reescribe la pestaña en cada corrida.
  - Detalle con PII → `tools/mujeres-rofe-correos/data/rebotes_YYYYMMDD.csv` (gitignoreado);
    a consola solo conteos.
  ```powershell
  python capturar_rebotes.py                     # últimos 30 días (Supabase + Sheet)
  python capturar_rebotes.py --desde 2026-07-14  # desde una fecha
  python capturar_rebotes.py --no-sheet          # no toca el Sheet
  python capturar_rebotes.py --dry-run           # no escribe nada
  ```
  Estado acumulado (2026-07-15): 61 hard (se excluyen de la lista) + 71 soft (buzón lleno,
  no se excluyen). Cron n8n **diario** 6:30 a.m.: `correos-rebotes-diario` (subido de
  semanal a diario el 2026-07-15 para detectar rebotes de campañas grandes al día
  siguiente, no esperar al lunes).
  - **Resaltado visual en Sheets (2026-07-15):** la pestaña `General` tiene una regla de
    formato condicional que pinta de **rojo** toda la fila cuando la columna AUXILIAR = FALSE
    (correo en Rebotes) — se recalcula sola, no requiere volver a correr nada.
  - **Marcador en Supabase (2026-07-15):** tabla `alertas_datos` (RLS + lectura pública, sin
    PII), fila `id='correos_mr_desactualizados'` con `activa`/`cantidad`/`detalle` — se
    actualiza en cada corrida con el total ACUMULADO de hard bounces. Fácil de consultar
    desde cualquier dashboard: `select * from alertas_datos where id='correos_mr_desactualizados'`.

---

## Uso

### 1. Preview (sin enviar, sin credenciales)

```powershell
cd scripts/mujeres-rofe-correos
python enviar_campana.py campanas/mr_ultimos_3_anios.json --preview
```

Abre `preview.html` en el navegador. Revisa: header, colores marca ROFÉ (#d6336c), botón CTA,
footer, responsive.

### 2. Piloto (un correo de prueba)

```powershell
python run_piloto.py
```

Pide la contraseña de forma oculta y envía a `samueldavidvida@gmail.com`. Ya validado el
2026-07-14 (llegó correctamente).

O manualmente:
```powershell
$env:SMTP_USER = "mujeres.rofe@tocaunavida.org"
$env:SMTP_PASSWORD = "..."
python enviar_campana.py campanas/mr_ultimos_3_anios.json --piloto CORREO@ejemplo.com
```

### 3. Envío masivo (2.693 mujeres)

```powershell
$env:SMTP_USER = "mujeres.rofe@tocaunavida.org"
$env:SMTP_PASSWORD = "..."
python enviar_campana.py campanas/mr_ultimos_3_anios.json --enviar
```

- Pide confirmación escrita (`ENVIAR 2693`).
- Lotes de 500, pausas entre lotes y entre correos.
- Con ~2.000 correos/día (Workspace) → **2 días** de envío.
- Si se corta, ejecuta el **mismo comando**: usa `enviados_mr_ultimos_3_anios.csv` para no
  reenviar a quien ya recibió.

**Ejecutado y completado el 2026-07-14.** Corrida original (12:54–14:05) cubrió 1.216 de
2.693; el resto se dividió en `lista_mr_parteA.csv` (738) y `lista_mr_parteB.csv` (739) y
se envió por separado (14:13–14:51). Total: **2.693/2.693 enviados, 0 fallos** (verificado
cruzando `enviados_mr_ultimos_3_anios.csv` + `enviados_mr_parteA.csv` + `enviados_mr_parteB.csv`
contra `lista_mr_ultimos_3_anios.csv` — cobertura 100%, sin duplicados).

---

## Nueva campaña (plantilla reutilizable)

1. Crear `campanas/<id>.json` (copiar `mr_ultimos_3_anios.json` y adaptar variables).
2. Crear `tools/mujeres-rofe-correos/data/lista_<id>.csv` con columnas `nombre,correo,cohorte`
   (o generarlo con un script de extracción como `extraer_lista_mr_ultimos3anios.py`).
3. `--preview` → `--piloto` → `--enviar`.

Variables disponibles en el HTML: `$ASUNTO`, `$TITULO_EVENTO`, `$PARRAFO_INTRO`,
`$PARRAFO_DESCRIPCION`, `$DATOS_EVENTO`, `$PARRAFO_CIERRE`, `$TEXTO_CTA`, `$URL_CTA`, `$FIRMA`,
y `$NOMBRE` (automático, por destinataria).

---

## Certificados personalizados (adjunto por destinataria)

`enviar_campana.py` no soporta adjuntos distintos por persona (solo imágenes inline iguales
para todos). Para casos como "42 certificados en un PDF de Canva, uno por página, hay que
mandarle a cada quien el suyo", usar `certificados/`:

```powershell
cd scripts/mujeres-rofe-correos/certificados
python preparar_certificados.py --dividir "RUTA\certificados.pdf"    # separa páginas + muestra texto
python preparar_certificados.py --emparejar --linea N                # cruza nombre → correo (BD-Mujeres ROFÉ)
# revisar tools/mujeres-rofe-correos/data/certificados/certificados_matches.csv (columna revisar)
python enviar_certificados.py ..\campanas\<campana>.json --piloto samueldavidvida@gmail.com
python enviar_certificados.py ..\campanas\<campana>.json --enviar
```

Requiere `pypdf` (`pip install pypdf`). El JSON de campaña puede declarar
`PLANTILLA_TEMPLATE` propia (ver `templates/email_certificado_template.html`, variante sin
banner de encabezado) igual que ya permite `IMG_BANNER`/`IMG_FIRMA`.

Detalle completo (gotchas de extracción de texto de Canva, matching difuso) en la entrada
2026-07-15 de `claude_sessions.md`.

---

## Seguridad — incidente resuelto

El script anterior (`Downloads/Correos-fast/enviar_correos.py`) tenía la contraseña SMTP
hardcodeada en el código. La versión de este directorio la lee **solo** de variables de
entorno. Si sigues usando el script viejo, bórrale esa línea y pásale `$env:SMTP_PASSWORD`.
