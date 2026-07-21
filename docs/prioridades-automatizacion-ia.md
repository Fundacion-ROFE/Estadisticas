# Prioridades de Automatización e IA — Fundación ROFÉ (2026)

> Documento de priorización de las necesidades planteadas por la dirección
> (áreas 2–8 del documento "Necesidades de Fundación ROFÉ en IA y Automatización"),
> con el argumento técnico de por qué la **base de datos centralizada es el prerrequisito
> transversal** de casi todas ellas.
>
> Fecha: 2026-07-10 · Autor: Samuel Rojas (con Claude Code)
> Conexiones: [[00-vision-global]] · [[panel-datos-etl]] · [[q10-consolidacion]]

---

## Resumen ejecutivo

| Prioridad | Área solicitada | Dependencia de la BD central | Estado actual |
|---|---|---|---|
| **P0** | Diagnóstico por entrevistas (oficina) | — (lo alimenta) | Solicitado por dirección — **obligatorio, primero** |
| **P1** | Fundación de datos: BD centralizada (Supabase) | ES la BD | **~70% construida** — MVP en producción |
| **P2** | Gestión inteligente de participantes (área 2) | **Crítica** | ~60% ya operando (Q10, Zoom, dashboards, riesgo) |
| **P3** | Analítica y toma de decisiones (área 8) | **Crítica** | Parcial (dashboards públicos + Power BI existente) |
| **P4** | Ecosistema Google Workspace (área 7) | Alta | Parcial (Sheets/Drive ya automatizados vía n8n) |
| **P5** | Convocatorias y selección (área 3) | Alta | No iniciado |
| **P6** | Asistentes virtuales / WhatsApp (área 4) | Media–Alta | No iniciado |
| **P7** | Organización documental institucional (área 6) | Media | No iniciado (existe pseudonimizador) |
| **P8** | Marketing y difusión (área 5) | Media | No iniciado |

**Lectura rápida:** de las 7 áreas solicitadas, **5 consumen directamente datos de
participantes**. Sin una fuente única y confiable, cada automatización hereda el mismo
vicio que ya obligó a rehacer la estructura una vez (BD principal viciada, Q10 con
filtros e información insuficientes). La BD no es "otra tarea más": es el cimiento que
determina si las demás se construyen una vez o se reconstruyen varias veces.

---

## P0 — Diagnóstico por entrevistas (obligatorio, ya ordenado)

Agendar cita individual con cada integrante de la oficina para levantar:

- Tareas repetitivas que consume cada rol (candidatas a automatización).
- Fuentes de datos que cada quien mantiene por su cuenta (hojas paralelas, copias locales)
  → estas son exactamente las que vician la BD.
- Dolores con los procesos actuales (Q10, Sheets, Zoom, correo).
- Expectativas frente a IA (calibrar qué es viable vs. qué es percepción).

**Entregable:** matriz necesidad × rol × frecuencia × impacto, que ajusta las prioridades
P2–P8 de este documento. Las entrevistas también sirven para inventariar **todas** las
fuentes de datos dispersas antes de terminar el modelo de la BD central (P1) — por eso
P0 y P1 se refuerzan mutuamente, no compiten.

---

## P1 — Fundación de datos: BD centralizada

**No parte de cero.** El proyecto Supabase `panel-datos-rofe` ya existe y está en
producción (2026-07-10):

- Participantes únicos con identidad cruzada por email/cédula (2.875 históricos + cohorte 2026).
- 18.195 matrículas con historial por cohorte 2023–2026, programa JC/MR, retirados con etapa.
- Sociodemográficos JC (BD monitorias, 775) y MR (BD-Mujeres ROFÉ, 531 = 99% cohorte 2026).
- ETL diario automatizado (n8n 9:45) con normalización que corrige los filtros
  insuficientes de Q10 en origen.
- Cuadre verificado 9/9 exacto contra el dashboard canónico.
- Vistas públicas de solo-agregados (sin PII) que ya alimentan un frontend en Netlify.

**Lo que falta para que sea LA fuente única:**

1. Incorporar las fuentes que aparezcan en las entrevistas P0 (hojas paralelas por rol).
2. Definir el diccionario de datos y las reglas de escritura (quién escribe qué, dónde,
   y qué queda prohibido duplicar).
3. Conectar Power BI directamente a Supabase (ya cuentan con Power BI — se conecta vía
   PostgreSQL nativo, sin exportes manuales).
4. Asistencia (Zoom) e interacciones (correos, formularios) como tablas de eventos.

---

## P2 — Gestión inteligente de participantes (área 2)

La de mayor retorno inmediato porque **más de la mitad ya está operando**:

| Necesidad solicitada | Estado |
|---|---|
| Organización por cohortes/ciudades/programas | ✅ Hecho — Supabase modela cohorte, programa JC/MR, curso; Power BI puede leerlo ya |
| Seguimiento de asistencia | 🔶 Parcial — [[zoom-asistencia]] funcional en cuenta comunicaciones; bloqueado por Dashboard API de Zoom y cuenta soporte sin cubrir |
| Consolidación en tiempo real | ✅ Hecho — pipeline Q10 cada 4 h + ETL Supabase diario |
| Estadísticas e indicadores automáticos | ✅ Hecho — dashboard público + panel Netlify + vistas de agregados |
| Alertas de deserción/inactividad | 🔶 Parcial — `panel_riesgo` local cruza Avance × Q10; falta convertirlo en alerta automática (correo/Telegram) sobre la BD central |
| Actualización automática de bases | ✅ Hecho para Q10 y BD-Mujeres ROFÉ ([[mr-actualizacion-datos]]) |
| Seguimientos y recordatorios | ❌ Pendiente — depende de tener contacto + estado del participante en un solo lugar (BD) |

**Dependencia de la BD:** una alerta de deserción necesita cruzar asistencia + avance +
estado de matrícula **de la misma persona**. Hoy ese cruce vive en un script local
(`panel_riesgo.py`) precisamente porque las fuentes están separadas. Con la BD central,
la alerta es una consulta + un workflow n8n.

---

## P3 — Analítica y toma de decisiones (área 8)

- Dashboards automáticos: ✅ ya existen dos (GitHub Pages y Netlify) — se consolidan, no se crean.
- Reportes para financiadores: se generan desde las vistas de agregados de Supabase
  (mismo patrón sin-PII que ya está validado).
- **Análisis predictivo de permanencia:** imposible sin historial limpio. El modelo
  predictivo se entrena con las cohortes 2023–2026 que la BD ya consolida —
  este punto **no existe sin P1**.
- Power BI de la fundación se conecta a Supabase como fuente viva y desaparecen los
  exportes manuales.

---

## P4 — Ecosistema Google Workspace (área 7)

n8n local ya orquesta Sheets, Drive y Telegram con Service Accounts. Extensiones naturales:

- **Calendar + Zoom:** creación automática de reuniones (ya identificado como pendiente:
  "Creación reuniones Meet" — 2 asistentes lo hacen manual hoy). Reusa la app
  Server-to-Server de [[zoom-asistencia]].
- **Gmail:** clasificación y borradores automáticos — viable con nodos n8n + IA; los
  recordatorios a participantes (P2) usan esta misma pieza.
- **Sheets:** la consolidación solicitada ya está resuelta para Q10; lo nuevo es migrar
  la lógica que hoy vive en fórmulas hacia la BD para que Sheets sea interfaz, no almacén.

**Dependencia de la BD:** media-alta. Un recordatorio automático necesita saber *a quién*
(contacto vigente), *por qué* (estado en el programa) y *si ya se le envió* (log de
interacciones). Los tres viven naturalmente en la BD central.

---

## P5 — Convocatorias y selección (área 3)

Lectura de hojas de vida, clasificación de candidatos, ranking, entrevistas y correos
del proceso. Técnicamente viable con IA (extracción de CV → campos estructurados →
scoring contra perfil), pero:

- **Los postulantes de hoy son los participantes de mañana.** Si el proceso de selección
  escribe en su propia hoja aislada, se recrea el vicio: la misma persona existirá con
  datos distintos en selección, matrícula y seguimiento. Los candidatos deben nacer en
  la BD central (tabla `postulantes` → promoción a `participants` al ser admitidos).
- El ranking necesita perfiles definidos por programa — insumo que sale de las
  entrevistas P0 con las coordinadoras.

---

## P6 — Asistentes virtuales y WhatsApp (área 4)

Chatbot web, asistente de plataforma y WhatsApp 24/7 con escalamiento humano.

- Las respuestas de FAQ (programas, requisitos, fechas) requieren solo una base de
  conocimiento curada — eso puede arrancar sin la BD.
- Pero el valor diferencial que pide el documento ("captación de interesados",
  "orientación a usuarios") sí la requiere: un interesado captado por WhatsApp debe
  quedar registrado donde selección (P5) lo encuentre, y un participante que pregunta
  "¿cómo va mi curso?" solo recibe respuesta real si el bot consulta su estado en la BD.
- WhatsApp Business API tiene costo y proceso de aprobación de Meta — presupuestar.

---

## P7 — Organización documental (área 6) y P8 — Marketing (área 5)

Las de menor dependencia de datos de participantes y menor urgencia relativa:

- **Documental:** clasificación/etiquetado en Drive y resumen automático de informes son
  workflows n8n + IA autocontenidos. El pseudonimizador existente ya resuelve la pieza
  de compartir datos sin PII. Buen candidato a "victoria rápida" si las entrevistas P0
  revelan mucho dolor aquí.
- **Marketing:** generación de contenidos y correos masivos. La **segmentación de
  audiencias** que pide el documento sí depende de la BD (segmentar = consultar por
  cohorte, ciudad, estado, programa). Los correos masivos a participantes deben
  respetar el mismo registro de contacto/consentimiento central.

---

## Por qué la BD centralizada no es opcional

Respuesta directa al planteamiento de que "no es importante tener noción de la BD para
hacer esas tareas":

1. **Ya vivimos el costo de no tenerla.** La BD principal estaba viciada y la data de
   Q10 llegaba con filtros e información insuficientes; hubo que rehacer la estructura.
   Cada automatización que se construya sobre fuentes dispersas repite ese ciclo:
   funciona en la demo, se pudre en producción, y se reconstruye.

2. **5 de las 7 áreas son consultas sobre la misma entidad: la persona.** Alertas de
   deserción (P2), predictivo de permanencia (P3), recordatorios (P4), ranking de
   postulantes (P5), bot que responde estado (P6) y segmentación (P8) son, en el fondo,
   preguntas sobre participantes. Sin identidad única (email/cédula) y sin historial,
   cada área responde con una versión distinta de la verdad — exactamente lo que un
   financiador o la dirección no puede recibir.

3. **El costo marginal es bajo porque ya está al ~70%.** No se está proponiendo un
   proyecto nuevo de meses: Supabase ya consolida 4 cohortes con cuadre exacto y ETL
   diario. Terminarla (fuentes de las entrevistas + diccionario de datos + conexión
   Power BI) es semanas, y desbloquea todo lo demás.

4. **Automatizar sobre datos sucios multiplica el error, no lo reduce.** Un correo
   automático al email equivocado, una alerta de deserción sobre alguien ya retirado,
   un certificado a nombre mal escrito — a mano son errores puntuales; automatizados
   son errores a escala y con membrete institucional.

5. **Cada tarea hecha "sin noción de la BD" genera deuda de integración.** Es posible
   construir el clasificador de CVs o el bot de WhatsApp aislados — y al mes siguiente
   pagar el costo de conectarlos: migraciones, deduplicación, re-testing. Diseñarlos
   desde el día uno leyendo/escribiendo la BD central cuesta lo mismo y no genera deuda.

**Matiz honesto:** hay tareas que sí pueden avanzar en paralelo sin la BD —
organización documental (P7), generación de contenidos (P8), FAQ estático del bot (P6),
creación de reuniones Calendar/Zoom (P4). Son buenas victorias rápidas mientras P0 y P1
avanzan. Pero ninguna de las de alto impacto que pide el documento (alertas, predictivo,
selección, segmentación, atención personalizada) se sostiene sin ella.

---

## Ruta sugerida (90 días)

| Semanas | Frente A (datos) | Frente B (victorias rápidas) |
|---|---|---|
| 1–2 | **P0:** entrevistas + matriz de diagnóstico | Creación automática de reuniones Calendar/Zoom |
| 3–6 | **P1:** cierre de BD central (fuentes nuevas, diccionario, Power BI conectado) | P7: clasificación documental en Drive |
| 7–10 | **P2:** alertas de deserción + recordatorios sobre la BD | P6: FAQ bot web (base de conocimiento) |
| 11–13 | **P3:** reportes automáticos a financiadores + primer modelo de permanencia | P5: piloto lectura de CVs (escribiendo en la BD) |

Las entrevistas de P0 pueden reordenar los frentes — este documento se actualiza con
la matriz de diagnóstico.
