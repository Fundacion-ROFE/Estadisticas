# Alerta de deserción

**Estado:** Completado
**Última actualización:** 2026-07-15
**Workflow n8n:** `alerta-desercion-semanal` (id `g0zmkQB70FHXPPLN`, activo, lunes 07:00)
**Procesos relacionados:** [[panel-datos-etl]] · [[q10-consolidacion]] · [[asistencia-zoom-flujo]]

## Qué hace
Detecta semanalmente a los estudiantes en riesgo de deserción leyendo la fuente ya
consolidada en Supabase (`enrollments.porcentaje_avance`) y avisa a Samuel por Telegram
con un resumen + top de casos. Es la versión automatizada y "una sola fuente" de
`tools/panel_riesgo.py` (que corre a mano y cruza Google Sheets).

## Disparador (Trigger)
Schedule/Cron en n8n — **semanal**, lunes 07:00 (`0 7 * * 1`). Workflow
`alerta-desercion-semanal`.

## Flujo resumido
1. Cron semanal dispara `alerta_desercion.py --csv` vía Execute Command.
2. El script consulta Supabase: matrículas NO completadas con `avance < umbral` (60) en
   cursos `programa=jc`, `cohorte=2026`.
3. Clasifica cada estudiante: `0%` → "posible abandono"; `1–59%` → "avance bajo".
4. Imprime a stdout un mensaje resumido (conteos + por grupo/ciudad + top N nombres) y
   escribe el detalle con PII a `tools/reportes/alerta_desercion_YYYYMMDD.csv`.
5. n8n revisa el resultado (`estado=exito`) y envía el stdout al chat de Samuel con el
   nodo Telegram del bot q10-consolidacion (credencial `Telegram Q10 Bot`). Rama de
   error explícita → Telegram con el stderr.

## Fuentes de datos / APIs usadas
- **Supabase `panel-datos-rofe`** (REST, service_role): `enrollments` embebido con
  `participants!inner` (nombre/email/ciudad/grupo_ciudad) y `courses!inner`
  (programa/cohorte). El `!inner` es obligatorio para que el filtro por programa/cohorte
  realmente excluya.
- **Telegram Bot API** (vía nodo n8n, credencial `Telegram Q10 Bot`).

## Destino de los datos
- Mensaje resumido → chat privado de Samuel en Telegram.
- Detalle con PII (nombre/email/ciudad/curso/avance) → `tools/reportes/alerta_desercion_*.csv`
  (carpeta **gitignoreada** — nunca a GitHub).

## Decisiones de diseño clave
- **Una sola fuente (Supabase), no el cruce de dos fuentes de `panel_riesgo`** (decisión
  Samuel 2026-07-15): la pestaña `Avance` manual no está en Supabase, así que reproducir
  el cruce h2test × Avance no es posible desde ahí. El riesgo se define solo sobre el
  avance ya consolidado. Consecuencia aceptada: la lista no coincide 1:1 con una corrida
  local de `panel_riesgo.py` (esa exige presencia en la hoja manual).
- **Alcance JC 2026:** las cohortes 2023–2025 son cursos ya cerrados (ruido histórico:
  595 matrículas en 0% en 2025). Configurable con `--programa` / `--cohorte`.
- **Umbral 60%** (igual que `panel_riesgo`). `--umbral` configurable.
- **Notificación por Telegram, no correo:** el resultado son pocos nombres para Samuel,
  no un envío masivo; se reutiliza el bot q10-consolidacion existente.
- **Telegram lo envía n8n, no el script:** no hay token de Telegram en `.env.local`; la
  credencial vive en n8n. El script solo produce el texto; el nodo Telegram lo envía.
- **service_role para leer PII:** `participants` tiene RLS activa y no expone PII a anon;
  el script usa `SUPABASE_SERVICE_ROLE_KEY` (mismo patrón backend que `cargar_supabase.py`).

## Gotchas / Limitaciones conocidas
- **El bot q10 es command-driven:** todos sus nodos Telegram responden al `chat_id` de
  quien manda el comando. Para un push programado hace falta el `chat_id` FIJO de Samuel
  (no está en ningún workflow). En el JSON está como placeholder `<<SAMUEL_CHAT_ID>>`.
- **"Una sola fuente" ≠ señal de asistencia:** la Tarea 4 dependía nominalmente de la
  asistencia fresca (Tarea 2). Hoy el riesgo se define solo por avance. La asistencia
  (`asistencia_zoom` / `asistencia_promedio`) ya está en Supabase y podría enriquecer el
  motivo en una iteración futura (ver Pendiente).
- El detalle PII sobrescribe el CSV del día (nombre por fecha) — idempotente por día.

## Pendiente / Próximos pasos
- [x] Obtener el `chat_id` de Telegram de Samuel (`8141703221`, del historial de ejecuciones
      de n8n) y sustituir el placeholder.
- [x] Crear/activar el workflow `alerta-desercion-semanal` en n8n y prueba en vivo: la
      notificación llegó al Telegram de Samuel (2026-07-15) — criterio de aceptación cumplido.
- [ ] (Opcional) Enriquecer el motivo cruzando con asistencia Zoom: "avance bajo +
      sin asistencia reciente" = señal de deserción más fuerte.
- [ ] (Opcional) Guardar historial de alertas para reportar solo casos NUEVOS cada semana.
- [ ] (Futuro, pedido Samuel 2026-07-15) Reusar este motor de reporte para **avisos por
      WhatsApp** (hoy es Telegram). Se parece al panel SinCompletar del Sheet, pero automatizado
      y notificado.
