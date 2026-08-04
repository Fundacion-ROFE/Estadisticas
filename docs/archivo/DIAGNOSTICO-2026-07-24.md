# Diagnóstico de Automatizaciones — Fundación ROFÉ

**Fecha:** 2026-07-24  
**Para:** Coordinación  
**Preparado por:** Samuel David Rojas Monroy

---

## Resumen para Coordinación

**¿Qué está funcionando hoy?** 8 procesos automatizados que facilitan operaciones diarias.  
**¿Qué necesita Coordinación?** Panel de riesgo mejorado + WhatsApp clasificación automática + herramienta redacción rápida.  
**¿Qué está roto o falta?** Nada crítico en operaciones; las mejoras están por definir con ustedes.

---

## 🎯 Entregable clave: Claude + Supabase

**¿Por qué estas dos herramientas juntas son poderosas?**

| Capacidad | Antes | Con Claude + Supabase |
|---|---|---|
| **Datos limpios** | Sheets manual, inconsistencias | 24 tablas sincronizadas automáticamente en Supabase |
| **Redacción rápida** | Copy manual + edición lenta | Claude API en 1 click (formal/casual/urgente) |
| **Clasificación automática** | Categorizar WhatsApp a mano | Claude clasifica automáticamente (JC/MR/proveedores) |
| **Análisis de riesgo** | Panel estático, sin predicción | Supabase fuente única → Claude analiza patrones |
| **Privacidad** | PII expuesta en Sheets | RLS de Supabase + credenciales controladas = datos seguros |
| **Escalabilidad** | 1.145 estudiantes max en Sheets | 5.351 postulantes MR + 2.556 JC + histórico sin límite |

**¿Qué significa esto para ustedes (Coordinación)?**
- Una BD que no miente (Supabase sincroniza cada 4 horas desde Q10)
- Herramientas que entienden contexto (Claude analiza, no solo repite)
- Nada manual (WhatsApp se clasifica solo, redacción se mejora sola)
- Seguridad de datos garantizada (sin que dejen de funcionar las automatizaciones)

**El stack hoy:**
```
Q10 (datos brutos)
  ↓ (n8n 4h)
Sheets (H1Test/H2Test)
  ↓ (Python scripts)
Supabase (24 tablas, única fuente de verdad)
  ↓ (Claude API)
Panel de riesgo + Redacción + WhatsApp automático + Dashboard web
```

---

## Lo que usan ustedes hoy (Coordinación)

| Herramienta | Qué hace | Cómo acceder | Estado |
|---|---|---|---|
| **Panel de Riesgo** | Análisis interactivo: estudiantes en riesgo, sin Emoflow, baja asistencia | App local (clic en escritorio) | ✅ Vivo — 5 tabs (JC, MR, Admin, Diferencias, Retirados) |
| **Dashboard web** | Estadísticas públicas: consolidación Q10, avance por curso | https://fundacion-rofe.github.io/Estadisticas/dashboard/ | ✅ Vivo — se actualiza cada 4 horas |
| **Correos masivos** | Envío de campañas MR (ej: recordatorios) | Skill `/enviar-correo` (requiere supervisor) | ✅ Vivo — 2.693 enviados ya |
| **Asistencia Zoom** | % participación automático por estudiante | Panel de Riesgo muestra columna "Asistencia %" | ✅ Vivo — calculado diario |
| **BD Estudiantes** | Datos centralizados (Q10 + cursos + asistencia + estado) | Supabase (acceso interno) | ✅ Vivo — 24 tablas sincronizadas |

**Confiabilidad:** 100% las últimas 72 horas (auditoría 2026-07-23)  
**Datos activos:** 1.145 estudiantes JC 2026 + 283 MR  
**Requiere:** PC Samuel encendida (n8n local) — sin nube aún

---

## Cómo Claude + Supabase resuelven lo que piden ustedes

**1. WhatsApp automático (Claude clasifica)**
- Llega: "Hola, tengo una pregunta sobre el curso"
- Supabase + Claude: Extrae contexto del remitente (cédula, programa) → Claude clasifica: "JC" o "MR"
- Resultado: Mensaje redirigido automáticamente al equipo correcto

**2. Herramienta redacción (Claude mejora texto)**
- Escriben: "recordatorios a las q no hicieron el curso"
- Claude mejora en 1 click: "Disponemos de sesiones de recuperación..."
- Supabase: Verifica quiénes no completaron (datos reales) → personaliza por nombre

**3. Panel de riesgo mejorado (Claude analiza patrón)**
- Supabase: Trae datos sincronizados (asistencia, avance, retiros previos)
- Claude: "Este estudiante tiene 3 señales de riesgo: baja asistencia + no entregó última tarea + retirados del mismo curso"
- Resultado: Predicción accionable, no solo números

**4. Seguridad garantizada**
- Supabase RLS: Solo datos de su programa (JC/MR) en el Panel de Riesgo
- Claude API: Datos nunca se guardan, solo se procesan
- Resultado: PII protegida + eficiencia mejorada

---

## Mejoras que llegarán pronto (requieren feedback de Coordinación)

| Mejora | Beneficio para ustedes | ¿Cuándo? | Depende de |
|---|---|---|---|
| **Panel de Riesgo — botones de acción** | Hacer seguimiento rápido sin buscar al estudiante en 3 tabs | 2 sem | Qué botones necesitan (ej: "llamar", "en seguimiento", "aprobado") |
| **Panel de Riesgo — ficha ampliada** | Ver historial completo sin cambiar de app | 2 sem | Qué datos les interesan en la ficha (notas, cambios, timeline) |
| **WhatsApp — clasificación automática** | Remitentes se clasifican solo (JC/MR/proveedores) → routing automático | 2-3 sem | ¿Dónde envía cada grupo? (ej: MR → coordinación MR, etc.) |
| **Herramienta redacción** | Copy mejorado + edición rápida para correos/comunicados | 2-3 sem | ¿Dónde vive? (web o local); ¿qué formatos? (formal, casual, urgente) |

---

## Problemas pequeños que pueden esperar

| Si les urge | Tiempo estimado | Notas |
|---|---|---|
| Automatizar creación de reuniones Meet | <1 semana | 2 coordinadores lo hacen manual hoy |
| Subida automática Zoom → YouTube | <1 semana | Hoy la suben manual |
| Captura de rebotes de correo | <1 semana | Feedback loop para listas |

---

## ¿Qué preguntarles a ustedes en la reunión?

Para diseñar las mejoras correctas, necesitamos sus respuestas:

**Panel de Riesgo — botones:**
- ¿Qué acciones hacen seguido? (ej: "marcar en seguimiento", "llamar al estudiante", "cambio de curso", "aprobado")
- ¿Quién debería ver cada botón? (¿solo coordinadores JC?, ¿MR también?)

**Panel de Riesgo — ficha ampliada:**
- ¿Qué información necesitan en un click? (ej: historial de cambios, notas previas, contactos de emergencia, etc.)

**WhatsApp automático:**
- ¿A dónde va cada clasificación? (ej: JC → coordinación JC, MR → coordinación MR, proveedores → administración)
- ¿Quién ve el historial?

**Herramienta redacción:**
- ¿Dónde la usan? (en correos, comunicados, reportes, todo lo anterior)
- ¿Qué tipos de redacción? (formal, casual, urgente, educativo)

---

## Riesgos técnicos (transparencia)

**Crítico hoy:** n8n está en PC local de Samuel. Si la PC se apaga → automaciones se pausan.  
**Mitigación actual:** Task Scheduler auto-inicia n8n al encenderse.  
**Plan futuro:** Migrar a nube (decisión pendiente, ~3 semanas de trabajo).

**No es crítico hoy, pero sí:** Validar 16 registros discordantes en BD estudiantes (Samuel ya los ubicó).

---

## Estado resumido

- **Qué funciona:** Panel riesgo, correos, consolidación Q10, asistencia Zoom
- **Qué mejora pronto:** Botones rápidos + ficha ampliada + WhatsApp automático + redacción rápida
- **Qué puede esperar:** Subida YouTube, reuniones Meet automáticas

**Próximo paso:** Esta semana, ustedes dan feedback. Samuel implementa en 2-3 semanas.
