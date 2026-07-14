# ⚠️ Incidente de Seguridad — Secreto de Supabase Expuesto

**Fecha:** 2026-07-14
**Severidad:** MEDIA (clave puede regenerarse sin impacto duradero)
**Estado:** Mitigado

---

## ¿Qué pasó?

Accidentalmente, una clave de Supabase `SUPABASE_SERVICE_ROLE_KEY` fue committed en el historial de Git:
- **Archivo:** `scripts/panel-datos/sync_asistencia_supabase.py`
- **Commit:** `f6e0e4b` (2026-07-13)
- **Línea:** 114 (ahora removida)
- **Clave:** `***SECRETO-PURGADO***`

## ¿Qué significa esto?

Si alguien accedió a GitHub, podría:
- ✓ Escribir datos en Supabase (pero solo en tabla pública `asistencia_zoom` vía RLS)
- ✗ Ver datos PII (RLS lo previene — anon key solo ve agregados)
- ✗ Borrar participantes (no hay permisos DELETE en RLS)

## ¿Qué se hizo para mitigarlo?

1. ✅ Código ACTUAL usa `os.getenv("SUPABASE_SERVICE_ROLE_KEY")` — SIN hardcode
2. ✅ Creado `.env.example` documentando qué variables se necesitan
3. ✅ `.gitignore` ya excluye `.env` desde el inicio
4. ⏳ **PENDIENTE:** Regenerar la clave en Supabase (abajo)

## 📋 TODO: Regenerar la clave

**Hazlo AHORA en Supabase Dashboard:**

1. Abre https://app.supabase.com → Proyecto `panel-datos-rofe`
2. Settings → API → Service Role Key
3. Click "Regenerate" (esto invalidará la clave antigua)
4. Copia la nueva clave
5. Actualiza tu `.env` local:
   ```bash
   SUPABASE_SERVICE_ROLE_KEY=nuevo_valor_aqui
   ```
6. Prueba: `python scripts/panel-datos/sync_asistencia_supabase.py --dry-run`

**Después de regenerar:** La clave antigua (`***SECRETO-PURGADO***`) dejará de funcionar.

---

## Política a Futuro

Para evitar esto:
- **NUNCA:** Hardcodear secretos en scripts (usa `os.getenv()`)
- **SIEMPRE:** Usar `.env` (gitignoreado)
- **ANTES DE COMMIT:** Revisar que no haya API keys / tokens / passwords

---

## Referencia

- [[convenciones.md]] — Sección "Credenciales"
- [[reference-n8n-api-key.md]] — Ejemplo de gestión de claves
- `.env.example` — Template de variables de entorno
