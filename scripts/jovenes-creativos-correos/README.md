# Correos Jóvenes creaTIvos (v1 — calcado de Correos Mujeres ROFÉ)

**Envío parametrizado de correos para Jóvenes creaTIvos**, mismo patrón que
`scripts/mujeres-rofe-correos/` (código independiente, no compartido — cada programa tiene su
propia cuenta, plantilla e imágenes).

- **Seguridad**: credenciales SIEMPRE en variables de entorno (nunca en código)
- **Parametrización**: una plantilla, muchas campañas (JSON)
- **PII solo en `tools/jovenes-creativos-correos/`**: nunca en `scripts/` (que sí va a git)

---

## Estructura

```
scripts/jovenes-creativos-correos/          ← CÓDIGO (git)
├── enviar_campana.py                       # Envío (preview / piloto / masivo)
├── templates/email_v2_template_jc.html     # Plantilla parametrizada ($VAR), paleta azul #406C9E
├── img/header.jpg                          # Banner (1200x300, misma imagen que el header.png,
│                                            #   en jpg para pesar menos en el correo)
└── campanas/recordatorio_charla_ejemplo.json  # Ejemplo (contenido de una charla ya pasada,
                                                #   solo para validar que la plantilla renderiza)

tools/jovenes-creativos-correos/data/       ← PII (gitignoreado, NUNCA a GitHub)
├── lista_<ID>.csv                          # Se crea a mano por campaña (nombre,correo,cohorte)
└── enviados_<ID>.csv                       # Se genera al enviar (registro, reanudable)
```

---

## Cuenta remitente

```
Usuario: comunicaciones@tocaunavida.org
```

Misma cuenta que ya usan [[zoom-asistencia]] / [[zoom-youtube]] como host. Contraseña de
aplicación en `.env.local` (raíz del repo, gitignoreado): `SMTP_USER_JC` / `SMTP_PASSWORD_JC`.
Login SMTP verificado el 2026-07-22.

---

## Uso

### 1. Preview (sin enviar, sin credenciales)

```powershell
cd scripts/jovenes-creativos-correos
python enviar_campana.py campanas/<ID>.json --preview
```

### 2. Piloto (un correo de prueba)

```powershell
python enviar_campana.py campanas/<ID>.json --piloto CORREO@ejemplo.com
```

### 3. Envío masivo

```powershell
python enviar_campana.py campanas/<ID>.json --enviar
```

Pide confirmación escrita (`ENVIAR <N>`). Reanudable vía `enviados_<ID>.csv`.

**Antes de correr `--enviar` a un `ID` que ya se usó**: si el destino es el mismo grupo en un día
distinto (recordatorio diario), usa un `ID` nuevo por día — ver el gotcha documentado en
`scripts/mujeres-rofe-correos/README.md` y `docs/convenciones.md` (aplica igual aquí:
`enviados_<ID>.csv` salta a quien ya está `OK` para ese ID).

---

## Diferencias con la versión de Mujeres ROFÉ

- **Sin imagen de firma/footer** (`IMG_FIRMA`): JC solo tiene banner por ahora. Si se agrega una
  firma más adelante, replicar el patrón `cid:firma` de `mujeres-rofe-correos/enviar_campana.py`.
- **Captura de rebotes** (`capturar_rebotes.py`, calcado del de MR): lee por IMAP el buzón
  `soporte@tocaunavida.org` (`SMTP_USER_JC`/`SMTP_PASSWORD_JC` en `.env.local`), clasifica
  hard/soft, hace upsert en la MISMA tabla `email_bounces` (columna `programa` no distingue,
  pero las direcciones JC/MR no se solapan) y vuelca la foto a la pestaña `Rebotes` del Sheet
  `RebotesJC` (`1ACj0Dp-xv-f-NByfbyZLW8_h4ba1Bmb7aX7OUT6FKcI`), coloreada hard=rojo/soft=amarillo
  igual que MR. Marcador propio en `alertas_datos` (`id='correos_jc_desactualizados'`, separado
  del de MR). **Enganchado al cron n8n `correos-rebotes-diario` el 2026-07-29** (rama paralela a
  la de MR, mismo workflow) — antes de esa fecha el script existía pero nunca se había corrido
  en automático. **Tolerancia de soft bounces (2026-07-29, mismo umbral que MR):** un correo que
  rebota soft `UMBRAL_SOFT_A_HARD = 4` veces o más dentro de la ventana de 30 días se promueve
  a hard automáticamente (columna `veces_soft` en `email_bounces`, migración
  `028_email_bounces_veces_soft_APLICADA.sql`, compartida con MR). Primera corrida real
  (2026-07-29) ya promovió 4 correos por reincidencia. JC no tiene todavía un "sistema de
  actualización de datos" equivalente al de MR (`actualizar_bd_mr.py`), así que por ahora no hay
  liberación automática cuando alguien actualiza su correo — construir cuando exista ese flujo.
- **Sin lista real todavía**: `campanas/recordatorio_charla_ejemplo.json` es solo para validar la
  plantilla (contenido de una charla de mayo ya pasada). Falta decidir la fuente de la lista de
  destinatarios JC (¿Supabase `participants` con `programa=jc`? — confirmar con Samuel antes del
  primer envío real).

---

## Seguimiento de rebotes por ciudad (demo, 2026-08-19)

`seguimiento_rebotes_ciudad.py` — cruza `email_bounces` (programa=jc, vigentes) contra la
pestaña `Seguimiento` de la **BD Seguimiento de Monitorias** (Sheet vivo
`1ggzoJeZR3fS6AwRCLoGeYA5HEp_B7zvOwFGlGwny0l8`, columna `Grupo`=ciudad, cruce por email —
mismo Sheet que lee `tools/exportar_sin_completar.py`, sin tocar su formato) y publica un
snapshot semanal (semana ISO) en la pestaña **`RebotesCiudad`** del Sheet `RebotesJC`:
Ciudad · Total en Seguimiento · Hard · Soft · Total rebotes · % rebote. Semanas anteriores
quedan congeladas (mismo patrón `Historico` de `exportar_sin_completar.py`).

```powershell
python seguimiento_rebotes_ciudad.py             # escribe
python seguimiento_rebotes_ciudad.py --dry-run    # solo consola
```

**⚠ Alcance real — es un demo, NO mide "correos enviados":** los monitores mandan correo
por su cuenta, fuera de `enviar_campana.py` — no hay registro de envíos exitosos, solo de
rebotes (vía IMAP de `soporte@tocaunavida.org`). El "% rebote" es sobre el total de personas
de esa ciudad en Seguimiento, no sobre un total enviado. **Pendiente para escalar:** dar
control de cada cuenta de monitor (una por ciudad) para tener visibilidad real de envío, no
solo de rebote — bloqueado hasta tener esas credenciales.

**Hallazgo primera corrida (2026-08-19):** de 166 rebotes vigentes, 141 (85%) caen en "SIN
UBICACIÓN". Investigado a fondo con `tools/investigar_rebotes_sin_ubicacion.py` (cruce contra
`v_gui_personas` + `postulantes_jc`, no solo Seguimiento) — **descartada la hipótesis de
retiro/inhabilitación**: solo 1/141 es un retirado real. El desglose real: 10 son matriculados
**activos hoy** con typo de correo real (`gmail.con`, `gamil.com`, `hormail.com`, …) — vale la
pena corregirles el dato de contacto; 1 solo aparece en el universo histórico amplio
(`postulantes_jc`, nunca matriculó); **129/141 (91%) no tienen ningún rastro en ningún sistema
de JC** (ni matrícula, ni postulación histórica) — la lectura más probable es que el buzón
compartido `soporte@tocaunavida.org` sí está recibiendo tráfico de rebote ajeno a estudiantes
de JC, tal como ya advertía este README antes de que se verificara. El cruce por email (sin
cédula, porque las listas de campaña JC no la traen) es más débil que el de
`exportar_sin_completar.py`.

---

## Seguridad

La contraseña de aplicación (16 caracteres + espacios) NUNCA va en el código ni a git, y se
recomienda no pegarla en el chat de Claude (incidente de exposición con la cuenta de MR el
2026-07-15, ver `mujeres-rofe-correos/README.md`). Agregarla directo a `.env.local` desde una
terminal propia.
