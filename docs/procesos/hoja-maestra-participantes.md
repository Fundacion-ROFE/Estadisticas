# Hoja Maestra de Participantes (diseño futuro)

**Estado:** 📋 Diseño — NO iniciado (2026-07-10; en espera por otras prioridades)
**Procesos relacionados:** [[panel-datos-etl]] · [[mr-actualizacion-datos]] · [[bd-seguimiento-monitorias]] · [[q10-consolidacion]]

## Problema que resuelve

Hoy los datos sociodemográficos viven en dos Excel gigantes que NO se sincronizan solos:

| Fuente actual | Tamaño | Cómo llega a Supabase | Problemas |
|---|---|---|---|
| BD Seguimiento de Monitorías (JC) | 44 pestañas | `sync_sociodemograficos.py` sobre un export `.xlsx` en Downloads, **manual** | export manual, acrónimos (BAQ), edades 0 por fechas sin diligenciar, fórmulas mezcladas con datos |
| BD-Mujeres ROFÉ (MR) | 13 pestañas | `sync_sociodemograficos_mr.py` sobre un export `.xlsx` en Downloads, **manual** | export manual, texto libre (13 variantes de "nivel de estudios"), pestañas duplicadas (HerpowerED) |

El panel de Supabase queda desactualizado hasta que alguien descargue el xlsx y corra el script.
Además cada BD tiene su propio vocabulario y hay que mantener dos mapeos distintos.

## Diseño propuesto

```
   Google Form JC ──┐                              (diaria, n8n ~9:50)
   Google Form MR ──┤→ pestaña Respuestas ─→ script actualizador ─→ pestaña Maestra ─→ sync ─→ Supabase
   carga inicial ───┘      (separada)         (cruce por cédula,       (ÚNICA hoja        participants
   (seed una vez)                              solo celdas que          limpia, sin
                                               cambian)                 fórmulas)
```

**Tres piezas:**

1. **Un Sheet nuevo con UNA pestaña de datos (`Maestra`)** — 1 fila por participante, ambos
   programas (columna `Programa` los separa). Sin fórmulas, sin pestañas espejo, sin colores
   con significado. Es la única fuente que el pipeline lee.
2. **La actualización de datos de usuarios entra SOLO por Google Forms** — nadie edita la
   Maestra a mano (salvo correcciones puntuales del admin). Un script (patrón ya probado de
   [[mr-actualizacion-datos]]) cruza las respuestas por cédula y escribe solo lo que cambió.
3. **Sync diario automático a Supabase** — un único script lee la Maestra **del Sheet vivo**
   (Service Account, sin exports manuales) y hace upsert a `participants`. Se encadena al
   workflow n8n `q10-sync-supabase` después del paso de Q10.

## Columnas de la pestaña `Maestra` (propuesta)

Espejo de `participants` en Supabase — lo que el panel realmente consume. Fila 1 = headers
exactos; validación de datos (dropdown) en toda columna categórica.

| # | Columna | Tipo / valores permitidos | Obligatoria | Notas |
|---|---|---|---|---|
| A | `Cedula` | solo dígitos | ✅ llave | nunca se edita por Form (identifica la fila) |
| B | `Programa` | `JC` / `MR` | ✅ | separa las dos secciones ([[panel-datos-etl#Separación JC / MR]]) |
| C | `Nombre Completo` | texto | ✅ | |
| D | `Email` | email válido | ✅ | llave secundaria (cruce con Q10) |
| E | `Celular` | 10 dígitos | | |
| F | `Ciudad` | texto | | ciudad de residencia real |
| G | `Grupo` | dropdown: Barranquilla, Bogotá, Cali, Cartagena, Medellín, Guayaquil, Quito, Panamá, Uruguay | JC | nombre completo — se acaban los acrónimos BAQ/BOG |
| H | `Fecha Nacimiento` | fecha dd/mm/yyyy | | la edad NO se guarda: se deriva en el sync (fix de las edades 0) |
| I | `Genero` | dropdown: Femenino, Masculino, No binario, LGBTIQ+, Prefiere no responder | | |
| J | `Nivel de Estudios` | dropdown: Primaria, Bachillerato, Técnica/Tecnóloga, Profesional, Postgrado | | mapea 1:1 al enum de Supabase |
| K | `Estrato` | dropdown: 1-6 | | |
| L | `Estado Civil` | dropdown: Soltero/a, Casado/a, Unión libre, Divorciado/a-Separado/a, Otro | | |
| M | `Tipo de Vivienda` | dropdown: Propia, Arrendada, Familiar, Otra | | |
| N | `Situación Emprendimiento` | dropdown: En marcha, Tengo una idea, Me interesa, No me interesa | | unifica la encuesta JC (Diagnostico c32) y el campo libre MR |
| O | `Nombre Emprendimiento` | texto | | solo si N = "En marcha" |
| P | `Fecha Actualización` | fecha, la escribe el script | — | auditría: cuándo se tocó la fila |
| Q | `Origen` | `seed` / `form` / `manual`, lo escribe el script | — | de dónde salió el último dato |

**Reglas de la pestaña (las mismas que ya nos costaron incidentes):**
- **Cero fórmulas en `Maestra`** — una fórmula rota en un header tumbó el pipeline completo
  el 2026-07-08 ([[q10-consolidacion#Gotchas]]). Análisis y tableros van en OTRO Sheet que
  importe con `IMPORTRANGE`.
- Nada de columnas extra a la derecha sin avisar (el sync ignora lo que no conoce, pero
  documentarlo).
- La cédula es la llave: los typos de cédula se detectan con el clasificador de
  [[mr-actualizacion-datos]] (≥2 señales), nunca se corrigen solos.

## Los Forms (actualización de usuarios)

- **Un Form por programa** (JC y MR) — misma estructura, listas de opciones idénticas a los
  dropdowns de la Maestra (así el script no necesita mapeos de texto libre).
- Campos del Form = columnas C-O (el participante NO puede cambiar su cédula; la cédula se
  pide solo para identificarse).
- Respuestas caen en pestaña(s) `Respuestas` del mismo Sheet (separadas de `Maestra`).
- **Script actualizador** (adaptar `actualizar_bd_mr.py`, que ya hace exactamente esto para
  BD-Mujeres): dedup por cédula quedándose con la marca temporal más reciente, comparación
  insensible a tildes, vacío nunca sobreescribe, fila nueva solo si la cédula no existe y no
  es typo (color naranja para revisión humana), `Fecha Actualización` = fecha de la corrida.
- Schedule n8n diario (patrón del workflow `mr-actualizacion-datos`, 9:30).

## Sync diario a Supabase

- Nuevo `sync_hoja_maestra.py` que **reemplaza a los dos syncs actuales** (`sync_sociodemograficos.py`
  y `sync_sociodemograficos_mr.py`): lee `Maestra` vía Sheets API (Service Account de siempre),
  deriva `edad` desde `Fecha Nacimiento`, mapea dropdowns → enums (mapeo trivial, 1:1) y hace
  upsert a `participants` por cédula.
- Se encadena en el workflow n8n `q10-sync-supabase` DESPUÉS de `cargar_supabase` (~9:50):
  Q10 primero (crea participantes nuevos), sociodemográficos después (los enriquece).
- ⚠️ Recordar el gotcha del wipe ([[panel-datos-etl#Gotchas]]): el sync manda SOLO las columnas
  con dato — un null explícito en un upsert merge-duplicates BORRA lo que había.

## Migración (cuando se retome)

| Fase | Qué | Esfuerzo estimado |
|---|---|---|
| 1 | Crear Sheet + pestaña Maestra con validaciones; seed desde Supabase actual (que ya consolidó BD monitorias + BD-Mujeres + Q10) — un script de volcado, no re-mapear los Excel | 1 sesión |
| 2 | Crear los 2 Forms + adaptar `actualizar_bd_mr.py` al nuevo destino; corrida de prueba con dry-run | 1 sesión |
| 3 | `sync_hoja_maestra.py` + encadenar a n8n; correr en paralelo con los syncs viejos 1 semana validando cuadre | 1 sesión + observación |
| 4 | Apagar los syncs de xlsx; las BDs viejas quedan como archivo histórico (solo lectura) | trivial |

**Qué NO cambia:** Q10 sigue siendo la fuente de matrículas/avance/cursos (eso ya es automático
diario); la Maestra es solo sociodemográficos. Las BD viejas no se borran — dejan de ser fuente.

## Decisiones pendientes de Samuel (antes de implementar)

- [ ] ¿Un solo Form con sección por programa o dos Forms separados? (propuesta: dos, más simples)
- [ ] ¿Quién administra la Maestra? (correcciones manuales puntuales, revisión de filas naranjas)
- [ ] ¿Se pide algo en el Form que hoy no está en el panel? (agregarlo a la Maestra desde el
  día 1 cuesta nada; agregarlo después implica migración)
- [ ] ¿Los monitores de ciudad siguen llenando la BD de monitorías para SU operación? (la Maestra
  no la reemplaza para gestión operativa, solo como fuente del panel)
