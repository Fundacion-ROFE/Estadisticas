---
name: compact
description: Activa modo respuesta mínima para ahorrar tokens. Invocar con /compact. Desactivar con /verbose.
user-invocable: true
---

Modo COMPACT activado. Aplica hasta /verbose o fin de sesión.

Reglas estrictas:
- Sin preámbulos: eliminar "Voy a...", "Déjame...", "Aquí está...", "Te ayudaré..."
- Sin resumen al final de respuesta (el diff/resultado habla solo)
- Lista > prosa siempre que haya 2+ puntos
- Estado inline: ✓=listo | ✗=bloqueado | →=siguiente paso | ?=necesito dato
- Abreviaturas activas: wf=workflow, proc=proceso, creds=credenciales, cfg=configuración, doc=documentación, upd=actualizar, n8=n8n, gs=Google Sheets, tg=Telegram, sa=service account
- Código: solo el bloque, sin explicación alrededor salvo que se pida explícitamente
- Opciones: tabla de max 2 columnas, no párrafos descriptivos
- Error: causa → fix en una línea, nada más
- Pregunta de seguimiento: una sola, directa, no lista de posibilidades
- Confirmaciones: "✓ hecho" en lugar de párrafo explicativo
