# Stadspagina's — hoe werkt het?

**Kort:** je bewerkt alleen `index.html` (en soms `steden.json`). Netlify draait bij elke deploy `python3 build.py`, en dat maakt automatisch:

- 12 stadspagina's: `/rijschool-amersfoort`, `/rijschool-soest`, `/rijschool-nijkerk`, `/rijschool-leusden`, `/rijschool-hoevelaken`, `/rijschool-zeist`, `/rijschool-baarn`, `/rijschool-bunschoten`, `/rijschool-woudenberg`, `/rijschool-soesterberg`, `/rijschool-bilthoven`, `/rijschool-de-bilt`
- de map `/img/` (de foto's van de stadspagina's als losse bestanden)
- 2 dienstpagina's, precies dezelfde pagina als de homepage: `/automaat-rijles-amersfoort` (opent op de homepage) en `/spoed-rijlessen-amersfoort` (opent op de sectie Spoedcursus). Instellingen: `DIENSTEN` in `build.py`.
- `sitemap.xml`

De homepage (`/`) is algemeen ("WegMaster Rijopleidingen"). Amersfoort heeft een eigen pagina: `/rijschool-amersfoort`. In Google Ads gaat elk zoekwoord naar de pagina van zijn stad; de homepage wordt in Ads niet gebruikt.

## Wat moet ik doen als ik iets wil aanpassen?

| Wat | Waar | Resultaat |
| --- | --- | --- |
| Prijzen, foto's, teksten, design | `index.html` | Na upload naar GitHub worden binnen 1–2 min ook alle 12 stadspagina's bijgewerkt |
| Tekst van één stad (title, meta, intro, FAQ, buurplaatsen) | `steden.json` | Alleen die stad verandert |
| Nieuwe stad | `steden.json`: kopieer een blok, pas `slug`, `naam` en de teksten aan | Er komt automatisch een nieuwe pagina bij (zet hem ook in de footer "Werkgebied" in `index.html`) |

## Let op: deze teksten in index.html niet veranderen

`build.py` zoekt deze vaste teksten om de stadsnaam in te zetten. Verander je er één, dan **stopt de build**. De live site blijft dan gewoon zoals hij was; alleen de nieuwe versie komt niet online tot het is opgelost.

1. `Vandaag aanmelden, morgen al rijden` (de kop van de aanmeldkaart, 2x: mobiel + desktop) incl. `data-en="Sign up today, drive tomorrow"`
2. `<h1 class="hero-national" data-nl="Auto lespakketten" data-en="Car lesson packages">Auto lespakketten</h1>`
3. `<section class="section--tight gl-sec" id="geslaagden">` (hier komt het blok "Rijschool [stad]" boven)
4. `'Google advertentie' : 'Website (geen advertentie)'` (de bron in de admin-mail)
5. `<script src="consent.js"></script>`

En deze tracking moet blijven staan (anders stopt de build ook): `AW-18306777925`, `…/GRwtCOzhlJ8dEMWGrZlE` (formulier), `…/xI6uCKfg59QcEMWGrZlE` (bellen/WhatsApp), `allow_enhanced_conversions`, `template_xcebm69`, `template_zq02f9v`, `wm_gclid`.

## De build ging mis — wat nu?

Netlify → Deploys → klik op de mislukte deploy → onderaan staat `✗ BUILD GESTOPT` met de tekst die niet gevonden werd. Zet die tekst terug in `index.html`, of vraag Claude om `build.py` aan te passen.

## Lokaal testen (optioneel)

```
python3 build.py
```
