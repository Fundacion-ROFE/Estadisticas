# WordPress — tocaunavida.org (Fundación ROFÉ)

**Estado:** En progreso (rediseño standalone construido; pendiente pegar en Elementor)
**Última actualización:** 2026-07-21
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

## Rediseño standalone — CONSTRUIDO (2026-07-21)

Página HTML/CSS/JS autocontenida lista, en `tools/mujeres-rofe-redesign/` (gitignoreado — no toca prod):

- **`index.html`** — build de trabajo con preview local (imágenes relativas `img/…`). El bloque
  autocontenido va entre marcadores `<!-- EMBED-START -->` … `<!-- EMBED-END -->` (tipografía Gilroy +
  `<style>` scopeado a `#mr-root` + markup + `<script>` vanilla). Sin dependencias externas salvo Google Fonts.
- **`wordpress-embed.html`** — DELIVERABLE para pegar en un widget HTML de Elementor / bloque HTML.
  Es solo el bloque EMBED con las rutas de imagen ya absolutas. Se regenera con
  `build_wordpress_embed.py` (relee `index.html` → reemplaza `img/…` por URLs de wp-content).
- **`build_previews.py`** — previews aislados por sección para capturas. **`quitar_fondo_bombillos.py`**
  — recorte de fondo de bombillos/nova con PIL (flood-fill desde el borde; conserva el blanco interior).

**Contenido/estilo:** basado en [[mujeres-rofe-inventario-contenido]] + estética propia (paleta ROFÉ,
Poppins). Secciones: hero, 4 frentes (R·O·F·É = Red/Oportunidades/Formación/Emprendimiento con
bombillos de colores), cursos, servicios, requisitos+pasos, testimonios, FAQ, NOVA (Erasmus+), CTA.

**Imágenes en WordPress (Media Library, subir a mano — carpeta `Downloads/imagenes-wordpress/`):**

| Imagen | Ruta wp-content | Estado |
|---|---|---|
| `bombillo-r/o/f/e.png`, `nova-logo.png` (×2), `erasmus-logo.png` | `2026/07/` | **subir** (6 archivos) |
| Foto hero (mujeres) → `fondo-mr-4.png` | `2026/04/` | YA en el sitio (asset previo) |
| Cursos (5) + PDF autorización | `2026/01/` y `2025/01/` | YA en el sitio |

**Interacciones / decisiones clave:**
- Bombillos R·O·F·É: borde inferior + resplandor + panel trasero (flip en hover) = color del propio
  bombillo. La tarjeta amarilla (Formación) lleva texto oscuro por contraste.
- NOVA: logo transparente sobre su navy original `#070332` (manual de marca), en el panel grande y en
  el logo de la fila; con animación de flotación/mecido.
- Partículas de fondo: canvas global con formas rosadas (destellos ✦, aros, corazones) que titilan —
  NO manchas difusas (feedback de la dueña: "parecía pantalla sucia").
- Hover en texto (p/li): oscurece el texto + halo claro = lectura asistida.
- Hero: foto `fondo-mr-4.png` que aparece suavemente en hover con velo rojo degradado (legibilidad).
- Botón "subir arriba" reubicado (`bottom:6.2rem; right:2rem`) para no chocar con el FAB de WhatsApp (JoinChat).
- Cursos renombrados por la dueña: "Habilidades blandas"→"Habilidades clave" (contenido nuevo),
  "Ventas online"→"Estrategias online"; Emprendimiento = Ideación / Modelo de negocio / Validación y acción.

**Integración final:** pegar `wordpress-embed.html` en un widget HTML de Elementor en la página 17915
(o una página nueva). Lo hace Samuel manualmente.

## Ajustes v2 (2026-07-23)

Feedback de la dueña sobre el primer build, aplicado a `index.html` (+ `wordpress-embed.html`
regenerado con `build_wordpress_embed.py`, que se corrigió porque el hero dejó de usar
background-image por JS y ahora es un `<img>` directo):

- **Tipografía → Gilroy.** `#mr-root` pasó de Poppins a `'Gilroy','Century Gothic',...` (coincide con
  el manual de marca y con el Kit global de WordPress, que ya sirve Gilroy sitewide — por eso no hace
  falta `@font-face` propio, solo local cae a Century Gothic). Títulos peso 700, texto de cuerpo Gilroy
  Light (peso 300) tamaño base 15px.
- **Hero:** texto a la izquierda (columna fija, ya no centrado ni full-bleed), imagen `img/inicio.png`
  ahora SIEMPRE visible a la derecha (antes solo aparecía en hover como fondo). El halo/blobs de luz
  quedan detrás del título y se desvanecen hacia la derecha con un degradado sobre el borde de la foto.
- **Banner de stats eliminado** (4 frentes / 5 cursos / 3 servicios / $0) — quitado HTML+CSS+JS
  (contador animado también fuera).
- **"4 frentes de apoyo":** tarjetas más grandes (300→340px), bombillo 6.2rem→7.6rem, texto interno
  más grande (h3 1.18→1.35rem).
- **Formación (cursos):** el halo amarillo detrás del bombillo ya NO aparece automático — solo con
  `:hover` (antes tenía animación `mr-glow` infinita).
- **Acompañamiento ("No estás sola"):** ahora es un grid de 2 columnas — espacio de imagen reservado
  a la izquierda (`img/acompanamiento.png`, placeholder con `onerror` mientras no exista) + los 3
  servicios en lista vertical a la derecha, texto más oscuro y más grande para mejor lectura.
- **CTA "¿Lista para dar el primer paso?"** se movió: ahora aparece ANTES de la sección NOVA (antes
  iba después). También su fondo cambió de azul a rojo/rosado (paleta Mujeres ROFÉ, `--red`→`--coral`
  →`#ff8fa3`) — antes usaba el azul de NOVA, quedaba fuera de tono.
- **NOVA:** se quitó el bloque de stats "10+ Entrevistas / 50+ Empresas / 1 Guía" (las tarjetas
  detalladas de "El rol de Fundación ROFÉ" se mantienen intactas). Logo NOVA sin tocar en posición —
  la dueña pidió no moverlo, sigue sobre su navy original `#070332`. Se eliminó además la animación
  de flotación/mecido (`mr-novafloat`, wobble+rotate+scale infinito) que tenía el logo grande — pidió
  que dejara de moverse por tratarse de un logo institucional serio. El halo de luz detrás (`mr-novaglow`)
  se mantiene, es ambiental y no mueve el logo.
- Paleta rosa (partículas, gradientes rojo/coral/naranja) sin cambios.

**Resuelto:** las 2 imágenes pendientes (acompañamiento, preguntas frecuentes) ya tienen URL real en
Media Library, provistas por Samuel — ya no son placeholders. `index.html` usa el mismo patrón dual que
los cursos: `src` = URL absoluta de WordPress (funciona igual en preview local y en producción) +
`data-local` = ruta relativa opcional para servir una copia local más rápida si algún día se agrega a
`img/`. No hizo falta tocar `build_wordpress_embed.py` (solo reescribe `src="img/…"`, no `data-local`).
- Acompañamiento: `2026/01/Foto-3-encuentro-.webp`
- Preguntas frecuentes: `2023/02/WhatsApp-Image-2022-07-08-at-12.34.10-PM.jpg`

Ya no quedan imágenes pendientes en el rediseño (verificado: `build_wordpress_embed.py` reporta 0 rutas
relativas sin resolver).

**Ajuste adicional (mismo día):** foto del hero (`.mr-hero-photo`) más grande — columna del grid pasó
de `1.15fr .85fr` a `1fr 1.05fr`, `min-height` 320px→400px — y con marco orgánico tipo blob en vez de
esquinas parejas: `border-radius` asimétrico (8 valores) con una animación sutil que lo hace mutar
lentamente entre dos formas (`mr-blobshape`, respeta `prefers-reduced-motion`). Elegido entre 4
opciones de estilo presentadas (blob orgánico, polaroid, medallón circular, esquina cortada) — la
dueña prefirió el orgánico para que combine con las partículas/formas del resto del sitio.

**Revertido + fix, mismo día:** el blob se revirtió a petición de la dueña — volvió al recuadro
`border-radius:var(--r-lg)` de siempre (sin animación), pero se mantuvo el tamaño grande. El motivo real
del pedido era otro: `img/inicio.png` tiene un letrero/flecha roja grande de fondo (cartel del salón
donde se tomó la foto) que se leía como texto ajeno encima de la marca. Solución en dos partes:
1. `transform:scale(1.32) translateY(9%)` en la `<img>` — recorta/desplaza el encuadre hacia abajo así
   ya no se ve la mayor parte del letrero (sin tocar `object-fit:cover`).
2. Lo que queda del letrero (esquina superior derecha) se disuelve con un `::after` que combina
   `backdrop-filter:blur(14px)` + tinte `rgba(191,20,32,.5)` (el rojo del hero), recortado con un
   `mask-image` de dos capas — una franja delgada arriba (0-16%) + una elipse radial anclada en la
   esquina superior derecha (`radial-gradient(ellipse 90% 88% at 100% 0%, ...)`) — para que el efecto
   quede concentrado ahí y NO toque las caras de las mujeres (que están más centradas/abajo en el
   encuadre). Iterado 3 veces con capturas hasta que el letrero quedó disuelto sin afectar rostros.

**Revertido TODO el mismo día:** la dueña pidió dejar la foto del hero exactamente como estaba antes de
esta tanda de cambios (más grande + blob + fix del letrero) — se deshicieron los 3 ajustes: grid volvió
a `1.15fr .85fr`, texto a `max-width:36rem`, foto a `min-height:320px` sin `transform` en la `img`, sin
el `::after` de blur/máscara, y el responsive móvil volvió a `aspect-ratio:16/10`. El letrero de fondo
sigue visible (no se resolvió), queda documentado por si se retoma más adelante.

**Revert final del hero (mismo día):** la dueña pegó una versión vieja de `wordpress-embed.html` (de
antes de TODOS los cambios de hoy — Poppins, banner de stats, NOVA azul+amarillo mezclado, etc.) diciendo
que "se veía bien". Se confirmó con ella el alcance exacto: solo el HERO vuelve a ese estilo antiguo —
imagen de fondo `mr-hero-bgimg`/`#mr-herobg` que aparece SOLO al pasar el mouse (JS con `probe.src`,
sin la columna de foto fija a la derecha ni el grid `mr-hero-grid`/`mr-hero-text`/`mr-hero-photo`), blobs
y ring de vuelta a su posición original (`right:8%`/`right:14%`, ya no `left:18%`/`left:36%`), `.mr-hero-inner`
con `max-width:780px`. `build_wordpress_embed.py` también se revirtió para reemplazar `url('img/inicio.png')`
+ `probe.src` (patrón viejo) en vez de `src="img/inicio.png"`. TODO lo demás de hoy se mantuvo intacto:
Gilroy, banner de stats fuera, pilares más grandes, halo de Formación solo en hover, acompañamiento/FAQ
con espacio de imagen, CTA rosado antes de NOVA, NOVA 100% azul rey con títulos amarillos del logo, nota
de los $120.000.

**Último ajuste del hero (mismo día):** imagen de fondo pasó de "solo hover" a permanente
(`.mr-hero-bgimg{opacity:1}` fijo, sin transición ni regla `:hover`) y el velo oscuro se reforzó —
`linear-gradient(90deg, rgba(140,14,24,.92) 0%, rgba(160,18,28,.72) 40%, rgba(191,20,32,.28) 75%,
rgba(191,20,32,.1) 100%)` — más oscuro justo donde cae el texto (izquierda) y desvaneciendo hacia la
derecha, para que el texto quede legible con la foto siempre visible detrás. El texto ya estaba pegado
a la izquierda por estructura (`.mr-hero-inner` sin `margin:auto`, `max-width:780px`), no necesitó cambio.

**Ajuste siguiente, mismo día — quitar el velo, zoom + imagen solo a la derecha:** pidieron quitar el
efecto de sombreado sobre toda la foto (se sentía muy oscuro) y en su lugar: `.mr-hero-bgimg` ya no
cubre todo el hero (`inset:0`) sino solo la mitad derecha (`top:0;right:0;bottom:0;left:44%`), con
`background-size:150%` + `background-position:68% 35%` (zoom + encuadre movido a la derecha, mostrando
más a las mujeres). El 44% izquierdo del hero (donde va el texto) queda con el fondo de gradiente propio
del hero, sin imagen. Donde ambos se tocan (el borde izquierdo del bloque de imagen) hay una transición
suave — `linear-gradient(90deg, rgba(217,30,48,.9) 0%, rgba(217,30,48,.5) 12%, transparent 30%)` — para
un contraste leve en vez de un corte duro.

## Auditoría del sitio en vivo + sección Galería nueva (mismo día)

Se le dio permiso explícito de **solo lectura** sobre `https://tocaunavida.org/mujeres-rofe/` (el sitio
real, no el rediseño) vía `WebFetch` para comparar estructura. Hallazgos:
- El sitio en vivo YA muestra un aviso de convocatoria con fechas ("Convocatoria abierta del 26 de enero
  al 20 de febrero") — respalda la nota de los $120.000 que se agregó al rediseño.
- Nombres de cursos difieren un poco del rediseño (live: "Habilidades blandas" + "Modelo CANVAS" +
  "Identidad de marca"; rediseño: "Habilidades clave" + "Modelo de negocio" + "Validación y acción") —
  no se tocó, queda como diferencia conocida (puede ser un rename ya decidido en otra sesión, ver
  [[wordpress-fundacion-rofe]]).
- El live tiene una **galería de 3 fotos de encuentros comunitarios** (sin título propio, ubicada junto
  a "¡Puedes hacer parte de esta comunidad!") que el rediseño NO tenía. URLs reales obtenidas por
  WebFetch: `2026/01/foto-2-encuentro.webp`, `2026/01/Foto-3-encuentro-.webp` (la misma que ya usa
  Acompañamiento), `2026/01/2-encuentro-scaled.webp`.

**Nueva sección "Galería" agregada** entre Requisitos e inscripción y Preguntas frecuentes, pedida
explícitamente con "estructura similar [al hero], texto a la izquierda, imagen cambiante, mismo efecto
de luz detrás de la imagen":
- `.mr-gallery-grid` — mismo patrón 2 columnas que el resto del rediseño (texto plano a la izquierda,
  imagen a la derecha).
- Imagen: 3 `<img>` apiladas (`.mr-gallery-slide`) con crossfade automático por JS cada 4.2s
  (`setInterval` alternando clase `.mr-active`), respeta `prefers-reduced-motion` (no arranca el
  intervalo si está activo).
- Mismo "efecto de luz" que el hero pero adaptado al fondo claro de esta sección: `::after` con
  `linear-gradient(90deg, #fff 0%, rgba(255,255,255,.55) 12%, transparent 30%)` en vez del rojo del hero.

**Ajuste adicional (mismo día):** "Preguntas frecuentes" pasó de lista centrada de ancho fijo a grid
de 2 columnas — el acordeón de FAQ a la izquierda + espacio reservado para imagen a la derecha
(`img/preguntas.png`, mismo patrón `onerror`→placeholder que las demás imágenes pendientes). También
se quitó la animación de flotación/mecido del logo grande de NOVA (`mr-novafloat`) — pidieron que
dejara de moverse por ser un logo institucional serio; el halo de luz ambiental detrás se mantiene.

**Ajuste adicional (mismo día):** sección NOVA quedó 100% en tonos de azul rey — se quitaron todos los
acentos amarillos que quedaban mezclados (badge Erasmus+, texto en negrita, borde de la cita de
financiamiento, números de las tarjetas "El rol de Fundación ROFÉ", halo detrás del logo grande, blob
de fondo). Nuevos acentos: `#7db8ff` (texto/iconos claros sobre el navy) y `#3a6ee0`→`#6fa0f5`
(elementos sólidos tipo los círculos numerados). El navy de fondo (`#0b2e57`→`var(--blue)`) no cambió.

**Ajuste adicional (mismo día, ronda siguiente):**
- Fondo de TODA la sección NOVA (`.mr-nova`) pasó a `#070332` sólido — el mismo tono exacto donde ya
  vivía el logo (`.mr-ph--novamain`, `.mr-nova-logos .mr-ph--novasmall`), pedido explícito de que todo
  el bloque compartiera un solo tono en vez del degradado azul anterior.
- Títulos y subtítulos de NOVA (`h2`, `.mr-nova-tag`, `.mr-nova-rol h3`, `.mr-entregable h4`) pasaron a
  `#f0c823` — el amarillo dorado exacto de los pétalos del logo (sampleado con PIL directo de
  `img/nova-logo.png`, RGB 240,200,35). El resto de acentos (badge, negrita, números) se quedó en el
  azul de la ronda anterior — solo títulos/subtítulos usan el amarillo de marca del logo.
- **Nueva info de negocio:** después de que cierra una convocatoria, inscribirse cuesta **$120.000**
  (antes el sitio no lo mencionaba en ningún lado). Se agregó en dos sitios: (1) nota corta bajo el
  botón "REGÍSTRATE" del paso 1 en Requisitos e inscripción (clase nueva `.mr-note`, mismo patrón
  visual que `.mr-nova-funding` — borde naranja + texto pequeño), y (2) una FAQ nueva "¿Qué pasa si la
  convocatoria ya cerró?" justo después de "¿La membresía tiene costo?", cuya respuesta también se
  ajustó para aclarar "mientras la convocatoria esté abierta" (antes decía "no tiene ningún costo" sin
  matiz, lo cual quedaba contradictorio). También se suavizó el texto del paso 3 ("sin ningún costo"
  → sin esa frase) por la misma razón.

## Pendiente

- [x] ~~Construir el HTML/CSS/JS standalone del rediseño~~ → hecho 2026-07-21
- [ ] **Subir las 6 imágenes nuevas** a Media (`2026/07/`) y **pegar `wordpress-embed.html`** en Elementor
- [ ] Confirmar carpeta/nombres reales de las 6 imágenes si WordPress las renombra (asumido `2026/07/`)
- [ ] Decidir mecanismo de integración final a WordPress una vez aprobado (¿página nueva? ¿reemplazo
  del contenido de 17915 vía Elementor manual? ¿iframe?)
- [ ] Re-export Duplicator completo (con plugins) si se vuelve a necesitar réplica local fiel
- [ ] Favicon del Kit aún apunta a `http://143.110.201.40/...` (IP vieja) — corregir a dominio
- [ ] Página de prueba 18716 quedó con el custom_css de la v2 (nunca se revirtió, solo el Kit
  global) — sigue en draft, sin impacto público, pero pendiente de limpiar o reutilizar
