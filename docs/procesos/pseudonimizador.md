# Pseudonimizador — Herramienta de privacidad para IA

**Estado:** Completado (en producción)
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

### Web Worker para archivos grandes (≥ 22 MB / 44 pestañas)
- Todo el procesamiento pesado (fases 1-3 de codificación, decodificación) corre en un
  **Web Worker inline** con heap propio, aislado del hilo de la UI.
- El Worker se construye como `Blob URL` en tiempo de ejecución → sigue siendo un único
  `.html` estático, sin dependencias adicionales.
- Output usa `XLSX.write(..., {type:'buffer'})` → `Uint8Array` transferible sin copia
  de vuelta al hilo principal. (`uint8array` no existe en SheetJS 0.18.5 — usar `buffer`.)
- Si el Worker se queda sin memoria, el error llega como mensaje `{type:'error'}` al
  manejador del hilo principal en vez de matar la pestaña completa.
- Barra de progreso por fase: Analizando pestañas → Codificando valores → Generando Excel → Escribiendo.
- Fase 3 usa reemplazo directo celda-a-celda en lugar de rebuild AoA — preserva estructura
  dispersa del xlsx original y evita la explosión de tamaño (22 MB → 202 MB era el bug).

### Detección PII ampliada (2026-07-01)
Columnas detectadas automáticamente además de las originales:
- `contraseña`, `credencial`, `clave`, `password` — credenciales en texto plano
- `foto`, `imagen`, `rostro` — columnas con URLs de fotos biométricas
- `\bnombres?\b` (antes `\bnombre\b`) — detecta tanto "Nombre" como "Nombres"
- Valores: prefijos internacionales `+NNN...` y URLs `http/https` (fotos en Drive)
- Emails embebidos en campos de texto libre (Novedades, Diagnóstico, etc.) se detectan
  y pseudonimizan inline aunque la columna no esté marcada como PII

### Tab "Pegar texto" (2026-07-01)
Para rangos simples sin necesidad de subir un archivo completo:
- Usuario copia celdas de Excel/Sheets con Ctrl+C → pega en textarea → codifica → copia resultado
- Misma clave HMAC → pseudónimos idénticos y compatibles con el flujo de archivo
- Sección de decodificación en el mismo tab: cargar .json + pegar TSV codificado → restaurar → copiar
- El `.json` generado tiene `origen: 'pegado directo (texto)'` para distinguirlo del flujo de archivo
- Crypto corre en el hilo principal (datos pequeños → no necesita Worker)

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

### Fase 5 — Deploy y entrega (completada 2026-06-30)
- [x] Push a GitHub Pages → URL pública disponible (commit `9c6ffb3`)
- [ ] Demo con el equipo
- [x] Soporte archivos reales de 44 pestañas / 22 MB — Web Worker implementado
- [x] Documentar gotchas de producción (ver sección Gotchas)

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
- **OOM en archivos grandes (≥ 22 MB / 44 pestañas):** el problema raíz es que SheetJS
  mantiene las 44 pestañas en el objeto `newWb` simultáneamente en memoria hasta que
  `XLSX.write` las serializa. Con 44 pestañas el pico puede superar 600 MB en el heap
  del hilo principal. **Solución:** Web Worker con heap propio (implementado en Fase 5).
  Si el Worker también se queda sin memoria (archivos > ~150 MB), la siguiente solución
  sería construir el XLSX como un ZIP con `fflate`, procesando una pestaña a la vez
  sin acumular el workbook — no implementado porque no es necesario para 22 MB.
- **Explosión de tamaño (22 MB → 202 MB):** `aoa_to_sheet` con `defval:''` crea entradas
  XML para cada celda del rango, incluyendo vacías. Para una hoja de 1000×200 celdas
  esto genera 200 000 nodos en vez de los ~10 000 no vacíos reales. **Solución:** reemplazo
  directo celda-a-celda (`for addr in ws`) que preserva la estructura dispersa original.
- **`type:'uint8array'` no existe en SheetJS 0.18.5** — usar `type:'buffer'` (devuelve
  `Uint8Array` en browser, cuyo `.buffer` es el `ArrayBuffer` transferible al hilo principal).
- **Columna "Nombres" (plural) no detectada:** regex original `\bnombre\b` no coincide
  con "Nombres". Corregido a `\bnombres?\b`.
- **Credenciales en texto plano:** columnas "Contraseña" y "Credencial" no estaban en la
  lista de PII. Detectadas en auditoría de seguridad externa — añadidas en 2026-07-01.
- **Emails en campos libres:** columnas de texto como "Novedades" o "Breve explicación"
  pueden contener emails no estructurados. El sistema ahora los detecta con regex inline.
- **Blob Worker y CSP:** si la organización tiene Content-Security-Policy que bloquea
  `blob:` workers, el procesador no arrancará. En ese caso, servir el HTML desde un
  servidor que permita `worker-src blob:` en sus cabeceras CSP.

---

## Pendiente / Próximos pasos

- Demo con el equipo (Fase 5, único ítem restante)
- Evaluar si se necesita soporte para Google Sheets directamente (vía API) en una v2
- Decidir si se agrega columna `Retirados` al flujo de Q10 (decisión pendiente del equipo)
  → si se agrega, actualizar los campos de detección automática de PII si aplica
