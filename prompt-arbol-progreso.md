# PROMPT PARA CLAUDE CODE — "Árbol ROFÉ": el ecosistema de automatización como árbol vivo

> **Cómo usar:** copia TODO este archivo como primer mensaje en Claude Code, con el MCP de
> 21st.dev (Magic) activo. Crear el proyecto en una carpeta nueva `arbol-progreso/`
> (independiente — NO tocar el repo Estadisticas).

---

## 0. Tu rol y la misión

Actúa como desarrollador frontend senior experto en visualización de datos y motion design
(nivel Awwwards). Vas a construir **una sola página web** que corre local (`npm run dev`) y
que después, con autorización, se publicará en Netlify vía GitHub — por eso debe ser 100%
estática.

La página es un **árbol animado, orgánico e interactivo** que representa todo el ecosistema
de automatización e IA que Samuel Rojas construyó para la Fundación ROFÉ en ~4 semanas.

**Audiencia: su jefe (dirección, perfil no técnico).** En menos de 5 minutos frente a la
pantalla debe entender:

1. Todo lo que ya está hecho y funcionando (y desde cuándo).
2. Lo que está en construcción y su % de avance.
3. Todo lo que falta — y por qué cada departamento nuevo significa **más ramas** del árbol.
4. Que una sola persona, contratada como soporte técnico, está cubriendo 7 roles.
5. Cuánto dinero se ahorra haciéndolo local/propio (n8n self-hosted, dashboards que
   sustituyen licencias tipo Power BI, hosting gratuito).

No es un diagrama ni un organigrama ni un mindmap: **es un árbol que se ve como árbol de
verdad** (anatomía realista — sección 5), crece en pantalla, se mece, se puede explorar con
zoom libre, y cada parte tiene significado y es clickeable con foco de cámara (sección 7.0).

---

## 1. Regla de oro de la composición

**Importancia = cercanía al tronco.**

- El tronco es lo más crítico de todo: la **BD centralizada** (la unión de todas las fuentes
  de datos). Todo lo demás nace de ahí.
- Las ramas más bajas y gruesas son los frentes de mayor prioridad y mayor avance.
- Las ramas altas y delgadas son el futuro: los departamentos que pidieron consultoría IA y
  las áreas aún no iniciadas. Se ven como ramas jóvenes con yemas — el mensaje visual es
  "el árbol quiere seguir creciendo, necesita tiempo/recursos".
- Las raíces (bajo la línea del suelo) son la infraestructura invisible que sostiene todo.

El orden de prioridad ya está definido (P0–P8 en los datos de la sección 4). Respétalo.

---

## 2. Stack (obligatorio)

- **Vite + React + TypeScript + Tailwind CSS + framer-motion.**
- **d3-zoom** para la cámara (zoom libre + foco al click — spec en sección 7.0). Es la
  ÚNICA pieza de d3 permitida: el layout del árbol sigue siendo artesanal.
- Recursos externos permitidos: Google Fonts, y texturas/ruido sutiles vía CDN si hicieran
  falta — aunque preferir filtros SVG nativos (`feTurbulence`) para no depender de assets.
- Componentes de UI (drawer lateral, cards, KPI stats, timeline, badges, tooltips, modales):
  pedirlos al **MCP de 21st.dev (Magic)** con estética dark elegante. Si el MCP no responde,
  construir equivalentes estilo shadcn/ui a mano — no bloquearse.
- **El árbol es SVG artesanal**: paths bézier orgánicos de contorno cerrado con taper
  continuo (tronco → rama → ramita), construidos según la anatomía de la sección 5.
  **Prohibido** usar layouts automáticos de grafos (d3.tree, dagre, mermaid, react-flow):
  debe parecer un árbol real, no un diagrama.
- La **geometría se genera desde los datos** (`lib/geometria.ts`): agregar una rama u hoja
  nueva en el archivo de datos debe funcionar sin tocar componentes.
- 100% estático, sin backend, sin localStorage obligatorio. `npm run build` debe producir
  un sitio deployable a Netlify tal cual.
- **Todos los datos y textos viven en `src/data/arbol.data.ts`** — actualizar el avance
  semana a semana = editar ese único archivo.

---

## 3. Metáfora del árbol (mapeo semántico exacto)

| Parte | Significa | Tratamiento visual |
|---|---|---|
| **Raíces** | Infraestructura que sostiene todo (n8n local, túnel fijo, Service Accounts, seguridad) | Bajo una línea de "suelo", semitransparentes; hover las ilumina |
| **Tronco** | BD centralizada Supabase — la unión de toda la data. Prerrequisito de casi todo | Grueso, con vetas y un **anillo de progreso 70%**; clickeable |
| **Ramas bajas gruesas** | Frentes prioritarios con mayor avance (participantes, analítica) | Follaje denso y verde |
| **Ramas medias** | Frentes en construcción (Workspace, web MR) | Follaje parcial + brotes |
| **Ramas altas delgadas** | Frentes futuros: consultoría IA por departamento, convocatorias, WhatsApp, documental, marketing | Ramas desnudas con yemas punteadas |
| **Hojas** | Procesos/tareas individuales | Verde intenso = hecho · verde claro con pulso suave = en curso · yema gris punteada = pendiente |
| **Frutos ámbar** | Entregables públicos ya vivos (con link real) | Brillo sutil; click abre el link en pestaña nueva |
| **Anillos del tronco** (detalle en drawer) | Los roles que Samuel acumula | Se listan al clickear el tronco o en el panel Roles |

El árbol comunica el estado global de un vistazo: zonas frondosas = hecho, ramas peladas =
por hacer. Un contador de **progreso global ponderado** (calculado desde los datos, no
hardcodeado) acompaña en el header.

---

## 4. DATOS REALES — usar EXACTAMENTE estos, no inventar NADA

Lo que falte se marca `[EDITAR]` para que Samuel lo complete. Este bloque es el contenido
íntegro de `src/data/arbol.data.ts` (ajusta tipos TS como convenga):

```ts
export const meta = {
  titulo: "Ecosistema de Automatización e IA — Fundación ROFÉ",
  subtitulo: "Jóvenes creaTIvos · Mujeres ROFÉ",
  autor: "Samuel Rojas",
  corteDatos: "2026-07-15",
  inicio: "junio 2026", // ~4 semanas de trabajo al corte
};

export const kpis = [
  { etiqueta: "Procesos automatizados en producción", valor: "8" },
  { etiqueta: "Frentes en construcción", valor: "3" },
  { etiqueta: "Frentes futuros identificados", valor: "8" },
  { etiqueta: "Participantes únicos consolidados", valor: "4.553" },
  { etiqueta: "Matrículas históricas 2023–2026", valor: "18.195" },
  { etiqueta: "Costo mensual de infraestructura", valor: "$0" },
];

// ============ RAÍCES ============
export const raices = [
  { id: "n8n", nombre: "n8n self-hosted (PC local)", detalle: "Orquestador de todos los flujos. Arranca solo con la sesión de Windows (Task Scheduler). Versión 2.8.4." },
  { id: "tunel", nombre: "Túnel con dominio fijo (ngrok)", detalle: "Recibe los webhooks de Telegram y Zoom sin pagar servidor. Antes el túnel rotaba y se caía; ahora es estable." },
  { id: "google", nombre: "Service Accounts Google Workspace", detalle: "Identidad técnica por proceso para Sheets/Drive — sin usar contraseñas personales." },
  { id: "seguridad", nombre: "Seguridad y privacidad", detalle: "Los datos personales NUNCA salen a repositorios públicos: solo cifras agregadas. RLS en Supabase, pseudonimizador propio, y purga verificada de secretos en git (2026-07-14)." },
  { id: "red", nombre: "Red corporativa dominada", detalle: "Patrón SSL corporativo estandarizado para Python, git y n8n — cualquier script nuevo funciona a la primera." },
];

// ============ TRONCO ============
export const tronco = {
  id: "bd-central",
  nombre: "Base de Datos Centralizada (Supabase)",
  estado: "en-progreso" as const,
  progreso: 70,
  lema: "La unión de todas las fuentes de datos: decide si lo demás se construye una vez… o se reconstruye muchas veces.",
  queEs: "Una sola fuente de verdad para toda persona que pasa por la fundación: identidad única cruzada por email/cédula, historial completo por cohorte y programa.",
  logros: [
    "MVP en producción desde 2026-07-10, con panel público en Netlify",
    "2.875 participantes históricos únicos + cohorte 2026 con identidad cruzada",
    "18.195 matrículas consolidadas (cohortes 2023–2026, programas JC y MR)",
    "Sociodemográficos integrados: 775 JC + 531 MR (99% de la cohorte 2026)",
    "ETL diario automático (n8n, 9:45 am) que corrige en origen los filtros insuficientes de Q10",
    "Cuadre verificado 9/9 exacto contra el dashboard canónico",
    "Filtro por 9 ciudades en todos los gráficos (2026-07-14)",
  ],
  falta: [
    "Incorporar las fuentes paralelas que revelen las entrevistas por departamento",
    "Diccionario de datos y reglas de escritura (quién escribe qué y dónde)",
    "Conectar el Power BI de la fundación directo a Supabase → desaparecen los exportes manuales",
    "Asistencia e interacciones (correo, formularios) como tablas de eventos",
  ],
  valor: "5 de las 7 áreas que pidió dirección son preguntas sobre participantes. Sin esta BD, cada automatización responde con una versión distinta de la verdad.",
  links: [{ etiqueta: "Panel en producción", url: "https://classy-pasca-eecdd6.netlify.app" }],
};

// ============ RAMAS (orden = prioridad; índice 0 = rama más baja y gruesa) ============
export const ramas = [
  {
    id: "participantes",
    nombre: "Gestión inteligente de participantes",
    prioridad: "P2",
    estado: "en-progreso" as const,
    progreso: 60,
    queEs: "Que la información de cada participante se recoja, ordene y actualice sola.",
    hojas: [
      { id: "q10", nombre: "Consolidación Q10", estado: "completado", fecha: "2026-06-25",
        detalle: "Bot de Telegram + actualización automática cada 4 horas. 1.145 estudiantes 2026 · 4.553 históricos. Antes: descargas y copiados manuales." },
      { id: "riesgo", nombre: "Panel de riesgo (escritorio)", estado: "completado", fecha: "2026-06-26",
        detalle: "5 vistas interactivas que cruzan avance × matrícula × asistencia. Datos sensibles solo en el PC local, jamás publicados." },
      { id: "retirados", nombre: "Panel de retirados", estado: "completado", fecha: "2026-07-02",
        detalle: "Pipeline de estudiantes cancelados con etapa de retiro. Cohorte 2026: 82 retirados únicos (353 históricos)." },
      { id: "bd-mr", nombre: "Actualización diaria BD Mujeres ROFÉ", estado: "completado", fecha: "2026-07-08",
        detalle: "Formulario → base de datos con cruce por cédula, todos los días 9:30 am. Backfill inicial: 286 filas actualizadas + 24 nuevas detectadas." },
      { id: "zoom-asistencia", nombre: "Asistencia Zoom automática", estado: "completado", fecha: "2026-07-13",
        detalle: "Webhooks de Zoom → 704 registros → promedio de asistencia por estudiante (490) visible en el panel de riesgo. Pendiente menor: programar el cron diario 00:00 en n8n." },
      { id: "alertas", nombre: "Alertas automáticas de deserción", estado: "pendiente",
        detalle: "Aviso por correo/Telegram cuando alguien entra en riesgo (asistencia + avance + estado). Requiere terminar el tronco: hoy ese cruce solo existe en un script local." },
      { id: "recordatorios", nombre: "Recordatorios a participantes", estado: "pendiente",
        detalle: "Seguimientos automáticos. Necesita contacto + estado + historial de envíos en un solo lugar (la BD)." },
    ],
  },
  {
    id: "analitica",
    nombre: "Analítica y toma de decisiones",
    prioridad: "P3",
    estado: "en-progreso" as const,
    progreso: 55,
    queEs: "Que dirección y los financiadores vean cifras vivas sin que nadie arme reportes a mano.",
    hojas: [
      { id: "dashboard", nombre: "Dashboard institucional web", estado: "completado", fecha: "2026-06-26",
        detalle: "4 pestañas (Q10, Avance, Comparativo, Admin) + panel Mujeres ROFÉ + panel de aprobación por cohorte + tendencia con historial diario. Rediseñado a pedido del supervisor (2026-07-07) y refactorizado en 3 fases.",
        fruto: { etiqueta: "Ver dashboard", url: "https://fundacion-rofe.github.io/Estadisticas/dashboard/" } },
      { id: "panel-netlify", nombre: "Panel de datos moderno (Netlify)", estado: "completado", fecha: "2026-07-10",
        detalle: "Frontend Next.js sobre la BD central: filtros por ciudad/programa/cohorte, demografía, emprendimiento, historial. En mejora continua.",
        fruto: { etiqueta: "Ver panel", url: "https://classy-pasca-eecdd6.netlify.app" } },
      { id: "powerbi", nombre: "Power BI conectado a la BD viva", estado: "pendiente",
        detalle: "La fundación ya paga Power BI: conectarlo a Supabase elimina los exportes manuales. A mediano plazo, los dashboards propios pueden reemplazar licencias." },
      { id: "reportes", nombre: "Reportes automáticos a financiadores", estado: "pendiente",
        detalle: "Generados desde las vistas agregadas (mismo patrón sin datos personales ya validado)." },
      { id: "predictivo", nombre: "Modelo predictivo de permanencia", estado: "pendiente",
        detalle: "Anticipar deserción entrenando con las 4 cohortes ya consolidadas. Imposible sin el tronco terminado." },
    ],
  },
  {
    id: "workspace",
    nombre: "Ecosistema Google Workspace",
    prioridad: "P4",
    estado: "en-progreso" as const,
    progreso: 35,
    queEs: "Que Calendar, Gmail, Sheets y Drive trabajen solos, orquestados por n8n.",
    hojas: [
      { id: "meet", nombre: "Creación automática de reuniones Meet/Zoom", estado: "pendiente",
        detalle: "Hoy 2 asistentes lo hacen a mano. Victoria rápida: reutiliza la app de Zoom ya construida para asistencia." },
      { id: "zoom-youtube", nombre: "Grabaciones Zoom → YouTube", estado: "pendiente",
        detalle: "Subida manual hoy. Ya documentado y viable (2026-07-03) reutilizando la misma app de Zoom." },
      { id: "gmail", nombre: "Clasificación de correo + borradores con IA", estado: "pendiente",
        detalle: "n8n + IA. Es la misma pieza que luego envía los recordatorios a participantes." },
      { id: "sheets-interfaz", nombre: "Sheets como interfaz, no como almacén", estado: "pendiente",
        detalle: "Migrar la lógica que hoy vive en fórmulas hacia la BD. La consolidación Q10 ya resolvió su parte." },
    ],
  },
  {
    id: "web-mr",
    nombre: "Website Mujeres ROFÉ",
    prioridad: "extra",
    estado: "en-progreso" as const,
    progreso: 15,
    queEs: "Mantenimiento y evolución del sitio institucional (Angular + Express + Mongo en DigitalOcean).",
    hojas: [
      { id: "web-mr-doc", nombre: "Documentación inicial del sitio", estado: "completado", fecha: "2026-07-07",
        detalle: "Arquitectura levantada y documentada. Bloqueado por: definir alcance de cambios + clonar repos remotos." },
    ],
  },
  {
    id: "consultoria",
    nombre: "Consultoría IA por departamento",
    prioridad: "P0 — ordenado por dirección, va primero",
    estado: "pendiente" as const,
    progreso: 0,
    queEs: "Entrevista individual con cada rol de la oficina para levantar tareas repetitivas, fuentes de datos paralelas y dolores → matriz necesidad × rol × frecuencia × impacto. CADA DEPARTAMENTO SE CONVIERTE EN UNA RAMA NUEVA DE ESTE ÁRBOL.",
    // Sub-ramas jóvenes con yemas — visualmente deben verse como brotes queriendo crecer:
    brotes: [
      { id: "d-monitores", nombre: "Monitores / monitorias" },
      { id: "d-coordinacion", nombre: "Coordinación" },
      { id: "d-contabilidad", nombre: "Contabilidad" },
      { id: "d-programacion", nombre: "Programación / desarrollo" },
      { id: "d-comunicaciones", nombre: "Comunicaciones y marketing" },
      { id: "d-direccion", nombre: "Dirección" },
    ],
    hojas: [],
  },
  {
    id: "convocatorias",
    nombre: "Convocatorias y selección",
    prioridad: "P5",
    estado: "pendiente" as const,
    progreso: 0,
    queEs: "Lectura de hojas de vida con IA, clasificación y ranking de candidatos, correos del proceso.",
    hojas: [
      { id: "cv", nombre: "Lectura y ranking de CVs", estado: "pendiente",
        detalle: "Los postulantes de hoy son los participantes de mañana: deben nacer en la BD central, no en otra hoja aislada." },
    ],
  },
  {
    id: "asistentes",
    nombre: "Asistentes virtuales / WhatsApp",
    prioridad: "P6",
    estado: "pendiente" as const,
    progreso: 0,
    queEs: "Chatbot web y WhatsApp 24/7 con escalamiento humano.",
    hojas: [
      { id: "faq", nombre: "Bot FAQ (programas, requisitos, fechas)", estado: "pendiente",
        detalle: "Puede arrancar sin la BD, con base de conocimiento curada." },
      { id: "whatsapp", nombre: "WhatsApp Business con consulta de estado real", estado: "pendiente",
        detalle: "\"¿Cómo va mi curso?\" solo tiene respuesta real si el bot consulta la BD. API de Meta tiene costo — presupuestar." },
    ],
  },
  {
    id: "documental",
    nombre: "Organización documental institucional",
    prioridad: "P7",
    estado: "pendiente" as const,
    progreso: 10,
    queEs: "Clasificación y etiquetado automático en Drive, resúmenes de informes.",
    hojas: [
      { id: "pseudonimizador", nombre: "Pseudonimizador web", estado: "completado", fecha: "2026-06-30",
        detalle: "Compartir Excel sin exponer datos personales: procesa 22 MB / 44 pestañas directamente en el navegador. Ya publicado; pendiente demo al equipo.",
        fruto: { etiqueta: "Ver herramienta", url: "[EDITAR: URL del pseudonimizador en GitHub Pages]" } },
      { id: "drive", nombre: "Clasificación documental en Drive", estado: "pendiente",
        detalle: "Workflow n8n + IA autocontenido. Buen candidato a victoria rápida según lo que digan las entrevistas." },
    ],
  },
  {
    id: "marketing",
    nombre: "Marketing y difusión",
    prioridad: "P8",
    estado: "pendiente" as const,
    progreso: 0,
    queEs: "Generación de contenidos, correos masivos y segmentación de audiencias.",
    hojas: [
      { id: "segmentacion", nombre: "Segmentación de audiencias", estado: "pendiente",
        detalle: "Segmentar = consultar la BD por cohorte, ciudad, estado, programa. Depende del tronco." },
      { id: "contenidos", nombre: "Generación de contenidos con IA", estado: "pendiente",
        detalle: "Puede avanzar en paralelo. Área candidata al plan de contratación futuro — hoy no hay quien la opere." },
    ],
  },
];

// ============ PANEL: ROLES (anillos del tronco) ============
export const roles = {
  mensaje: "1 persona · 7 roles",
  nota: "El cargo contratado es el primero de la lista. El plan de contratación futuro (p. ej. marketing) libera ramas para que el árbol crezca más rápido.",
  items: [
    { rol: "Soporte técnico", nota: "El cargo contratado" },
    { rol: "Backend / ETL", nota: "Python: pipelines Q10 → Sheets → Supabase" },
    { rol: "Frontend", nota: "Dashboard institucional + panel Next.js en Netlify" },
    { rol: "Ingeniería y análisis de datos", nota: "BD central con identidad única, 4 cohortes, cuadre 9/9 verificado" },
    { rol: "DevOps", nota: "n8n self-hosted, túnel fijo, arranque automático, deploy continuo" },
    { rol: "Seguridad y privacidad", nota: "Publicación sin PII, RLS, pseudonimizador, purga de secretos en git" },
    { rol: "Consultoría IA interna", nota: "Entrevistas por departamento ordenadas por dirección (P0)" },
  ],
};

// ============ PANEL: AHORRO (cifras de referencia — Samuel las ajusta) ============
export const ahorro = {
  nota: "Cifras mensuales de referencia en USD — [EDITAR] antes de presentar.",
  items: [
    { propio: "n8n self-hosted en PC local", evita: "n8n Cloud / Zapier / Make", usdMes: "[EDITAR ~20–50]" },
    { propio: "Dashboards web propios (GitHub Pages + Netlify, gratis)", evita: "Licencias Power BI Pro por usuario que solo consulta", usdMes: "[EDITAR ~14/usuario]" },
    { propio: "Supabase capa gratuita", evita: "Base de datos gestionada de pago", usdMes: "[EDITAR ~25]" },
    { propio: "Túnel ngrok gratuito con dominio fijo", evita: "Servidor/VPS para webhooks", usdMes: "[EDITAR ~6–12]" },
  ],
};

// ============ PANEL: USO DE IA ============
export const usoIA = {
  hoy: [
    "Desarrollo asistido con Claude Code: 8 procesos en producción + BD central + 2 frontends, construidos por 1 persona en ~4 semanas",
    "Documentación viva: cada sesión de trabajo queda registrada en bitácora y notas de proceso (Obsidian)",
  ],
  siguiente: [
    "Alertas de deserción con criterio (cruce asistencia × avance × estado)",
    "Clasificación de correos y borradores automáticos (Gmail + n8n)",
    "Lectura y ranking de hojas de vida en convocatorias",
    "Chatbot FAQ / WhatsApp consultando el estado real del participante",
    "Clasificación documental en Drive y resúmenes automáticos de informes",
  ],
};

// ============ TIMELINE DE HITOS (para la franja inferior) ============
export const hitos = [
  { fecha: "2026-06-25", hito: "Consolidación Q10 automática (bot + cada 4 h)", nodo: "q10" },
  { fecha: "2026-06-26", hito: "Dashboard institucional en línea + panel de riesgo", nodo: "dashboard" },
  { fecha: "2026-06-30", hito: "Pseudonimizador web publicado", nodo: "pseudonimizador" },
  { fecha: "2026-07-02", hito: "Pipeline de retirados + panel público", nodo: "retirados" },
  { fecha: "2026-07-07", hito: "Panel de aprobación por cohorte + rediseño de pestañas (pedido del supervisor)", nodo: "dashboard" },
  { fecha: "2026-07-08", hito: "Actualización diaria BD Mujeres ROFÉ", nodo: "bd-mr" },
  { fecha: "2026-07-09", hito: "Retirados 2026 con etapa de retiro + funnel de retención", nodo: "retirados" },
  { fecha: "2026-07-10", hito: "BD central: MVP en producción (Netlify) + doc de prioridades P0–P8", nodo: "bd-central" },
  { fecha: "2026-07-13", hito: "Asistencia Zoom automática de punta a punta", nodo: "zoom-asistencia" },
  { fecha: "2026-07-14", hito: "Filtro por ciudad en todo el panel + purga de seguridad en git", nodo: "panel-netlify" },
];
```

---

## 5. Diseño visual — el árbol debe parecer un árbol DE VERDAD

**Referencia de silueta:** una ceiba / roble maduro, de tronco poderoso y copa amplia
redondeada e irregular. Primero construye un boceto SVG estático del árbol completo y
ajústalo hasta que cualquiera diría "eso es un árbol" — no un lollipop (bola sobre palo),
no un fractal simétrico, no un diagrama. Solo entonces conecta datos, estados y animaciones.

### 5.1 Anatomía y proporciones (números concretos)

- Árbol ≈ 75–80% del alto del viewport. Copa: ~60–65% de esa altura y 1.2–1.4× más ancha
  que alta.
- **Tronco:** ancho basal ≈ 5–7% de la altura total; sube limpio ~25–30% de la altura antes
  de la primera bifurcación, con una leve curva natural (nunca un rectángulo vertical).
- **Root flare:** en el contacto con el suelo el tronco se acampana ~1.8× y se divide en
  4–6 raíces que se abren radialmente y se hunden bajo la línea del suelo.
- **Regla de Leonardo (taper realista):** en cada bifurcación, la suma de las secciones de
  las ramas hijas ≈ la sección del padre (`anchoHija ≈ anchoPadre / √nHijas`). Además toda
  rama se adelgaza de forma CONTINUA desde su base hasta la punta. Implementación: paths de
  contorno cerrado con relleno — no strokes de ancho fijo.
- **Ángulos:** las ramas primarias salen del tronco a 35–55° de la vertical. Las bajas son
  más horizontales, más LARGAS y más gruesas; las altas más verticales y cortas. Las puntas
  de todas las ramas curvan suavemente hacia arriba (los árboles buscan la luz).
- **Tres niveles de ramificación:** rama primaria → 2–3 secundarias → ramitas terminales.
  Las hojas y los frutos SOLO se insertan en ramitas terminales — jamás pegados a una rama
  gruesa.
- **Cero líneas rectas:** cada segmento es un bézier con leve curva en S; jitter orgánico
  de ±10–15% en longitudes y ángulos, con **semilla aleatoria FIJA** (el árbol debe salir
  idéntico en cada carga).

### 5.2 Materia, luz y textura

- **Corteza:** gradiente vertical marrón-gris (oscuro en centro/base, cálido en el borde
  iluminado) + `feTurbulence` + `feDisplacementMap` sutiles para bordes irregulares + 2–3
  vetas verticales tenues. Nada de rellenos planos.
- **Follaje:** por cada ramita, un racimo de 3–5 blobs orgánicos superpuestos en 3 capas de
  profundidad (fondo oscuro y desaturado → medio → frente claro con highlight). El color
  del racimo codifica el estado de su rama.
- **Hojas interactivas** (los nodos de datos): silueta de hoja real (limbo ovalado con
  punta + peciolo corto), rotaciones levemente distintas entre sí — no círculos.
- **Frutos:** esferas ámbar con highlight especular y glow suave, colgando de su ramita.
- **Luz coherente:** una sola fuente arriba-izquierda; highlights y sombras consistentes en
  tronco, ramas y follaje + sombra elíptica suave del árbol proyectada en el suelo.
- **Profundidad:** 1–2 ramas secundarias y parte del follaje pasan POR DETRÁS del tronco
  con menor opacidad/saturación.
- **Suelo:** montículo suave con gradiente y pasto sugerido; bajo tierra, un degradado más
  oscuro donde viven las raíces semitransparentes.

### 5.3 Escena y paleta

- **Fondo oscuro elegante** (grafito / azul noche con gradiente radial sutil). El árbol es
  el protagonista absoluto, centrado.
- Paleta por estado — consistente en árbol, leyenda, drawer y timeline:
  - Completado: verde esmeralda saturado.
  - En progreso: verde lima/ámbar con pulso suave + anillo o badge de %.
  - Pendiente: gris azulado, trazo punteado, yema sin abrir.
  - Frutos (links vivos): ámbar/naranja con glow sutil.
- Tipografía moderna vía Google Fonts (Inter para UI; opcional una serif elegante solo para
  el título). Números tabulares en KPIs.
- Glow y cursor pointer en todo lo clickeable; focus visible (accesibilidad teclado).
- Pensado para **proyector 16:9** primero; responsive razonable después.

## 6. Animaciones (framer-motion)

- **Secuencia de entrada (~4 s, skippable con un click):** las raíces se dibujan → el tronco
  sube (pathLength) → aparece el anillo de 70% → las ramas brotan en orden de prioridad →
  las hojas hacen pop con stagger (spring) → los frutos brillan → los KPIs cuentan (count-up).
- **Idle permanente:** vaivén suave de ramas (±1.5°, transform-origin en la base de cada
  rama, desfasado entre ramas), alguna hoja que cae ocasionalmente. Sutil, no circo.
- **Hover:** la rama sube saturación y muestra tooltip (nombre + estado + %); el resto del
  árbol baja levemente su opacidad.
- **Click:** foco cinematográfico de cámara hacia el nodo + apertura del drawer
  (spec exacta en sección 7.0).
- Respetar `prefers-reduced-motion` (entrada instantánea, sin vaivén).
- 60 fps: animar solo transform/opacity; nada de re-renders de React por frame.

## 7. Interacciones

### 7.0 Cámara: zoom libre + foco al click (requisito central)

- Todo el árbol vive dentro de un único `<g id="mundo">`; la cámara es el transform de ese
  grupo, controlado con **d3-zoom**. Nunca implementar el zoom con CSS scale del contenedor.
- **Zoom libre a cualquier parte del árbol:** rueda del mouse = zoom hacia el cursor,
  arrastrar = pan, pinch en trackpad. Límites: escala 0.6×–8×, pan acotado para nunca
  perder el árbol de vista. Doble click en zona vacía = acercamiento rápido. Controles
  flotantes `+ / − / ⌂` (⌂ = volver a ver el árbol completo).
- **Click en un nodo = foco cinematográfico:** transición suave (~700–900 ms, estilo
  `d3.interpolateZoom`) que acerca y centra el nodo en el área que queda visible JUNTO al
  drawer — compensar el ancho del drawer (~420 px) para que el panel NUNCA tape el nodo.
  El nodo queda resaltado (glow + leve escala) y el resto atenuado: debe ser obvio que ESA
  parte del árbol contiene ESA información.
- Cerrar el drawer (✕, ESC o click fuera) → la cámara regresa animada a la vista en la que
  estaba el usuario antes del click.
- Con zoom activo todo sigue funcionando: tooltips, hover y clicks (hit-areas generosas,
  mínimo ~24 px efectivos).
- Rendimiento: la cámara transforma UN solo `<g>` — jamás re-render de React por frame; el
  vaivén idle se pausa durante las transiciones de cámara.
- El modo presentación (sección 8) reutiliza ESTA misma cámara para sus 8 pasos.

### 7.1 Nodos, paneles y filtros

- **Click en CUALQUIER nodo** (raíz, tronco, rama, brote, hoja, fruto) → foco de cámara
  (7.0) + drawer lateral derecho con: título, badge de estado + %, fecha, "Qué es"
  (1 frase no técnica), "Qué se logró" (bullets), "Qué falta", "Valor para la fundación",
  links si hay. Todos los textos salen del data file.
- **KPI bar** superior sticky con los 6 KPIs + progreso global calculado.
- **Filtros:** Todo / Hecho / En curso / Futuro — el árbol atenúa lo que no aplica.
- **Timeline horizontal inferior** con los 10 hitos; click en un hito resalta su nodo en el
  árbol (usar el campo `nodo`).
- **Botones de panel:** Roles · Ahorro · IA — modales o tabs dentro del drawer.
- Leyenda flotante colapsable (qué significa cada color/forma).

## 8. Modo presentación (clave para la reunión)

Tecla `P` o botón "Presentar": tour guiado con flechas ← → de **8 pasos**, cada uno usando
la cámara de la sección 7.0 (foco animado + atenuación del resto) y una tarjeta de
narrativa de 2–3 líneas:

1. Las raíces — "todo esto corre solo, en infraestructura propia de costo $0".
2. El tronco — "la BD central: la unión de toda la data, 70% construida, cuadre exacto verificado".
3. Rama participantes — "5 procesos ya corren solos todos los días".
4. Rama analítica + frutos — "dos paneles públicos en vivo" (abrir los links).
5. Timeline — "todo esto en ~4 semanas".
6. Roles — "1 persona · 7 roles".
7. Ahorro — "hecho local y propio vs. licencias".
8. Ramas jóvenes — "cada departamento es una rama nueva: consultoría IA, convocatorias,
   WhatsApp, documental, marketing. El árbol sigue creciendo." (cierre)

Los textos de narrativa también viven en el data file.

## 9. Estructura de archivos

```
arbol-progreso/
├── src/
│   ├── data/arbol.data.ts        ← LO ÚNICO que se edita para actualizar el avance
│   ├── lib/geometria.ts          ← anatomía del árbol (sección 5): paths desde los datos
│   ├── lib/camara.ts             ← d3-zoom: zoom libre, focoEnNodo(id), reset (sección 7.0)
│   ├── components/
│   │   ├── Arbol.tsx  Tronco.tsx  Rama.tsx  Hoja.tsx  Fruto.tsx  Raices.tsx
│   │   ├── Drawer.tsx  KpiBar.tsx  Timeline.tsx  Leyenda.tsx
│   │   ├── PanelRoles.tsx  PanelAhorro.tsx  PanelIA.tsx
│   │   └── Tour.tsx
│   └── App.tsx
└── README.md                     ← cómo correr, cómo actualizar estados, cómo agregar ramas
```

## 10. Criterios de aceptación

- [ ] Parece un árbol vivo, no un grafo ni un mindmap.
- [ ] Pasa la "prueba de realismo" (sección 5): regla de Leonardo en el taper, 3 niveles de
      ramificación, root flare, curvas en S sin líneas rectas, hojas solo en ramitas
      terminales, follaje en 3 capas de profundidad, luz coherente.
- [ ] Zoom libre a cualquier parte (rueda / drag / pinch) con límites + controles `+ / − / ⌂`.
- [ ] Click en nodo = foco de cámara que centra el nodo SIN que el drawer lo tape; al
      cerrar, la cámara vuelve sola a la vista anterior.
- [ ] Lo más importante está más cerca del tronco (orden P0–P8 respetado).
- [ ] Todo nodo es clickeable y su drawer usa los textos del data file.
- [ ] Animación de crecimiento al cargar + vaivén idle, 60 fps, reduced-motion respetado.
- [ ] KPI bar + progreso global calculado (no hardcodeado).
- [ ] Paneles Roles ("1 persona · 7 roles"), Ahorro (cifras `[EDITAR]` visibles) y Uso de IA.
- [ ] Timeline con los 10 hitos, enlazada a los nodos.
- [ ] Modo presentación de 8 pasos funcionando con teclado.
- [ ] `npm run build` produce estático listo para Netlify.
- [ ] Ningún dato inventado; todo faltante marcado `[EDITAR]`.
- [ ] Cero PII: solo agregados y nombres de procesos.

## 11. Qué NO hacer

- No usar layouts automáticos de grafos (d3.tree, dagre, mermaid, react-flow).
- No árbol "lollipop" (bola verde sobre un palo) ni fractal perfectamente simétrico: manda
  la anatomía de la sección 5.
- No hojas ni frutos pegados a ramas gruesas — solo en ramitas terminales.
- No implementar el zoom con CSS scale del contenedor HTML: la cámara es el transform del
  `<g id="mundo">` del SVG (d3-zoom).
- No inventar cifras, fechas ni URLs — lo que falte se marca `[EDITAR]`.
- No backend, no base de datos, no autenticación.
- No sobrecargar el lienzo: máximo 2 niveles visibles (rama → hoja); el detalle profundo
  vive en el drawer.
- No tocar el repo `Estadisticas` existente — proyecto nuevo e independiente.

## 12. Cómo empezar

1. Muestra primero un plan corto: boceto del layout (ASCII o descripción), lista de
   componentes que pedirás a 21st.dev y orden de construcción.
2. Scaffolding Vite + Tailwind + framer-motion + d3-zoom.
3. `arbol.data.ts` con los datos de la sección 4 tal cual.
4. **Boceto estático del árbol realista** (sección 5) y ajústalo hasta que convenza →
   geometría desde datos → cámara d3-zoom (7.0) → animaciones → drawer e interacciones →
   paneles → tour.
5. Verifica el checklist de la sección 10 antes de dar por terminado.
