# Botonera de Comandos

Ventana de escritorio (Tkinter) con un botón por cada comando del **bot de Telegram**
del proyecto, con una descripción breve de para qué sirve cada uno. Sirve para no tener
que recordar los comandos: se abre, se lee y se hace clic.

## Cómo abrir

Doble clic en **`Abrir_Botonera_Comandos.bat`** (en la raíz del repo), o:

```
python scripts/botonera-comandos/botonera_comandos.py
```

## Qué hace cada botón

Ejecuta **localmente, en esta PC**, exactamente el mismo comando que dispara el bot de
Telegram (`/actualizar <algo>`). No pasa por Telegram ni por n8n — corre los scripts
directamente, que es lo mismo que hace el bot por debajo. La salida de cada script se ve
en vivo en la consola de abajo.

| Botón | Comando Telegram | Qué hace |
|---|---|---|
| Q10 → Sheets + Dashboard | `/actualizar q10` | Pipeline completo de Q10 → dashboard público (PESADO) |
| Pipeline Panel de Datos | `/actualizar panel` | Normaliza Q10 → Supabase → Emoflow → Sheets (panel Vercel) |
| Asistencia Zoom | `/actualizar asistencia` | Sincroniza asistencia de Zoom → Supabase |
| Form MR2024 | `/actualizar mr` | Respuestas del formulario MR → BD-Mujeres ROFÉ |
| Rebotes de correo | `/actualizar rebotes` | Marca correos rebotados de campañas MR |
| Alerta de deserción | `/actualizar alerta` | Recalcula estudiantes en riesgo (JC) |
| Grabaciones Zoom | `/actualizar backfill` | Sube grabaciones recientes a YouTube/Drive |

## Notas

- **Confirmación:** cada botón pide confirmar antes de correr (son acciones reales:
  escriben en Sheets/Supabase, suben videos, etc.).
- **Pesados (`q10`, `panel`):** tardan varios minutos. `q10` además usa el mismo lock
  (`lock_cli.py`) que el bot programado, así que no se solapa con una corrida automática
  de n8n: si hay una en curso, el botón avisa y no arranca.
- **Fuente de verdad:** la lista de comandos es un espejo de
  `n8n-workflows/q10-consolidacion.json` (nodo *Parsear Comando*). Si allí cambia un
  comando, actualizar la lista `COMANDOS` en `botonera_comandos.py`.
