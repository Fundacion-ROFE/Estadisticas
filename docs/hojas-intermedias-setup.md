# Hojas Intermedias — Setup para el Equipo

**Objetivo:** mantener hojas de lectura/escritura en Google Sheets para que el equipo pueda consultar datos sin abandonar Excel.

**Flujo bidireccional:**
```
Emoflow API / Q10
    ↓
Supabase (backend de verdad)
    ↓
Hojas h1, h2, h3 (lectura + edición manual del equipo)
```

---

## Setup (10 minutos)

### Opción A: Usar el Sheet existente (1ggzoJeZR3fS6AwRCLoGeYA5HEp_B7zvOwFGlGwny0l8)

1. **Abre:** https://docs.google.com/spreadsheets/d/1ggzoJeZR3fS6AwRCLoGeYA5HEp_B7zvOwFGlGwny0l8/edit

2. **Crea 3 hojas nuevas:**
   - Haz clic en el `+` al final de las pestañas
   - Llama cada una: `h1`, `h2`, `h3`
   - Déjalas vacías por ahora

3. **Ejecuta el sync:**
   ```bash
   python scripts/panel-datos/sync_supabase_to_sheets.py
   ```

   Esto llena:
   - **h1:** Lista de participantes (Cédula | Nombre | Email | Programa | Ciudad)
   - **h2:** Emoflow (Email | Nombre | Ciudad | Ingresos al Sistema | Último Ingreso)
   - **h3:** Resumen ejecutivo (KPIs de la cohorte)

---

## Qué va en cada hoja

### `h1` — Participantes (referencia)
| Cédula | Nombre | Email | Programa | Ciudad |
|--------|--------|-------|----------|--------|
| 1054... | Juan | juan@... | jc | Bogotá D.C. |
| ... | ... | ... | ... | ... |

**Lectura:** referencia rápida para el equipo.
**Edición:** manual (no se sincroniza de vuelta a Supabase).

---

### `h2` — Emoflow (ingresos al sistema)
| Email | Nombre | Ciudad | Ingresos al Sistema | Último Ingreso |
|-------|--------|--------|----------------------|-----------------|
| juan@... | Juan | Bogotá | 42 | 2026-07-20 |
| ... | ... | ... | ... | ... |

**Lectura:** vee qué estudiantes entran al sistema y cuántas veces.
**Edición:** manual (el equipo puede ajustar/validar si ve errores).
**Sincronización:** `sync_emoflow_api.py` (n8n diario 9:45) sobrescribe con datos frescos de Emoflow API.

---

### `h3` — Resumen Ejecutivo
Tabla de KPIs de la cohorte actual:
- Ingresados, Activos, Aprobados, En Progreso, Retirados
- Emoflow: participantes, promedio ingresos, mediana, máximo, % activos 7d/30d
- Fecha de actualización

**Lectura:** dashboard rápido (no necesita filtros).
**Edición:** no editar (generada automáticamente).

---

## Automatización

El script `sync_supabase_to_sheets.py` se puede ejecutar:

1. **Manualmente:**
   ```bash
   python scripts/panel-datos/sync_supabase_to_sheets.py
   ```

2. **En n8n (scheduled):** agregar un nodo que ejecute el script tras `sync_emoflow_api.py`
   (Sugerencia: mismo horario diario 9:45, después de que Emoflow se actualice).

---

## Notas

- **h1, h2, h3 NO son fuentes de verdad.** Supabase es la base de datos. Sheets es una interfaz amigable.
- **Cambios en Sheets no se replican automáticamente a Supabase** (solo Supabase → Sheets). Si el equipo necesita editar datos, hace cambios en Sheets y alguien los ingresa manualmente en Supabase o Q10.
- **Privacidad:** h1 y h2 contienen email/nombre (PII). No compartir públicamente.
- **Actualización:** las hojas se refrescan cada vez que corre el script (~ 2 minutos de ejecución).

---

## Solución de problemas

**"Faltan hojas h1, h2, h3"**
→ Créalas manualmente en el Sheet (ver Opción A arriba).

**"Permiso insuficiente para escribir"**
→ Verifica que la Service Account (`credenciales_service_account.json`) tenga acceso al Sheet.
  Comparte el Sheet con `q10-automatizacion@n8n-automatizacion-q10.iam.gserviceaccount.com` (role: Editor).

**"Datos no se actualizan"**
→ Ejecuta el script manualmente (`python sync_supabase_to_sheets.py`).
  Si falla, revisa los logs de Supabase (`SUPABASE_URL`, `SUPABASE_ANON_KEY` en `.env.local`).
