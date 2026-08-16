# WordPress — tocaunavida.org (Fundación ROFÉ)

**Estado:** En progreso (rediseño standalone construido; pendiente pegar en Elementor)
**Última actualización:** 2026-08-15 (verificado en vivo vía API: el iframe de la página
"Panel De Datos" ya apunta a Vercel, no a Netlify — ver nota abajo)
**Procesos relacionados:** [[mr-website]] (sitio distinto — Angular/Express en mujeresrofe.com) · [[panel-datos-etl]] (el panel se embebe aquí) · [[mujeres-rofe-inventario-contenido]] (insumo para rediseño standalone)

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
3. **Página "Panel De Datos"** (id 18705, `/panel-de-datos/`, publicada) con iframe del panel.
   **Estado 2026-08-15 (verificado en vivo vía `GET /wp-json/wp/v2/pages/18705?context=edit`,
   `_elementor_data`):** el `<iframe src="...">` ya apunta a `https://panel-de-datos.vercel.app`
   — no depende de Netlify (dado de baja 2026-08-11), no hace falta tocarlo. Quedó actualizado
   en algún momento entre el 2026-07-16 (nota de abajo, histórica) y hoy, sin que este doc se
   actualizara — verificar en vivo, no confiar solo en el doc (ver [[feedback_verificar_n8n_en_vivo]]
   para la lección general, aunque ahí es sobre n8n, aplica igual acá).
4. **Migración del panel (histórico, 2026-07-16):** repo nuevo `comunicaciones-ai/Panel-De-Datos`
   (antes soportejunior-codeJR/PowerBi que dejó de desplegar) → URL Netlify de ese momento
   `venerable-truffle-331f3c.netlify.app` (ver [[panel-datos-etl]]). Superada por el punto 3.
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

**Rediseño final del hero (mismo día) — se descarta la imagen de fondo suelta:** la dueña reportó que
"la imagen se ve mal" y que el texto tapaba la cara de las mujeres. Causa raíz: el enfoque de
`.mr-hero-bgimg` (imagen de fondo posicionada aparte del flujo, cubriendo el 56% derecho) no garantizaba
que el texto NUNCA invadiera esa zona — en viewports intermedios el párrafo sí se montaba sobre la foto.
Se volvió a un layout de **grid de 2 columnas real** (`.mr-hero-grid` > `.mr-hero-text` + `.mr-ph
.mr-hero-photo`), donde texto e imagen son columnas separadas — estructuralmente imposible que se
superpongan. La foto es un recuadro (`border-radius:var(--r-lg)`, `aspect-ratio:4/5`) con
`transform:scale(1.3) translateY(9%)` en la `<img>` para recortar el letrero rojo de fondo y centrar el
encuadre en las caras de las mujeres, más un `::before` con blend leve rojo→transparente en el borde
izquierdo para integrarla con el fondo del hero. Se eliminó `#mr-herobg` y el JS de `probe` que ya no
aplican; `build_wordpress_embed.py` volvió a mapear `src="img/inicio.png"` en vez del patrón
`url()`/`probe.src`. Verificado en desktop y mobile (390px) — caras completamente libres de texto en
ambos.

## Exploración de 4 direcciones de hero + elegida "full-bleed duotono" (mismo día)

Ante el feedback repetido sobre el hero, se le ofreció a la dueña **probar al azar**: se armó un
artifact aparte (`hero_options.html`, fuera del repo, en el scratchpad de la sesión) con 4 mockups
reales — misma paleta ROFÉ y misma foto, solo cambiando la composición:
- **A. Diagonal** — corte diagonal con filo amarillo entre texto y foto.
- **B. Polaroid** — foto como instantánea inclinada con cinta y firma a mano.
- **C. Full-bleed duotono** — foto de fondo completa, tratada en blanco/negro + multiply rojo (se lee
  como pieza de marca, no como foto suelta; contraste de texto garantizado por diseño).
- **D. Medallón con bombillos** — foto circular con los 4 bombillos R·O·F·É orbitando.

**Elegida: C (full-bleed duotono)**, además pidiendo que las fotos vayan cambiando. Implementado en
`index.html`:
- `.mr-hero-photos` con 3 `<img class="mr-hero-slide">` apiladas (mismas 3 URLs que dio la dueña:
  `2026/04/fondo-mr-1.png`, `2026/01/64.png`, `2024/06/Meta-imagen.jpg`), crossfade cada 5.5s.
- Tratamiento duotono: `filter:grayscale(1) contrast(1.12)` en cada slide + `.mr-hero-tint` (gradiente
  rojo/coral con `mix-blend-mode:multiply`) + `.mr-hero-veil` (gradiente oscuro solo a la izquierda,
  donde va el texto) — contraste garantizado sin depender del contenido de cada foto.
- La función de crossfade se generalizó (`startCrossfade(box, ms)`, selector `img[class*="-slide"]`)
  para servir tanto al hero como a la sección Galería (mismo mecanismo, distinto intervalo).
- Se eliminó por completo el enfoque anterior de grid de 2 columnas (`.mr-hero-grid`/`.mr-hero-text`/
  `.mr-hero-photo`, `img/inicio.png`) — ya no aplica con fondo completo. `build_wordpress_embed.py` se
  limpió del mapeo de `img/inicio.png` que quedó obsoleto (las 3 fotos nuevas ya son URLs absolutas del
  sitio, no necesitan reescritura).

## Auditoría del sitio en vivo + sección Galería nueva (mismo día)

Se le dio permiso explícito de **solo lectura** sobre `https://tocaunavida.org/mujeres-rofe/` (el sitio
real, no el rediseño) vía `WebFetch` para comparar estructura. Hallazgos:
- El sitio en vivo YA muestra un aviso de convocatoria con fechas ("Convocatoria abierta del 26 de enero
  al 20 de febrero") — respalda la nota de los $120.000 que se agregó al rediseño.
- Nombres de cursos difieren un poco del rediseño (live: "Habilidades blandas" + "Modelo CANVAS" +
  "Identidad de marca"; rediseño: "Habilidades clave" + "Modelo de negocio" + "Validación y acción") —
  no se tocó, queda como diferencia conocida. **Resuelto en la auditoría de documentación
  2026-08-04:** el enlace `[[wordpress-fundacion-rofe]]` que quedó aquí apuntaba a una nota que
  nunca se creó — este mismo documento (`wordpress-tocaunavida.md`) es la nota viva del sitio, no
  hubo un rename pendiente en otra parte.
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

## Rediseño del hero v3 — "portal orgánico" (2026-07-24)

El hero "full-bleed duotono" (v2, arriba) NO gustó tras mostrarlo — feedback llegó como un **prompt de
generación de imagen con IA** (mancha de tinta orgánica multicolor tipo "portal" enmarcando el grupo
nítido, mosaico caleidoscópico cambiante de fondo con escenas diversas tipo coding/pitching/networking,
aura pearlescente). Se le aclaró explícitamente a la dueña que esta sesión de código NO tiene
generación de imágenes — se ofreció interpretar el concepto con SVG/CSS usando fotos REALES del sitio
en vez de escenas inventadas que no existen (coding/pitching no son fotos que la fundación tenga);
aprobó esa interpretación.

**Implementación (`index.html`):**
- **Mancha orgánica ("portal"):** `clipPath` SVG (`clipPathUnits="objectBoundingBox"`) con un path
  generado por script (Catmull-Rom→Bézier, 11 puntos, radio 0.40 ± jitter 0.075) — 3 variantes con la
  misma estructura de comandos para poder interpolarse. Un `<animate attributeName="d">` con
  `calcMode="spline"` hace que la mancha respire/mute lentamente entre las 3 formas cada 17s.
  `begin="indefinite"`: no arranca hasta que JS llama `beginElement()`, y solo lo hace si
  `!prefers-reduced-motion` — con reduced-motion la mancha queda estática en la forma inicial (fallback
  aceptable).
- **Foto nítida dentro de la mancha:** una sola foto fija (`fondo-mr-1.png`, la primera que dio la
  dueña), `clip-path:url(#mrBlobClip)` + una cadena de `drop-shadow()` (blanco, dorado, rojo) que seguía
  EXACTAMENTE el contorno orgánico de la silueta — mucho más simple y fiable que intentar dibujar un
  `<path>` con `stroke` aparte para el borde brillante.
- **Aura pearlescente:** un `<div>` detrás con el MISMO `clip-path`, relleno de 3 `radial-gradient` (oro
  arriba-izq, morado arriba-der, rojo abajo) + gradiente lineal base, `blur(24px)`, pulso de opacidad/
  escala cada 9s — da el efecto "atrapa luz desde todos los ángulos" sin necesitar WebGL.
- **Mosaico cinético de fondo:** 8 `<div>` (`.mr-mosaic-tile`) con `background-image` de **fotos reales
  del sitio** (no inventadas) — las 2 fotos de grupo que sobraron (`64.png`, `Meta-imagen.jpg`), las 3
  fotos de la galería de encuentros, y las 3 miniaturas de YouTube de los testimonios — cada una con
  `hue-rotate` distinto (variedad de tono rojo→morado→dorado vía variable CSS `--hue`), `mix-blend-mode:
  soft-light`, y una deriva lenta (`scale`+`translate`) con duración/delay individuales para que no se
  muevan sincronizadas. Un `::after` con gradiente rojo→transparente sobre el mosaico mantiene el lado
  del texto siempre legible.
- Posición: mancha ocupa desde 31% hasta fuera del borde derecho (`right:-10%`) — deja el 31% izquierdo
  completamente libre de foto para el texto, así es estructuralmente imposible que el texto tape caras
  (misma lección de la ronda anterior). En `<1080px` la mancha se recorta (`left:46%`); en `<760px` se
  oculta del todo (`display:none`) y el mosaico + gradiente cargan solos el fondo.

**Bug real encontrado y corregido de paso:** `.mr-hero-inner{padding:6.5rem 0 8.5rem}` (shorthand) pisaba
por completo el `padding:0 1.5rem` de `.mr-wrap` en el mismo elemento (misma especificidad, orden de
cascada) — dejaba el padding horizontal en 0 para TODO el contenido del hero, enmascarado en desktop por
el auto-margin del `max-width:1240px` centrado, pero visible en viewports angostos. Arreglado usando
`padding-top`/`padding-bottom` en vez del shorthand (mismo fix en la regla de `<760px`). Bug preexistente
desde la primera versión del hero, no introducido hoy.

**Nota de proceso:** parte de la sesión se fue diagnosticando un supuesto "texto cortado" en móvil que
resultó ser un artefacto de la herramienta de verificación (Chrome headless en modo `--screenshot`
ignora `--window-size` por debajo de ~500px de viewport, renderiza a 500px igual y recorta la imagen de
salida al tamaño pedido) — no un bug real de la página. Confirmado inyectando un badge de diagnóstico
(`getBoundingClientRect` + `scrollWidth`) directamente en una copia temporal del HTML.

**Optimización mismo día (feedback: "muy saturado" + lento):** de 9 imágenes remotas en el hero (1 foto
+ 8 tiles de mosaico) a **4** (1 foto + 3 tiles) — menos ruido visual y menos peso de red. Cambios de
rendimiento:
- **Se quitó el morph SMIL de la mancha** (`<animate attributeName="d">` interpolando 3 paths cada
  17s) — era el mayor costo: forzaba recalcular el `clip-path` + los `drop-shadow` de toda la foto en
  cada frame. La mancha ahora es un `<path>` estático (una sola forma orgánica fija). JS que la
  arrancaba (`blobAnim.beginElement()`) también se quitó.
- **Cadena de `drop-shadow` en la foto:** de 4 capas a 2 (rim blanco + sombra de piso), blur reducido.
- **Aura/glow:** blur 24px→16px, animación de vuelta a solo `opacity` (sin `scale`) — una animación de
  opacidad es trabajo de compositor (barata); animar `transform` sobre una capa con `blur()` fuerza
  repintar el blur en cada frame (cara).
- **Mosaico:** 8 tiles → 3, se quitó la variedad de `hue-rotate` por tile (daba look "multicolor
  saturado") y la animación de deriva individual por tile — ahora es un tinte uniforme
  (`grayscale(.4) contrast(1.05)`, opacidad .5) totalmente estático.

## "El bombillo ES la tarjeta" en Cuatro frentes de apoyo (mismo día)

El jefe pidió que los bombillos (Red/Oportunidades/Formación/Emprendimiento) tuvieran más
protagonismo. Se presentaron 2 opciones (agrandar el bombillo dentro de la tarjeta blanca vs. quitar
la tarjeta y que el bombillo ocupe todo el espacio) — eligió la segunda:
- `.mr-face--f` (cara frontal de la tarjeta flip) perdió `background:#fff`, el borde y el
  `box-shadow` — ya no hay caja visible, solo el bombillo flotando sobre el fondo de la sección.
- `.mr-chip--bulb` pasó de `7.6rem` a `11.5rem` (≈121px→184px) y su halo (`::before`, el resplandor
  radial detrás) de `inset:-6px` a `inset:-22px` para que el aura crezca proporcional al bombillo.
- `.mr-flip` (contenedor 3D del flip) subió de 340px a 390px de alto (300px→340px en el breakpoint
  `<760px`) para que el bombillo grande no quede apretado.
- El texto (`h3`) subió de `1.35rem` a `1.55rem` para que acompañe la nueva escala.
- La cara TRASERA (el panel de color que aparece al pasar el mouse, con la descripción) SÍ conserva
  su `box-shadow` — solo se quitó la caja de la cara frontal (donde vive el bombillo).

## Texto DENTRO del bombillo al voltear (mismo día, pedido explícito del jefe)

Antes, al pasar el mouse la tarjeta completa volteaba (`rotateY`) y mostraba un panel rectangular de
color con el título+descripción — el jefe pidió que en su lugar el propio bombillo "diera la vuelta"
(sin mostrar la letra, como si fuera su otro lado) y que el texto quedara DENTRO de la silueta del
bombillo, no en un rectángulo aparte.

**Cómo se logró (técnica: `mask-image` con la misma imagen del bombillo):**
- Se midió con PIL el ancho de píxeles opacos del PNG fila por fila (`img/bombillo-r.png`, 600×450) para
  encontrar la "panza" más ancha del bombillo: el pico de ancho (~49%) cae en el 33% de la altura, con
  ancho ≥42% entre el 13% y el 60% de la altura — esa es la franja segura para texto.
- Nueva clase `.mr-bulb-back`: mismo tamaño proporcional que el bombillo del frente, pero en vez de
  `<img>` usa `mask-image:var(--bulb-img)` (variable CSS por pilar, ej. `--bulb-img:url('img/bombillo-r.png')`)
  — el `mask-image` solo toma el CANAL ALFA del PNG (la silueta), nunca su color/letra pintada, así que
  el resultado es un bombillo sólido de color SIN la letra visible (exactamente "como si estuviera al
  revés"). El relleno de color es el mismo gradiente que antes vivía en `.mr-face--b`.
- Dentro, `.mr-bulb-back-inner` (ancho 47%, `margin-top:17%` — la franja seca medida arriba) contiene el
  `<h3>` + `<p>` originales, con fuente reducida agresivamente (`h3` .64rem, `p` .42rem) para que quepan
  sin desbordar el contorno curvo — iterado 3 veces con capturas forzando `rotateY(180deg)` vía CSS
  temporal hasta que ni el texto más largo (RED) se saliera de la silueta.
- `.mr-face--b` perdió su fondo/caja rectangular (igual que ya le había pasado a `.mr-face--f` en la
  ronda anterior) — ahora es 100% transparente, el bombillo-máscara es la única forma visible.
- `build_wordpress_embed.py` se actualizó para reescribir también el patrón `url('img/NAME')` (usado en
  `--bulb-img`), no solo `src="img/NAME"` — verificado que las 4 URLs quedaron absolutas en el
  deliverable.

## Fix: "el texto no se ve" en el bombillo volteado (mismo día)

Tras implementar el bombillo-volteado-con-texto-dentro, feedback fue que el texto no se veía. Se
descartó primero un bug de Chromium (mask + `backface-visibility:hidden` + transform 3D) reproduciendo
la transición real de hover vía JS (clase disparada con `setTimeout` en vez de forzar el estado final
con `!important`, para pasar por la MISMA animación que un hover real) — renderizó bien en Chrome, dos
veces. Eso apunta a un problema específico de **Safari**: `mask-image` con una imagen PNG a color
enmascara por **luminosidad** por defecto en WebKit (no por transparencia) — el amarillo/blanco de la
letra se vuelve la parte MÁS visible de la máscara y el cuerpo de color del bombillo (donde vive el
texto que debía verse) queda casi transparente. Es un gotcha clásico de `mask-image` cross-browser.

**Fix aplicado:** se reemplazó `mask-image:var(--bulb-img)` (CSS, ambiguo en modo de máscara) por una
máscara SVG explícita con `mask-type="alpha"` — 4 `<mask>` ocultos (uno por bombillo) con un `<image>`
adentro (`maskContentUnits="objectBoundingBox"`), referenciados desde CSS con `mask:url(#mrBulbMaskR)`
+ `-webkit-mask:url(#mrBulbMaskR)`. `mask-type="alpha"` fuerza SIEMPRE transparencia como criterio,
nunca luminosidad, en todos los navegadors que soportan CSS Masking — es el fix estándar recomendado
para este problema. No se pudo probar en Safari real en esta sesión (sin acceso), pero es la solución
documentada/consensuada para el bug descrito. `build_wordpress_embed.py` actualizado para reescribir
también `href="img/NAME"` (nuevo, usado por los `<image>` dentro de las máscaras) — verificado: las 8
referencias (4 bombillos × `href` + `xlink:href`) quedaron con URL absoluta en el deliverable.

## Fix: bombillos con ambas caras visibles en iPhone (2026-08-04)

Lina reportó que en iPhone las tarjetas de "Cuatro frentes de apoyo" (`.mr-flip`) mostraban el
bombillo de adelante y el texto de atrás mezclados/superpuestos en vez de voltear limpio. Causa: el
CSS de `backface-visibility`, `transform-style` y `perspective` no tenía prefijo `-webkit-` — Safari/iOS
sigue requiriéndolo para que el flip 3D oculte la cara trasera correctamente (gotcha clásico, distinto
del bug de `mask-image` ya resuelto el 2026-07-21 quitando la máscara). Se agregaron los prefijos en
`.mr-flip`, `.mr-flip-in`, `.mr-face` y `.mr-face--b` en `index.html`, y se regeneró
`wordpress-embed.html` con `build_wordpress_embed.py`. Sin acceso a Safari real en esta sesión — pendiente
confirmar en un iPhone antes de publicar.

También se aclaró el velo oscuro del hero (`.mr-hero-veil`) SOLO en el breakpoint móvil (`max-width:760px`):
en desktop el velo solo oscurece el lado izquierdo (donde va el texto) y se aclara hacia la derecha, pero
en móvil el texto ocupa el ancho completo y el mismo velo tapaba casi toda la foto. Se cambió a un
gradiente vertical que aclara mucho más rápido hacia abajo, y se redujo la intensidad del resplandor rojo
detrás del texto (`.mr-hero-text::before`) en ese mismo breakpoint.

## Fix: previsualizador de testimonios con tamaños distintos (2026-08-04)

Lina reportó que en la sección de testimonios las tarjetas de Linda Cogollo y Carmen Alicia Herrera se
veían con un tamaño distinto (más angosto/alto) al de Anatilde Arias Cadena. Causa: sus videos son
YouTube Shorts (verticales, 9:16) y la tarjeta tenía una clase `.mr-testi--vertical` que forzaba
`aspect-ratio:9/16` en la miniatura solo para esas dos, mientras Anatilde (video normal) quedaba en
`16/9` — un fix intencional de 2026-07-24 para evitar barras negras del reproductor de YouTube al
reproducir un Short dentro de una caja 16:9. Pedido explícito: unificar todas al tamaño de Anatilde
(el "ideal"). Se quitó la regla `aspect-ratio:9/16` y la clase `mr-testi--vertical` de las 3 tarjetas
en `index.html`, y se regeneró `wordpress-embed.html` con `build_wordpress_embed.py`. Trade-off
aceptado: la miniatura (imagen `object-fit:cover`) ahora se ve uniforme, pero al reproducir los 2
Shorts dentro del iframe 16:9 puede volver a aparecer la barra negra lateral que el fix anterior evitaba.
Sin acceso a navegador en esta sesión (extensión de Chrome desconectada) — verificado solo por lectura
de HTML/CSS, pendiente confirmar visualmente. Pendiente además re-pegar `wordpress-embed.html` en
Elementor para que el cambio llegue al sitio en vivo.

## Pendiente

- [ ] **Confirmar en iPhone real** el fix de prefijos `-webkit-` del flip de bombillos (2026-08-04) y el
  aclarado del velo del hero en móvil — ambos sin poder probarse en esta sesión.
- [ ] **Confirmar visualmente** el fix de tamaño uniforme de testimonios (2026-08-04, sin navegador
  disponible en esa sesión) y revisar si los 2 Shorts muestran barra negra al reproducirse en la caja 16:9.
- [ ] Conseguir feedback de la dueña sobre el hero v3 optimizado (portal orgánico, 4 imágenes, sin
  animaciones costosas) — recién ajustado, sin aprobar todavía.
- [ ] Confirmar con el jefe si el tamaño/protagonismo de los bombillos y el nuevo efecto de "voltear
  dentro del bombillo" en "Cuatro frentes de apoyo" son los esperados.
- [ ] **Probar en Safari real** (Mac/iPhone) el fix de `mask-type="alpha"` — no se pudo verificar en
  esta sesión (sin acceso a Safari), solo confirmado que no rompió nada en Chrome. (Nota: el flip actual
  ya no usa `mask-image`, ver arriba — este ítem puede estar obsoleto, revisar antes de invertir tiempo.)
- [x] ~~Construir el HTML/CSS/JS standalone del rediseño~~ → hecho 2026-07-21
- [ ] **Subir las 6 imágenes nuevas** a Media (`2026/07/`) y **pegar `wordpress-embed.html`** en Elementor
- [ ] Confirmar carpeta/nombres reales de las 6 imágenes si WordPress las renombra (asumido `2026/07/`)
- [ ] Decidir mecanismo de integración final a WordPress una vez aprobado (¿página nueva? ¿reemplazo
  del contenido de 17915 vía Elementor manual? ¿iframe?)
- [ ] Re-export Duplicator completo (con plugins) si se vuelve a necesitar réplica local fiel
- [ ] Favicon del Kit aún apunta a `http://143.110.201.40/...` (IP vieja) — corregir a dominio
- [ ] Página de prueba 18716 quedó con el custom_css de la v2 (nunca se revirtió, solo el Kit
  global) — sigue en draft, sin impacto público, pero pendiente de limpiar o reutilizar
