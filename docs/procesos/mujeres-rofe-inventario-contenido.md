# Inventario de contenido — /mujeres-rofe/ (página real, id 17915)

**Estado:** Insumo para rediseño standalone (HTML/CSS/JS) — NO tocar WordPress hasta nueva orden
**Última actualización:** 2026-07-16
**Fuente:** `_elementor_data` de la página publicada vía API REST (ver [[wordpress-tocaunavida]])
**Objetivo:** que este documento sea suficiente para reconstruir la página desde cero, con mejor
calidad visual, sin depender de WordPress/Elementor. Referencia de estilo aprobada por el equipo:
https://front-end-visuals-reborn.lovable.app (paleta y componentes en [[wordpress-tocaunavida]] →
sección "Trabajo hecho").

---

## 1. Estructura completa, en orden de aparición

### Hero
- **H1:** "Mujeres ROFÉ"
- **Subtítulo:** "una comunidad para crecer, aprender y emprender."
- **Botón 1:** "Objetivo del Proyecto" → `#convocatoria` (ancla interna)
- **Botón 2:** "Preguntas frecuentes" → `#preguntas` (ancla interna)
- **Texto pequeño:** "Convocatoria abierta del 26 de enero al 20 de febrero." (fecha dinámica — verificar vigencia antes de reconstruir)

### Cuatro pilares ("Cuatro frentes de apoyo para ti Mujer")
Tarjetas flip-box (efecto voltear al hover), 4 columnas:

| # | Imagen | Frente | Dorso — título | Dorso — descripción |
|---|---|---|---|---|
| 1 | `2025/08/3.png` | Red | RED | Conexión con otras mujeres directorio y grupo de Facebook, apoyo emocional, derechos de la mujer, entre otros beneficios. |
| 2 | `2025/08/4.png` | Oportunidades | OPORTUNIDAD | Oportunidades de trabajo, becas, subsidios y cursos. |
| 3 | `2025/08/Formacion.png` | Formación | FORMACIÓN | Cursos, talleres y charlas enfocadas al fortalecimiento de las mujeres en el entorno del emprendimiento. |
| 4 | `2025/08/6.png` | Emprendimiento | EMPRENDIMIENTO | Canal para aplicar a asesorías y acceso a microcrédito para comenzar o fortalecer su emprendimiento. |

### Catálogo de cursos ("Te presentamos nuestros cursos...")
5 columnas, cada una: imagen + acordeón (título + descripción en texto). **Nota:** esta sección
está **duplicada íntegramente dos veces seguidas** en la página (probablemente versión desktop +
versión mobile con visibilidad condicional por CSS de Elementor — verificar si el rediseño necesita
ambas o si es contenido redundante a limpiar).

| Imagen | Curso | Contenido |
|---|---|---|
| `2026/01/curso-blandas.png` | Habilidades blandas | Liderazgo. Trabajo en equipo. Comunicación asertiva. Resolución de conflictos. |
| `2026/01/curso-emprendimiento.png` | Emprendimiento | Ideación. Modelo CANVAS. Validación. Identidad de marca. |
| `2026/01/curso-finanzas.png` | Finanzas | Deudas. Ingresos. Ahorros. Gastos. Control de flujo de caja. |
| `2026/01/curso-online.png` | Ventas online | Persuasión. Perfil del cliente. Anuncios. Planeación. Remarketing. |
| `2026/01/Curso-Empoderamiento.png` | Curso de Empoderamiento en ventas | Conoce mejor a tus clientes. Vende con confianza y claridad. Ofrece tu producto con seguridad. Aprende a cerrar más ventas. Posiciona tu marca y fideliza clientes. |

### Servicios de apoyo ("Servicios de apoyo a mujeres emprendedoras en Colombia durante el programa")
Flip-box, **también duplicada dos veces** (mismo patrón que arriba):

| Imagen | Título | Descripción |
|---|---|---|
| `2026/01/apoyo-emocional.png` | Apoyo emocional | En los momentos difíciles, pedir apoyo es el primer paso. Estamos para escucharte, acogerte e impulsarte, porque todo es posible. Nuestro equipo puede brindarte el mejor apoyo emocional. |
| `2026/01/Bienestar.png` | Bienestar | Estas charlas buscan fortalecer la conexión mente-cuerpo y mejorar la gestión de las emociones en lo cotidiano y en situaciones complejas. Te invitamos a participar dos veces al mes en estos espacios. |
| `2026/01/asesorias.png` | Asesorías personalizadas | Emprender requiere energía y valentía, pero también una mirada experta que ayude a analizar tu negocio. Aquí podrás compartir tu idea o empresa y recibir la guía de un mentor para validar y ajustar tu modelo de negocio. |

### Requisitos para inscribirte
Lista de íconos (icon-list):
1. Ser mujer cabeza de hogar, con ingresos familiares inferiores a dos salarios mínimos mensuales.
2. Tener acceso a internet y a dispositivo móvil.
3. Tener whatsapp y perfil de facebook (recomendado).
4. Tener correo electrónico personal.
5. Tener disposición para participar activamente en los espacios y estudiar virtualmente.
6. Querer ser parte de una comunidad de mujeres que se apoyan y buscan superarse.
7. Debes llenar tu misma el formulario de inscripción.

Además: un **carrusel de imágenes** (`image-carousel`, contenido no extraíble por API — revisar
en vivo qué imágenes trae) y una imagen de fondo `2023/01/mujeres_rofe-removebg-preview.png`.

### "¡Puedes hacer parte de esta comunidad!" (pasos de registro)
**Duplicada dos veces** (mismo contenido, layout gemelo):
- Imagen: `2023/02/MOCKUP-DISPOSITIVOS.png`
- Imagen: `2025/01/Charlas-JC-1-e1736869977557.png` (primera instancia) / `2025/01/Charlas-JC-2.png` (segunda instancia)
- **Paso 1** (ícono `fa-user-plus`): "Regístrate en mujeresrofe.com" → botón "REGÍSTRATE" → `https://mujeresrofe.com/`
- **Paso 2** (ícono `fa-lightbulb`): "Ingresa desde la web" → botón "INICIAR SESIÓN" → `https://mujeresrofe.com/`
- **Paso 3** (ícono `fa-check-circle`): "Ingresa, aprende y disfruta los beneficios. Ingresa a la WEB con el usuario y contraseña que previamente habremos enviado a tu correo electrónico."

> Nota: ambos botones (registro e inicio de sesión) apuntan al **mismo sitio externo**
> `mujeresrofe.com` — el proyecto Angular/Express documentado en [[mr-website]]. Confirmar si eso
> sigue siendo correcto antes de reconstruir.

### Preguntas frecuentes
Acordeón, 6 preguntas:
1. **¿Qué incluye el programa de Mujeres ROFÉ?** — Este programa incluye capacitación gratuita para mujeres emprendedoras cabeza de hogar. Inicialmente 5 cursos principales, talleres de formación y charlas de bienestar o testimonios.
2. **¿Qué NO incluye el programa de Mujeres ROFÉ?** — NO otorga ayuda monetaria, NO da auxilio de conectividad NI dispositivos para ingresar a la plataforma.
3. **¿Se darán certificados?** — SI otorgamos certificados de asistencia a quienes completen los 3 módulos de cada curso tomado. Esto es un beneficio para su emprendimiento o trabajo.
4. **¿El programa es 100% virtual?** — SI, todos los cursos, talleres o charlas así como los servicios ofrecidos a través de nuestra plataforma son virtuales.
5. **¿La participación es obligatoria?** — SI esperamos tu participación activa en la programación mensual, si no puedes conectarte tienes disponible la grabación al día siguiente.
6. **¿La membresía por pertenecer a la comunidad de Mujeres ROFÉ tiene costo?** — Participar en Mujeres ROFÉ no tiene ningún costo. Accede a todos los beneficios del programa sin pagar inscripción ni mensualidad.

### Testimonios
"Testimonios Mujeres ROFÉ" — 3 videos de YouTube embebidos, con nombre debajo de cada uno:

| Persona | Video |
|---|---|
| Tania Banquez | https://www.youtube.com/embed/_wflSyaAmOo |
| Luz Mery Yepes | https://www.youtube.com/embed/3p615RZmo8E |
| Belsys Padilla | https://www.youtube.com/embed/MfD5iUxToyc |

Botón: "VER MÁS DE NOSOTROS" → `https://www.youtube.com/@fundacionrofe-tocaunavida7147/videos`

### Términos y condiciones
- Título: "Mujeres ROFÉ - Términos y Condiciones (pdf)"
- Botón "DESCARGAR" → `https://tocaunavida.org/wp-content/uploads/2025/01/Autorizacion-terminos-y-condiciones-2025.pdf`

Hay también un widget `html` sin texto extraíble (código embebido custom, ej. tracking/script — revisar en vivo).

---

## 2. Todas las imágenes usadas (URLs completas)

```
https://tocaunavida.org/wp-content/uploads/2023/01/mujeres_rofe-removebg-preview.png   (fondo, secciones "puedes hacer parte")
https://tocaunavida.org/wp-content/uploads/2023/02/MOCKUP-DISPOSITIVOS.png             (mockup dispositivos, x2)
https://tocaunavida.org/wp-content/uploads/2025/01/Charlas-JC-1-e1736869977557.png
https://tocaunavida.org/wp-content/uploads/2025/01/Charlas-JC-2.png
https://tocaunavida.org/wp-content/uploads/2025/08/3.png            (flip-box "Red")
https://tocaunavida.org/wp-content/uploads/2025/08/4.png            (flip-box "Oportunidades")
https://tocaunavida.org/wp-content/uploads/2025/08/6.png            (flip-box "Emprendimiento")
https://tocaunavida.org/wp-content/uploads/2025/08/Formacion.png    (flip-box "Formación")
https://tocaunavida.org/wp-content/uploads/2026/01/Bienestar.png
https://tocaunavida.org/wp-content/uploads/2026/01/Curso-Empoderamiento.png
https://tocaunavida.org/wp-content/uploads/2026/01/apoyo-emocional.png
https://tocaunavida.org/wp-content/uploads/2026/01/asesorias.png
https://tocaunavida.org/wp-content/uploads/2026/01/curso-blandas.png
https://tocaunavida.org/wp-content/uploads/2026/01/curso-emprendimiento.png
https://tocaunavida.org/wp-content/uploads/2026/01/curso-finanzas.png
https://tocaunavida.org/wp-content/uploads/2026/01/curso-online.png
```

**Gap detectado:** ninguna imagen tiene texto `alt` cargado (todas vacías) — problema de
accesibilidad/SEO preexistente en el sitio actual, vale la pena corregirlo en la reconstrucción.

## 3. Todos los enlaces usados

| Destino | Uso |
|---|---|
| `#convocatoria`, `#preguntas` | anclas internas (scroll a sección) |
| `https://mujeresrofe.com/` | registro E inicio de sesión (mismo destino para ambos botones) |
| `https://www.youtube.com/@fundacionrofe-tocaunavida7147/videos` | canal de YouTube |
| `https://tocaunavida.org/wp-content/uploads/2025/01/Autorizacion-terminos-y-condiciones-2025.pdf` | descarga PDF T&C |

## 4. Videos (YouTube embed)

Ver tabla de Testimonios arriba — 3 videos, IDs: `_wflSyaAmOo`, `3p615RZmo8E`, `MfD5iUxToyc`.

## 5. Paleta y tipografía a reutilizar

Ya documentada en [[wordpress-tocaunavida]] — Kit global del sitio: `#EEC935` `#D1793F` `#F93548`
`#406C9E` `#6EA050` `#6FA0BC` `#FF9714` `#E9EAEC` `#0C175D`, tipografía Gilroy. Referencia de
estilo objetivo (aprobada por el equipo): paleta Lovable `#ef2b3c` `#ff5964` `#f6a129` `#1a7bb8`
`#4bb04f` `#f2c40b` `#1f2937`, tarjetas blancas `rounded-2xl` con sombra, botones pill.

## 6. Observaciones para la reconstrucción

- **Contenido duplicado 2x** en tres secciones (catálogo de cursos, servicios de apoyo, pasos de
  registro) — muy probablemente una versión desktop y otra mobile hechas a mano en vez de responsive
  real. En el HTML nuevo esto se resuelve con CSS responsive normal, **no duplicar el markup**.
  Bombillos exactamente iguales entre ambas versiones — con hooks CSS de Elementor generando la caja
  que hacía que "los bombillos" se vieran sobrepuestos a un cuadrado (el problema reportado).
- Sin `alt` en ninguna imagen — corregir en la reconstrucción.
- Botones de "Regístrate" e "Iniciar sesión" van al mismo URL externo — confirmar con el equipo si
  es intencional antes de replicarlo.
- Fecha de convocatoria ("26 de enero al 20 de febrero") está hardcodeada en el texto — si se
  reconstruye standalone, considerar hacerla fácil de actualizar (variable/config al inicio del JS).
- Carrusel de imágenes en "Requisitos" no se pudo leer por API (contenido dinámico) — revisar
  manualmente en el editor de Elementor qué imágenes trae antes de reconstruir esa sección.

---

## Siguiente paso

Este documento es el insumo. **Esperar señal explícita del usuario** para construir el HTML+CSS+JS
standalone (un solo archivo autocontenido, sin dependencias externas rotas) usando este inventario
como fuente de verdad de contenido y la referencia Lovable como fuente de verdad de estilo. No se
toca WordPress en este paso.
