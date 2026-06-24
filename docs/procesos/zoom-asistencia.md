# Asistencia Zoom

**Estado:** En progreso (bloqueado por 4 preguntas pendientes a jefatura)
**Última actualización:** 2026-06-22
**Procesos relacionados:** —

## Qué hace
Automatiza la toma de asistencia de clases virtuales en Zoom (2 salas, plan Business,
100 usuarios c/u), extrayendo 4 de las ~20 columnas del reporte de participantes y
enviándolas a Google Sheets para validación contra lista maestra de inscritos.

## Disparador (Trigger)
Por definir: Google Calendar Trigger (si el evento de la clase está en Calendar) vs
Schedule/Cron Trigger. Pendiente confirmar si Calendar y Zoom están integrados de forma
consistente (¿el link/Meeting ID siempre queda en la descripción del evento?).

## Flujo resumido (diseño preliminar, sujeto a cambios)
1. Trigger dispara al finalizar la clase (con margen de tiempo, el reporte no es
   instantáneo).
2. Resolver el Meeting ID de la sesión (los IDs NO son fijos/recurrentes).
3. Llamar a Zoom Reports API → `/report/meetings/{meetingId}/participants`.
4. Parsear/limpiar los datos de Email e Identificación (capturados como texto plano
   manual por los estudiantes — no estructurado).
5. Filtrar a las 4 columnas necesarias: Nombre, Apellido, Correo, Identificación.
6. Escribir a Google Sheets (hoja de asistencia / Seguimiento).

## Fuentes de datos / APIs usadas
- Zoom API — Server-to-Server OAuth (pendiente crear app en Marketplace y confirmar
  scopes exactos: `report:read`, `meeting:read`, etc.)
- Google Calendar (lectura de evento)
- Google Sheets (escritura)

## Destino de los datos
Hoja con columnas: Nombre, Apellido, Correo electrónico, Identificación, Validar.
La columna "Validar" usa fórmula existente que compara contra hoja `Seguimiento` (columnas
E:F = Correo e Identificación de la lista maestra de inscritos). La automatización NO
necesita calcular "Validar" — solo alimentar las 4 columnas crudas.

## Decisiones de diseño clave
- Server-to-Server OAuth elegido sobre OAuth clásico para evitar flujo de consentimiento
  de usuario (proceso desatendido). [Confirmar al implementar]

## Gotchas / Limitaciones conocidas
- **Crítico, sin resolver:** Email e Identificación se capturan como texto libre manual
  por el estudiante al unirse (no vía formulario de registro de Zoom estructurado).
  Esto implica parseo de texto sucio, alto riesgo de error de formato humano.
  Escenarios posibles: (A) todo en el campo "nombre", (B) campos de registro de Zoom
  estructurados, (C) fuente separada (Form/chat). Aún sin confirmar cuál aplica.
- Meeting IDs no son fijos — hay que resolverlos dinámicamente, no se puede hardcodear.
- El reporte de participantes de Zoom puede no estar disponible inmediatamente al
  terminar la reunión — necesita margen de espera o reintento.
- Infraestructura: n8n corre local en PC de Samuel (EstudiantesJC) + cloudflared para tunnel; decisión pendiente sobre mover a máquina dedicada para estabilidad en horario laboral.

## Contingencia manual

Proceso en diseño — no hay contingencia definida aún. Al implementar, documentar aquí:
el paso manual equivalente si n8n falla durante una sesión Zoom.

## Conexiones del sistema

- [[mapa-codigo]] — al implementar, los scripts asociados quedarán documentados ahí
- [[convenciones]] — Server-to-Server OAuth (Zoom), SSL corporativo
- [[q10-consolidacion]] — patrón de trigger Telegram + n8n reutilizable
- [[dashboard-web]] — si se decide publicar estadísticas de asistencia, este proceso alimentaría un tab adicional

## Pendiente / Próximos pasos
- [ ] Confirmar cómo se captura hoy Email/ID en la sesión real (revisar un CSV de
  asistencia exportado de una clase pasada).
- [ ] Confirmar si Calendar trae el Meeting ID de forma consistente.
- [ ] Crear app Server-to-Server OAuth en Zoom Marketplace y confirmar scopes.
- [ ] Decidir infraestructura final (portátil vs Raspberry Pi).
- [ ] Definir manejo de errores (ver `docs/convenciones.md`).
