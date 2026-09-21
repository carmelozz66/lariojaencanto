"""Genera el sitio estático en ./dist a partir de content/ + media/ + templates/ + static/.

    python build.py

Requisitos: pip install jinja2 markdown pyyaml pillow
"""
import hashlib, json, math, re, shutil, sys, unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path

import markdown
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape
from PIL import Image

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
CONTENT = ROOT / "content"
MEDIA = ROOT / "media"

NIVEL = {"baja": 1, "media-baja": 2, "media": 3, "media-alta": 4, "alta": 5}
ZONAS_ORDEN = ["Oja", "Najerilla", "Iregua", "Leza", "Jubera", "Cidacos"]
ABREV = ("Sra.", "Sr.", "Ntra.", "Pto.", "Sta.", "Sto.", "S.", "Nª", "Avda.", "kms.", "km.", "aprox.", "etc.")


def split_front_matter(text):
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.S)
    if not m:
        return {}, text
    return yaml.safe_load(m.group(1)) or {}, m.group(2).strip()


def paragraphs(text):
    """Si el texto viene en un solo bloque, lo trocea en párrafos legibles (~350 caracteres)."""
    if "\n\n" in text.strip():
        return text
    frases = re.split(r"(?<=[.!?…])\s+(?=[A-ZÁÉÍÓÚÑ¿¡«])", text.strip())
    unidas = []
    for f in frases:
        if unidas and unidas[-1].endswith(ABREV):
            unidas[-1] += " " + f
        else:
            unidas.append(f)
    out, cur = [], ""
    for f in unidas:
        cur = f if not cur else cur + " " + f
        if len(cur) >= 330:
            out.append(cur)
            cur = ""
    if cur:
        if out and len(cur) < 120:
            out[-1] += " " + cur
        else:
            out.append(cur)
    return "\n\n".join(out)


def md(text):
    return markdown.markdown(text, extensions=["extra", "smarty"])


def save_image(src, dst, max_w, quality=82):
    dst.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as im:
        im = im.convert("RGB")
        if im.width > max_w:
            im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
        im.save(dst, "JPEG", quality=quality, optimize=True, progressive=True)
        return im.width, im.height


def tiempo_orientativo(km, desnivel, horas=None):
    if horas is None:
        horas = km / 4 + desnivel / 500
    horas = max(0.5, round(horas * 2) / 2)
    h = int(horas)
    txt = f"{h} h" if horas == h else (f"{h} h 30 min" if h else "30 min")
    return txt


TRACKS = ROOT / "tracks"


def track_name(titulo):
    """'Paraíso Urbión' -> 'paraisourbion' (minúsculas, sin acentos, sin espacios ni signos)."""
    s = unicodedata.normalize("NFKD", str(titulo)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", s)


def find_track(titulo):
    """Busca tracks/<nombre>.gpx sin distinguir mayúsculas. Devuelve Path o None."""
    if not TRACKS.exists():
        return None
    want = track_name(titulo) + ".gpx"
    for f in TRACKS.iterdir():
        if f.is_file() and f.name.lower() == want:
            return f
    return None


def _hav(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371.0088 * math.asin(math.sqrt(h))


def parse_gpx(path):
    """Lee un GPX (track o ruta). Devuelve datos resumidos o None si no es válido."""
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return None
    pts, wpts = [], []
    for el in root.iter():
        tag = el.tag.split("}")[-1]
        if tag == "wpt":
            try:
                w = {"lat": round(float(el.get("lat")), 6), "lng": round(float(el.get("lon")), 6), "nombre": "", "ele": None}
            except (TypeError, ValueError):
                continue
            for c in el:
                t = c.tag.split("}")[-1]
                if t == "name":
                    w["nombre"] = (c.text or "").strip()
                elif t == "ele":
                    try:
                        w["ele"] = round(float(c.text))
                    except (TypeError, ValueError):
                        pass
            wpts.append(w)
        elif tag in ("trkpt", "rtept"):
            try:
                lat, lon = float(el.get("lat")), float(el.get("lon"))
            except (TypeError, ValueError):
                continue
            ele = None
            for c in el:
                if c.tag.split("}")[-1] == "ele":
                    try:
                        ele = float(c.text)
                    except (TypeError, ValueError):
                        pass
            pts.append((lat, lon, ele))
    if len(pts) < 2:
        return None
    dist, acum, up, down, ref = 0.0, [0.0], 0.0, 0.0, None
    for i, p in enumerate(pts):
        if i:
            dist += _hav(pts[i - 1], p)
        acum.append(dist)
        if p[2] is not None:
            if ref is None:
                ref = p[2]
            elif abs(p[2] - ref) >= 3:
                up, down = (up + p[2] - ref, down) if p[2] > ref else (up, down + ref - p[2])
                ref = p[2]
    acum = acum[1:]
    eles = [p[2] for p in pts if p[2] is not None]
    step = max(1, len(pts) // 350)
    idx = list(range(0, len(pts), step)) + ([len(pts) - 1] if (len(pts) - 1) % step else [])
    out = {
        "inicio": (round(pts[0][0], 6), round(pts[0][1], 6)),
        "fin": (round(pts[-1][0], 6), round(pts[-1][1], 6)),
        "puntos": [[round(pts[i][0], 5), round(pts[i][1], 5)] for i in idx],
        "km": dist, "km_txt": f"{dist:.1f}".replace(".", ",") + " km",
        "sube": round(up), "baja": round(down),
        "alt_min": round(min(eles)) if eles else None, "alt_max": round(max(eles)) if eles else None,
        "perfil": None,
        "waypoints": wpts,
    }
    if len(eles) > 2 and dist > 0:
        W, H, pad = 300, 90, 6
        lo, hi = min(eles), max(eles)
        span = (hi - lo) or 1
        xy = [(acum[i] / dist * W, H - pad - (pts[i][2] - lo) / span * (H - 2 * pad)) for i in idx if pts[i][2] is not None]
        line = " ".join(f"{x:.1f},{y:.1f}" for x, y in xy)
        out["perfil"] = {"line": line, "area": f"0,{H} {line} {W},{H}", "w": W, "h": H}
    return out


def load_rutas():
    rutas = []
    for p in sorted((CONTENT / "rutas").glob("*.md")):
        meta, body = split_front_matter(p.read_text(encoding="utf-8"))
        slug = p.stem
        meta["slug"] = slug
        meta["nivel"] = NIVEL.get(str(meta.get("dificultad", "")).strip().lower(), 3)
        meta["km"] = float(meta.get("distancia_km", 0) or 0)
        meta["desnivel"] = int(meta.get("desnivel_m", 0) or 0)
        gpx = find_track(meta["titulo"])
        meta["track"] = parse_gpx(gpx) if gpx else None
        meta["track_src"] = gpx
        if meta["track"]:  # con GPX, la distancia sale siempre del track: así coincide en todas partes
            meta["km"] = float(f"{meta['track']['km']:.1f}")
        km_txt = f"{meta['km']:g}".replace(".", ",")
        meta["km_txt"] = km_txt + " km"
        # `tiempo_h` (opcional, en horas) fija el tiempo a mano; si no, se calcula con la fórmula
        th = meta.get("tiempo_h")
        meta["tiempo"] = tiempo_orientativo(0, 0, float(th)) if th else tiempo_orientativo(meta["km"], meta["desnivel"])
        meta["html"] = md(paragraphs(body))
        meta["resumen_html"] = md(paragraphs(meta.get("resumen", "")))
        meta["ida_vuelta"] = bool(meta.get("ida_vuelta", False))
        media = MEDIA / "rutas" / slug
        meta["fotos"] = []
        for i in (1, 2):
            f = media / f"foto-{i}.jpg"
            if f.exists():
                meta["fotos"].append({"n": i, "pie": meta.get(f"foto_{i}_pie") or meta["titulo"]})
        meta["tiene_mapa"] = (media / "mapa.jpg").exists()
        meta["track_file"] = track_name(meta["titulo"]) + ".gpx"
        if meta["track"]:  # el punto de salida real del track sustituye a la coordenada aproximada
            meta["lat"], meta["lng"] = meta["track"]["inicio"]
        meta.setdefault("orden", 999)
        rutas.append(meta)
    rutas.sort(key=lambda r: (r["orden"], r["titulo"]))
    return rutas


def build():
    site = yaml.safe_load((CONTENT / "site.yml").read_text(encoding="utf-8"))
    rutas = load_rutas()
    zonas = [z for z in ZONAS_ORDEN if any(r["zona"] == z for r in rutas)]
    zonas += sorted({r["zona"] for r in rutas} - set(zonas))

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    shutil.copytree(ROOT / "static", DIST / "assets")

    # imágenes
    for r in rutas:
        src = MEDIA / "rutas" / r["slug"]
        for i in (1, 2):
            f = src / f"foto-{i}.jpg"
            if f.exists():
                w, h = save_image(f, DIST / "img" / r["slug"] / f"foto-{i}.jpg", 1400)
                save_image(f, DIST / "img" / r["slug"] / f"foto-{i}-m.jpg", 640, 78)
                r["fotos"][i - 1].update(w=w, h=h)
        if r["track"]:
            (DIST / "tracks").mkdir(exist_ok=True)
            shutil.copy(r["track_src"], DIST / "tracks" / r["track_file"])
            # Copia en .js: permite descargar el GPX aunque la web se abra como archivo local (file://)
            texto = r["track_src"].read_text(encoding="utf-8", errors="replace")
            (DIST / "tracks" / (r["track_file"] + ".js")).write_text(
                "window.__gpxLoaded&&window.__gpxLoaded(" + json.dumps(texto, ensure_ascii=False).replace("</", "<\\/") + ");", encoding="utf-8")
        if r["tiene_mapa"]:
            save_image(src / "mapa.jpg", DIST / "img" / r["slug"] / "mapa.jpg", 1600, 85)
    if (MEDIA / "site").exists():
        shutil.copytree(MEDIA / "site", DIST / "img" / "site")

    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=select_autoescape(["html"]))
    env.filters["md"] = md

    # versión de los recursos: cambia al modificarse el CSS/JS, así el navegador nunca usa copias antiguas
    ver = hashlib.md5(b"".join(p.read_bytes() for p in sorted((ROOT / "static").rglob("*")) if p.is_file() and "fonts" not in p.parts)).hexdigest()[:8]

    def render(name, out, base="", **ctx):
        html = env.get_template(name).render(site=site, rutas=rutas, zonas=zonas, base=base, ver=ver, **ctx)
        target = DIST / out
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html, encoding="utf-8")

    datos = [
        {k: r[k] for k in ("slug", "titulo", "zona", "localidad", "lat", "lng", "km", "desnivel", "nivel", "dificultad")}
        | {"foto": f"img/{r['slug']}/foto-1-m.jpg" if r["fotos"] else ""}
        for r in rutas
    ]
    (DIST / "assets" / "rutas.json").write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")

    destacadas = [r for r in rutas if r["slug"] in ("rajao", "hiedra", "paraiso", "prudencio", "acebal", "penalba")] or rutas[:6]
    render("home.html", "index.html", destacadas=destacadas, activo="inicio", datos=datos)
    render("rutas.html", "rutas.html", activo="rutas", datos=datos)
    for i, r in enumerate(rutas):
        render("ruta.html", f"rutas/{r['slug']}.html", base="../", r=r, activo="rutas",
               prev=rutas[i - 1] if i > 0 else None, next=rutas[i + 1] if i < len(rutas) - 1 else None,
               relacionadas=[x for x in rutas if x["zona"] == r["zona"] and x["slug"] != r["slug"]][:3])

    mapa = [
        {"slug": r["slug"], "titulo": r["titulo"], "km": r["km"], "dificultad": r["dificultad"],
         "lat": r["lat"], "lng": r["lng"], "puntos": r["track"]["puntos"] if r["track"] else []}
        for r in rutas
    ]
    render("mapa-general.html", "mapa-general.html", mapa=mapa)
    for r in rutas:
        if r["track"]:
            render("mapa.html", f"rutas/{r['slug']}-mapa.html", base="../", r=r)

    for p in sorted((CONTENT / "paginas").glob("*.md")):
        meta, body = split_front_matter(p.read_text(encoding="utf-8"))
        render("pagina.html", f"{p.stem}.html", pag=meta, html=md(body), activo=p.stem)
    render("404.html", "404.html", activo="")

    # robots.txt: bloquea buscadores mientras indexar sea false
    if site.get("indexar"):
        robots = "User-agent: *\nAllow: /\n" + (f"Sitemap: {site['url']}/sitemap.xml\n" if site.get("url") else "")
    else:
        robots = "User-agent: *\nDisallow: /\n"
    (DIST / "robots.txt").write_text(robots, encoding="utf-8")

    # sitemap solo si la web es indexable y hay dirección
    if site.get("url") and site.get("indexar"):
        urls = ["index.html", "rutas.html"] + [f"rutas/{r['slug']}.html" for r in rutas] + \
               [f"{p.stem}.html" for p in (CONTENT / "paginas").glob("*.md")]
        xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + \
              "\n".join(f"  <url><loc>{site['url']}/{u}</loc></url>" for u in urls) + "\n</urlset>\n"
        (DIST / "sitemap.xml").write_text(xml, encoding="utf-8")
    print(f"OK · {len(rutas)} rutas · sitio generado en {DIST}")


if __name__ == "__main__":
    sys.exit(build())

