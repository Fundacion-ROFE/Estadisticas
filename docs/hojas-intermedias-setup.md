# Hojas Intermedias — Setup para el Equipo

**Objetivo:** mantener hojas de lectura/escritura en Google Sheets (H1Test, H2Test, H3Test) para que el equipo pueda consultar datos sin abandonar Excel.

**Flujo bidireccional actualizado (2026-07-20):**
```
Emoflow API / Q10
    ↓
Supabase (backend de verdad, única fuente)
    ↓
├─ Google Sheets (H1Test, H2Test, H3Test) — equipo
│  Lectura + edición manual por operadores
│
└─ GitHub (docs/datos/*.json) — panel Netlify
   Visualización pública en venerable-truffle-331f3c.netlify.app
```

---

## Setup Automático

Ya TODO está automático. Los datos fluyen así:

1. **`export_supabase_json.py`** (ejecutar diario o en n8n):
   ```bash
   python scripts/panel-datos/export_supabase_json.py
   ```
   - Exporta 16 tablas/vistas públicas de Supabase a JSON
   - Genera `docs/datos/*.json` (aprobacion, emoflow, cursos, historial, etc)
   - Listo para GitHub Pages / Netlify

2. **`sync_supabase_to_sheets.py`** (ejecutar diario):
   ```bash
   python scripts/panel-datos/sync_supabase_to_sheets.py
   ```
   - Rellena **H1Test, H2Test, H3Test** automáticamente
   - Requiere que las hojas YA existan en el Sheet

---

## Contenido de cada Hoja

---

## Qué va en cada hoja

### `H1Test` — Participantes (referencia)
| Cédula | Nombre | Email | Programa | Ciudad |
|--------|--------|-------|----------|--------|
| 1054... | Juan | juan@... | jc | Bogotá D.C. |
| ... | ... | ... | ... | ... |

**Lectura:** referencia rápida para el equipo.
**Edición:** manual (no se sincroniza de vuelta a Supabase).

---

### `H2Test` — Emoflow (ingresos al sistema)
| Email | Nombre | Ciudad | Ingresos al Sistema | Último Ingreso |
|-------|--------|--------|----------------------|-----------------|
| juan@... | Juan | Bogotá | 42 | 2026-07-20 |
| ... | ... | ... | ... | ... |

**Lectura:** vee qué estudiantes entran al sistema y cuántas veces.
**Edición:** manual (el equipo puede ajustar/validar si ve errores).
**Sincronización:** `sync_emoflow_api.py` (n8n diario 9:45) + `sync_supabase_to_sheets.py` → sobrescribe con datos frescos.

---

### `H3Test` — Resumen Ejecutivo
Tabla de KPIs de la cohorte actual:
- Ingresados, Activos, Aprobados, En Progreso, Retirados
- Emoflow: participantes, promedio ingresos, mediana, máximo, % activos 7d/30d
- Fecha de actualización

**Lectura:** dashboard rápido (no necesita filtros).
**Edición:** no editar (generada automáticamente).

---

## Automatización (Recomendado)

Agregá estos 2 nodos a n8n (en el workflow `q10-sync-supabase`, después de `sync_emoflow_api.py`):

1. **Ejecutar `export_supabase_json.py`:**
   - Exporta Supabase → docs/datos/*.json
   - GitHub Push automático (para panel Netlify)
   - Tiempo: ~3-5 minutos

2. **Ejecutar `sync_supabase_to_sheets.py`:**
   - Actualiza H1Test, H2Test, H3Test en Google Sheets
   - Tiempo: ~1-2 minutos

**Horario:** Después de 9:45 (cuando `sync_emoflow_api.py` termine).

---

## Flujo de Datos Completo (2026-07-20)

```
1. Emoflow API (27K registros)
   ↓ sync_emoflow_api.py
2. Supabase (única fuente de verdad)
   ↓↓
   ├─→ export_supabase_json.py → docs/datos/*.json → git push → GitHub
   │   ↓
   │   Panel Netlify (venerable-truffle-331f3c.netlify.app)
   │
   └─→ sync_supabase_to_sheets.py → Google Sheets (H1Test/H2Test/H3Test)
       ↓
       Equipo (lectura + edición manual)
```

---

## Notas Importantes

- **H1Test, H2Test, H3Test NO son fuentes de verdad.** Supabase es la BD única. Sheets es interfaz amigable.
- **Sincronización unidireccional:** Supabase → Sheets/GitHub. NO hay sync de vuelta (Sheets → Supabase).
  Si el equipo edita datos en Sheets, coordina con alguien para ingresarlos en Supabase/Q10 manualmente.
- **Privacidad:** H1Test y H2Test contienen email/nombre (PII). No compartir públicamente.
- **Actualización:** las hojas + JSON se refrescan cada vez que corren los scripts (~1-2 min para Sheets, ~3-5 min para JSON).

---

## Solución de Problemas

**"Faltan hojas H1Test, H2Test, H3Test"**
→ Créalas manualmente en el Sheet. El script las verá automáticamente.

**"Permiso insuficiente para escribir en Sheet"**
→ Verifica que la Service Account tenga acceso.
  Comparte el Sheet con `q10-automatizacion@n8n-automatizacion-q10.iam.gserviceaccount.com` (role: Editor).

**"No ve JSON en GitHub / Panel Netlify"**
→ Ejecuta `python export_supabase_json.py` y espera a que haga push.
  Netlify puede tardarse 1-2 minutos en actualizar tras el push.

**"Datos no se actualizan en Sheets"**
→ Ejecuta `python sync_supabase_to_sheets.py` manualmente.
  Revisa los logs si falla. Verifica credenciales Supabase en `.env.local`.
