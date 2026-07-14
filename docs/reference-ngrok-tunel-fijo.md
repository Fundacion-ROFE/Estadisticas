# ngrok — Túnel Fijo de n8n

**Estado:** Activo — dominio permanente, no cambia entre reinicios (reemplaza cloudflared).

---

## Configuración (2026-07-07)

### Dominio público
- **URL estática:** `ergonomic-absinthe-refract.ngrok-free.dev` (nunca cambia)
- **Webhook Zoom asistencia:** `https://ergonomic-absinthe-refract.ngrok-free.dev/webhook/zoom-asistencia`
- **Plan:** ngrok free tier (cuenta de Samuel, plan "dev domain")

### Configuración local
```
Archivo: %LOCALAPPDATA%\ngrok\ngrok.yml (version "2")

tunnels:
  n8n:
    proto: http
    addr: http://localhost:5678
    authtoken: [guardado en ngrok.yml]
```

**Nota:** No duplicar el token — vive en `ngrok.yml`.

### Arranque
```bash
ngrok start n8n
```

**Requisitos:**
- Agente ngrok **≥ 3.20** (actualizar con `ngrok update` si es necesario)
- No correr ngrok manual y como servicio Windows simultáneamente (free tier: 1 agente)
- Terminal de administrador para `ngrok service install`

### Automatización en iniciar_n8n.bat
```batch
# Script arranca ngrok + n8n juntos
ngrok start n8n &
n8n start
```

- Watchdog revive ngrok si cae
- Guard previene lanzar segundo agente
- Espera el túnel vía API local `:4040`

---

## Estado de validación (2026-07-07)

✅ **Completado:**
- Túnel vía ngrok probado end-to-end
- Healthz público: HTTP 200
- Handshake CRC de Zoom: validado
- WEBHOOK_URL hardcodeada al dominio fijo en iniciar_n8n.bat

⏳ **Pendiente:**
- Samuel repega la URL fija en Event Subscription de Zoom (comunicaciones)
- Pulsa "Validate" en Zoom para confirmar handshake

---

## Gotchas y troubleshooting

| Problema | Solución |
|----------|----------|
| `ngrok service install` falla | Usar terminal de administrador |
| ngrok cae sin revivar | Script watchdog está activo; revisar logs en `iniciar_n8n.bat` |
| Dos agentes corriendo | Matar proceso ngrok extra; free tier: 1 solo |
| Token desactualizado | Sincronizar con credencial vigente en n8n dashboard |

---

## Referencia cruzada

- [[reference-n8n-api-key]] — API Keys y endpoints n8n
- [[zoom-asistencia]] — Webhook Zoom que usa esta URL
- CLAUDE.md — `iniciar_n8n.bat` explicado
