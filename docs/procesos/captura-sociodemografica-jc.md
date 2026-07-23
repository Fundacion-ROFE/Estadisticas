# Captura sociodemográfica JC (vivienda / estrato / estado civil / nivel de estudio)

**Estado:** Idea / diseño, no implementado
**Última actualización:** 2026-07-21
**Procesos relacionados:** [[mr-actualizacion-datos]] (patrón que se espeja) · [[panel-datos-etl]] (destino final en Supabase `participants`) · [[bd-seguimiento-monitorias]] (Sheet hub de JC donde viviría la pestaña nueva)

## Qué hace (propuesto)
Diseña cómo capturar para **Jóvenes creaTIvos (JC)** los 4 campos sociodemográficos que hoy
**no tienen ninguna fuente** en ese programa: `tipo_vivienda`, `estrato`, `estado_civil`,
`nivel_estudio`. Para **Mujeres ROFÉ (MR)** estos mismos 4 campos ya se recolectan y sincronizan
con éxito (ver [[mr-actualizacion-datos]] + sección "Sociodemográficos MR" de
[[panel-datos-etl]]) — este documento adapta ese mismo patrón a JC, sin inventar enums nuevos ni
tocar los campos que JC ya obtiene de otra fuente (género, edad, ciudad, emprendimiento vienen de
la BD de monitorias vía `sync_sociodemograficos.py` — este diseño **no los duplica**).

Este documento es solo diseño: **no se implementa ningún script ni Form real** hasta que se
prepare la estructura/matrícula del próximo año.

## Disparador (Trigger) propuesto
Igual que MR: **Google Form** de inscripción/actualización de datos que cada joven diligencia al
matricularse (o al actualizar sus datos), corrido por un schedule n8n diario (mismo patrón que
`mr-actualizacion-datos`, workflow `LgkDbNPERYgKMrYj`).

## Flujo resumido propuesto
1. Form **"Actualización de datos sociodemográficos JC"** (nuevo) — el joven responde cédula +
   los 4 campos (ver preguntas abajo).
2. Script **`actualizar_bd_jc_socio.py`** (nuevo, espejo de `actualizar_bd_mr.py`): lee las
   respuestas del Form, cruza por cédula contra la pestaña destino, escribe solo lo que cambia,
   clasifica las cédulas sin match en retiradas / posibles typos / nuevas reales (misma lógica de
   `actualizar_bd_mr.py`: ≥2 señales entre correo/celular/nombre/cédula parecida).
3. Script **`sync_sociodemograficos_jc_extra.py`** (nuevo, espejo de
   `sync_sociodemograficos_mr.py`): lee la pestaña destino, mapea texto libre → los mismos 4
   enums ya existentes, y hace upsert en Supabase `participants` **restringido a
   `programa=jc`**, escribiendo *solo* `tipo_vivienda`, `estrato`, `estado_civil`,
   `nivel_estudio` (no toca género/edad/ciudad/emprendimiento — esos siguen viniendo de
   `sync_sociodemograficos.py`).
4. n8n: schedule diario (candidato a encadenarse a `q10-sync-supabase` o correr independiente,
   como hoy corre `sociodemograficos-semanal` para JC) → alerta Telegram en error, no
   `stopAndError` (no bloquea el pipeline crítico, mismo criterio ya usado para los syncs
   sociodemográficos existentes).

## Fuentes de datos / APIs usadas (propuestas)
- Google Form nuevo (Google Forms API / Sheet de respuestas vinculado), mismo Service Account
  `q10-automatizacion@n8n-automatizacion-q10.iam.gserviceaccount.com` que el resto del proyecto.
- Google Sheets API — pestaña destino (ver estructura abajo).
- Supabase REST API — proyecto `panel-datos-rofe`, tabla `participants` (mismos enums:
  `nivel_estudio_type`, `estado_civil_type`, `vivienda_type`, `estrato` entero 1-6).

## Destino de los datos (propuesto)
**Opción recomendada:** nueva pestaña **`Sociodemograficos`** dentro del Sheet ya existente
**"BD Seguimiento de Monitorias"** (id `1ggzoJeZR3fS6AwRCLoGeYA5HEp_B7zvOwFGlGwny0l8`, el mismo
hub gigante que ya tiene `Seguimiento`, `Diagnostico`, `Estadísticas`, `Avance`, etc.) — evita
crear un Sheet nuevo que administrar y sigue el patrón de "un solo hub, muchas pestañas" que ya
usa JC. (Alternativa descartada por ahora: un Sheet dedicado tipo "BD-Mujeres ROFÉ" — tendría
sentido solo si el equipo prefiere aislar por completo esta captura del resto de JC; no hay
motivo hoy para esa separación.)

### Columnas propuestas de la pestaña `Sociodemograficos` (headers fila 1)
| Columna | Contenido | Notas |
|---|---|---|
| A | `#` | correlativo, igual que General de MR |
| B | `Cédula` | **llave de cruce** — nunca se sobreescribe, normalizada solo dígitos |
| C | `Nombre Completo` | para detección de typos (señal, no se usa para escribir en Supabase) |
| D | `Correo` | señal de match, opcional |
| E | `Celular` | señal de match, opcional |
| F | `Nivel de estudios` | texto libre del Form → mapea a `nivel_estudio_type` |
| G | `Estrato` | número 1-6 |
| H | `Estado civil` | texto libre del Form → mapea a `estado_civil_type` |
| I | `Tipo de vivienda` | texto libre del Form → mapea a `vivienda_type` |
| J | `Fecha Actualización` | fecha de la corrida, dd/mm/yyyy — igual criterio que MR (fecha de
corrida, no marca temporal del Form) |

### Cruce por cédula (mismo criterio que `actualizar_bd_mr.py`)
- Normalizar cédula a solo dígitos antes de comparar.
- Deduplicar respuestas del Form por cédula, gana la de marca temporal más reciente.
- Cédula con match en `Sociodemograficos` → actualizar solo las celdas que cambian + fecha.
- Cédula sin match:
  - Si aparece en la pestaña de retirados/inactivos de JC (equivalente a `Inactivas` de MR — a
    definir cuál es la fuente canónica de retirados JC, candidato: pestaña `Retirados` de
    [[q10-consolidacion]]) → **RETIRADA**, no se agrega, solo se reporta.
  - Match fuerte (≥2 señales: correo igual, celular igual, nombre exacto/contenido, cédula a
    distancia Levenshtein ≤2, o cédula = su propio celular) con otra fila → **POSIBLE TYPO**, no
    se agrega, se reporta para revisión humana.
  - Sin candidata → fila nueva al final, con fondo naranja claro (igual color que MR:
    `{red:1.0, green:0.85, blue:0.6}`).

## Preguntas del Form propuestas (mapean a los enums ya existentes — no se inventan enums nuevos)
**Importante:** a diferencia de MR (`genero='Femenino'` constante, programa exclusivo de
mujeres), JC es **mixto** — este Form **no incluye pregunta de género** (ese dato ya lo trae la
BD de monitorias, columna `Género` de la pestaña `Seguimiento`, y lo escribe
`sync_sociodemograficos.py`; duplicarlo aquí arriesgaría inconsistencia entre dos fuentes para
el mismo campo).

| Pregunta del Form | Opciones | Mapea a (reutilizando `MAPA_*` de `sync_sociodemograficos_mr.py`) |
|---|---|---|
| Número de cédula | texto libre, numérico | llave de cruce |
| Nombres y Apellidos | texto libre | señal de match (typos) |
| Correo electrónico | texto libre | señal de match |
| Celular | texto libre, 10 dígitos | señal de match |
| ¿Cuál es tu nivel de estudios? | Primaria / Secundaria (bachillerato) / Técnico o Tecnólogo / Profesional / Especialización o Postgrado | `MAPA_NIVEL`: `"especializac"→postgrado`, `"tecn"→técnico`, `"bachiller"→secundaria`, `"profesional"→profesional`, `"primaria"→primaria` |
| ¿Cuál es tu estrato socioeconómico? | 1 / 2 / 3 / 4 / 5 / 6 | entero 1-6 directo, sin mapeo de texto (igual que `_num(valor, 1, 6)` en el sync MR) |
| ¿Cuál es tu estado civil? | Soltero(a) / Unión libre / Casado(a) / Divorciado(a) / Otro | `MAPA_CIVIL`: `"unión libre"/"union libre"→unión_libre`, `"soltera"/"soltero"/"sola"→soltero`, `"casada"/"casado"→casado`, `"divorci"/"separada"→divorciado`, `"viuda"/"otro"→otro` |
| ¿Cuál es tu tipo de vivienda? | Arrendada / Familiar (vive con familia, no paga arriendo) / Propia | `MAPA_VIVIENDA`: `"arrend"→arrendado`, `"familiar"→familiar`, `"propia"→propia` |

Las opciones del Form se redactan explícitamente en el texto que ya matchea las claves de
substring de los `MAPA_*` existentes (ej. la opción de nivel de estudios dice literalmente
"bachillerato" y "técnico/tecnólogo") para que el mapeo sea directo y no requiera tocar
`sync_sociodemograficos_mr.py` ni duplicar listas de sinónimos — el script nuevo **importa o
copia literalmente** `MAPA_NIVEL`, `MAPA_CIVIL`, `MAPA_VIVIENDA` de `sync_sociodemograficos_mr.py`
en vez de redefinir mapeos propios que puedan divergir con el tiempo.

## Script de sync propuesto — `sync_sociodemograficos_jc_extra.py`
Espejo de `scripts/panel-datos/sync_sociodemograficos_mr.py`, con estas diferencias:

- **Fuente:** pestaña `Sociodemograficos` del Sheet "BD Seguimiento de Monitorias" (mismo
  `SHEET_ID` que ya usan `sync_sociodemograficos.py` / `sync_emoflow_participacion.py`,
  `1ggzoJeZR3fS6AwRCLoGeYA5HEp_B7zvOwFGlGwny0l8`) en vez de la BD-Mujeres ROFÉ.
- **Filtro de destino:** solo participantes con matrícula en cursos `programa=jc` (mismo patrón
  del filtro `programa=mr` del script MR, invertido) — si una cédula está matriculada en ambos
  programas, este script no debe pisar los datos que ya tenga MR para esos 4 campos (ni al
  revés); cada sync solo escribe sobre su propio universo de programa.
- **Campos que SÍ escribe:** únicamente `tipo_vivienda`, `estrato`, `estado_civil`,
  `nivel_estudio` (los 4 que hoy no tienen fuente). **No** escribe `genero`, `edad`, `ciudad`,
  `nombre_emprendimiento`/`tiene_emprendimiento` — esos ya los cubre
  `sync_sociodemograficos.py` para JC y este script nuevo no debe competir con esa fuente.
- **Mapeos:** reutiliza literalmente `MAPA_NIVEL`, `MAPA_CIVIL`, `MAPA_VIVIENDA` y la función
  `_num(valor, 1, 6)` para estrato, tal como están definidos en `sync_sociodemograficos_mr.py`
  — cero enums nuevos, cero mapeos nuevos.
- **No crea participantes:** igual que el sync MR, las cédulas del Form sin matrícula JC en
  Supabase se reportan (`sin_match_supabase`), no se insertan — Q10 sigue siendo la fuente de
  verdad de quién existe.
- **Salida:** mismo formato parseable para n8n:
  `RESUMEN: actualizados=N sin_match_supabase=X sin_datos=Y estado=exito`.
- **Idempotente:** re-correrlo sin respuestas nuevas no debería generar cambios (mismo criterio
  de comparación normalizada que ya usan `actualizar_bd_mr.py` y los syncs existentes).

## Decisiones de diseño clave (propuestas)
- **Reutilizar los 4 enums existentes tal cual** (`nivel_estudio_type`, `estado_civil_type`,
  `vivienda_type`, `estrato` entero) — no se crean variantes JC de estos tipos; son atributos
  de la persona, no del programa.
- **No duplicar campos que JC ya tiene fuente propia** (género/edad/ciudad/emprendimiento vía BD
  de monitorias) — este diseño cubre estrictamente el hueco de los 4 campos "sin fuente", nada más.
- **Espejo exacto del patrón MR** (Form → script de actualización de Sheet con cruce por cédula
  y clasificación nuevos/typos/retiradas → script de sync Sheet→Supabase con mapeos de texto a
  enum) — mismo Service Account, mismas convenciones de idempotencia y de salida parseable para
  n8n, para minimizar código y decisiones nuevas.
- **Ubicación del Sheet destino:** pestaña nueva en el hub ya existente de JC en vez de un Sheet
  aparte, siguiendo la convención "un hub, muchas pestañas" que ya usa la BD de monitorias.

## Cuándo desplegar
**No ahora — al preparar la estructura/matrícula del próximo año (onboarding),** igual que ya
quedó anotado en `docs/procesos/panel-datos-etl.md` (sección "Vivienda / estrato / estado civil /
nivel de estudio para JC"). Motivo: intentar recolectar esto retroactivo a mitad de año da mala
cobertura y obliga a perseguir estudiantes ya matriculados; incluirlo desde el Form de
inscripción/matrícula del inicio de cohorte es la ventana natural (mismo argumento que ya se
documentó ahí, sin repetirlo en detalle en esta nota).

## Gotchas / Limitaciones conocidas (anticipadas, a validar cuando se implemente)
- **Cobertura probablemente parcial al inicio**, como pasó con MR (99.3% de la cohorte 2026 vs
  solo 26.9% de las MR históricas 2025 que ya no figuran en la BD 2026) — la participación en el
  Form no es 100% garantizada aunque se incluya en la matrícula.
- **Población mixta:** cualquier pregunta o mapeo que se copie de MR debe revisarse para no
  arrastrar supuestos de "programa de mujeres" (el más obvio, `genero` constante, ya queda
  excluido de este diseño).
- **Definir la fuente de "retirados JC"** equivalente a la pestaña `Inactivas` de MR antes de
  implementar el paso de clasificación — candidato natural es la pestaña `Retirados` de
  [[q10-consolidacion]], pero falta confirmar que tenga cédula en un formato cruzable.
- **No confundir con `sync_sociodemograficos.py`:** dos scripts de sync corriendo sobre JC
  (el existente para género/edad/ciudad/emprendimiento, este nuevo para los 4 campos) deben
  quedar claramente documentados como complementarios, no duplicados, para evitar que alguien
  en el futuro asuma que uno reemplaza al otro.

## Pendiente / Próximos pasos
- [ ] Confirmar con Samuel/equipo si la pestaña destino va en el hub "BD Seguimiento de
      Monitorias" o en un Sheet dedicado nuevo.
- [ ] Definir la fuente canónica de "retirados JC" para la clasificación de sin-match.
- [ ] Redactar y crear el Google Form real ("Actualización de datos sociodemográficos JC"),
      con las opciones exactas de este documento.
- [ ] Crear la pestaña `Sociodemograficos` con las columnas propuestas.
- [ ] Implementar `actualizar_bd_jc_socio.py` (espejo de `actualizar_bd_mr.py`).
- [ ] Implementar `sync_sociodemograficos_jc_extra.py` (espejo de `sync_sociodemograficos_mr.py`).
- [ ] Encadenar a un schedule n8n (candidato: mismo horario/patrón que
      `sociodemograficos-semanal`).
- [ ] Coordinar con el equipo de matrícula para incluir el Form en el onboarding del próximo año.
