# BD Seguimiento de Monitorías (la "DB de 44 pestañas")

> Documentación de **arquitectura interna** de la hoja maestra manual de operaciones.
> Generada por introspección estructural (sin exponer PII) del archivo real el 2026-07-09.
> **Conexiones:** [[00-vision-global]] · [[mapa-codigo]] · [[q10-consolidacion]] · [[zoom-asistencia]] · [[pseudonimizador]]

**Estado:** Fuente de datos externa **manual** — ningún sistema le escribe automáticamente hoy.
Se consume solo en modo lectura y local (ver "Consumo desde la automatización").
**Última introspección:** 2026-07-09 sobre `BD Seguimiento de Monitorias - JC2026 (1).xlsx`.

---

## Naturaleza del archivo (crítico para refactorizar)

- **Es un Google Sheet, no un Excel nativo.** El `.xlsx` es un *export*. Evidencia dura:
  celdas con `__xludf.DUMMYFUNCTION(...)` (artefacto que deja Google al exportar fórmulas
  no soportadas como `QUERY`/`IMPORTRANGE`) y `ArrayFormula`. **El objetivo de cualquier
  refactor es el Google Sheet vivo, no este archivo.**
- **Alimentación externa:** la pestaña `Nivelación` se llena con
  `QUERY(IMPORTRANGE("…/d/15fXEc93zpcfRe-LU1-HAJxy7xCFI--5U2N-Bpwad_gw/…", "'Respuestas de formulario 1'!A:AI"), "SELECT …")`
  → hay **≥1 Google Sheet externo** (respuestas de un Form) del que este libro depende por `IMPORTRANGE`.
- **Discrepancia de conteo:** esta copia tiene **35 pestañas**, no 44 como registraba la doc previa.
  Probablemente una versión/copia distinta, o pestañas borradas. Confirmar cuál es la de producción.
- **Tamaño ~20 MB.** Carga de fórmulas enorme (ver abajo) → lenta y frágil.

---

## Modelo de datos: un hub y radios

```
                 Google Form(s) externos ──IMPORTRANGE──► Nivelación
                                                              │
  Formularios/dumps          ┌───────────── HUB ─────────────┐│
  (sin fórmulas):            │          Seguimiento          │▼
   Visita BAQ/CTG/MED        │  (903 filas · 170 cols ·      │
   Inscripción de proyecto   │   34.945 fórmulas)            │
   Diagnóstico Junio  ───────┤  roster maestro + panel de    │
   Diagnostico               │  control; lee de 11 pestañas: │
   Matrículas                │  Asistencia, Avance,          │
   Credenciales  ◄───────────┤  Barranquilla, Bogotá,        │
   Global  ◄─────────────────┤  Credenciales, Diagnostico,   │
   Novedades                 │  Diagnóstico Junio, Emoflow,  │
   Casos Críticos            │  Inscripción de proyecto,     │
   S Retirados               │  Matrículas, Nivelación       │
   Emoflow / Videos / …      └───────────────────────────────┘
                                    ▲                 ▲
        Estadísticas ──lee──────────┘                 │
        Asistencia   ──valida contra roster───────────┘
        9 hojas-ciudad (Barranquilla…Uruguay) ──lee──► Global + Credenciales (+ Seguimiento)
```

### Grafo de referencias cruzadas (quién lee a quién — fórmulas reales)
| Pestaña | Referencia a |
|---|---|
| **Seguimiento** (hub) | Asistencia, Avance, Barranquilla, Bogotá, Credenciales, Diagnostico, Diagnóstico Junio, Emoflow, Inscripción de proyecto, Matrículas, Nivelación |
| Estadísticas | Seguimiento, Guayaquil *(+ ref muerta `Seguimiento (Original) 1`)* |
| Asistencia | Seguimiento |
| Horarios-Martes-10AM | Seguimiento |
| Horarios Lógica | Seguimiento, Matrículas |
| Diagnostico | Cali, Panamá |
| Barranquilla | Credenciales, Global *(+ ref muerta `BAQ-1-Visita`)* |
| Bogotá | Credenciales, Global, Videos |
| Cali / Panamá / Quito / Uruguay | Credenciales, Global |
| Cartagena | Credenciales, Global, Seguimiento, Visita CTG |
| Medellín | Credenciales, Global, Visita MED |
| Guayaquil | Credenciales, Global, Seguimiento |
| Est. General. | Seguimiento, Uruguay |
| Uruguay-2026 | Uruguay |
| Global | Credenciales |

**Llaves de cruce:** todo el libro cruza por **`ID` (cédula, col G en Seguimiento)** y **`E-mail` (col F)** —
mismas dos llaves que usa el pipeline Q10. Los `VLOOKUP`/`COUNTIF` usan una u otra (o ambas con `OR`).

---

## Inventario de las 35 pestañas

### Núcleo con lógica (fórmulas)
| Pestaña | Estado | Filas | Cols | Fórmulas | Rol |
|---|---|---|---|---|---|
| **Seguimiento** | visible | 903 | 170 | 34.945 | **Hub**: roster maestro + panel de control por estudiante |
| **Estadísticas** | visible | 2.228 | **1.145** | 3.252 | Tablero de métricas (COUNTIFS sobre Seguimiento); doble encabezado (merges) |
| **Asistencia** | hidden | 3.028 | 88 | 12.902 | Bloques por módulo/semana; valida asistentes contra el roster ("Correcto/Incorrecto") |
| **Avance** | hidden | **24.548** | 70 | 10.773 | Volcado de avance Q10 por curso (bloques Bienvenida/Hackea/Habilidades/Emprend./IA/Lógica/HTML) |
| **Global** | hidden | 875 | 26 | 5.160 | "DATOS PERSONALES" — tabla de identidad consolidada; lee Credenciales |
| **Nivelación** | hidden | 2.085 | 26 | 5.610 | Alimentada por `IMPORTRANGE` de Form externo; asigna Ruta básica/avanzada |
| **Diagnostico** | hidden | 926 | 43 | 3.316 | Diagnóstico socioemocional/técnico de ingreso; marca duplicados |
| **Horarios Lógica** | hidden | 990 | 26 | 2.829 | Horarios IA/Lógica; VLOOKUP a Seguimiento + Matrículas |
| Est. General. | hidden | 59 | 30 | 151 | Resumen "Activos" |
| Uruguay-2026 | hidden | 180 | 26 | 76 | Form de inauguración UY |
| Horarios-Martes-10AM | hidden | 1.001 | 27 | 15 | Reasignación de horario |
| Asistencia Presenciales | hidden | 30 | 8 | 55 | Conteo asistencia presencial (merges) |

### Hojas-ciudad (mismo esquema replicado ~170 cols cada una)
| Pestaña | Filas | Cols | Fórmulas |
|---|---|---|---|
| Bogotá | 2.246 | 172 | 1.534 |
| Cartagena | 2.205 | 176 | 866 |
| Barranquilla | 988 | 171 | 823 |
| Medellín | 2.202 | 171 | 694 |
| Cali | 985 | 177 | 618 |
| Guayaquil | 2.257 | 173 | 538 |
| Uruguay | 994 | 179 | 462 |
| Panamá | 998 | 172 | 380 |
| Quito | 2.208 | 173 | 235 |

> Las 9 ciudades **replican el esquema del roster** (Nombres, Apellidos, E-mail, ID, credenciales,
> prematrículas HTML/IA/EMP, avances Q10, asistencias por sesión…). Panamá y Uruguay usan
> **doble encabezado** (fila 1 = secciones fusionadas: "Información General | Otros eventos |
> Prematriculas | Horarios y Links | Avance Cursos"). Redundancia masiva y desnormalizada.

### Fuentes de datos crudas / dumps (sin fórmulas)
| Pestaña | Filas | Contenido |
|---|---|---|
| Emoflow | 11.946 | Seguimiento emocional semanal (Semana 1–11) |
| Matrículas | 1.582 | Matrículas por curso (Hackea/Habilidades/Emprend./IA/Lógica/HTML) — **fuente de horarios y prematrículas** |
| Credenciales | 1.000 | Nombre·Apellido·Documento·**Credencial**·Correo·Ciudad (logins de plataforma) |
| S Retirados | 940 | Retirados con Motivo/Fecha de retiro/Correo de Revocación |
| Videos | 785 | Form: foto de rostro + video de 45 s (biométrico) |
| Diagnóstico Junio | 719 | Encuesta de satisfacción/autopercepción (37 preguntas) |
| Inscripción de proyecto | 472 | Form de proyectos (individual/pareja) |
| Novedades | 2.149 | Bitácora de incidencias por estudiante + causas de retiro |
| Casos Críticos | 59 | Estudiantes en riesgo/retiro con seguimiento manual |
| H-Avanzados | 68 | Form de horarios ruta avanzada |
| Uruguay-2026 / Visita BAQ/CTG/MED / Faltantes kits Bogotá | 20–180 | Forms de eventos puntuales |

---

## Consumo desde la automatización (estado actual)

Solo **lectura, local y manual** — ningún workflow n8n escribe aquí. Ver [[mapa-codigo]]:
- `tools/analizar_cupos_bd.py` → lee `Seguimiento` (columnas `Horario *`) → cupos por clase.
- `tools/exportar_sin_completar.py` → lee `Seguimiento` (columna `Grupo` = ciudad del encargado).
- `tools/verificar_retirados_bd.py` → lee `S Retirados` (cruza contra Q10 cancelados).
- **[[zoom-asistencia]]** busca **reemplazar la lógica manual de la pestaña `Asistencia`** (bloques
  horizontales por clase + columna `Validar`) por escritura automática desde n8n.
- El acceso siempre es sobre una **copia pseudonimizada** (ver [[pseudonimizador]]); las cédulas/
  nombres/correos se restauran en memoria con la clave local, nunca se suben a git.

---

## Deuda técnica / riesgos para el refactor

1. **Decenas de miles de fórmulas volátiles entre pestañas** (Seguimiento 34.9k, Asistencia 12.9k,
   Avance 10.8k, Nivelación 5.6k, Global 5.2k). VLOOKUP/COUNTIF de columna completa → recálculo lento
   y propagación de errores en cadena (un `#N/A`/`#NAME?` en un origen contamina el hub).
2. **Redundancia por desnormalización:** 9 hojas-ciudad replican el mismo esquema de ~170 columnas
   del roster. El mismo estudiante existe en su ciudad, en Global, en Credenciales y en Seguimiento.
3. **Referencias muertas / rotas:** `'Seguimiento (Original) 1'` (en Estadísticas), `'BAQ-1-Visita'`
   (en Barranquilla) y una fórmula localizada suelta `=BUSCARV(F;Global!F:G;2;FALSO)` (mezcla es/en).
4. **Dependencia externa por `IMPORTRANGE`:** Nivelación depende de un Google Sheet ajeno
   (`15fXEc93…`); si se mueve/cae, se rompe silenciosamente.
5. **PII y credenciales en claro:** columnas `Credencial`/`Contraseña`, `Usuario`, biometría en
   `Videos` (foto de rostro), contactos de emergencia en `Visita *`. Cualquier automatización debe
   pasar por el flujo de pseudonimización.
6. **Doble encabezado (merges)** en Asistencia, Estadísticas, Panamá y Uruguay → parsers deben usar
   el patrón `detectar_grupos()` (ver [[convenciones#Doble encabezado en Google Sheets]]).
7. **Solapamiento con el pipeline Q10:** las columnas `Avance Q10 - HTML/Lógica/IA/EMP/Bienvenida`
   de Seguimiento y la pestaña `Avance` duplican datos que la automatización ya extrae de Q10 a
   `h2test`. Candidato #1 a reemplazar con un feed automático en vez de VLOOKUP manuales.

---

## Método de introspección (reproducible, sin PII)

Script `scratchpad/introspeccion_bd.py` (openpyxl): extrae nombres de pestaña, dimensiones,
encabezados, celdas fusionadas, formas de fórmula y grafo de referencias cruzadas. **Redacta**
emails (`<EMAIL>`) y secuencias ≥6 dígitos (`<NUM>`) antes de imprimir — nunca vuelca valores de
datos. Salida completa: `scratchpad/estructura_bd.json`. Re-ejecutar con la ruta del archivo si
cambia la versión.
