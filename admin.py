"""Editor local de la web: crear / editar / borrar rutas y textos sin tocar código.

    python admin.py        (o doble clic en EDITOR.bat)

Abre http://127.0.0.1:8080 . Solo escucha en tu propio ordenador.
Cada vez que guardas, la web se regenera en ./dist
"""
import html, io, re, shutil, threading, unicodedata, webbrowser
from email import message_from_bytes
from email.policy import HTTP
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse, quote

import yaml
from PIL import Image

import build

ROOT = Path(__file__).resolve().parent
RUTAS = ROOT / "content" / "rutas"
PAGINAS = ROOT / "content" / "paginas"
MEDIA = ROOT / "media" / "rutas"
PORT = 8080
DIFICULTADES = ["baja", "media-baja", "media", "media-alta", "alta"]
CAMPOS_TEXTO = ["titulo", "zona", "localidad", "punto_partida", "terreno", "epoca", "resumen", "foto_1_pie", "foto_2_pie"]

E = html.escape


def slugify(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "ruta"


def yq(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").strip() + '"'


def leer_ruta(slug):
    meta, body = build.split_front_matter((RUTAS / f"{slug}.md").read_text(encoding="utf-8"))
    meta["slug"], meta["cuerpo"] = slug, body
    return meta


def zonas_existentes():
    z = list(build.ZONAS_ORDEN)
    for p in RUTAS.glob("*.md"):
        zz = build.split_front_matter(p.read_text(encoding="utf-8"))[0].get("zona")
        if zz and zz not in z:
            z.append(zz)
    return z


def guardar_imagen(datos, destino):
    """Valida con Pillow, corrige rotación EXIF y limita a 2000 px."""
    from PIL import ImageOps
    with Image.open(io.BytesIO(datos)) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        if im.width > 2000:
            im = im.resize((2000, round(im.height * 2000 / im.width)), Image.LANCZOS)
        destino.parent.mkdir(parents=True, exist_ok=True)
        im.save(destino, "JPEG", quality=88, optimize=True)


CSS = """
:root{--g:#2f5d3a;--w:#8a2f3f;--l:#dcd3c0;--bg:#f5f0e6}
*{box-sizing:border-box}body{font:16px/1.5 system-ui,sans-serif;background:var(--bg);color:#23291f;margin:0}
header{background:var(--g);color:#fff;padding:14px 24px;display:flex;gap:20px;align-items:center;flex-wrap:wrap}
header a{color:#fff;text-decoration:none;font-weight:600}header h1{font-size:1.1rem;margin:0 auto 0 0}
main{max-width:920px;margin:24px auto;padding:0 16px 80px}
h2{margin-top:0}table{width:100%;border-collapse:collapse;background:#fff;border-radius:10px;overflow:hidden}
td,th{padding:10px 14px;border-bottom:1px solid var(--l);text-align:left}th{background:#eee6d3;font-size:.85rem}
.btn{display:inline-block;background:var(--g);color:#fff;border:0;padding:10px 20px;border-radius:999px;font:600 1rem system-ui;cursor:pointer;text-decoration:none}
.btn.sec{background:#fff;color:var(--g);border:2px solid var(--g)}.btn.del{background:#fff;color:var(--w);border:2px solid var(--w);padding:6px 14px}
form.card{background:#fff;border:1px solid var(--l);border-radius:12px;padding:20px 22px;display:grid;gap:14px}
.row{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px}
label{display:grid;gap:4px;font-weight:600;font-size:.9rem}label small{font-weight:400;color:#666}
input,select,textarea{font:inherit;padding:9px 11px;border:1.5px solid var(--l);border-radius:8px;width:100%}
textarea{min-height:120px}.ok{background:#e3ecdd;border:1px solid var(--g);padding:12px 16px;border-radius:10px;margin-bottom:16px}
fieldset{border:1.5px solid var(--l);border-radius:10px;padding:12px 14px}legend{font-weight:700;padding:0 6px}
#pick{height:280px;border-radius:10px;border:1px solid var(--l)}img.pv{max-height:90px;border-radius:6px;margin-top:6px}
.chk{display:flex;align-items:center;gap:8px}.chk input{width:auto}
"""


def pagina(titulo, cuerpo, extra_head=""):
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(titulo)} · Editor</title><style>{CSS}</style>{extra_head}</head><body>
<header><h1>Editor · La Rioja, Lugares con encanto</h1><a href="/">Rutas</a><a href="/paginas">Textos</a><a href="/site/index.html" target="_blank">Ver la web ↗</a></header>
<main>{cuerpo}</main></body></html>""".encode("utf-8")


def vista_lista(msg=""):
    filas = ""
    for p in sorted(RUTAS.glob("*.md"), key=lambda p: leer_ruta(p.stem).get("orden", 999)):
        m = leer_ruta(p.stem)
        filas += (f"<tr><td><b>{E(str(m.get('titulo','')))}</b></td><td>{E(str(m.get('zona','')))}</td>"
                  f"<td>{m.get('distancia_km','')} km</td><td>{E(str(m.get('dificultad','')))}</td>"
                  f"<td><a class='btn sec' href='/editar?slug={quote(p.stem)}'>Editar</a></td></tr>")
    aviso = f"<div class='ok'>{msg}</div>" if msg else ""
    return pagina("Rutas", f"{aviso}<p><a class='btn' href='/editar'>＋ Nueva ruta</a></p><table><tr><th>Ruta</th><th>Comarca</th><th>Distancia</th><th>Dificultad</th><th></th></tr>{filas}</table>")


def vista_form(slug=None):
    m = leer_ruta(slug) if slug else {"orden": 999, "lat": 42.28, "lng": -2.5, "dificultad": "media", "distancia_km": 5, "desnivel_m": 100,
                                       "terreno": "camino y senda", "epoca": "todo el año", "cuerpo": ""}
    g = lambda k, d="": E(str(m.get(k, d)))
    zonas = "".join(f"<option value='{E(z)}'>" for z in zonas_existentes())
    difs = "".join(f"<option {'selected' if d == m.get('dificultad') else ''}>{d}</option>" for d in DIFICULTADES)

    def foto(n, nombre):
        ex = MEDIA / slug / nombre if slug else None
        pv = f"<img class='pv' src='/media/{quote(slug)}/{nombre}'>" if ex and ex.exists() else ""
        return f"<label>{'Foto ' + str(n) if n else 'Mapa del recorrido'} <small>(JPG/PNG; déjalo vacío para conservar la actual)</small><input type='file' name='{nombre}' accept='image/*'>{pv}</label>"

    tf = build.find_track(m.get("titulo", "")) if slug else None
    track_estado = (f"✅ Track cargado: <b>{E(tf.name)}</b>. Si subes otro, se sustituirá." if tf
                    else "⚪ Esta ruta todavía no tiene track: en la web el botón «Descargar track» aparece inactivo.")
    borrar = (f"<form method='post' action='/borrar' onsubmit=\"return confirm('¿Borrar esta ruta definitivamente?')\"><input type='hidden' name='slug' value='{E(slug)}'>"
              "<button class='btn del'>Borrar ruta</button></form>") if slug else ""
    cuerpo = f"""<h2>{'Editar' if slug else 'Nueva'} ruta</h2>
<form class="card" method="post" action="/guardar" enctype="multipart/form-data">
<input type="hidden" name="slug" value="{E(slug or '')}">
<label>Nombre de la ruta<input name="titulo" required value="{g('titulo')}"></label>
<div class="row">
 <label>Comarca / zona<input name="zona" list="zonas" required value="{g('zona')}"><datalist id="zonas">{zonas}</datalist></label>
 <label>Localidad más cercana<input name="localidad" required value="{g('localidad')}"></label>
</div>
<label>Punto de partida<input name="punto_partida" required value="{g('punto_partida')}"></label>
<div class="row">
 <label>Distancia (km) <small>(si la ruta tiene GPX, se usa la del GPX)</small><input name="distancia_km" type="number" step="0.1" min="0" required value="{g('distancia_km')}"></label>
 <label>Desnivel (m)<input name="desnivel_m" type="number" min="0" required value="{g('desnivel_m')}"></label>
 <label>Dificultad<select name="dificultad">{difs}</select></label>
</div>
<label class="chk"><input type="checkbox" name="ida_vuelta" {'checked' if m.get('ida_vuelta') else ''}> Es de ida y vuelta</label>
<div class="row">
 <label>Tipo de terreno<input name="terreno" value="{g('terreno')}"></label>
 <label>Época recomendada<input name="epoca" value="{g('epoca')}"></label>
</div>
<label>Presentación <small>(unas líneas que animen a hacer la ruta)</small><textarea name="resumen" required>{g('resumen')}</textarea></label>
<label>Recorrido paso a paso <small>(separa los párrafos con una línea en blanco)</small><textarea name="cuerpo" style="min-height:220px" required>{E(m.get('cuerpo',''))}</textarea></label>
<fieldset><legend>Imágenes</legend><div class="row">
 <div>{foto(1, 'foto-1.jpg')}<label>Pie de la foto 1<input name="foto_1_pie" value="{g('foto_1_pie')}"></label></div>
 <div>{foto(2, 'foto-2.jpg')}<label>Pie de la foto 2<input name="foto_2_pie" value="{g('foto_2_pie')}"></label></div>
 </div></fieldset>
<fieldset><legend>Track GPS (GPX)</legend>
 <p style="margin:0 0 8px">{track_estado}</p>
 <label>Subir o sustituir el track <small>(archivo .gpx; se guardará como <b id="trkname">{E(build.track_name(m.get('titulo','')) or 'nombre-de-la-ruta')}.gpx</b>)</small><input type="file" name="track.gpx" accept=".gpx,application/gpx+xml,text/xml"></label>
 <script>document.querySelector('[name=titulo]').addEventListener('input',function(e){{document.getElementById('trkname').textContent=(e.target.value.normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]/g,'')||'nombre-de-la-ruta')+'.gpx'}})</script>
</fieldset>
<fieldset><legend>Situación en el mapa</legend>
 <p style="margin:0 0 8px">Pulsa sobre el mapa donde está la ruta (o arrastra el punto).</p>
 <div id="pick"></div>
 <div class="row" style="margin-top:8px"><label>Latitud<input name="lat" id="lat" value="{g('lat')}"></label><label>Longitud<input name="lng" id="lng" value="{g('lng')}"></label></div>
</fieldset>
<div style="display:flex;gap:12px;justify-content:space-between;flex-wrap:wrap"><button class="btn">Guardar y regenerar la web</button></div>
</form><br>{borrar}
<link rel="stylesheet" href="/site/assets/vendor/leaflet.css"><script src="/site/assets/vendor/leaflet.js"></script>
<script>
var la=document.getElementById('lat'),lo=document.getElementById('lng');
var map=L.map('pick').setView([parseFloat(la.value)||42.28,parseFloat(lo.value)||-2.5],10);
L.tileLayer('https://{{s}}.tile.opentopomap.org/{{z}}/{{x}}/{{y}}.png',{{subdomains:'abc',maxZoom:17,attribution:'© OpenStreetMap, SRTM · © OpenTopoMap (CC-BY-SA)'}}).addTo(map);
var mk=L.marker([parseFloat(la.value)||42.28,parseFloat(lo.value)||-2.5],{{draggable:true}}).addTo(map);
function set(ll){{mk.setLatLng(ll);la.value=ll.lat.toFixed(4);lo.value=ll.lng.toFixed(4)}}
map.on('click',function(e){{set(e.latlng)}});mk.on('dragend',function(){{set(mk.getLatLng())}});
</script>"""
    return pagina("Ruta", cuerpo)


def vista_paginas(msg=""):
    items = "".join(f"<tr><td><b>{E(p.stem)}</b></td><td>{E(str(build.split_front_matter(p.read_text(encoding='utf-8'))[0].get('titulo','')))}</td>"
                    f"<td><a class='btn sec' href='/pagina?n={quote(p.stem)}'>Editar</a></td></tr>" for p in sorted(PAGINAS.glob("*.md")))
    aviso = f"<div class='ok'>{msg}</div>" if msg else ""
    return pagina("Textos", f"{aviso}<h2>Textos de la web</h2><table>{items}</table>")


def vista_pagina(n):
    raw = (PAGINAS / f"{n}.md").read_text(encoding="utf-8")
    return pagina(n, f"""<h2>Editar «{E(n)}»</h2><form class="card" method="post" action="/pagina">
<input type="hidden" name="n" value="{E(n)}"><label>Contenido <small>(Markdown: ## título, **negrita**, [enlace](url)…)</small>
<textarea name="raw" style="min-height:520px;font-family:ui-monospace,monospace">{E(raw)}</textarea></label><button class="btn">Guardar y regenerar la web</button></form>""")


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, body, ctype="text/html; charset=utf-8", code=200):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def redirect(self, to):
        self.send_response(303)
        self.send_header("Location", to)
        self.end_headers()

    def do_GET(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        try:
            if u.path == "/":
                return self.send(vista_lista(q.get("ok", "")))
            if u.path == "/editar":
                return self.send(vista_form(q.get("slug")))
            if u.path == "/paginas":
                return self.send(vista_paginas(q.get("ok", "")))
            if u.path == "/pagina":
                return self.send(vista_pagina(q["n"]))
            if u.path.startswith("/media/"):
                f = (ROOT / "media" / "rutas" / u.path[7:]).resolve()
                if MEDIA in f.parents and f.is_file():
                    return self.send(f.read_bytes(), "image/jpeg")
            if u.path.startswith("/site/"):
                rel = u.path[6:] or "index.html"
                f = (build.DIST / rel).resolve()
                if build.DIST.resolve() in f.parents and f.is_file():
                    ct = {".html": "text/html; charset=utf-8", ".css": "text/css", ".js": "text/javascript", ".png": "image/png",
                          ".jpg": "image/jpeg", ".svg": "image/svg+xml", ".json": "application/json"}.get(f.suffix, "application/octet-stream")
                    return self.send(f.read_bytes(), ct)
            self.send(b"No encontrado", "text/plain", 404)
        except Exception as e:  # noqa
            self.send(pagina("Error", f"<h2>Error</h2><pre>{E(repr(e))}</pre>"), code=500)

    def form(self):
        n = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(n)
        ct = self.headers.get("Content-Type", "")
        campos, ficheros = {}, {}
        if ct.startswith("multipart/"):
            msg = message_from_bytes(b"Content-Type: " + ct.encode() + b"\r\n\r\n" + raw, policy=HTTP)
            for part in msg.iter_parts():
                name = part.get_param("name", header="content-disposition")
                if part.get_filename():
                    data = part.get_payload(decode=True)
                    if data:
                        ficheros[name] = data
                else:
                    campos[name] = part.get_payload(decode=True).decode("utf-8", "replace").replace("\r\n", "\n")
        else:
            campos = {k: v[0] for k, v in parse_qs(raw.decode("utf-8")).items()}
        return campos, ficheros

    def do_POST(self):
        try:
            c, f = self.form()
            if self.path == "/guardar":
                slug = c.get("slug") or slugify(c["titulo"])
                if not c.get("slug"):
                    base, i = slug, 2
                    while (RUTAS / f"{slug}.md").exists():
                        slug, i = f"{base}-{i}", i + 1
                orden = leer_ruta(slug).get("orden") if (RUTAS / f"{slug}.md").exists() else len(list(RUTAS.glob("*.md"))) + 1
                fm = ["---"] + [f"{k}: {yq(c.get(k, ''))}" for k in CAMPOS_TEXTO]
                fm += [f"distancia_km: {float(c['distancia_km'].replace(',', '.')):g}", f"desnivel_m: {int(float(c['desnivel_m']))}",
                       f"dificultad: {yq(c['dificultad'])}", f"ida_vuelta: {'true' if 'ida_vuelta' in c else 'false'}",
                       f"lat: {float(c['lat'].replace(',', '.'))}", f"lng: {float(c['lng'].replace(',', '.'))}", f"orden: {orden}", "---", "",
                       c["cuerpo"].strip(), ""]
                if (RUTAS / f"{slug}.md").exists():  # si cambia el nombre, el track se renombra con él
                    viejo = build.find_track(leer_ruta(slug).get("titulo", ""))
                    nuevo = build.TRACKS / (build.track_name(c["titulo"]) + ".gpx")
                    if viejo and viejo != nuevo and not nuevo.exists():
                        viejo.rename(nuevo)
                (RUTAS / f"{slug}.md").write_text("\n".join(fm), encoding="utf-8")
                for nombre, datos in f.items():
                    if nombre == "track.gpx":
                        build.TRACKS.mkdir(exist_ok=True)
                        tmp = build.TRACKS / "_tmp.gpx"
                        tmp.write_bytes(datos)
                        if not build.parse_gpx(tmp):
                            tmp.unlink()
                            raise ValueError("El archivo GPX no es válido o no contiene ningún track.")
                        destino = build.TRACKS / (build.track_name(c["titulo"]) + ".gpx")
                        antiguo = build.find_track(c["titulo"])
                        if antiguo and antiguo != destino:
                            antiguo.unlink()
                        tmp.replace(destino)
                    else:
                        guardar_imagen(datos, MEDIA / slug / nombre)
                build.build()
                return self.redirect("/?ok=" + quote(f"Ruta «{c['titulo']}» guardada y web regenerada."))
            if self.path == "/borrar":
                slug = c["slug"]
                (RUTAS / f"{slug}.md").unlink(missing_ok=True)
                shutil.rmtree(MEDIA / slug, ignore_errors=True)
                build.build()
                return self.redirect("/?ok=" + quote("Ruta borrada."))
            if self.path == "/pagina":
                (PAGINAS / f"{Path(c['n']).name}.md").write_text(c["raw"], encoding="utf-8")
                build.build()
                return self.redirect("/paginas?ok=" + quote("Texto guardado y web regenerada."))
            self.send(b"No encontrado", "text/plain", 404)
        except Exception as e:  # noqa
            self.send(pagina("Error", f"<h2>No se pudo guardar</h2><pre>{E(repr(e))}</pre><p><a href='javascript:history.back()'>← Volver</a></p>"), code=500)


if __name__ == "__main__":
    build.build()
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), H)
    print(f"Editor en http://127.0.0.1:{PORT}  (Ctrl+C para cerrar)")
    threading.Timer(0.8, lambda: webbrowser.open(f"http://127.0.0.1:{PORT}")).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
