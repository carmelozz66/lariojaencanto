# La Rioja, Lugares con encanto — nueva web

Sitio estático (HTML/CSS/JS puro). No necesita base de datos ni PHP: la carpeta `dist/` se sube a cualquier alojamiento.

## Uso diario (sin tocar código)

1. **Doble clic en `EDITOR.bat`** → se abre el editor en el navegador.
2. Pestaña **Rutas**: crear, editar o borrar rutas (formulario con fotos, mapa y punto en el mapa).
3. Pestaña **Textos**: editar Presentación y Contacto.
4. Al guardar, la web se regenera sola en la carpeta `dist/`.
5. Para publicar: subir el contenido de `dist/` al servidor.

`GENERAR.bat` solo regenera la web (útil si editas los archivos a mano).

## Publicar en internet

Doble clic en **`PUBLICAR.bat`**: regenera la web y la envía a GitHub, que la publica sola en <https://carmelozz66.github.io/lariojaencanto/> en 1–2 minutos.

- Mientras `indexar: false` en `content/site.yml`, la web pide a Google que no la indexe. Ponlo en `true` cuando esté lista.
- Cuando tengas dominio, cambia `url:` en `content/site.yml`.

## Tracks GPX

Cada ruta muestra un botón «Descargar track». Se activa solo si existe `tracks/<nombre>.gpx`, donde `<nombre>` es el título de la ruta **en minúsculas, sin acentos, sin espacios ni signos**:

| Ruta | Archivo |
|---|---|
| Paraíso Urbión | `paraisourbion.gpx` |
| Acebal de Valgañón | `acebaldevalganon.gpx` |
| Dehesa de San Román | `dehesadesanroman.gpx` |

Basta con copiar el archivo a `tracks/` y ejecutar `GENERAR.bat` (o subirlo desde la ficha de la ruta en el editor, que le pone el nombre correcto). Sin archivo, el botón aparece inactivo.
Si hay track, la ficha muestra además el recorrido sobre el mapa, la distancia y el desnivel medidos, el perfil de altitud y enlaces a Google Maps; y el punto de salida del track sustituye a la coordenada aproximada de la ruta.

Con track hay un botón **Descargar track (GPX)** y un enlace a KML para Google Earth. `GENERAR.bat` crea junto a cada GPX un `.gpx.js` que permite la descarga incluso abriendo la web como archivo local; al publicar hay que subir toda la carpeta `dist/`.

> `tracks/paraisourbion.gpx` es actualmente un archivo de prueba (no está en Urbión): sustitúyelo por el real.

## Estructura

| Carpeta | Contenido |
|---|---|
| `content/rutas/*.md` | Una ficha por ruta (datos + recorrido) |
| `content/paginas/*.md` | Textos de las páginas |
| `content/site.yml` | Nombre, lema, email y dominio de la web |
| `media/rutas/<ruta>/` | `foto-1.jpg`, `foto-2.jpg`, `mapa.jpg` |
| `templates/`, `static/` | Diseño (solo si quieres cambiar el aspecto) |
| `dist/` | **La web terminada** |
| `migrate.py` | Script de migración inicial desde la web antigua (ya ejecutado) |

## Requisitos

Python 3 con `pip install jinja2 markdown pyyaml pillow` (`EDITOR.bat` lo instala si falta).

## Pendiente de revisar

- **Coordenadas**: las posiciones de las rutas en los mapas son *aproximadas* (localidad más cercana). Ajústalas en el editor pulsando sobre el mapa.
- **Dominio**: cuando lo tengas, escríbelo en `content/site.yml` (`url:`) para generar `sitemap.xml`.
- El **tiempo orientativo** se calcula con una fórmula sencilla (4 km/h + 500 m de ascenso por hora).
