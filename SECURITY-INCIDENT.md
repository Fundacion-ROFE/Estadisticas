# Incidente de seguridad — clave de Supabase en historia local (2026-07-14)

**Severidad:** BAJA — la clave **nunca llegó a GitHub**.
**Estado:** Resuelto (historia purgada). Rotación de la clave: recomendada.

---

## Qué pasó

Una `SUPABASE_SERVICE_ROLE_KEY` quedó hardcodeada en
`scripts/panel-datos/sync_asistencia_supabase.py` (commit `f6e0e4b`, 2026-07-13) y sobrevivió en
8 blobs de la historia local.

**El push protection de GitHub bloqueó el push antes de que saliera del equipo.** Se verificó con
`git branch -r --contains f6e0e4b`: ningún remoto contenía esos commits. O sea: fue un **casi
accidente**, no una fuga pública. Esa distinción cambia la severidad — no hubo ventana de
exposición para terceros.

## Qué se hizo

1. El código pasó a leer la clave del entorno: `os.getenv("SUPABASE_SERVICE_ROLE_KEY")`.
2. Se agregó `.env.example` con las variables necesarias (`.gitignore` ya excluía `.env`).
3. **Se purgó el literal de toda la historia** con `git filter-repo --replace-text` y se
   reescribieron los 14 commits locales. Respaldo previo en el tag `backup/pre-purga-secreto`.

## Pendiente (recomendado, no urgente)

Rotar la clave en Supabase → Settings → API → Service Role Key → Regenerate, y actualizar el
`.env` local. No es urgente porque la clave nunca salió del equipo, pero rotar es barato y cierra
el tema del todo.

---

## Gotchas aprendidos

- **Un documento de incidente NO debe contener el secreto.** La primera versión de este archivo
  citaba la clave literal para "documentarla" — y por eso el push seguía bloqueado: el propio
  archivo era la fuga. Documentá *dónde* estuvo y *qué* se hizo, nunca el valor.
- **Purgar la historia no basta si el secreto ya se publicó.** Aquí funcionó porque nunca llegó al
  remoto. Si un secreto sí llegó a un repo público, la reescritura no lo des-publica: hay que
  asumir compromiso y **rotar** de inmediato.

## Referencia

- [[convenciones]] — sección "Credenciales"
- `.env.example` — template de variables de entorno
