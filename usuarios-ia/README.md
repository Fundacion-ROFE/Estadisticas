# Gobernanza de contexto IA — estructura por usuario

> Ver proceso completo en [[gobernanza-contexto-ia]] (`docs/procesos/gobernanza-contexto-ia.md`).

> **Este repo (`Fundacion-ROFE/Estadisticas`) es público.** El diseño siempre asumió un repo
> privado dedicado para `usuarios-ia/` — pendiente de crear (requiere decisión/permisos de
> Samuel). Mientras tanto: el contenido de `CLAUDE.md`/`skills/` de cada persona puede vivir
> acá (no es PII, aunque sí info operativa interna), pero **ningún `logs/` de sesión real se
> activa hasta migrar al repo privado** — ver el detalle en `gobernanza-contexto-ia.md`.

Repo **central** (no uno por persona). Una carpeta por usuario de la organización que usa
Claude/IA en su trabajo:

```
usuarios-ia/
├── README.md                    ← este archivo
├── _plantilla/                  ← copiar para dar de alta a una persona nueva
│   ├── CLAUDE.md                ← contexto/instrucciones asignadas a esta persona
│   ├── skills/                  ← skills habilitados (copiar, no symlink — debe quedar
│   │                               versionado igual que el resto)
│   └── logs/                    ← transcripciones de sesión, SOLO después de pasar por
│                                   scan_pii.py (ver scripts/gobernanza-ia/)
└── <nombre-persona>/
    ├── CLAUDE.md
    ├── skills/
    └── logs/
        └── YYYY-MM-DD_sesion.md
```

## Regla no negociable

Ningún archivo entra a `logs/` sin pasar antes por `scripts/gobernanza-ia/scan_pii.py`.
Si el scan encuentra un patrón de PII sin pseudonimizar (cédula, email, celular, nombre
completo en contexto sensible), el commit se bloquea — no se "arregla a mano y se sube
igual". Mismo principio que ya aplica en `tools/` (gitignoreado) y en el pseudonimizador:
dato individual real nunca llega a un repo, ni siquiera privado.

Ver el gotcha de `docs/convenciones.md` ("secreto commiteado por error", 2026-07-14):
un repo privado no es sinónimo de seguro, y el propio reporte de una fuga puede
convertirse en la fuga si repite el valor real. `scan_pii.py` nunca imprime el valor
encontrado completo — solo una versión enmascarada y la ubicación.

## Cómo dar de alta a una persona nueva

1. Copiar `_plantilla/` a `usuarios-ia/<nombre-persona>/`.
2. Completar su `CLAUDE.md`: Rol/Permisos/Skills/Restricciones, y la línea de "Carpeta de
   este contexto en GitHub" del encabezado con su URL real. **No tocar** las secciones fijas
   ("Conexión a la base de datos", "Reglas de datos", "Límites de autonomía y luz verde de
   Samuel") — son iguales para todas las personas, copiar-pegar tal cual.
3. Copiar (no symlink) los skills que le aplican a `skills/`.
4. Los `logs/` se llenan solos vía el pipeline de `scripts/gobernanza-ia/` (hook `Stop` local
   de Claude Code con `commit_y_push.py --usuario <nombre-persona>`) — no escribir ahí a mano,
   y no activar hasta que exista el repo privado (ver nota arriba).
