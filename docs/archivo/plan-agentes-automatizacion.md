# Plan de Agentes y Herramientas — Ecosistema ROFÉ

**Estado:** En progreso
**Última actualización:** 2026-07-14
**Procesos relacionados:** [[prioridades-automatizacion-ia]] · [[panel-datos-etl]] · [[00-vision-global]]

> **Ejecución:** este documento es el contexto/justificación. El plan operativo desglosado
> en tareas atómicas (pensado para ejecutarse con Sonnet, una tarea a la vez) está en
> [[plan-ejecucion-sonnet]].

## Nota de alcance

Se pidió analizar `Downloads/panel-datos-rofe` y `Downloads/Correos-fast` como carpetas
sueltas. Ambas **ya están absorbidas dentro de este repo** — no son código externo pendiente
de integrar:

- `panel-datos-rofe` (repo Next.js separado) es el frontend del proceso [[panel-datos-etl]],
  documentado y en producción en Netlify. El ETL que lo alimenta vive en `scripts/panel-datos/`.
- `Downloads/Correos-fast/enviar_correos.py` es la **versión vieja** (contraseña SMTP
  hardcodeada — ver el incidente citado en `scripts/mujeres-rofe-correos/README.md`) del
  sistema de correos, ya **reemplazada** por `scripts/mujeres-rofe-correos/` (v2, segura,
  parametrizada por JSON, con preview/piloto/envío masivo). No hay nada que rescatar de la
  versión vieja salvo borrarla para que nadie la use por error.

Si querías que analizara contenido *distinto* al que ya está documentado en este repo (por
ejemplo, si `Correos-fast` tiene campañas o listas que no llegaron a `mujeres-rofe-correos`),
dime y las reviso directamente — no tuve acceso de archivos a esas dos carpetas en esta
sesión (solo a la carpeta que seleccionaste, `Admin-usable`).

---

## Qué hace

Inventaría el estado real de automatización (manual, script local, workflow n8n, o agente
Claude) por cada proceso identificado en [[prioridades-automatizacion-ia]], y propone —
proceso por proceso — si la siguiente pieza que falta debe ser (a) un script, (b) un workflow
n8n, o (c) un agente/skill de Claude, con criterio explícito para elegir entre las tres.

## Criterio: ¿script, workflow n8n, o agente Claude?

| Usar... | Cuando... |
|---|---|
| **Script Python + n8n (cron/webhook)** | La tarea es determinística, repetitiva, mismo input→output cada vez (ETL, sync, cálculo). Cero juicio humano necesario. |
| **Agente Claude (skill o sesión bajo demanda)** | La tarea requiere criterio, lenguaje natural, o "hazlo ahora mismo con estos parámetros distintos a lo usual" — algo que no vale la pena cablear como flujo fijo. |
| **Agente Claude + script como herramienta** | El caso normal ya tiene script (ej. `enviar_campana.py`), pero se necesita una capa que decida *qué* correr, con *qué* parámetros, a partir de una petición ambigua ("mándale un recordatorio a las que no completaron el curso de Bogotá") — el agente arma el JSON de campaña y invoca el script existente. |

La regla corta: **si ya hay un script que hace el trabajo pesado, no le construyas un agente
propio — dale al agente permiso de invocarlo.** Evita reimplementar lógica dos veces.

---

## 1. Asistente de correos (el que pediste)

**Base existente:** `scripts/mujeres-rofe-correos/` ya resuelve el 80% — plantilla HTML
parametrizada, extracción de listas desde Supabase+Excel, envío con reintentos/cuota/registro
reanudable, modo preview/piloto/masivo.

**Lo que falta para que sea "agente":**

1. **Modo agente conversacional.** Hoy correr una campaña requiere: editar JSON de campaña a
   mano → `--preview` → `--piloto` → `--enviar` por PowerShell. El agente debería poder recibir
   una petición como *"mándale a las mujeres de Bogotá que no han completado el curso un
   recordatorio del cierre de inscripciones el viernes"* y:
   - Consultar Supabase (vía las vistas ya existentes) para armar la lista filtrada.
   - Generar el JSON de campaña rellenando las variables de la plantilla.
   - Mostrar el preview HTML antes de pedir confirmación.
   - Ejecutar `enviar_campana.py --piloto` a Samuel primero, y solo tras aprobación explícita
     pasar a `--enviar`.
   - Nunca imprimir ni loguear `SMTP_PASSWORD` (ya lo hace bien `run_piloto.py` con `getpass`;
     el agente debe seguir el mismo patrón, pidiéndola en el momento, no guardándola).
2. **Generalizar a JC**, no solo Mujeres ROFÉ — hoy el sistema es específico de MR
   (`mujeres.rofe@tocaunavida.org`, plantilla con paleta MR). Para reutilizarlo en Jóvenes
   creaTIvos hace falta una segunda cuenta remitente + plantilla, mismo motor.
3. **Registro de consentimiento/opt-out.** El documento [[prioridades-automatizacion-ia]] (P8)
   ya señala esto: los correos masivos deben respetar un registro central de contacto/
   consentimiento. Ahora mismo no existe tabla de opt-out en Supabase — si alguien pide no
   recibir más correos, no hay dónde registrarlo. Es una tabla chica (`email_optout`) y un
   filtro adicional en `extraer_lista_mr_ultimos3anios.py`.
4. **Log de envíos en Supabase, no solo CSV local.** Hoy `enviados_mr_ultimos_3_anios.csv` es
   el único registro (vive en `tools/`, PII, no versionado). Subir un resumen agregado
   (cuántos enviados, cuándo, qué campaña — sin direcciones) a Supabase permitiría que el
   agente responda "¿ya le mandamos algo a esta cohorte esta semana?" sin abrir el CSV.

**Plan de implementación (2 fases):**

- **Fase A (ahora, script solamente):** ejecutar el envío pendiente de MR (2.693 destinatarias,
  "aún no ejecutado" según el README) usando el flujo manual actual. No bloquea nada más.
- **Fase B (agente):** envolver `enviar_campana.py` + `extraer_lista_mr_ultimos3anios.py` como
  herramientas invocables desde una skill de Claude (`/enviar-correo` o similar) que arma el
  JSON de campaña a partir de lenguaje natural, muestra preview, y exige confirmación explícita
  antes de cualquier envío masivo. Esta es la pieza que responde directamente a "en caso de que
  se necesite de manera rápida, hacerlo mediante el agente".

---

## 2. Mapa completo: proceso → estado → siguiente pieza

| Proceso | Estado actual | Tipo de siguiente pieza | Detalle |
|---|---|---|---|
| Consolidación Q10 → Sheets | ✅ Automatizado (n8n, 4h + Telegram) | — | Completo |
| Dashboard web (GitHub Pages) | ✅ Automatizado | — | Completo |
| Panel de Datos (Supabase + Netlify) | ✅ MVP producción | Script | Verificar 1ª corrida automática n8n; retirados en Supabase |
| Asistencia Zoom → Supabase | 🔶 Parcial | n8n | Falta cron diario 00:00 (script ya funciona) |
| Actualización BD MR (Q10↔Excel) | ✅ Automatizado (n8n diario) | — | Completo |
| **Correos masivos (MR)** | 🔶 Script v2 listo, sin agente | **Agente** | Ver sección 1 |
| Alertas de deserción/inactividad | 🔶 Solo local (`panel_riesgo.py`) | **Agente + script** | Cruce ya existe; falta convertirlo en alerta enviada (correo/Telegram) sobre la BD central en vez de ejecución manual |
| Seguimientos y recordatorios a participantes | ❌ No existe | **Agente + script** | Depende de: BD con estado consolidado (ya existe en Supabase) + reutiliza el motor de correos de la sección 1 |
| Creación de reuniones Meet/Zoom | ❌ Manual (2 personas) | n8n | Reutiliza la app Server-to-Server de Zoom que ya existe en [[zoom-asistencia]]; sin dependencia de IA |
| Grabaciones Zoom → YouTube | ❌ Manual, viable, no iniciado | n8n | Documentado en [[zoom-youtube]], no requiere agente |
| Convocatorias/selección (lectura de CVs) | ❌ No iniciado | **Agente** | Extracción de CV → campos estructurados es tarea de criterio (IA), pero debe escribir directo en tabla `postulantes` de Supabase, no en hoja aislada |
| Asistente virtual / WhatsApp | ❌ No iniciado | **Agente** | FAQ estático puede arrancar ya (base de conocimiento curada); la parte de "consultar mi estado" depende de leer Supabase |
| Organización documental (Drive) | ❌ No iniciado, pseudonimizador ya resuelve la pieza de PII | n8n + Agente liviano | Clasificación/etiquetado es candidato de "victoria rápida" — no depende de la BD |
| Reportes automáticos a financiadores | 🔶 Vistas de agregados ya existen en Supabase | **Agente** | El agente arma el reporte (docx/pdf) desde las vistas — no requiere nueva infraestructura, solo una skill de generación de documentos |
| Análisis predictivo de permanencia | ❌ No iniciado, bloqueado por P0/P1 | Script (modelo) | Requiere historial limpio; no es agente conversacional, es un job de entrenamiento/scoring |

---

## 3. Plan de acción priorizado (próximas 6-8 semanas)

1. **Ejecutar el envío pendiente de MR** con el flujo manual actual (Fase A de la sección 1) —
   no requiere desarrollo, solo decisión de Samuel sobre cuándo.
2. **Cron n8n para asistencia Zoom (00:00)** — 15 minutos de trabajo, desbloquea que el panel
   de riesgo tenga asistencia fresca todos los días.
3. **Construir el agente de correos (Fase B, sección 1)** — mayor apalancamiento porque es
   reutilizable: el mismo patrón (skill que arma JSON de campaña + confirma + invoca script)
   sirve luego para recordatorios (ítem 4) sin reescribir nada.
4. **Alerta de deserción automática** — cruce ya existe en `panel_riesgo.py`; falta
   convertir la consulta a Supabase + reusar el motor de correos del ítem 3 para notificar.
5. **Tabla `email_optout` + log de envíos agregado en Supabase** — deuda técnica antes de
   escalar los envíos masivos a JC.
6. **Creación automática de reuniones Meet/Zoom** — victoria rápida sin IA, en paralelo a lo
   anterior.
7. **Reportes a financiadores como skill de documentos** — una vez el agente de correos esté
   probado, este es el segundo caso de uso de "agente que lee Supabase y produce un
   entregable", reutilizando la misma capa de acceso a datos.

Lo que queda fuera de este horizonte (convocatorias/CVs, WhatsApp, predictivo) depende de las
entrevistas P0 y del cierre de P1 según [[prioridades-automatizacion-ia]] — no tiene sentido
adelantarlo antes.

---

## Decisiones de diseño clave

- **Un solo motor de correos, no uno por caso de uso.** Correos MR, recordatorios de
  seguimiento y alertas de deserción son la misma pieza (plantilla + lista + envío
  controlado) con distintos triggers. Construir el agente una vez sobre `enviar_campana.py`
  y reutilizarlo evita 3 implementaciones divergentes.
- **El agente nunca envía en masa sin confirmación explícita.** Sigue el patrón ya
  establecido en `enviar_campana.py --enviar` (pide escribir "ENVIAR N").
- **Credenciales SMTP nunca las maneja el agente por su cuenta** — se piden por variable de
  entorno/getpass en el momento de ejecución, igual que hoy.

## Pendiente / Próximos pasos

- Confirmar con Samuel si hay contenido en `Downloads/Correos-fast` no migrado a
  `mujeres-rofe-correos` (esta sesión no tuvo acceso de archivos a esa carpeta).
- Decidir cuenta remitente para correos de JC (paralelo a `mujeres.rofe@tocaunavida.org`).
- Diseñar el esquema mínimo de `email_optout` y `campanas_enviadas` (agregado) en Supabase.
