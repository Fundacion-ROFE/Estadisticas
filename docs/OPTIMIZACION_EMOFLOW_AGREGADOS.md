# Optimización: Emoflow Agregados vs Snapshots Individuales

**Problema actual:**
- Historial de ingresos usa snapshots DIARIOS de totales individuales
- Datos REDUNDANTES: si usuario A ingresó 50 veces, aparece 50 veces en el histórico
- No apto para análisis estadístico (ruido, no información)
- Panel muestra tendencias falsas (acumulación, no participación real)

**Solución propuesta:**
- Cambiar a **datos AGREGADOS cada 4 horas**
- Métricas reales: "¿cuántos % del cohorte ingresó?" (no "¿total de ingresos?")
- Limpiar: dos dimensiones de participación (Emociones + Bienestar)
- Visualizar: velocidad intra-día, distribución, por ciudad

---

## 📊 COMPARACIÓN: Snapshots Diarios vs Agregados 4h

### ❌ ACTUAL (Snapshots Diarios — Redundante)

```
Fecha       Participantes  Promedio  Mediana  Máximo
2026-07-15       827        23.2      18      309
2026-07-16       827        23.5      18      312    ← Solo aumentan (acumulativo)
2026-07-17       827        23.8      19      315    ← Ruido acumulativo
2026-07-18       827        24.1      19      318
2026-07-19       827        24.4      20      321
2026-07-20       827        24.7      20      325
```

**Problema:** El "promedio de ingresos" solo sube porque es acumulativo.
No puedes saber: "¿Cuánta gente NUEVA ingresó hoy?"

---

### ✅ OPTIMIZADO (Agregados cada 4h — Limpio)

```
Timestamp           Pct_Emoción  Pct_Bienestar  Nuevos_Ingresos_4h  Velocidad
2026-07-20 00:00        45%            32%            12                3/h
2026-07-20 04:00        48%            35%            18                4.5/h
2026-07-20 08:00        52%            38%            24                6/h
2026-07-20 12:00        55%            41%            15                3.75/h
2026-07-20 16:00        58%            43%            8                 2/h
2026-07-20 20:00        60%            45%            5                 1.25/h
```

**Ventajas:**
- % de participación real (no acumulativo)
- Dos dimensiones: Emociones vs Bienestar
- Velocidad de ingresos intra-día (cuándo se concentra actividad)
- Datos LIMPIOS para análisis estadístico
- Comprable día a día (no ruido acumulativo)

---

## 🔄 FLUJO PROPUESTO

### Nueva tabla en Supabase:
```sql
CREATE TABLE emoflow_ingresos_agregados_4h (
  id BIGSERIAL PRIMARY KEY,
  fecha DATE,
  hora_snapshot TIMESTAMP,
  grupo_ciudad VARCHAR(10),  -- BAQ, BOG, CAL, ... o NACIONAL
  
  -- Emociones
  pct_participacion_emociones DECIMAL(5,2),
  nuevos_ingresos_emociones INT,
  velocidad_ingresos_emociones DECIMAL(5,2),  -- por hora
  
  -- Bienestar
  pct_participacion_bienestar DECIMAL(5,2),
  nuevos_ingresos_bienestar INT,
  velocidad_ingresos_bienestar DECIMAL(5,2),
  
  -- Distribución (% en cada rango)
  pct_rango_0_ingresos DECIMAL(5,2),
  pct_rango_1_5_ingresos DECIMAL(5,2),
  pct_rango_6_15_ingresos DECIMAL(5,2),
  pct_rango_16_30_ingresos DECIMAL(5,2),
  pct_rango_31_60_ingresos DECIMAL(5,2),
  pct_rango_61plus_ingresos DECIMAL(5,2),
  
  fuente VARCHAR(50),  -- 'emoflow-api-4h'
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_emoflow_agg_4h 
  ON emoflow_ingresos_agregados_4h(fecha, hora_snapshot, grupo_ciudad);
```

### Cronograma:
```
Cada 4 horas:
00:00 ──► extract_emoflow_agregados.py
04:00 ──► extract_emoflow_agregados.py
08:00 ──► extract_emoflow_agregados.py
12:00 ──► extract_emoflow_agregados.py
16:00 ──► extract_emoflow_agregados.py
20:00 ──► extract_emoflow_agregados.py
```

---

## 📈 OPCIONES DE VISUALIZACIÓN MEJORADA

### 1️⃣ Gráfico: % Participación Intra-día (Línea doble)
```
100% ┤                              ╱╲
  80% ┤             ╱╲            ╱  ╲
  60% ┤           ╱  ╲         ╱      ╲
  40% ┤       ╱╲╱    ╲╱╲   ╱╲╱
  20% ┤    ╱╲╱          ╲╱╲╱
   0% ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━
      00h  04h  08h  12h  16h  20h
      
      ─── Emociones
      ─── Bienestar
```

### 2️⃣ Gráfico: Velocidad de Ingresos/Hora (Barras)
```
10/h ┤      █
  8/h ┤      █  █
  6/h ┤  █   █  █  █
  4/h ┤  █   █  █  █  █
  2/h ┤  █   █  █  █  █  █
  0/h ┗━━━━━━━━━━━━━━━━━━━━
      00h  04h  08h  12h  16h  20h
```

### 3️⃣ Heatmap: % Participación por Ciudad (Última semana)
```
       Lun  Mar  Mié  Jue  Vie  Sab  Dom
BAQ    ▓▓▓  ▓▓░  ▓▒░  ░░░  ░░░  ░░░  ░░░
BOG    ▓▓▓  ▓▓▓  ▓▓░  ▓░░  ░░░  ░░░  ░░░
CAL    ▓▓░  ▓▓░  ▓░░  ░░░  ░░░  ░░░  ░░░
CTG    ▓░░  ░░░  ░░░  ░░░  ░░░  ░░░  ░░░
...
```

### 4️⃣ Tabla: Últimas 24h (6 snapshots × 9 ciudades)
```
Timestamp       Emoción%  Bienestar%  Nuevos  Velocidad
2026-07-20 00:00  45%      32%        12      3/h
2026-07-20 04:00  48%      35%        18      4.5/h
2026-07-20 08:00  52%      38%        24      6/h
2026-07-20 12:00  55%      41%        15      3.75/h
2026-07-20 16:00  58%      43%        8       2/h
2026-07-20 20:00  60%      45%        5       1.25/h
```

---

## 🎯 IMPORTANCIA PARA EL PANEL

### Antes (Redundante):
- "Promedio de ingresos: 24.7" → No dice nada útil
- "Participantes: 827" → Estático, no cambia
- "Tendencia: subiendo" → Falsa (es acumulativa)

### Después (Limpio):
- "Participación Emociones: 60%" → Métrica clara
- "Nuevos ingresos últimas 4h: 5" → Actividad REAL
- "Velocidad: 1.25/h" → Ritmo actual (bajando al anochecer)
- "Distribución: 30% sin ingresos, 25% con 1-5" → Cohort analysis

---

## 📋 IMPLEMENTACIÓN

### Script nuevo:
- `extract_emoflow_agregados.py` (cada 4h)
- Lee "Registro de ingresos" agregado de Emoflow
- Calcula % participación por tipo (Emociones + Bienestar)
- Inserta en tabla `emoflow_ingresos_agregados_4h`

### Panel Netlify:
- Importar nueva tabla JSON
- Agregar 4 gráficos (línea, barras, heatmap, tabla)
- Filtro por ciudad + rango de fechas
- Comparador semana vs semana

### Depreciación:
- Mantener `historial_emoflow` para histórico (pero no actualizar diariamente)
- Solo usar para tendencias largas (meses)
- Datos limpios en `emoflow_ingresos_agregados_4h` (reemplazo)

---

## ✅ VENTAJAS FINALES

| Aspecto | Antes | Después |
|---|---|---|
| Granularidad | Diaria (estática) | 4h (dinámica) |
| Métrica | Total ingresos (acumulativo) | % participación (real) |
| Dimensiones | 1 (ingresos) | 3 (Emociones, Bienestar, velocidad) |
| Limpieza | Redundante (ruido acumulativo) | Limpia (delta real) |
| Análisis | Limitado | Estadístico robusto |
| Compañero | Manual, lento | Automatizado cada 4h |

---

**Próximo paso:** Importar tabla JSON en panel Netlify y agregar visualizaciones.
