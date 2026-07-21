// Nodo: Presentes @10min  — control temprano de asistencia (rediseño 2026-07-07)
// Rama `meeting.started` del workflow "Zoom - Asistencia" (ID jkNaE51PKQ4TQzNq).
// Copia de referencia del jsCode del nodo. Todo cambio va en AMBOS lados:
// editar aquí → PUT /api/v1/workflows/jkNaE51PKQ4TQzNq → re-exportar a n8n-workflows/.
//
// Entrada: filas de LIVE-LOG filtradas por UUID (nodo "Leer LIVE-LOG"):
//   { UUID, Evento: 'joined'|'left', Nombre, Correo, HoraMs, ... }
// acumuladas por la rama meeting.participant_joined/_left. Ya NO usa la Dashboard
// API (GET /metrics/...?type=live) — bloqueada por el feature flag de cuenta que
// Zoom se negó a habilitar (ticket cerrado 2026-07-07).
//
// Presente al minuto ~10 = misma persona con más 'joined' que 'left' en el log
// (tolera reconexiones: 2 joins + 1 left = sigue adentro). NO calcula % ni
// momentos dorados — eso lo hace la rama completa al meeting.ended.
// El curso y la fecha salen del payload del webhook meeting.started.

const RE_EMAIL = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/;
const RE_CEDULA = /\b\d{6,10}\b/;

const obj = $('Webhook Trigger').first().json.body.payload.object;
const curso = (obj.topic || '').trim();
const inicio = new Date(obj.start_time);

// Hora Colombia (UTC-5 fijo, sin DST) — igual que el nodo de la toma completa.
function fechaBogota(d) {
  return new Date(d.getTime() - 5 * 3600000).toISOString().slice(0, 16).replace('T', ' ');
}
function horaBogota(d) {
  return new Date(d.getTime() - 5 * 3600000).toISOString().slice(11, 16);
}

// Extraer email/cédula desde el "name" de texto libre manual (mismo gotcha del proceso).
function extraerContacto(nombreCrudo, emailCrudo) {
  const email = RE_EMAIL.test(emailCrudo)
    ? emailCrudo.toLowerCase()
    : (nombreCrudo.match(RE_EMAIL) || [''])[0].toLowerCase();
  const cedula = (nombreCrudo.match(RE_CEDULA) || [''])[0];
  const nombreLimpio = nombreCrudo.split(/[-|/]/)[0].trim();
  return { email, cedula, nombreLimpio };
}
function partirNombre(nombreCompleto) {
  const idx = nombreCompleto.indexOf(' ');
  if (idx === -1) return { nombre: nombreCompleto, apellido: '' };
  return { nombre: nombreCompleto.slice(0, idx), apellido: nombreCompleto.slice(idx + 1) };
}

// Agrupar eventos del log por persona (clave = email o nombre normalizado, igual
// que la rama completa) y contar joins vs lefts.
const grupos = new Map();
for (const item of $input.all()) {
  const r = item.json;
  const nombreCrudo = (r.Nombre || '').toString().trim();
  const emailCrudo = (r.Correo || '').toString().trim();
  if (!nombreCrudo && !emailCrudo) continue;
  const { email, cedula, nombreLimpio } = extraerContacto(nombreCrudo, emailCrudo);
  const clave = email || nombreLimpio.toLowerCase().replace(/\s+/g, ' ');
  if (!grupos.has(clave)) {
    grupos.set(clave, { nombreLimpio, email, cedula, joins: 0, lefts: 0, primerJoinMs: null });
  }
  const g = grupos.get(clave);
  if ((r.Evento || '').toString().trim() === 'left') {
    g.lefts++;
  } else {
    g.joins++;
    const ms = Number(r.HoraMs);
    if (Number.isFinite(ms) && (g.primerJoinMs === null || ms < g.primerJoinMs)) {
      g.primerJoinMs = ms;
    }
  }
  if (!g.email && email) g.email = email;
  if (!g.cedula && cedula) g.cedula = cedula;
}

// Una fila por persona que sigue conectada al momento de leer el log (~minuto 10).
const filas = [];
for (const [, g] of grupos) {
  if (g.joins <= g.lefts) continue; // ya salió de la reunión
  const { nombre, apellido } = partirNombre(g.nombreLimpio);
  filas.push({
    json: {
      Nombre: nombre,
      Apellido: apellido,
      'Correo electrónico': g.email,
      Identificacion: g.cedula,
      Curso: curso,
      Fecha: fechaBogota(inicio),
      'Hora ingreso': g.primerJoinMs !== null ? horaBogota(new Date(g.primerJoinMs)) : '',
    },
  });
}

return filas;
