// Nodo: Calcular Momentos Dorados
// Requiere: nodo "Info Reunion" con { start_time, duration } reales (no programados)
// Entrada: items de "Participantes" — cada item.json puede traer un array "participants"
//
// Copia de referencia del jsCode del nodo "Calcular Momentos Dorados" del workflow
// "Zoom - Asistencia" (ID jkNaE51PKQ4TQzNq). Todo cambio va en AMBOS lados:
// editar aquí → PUT /api/v1/workflows/jkNaE51PKQ4TQzNq → re-exportar a n8n-workflows/.

const MARGEN_MIN = 10;
const RE_EMAIL = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/;
const RE_CEDULA = /\b\d{6,10}\b/;

// 1. Metadata real de la reunión
const info = $('Info Reunion').first().json;
const inicio = new Date(info.start_time);
const duracionMin = info.duration;

// Curso = tema de la reunión (las clases se programan una a una con nombre del curso).
// Fecha en hora Colombia (UTC-5 fijo, sin DST) para coordinar filas con la clase.
const curso = (info.topic || $('Webhook Trigger').first().json.body.payload.object.topic || '').trim();
function fechaBogota(d) {
  return new Date(d.getTime() - 5 * 3600000).toISOString().slice(0, 16).replace('T', ' ');
}

if (isNaN(inicio.getTime())) {
  throw new Error('start_time inválido en "Info Reunion" — revisar respuesta de Zoom');
}
const finReal = new Date(inicio.getTime() + duracionMin * 60000);

// 2. Los 3 momentos dorados (instantes exactos)
const checkpoints = {
  min10:   new Date(inicio.getTime() + MARGEN_MIN * 60000),
  mitad:   new Date(inicio.getTime() + (duracionMin / 2) * 60000),
  final10: new Date(inicio.getTime() + (duracionMin - MARGEN_MIN) * 60000),
};

// 3. Aplanar todas las sesiones join/leave (soporta 1 array grande o varias páginas)
const sesiones = [];
for (const item of $input.all()) {
  const participantes = Array.isArray(item.json.participants) ? item.json.participants : [item.json];
  for (const p of participantes) {
    if (!p.join_time) continue;
    sesiones.push({
      nombreCrudo: (p.name || '').trim(),
      emailCrudo: (p.user_email || '').trim(),
      join: new Date(p.join_time),
      leave: p.leave_time ? new Date(p.leave_time) : finReal, // sin leave_time → sigue conectado hasta el fin
    });
  }
}

// 4. Extraer email/identificación reales desde "name" (texto libre manual — ver gotcha conocido)
function extraerContacto(nombreCrudo, emailCrudo) {
  const email = RE_EMAIL.test(emailCrudo)
    ? emailCrudo.toLowerCase()
    : (nombreCrudo.match(RE_EMAIL) || [''])[0].toLowerCase();
  const cedula = (nombreCrudo.match(RE_CEDULA) || [''])[0];
  const nombreLimpio = nombreCrudo.split(/[-|/]/)[0].trim();
  return { email, cedula, nombreLimpio };
}

// 5. Agrupar sesiones por participante — clave = email si existe, si no nombre normalizado
const grupos = new Map();
for (const s of sesiones) {
  const { email, cedula, nombreLimpio } = extraerContacto(s.nombreCrudo, s.emailCrudo);
  const clave = email || nombreLimpio.toLowerCase().replace(/\s+/g, ' ');
  if (!grupos.has(clave)) {
    grupos.set(clave, { nombreLimpio, email, cedula, intervalos: [] });
  }
  const g = grupos.get(clave);
  g.intervalos.push([s.join, s.leave]);
  if (!g.email && email) g.email = email;
  if (!g.cedula && cedula) g.cedula = cedula;
}

// 6. ¿Un instante cae dentro de alguna sesión join→leave del participante?
function estuvoConectado(instante, intervalos) {
  return intervalos.some(([join, leave]) => instante >= join && instante <= leave);
}

// 6b. % de la clase que estuvo conectado: fusionar intervalos solapados/contiguos
// (las sesiones de reconexión pueden solaparse — no sumar doble), recortar a
// [inicio, finReal] y dividir por la duración real de la reunión.
function porcentajeAsistencia(intervalos) {
  const ordenados = [...intervalos].sort((a, b) => a[0] - b[0]);
  const fusionados = [];
  for (const [join, leave] of ordenados) {
    const ultimo = fusionados[fusionados.length - 1];
    if (ultimo && join <= ultimo[1]) {
      if (leave > ultimo[1]) ultimo[1] = leave;
    } else {
      fusionados.push([join, leave]);
    }
  }
  let msConectado = 0;
  for (const [join, leave] of fusionados) {
    const desde = Math.max(join.getTime(), inicio.getTime());
    const hasta = Math.min(leave.getTime(), finReal.getTime());
    if (hasta > desde) msConectado += hasta - desde;
  }
  const totalMs = duracionMin * 60000;
  if (totalMs <= 0) return '0%';
  return `${Math.round((msConectado / totalMs) * 100)}%`;
}

// 7. Nombre/Apellido: primer espacio separa, todo el resto va a Apellido
function partirNombre(nombreCompleto) {
  const idx = nombreCompleto.indexOf(' ');
  if (idx === -1) return { nombre: nombreCompleto, apellido: '' };
  return { nombre: nombreCompleto.slice(0, idx), apellido: nombreCompleto.slice(idx + 1) };
}

// 8. Evaluar los 3 momentos dorados por participante — SIN filtrar a nadie
const resultado = [];
for (const [, g] of grupos) {
  const min10 = estuvoConectado(checkpoints.min10, g.intervalos);
  const mitad = estuvoConectado(checkpoints.mitad, g.intervalos);
  const final10 = estuvoConectado(checkpoints.final10, g.intervalos);
  const totalInstancias = [min10, mitad, final10].filter(Boolean).length;
  const { nombre, apellido } = partirNombre(g.nombreLimpio);

  resultado.push({
    json: {
      Nombre: nombre,
      Apellido: apellido,
      'Correo electrónico': g.email,
      Identificacion: g.cedula,
      Instancias: `${totalInstancias}/3`,
      Curso: curso,
      Fecha: fechaBogota(inicio),
      '% Asistencia': porcentajeAsistencia(g.intervalos),
    },
  });
}

return resultado;
