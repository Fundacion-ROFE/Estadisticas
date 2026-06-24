# Runbook: Actualizar datos Q10 en Google Sheets

**Para:** Equipo no técnico (operadores)
**Tiempo:** ~2 minutos de espera activa
**Frecuencia:** Bajo demanda — cuando el equipo necesite datos frescos

---

## Requisitos previos

- Tener acceso al bot de Telegram del equipo
- El PC de Samuel (EstudiantesJC) debe estar encendido y con n8n corriendo
  - Samuel lo inicia con doble clic en `iniciar_n8n.bat` en su escritorio
  - Si no está corriendo: pedir a Samuel que lo inicie (~45 segundos para arrancar)

---

## Pasos para actualizar H1Test

1. Abrir Telegram
2. Buscar el bot del equipo (nombre: el que Samuel compartió internamente)
3. Enviar el comando:
   ```
   /actualizar h1test
   ```
4. Esperar ~2 minutos
5. El bot responderá con un mensaje como:
   ```
   ✅ h1test actualizado: 8,818 filas
   ```
6. Abrir Google Sheets → hoja **H1Test** — los datos ya están actualizados

---

## Qué datos trae

| Columna | Contenido |
|---------|-----------|
| A — Identificacion | Número de documento del estudiante |
| B — Nombre | Nombre completo |
| C — Celular | Teléfono registrado en Q10 |
| D — Email | Correo electrónico |
| E — Curso | Nombre del curso matriculado |
| F — Avance | Porcentaje de progreso (0–100%) |

Una fila por estudiante × curso. Si un estudiante tiene 3 cursos → 3 filas.

---

## Categorías de anomalías a revisar

| Situación | Qué significa |
|-----------|---------------|
| Columna Curso vacía | Estudiante registrado pero sin curso virtual asignado |
| Avance = 0% | Matriculado pero nunca abrió el contenido |
| Email no coincide | Typo o email alternativo entre sistemas Q10 |
| Avance > 100% | Error de sincronización en Q10 (puede llegar a 101%) |

---

## Qué NO hace esta automatización

- No modifica datos en Q10 — solo lectura
- No envía correos ni notificaciones a estudiantes
- No calcula promedios ni genera reportes — eso se hace con fórmulas en Sheets

---

## Si algo sale mal

| Problema | Qué hacer |
|----------|-----------|
| El bot no responde en 5 min | Avisar a Samuel — puede que n8n esté caído |
| El bot responde "error" | Reenviar el comando una vez más; si persiste, avisar a Samuel |
| Los datos en Sheets no cambiaron | Verificar que el bot confirmó éxito; si sí confirmó y Sheets no cambió, avisar a Samuel |
| El bot dice "comando no reconocido" | Verificar que el comando esté escrito exactamente: `/actualizar h1test` |

---

## Contacto técnico

Samuel David Vida — samueldavidvida@gmail.com
