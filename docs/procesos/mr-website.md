# MR — Website Mujeres ROFÉ (mujeresrofe.com)

**Estado:** En progreso (documentación inicial — cambios por definir)
**Última actualización:** 2026-07-07
**Procesos relacionados:** [[mr-actualizacion-datos]] (misma población MR; BD paralela en Sheets) · [[wordpress-tocaunavida]] (OTRO sitio: el institucional de la Fundación es WordPress en tocaunavida.org — no confundir)

## Qué es
Sitio web público de Mujeres ROFÉ (`mujeresrofe.com`) con panel de administración de contenido.
**El código NO vive en este repo** — es un proyecto independiente con su propio ciclo de deploy:

```
C:\Users\EstudiantesJC\Downloads\Mujeres-Rofe-Website\   ← repo independiente (aún sin .git local)
├── back/     Node 18 + Express 4 + TypeScript · MongoDB (Mongoose 6)
└── front/    Angular 15 (SCAM pattern, ngx-sub-form) · nginx
```

Esta nota es el nodo de documentación en el vault; el detalle operativo local vive en el
`CLAUDE.md` dentro de esa carpeta.

## Arquitectura

```
Usuario ──► mujeresrofe.com (front Angular 15, nginx en Docker)
                │  HTTP
                ▼
        api.mujeresrofe.com/api (back Express, Docker)
                │
    ┌───────────┼──────────────┐
    ▼           ▼              ▼
 MongoDB    Cloudinary     SendGrid
 (datos)    (imágenes/     (emails: registro,
             media)         forgot-password, requests)
```

- **Hosting:** Droplet de DigitalOcean. Deploy vía GitHub Actions (push a `main` → SSH al
  droplet → `git pull` + `docker-compose`). Orquestación en un **tercer repo `rofe-composal`**
  (`docker-compose.mujeres-rofe.yml`) que vive en el droplet (`~/rofe-composal`).
- **Auth:** JWT + refresh tokens (colección propia), bcrypt para passwords.
- **Backend:** clean architecture — `api/` (controllers+routes) → `domain/` (use-cases,
  repositories, mappers) → `data/` (modelos Mongoose). Config por `.env`
  (JWT_PSW, DATABASE_URI_*, CLOUDINARY_*, SENDGRID_API_KEY, PORT).
- **Frontend:** Angular 15 · componentes SCAM · `ngx-sub-form` para formularios ·
  `swiper` (sliders) · `xlsx` (export a Excel desde admin). API URL fija en
  `src/environments/environment*.ts`.

## Entidades del backend (colecciones Mongo)

| Entidad | Qué es |
|---|---|
| `user` | Usuarias registradas + admins (roles vía token middleware) |
| `notice` | Noticias, agrupadas por `channel` |
| `channel` | Canales/categorías de contenido |
| `slide` | Slides del carrusel del home (por tipo) |
| `witness` | Testimonios |
| `highlighted-city` | Ciudades destacadas |
| `form-request` | Definición de formularios dinámicos (admin los crea) |
| `request` | Respuestas/solicitudes enviadas por usuarias |
| `state` / `city` | Catálogo de departamentos y ciudades (Colombia) |
| `refresh-token` | Sesiones |

Front espejo: sección pública (home, noticias, testimonios, registro, contacto) + sección
privada `/admin` (CRUD de todas las entidades anteriores + lista de usuarias con filtros y
export xlsx).

## Relación con el ecosistema de automatización

- La población es la misma de [[mr-actualizacion-datos]], pero **son bases de datos distintas
  y no sincronizadas**: el website usa MongoDB propio; la BD-Mujeres ROFÉ 2026 es un Google
  Sheet alimentado por el Form MR2024. Cruce posible por cédula/correo — hoy no existe.
- El dashboard público ([[dashboard-web]]) muestra datos MR desde `data.json` (Q10), tampoco
  conectado al website.

## Decisiones de diseño clave

- **Código fuera de `admin-usable`:** el website tiene backend con secretos y su propio deploy
  (droplet + Actions). Se documenta aquí (nodo del vault) pero no se integra al repo, siguiendo
  el precedente de n8n/tools. `CLAUDE.md` local en la carpeta del website apunta de vuelta acá.
- Esta nota NO contiene credenciales ni URIs de conexión — `docs/` se publica en GitHub Pages.

## Gotchas / Limitaciones conocidas

- La copia local (`Downloads\Mujeres-Rofe-Website`) **no tiene `.git`** — antes de tocar código
  hay que clonar/vincular los repos remotos reales (los workflows asumen `mujeres-rofe-backend`
  y `mujeres-rofe-frontend` en GitHub + `rofe-composal` para el compose).
- `front/src/environments/environment.ts` (dev) también apunta a la **API de producción** —
  ojo al probar localmente: se escribe contra datos reales salvo que se levante el back local.
- Deploy corre como `root` en el droplet vía `appleboy/ssh-action`; secretos en GitHub
  (`DROPLET_HOST`, `DROPLET_SSH_KEY`, var `ENVIRONMENT_FILE`).
- Stack con versiones 2023 (Angular 15, Express 4, Mongoose 6, Node 18) — considerar el costo
  de upgrade antes de cambios grandes.

## Pendiente / Próximos pasos

- [ ] **Definir alcance de los cambios solicitados** (qué pide el grupo de mujeres — bloqueante)
- [ ] Localizar los repos remotos en GitHub y clonar con historial (la copia en Downloads no tiene .git)
- [ ] Verificar acceso al droplet / cuenta DigitalOcean y a los secretos de GitHub Actions
- [ ] Evaluar si conviene cruce website-Mongo ↔ BD-Mujeres ROFÉ (Sheets) por cédula
