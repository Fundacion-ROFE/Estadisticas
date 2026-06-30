# Pseudonimizador — Herramienta de privacidad para IA

**Estado:** En progreso
**Última actualización:** 2026-06-30
**Procesos relacionados:** [[dashboard-web]] · [[q10-consolidacion]]

## Qué hace

Convierte archivos Excel/CSV con PII (cédulas, emails, nombres, celulares) en versiones
pseudonimizadas seguras para compartir con herramientas de IA externas, manteniendo
la consistencia entre pestañas y la trazabilidad por usuario. Incluye el proceso inverso:
restaurar los datos reales a partir del diccionario de recuperación.

---

## Flujo de uso

```
Archivo original (.xlsx / .xls / .csv)
    │
    ▼ [Pantalla: Codificar]
    │  1. Usuario ingresa su nombre y clave personal
    │  2. Sube el archivo
    │  3. Selecciona qué pestañas procesar (checkboxes)
    │  4. Confirma qué columnas encriptar por pestaña
    │     (el sistema detecta automáticamente PII)
    │  5. Click "Codificar y descargar"
    │
    ├──► 📄 datos_codificado.xlsx  → va a la IA
    └──► 🔑 clave_{usuario}_{fecha}.json  → queda con el usuario (NUNCA a la IA)

        [IA recibe el Excel, hace sus cambios]

datos_modificado.xlsx (devuelto por la IA)
    │
    ▼ [Pantalla: Decodificar]
    │  1. Sube datos_modificado.xlsx
    │  2. Sube clave_{usuario}_{fecha}.json
    │  3. El sistema verifica que el .json corresponde al archivo
    │  4. Click "Restaurar y descargar"
    │
    └──► 📄 datos_restaurado.xlsx  → ingresa a la DB original
```

**Para buscar un registro específico por su valor real:**
- Pantalla auxiliar "Buscar": ingresa la cédula/nombre real → obtiene el pseudónimo
- Busca ese pseudónimo en el Excel codificado para identificar la fila

---

## Decisiones de arquitectura

### App web estática (GitHub Pages)
- URL pública, **cero instalación** en cada PC
- TODO el procesamiento corre en el navegador → ningún byte sube a ningún servidor
- Funciona en Windows, Mac, cualquier navegador moderno (Chrome, Edge, Firefox)
- GitHub Pages: 100 GB/mes bandwidth — más que suficiente

### HMAC-SHA256 + diccionario local
- Pseudónimo = primeros 12 chars del HMAC-SHA256(valor + clave_personal)
- **Determinístico**: la misma cédula en la pestaña 1 y en la pestaña 50 produce
  el mismo pseudónimo → la IA puede cruzar registros entre pestañas
- **Auditabilidad**: cada persona usa su propia clave → pseudónimos distintos entre usuarios
  → si hay mal manejo, se sabe quién generó el archivo
- **Reversibilidad**: el .json descargado es el diccionario `{pseudónimo → valor_real}`
  → sin el .json no hay recuperación (igual que perder una contraseña)

### Clave personal por usuario
- No hay clave maestra de organización
- Cada persona gestiona su .json
- Si se pierde el .json = datos irrecuperables (se avisa prominentemente en la UI)

### Multi-formato
- Input: `.xlsx`, `.xls`, `.csv`
- Output: siempre `.xlsx` (para preservar estructura multi-pestaña)
- Librería: SheetJS (xlsx) desde CDN — sin instalación

---

## Detección automática de columnas PII

El sistema marca automáticamente como candidatas a encriptar las columnas cuyo:
- **Nombre contiene:** cédula, cedula, identificación, identificacion, id, dni,
  nombre, apellido, email, correo, celular, telefono, tel, phone, documento
- **Contenido coincide con:** formato email (`@`), números de 7-12 dígitos (IDs/cédulas),
  números de 10 dígitos (celulares)

El usuario puede desmarcar cualquier columna antes de procesar.

---

## Estructura del archivo .json de recuperación

```json
{
  "meta": {
    "usuario": "Samuel",
    "fecha": "2026-06-30T14:30:00",
    "archivo_origen": "datos.xlsx",
    "pestanas_procesadas": ["Hoja1", "Matriculados"],
    "columnas_por_pestana": {
      "Hoja1": ["Cédula", "Email"],
      "Matriculados": ["Identificacion", "Correo", "Celular"]
    }
  },
  "diccionario": {
    "a3f7b2c1d4e5": "Samuel Rodriguez",
    "b2c3d4e5f6a7": "1234567890",
    "...": "..."
  }
}
```

---

## Plan de implementación — Semana 2026-06-30

### Fase 1 — Arquitectura + docs (completada 2026-06-30)
- [x] Definir arquitectura y decisiones de diseño
- [x] Documentar proceso y plan de acción

### Fase 2+3+4 — App completa (completada 2026-06-30)
- [x] Crear `docs/pseudonimizador/index.html` — app de una sola página, 3 tabs
- [x] Integrar SheetJS (leer Excel/CSV → objeto JS en memoria)
- [x] Detección automática de columnas PII (nombre + patrón de contenido)
- [x] UI de selección: checkboxes de pestañas + checkboxes de columnas por pestaña
- [x] Implementar HMAC-SHA256 (Web Crypto API nativa del navegador)
- [x] Generar archivo codificado + .json de recuperación con metadata completa
- [x] Botones de descarga diferenciados (📄 para IA · 🔑 para guardar)
- [x] Motor de decodificación: upload Excel modificado + .json → restaurar → descargar
- [x] Buscador bidireccional: valor real ↔ pseudónimo en el diccionario .json
- [x] UX para usuarios no técnicos: pasos numerados, advertencias prominentes, drag-and-drop

### Fase 5 — Deploy y entrega (pendiente)
- [ ] Push a GitHub Pages → URL pública disponible
- [ ] Demo con el equipo
- [ ] Pruebas con archivos reales de 44 pestañas
- [ ] Documentar gotchas adicionales encontrados en producción

---

## Ubicación del archivo

```
docs/pseudonimizador/
└── index.html    ← app completa (HTML + CSS + JS en un solo archivo)
```

---

## Gotchas / Limitaciones conocidas

- **El .json es tan sensible como el archivo original** — contiene los valores reales.
  Si se pierde o se comparte accidentalmente, la pseudonimización fue en vano.
- **Sin clave = sin recuperación** — advertir prominentemente en la UI.
- **Valores numéricos en Excel:** SheetJS puede leer números como `number` en vez de
  `string`. El HMAC se aplica sobre `String(valor)` para garantizar consistencia.
- **Celdas vacías:** se dejan vacías — no se pseudonimizan valores nulos.
- **Columnas con datos mixtos** (ej: una columna "ID" que tiene cédulas y también textos
  como "N/A"): el sistema pseudonimiza TODO lo que encuentre, incluyendo los "N/A".
  Aclarar esto al usuario en la detección.

---

## Pendiente / Próximos pasos

- Implementar Fases 2-5 según el plan de la semana
- Evaluar si se necesita soporte para Google Sheets directamente (vía API) en una v2
- Decidir si se agrega columna `Retirados` al flujo de Q10 (decisión pendiente del equipo)
  → si se agrega, actualizar los campos de detección automática de PII si aplica
