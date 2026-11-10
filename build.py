#!/usr/bin/env python3
"""
WegMaster - stadspagina's bouwen
================================
Netlify draait dit script bij elke deploy (zie netlify.toml).
Het leest index.html + steden.json en maakt voor elke stad:
    rijschool-<slug>.html   (bereikbaar als /rijschool-<slug>)
Afbeeldingen die als base64 in index.html staan, worden voor de
stadspagina's als losse bestanden in /img/ gezet (sneller, cache).
index.html zelf wordt NOOIT gewijzigd.

Jij hoeft alleen index.html (en eventueel steden.json) te bewerken.
Stopt de build met een fout? Dan blijft de huidige live site gewoon
online. Lees de foutmelding in de Netlify deploy log: die zegt welke
tekst niet meer gevonden werd (zie ook README-steden.md).

Alleen Python-standaardbibliotheek; geen installatie nodig.
"""
import base64
import hashlib
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = "https://wegmaster-rijopleidingen.nl"

# Tracking die op ELKE pagina aanwezig moet zijn. Ontbreekt er één,
# dan stopt de build (de live site blijft dan zoals hij is).
TRACKING = [
    "AW-18306777925",
    "AW-18306777925/GRwtCOzhlJ8dEMWGrZlE",   # formulier (primair)
    "AW-18306777925/xI6uCKfg59QcEMWGrZlE",   # bellen / WhatsApp
    "allow_enhanced_conversions",
    "template_xcebm69",                      # EmailJS admin
    "template_zq02f9v",                      # EmailJS leerling
    "wm_gclid",
]

# Vaste teksten in index.html waar de build zijn stadsteksten aan hangt.
# Wijzig je één van deze in index.html, pas dan ook deze lijst aan
# (of vraag het Claude).
ANCHOR_OFFER = ('data-nl="Vandaag aanmelden, morgen al rijden" '
                'data-en="Sign up today, drive tomorrow">'
                'Vandaag aanmelden, morgen al rijden</h3>')
ANCHOR_PAKKETTEN = ('<h1 class="hero-national" data-nl="Auto lespakketten" '
                    'data-en="Car lesson packages">Auto lespakketten</h1>')
ANCHOR_GESLAAGDEN = '<section class="section--tight gl-sec" id="geslaagden">'
ANCHOR_BRON = "'Google advertentie' : 'Website (geen advertentie)'"


class BuildFout(Exception):
    pass


def e(s):
    """HTML-escape voor tekst en attributen."""
    return html.escape(s, quote=True)


def vervang_een(h, oud, nieuw, wat, aantal=1):
    n = h.count(oud)
    if n != aantal:
        raise BuildFout(f"'{wat}': verwacht {aantal}x in index.html, gevonden {n}x.\n"
                        f"   Gezochte tekst: {oud[:120]}")
    return h.replace(oud, nieuw)


def vervang_regex(h, patroon, nieuw, wat, flags=0):
    h2, n = re.subn(patroon, nieuw, h, count=1, flags=flags)
    if n != 1:
        raise BuildFout(f"'{wat}' niet gevonden in index.html (patroon: {patroon[:80]})")
    return h2


# ---------- afbeeldingen ----------
IMG_RE = re.compile(r"data:image/(png|jpe?g|webp|gif|avif|svg\+xml);base64,([A-Za-z0-9+/=]+)")
EXT = {"png": "png", "jpg": "jpg", "jpeg": "jpg", "webp": "webp", "gif": "gif",
       "avif": "avif", "svg+xml": "svg"}


def extraheer_afbeeldingen(h, img_dir):
    """Zet base64-afbeeldingen om naar /img/<hash>.<ext> (inhoud-hash = cache-veilig)."""
    os.makedirs(img_dir, exist_ok=True)
    cache = {}

    def sub(m):
        b64 = m.group(2)
        if b64 not in cache:
            data = base64.b64decode(b64)
            naam = hashlib.sha1(data).hexdigest()[:12] + "." + EXT[m.group(1)]
            pad = os.path.join(img_dir, naam)
            if not os.path.exists(pad):
                with open(pad, "wb") as f:
                    f.write(data)
            cache[b64] = "/img/" + naam
        return cache[b64]

    return IMG_RE.sub(sub, h), len(cache)


# ---------- stadsblok ----------
CSS = """<style>
/* stadspagina (build.py) */
.hero h2.hero-national{color:var(--ink);letter-spacing:-.015em}
.city-sec{padding:40px 0;background:#f0f5fa}
.city-sec .city-title{margin:0 0 6px;font-size:clamp(26px,3vw,36px);line-height:1.15;color:#17354d}
.city-pickup{margin:0 0 12px;font-weight:700;color:#b74c09;font-size:16px}
.city-sec .city-lead{max-width:760px;font-size:16px;line-height:1.6;color:#17354d;margin:0 0 16px}
.city-faq details{background:#fff;border:1px solid #cddae5;border-radius:12px;padding:12px 16px;margin:0 0 10px;max-width:760px}
.city-faq summary{font-weight:700;cursor:pointer;color:#17354d}
.city-faq details p{margin:8px 0 0;line-height:1.55}
.city-near{margin-top:14px;font-size:14px;color:#17354d;display:flex;flex-wrap:wrap;gap:4px 14px;align-items:baseline}
.city-near a{color:#b74c09;font-weight:700}
</style>"""


def stadsblok(s):
    n = s["naam"]
    ni = s.get("in_naam", n)   # optioneel: tekst na "in" (bv. "de Gooi regio")
    faq = "".join(
        f'<details><summary data-nl="{e(f["q_nl"])}" data-en="{e(f["q_en"])}">{e(f["q_nl"])}</summary>'
        f'<p data-nl="{e(f["a_nl"])}" data-en="{e(f["a_en"])}">{e(f["a_nl"])}</p></details>'
        for f in s["faq"])
    buren = "".join(f'<a href="{e(u)}">{e(t)}</a>' for t, u in s["buren"])
    return (
        f'<section class="city-sec" id="rijles-in-{e(s["slug"])}"><div class="container">\n'
        f'<h1 class="city-title" data-nl="Rijschool {e(n)}" data-en="Driving school {e(n)}">Rijschool {e(n)}</h1>\n'
        f'<p class="city-pickup" data-nl="📍 Wij halen je thuis op in {e(ni)}" '
        f'data-en="📍 We pick you up at home in {e(s.get("in_naam_en", ni))}">📍 Wij halen je thuis op in {e(ni)}</p>\n'
        f'<p class="city-lead" data-nl="{e(s["intro_nl"])}" data-en="{e(s["intro_en"])}">{e(s["intro_nl"])}</p>\n'
        f'<div class="city-faq">{faq}</div>\n'
        f'<div class="city-near"><span data-nl="Ook rijles in de buurt:" data-en="Also lessons nearby:">'
        f'Ook rijles in de buurt:</span> {buren}</div>\n'
        f'</div></section>\n'
    )


# ---------- JSON-LD ----------
def pas_jsonld_aan(h, s, url):
    blokken = list(re.finditer(r'<script type="application/ld\+json">(.*?)</script>', h, re.S))
    if not blokken:
        raise BuildFout("Geen JSON-LD gevonden in index.html")
    gezien = set()
    for m in reversed(blokken):
        d = json.loads(m.group(1))
        t = d.get("@type")
        gezien.add(t)
        if t == "LocalBusiness":
            d["url"] = url
            d["areaServed"] = [{"@type": "City", "name": s["naam"]}]
            if s.get("geo"):
                d["areaServed"][0]["geo"] = {"@type": "GeoCoordinates",
                                             "latitude": s["geo"][0], "longitude": s["geo"][1]}
        elif t == "FAQPage":
            stad = [{"@type": "Question", "name": f["q_nl"],
                     "acceptedAnswer": {"@type": "Answer", "text": f["a_nl"]}} for f in s["faq"]]
            namen = {q["name"] for q in stad}
            d["mainEntity"] = stad + [q for q in d.get("mainEntity", []) if q.get("name") not in namen]
        nieuw = '<script type="application/ld+json">' + json.dumps(d, ensure_ascii=False, indent=2) + "</script>"
        h = h[:m.start()] + nieuw + h[m.end():]
    for t in ("LocalBusiness", "FAQPage"):
        if t not in gezien:
            raise BuildFout(f"JSON-LD blok '{t}' ontbreekt in index.html")
    crumb = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
        {"@type": "ListItem", "position": 2, "name": f"Rijschool {s['naam']}", "item": url}]}
    return h.replace("</head>", '<script type="application/ld+json">'
                     + json.dumps(crumb, ensure_ascii=False) + "</script>\n</head>", 1)


# ---------- één stad ----------
def bouw_stad(bron, s, img_dir):
    n, slug = s["naam"], s["slug"]
    ni = s.get("in_naam", n)
    ne = s.get("in_naam_en", ni)
    url = f"{SITE}/rijschool-{slug}"
    h = bron

    # head
    h = vervang_regex(h, r"<title>.*?</title>", f"<title>{e(s['title'])}</title>", "<title>", re.S)
    h = vervang_regex(h, r'<meta name="description" content="[^"]*">',
                      f'<meta name="description" content="{e(s["meta"])}">', "meta description")
    h = vervang_regex(h, r'<link rel="canonical" href="[^"]*">', f'<link rel="canonical" href="{url}">', "canonical")
    h = vervang_regex(h, r'<meta property="og:url" content="[^"]*">', f'<meta property="og:url" content="{url}">', "og:url")
    for tag in ('property="og:title"', 'name="twitter:title"'):
        h = vervang_regex(h, rf'<meta {tag} content="[^"]*">',
                          f'<meta {tag} content="Rijschool {e(n)} — WegMaster Rijopleidingen">', tag)
    for tag in ('property="og:description"', 'name="twitter:description"'):
        h = vervang_regex(h, rf'<meta {tag} content="[^"]*">', f'<meta {tag} content="{e(s["meta"])}">', tag)

    # zichtbare teksten
    h = vervang_een(h, ANCHOR_OFFER,
                    f'data-nl="Rijles in {e(ni)}, morgen al rijden" data-en="Lessons in {e(ne)}, drive tomorrow">'
                    f'Rijles in {e(ni)}, morgen al rijden</h3>', "kop aanmeldkaart", aantal=2)
    h = vervang_een(h, ANCHOR_PAKKETTEN,
                    f'<h2 class="hero-national" data-nl="Auto lespakketten in {e(ni)}" '
                    f'data-en="Car lesson packages in {e(ne)}">Auto lespakketten in {e(ni)}</h2>', "kop pakketten")
    h = vervang_een(h, ANCHOR_GESLAAGDEN, stadsblok(s) + ANCHOR_GESLAAGDEN, "sectie geslaagden")

    # bron in de admin-mail: welke stadspagina
    h = vervang_een(h, ANCHOR_BRON,
                    f"'Google advertentie – Rijschool {n}' : 'Website – Rijschool {n}'", "bron (EmailJS)")

    # relatieve paden absoluut maken (werkt ook als de URL ooit een / krijgt)
    h = vervang_een(h, '<script src="consent.js"></script>', '<script src="/consent.js"></script>', "consent.js")
    h = h.replace("'geslaagden/", "'/geslaagden/")

    # JSON-LD
    h = pas_jsonld_aan(h, s, url)

    # CSS
    h = h.replace("</head>", CSS + "\n</head>", 1)

    # afbeeldingen naar /img/
    h, aantal_img = extraheer_afbeeldingen(h, img_dir)

    # afbeeldingen lager op de pagina mogen de hero niet vertragen
    h = re.sub(r'<img(?![^>]*fetchpriority)([^>]*loading="lazy")', r'<img fetchpriority="low"\1', h)

    # hero-afbeelding (LCP) direct laten laden: preload in <head>
    m = re.search(r'<img[^>]*fetchpriority="high"[^>]*src="(/img/[^"]+)"', h)
    if m:
        h = h.replace("</head>", f'<link rel="preload" as="image" href="{m.group(1)}" fetchpriority="high">\n</head>', 1)

    # controles
    for t in TRACKING:
        if t not in h:
            raise BuildFout(f"Tracking ontbreekt op rijschool-{slug}: {t}")
    if len(re.findall(r"<h1[\s>]", h.split('id="page-home"', 1)[1].split("</main>", 1)[0])) != 1:
        raise BuildFout(f"rijschool-{slug}: homepage-deel moet precies 1 <h1> hebben")
    if "Vandaag aanmelden, morgen al rijden" in h:
        raise BuildFout(f"rijschool-{slug}: kop aanmeldkaart niet vervangen")

    with open(os.path.join(ROOT, f"rijschool-{slug}.html"), "w", encoding="utf-8") as f:
        f.write(h)
    return len(h.encode("utf-8")), aantal_img


# ---------- dienstpagina's (zelfde pagina als de homepage) ----------
# Oude losse pagina's die nu dezelfde inhoud en stijl krijgen als index.html.
# De URL blijft gelijk (Google en links blijven werken).
#   start = welke sectie je ziet als je de pagina opent (home = homepage, spoedcursus = spoed-sectie)
DIENSTEN = [
    {"bestand": "automaat-rijles-amersfoort", "start": "home",
     "title": "Automaat rijles Amersfoort | WegMaster Rijopleidingen",
     "kort": "Automaat rijles Amersfoort",
     "meta": "Automaat rijles in Amersfoort, Soest en omgeving. Wij halen je thuis op. "
             "95% geslaagd, 5.0 op Google. Plan je proefles bij WegMaster Rijopleidingen."},
    {"bestand": "spoed-rijlessen-amersfoort", "start": "spoedcursus",
     "title": "Spoedcursus rijbewijs Amersfoort | WegMaster Rijopleidingen",
     "kort": "Spoedcursus Amersfoort",
     "meta": "Spoedcursus rijbewijs in Amersfoort, Soest en omgeving: meer lessen per week, "
             "een lesplan op jouw niveau. 95% geslaagd, 5.0 op Google."},
]


def bouw_dienst(bron, d, img_dir):
    naam, url = d["bestand"], f"{SITE}/{d['bestand']}"
    h = bron
    h = vervang_regex(h, r"<title>.*?</title>", f"<title>{e(d['title'])}</title>", "<title>", re.S)
    h = vervang_regex(h, r'<meta name="description" content="[^"]*">',
                      f'<meta name="description" content="{e(d["meta"])}">', "meta description")
    h = vervang_regex(h, r'<link rel="canonical" href="[^"]*">', f'<link rel="canonical" href="{url}">', "canonical")
    h = vervang_regex(h, r'<meta property="og:url" content="[^"]*">', f'<meta property="og:url" content="{url}">', "og:url")
    for tag in ('property="og:title"', 'name="twitter:title"'):
        h = vervang_regex(h, rf'<meta {tag} content="[^"]*">', f'<meta {tag} content="{e(d["title"])}">', tag)
    for tag in ('property="og:description"', 'name="twitter:description"'):
        h = vervang_regex(h, rf'<meta {tag} content="[^"]*">', f'<meta {tag} content="{e(d["meta"])}">', tag)

    # startsectie (zonder #... in de URL)
    if d["start"] != "home":
        n = h.count("(location.hash || '#home')")
        if n < 3:
            raise BuildFout(f"{naam}: route-code niet gevonden (location.hash || '#home')")
        h = h.replace("(location.hash || '#home')", f"(location.hash || '#{d['start']}')")

    # bron in de admin-mail
    h = vervang_een(h, ANCHOR_BRON,
                    f"'Google advertentie – {d['kort']}' : 'Website – {d['kort']}'", "bron (EmailJS)")
    h = vervang_een(h, '<script src="consent.js"></script>', '<script src="/consent.js"></script>', "consent.js")
    h = h.replace("'geslaagden/", "'/geslaagden/")

    h, aantal_img = extraheer_afbeeldingen(h, img_dir)
    h = re.sub(r'<img(?![^>]*fetchpriority)([^>]*loading="lazy")', r'<img fetchpriority="low"\1', h)
    m = re.search(r'<img[^>]*fetchpriority="high"[^>]*src="(/img/[^"]+)"', h)
    if m:
        h = h.replace("</head>", f'<link rel="preload" as="image" href="{m.group(1)}" fetchpriority="high">\n</head>', 1)

    for t in TRACKING:
        if t not in h:
            raise BuildFout(f"Tracking ontbreekt op {naam}: {t}")
    with open(os.path.join(ROOT, f"{naam}.html"), "w", encoding="utf-8") as f:
        f.write(h)
    return len(h.encode("utf-8")), aantal_img


# ---------- sitemap.xml ----------
def redirect_bronnen():
    """Paden die in _redirects worden doorgestuurd (horen niet in de sitemap)."""
    pad = os.path.join(ROOT, "_redirects")
    bronnen = set()
    if os.path.exists(pad):
        for regel in open(pad, encoding="utf-8"):
            regel = regel.strip()
            if regel and not regel.startswith("#"):
                bronnen.add(regel.split()[0].removesuffix(".html"))
    return bronnen


def laatst_gewijzigd(bestand):
    """Datum van de laatste git-commit van dit bestand; anders vandaag."""
    import datetime
    import subprocess
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%cs", "--", bestand], cwd=ROOT,
                             capture_output=True, text=True, timeout=10).stdout.strip()
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", out):
            return out
    except Exception:
        pass
    return datetime.date.today().isoformat()


def schrijf_sitemap(steden):
    import datetime
    vandaag = datetime.date.today().isoformat()
    weg = redirect_bronnen()
    gebouwd = {f"rijschool-{s['slug']}.html" for s in steden} | {f"{d['bestand']}.html" for d in DIENSTEN}
    urls = [(SITE + "/", vandaag, "1.0")]
    urls += [(f"{SITE}/rijschool-{s['slug']}", vandaag, "0.8") for s in steden]
    urls += [(f"{SITE}/{d['bestand']}", vandaag, "0.7") for d in DIENSTEN]
    overig = sorted(f for f in os.listdir(ROOT)
                    if f.endswith(".html") and f not in gebouwd and f != "index.html"
                    and not f.startswith("google") and "/" + f[:-5] not in weg)
    urls += [(f"{SITE}/{f[:-5]}", laatst_gewijzigd(f), "0.6") for f in overig]
    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    xml += [f"  <url><loc>{u}</loc><lastmod>{d}</lastmod><priority>{p}</priority></url>" for u, d, p in urls]
    xml.append("</urlset>")
    with open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write("\n".join(xml) + "\n")
    return len(urls)


def main():
    with open(os.path.join(ROOT, "index.html"), encoding="utf-8") as f:
        bron = f.read()
    with open(os.path.join(ROOT, "steden.json"), encoding="utf-8") as f:
        steden = json.load(f)["steden"]
    for t in TRACKING:
        if t not in bron:
            raise BuildFout(f"Tracking ontbreekt al in index.html: {t}")
    img_dir = os.path.join(ROOT, "img")
    for s in steden:
        grootte, n_img = bouw_stad(bron, s, img_dir)
        print(f"  ✓ rijschool-{s['slug']}.html  {grootte/1024:.0f} KB  ({n_img} afbeeldingen in /img/)")
    for d in DIENSTEN:
        grootte, n_img = bouw_dienst(bron, d, img_dir)
        print(f"  ✓ {d['bestand']}.html  {grootte/1024:.0f} KB  ({n_img} afbeeldingen in /img/)")
    n_urls = schrijf_sitemap(steden)
    print(f"  ✓ sitemap.xml  {n_urls} URL's")
    print(f"build.py: {len(steden)} stadspagina's + {len(DIENSTEN)} dienstpagina's OK")


if __name__ == "__main__":
    try:
        main()
    except BuildFout as fout:
        print("\n✗ BUILD GESTOPT — de live site blijft ongewijzigd.\n  " + str(fout), file=sys.stderr)
        sys.exit(1)
