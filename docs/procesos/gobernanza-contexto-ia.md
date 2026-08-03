# Gobernanza de contexto IA por usuario

**Estado:** En progreso (Lina/Rocío/Cristian activados con carpeta+skills; Astrid/Sandra
bloqueadas pendiente de su propia entrevista; repo privado real sigue sin crear)
**Última actualización:** 2026-08-03
**Procesos relacionados:** [[pseudonimizador]] · [[convenciones]] · [[prioridades-automatizacion-ia]]

## Qué hace

Da control centralizado sobre el contexto (CLAUDE.md, skills) y el uso real (logs de
sesión) de cada persona de la organización que usa Claude/IA en su trabajo. Objetivo:
poder revisar si hubo filtración de datos o un error de uso, sin depender de que cada
persona reporte manualmente.

## Disparador (Trigger)

**Corrección de diseño (2026-08-03):** el plan original era un Schedule n8n corriendo
`commit_y_push.py` sobre todo `usuarios-ia/` — pero eso solo funciona si todas las carpetas
viven en la misma máquina que corre n8n (hoy, la de Samuel). Lina, Rocío y Cristian van a
correr su propia instancia de Claude Code en su propia máquina, así que n8n no puede ver sus
cambios locales. Mecanismo real: un **hook `Stop` de Claude Code** en el `settings.json` local
de cada persona, que al terminar la sesión corre:

```
python scripts/gobernanza-ia/commit_y_push.py --usuario <nombre>
```

acotado a su propia carpeta (`commit_y_push.py` ya soporta `--usuario`, agregado 2026-08-03).
El Schedule n8n sigue siendo válido solo para el caso "todo corre en la máquina de Samuel"
(sin `--usuario`, sube todo el árbol de una vez) — ninguno de los dos está conectado todavía
a un trigger real (ver Pendiente).

## Flujo resumido

1. Cada persona tiene una carpeta en `usuarios-ia/<nombre>/` (repo central, no un repo por
   persona) con su `CLAUDE.md`, sus `skills/` y sus `logs/` de sesión.
2. Al final del día (o cuando cambie el contexto), `scan_pii.py` escanea todo lo que se
   vaya a commitear en `logs/`.
3. Si encuentra un patrón de PII sin pseudonimizar (cédula, celular, email, credencial en
   texto plano), bloquea el commit de esa persona y avisa — no sube nada de ese ciclo.
4. Si está limpio, `commit_y_push.py` hace commit + push al repo central.
5. Revisión humana periódica del historial de git = la auditoría (diffs por persona, en un
   solo repo).

## Fuentes de datos / APIs usadas

- Ninguna externa. Todo el flujo es local: filesystem + git.

## Destino de los datos

**El diseño siempre fue un repo git privado central** (una carpeta por persona bajo
`usuarios-ia/`), pero ese repo privado **aún no existe**. El scaffolding se construyó como
prototipo dentro de `Fundacion-ROFE/Estadisticas` — que es **público** (verificado vía API de
GitHub, 2026-08-03: `"private": false`). Mientras no se migre:

- La `anon key` de Supabase embebida en cada `CLAUDE.md` **no es un riesgo nuevo** — ya es
  pública por diseño (RLS la protege, solo expone agregados, y ya vive en el frontend Netlify).
- Lo que **sí** queda expuesto públicamente sin necesidad son los roles/restricciones/estado
  interno de cada persona (ej. la nota de incidente de Cristian) y, si se activaran, sus
  `logs/` de sesión — información operativa interna, no destinada a ser pública.

**Migrar a un repo privado real es un prerrequisito explícito antes de:** activar cualquier
push automático de `logs/` de sesión, o subir cualquier dato operativo más sensible que el ya
público hoy. Ver Pendiente.

## Decisiones de diseño clave

- **Repo central con carpetas por persona, no un repo por persona.** Menos overhead de
  permisos/credenciales que administrar (N repos = N configuraciones), un solo pipeline de
  scan aplicado a todos, y la auditoría completa queda en un solo lugar en vez de repartida.
- **Config estática y logs de uso son cosas distintas, aunque compartan carpeta.**
  `CLAUDE.md`/`skills/` cambian poco y casi nunca tienen PII. `logs/` es donde vive el
  riesgo real (ahí es donde podría aparecer una filtración o un error de uso) — por eso
  solo `logs/` pasa por el scan antes de cada push, no todo el árbol por igual.
- **El scan reutiliza la lógica de detección del pseudonimizador** (`docs/pseudonimizador/index.html`):
  mismos patrones de columna/contenido (cédula, celular, email, credenciales en texto
  plano), adaptados de "columna de Excel" a "texto libre" porque acá el input son
  transcripciones, no hojas de cálculo.
- **Nunca imprimir el valor real encontrado, ni en el log de alerta.** Aplica la misma
  lección del incidente de secreto commiteado (2026-07-14, ver `convenciones.md`): el
  reporte de una fuga puede convertirse él mismo en la fuga si repite el dato. `scan_pii.py`
  solo enmascara (`s****z`) y da la ubicación.
- **Bloquear, no limpiar automáticamente.** El script no intenta pseudonimizar por sí solo
  ni redactar y subir de todos modos — corta el push y deja que un humano decida (mismo
  principio que "vacío nunca sobreescribe" y otros patrones de este proyecto: ante la duda,
  no actuar solo).

## Gotchas / Limitaciones conocidas

- `scan_pii.py` usa regex simples (7-10 dígitos para cédula, `3\d{9}` para celular) —
  va a tener falsos positivos con IDs de curso, números de factura, etc. Ajustar los
  patrones a medida que aparezcan casos reales, no intentar cubrir todo de entrada.
- El push automático necesita la misma configuración de git no-interactivo que ya se
  documentó para n8n (`credential.interactive never`, `GCM_INTERACTIVE=never`,
  `GIT_TERMINAL_PROMPT=0`) — si no, un push colgado en modo credencial se cuelga para
  siempre sin avisar (mismo gotcha ya resuelto en `convenciones.md`).
- El repo privado dedicado aún no existe — hay que decidir bajo qué organización/cuenta vive,
  quién tiene acceso, y crear el remoto. Hoy `commit_y_push.py` pushearía a `Fundacion-ROFE/Estadisticas`
  (el remoto configurado en este checkout), que es público — ver "Destino de los datos".

## Estado por persona (2026-08-03)

| Persona | Carpeta | Estado | Skills habilitados | Notas |
|---|---|---|---|---|
| Lina | `usuarios-ia/lina/` | **Activa** | `evaluar`, `consejo-ligero`, `consejo-medio`, `consejo-profundo` | Coordinación/estratégico |
| Rocío | `usuarios-ia/rocio/` | **Activa** | Ninguno formal (redacción libre ya cubierta por conversación) | Clasificador WhatsApp es proyecto aparte ([[whatsapp-identificacion-manychat]]), no un skill suyo |
| Cristian | `usuarios-ia/cristian/` | **Activa** (contenido actualizado; carpeta de trabajo real sigue standalone fuera del repo) | Ninguno (su necesidad la resuelve [[zoom-asistencia]]/[[panel-clase-vivo]]) | Pendiente migrar su carpeta física a este modelo |
| Astrid | — | **Bloqueada** | — | Falta su entrevista P0; acordado con Lina que la DB debe estar lista antes de darle instancia |
| Sandra | — | **Bloqueada** | — | Falta levantar sus necesidades específicas |

## Pendiente / Próximos pasos

- **Crear el repo privado real en GitHub** y migrar `usuarios-ia/` ahí (fuera del alcance de
  sesiones de código — requiere credenciales/decisión de cuenta de Samuel). Configurar
  `http.sslBackend schannel` + `credential.interactive never` en él, igual que cualquier repo
  nuevo de esta red. **Bloquea:** activar `logs/` real de cualquier persona.
- Configurar el hook `Stop` de Claude Code en las máquinas de Lina, Rocío y Cristian (comando
  documentado arriba en "Disparador") — requiere estar en cada máquina.
- Decidir quién revisa las alertas de bloqueo y con qué frecuencia se mira el historial del
  repo (la "auditoría" en sí — hoy el diseño deja los datos, falta el proceso humano de
  revisión).
- Evaluar si además de escanear, conviene correr los logs por el pseudonimizador
  directamente antes de guardarlos en `logs/` (en vez de solo bloquear y esperar que un
  humano pseudonimice a mano).
- Diseñar el skill de "borrador de correo" para Rocío si el volumen lo justifica (separado de
  `enviar-correo`, sin capacidad de envío real).
- Activar a Astrid/Sandra cuando se levanten sus necesidades específicas (su propia
  entrevista P0).

**Confirmado en entrevistas P0 (2026-07-28):** con Lina se validó que la cadencia de
revisión humana del repo sea **semanal** (no ad hoc) y que se sume una **alerta antes de
ejecutar cualquier acción dudosa** dentro de una instancia individual, además de la
alerta ya prevista por bloqueo de PII en el push. Cada persona (Lina, Astrid, Sandra,
Rocío, Cristian, y quien más se sume) tendrá su propia carpeta bajo `usuarios-ia/<nombre>/`
con su `CLAUDE.md` propio, sobre la misma base de repo central ya diseñada — este
scaffolding pasa a ser prerrequisito directo de las instancias individuales de Claude
Workspace que pidió el equipo, no solo un proyecto de cumplimiento en paralelo.

**Corrección de roles (2026-07-28):** en la primera ronda de entrevistas se atribuyó a
"Astrid" la función de Coordinación (crecimiento y búsquedas estratégicas asumidas por
falta de personal). Esa función es de **Lina**; Astrid es Coordinadora Junior, con
necesidades propias aún sin levantar. Se sumó además a **Sandra**, Jefe de Operaciones de
Mujeres ROFÉ — ver [[prioridades-automatizacion-ia]] y el docx
`Entrevistas-diagnostico-P0-2026-07-28-v2.docx` para el detalle completo, incluida la
tensión de carga operativa que las tareas de Sandra generan sobre el tiempo técnico de
Lina/Cristian.
