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
ANCHOR_NA_REVIEWS = ('<section class="section--tight">\n    <div class="container">\n'
                     '      <div class="transmission-band">')   # eerste sectie na de reviews
ANCHOR_BRON = "'Google advertentie' : 'Website (geen advertentie)'"
ANCHOR_HERO_H2 = ('<h2 data-nl="Snel je rijbewijs halen? <span class=\'accent\'>Check!</span>"')


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


# ---------- hero-foto's: elk apparaat laadt alleen wat het toont ----------
# Desktop (>=1025px) toont .stp-clean; mobiel/tablet (<=1024px) toont .stp-s2 (boven) + .stp-city.
# <picture> met een 1x1-pixel voor het andere formaat: zo downloadt een telefoon de desktopfoto niet
# en andersom. display:contents = de <picture> verandert niets aan de opmaak.
LEEG = "data:image/svg+xml,%3Csvg%20xmlns=%27http://www.w3.org/2000/svg%27%20width=%271%27%20height=%271%27/%3E"   # 1x1, geen download
MQ_KLEIN, MQ_GROOT = "(max-width:1024px)", "(min-width:1025px)"
VARIANT_DIR = "img-v"          # kleinere versies van .stp-s2 (in de repo; bestandsnaam = hash van het origineel)
VARIANT_BREEDTES = (640, 960, 1280)


def optimaliseer_hero(h, wat):
    def tag(cls):
        m = re.search(r'<img class="' + re.escape(cls) + r'"[^>]*>', h) or \
            re.search(r'<img [^>]*class="' + re.escape(cls) + r'"[^>]*>', h)
        if not m:
            raise BuildFout(f"{wat}: hero-foto {cls} niet gevonden")
        return m.group(0)

    t_s2, t_clean, t_city = tag("stp-slide stp-s2"), tag("stp-clean"), tag("stp-city")
    src = lambda t: re.search(r'src="(/img/[^"]+)"', t).group(1)
    s2, clean, city = src(t_s2), src(t_clean), src(t_city)

    # srcset voor .stp-s2 als de kleinere versies bestaan
    naam = os.path.splitext(os.path.basename(s2))[0]
    varianten = [(f"/{VARIANT_DIR}/{naam}-{w}.webp", w) for w in VARIANT_BREEDTES
                 if os.path.exists(os.path.join(ROOT, VARIANT_DIR, f"{naam}-{w}.webp"))]
    s2_srcset = ", ".join(f"{u} {w}w" for u, w in varianten + [(s2, 1672)]) if varianten else ""

    # telefoon (<=600px): .stp-city als uitsnede = precies het deel dat je ziet (zelfde pixels, half zo groot)
    naam_c = os.path.splitext(os.path.basename(city))[0]
    city_m = f"/{VARIANT_DIR}/{naam_c}-m.webp" if os.path.exists(os.path.join(ROOT, VARIANT_DIR, f"{naam_c}-m.webp")) else ""

    nieuw_s2 = t_s2
    if s2_srcset:
        nieuw_s2 = nieuw_s2.replace(f'src="{s2}"', f'src="{s2}" srcset="{s2_srcset}" sizes="100vw"')
    nieuw_clean = re.sub(r'\s(loading="lazy"|fetchpriority="low")', "", t_clean)
    nieuw_clean = nieuw_clean.replace("<img ", '<img fetchpriority="high" ', 1)
    nieuw_city = t_city.replace("<img ", '<img fetchpriority="high" ', 1)

    pic = lambda media, img: (f'<picture style="display:contents"><source media="{media}" srcset="{LEEG}">'
                              f'{img}</picture>')
    pic_city = pic(MQ_GROOT, nieuw_city)
    if city_m:
        pic_city = pic_city.replace("<img ", f'<source media="(max-width:600px)" srcset="{city_m}"><img ', 1)
    for oud, nieuw in ((t_s2, pic(MQ_GROOT, nieuw_s2)), (t_clean, pic(MQ_KLEIN, nieuw_clean)),
                       (t_city, pic_city)):
        if h.count(oud) != 1:
            raise BuildFout(f"{wat}: hero-foto niet precies 1x gevonden")
        h = h.replace(oud, nieuw)

    # preload per schermformaat (oude algemene preload vervalt)
    pre_s2 = (f'<link rel="preload" as="image" href="{s2}" imagesrcset="{s2_srcset}" imagesizes="100vw" '
              if s2_srcset else f'<link rel="preload" as="image" href="{s2}" ')
    pre = (pre_s2 + f'media="{MQ_KLEIN}" fetchpriority="high">\n'
           + (f'<link rel="preload" as="image" href="{city_m}" media="(max-width:600px)" fetchpriority="high">\n'
              f'<link rel="preload" as="image" href="{city}" media="(min-width:601px) and (max-width:1024px)" fetchpriority="high">\n'
              if city_m else
              f'<link rel="preload" as="image" href="{city}" media="{MQ_KLEIN}" fetchpriority="high">\n') +
           f'<link rel="preload" as="image" href="{clean}" media="{MQ_GROOT}" fetchpriority="high">\n')
    h = h.replace("</head>", pre + "</head>", 1)

    # achtergrondfoto van .hero (pakketten-sectie) pas laden als die sectie in beeld komt
    m = re.search(r"(\.hero::before\{[^}]*?background:\s*)(linear-gradient\([^;]*?\)\)),\s*"
                  r"(url\('/img/[^']+'\)[^;]*);", h)
    if not m:
        raise BuildFout(f"{wat}: .hero::before-achtergrond niet gevonden")
    h = h[:m.start()] + m.group(1) + m.group(2) + ";" + h[m.end():]
    h = h.replace("</head>", "<style>.hero.wm-bg::before{background:" + m.group(2) + ", " + m.group(3) +
                  ";}</style>\n</head>", 1)
    js = ("<script>(function(){var l=document.querySelectorAll('.hero');function on(e){e.classList.add('wm-bg');}"
          "if(!('IntersectionObserver' in window)){l.forEach(on);return;}"
          "var o=new IntersectionObserver(function(es){es.forEach(function(x){if(x.isIntersecting){on(x.target);"
          "o.unobserve(x.target);}});},{rootMargin:'800px 0px'});l.forEach(function(e){o.observe(e);});})();</script>")
    h = h.replace("</body>", js + "\n</body>", 1)
    return h


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
/* stadsnaam bovenaan in de hero (Quality Score: zoekwoord direct zichtbaar) */
#zowerkt .stp-intro h1.stp-kicker{display:inline-block;margin:0 0 6px;padding:3px 10px 3px 8px;border-radius:999px;
  background:rgba(255,255,255,.92);color:#b74c09;font-size:15px;line-height:1.3;font-weight:800;letter-spacing:0;
  box-shadow:0 2px 8px -4px rgba(11,27,46,.35);white-space:normal}
#zowerkt .stp-intro h1.stp-kicker::before{content:"📍 ";}
/* tablet/mobiel: de kop staat daar in de foto en de aanmeldkaart toont al "Rijles in <stad>" -> kicker alleen voor Google/schermlezers */
@media(max-width:1024px){#zowerkt .stp-intro h1.stp-kicker{position:absolute!important;width:1px!important;height:1px!important;
  padding:0!important;margin:-1px!important;overflow:hidden!important;clip:rect(0,0,0,0)!important;white-space:nowrap!important;border:0!important;box-shadow:none!important}}
.dorp-chips{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 18px}
.dorp-chips a{background:#fff;border:1px solid #cddae5;border-radius:999px;padding:6px 12px;font-weight:700;font-size:14px;color:#17354d;text-decoration:none}
.dorp-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px;margin:0 0 22px}
.dorp-kaart{background:#fff;border:1px solid #cddae5;border-radius:14px;padding:16px;scroll-margin-top:90px}
.dorp-kaart h3{margin:0 0 6px;font-size:19px;color:#17354d}
.dorp-kaart p{margin:0 0 12px;line-height:1.55;font-size:15px;color:#17354d}
.dorp-knoppen{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center}
.dorp-cta{background:#e8600a;color:#fff;border-radius:10px;padding:9px 14px;font-weight:700;font-size:14px;text-decoration:none}
.dorp-meer{color:#b74c09;font-weight:700;font-size:14px}
</style>"""


def dorpenblok(s):
    """Optioneel (steden.json "dorpen"): per plaats een kaart, met snelknoppen erboven."""
    dorpen = s.get("dorpen") or []
    if not dorpen:
        return ""
    chips = "".join(f'<a href="#dorp-{e(d["id"])}">{e(d["naam"])}</a>' for d in dorpen)
    kaarten = ""
    for d in dorpen:
        n = e(d["naam"])
        meer = (f'<a class="dorp-meer" href="{e(d["link"])}" data-nl="Meer over {n}" '
                f'data-en="More about {n}">Meer over {n}</a>' if d.get("link") else "")
        kaarten += (
            f'<div class="dorp-kaart" id="dorp-{e(d["id"])}">'
            f'<h3 data-nl="Rijles in {n}" data-en="Driving lessons in {n}">Rijles in {n}</h3>'
            f'<p data-nl="{e(d["nl"])}" data-en="{e(d["en"])}">{e(d["nl"])}</p>'
            f'<div class="dorp-knoppen"><a class="dorp-cta" href="#register" '
            f'data-nl="Aanmelden in {n}" data-en="Sign up in {n}">Aanmelden in {n}</a>{meer}</div>'
            f'</div>')
    return (f'<div class="dorp-chips">{chips}</div>\n'
            f'<div class="dorp-grid">{kaarten}</div>\n')


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
        f'<h2 class="city-title" data-nl="Rijschool {e(n)}" data-en="Driving school {e(n)}">Rijschool {e(n)}</h2>\n'
        f'<p class="city-pickup" data-nl="📍 Wij halen je thuis op in {e(ni)}" '
        f'data-en="📍 We pick you up at home in {e(s.get("in_naam_en", ni))}">📍 Wij halen je thuis op in {e(ni)}</p>\n'
        f'<p class="city-lead" data-nl="{e(s["intro_nl"])}" data-en="{e(s["intro_en"])}">{e(s["intro_nl"])}</p>\n'
        + dorpenblok(s)
        + f'<div class="city-faq">{faq}</div>\n'
        + (f'<div class="city-near"><span data-nl="Ook rijles in de buurt:" data-en="Also lessons nearby:">'
           f'Ook rijles in de buurt:</span> {buren}</div>\n' if buren else '')
        + '</div></section>\n'
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
    nk, nke = s.get("kort_naam", ni), s.get("kort_naam_en", ne)   # korte naam voor de kop van de aanmeldkaart
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
                    f'data-nl="Rijles in {e(nk)}, morgen al rijden" data-en="Lessons in {e(nke)}, drive tomorrow">'
                    f'Rijles in {e(nk)}, morgen al rijden</h3>', "kop aanmeldkaart", aantal=2)
    h = vervang_een(h, ANCHOR_PAKKETTEN,
                    f'<h2 class="hero-national" data-nl="Auto lespakketten in {e(ni)}" '
                    f'data-en="Car lesson packages in {e(ne)}">Auto lespakketten in {e(ni)}</h2>', "kop pakketten")
    # stadsnaam bovenaan in de hero, als <h1> (de h1 in het stadsblok wordt een h2)
    h = vervang_een(h, ANCHOR_HERO_H2,
                    f'<h1 class="stp-kicker" data-nl="Rijschool {e(n)}" data-en="Driving school {e(n)}">'
                    f'Rijschool {e(n)}</h1>\n        ' + ANCHOR_HERO_H2, "stadsnaam in hero")
    # volgorde: pakketten > geslaagden (foto's) > reviews > stadsblok > rest
    h = vervang_een(h, ANCHOR_NA_REVIEWS, stadsblok(s) + ANCHOR_NA_REVIEWS, "sectie na reviews")

    # bron in de admin-mail: welke stadspagina
    h = vervang_een(h, ANCHOR_BRON,
                    f"'Google advertentie – Rijschool {n}' : 'Website – Rijschool {n}'", "bron (EmailJS)")

    # relatieve paden absoluut maken (werkt ook als de URL ooit een / krijgt)
    h = vervang_een(h, '<script src="consent.js"></script>', '<script src="/consent.js"></script>', "consent.js")
    h = h.replace("'geslaagden/", "'/geslaagden/")

    # optioneel: eigen werkgebied in de footer (alleen tekst, geen links)
    if s.get("footer_plaatsen"):
        lijst = "".join(f"<li>{e(x)}</li>" for x in s["footer_plaatsen"])
        h, n_ft = re.subn(r'(<div class="footer-regio">\s*<h4[^>]*>Werkgebied</h4>\s*)<ul>.*?</ul>',
                          lambda m: m.group(1) + "<ul>" + lijst + "</ul>", h, count=1, flags=re.S)
        if n_ft != 1:
            raise BuildFout(f"rijschool-{slug}: footer-werkgebied niet gevonden")

    # optioneel: vaste teksten vervangen (bv. regio in de algemene FAQ)
    for oud, nieuw in s.get("vervang", []):
        if oud not in h:
            raise BuildFout(f"rijschool-{slug}: tekst niet gevonden: {oud[:50]}")
        h = h.replace(oud, nieuw)

    # JSON-LD
    h = pas_jsonld_aan(h, s, url)

    # CSS
    h = h.replace("</head>", CSS + "\n</head>", 1)

    # afbeeldingen naar /img/
    h, aantal_img = extraheer_afbeeldingen(h, img_dir)

    # afbeeldingen lager op de pagina mogen de hero niet vertragen
    h = re.sub(r'<img(?![^>]*fetchpriority)([^>]*loading="lazy")', r'<img fetchpriority="low"\1', h)

    # hero-afbeelding (LCP) direct laten laden: preload in <head>
    h = optimaliseer_hero(h, f"rijschool-{slug}")

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
    h = optimaliseer_hero(h, naam)

    for t in TRACKING:
        if t not in h:
            raise BuildFout(f"Tracking ontbreekt op {naam}: {t}")
    with open(os.path.join(ROOT, f"{naam}.html"), "w", encoding="utf-8") as f:
        f.write(h)
    return len(h.encode("utf-8")), aantal_img


# ---------- homepage (snelle versie) ----------
# index.html in de repo blijft de bron (met base64-afbeeldingen).
# Alleen op Netlify (NETLIFY=true) wordt de gepubliceerde index.html vervangen door
# dezelfde pagina met de afbeeldingen als losse bestanden in /img/ (zoals de stadspagina's).
# Lokaal testen: WM_HOME_TEST=1 schrijft index.build.html (index.html blijft onaangeroerd).
def bouw_home(bron, img_dir):
    h = bron
    h, aantal_img = extraheer_afbeeldingen(h, img_dir)
    h = re.sub(r'<img(?![^>]*fetchpriority)([^>]*loading="lazy")', r'<img fetchpriority="low"\1', h)
    h = optimaliseer_hero(h, "homepage")
    for t in TRACKING:
        if t not in h:
            raise BuildFout(f"Tracking ontbreekt op homepage: {t}")
    if "data:image/" in h and IMG_RE.search(h):
        raise BuildFout("homepage: nog base64-afbeeldingen over")
    if len(re.findall(r"<h1[\s>]", h)) != len(re.findall(r"<h1[\s>]", bron)):
        raise BuildFout("homepage: aantal <h1> veranderd")
    if os.environ.get("NETLIFY") == "true":
        doel = "index.html"
    elif os.environ.get("WM_HOME_TEST") == "1":
        doel = "index.build.html"
    else:
        return None, aantal_img
    with open(os.path.join(ROOT, doel), "w", encoding="utf-8") as f:
        f.write(h)
    return (doel, len(h.encode("utf-8"))), aantal_img


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
                    if f.endswith(".html") and f not in gebouwd and f not in ("index.html", "index.build.html")
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
    res, n_img = bouw_home(bron, img_dir)
    if res:
        print(f"  ✓ {res[0]} (homepage)  {res[1]/1024:.0f} KB  ({n_img} afbeeldingen in /img/)")
    else:
        print(f"  ✓ homepage gecontroleerd ({n_img} afbeeldingen); index.html wordt alleen op Netlify vervangen")
    n_urls = schrijf_sitemap(steden)
    print(f"  ✓ sitemap.xml  {n_urls} URL's")
    print(f"build.py: {len(steden)} stadspagina's + {len(DIENSTEN)} dienstpagina's OK")


if __name__ == "__main__":
    try:
        main()
    except BuildFout as fout:
        print("\n✗ BUILD GESTOPT — de live site blijft ongewijzigd.\n  " + str(fout), file=sys.stderr)
        sys.exit(1)
