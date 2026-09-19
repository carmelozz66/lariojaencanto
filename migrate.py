"""Migra las fichas del sitio antiguo (HTML FrontPage) a content/rutas/*.md + media/.
Se ejecuta una sola vez:  python migrate.py
"""
import re, html, shutil
from pathlib import Path

OLD = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent
(OUT / "content" / "rutas").mkdir(parents=True, exist_ok=True)

# zona por ruta (tomada del índice antiguo, lugares.html)
ZONAS = {
    "acebal": "Oja", "rajao": "Najerilla", "hiedra": "Najerilla", "ormazal": "Najerilla",
    "dromedario": "Najerilla", "paraiso": "Najerilla", "laturce": "Iregua", "bajenza": "Iregua",
    "nava": "Iregua", "cebollera": "Iregua", "esteban": "Iregua", "soto": "Leza",
    "sanroman": "Leza", "prudencio": "Leza", "reinares": "Jubera", "prejano": "Cidacos",
    "penalba": "Cidacos",
}
# orden de aparición (el del índice antiguo)
ORDEN = list(ZONAS)

# Coordenadas APROXIMADAS (localidad más próxima). Revisar/ajustar desde el editor.
COORDS = {
    "acebal": (42.318, -3.052), "rajao": (42.262, -2.888), "hiedra": (42.222, -2.790),
    "ormazal": (42.175, -2.830), "dromedario": (42.245, -2.745), "paraiso": (42.185, -2.815),
    "laturce": (42.310, -2.480), "bajenza": (42.290, -2.500), "nava": (42.190, -2.640),
    "cebollera": (42.205, -2.650), "esteban": (42.335, -2.400), "soto": (42.230, -2.400),
    "sanroman": (42.190, -2.350), "prudencio": (42.320, -2.470), "reinares": (42.180, -2.220),
    "prejano": (42.170, -2.250), "penalba": (42.190, -2.170),
}


def clean(s):
    s = re.sub(r"<br\s*/?>", " ", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s).replace("\xa0", " ")
    return re.sub(r"\s+", " ", s).strip()


def q(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


for slug in ORDEN:
    raw = (OLD / f"{slug}.html").read_bytes().decode("cp1252", errors="replace")
    titulo = clean(re.search(r'<font face="Arial Black">(.*?)</font>', raw, re.S).group(1))
    tds = re.findall(r"<td[^>]*bgcolor=\"#(?:008000|CC6600|666633)\"[^>]*>(.*?)</td>", raw, re.S | re.I)
    facts, intro, recorrido = clean(tds[0]), clean(tds[1]), clean(tds[2])
    recorrido = re.sub(r"^Recorrido\s*:\s*", "", recorrido)

    def f(label):
        m = re.search(label + r"\s*:\s*(.*?)(?=\s(?:Zona|Localidad más cercana|Punto de partida|Tipo de terreno|Distancia a recorrer|Desnivel|Dificultad|Época recomendada)\s*:|$)", facts)
        return m.group(1).strip() if m else ""

    alts = re.findall(r'<img[^>]+src="(%s-(?:10|20)\.jpg)"[^>]*?(?:alt="([^"]*)")?[^>]*>' % slug, raw)
    caps = {}
    for tag in re.findall(r"<img[^>]+>", raw):
        m = re.search(r'src="(%s-(?:10|20))\.jpg"' % slug, tag)
        if m:
            a = re.search(r'alt="([^"]*)"', tag)
            caps[m.group(1)] = html.unescape(a.group(1)) if a else titulo

    media = OUT / "media" / "rutas" / slug
    media.mkdir(parents=True, exist_ok=True)
    for src, dst in ((f"{slug}-10.jpg", "foto-1.jpg"), (f"{slug}-20.jpg", "foto-2.jpg"), (f"{slug}-mapa.jpg", "mapa.jpg")):
        shutil.copy(OLD / src, media / dst)

    dist = f("Distancia a recorrer")
    km = re.search(r"[\d,.]+", dist)
    desn = re.search(r"\d+", f("Desnivel"))
    lat, lng = COORDS[slug]
    fm = f"""---
titulo: {q(titulo)}
zona: {q(ZONAS[slug])}
localidad: {q(f("Localidad más cercana"))}
punto_partida: {q(f("Punto de partida"))}
terreno: {q(f("Tipo de terreno"))}
distancia_km: {km.group(0).replace(",", ".") if km else 0}
desnivel_m: {desn.group(0) if desn else 0}
dificultad: {q(f("Dificultad"))}
epoca: {q(f("Época recomendada"))}
resumen: {q(intro)}
foto_1_pie: {q(caps.get(slug + "-10", titulo))}
foto_2_pie: {q(caps.get(slug + "-20", titulo))}
lat: {lat}
lng: {lng}
orden: {ORDEN.index(slug) + 1}
---

{recorrido}
"""
    (OUT / "content" / "rutas" / f"{slug}.md").write_text(fm, encoding="utf-8")
    print(slug, "|", titulo, "|", dist, "|", f("Desnivel"), "|", f("Dificultad"), "|", f("Localidad más cercana"))

# Imágenes de sitio
(OUT / "media" / "site").mkdir(parents=True, exist_ok=True)
shutil.copy(OLD / "portada2.jpg", OUT / "media" / "site" / "mapa-antiguo.jpg")
