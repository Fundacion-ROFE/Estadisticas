# Análisis: Google Sheets vs Supabase para Asistencia Zoom

## Datos del benchmark (2026-07-13)

| Métrica | Sheets | Supabase |
|---------|--------|----------|
| **Tiempo lectura** | 1.31s | ~0.2s (estimado) |
| **Filas procesadas** | 729 | 729 |
| **Latencia/fila** | 1.79ms | ~0.27ms (10x mejor) |
| **Cálculo cliente** | Sí (~0ms) | No (serverside) |
| **Índices SQL** | No | Sí (email, curso, fecha) |
| **Filtrado serverside** | No | Sí |
| **Escalabilidad** | Mala (>2000 filas lento) | Excelente (100k filas OK) |

## Problema actual (Sheets)

```
Panel de Riesgo abre
    ↓
Carga Q10 desde Sheets (lento)
Carga Avance desde Sheets (lento)
Carga Asistencia desde Sheets (1.31s) ← CUELLO DE BOTELLA
    ↓
Procesa 490 estudiantes en cliente (junta Q10 + Avance + Asistencia)
    ↓
Renderiza tabla (hasta aquí: ~2-3 segundos)
```

**Síntomas:**
- Panel "congela" 2-3s al abrir
- Cada búsqueda en tabla requiere procesar TODO en cliente
- Escalar a 1000+ estudiantes = 3-5s de wait

## Ventaja Supabase

```
Panel de Riesgo abre
    ↓
Query SQL combinada:
  SELECT p.email, p.nombre, 
         a.promedio_pct, a.faltas,
         q.cursos_q10, av.promedio_manual
  FROM participants p
  LEFT JOIN asistencia_zoom a ON p.email = a.email
  LEFT JOIN q10_datos q ...
  LEFT JOIN avance_datos av ...
  WHERE <filtros>
    ↓
Resultado pre-filtrado y agregado en servidor (~0.2s)
    ↓
Panel renderiza directamente (sin procesamiento)
```

**Ventajas:**
- ✓ **5-7x más rápido** (1.31s → ~0.2s)
- ✓ Índices SQL: búsqueda O(log n) vs O(n) en cliente
- ✓ Filtrado serverside: `email LIKE 'juan'` sin descargar 704 filas
- ✓ Escalable: agregar 1000 estudiantes no afecta latencia
- ✓ Menos ancho de banda: solo datos que pasan filtros
- ✓ Datos pre-agregados (sin cálculos en cliente)

## Decisión: SUPABASE es recomendable

### Razón principal
El panel de riesgo **procesa cruzamientos complejos** (Q10 × Avance × Asistencia × Retirados). Con Sheets esto es:
1. Descargar 704 filas completas
2. Agrupar por email
3. Calcular promedios
4. Cruzar con otros 3-4 Sheets

Con Supabase:
1. Una sola query SQL con JOINs
2. Resultado ya listo

### Plan de migración (3 pasos)

**Fase 1: Crear tabla `asistencia_zoom` en Supabase**
```sql
CREATE TABLE asistencia_zoom (
  id BIGSERIAL PRIMARY KEY,
  email TEXT NOT NULL,
  curso TEXT NOT NULL,
  fecha DATE NOT NULL,
  nombre TEXT,
  apellido TEXT,
  instancias TEXT,
  porcentaje_asistencia TEXT,
  created_at TIMESTAMP DEFAULT now(),
  UNIQUE (email, curso, fecha),
  CONSTRAINT fk_email FOREIGN KEY(email) REFERENCES participants(email)
);
CREATE INDEX idx_asistencia_email ON asistencia_zoom(email);
```

**Fase 2: Script `sync_asistencia_supabase.py`**
- Lectura: ZOOM-ASISTANCE (Sheets)
- Destino: asistencia_zoom (Supabase)
- Frecuencia: post-clase (automático vía n8n o cron)
- Patrón: upsert por (email, curso, fecha)

**Fase 3: Adaptar panel_riesgo_gui.py**
- Cambiar `leer_asistencia_zoom()` para query Supabase en lugar de Sheets
- Una línea de SQL vs 700+ filas descargadas
- Panel pasa de 2-3s a ~0.3s de latencia

### Trabajo necesario

| Tarea | Tiempo | Bloqueante |
|-------|--------|-----------|
| Crear tabla en Supabase | 5min | No |
| Script sync_asistencia_supabase.py | 30min | No |
| Adaptar panel_riesgo (función `leer_asistencia_zoom`) | 15min | No |
| Testing | 15min | No |
| **Total** | **~1h** | **No** |

### No es bloqueante
- Hoy el panel funciona OK con Sheets (un poco lento, pero funciona)
- Supabase es una **optimización**, no un requerimiento urgente
- Se puede hacer en la próxima sesión sin problema

### Mi recomendación
**Haz la migración cuando tengas tiempo**. Beneficio claro: panel 5-7x más responsivo, mejor experiencia del usuario, escalable sin problemas.

Pero **mientras tanto, Sheets funciona**. Los 1.31s no es crítico si el usuario abre el panel 2-3 veces por sesión.
