# Emoflow → Supabase (nota temprana)

**Estado:** Redirect — contenido vivo fusionado en [[panel-datos-etl]]
**Última actualización:** 2026-08-04 (auditoría de documentación)

> Esta nota estaba vacía (0 bytes) pero tenía enlaces entrantes reales desde `claude_sessions.md`
> (2026-07-20/21). Era el marcador de la primera versión del proceso: ingresos a Emoflow como
> proxy de calidad, ingesta directa por API (sin Sheet intermedio), cruce por email (91.9% match),
> n8n diario 9:45 COT. La auditoría de centralización del 2026-07-21 encontró que el nodo real en
> producción todavía corría el script deprecado (`sync_emoflow.py`, hoy en
> `scripts/panel-datos/_obsoletos/`) y lo corrigió — desde entonces todo el desarrollo de Emoflow
> (incluida la serie diaria real por ciudad y el análisis de asociación con resultados) se
> documenta en **[[panel-datos-etl]]**, no aquí. No dupliques contenido: si hay novedades de
> Emoflow, van en esa nota.
