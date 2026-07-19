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
├── README.md                 # Yleiskuvaus ja käyttöönotto
├── design.md                 # Arkkitehtuuri ja suunnittelupäätökset
├── oura-api-decisions.md     # Oura API v2 -selvitysten ratkaisut
├── CONTRIBUTING.md           # Tämä tiedosto
└── src/                      # Tulossa: oura_client.py, pipeline.py jne.
```

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

## Oura API

Katso [`oura-api-decisions.md`](oura-api-decisions.md) — siellä on koottu kaikki MVP:n endpointtipäätökset ja kenttävalinnat.
