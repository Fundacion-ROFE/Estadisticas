# Prompt para Claude Code — arreglar las alertas de Telegram antes de seguir con visualización

> Creado 2026-07-30 (sesión Cowork con Lina). Son 4 arreglos chicos y aislados, todos en n8n
> y una migración de umbral. Ninguno toca el pipeline de datos ni la capa de visualización, así
> que puede correr antes o en paralelo con `plan-visualizacion-2026-07-30.md`.
> Modelo recomendado: **Sonnet**.

---

```
Vas a arreglar 4 problemas de las alertas de Telegram de panel-datos-rofe (Fundación ROFÉ /
Jóvenes creaTIvos). El diagnóstico ya está hecho y verificado en vivo — ejecutá y verificá, no
rediseñes.

## Lectura obligatoria antes de tocar nada
1. CLAUDE.md — reglas duras.
2. docs/convenciones.md, sección de editar workflows n8n por API (el gotcha de concatenar
   strings en expresiones y el de JSON inline por PowerShell).
3. docs/migrations/019_v_frescura.sql — leelo completo, incluido el bloque de comentarios. Ahí
   está el precedente exacto del arreglo #4.
4. Las últimas 3 entradas de claude_sessions.md.

## Por qué importa (contexto, no lo pierdas de vista)
Ayer se construyeron dos vistas de vigilancia (v_choques_cursos, v_choques_cohorte) que
detectaron un curso renombrado sin aviso y 167 falsas retiradas de MR. Esa vigilancia solo
sirve si alguien lee el canal de Telegram. Hoy el canal recibe **8 alertas falsas por día** más
mensajes con caracteres corruptos, y eso entrena a la gente a ignorarlo. Los 4 arreglos son
para que el canal vuelva a ser creíble.

## Reglas duras
- JSON de n8n siempre desde archivo UTF-8, nunca inline por PowerShell (mutila tildes y ñ).
- Nunca construyas el texto del mensaje concatenando strings en una expresión de n8n. El texto
  va dentro del script Python. Ya está hecho así en check_choques_cursos.py — mantené ese patrón.
- Re-exportá el JSON de cada workflow que toques a `n8n-workflows/` en el MISMO commit.
- Un commit por arreglo, mensaje en español, sin PII.
- ⚠ El árbol de trabajo tiene cambios sin commitear de otras sesiones: `git add` SOLO de tus
  archivos, nunca `git add -A`.
- Si un número no cuadra con lo que dice este prompt: PARÁ y reportalo con la query exacta.

---

## ARREGLO 1 — alerta-choques-cursos manda informativas como si fueran alertas

**Síntoma:** el canal recibe "Choques de curso detectados: 1 curso MR sin verse en Q10 hace 8
días". Eso NO es una alerta: es una señal informativa de un curso que cerró clases con
normalidad.

**Y son 2, no 1.** Verificado en vivo hoy: `DE LA IDEA A LA ACCIÓN…` (última vez visto
2026-07-21) y `HABILIDADES DEL SER…` (2026-07-29). Los dos cerraron para abrir Finanzas
Inteligentes — confirmado por Lina. Si el filtro no cambia, ese mensaje va a llegar todos los
días para siempre.

**Arreglo:** el query que alimenta el workflow debe filtrar `WHERE severidad = 'alta'`.
Los valores reales del campo son `'alta'`, `'media'`, `'informativa'` — **no existe `'baja'`**.
Usá el campo `severidad` tal como viene de la vista, sin traducirlo ni reinterpretarlo.
Cuando no haya filas de severidad alta, **no mandar mensaje**. Silencio = todo bien.

Estado esperado hoy tras el arreglo: `SELECT count(*) FROM v_choques_cursos WHERE
severidad='alta'` = 0, y `SELECT count(*) FROM v_choques_cohorte WHERE severidad='alta'` = 0.
O sea: el canal no debería recibir nada de choques hoy.

Revisá si v_choques_cohorte (migración 028) ya está conectada a algún workflow. Si no lo está,
conectala con el mismo patrón y el mismo filtro de severidad alta — es la que vigila las falsas
deserciones por cierre de curso.

---

## ARREGLO 2 — mojibake "â€¢" en alerta-frescura-vencida

**Causa (ya diagnosticada):** el nodo ejecuta `python check_frescura.py > log.txt 2>&1` y
después relee ese log con `powershell ... Get-Content -Tail 15`. Python escribe UTF-8, pero
Get-Content en PowerShell 5.1 lee con el codepage ANSI del sistema, así que el bullet "•"
(3 bytes UTF-8) se interpreta como 3 caracteres → "â€¢".

**Arreglo:** agregar `-Encoding UTF8` a ese `Get-Content`.

Verificá que no haya otros `Get-Content` sin `-Encoding UTF8` en los demás workflows —
si el patrón se copió, el bug está copiado también.

---

## ARREGLO 3 — mojibake ya horneado en panel-verificacion-diaria

El texto del nodo "Notificar error" tiene literalmente `âš ` en el JSON: es el
mojibake de "⚠" pegado ya corrupto en la config del nodo. Cada vez que ese workflow falle va a
mandar "âš " en vez de "⚠".

**Arreglo:** reemplazar por el carácter correcto, editando el JSON como archivo UTF-8 (no
inline). Revisá el resto del JSON de ese workflow por si hay más caracteres corruptos pegados
del mismo copy/paste.

---

## ARREGLO 4 — el umbral de frescura genera 8 falsas alarmas por día

Este es el más importante de los 4.

**Diagnóstico verificado en vivo hoy:**
`q10-sync-supabase` corre con cron `30 17,19,21,23,1,3,5,7 * * *` — o sea 17:30, 19:30, 21:30,
23:30, 01:30, 03:30, 05:30, 07:30. Es una ventana nocturna. Entre la última corrida del día
(07:30) y la primera de la tarde (17:30) hay un hueco **de diseño de 10 horas**.

Pero estos tres procesos tienen umbral de **6 horas** en `v_frescura`:
  · cohorte_ingresos
  · aprobacion_cursos
  · retiros (sync_retiros)

Entonces todos los días, de 13:30 a 17:30, los tres aparecen VENCIDO. Y como
`alerta-frescura-vencida` corre cada 30 minutos, son **8 mensajes falsos diarios**. Medido hoy
a media tarde: los tres en 6,9 h, vencido=true, con el sync funcionando perfectamente (corrió
a las 07:31).

**Precedente exacto:** el comentario de `019_v_frescura.sql` dice que la migración 021 ya
corrigió `emoflow_ingresos_diario` de 6h a 30h por esta misma razón — *"el umbral original
disparaba falsa alarma toda la tarde"*. Se arregló para un proceso y quedó igual en los otros
tres.

**Arreglo: umbral 6h → 12h** para esos tres procesos, vía migración numerada nueva (siguiente
número libre; la última aplicada es la 028). No edites las migraciones viejas.

**Por qué 12 y no otro número:**
  · a las 17:29 la antigüedad máxima posible es 9,98 h → 12 h no dispara. Cero falsas alarmas.
  · si la corrida de las 17:30 falla, a las 19:30 la antigüedad llega a 12 h → dispara.
    Detecta una falla real en ~2 h, que es una corrida perdida.
No subas a 30 h como emoflow_ingresos_diario: esos tres corren 8 veces por ventana, y 30 h
dejaría pasar una noche entera de fallas sin avisar.

**Verificación obligatoria tras aplicar:**
```sql
SELECT proceso, round(horas_desde_ultimo::numeric,1) AS horas, umbral_horas, vencido
FROM v_frescura ORDER BY vencido DESC, horas DESC;
```
Esperado a media tarde: **0 procesos vencidos**. Si alguno sigue vencido, reportalo antes de
seguir — puede ser una falla real que el ruido estaba tapando.

Y comprobá que la alerta todavía sirve: confirmá con una query que la condición
`horas_desde_ultimo > umbral_horas` seguiría siendo verdadera para un proceso genuinamente
atrasado (por ejemplo calculando qué pasaría con un ultimo_dato de hace 13 h). No hace falta
romper nada para probarlo.

---

## Al terminar
1. Mandá un mensaje de prueba por cada workflow tocado y confirmá que "•" y "⚠" llegan bien
   a Telegram (es el punto de todo el arreglo 2 y 3 — si no se verifica en el canal real, no
   está verificado).
2. JSONs re-exportados a `n8n-workflows/`.
3. Migración nueva con sufijo `_APLICADA` y su bloque de comentarios explicando el porqué
   (seguí el estilo de 019/026/027/028: contexto, diagnóstico medido, umbral justificado).
4. Actualizá `docs/procesos/supabase-estructura.md` si cambia algo del estado de v_frescura.
5. Agregá a `docs/convenciones.md` la regla que se desprende del arreglo 4: **un umbral de
   frescura tiene que ser mayor al hueco de diseño del cron que alimenta el proceso** — si no,
   la alerta grita todos los días a la misma hora y la gente aprende a ignorar el canal. Con la
   fórmula: umbral > hueco máximo entre corridas consecutivas + una corrida de tolerancia.
6. Entrada al final de claude_sessions.md.

Arrancá por el arreglo 4 (es el que más ruido quita), después 1, y al final 2 y 3 juntos que
son el mismo tipo de fix. Reportá cada uno antes de pasar al siguiente.
```
