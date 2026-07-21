# WordPress — tocaunavida.org (Fundación ROFÉ)

**Estado:** En progreso (acceso API funcionando; refresco visual en curso)
**Última actualización:** 2026-07-16
**Procesos relacionados:** [[mr-website]] (sitio distinto — Angular/Express en mujeresrofe.com) · [[panel-datos-etl]] (el panel Netlify se embebe aquí) · [[mujeres-rofe-inventario-contenido]] (insumo para rediseño standalone)

## Qué es

Sitio institucional público de la Fundación ROFÉ (`tocaunavida.org`). **Es WordPress + Elementor Pro**,
NO confundir con `mujeresrofe.com` (que es el proyecto Angular/Express documentado en [[mr-website]]).
Corre en un droplet de DigitalOcean (IP `143.110.201.40` — la BD interna aún referencia esa IP como
siteurl histórico en algunos assets).

## Stack detectado

- **Tema activo:** `hello-elementor` (los otros: astra, twentytwenty* instalados sin usar)
- **Constructor:** Elementor 4.1.4 + Elementor Pro 3.28.2 — el diseño vive en la BD (`_elementor_data`), no en PHP
- **Kit global activo:** post id **6** ("Kit por defecto") — colores/tipografía globales + `custom_css` sitewide
- **Plugins observados (por CSS/tablas):** LiteSpeed Cache, Wordfence, Rank Math, WPForms, Fluent Forms,
  Ninja Forms, Smart Slider 3, LayerSlider, JoinChat (WhatsApp), Google Site Kit, Essential Addons, Ele Custom Skin
- **Tipografía de marca:** Gilroy (coincide con manual de identidad)
- **Paleta del Kit:** `#EEC935` `#D1793F` `#F93548` `#406C9E` `#6EA050` `#6FA0BC` `#FF9714` naranja ·
  `#E9EAEC` gris bg · `#0C175D` azul principal

## Acceso programático (API REST)

- **Application Password** de WordPress (usuario `Samuel ROFE`, id 24, nombre del token: `claude-code`).
  Credencial local en `.env.local` (gitignoreado) — NUNCA en docs/ ni en git. Revocable desde
  wp-admin → Usuarios → Perfil → Contraseñas de aplicación.
- Basic Auth contra `https://tocaunavida.org/wp-json/wp/v2/...`
- Campos meta de Elementor expuestos en la API: `_elementor_data`, `_elementor_page_settings` (con
  `context=edit`) — se puede leer/escribir el diseño completo de una página sin entrar a wp-admin.
- Limpiar cache CSS de Elementor: `DELETE /wp-json/elementor/v1/cache` (regenera al siguiente pageview).
- Colores globales (solo lectura útil): `GET /wp-json/elementor/v1/globals/colors`.

## Trabajo hecho (2026-07-16)

1. **Backup completo con Duplicator** (plugin) → `Downloads\wordpress\` (1.3 GB zip + installer.php).
   ⚠ El export NO incluyó `wp-content/plugins/` (ver Gotchas).
2. **Réplica local en Docker** (`Downloads\wordpress\wp-local\docker-compose.yml`): WordPress + MariaDB,
   BD real importada, search-replace IP→localhost:8080. Sin plugins se ve rota — útil solo para
   inspeccionar BD/temas, no para previsualizar diseño.
3. **Página "Panel De Datos"** (id 18705, `/panel-de-datos/`, publicada) con iframe del panel Netlify.
4. **Migración del panel Netlify:** repo nuevo `comunicaciones-ai/Panel-De-Datos` (antes
   soportejunior-codeJR/PowerBi que dejó de desplegar) → URL nueva
   `https://venerable-truffle-331f3c.netlify.app` (ver [[panel-datos-etl]]).
5. **Refresco visual global (Kit 6):** sombra nativa de imágenes + `custom_css` sitewide (hover con
   elevación en botones/iconos, barrido de brillo en botones, subrayado degradado `#F93548→#FF9714`
   en headings). Respaldo del estado previo: `kit6_original_settings.json` (scratchpad de la sesión).
6. **Página de prueba id 18716** ("Mujeres ROFÉ", draft): rediseño visual iterativo vía
   `_elementor_page_settings.custom_css` scoped a `body.page-id-18716`. Referencia de diseño aprobada
   por el equipo: https://front-end-visuals-reborn.lovable.app (paleta `#ef2b3c` `#ff5964` `#f6a129`
   `#1a7bb8` `#4bb04f` `#f2c40b` `#1f2937`, tarjetas rounded-2xl blancas con sombra, botones pill,
   chips circulares con tinte al 8%).

## Gotchas

- **Duplicator omitió `wp-content/plugins/`** en el export — la BD referencia ~15 plugins que no
  vinieron. Para una réplica local fiel hay que re-exportar verificando el paso Scan, o bajar plugins
  por SFTP/SSH.
- **Las páginas draft devuelven 404 público** — no se pueden verificar con curl anónimo; usar el
  editor de Elementor o Vista previa con sesión.
- El `custom_css` del Kit aplica a TODO el sitio — cambios de página de prueba deben ir scoped
  (`body.page-id-XXXXX`) en el `custom_css` de esa página, no en el Kit.
- El editor REST devuelve `_elementor_data` como **string JSON** (doble-encoded) dentro del meta.
- El `.env` con espacios necesita comillas para `source` en bash.
- Hay 34+ páginas publicadas, varias de test/legacy (`test`, `test-juan`, `toca-una-vida-v2`,
  `quienes-somos-2`…) — posible limpieza futura.

## Cambio de enfoque (2026-07-16, tarde) — de edición en vivo a standalone

El refresco visual por API directamente sobre el Kit/páginas de WordPress se **revirtió por
completo** (ver Gotchas) tras dificultades para verificar visualmente los cambios (cache de
Elementor por página, sin herramienta de navegador para confirmar antes de publicar). Kit 6
restaurado a su estado original; sitio público sin ningún rastro de los experimentos.

**Nuevo plan acordado:** en vez de editar Elementor a ciegas, construir una página **HTML+CSS+JS
standalone** (autocontenida, sin WordPress) con mejor calidad visual que la actual, usando:
- [[mujeres-rofe-inventario-contenido]] como fuente de verdad de contenido (todo el texto, imágenes,
  enlaces y videos de `/mujeres-rofe/` extraídos vía API el 2026-07-16)
- La referencia Lovable (`front-end-visuals-reborn.lovable.app`) como fuente de verdad de estilo
- Solo se integra a WordPress **después de aprobación**, evitando repetir el ciclo de prueba-error
  en producción

## Pendiente

- [ ] **Esperar señal del usuario** para construir el HTML/CSS/JS standalone del rediseño
- [ ] Decidir mecanismo de integración final a WordPress una vez aprobado (¿página nueva? ¿reemplazo
  del contenido de 17915 vía Elementor manual? ¿iframe?)
- [ ] Re-export Duplicator completo (con plugins) si se vuelve a necesitar réplica local fiel
- [ ] Favicon del Kit aún apunta a `http://143.110.201.40/...` (IP vieja) — corregir a dominio
- [ ] Página de prueba 18716 quedó con el custom_css de la v2 (nunca se revirtió, solo el Kit
  global) — sigue en draft, sin impacto público, pero pendiente de limpiar o reutilizar
