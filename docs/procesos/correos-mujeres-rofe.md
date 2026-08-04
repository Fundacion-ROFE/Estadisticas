# Correos Mujeres ROFÉ (envíos masivos)

**Estado:** En producción / operativo
**Última actualización:** 2026-07-29
**Procesos relacionados:** [[mr-actualizacion-datos]] · [[postulantes-mr-supabase]] · [[panel-datos-etl]] · [[convenciones]]

> Nota creada en la auditoría de documentación 2026-08-04: el proceso ya existía y estaba en uso
> (skill `/enviar-correo`, cron n8n, campaña masiva del 2026-07-14), pero no tenía nota en
> `docs/procesos/` — solo el README técnico del código. Esta nota es el nivel "proceso"; el
> detalle línea por línea vive en `scripts/mujeres-rofe-correos/README.md` (no duplicar, actualizar
> ahí primero y resumir el cambio aquí).

## Qué hace

Envío masivo de correos a mujeres del programa Mujeres ROFÉ (últimos 3 años, 2024–2026) a partir
de una plantilla HTML parametrizada + una lista CSV. Orquestado en lenguaje natural por el skill
`/enviar-correo` (`.claude/skills/enviar-correo/SKILL.md`), que arma la lista, corre preview y
piloto, y solo pide confirmación a Samuel antes de un envío masivo real — nunca envía por su cuenta.

## Disparador (Trigger)

- **Manual, bajo demanda:** petición en lenguaje natural → skill `/enviar-correo` →
  `scripts/mujeres-rofe-correos/enviar_campana.py` (preview / piloto / `--enviar`).
- **Cron n8n diario 6:30 a.m. (`correos-rebotes-diario`):** corre `capturar_rebotes.py` para
  detectar rebotes de campañas recientes, no dispara envíos.

## Flujo resumido

1. Armar la lista de destinatarias (`tools/mujeres-rofe-correos/data/lista_<ID>.csv`) — combina
   Supabase (`postulantes_mr`, 2025/2026) + Excel `BD-Mujeres ROFÉ 2026 (2).xlsx` (cubre 2024, que
   Supabase no tiene) vía `extraer_lista_mr_ultimos3anios.py`, o por ciudad vía
   `extraer_lista_ciudad_mr.py`. Excluye automáticamente `email_optout` y `email_bounces` con
   `tipo=hard`.
2. `enviar_campana.py campanas/<id>.json --preview` — genera `preview.html`, sin credenciales.
3. `enviar_campana.py ... --piloto <correo>` (o `run_piloto.py`, pide la contraseña con `getpass`)
   — un solo correo de prueba antes de enviar en masivo.
4. `enviar_campana.py ... --enviar` — pide confirmación escrita (`ENVIAR <N>`), lotes de 500,
   reanudable vía `enviados_<ID>.csv` si se corta.
5. `capturar_rebotes.py` (cron diario) lee por IMAP los DSN de rebote de las 2 cuentas remitentes,
   clasifica hard/soft, actualiza `email_bounces` + pestaña `Rebotes` del Sheet BD-Mujeres ROFÉ.

## Fuentes de datos / APIs usadas

- Supabase `panel-datos-rofe`: `postulantes_mr`, `email_optout`, `email_bounces`,
  `campanas_enviadas`, `alertas_datos` (todas con RLS activa, sin política `anon`).
- Excel `BD-Mujeres ROFÉ 2026 (2).xlsx` (pestaña `General`) — histórico 2024 que Supabase no tiene.
- SMTP Gmail (2 cuentas: `mujeres.rofe@tocaunavida.org` y `envios.mr@tocaunavida.org`) vía
  contraseña de aplicación, nunca en código — `.env.local` o `getpass`.
- IMAP (mismas 2 cuentas) para leer rebotes (`mailer-daemon`).

## Destino de los datos

- Correos salen a las destinatarias vía SMTP.
- Registro agregado (sin direcciones) en Supabase `campanas_enviadas`.
- Rebotes en Supabase `email_bounces` + pestaña `Rebotes` del Sheet BD-Mujeres ROFÉ (con nombre,
  para que el equipo actualice el dato) + alerta pública `alertas_datos` (conteo, sin PII).
- PII individual (listas, rebotes detallados) solo en `tools/mujeres-rofe-correos/data/`
  (gitignoreado), nunca en `scripts/` ni en GitHub.

## Decisiones de diseño clave

- **Un `ID` de campaña distinto por día** para reenvíos del mismo contenido a las mismas personas
  (recordatorios) — `enviados_<ID>.csv` salta a quien ya recibió ese `ID`, así que reusar el mismo
  `ID` varios días seguidos enviaría 0 el 2º/3er día.
- **Tolerancia de soft bounces (2026-07-29):** un correo que rebota `soft` 4 veces en 30 días se
  promueve automáticamente a `hard` (excluido) — antes solo un `5.x` real excluía, y direcciones
  con buzón crónicamente lleno (ej. `@sena.edu.co`) nunca se filtraban.
- **Liberación automática (2026-07-29):** si `actualizar_bd_mr.py` detecta que una fila cambió de
  correo, borra el correo viejo de `email_bounces` — la persona ya dio uno nuevo, no tiene sentido
  seguir excluyéndola.
- **Certificados personalizados** (adjunto distinto por persona) usan un flujo aparte
  (`certificados/preparar_certificados.py` + `enviar_certificados.py`), porque
  `enviar_campana.py` no soporta adjuntos por destinataria.

## Gotchas / Limitaciones conocidas

- Cuenta `envios.mr@tocaunavida.org` no acepta la contraseña de aplicación disponible — usar
  `mujeres.rofe@tocaunavida.org` como remitente principal.
- Bug de rename de nodo Cron (2026-07-15 → corregido 2026-07-29): el workflow `correos-rebotes-diario`
  disparaba "success" en <1s sin llamar a `capturar_rebotes.py` — la clave de `connections` del
  JSON no se había actualizado al renombrar el nodo. Ver [[convenciones#Editar workflows n8n por API (sin abrir la UI)]]
  para el patrón general de este tipo de bug.
- Ver `scripts/mujeres-rofe-correos/README.md` para el detalle completo (estructura de archivos,
  comandos exactos, estado acumulado de rebotes).

## Pendiente / Próximos pasos

- Rotación de las contraseñas de aplicación SMTP (pendiente, ver `.env.local`).
- Panel/reporte simple de `whatsapp_contactos_declarados`/proveedores cuando haya volumen — fuera
  de alcance de este proceso, ver [[whatsapp-identificacion-manychat]].
