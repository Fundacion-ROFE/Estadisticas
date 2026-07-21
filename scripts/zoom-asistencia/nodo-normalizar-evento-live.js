// Nodo: Normalizar Evento Live — rama meeting.participant_joined / meeting.participant_left
// Workflow "Zoom - Asistencia" (ID jkNaE51PKQ4TQzNq).
// Copia de referencia del jsCode del nodo. Todo cambio va en AMBOS lados:
// editar aquí → PUT /api/v1/workflows/jkNaE51PKQ4TQzNq → re-exportar a n8n-workflows/.
//
// Zoom manda un webhook por CADA entrada/salida de participante. Este nodo lo
// convierte en una fila del log LIVE-LOG (append en Sheets). Al minuto 10 la rama
// meeting.started lee ese log y calcula presentes = joined − left. Reemplaza a la
// Dashboard API (GET /metrics/...?type=live), bloqueada por un feature flag de
// cuenta que Zoom se negó a habilitar (ticket cerrado 2026-07-07).

const body = $('Webhook Trigger').first().json.body;
const obj = body.payload.object;
const p = obj.participant || {};
const esJoin = body.event === 'meeting.participant_joined';

// join_time/leave_time del payload; fallback a event_ts si faltara
const horaIso = esJoin ? p.join_time : p.leave_time;
let hora = horaIso ? new Date(horaIso) : null;
if (!hora || isNaN(hora.getTime())) hora = new Date(body.event_ts || Date.now());

// Hora Colombia (UTC-5 fijo, sin DST) — columna legible para humanos.
// La lógica del minuto 10 usa HoraMs (epoch ms), inmune al locale del Sheet.
function fechaBogotaSeg(d) {
  return new Date(d.getTime() - 5 * 3600000).toISOString().slice(0, 19).replace('T', ' ');
}

return [{
  json: {
    UUID: obj.uuid,
    Evento: esJoin ? 'joined' : 'left',
    Nombre: (p.user_name || '').trim(),
    Correo: (p.email || '').trim().toLowerCase(),
    HoraMs: hora.getTime(),
    'Hora Bogota': fechaBogotaSeg(hora),
    Curso: (obj.topic || '').trim(),
  },
}];
