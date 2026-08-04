# Guía de Workflows n8n — Fundación ROFÉ

> Setup y configuración de los workflows automáticos en n8n (local, PC Samuel).
> Cada workflow está en `n8n-workflows/` como JSON exportado.

---

## Workflow: Cálculo automático de asistencia Zoom

**Nombre en n8n:** `asistencia-zoom-diario`
**Archivo:** `n8n-workflows/asistencia-zoom-diario.json` (ver abajo para crear)
**Trigger:** Cron job — Diariamente a las 00:00 (medianoche)
**Acción:** Ejecuta script Python `calcular_asistencia_promedio.py`

### Propósito

Cada noche, después de que Zoom envíe sus eventos y se cierren las reuniones:
1. Lee ZOOM-ASISTANCE (Google Sheets) con todos los registros del día
2. Calcula promedios por estudiante y por curso
3. Inserta/actualiza en Supabase `asistencia_promedio`
4. Notifica al usuario (opcional)

### Estructura del workflow

```
Trigger: Cron job (00:00 UTC)
  ↓
Execute Command: bash/python
  ├─ cd /path/to/admin-usable
  └─ python scripts/panel-datos/calcular_asistencia_promedio.py
  ↓
Output: Log de ejecución
  ├─ Registros leídos: XXX
  ├─ Estudiantes únicos: XXX
  ├─ Insertados/Actualizados: XXX
  └─ Status: OK / ERROR
```

### Pasos para crear en n8n

**1. Abre n8n**
```
http://localhost:5678
```

**2. Nuevo workflow → Naming**
- Nombre: `asistencia-zoom-diario`
- Descripción: "Calcula promedios de asistencia Zoom diariamente desde ZOOM-ASISTANCE (Sheet) a Supabase"

**3. Agregar trigger: Cron**
- Click "+ Add trigger" → search "Cron"
- Seleccionar "Cron" node
- Configurar:
  ```
  Trigger time: 00:00 (midnight UTC)
  ```

**4. Agregar acción: Execute Command**
- Click "+ Add" → search "Execute Command"
- Seleccionar "Execute Command" node
- Configurar:
  ```
  Command:
  cd "C:\Users\EstudiantesJC\downloads\admin-usable" && python scripts\panel-datos\calcular_asistencia_promedio.py
  
  Working Directory:
  C:\Users\EstudiantesJC\downloads\admin-usable
  
  Timeout (ms):
  120000  (2 minutos, suficiente para 490 estudiantes)
  ```

**5. (Opcional) Agregar notificación: Webhook o Slack**
- Click "+ Add" → search "Webhook"
- O search "Slack" si tienes canal de notificaciones
- Configurar para enviar resultado

**6. Conectar nodes**
- Cron → Execute Command
- Execute Command → (Notificación, si la hay)

**7. Guardar y activar**
- Click "Save" (esquina superior)
- Click el toggle de "Active" (arriba a la derecha)
- Workflow está listo

### Testing

**Antes de activar automático, prueba una vez:**

1. En n8n, click el play button (▶) de "Execute Command"
2. Verifica que la ejecución sea exitosa
3. Checklist:
   - ✓ Output muestra "Sync completado"
   - ✓ Registros leídos: ~704
   - ✓ Estudiantes únicos: ~490
   - ✓ Status OK

**Si falla:**
- Verifica el path absoluto de la carpeta
- Comprueba que Python está en PATH: `python --version`
- Comprueba que las credenciales de Sheets están disponibles en `scripts/q10-consolidacion/credenciales_service_account.json`

### Alternativa: Windows Task Scheduler

Si prefieres no usar n8n para esto, puedes usar **Windows Task Scheduler**:

```batch
"C:\Python314\python.exe" "C:\Users\EstudiantesJC\downloads\admin-usable\scripts\panel-datos\calcular_asistencia_promedio.py"
```

Pero n8n centraliza todos los workflows, por eso es preferible.

### Monitoreo

**En n8n:**
- Click en el workflow → Executions
- Verifica que cada noche a las 00:00 aparezca una ejecución
- Si hay errores, haz click y expande "Errors" para detalles

**En Supabase:**
- Dashboard → `asistencia_promedio`
- Columna `actualizado_en`: debe mostrar HOY a las 00:XX
- Si no hay cambios, el script no corrió

---

## Workflow: Dashboard web (existente)

**Nombre en n8n:** `q10-consolidacion` (schedule 4h)
**Estado:** Operativo desde 2026-06-23

Este workflow **NO** necesita cambios. Solo documentado para referencia:
- Trigger: Cron job cada 4 horas
- Acción: `q10_to_sheets.py` (extrae Q10 → Google Sheets h2test)

---

## Workflow: Actualización BD Mujeres ROFÉ (existente)

**Nombre en n8n:** `mr-actualizar` (schedule 7:30 AM)
**ID en n8n:** `LgkDbNPERYgKMrYj`
**Estado:** Operativo desde 2026-07-07

Documentado para referencia:
- Trigger: Cron job diariamente 7:30 AM
- Acción: Form MR2024 → BD-Mujeres ROFÉ (pestaña General)

---

## Notas generales

- **Credenciales:** Todos los workflows usan Service Accounts guardadas en `scripts/q10-consolidacion/credenciales_service_account.json` (nunca en n8n dashboard, por seguridad).
- **Logs:** n8n guarda logs de cada ejecución. Para auditoría, exporta desde "Executions" si necesitas un backup.
- **Errores comunes:**
  - Path incorrecto → mensaje "No such file or directory"
  - Timeout → aumenta `Timeout (ms)` en Execute Command
  - Credenciales vencidas → regenera Service Account en Google Cloud Console

---

## Próximos workflows (planificados)

- **Zoom → Sheets (webhook):** capture eventos en tiempo real (meeting.started, participant_joined, etc.)
- **Panel de Datos: sync_sociodemograficos (diario 8 AM):** sincroniza BD monitorias a Supabase
- **Grabaciones Zoom → YouTube:** sube videos procesados (manual hoy)
