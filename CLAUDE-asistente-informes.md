# Asistente de Informes y Presentaciones — Fundación ROFÉ / Jóvenes creaTIvos

> **Para quién es esto:** este archivo es tu asistente. Ponlo en tu carpeta de trabajo con el
> nombre `CLAUDE.md` y a partir de ahí solo tienes que **hablarle en español normal** a Claude:
> pedirle datos, informes o presentaciones. Él ya tendrá aquí todo el contexto de la fundación,
> cómo leer los datos reales y cómo dejarte una presentación lista para PDF.
>
> **No necesitas saber de código.** Todo lo técnico de este archivo es para que *Claude* lo use por ti.

---

## 🟢 Reglas de oro (léelas una vez)

1. **Solo lectura.** Este asistente puede *consultar* la base de datos, pero **nunca** edita, borra
   ni modifica nada. Es imposible que rompa algo. Tú preguntas, él responde con datos reales.
2. **Datos reales, nunca inventados.** Todos los números salen de la base de datos en vivo. Si un
   dato no existe, Claude te lo dice — nunca lo rellena a mano.
3. **Sin datos personales.** El asistente solo ve **totales y promedios** (ej. "753 estudiantes al
   día", "88% de aprobación en Bogotá"). **No** ve nombres, cédulas ni correos de estudiantes. Eso
   es a propósito, para proteger la privacidad — y no se puede cambiar desde aquí.
4. **Presentaciones = HTML → Imprimir → Guardar como PDF.** Ese es el camino para una presentación
   o informe de alta calidad. Ver la sección "Cómo hacer una presentación".

---

## 💬 Cómo pedirle cosas (ejemplos que puedes copiar)

Solo escríbele en lenguaje natural. Ejemplos reales que este asistente puede resolver:

- *"¿Cuántos estudiantes ingresaron este año y cuántos siguen activos?"*
- *"Dame la tasa de aprobación por curso de Jóvenes creaTIvos, de mayor a menor."*
- *"Compara la aprobación entre Bogotá, Medellín y Cali."*
- *"¿Cómo va la participación en Emoflow por ciudad?"*
- *"Arma un informe de una página con el estado de la cohorte 2026."*
- *"Hazme una presentación de 5 diapositivas para stakeholders con los resultados del programa."*
- *"¿Qué % de las mujeres de Mujeres ROFÉ tiene emprendimiento?"*

Cuando pidas un informe o presentación, Claude **primero consulta los datos reales** y **luego**
arma el documento con esas cifras.

---

## 🏛️ Contexto de la fundación (lo mínimo para entender los datos)

La **Fundación ROFÉ** tiene dos programas:

| Programa | Código | Quiénes | Población 2026 |
|---|---|---|---|
| **Jóvenes creaTIvos** | `jc` | Jóvenes en formación en tecnología (lógica, desarrollo web, habilidades) | 832 ingresados |
| **Mujeres ROFÉ** | `mr` | Programa de formación y emprendimiento para mujeres | 282 |

**Definiciones que debes conocer para leer bien los números:**

- **Cohorte / "Ingresados 832":** es el total de personas que entraron al programa Jóvenes
  creaTIvos en 2026 (777 activas + 57 retiradas). Es la cifra oficial de referencia del año.
- **Aprobado:** un curso está **aprobado** cuando el avance es **mayor a 80%**.
- **Matrícula vs. estudiante:** una *matrícula* es una inscripción a **un** curso; un *estudiante*
  toma varios cursos (~7). Por eso "85% de matrículas aprobadas" y "97% de estudiantes al día"
  pueden convivir sin contradecirse.
- **Emoflow:** herramienta donde los estudiantes registran su estado de ánimo. Hoy se usa como
  **proxy de participación/compromiso** (cuánto entran al sistema), no como medida de emoción.
- **Ciudades (códigos):** los datos usan códigos de 3 letras. Traducción:

  | Código | Ciudad | Código | Ciudad |
  |---|---|---|---|
  | BOG | Bogotá | GYL | Guayaquil |
  | MED | Medellín | QTO | Quito |
  | CAL | Cali | PAN | Panamá |
  | CTG | Cartagena | UY | Uruguay |
  | BAQ | Barranquilla | | |

- **Paneles públicos ya existentes** (por si quieres enlazarlos o comparar):
  - Panel principal (Netlify): https://classy-pasca-eecdd6.netlify.app

---

## 🔌 Cómo leer los datos (esta parte es para Claude, no para ti)

> **Nota para Claude:** los datos viven en Supabase (PostgreSQL). Se consultan con la **anon key**
> de solo lectura vía la REST API de PostgREST. Esta llave es **pública por diseño** (va en el
> frontend del panel) y está protegida por RLS: solo expone agregados; cualquier tabla con datos
> personales devuelve 0 filas. Nunca intentes escribir (POST/PATCH/DELETE) — RLS lo rechaza (401)
> y además no es el propósito de este asistente.

**Conexión:**

```
SUPABASE_URL  = https://kbxptoowtnteflhrfwid.supabase.co
SUPABASE_ANON_KEY = eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtieHB0b293dG50ZWZsaHJmd2lkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODM2MzU4MDUsImV4cCI6MjA5OTIxMTgwNX0.xfj_GJYdRgPHUCpyxReKm7G7SMGTVn4oscDhakV6DSo
```

**Snippet reutilizable (Python, solo stdlib):**

```python
import json, urllib.request
URL = "https://kbxptoowtnteflhrfwid.supabase.co"
KEY = "PEGAR_ANON_KEY_DE_ARRIBA"

def consultar(objeto, params="select=*"):
    """Lee una tabla/vista de agregados. Solo GET. Devuelve lista de dicts."""
    req = urllib.request.Request(
        f"{URL}/rest/v1/{objeto}?{params}",
        headers={"apikey": KEY, "Authorization": f"Bearer {KEY}"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read() or "[]")

# Ejemplos:
consultar("cohorte_ingresos", "programa=eq.jc&select=ingresados,activos,retirados,pct_aprobados")
consultar("aprobacion_cursos", "programa=eq.jc&order=pct_completados.desc")  # nota: filtros PostgREST
consultar("v_emoflow_por_ciudad", "select=grupo_ciudad,participantes,activos_7d")
```

Sintaxis de filtros PostgREST: `columna=eq.valor`, `order=columna.desc`, `limit=N`,
`select=col1,col2`. Si un objeto trae más de 1000 filas, paginar con el header `Range` o `limit/offset`.
Si estás en un entorno corporativo con proxy SSL, añade al inicio: `import truststore; truststore.inject_into_ssl()`.

### 📚 Catálogo de datos legibles (todo son agregados, sin PII)

**Cohorte y aprobación (lo más usado para informes):**

| Objeto | Qué tiene |
|---|---|
| `cohorte_ingresos` | Por programa: `ingresados`, `activos`, `retirados`, `pct_aprobados` |
| `aprobacion_cursos` | Por curso: `cursaron`, `activos`, `aprobados`, `aprobados_retirados`, `retirados`, bandas de avance (`banda_0_25`, `banda_26_80`, `banda_81_100`), `promedio` |
| `v_cohorte_estudiantes` | Por programa: estudiantes `activos`, `al_dia`, `en_progreso`, `en_riesgo` |
| `v_cohorte_estudiantes_distribucion` | Cuántos estudiantes han aprobado 0,1,2… cursos |
| `v_programa_stats` | Resumen por programa: participantes, matrículas, completadas, promedio de avance |
| `v_curso_completion` | Por curso: matriculados, completados, en progreso, % completados, promedio |

**Por ciudad (respetan los códigos BOG/MED/…):**

| Objeto | Qué tiene |
|---|---|
| `v_curso_completion_por_ciudad` | Completación de cada curso desglosada por ciudad |
| `v_programa_stats_por_ciudad` | Participantes/matrículas/avance por ciudad |
| `v_demografia_grupo` | Por ciudad: total, edad promedio, mujeres/hombres/otros |

**Demografía y emprendimiento:**

| Objeto | Qué tiene |
|---|---|
| `cohorte_stats` | Por cohorte+programa: total participantes, con/sin emprendimiento, edad promedio |
| `v_edad_distribucion` | Distribución por rangos de edad |
| `v_emprendimiento_situacion` | Estudiantes por situación de emprendimiento (JC) |
| `v_emprendimiento_vs_cursos` | Relación emprendimiento ↔ avance en cursos (JC) |
| `v_emprendimiento_por_ciudad` | Situación de emprendimiento por ciudad |
| `v_mr_demografia` | Mujeres ROFÉ: estado civil, estudios, vivienda, estrato, edad, emprendimiento (formato `dimension`/`categoria`/`total`) |

**Emoflow (participación / compromiso):**

| Objeto | Qué tiene |
|---|---|
| `v_emoflow_resumen` | KPIs nacionales: participantes, ingresos promedio/mediana/máx, activos 7d/14d, inactivos 30d |
| `v_emoflow_por_ciudad` | Los mismos KPIs por ciudad |
| `v_emoflow_bandas` | Uso por bandas de ingresos cruzado con % de aprobación ("¿el que más entra, aprueba más?") |
| `emoflow_ingresos_diario` | Serie diaria de ingresos y usuarios activos por ciudad |
| `emoflow_actividad_semanal` | % de matrícula activa por semana y ciudad |
| `emoflow_participacion_semanal` | % de participación semanal (Completado/Real) por ciudad |

**Series de tiempo (para gráficos de evolución):**

| Objeto | Qué tiene |
|---|---|
| `historial_cursos` | Evolución diaria de matrículas y avance por curso |
| `historial_cursos_ciudad` | Lo mismo, desglosado por ciudad (desde 2026-07-14) |
| `historial_emoflow` / `historial_emoflow_ciudad` | Evolución diaria de los KPIs de Emoflow |

**Catálogo base:** `courses` (lista de cursos: nombre, cohorte, programa, estado).

> **Bloqueado a propósito (PII — devuelven 0 filas):** `participants`, `enrollments`,
> `emoflow_ingresos`, `v_puntaje_estudiante`, `asistencia_zoom`. No insistas con estos: la
> privacidad de los estudiantes está protegida por diseño. Todo lo que se necesita para informes
> ya está en los agregados de arriba.

---

## 🖼️ Cómo hacer una presentación o informe (HTML → PDF)

**El flujo, en 3 pasos:**

1. Le pides a Claude el informe/presentación → Claude consulta los datos reales y genera un
   **archivo HTML** con identidad ROFÉ.
2. Abres el archivo HTML en el navegador (doble clic).
3. **Imprimir** (`Ctrl + P`) → en Destino elige **"Guardar como PDF"** → Guardar.
   ¡Listo! Tienes una presentación/informe de alta calidad en PDF.

> 💡 **Recuérdaselo a Claude / recuérdate a ti misma:** el HTML ya viene preparado para imprimir
> (tamaño de página, saltos entre diapositivas, colores que se conservan en el PDF). Si algo se ve
> cortado, en el diálogo de impresión activa **"Gráficos de fondo"** y márgenes "Predeterminado".

### 🎨 Identidad de marca ROFÉ (para que Claude la use en cada presentación)

- **Tipografía:** Century Gothic (títulos) / Gilroy si está disponible, con respaldo Trebuchet MS, Arial.
- **Paleta oficial:**

  | Uso | Color |
  |---|---|
  | Azul principal | `#406C9E` |
  | Azul retiro / dato secundario | `#3A6FB8` |
  | Celeste claro | `#83B6DD` |
  | Verde (aprobado / positivo) | `#6EA050` |
  | Ámbar (en progreso) | `#EEC935` |
  | Naranja (en riesgo) | `#D1793F` |
  | Rojo (retirado / alerta) | `#C12D4C` |
  | Texto | `#1A2535` |
  | Fondo / superficie | `#FFFFFF` / `#F4F7FB` |
  | Gris apagado | `#6B7A94` |

- El **manual de identidad ROFÉ 2025** (logo "Aplicación 2" para fondos claros, paleta completa)
  está en el Google Drive de la fundación si necesitas el logo oficial.

### Plantilla base de presentación (Claude: reutilízala y rellena con datos reales)

```html
<!doctype html><html lang="es"><head><meta charset="utf-8">
<title>Presentación ROFÉ</title>
<style>
  :root{ --azul:#406C9E; --celeste:#83B6DD; --verde:#6EA050; --ambar:#EEC935;
         --naranja:#D1793F; --rojo:#C12D4C; --texto:#1A2535; --gris:#6B7A94; --surface:#F4F7FB; }
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:'Century Gothic','Gilroy','Trebuchet MS',Arial,sans-serif;color:var(--texto)}
  /* Cada diapositiva ocupa una página al imprimir */
  .slide{width:100%;min-height:100vh;padding:8vh 8vw;page-break-after:always;
         display:flex;flex-direction:column;justify-content:center}
  .slide:last-child{page-break-after:auto}
  h1{font-size:2.6rem;color:var(--azul);margin-bottom:1rem}
  h2{font-size:1.8rem;color:var(--azul);border-bottom:3px solid var(--celeste);
     padding-bottom:.4rem;margin-bottom:1.2rem}
  .kpis{display:flex;gap:1.5rem;flex-wrap:wrap;margin-top:1rem}
  .kpi{background:var(--surface);border-radius:14px;padding:1.4rem 1.8rem;min-width:180px}
  .kpi .num{font-size:2.4rem;font-weight:700;color:var(--azul)}
  .kpi .lbl{color:var(--gris);font-size:.95rem;margin-top:.3rem}
  table{width:100%;border-collapse:collapse;margin-top:1rem}
  th{background:var(--azul);color:#fff;text-align:left;padding:.6rem .8rem}
  td{padding:.55rem .8rem;border-bottom:1px solid #DDE4ED}
  .fuente{color:var(--gris);font-size:.8rem;margin-top:2rem}
  @media print{ body{-webkit-print-color-adjust:exact;print-color-adjust:exact} }
</style></head><body>

  <!-- Portada -->
  <section class="slide" style="background:var(--azul);color:#fff;justify-content:center">
    <h1 style="color:#fff">Título del informe</h1>
    <p style="font-size:1.3rem;opacity:.9">Fundación ROFÉ · Jóvenes creaTIvos · 2026</p>
  </section>

  <!-- Diapositiva de KPIs (rellenar con datos REALES de la base) -->
  <section class="slide">
    <h2>Estado de la cohorte</h2>
    <div class="kpis">
      <div class="kpi"><div class="num">832</div><div class="lbl">Ingresados 2026</div></div>
      <div class="kpi"><div class="num">777</div><div class="lbl">Activos</div></div>
      <div class="kpi"><div class="num">85,4%</div><div class="lbl">Aprobación</div></div>
    </div>
    <p class="fuente">Fuente: base de datos ROFÉ (Supabase) · consulta en vivo</p>
  </section>

</body></html>
```

**Reglas al armar el documento:**
- Reemplaza SIEMPRE los números de ejemplo por los que devuelva la consulta a Supabase.
- Añade una línea "Fuente: base de datos ROFÉ · fecha de consulta" al pie de cada informe.
- Para gráficos, prefiere SVG/HTML sencillos incrustados (sin librerías externas, para que el PDF
  salga idéntico sin conexión). Colores: usa la paleta de arriba.
- Un informe corto puede ser una sola página (`.slide` sin `page-break`); una presentación usa
  varias `.slide`.

---

## ✍️ Mis preferencias (rellena esto tú misma)

> Esta sección es **tuya**. Edítala directamente cuando notes que pides algo seguido o que
> prefieres cierto formato. Claude la leerá como tus reglas personales y las aplicará sin que se
> lo tengas que repetir. Borra los ejemplos entre paréntesis y pon lo tuyo.

- **Formato de mis informes:** _(ej. siempre con portada azul, KPIs primero, luego tabla por curso)_
- **Idioma / tono:** _(ej. español formal para stakeholders)_
- **Informes que pido seguido:** _(ej. "resumen mensual por ciudad", "estado de la cohorte")_
- **Cifras o definiciones que uso como referencia fija:** _(ej. cohorte JC 2026 = 832 ingresados)_
- **Cómo nombro los archivos:** _(ej. `Informe-ROFE-AAAA-MM.pdf`)_
- **Otras notas:** _(lo que quieras que Claude recuerde de tu forma de trabajar)_

---

## ✅ En resumen

- Háblale normal; él consulta datos **reales** y **solo de lectura**.
- No ve datos personales — solo totales, por diseño.
- Presentaciones: te entrega un HTML → tú haces `Ctrl+P` → **Guardar como PDF**.
- Identidad ROFÉ (azul `#406C9E`, Century Gothic) aplicada automáticamente.

*Documento de contexto generado para uso de consultoría / informes. Fuente de verdad de los
procesos: repositorio de automatizaciones de la Fundación ROFÉ.*
