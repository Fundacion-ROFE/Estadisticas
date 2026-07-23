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
- **Sin captura de rebotes ni supresiones** (`capturar_rebotes.py`, `email_optout`,
  `email_bounces`): no existían para JC al crear esta infraestructura (2026-07-22) porque nunca
  se había mandado una campaña real — no hay historial de rebotes que capturar todavía. Construir
  cuando haya un primer envío masivo real (mismo patrón que MR, IMAP sobre `comunicaciones@`).
- **Sin lista real todavía**: `campanas/recordatorio_charla_ejemplo.json` es solo para validar la
  plantilla (contenido de una charla de mayo ya pasada). Falta decidir la fuente de la lista de
  destinatarios JC (¿Supabase `participants` con `programa=jc`? — confirmar con Samuel antes del
  primer envío real).

---

## Seguridad

La contraseña de aplicación (16 caracteres + espacios) NUNCA va en el código ni a git, y se
recomienda no pegarla en el chat de Claude (incidente de exposición con la cuenta de MR el
2026-07-15, ver `mujeres-rofe-correos/README.md`). Agregarla directo a `.env.local` desde una
terminal propia.
