# Contributing

Tämä projekti on henkilökohtainen N-of-1-tutkimustyökalu. Pull requesteja ei tällä hetkellä käsitellä, mutta tikettikeskustelu on avointa.

## Kehitysympäristö

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt  # kun requirements.txt on luotu
```

## Projektirakenne

```
weekly-cycle-oura-skill/
├── README.md                 # Yleiskuvaus, käyttöönotto ja OURA_TOKEN-ohje
├── design.md                 # Arkkitehtuuri ja suunnittelupäätökset
├── oura-api-decisions.md     # Oura API v2 -selvitysten ratkaisut (tikettien #14–#21 päätökset)
├── CONTRIBUTING.md           # Tämä tiedosto
├── LICENSING.md              # Käytetyt teknologiakomponentit ja niiden lisenssit
├── index.html                # GitHub Pages -etusivu (redirect → architecture.html)
├── architecture.html         # Interaktiivinen pipeline-dokumentti (tulossa)
├── LICENSE
└── src/                      # Tulossa: oura_client.py, pipeline.py jne.
```

## Riippuvuuksien lisääminen

Ennen kuin lisäät uuden paketin `requirements.txt`:iin tai `requirements-dev.txt`:iin:

1. Tarkista paketin lisenssi (PyPI-sivu tai pakettirepo).
2. Varmista yhteensopivuus projektin MIT-lisenssin kanssa. MIT + Apache 2.0 + BSD + ISC ovat yhteensopivia. GPL on ei-yhteensopiva.
3. Lisää paketti [`LICENSING.md`](LICENSING.md):hen oikeaan taulukkoon (tuotanto- tai kehitysriippuvuus) ennen committia.
4. Lisää paketti `requirements.txt`:iin tai `requirements-dev.txt`:iin.

**Konventio:** `LICENSING.md` on aina ajan tasalla. Jos se ei ole, se on bugi.

## Tiketöintikäytäntö

- **MVP-label**: tiketti kuuluu minimitoteutukseen
- **post-MVP-label**: hyvä idea, ei blokkaa MVP:tä
- Tikettien kommentit toimivat päätöslogina — älä siivoa niitä
- Kun tiketti on ratkaistu, lisää `## ✅ Ratkaistu`-kommentti ja sulje tiketti `completed`-tilaan

## Koodikonventiot

- Python 3.11+
- Tyyppiannotaatiot kaikissa julkisissa funktioissa
- Docstring jokaiseen `compute_*` ja `analyze_*` -funktioon
- Testit `tests/`-kansioon (pytest)
- Ei hard-kodattuja päivämääriä tai kynnysarvoja — kaikki konfiguraatioon tai vakioihin
- Lint ja formatointi: `ruff check` + `ruff format` (CI tarkistaa automaattisesti, #24)

## Oura API

Katso [`oura-api-decisions.md`](oura-api-decisions.md) — siellä on koottu kaikki MVP:n endpointtipäätökset ja kenttävalinnat.
