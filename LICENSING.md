# Licensing

Tämä dokumentti listaa kaikki `weekly-cycle-oura-skill`-projektin käyttämät teknologiakomponentit ja niiden lisenssit. Kaikki uudet riippuvuudet dokumentoidaan tänne ennen lisäämistä `requirements.txt`:iin.

---

## Projektin oma lisenssi

| Komponentti | Lisenssi | Huomio |
|---|---|---|
| weekly-cycle-oura-skill | [MIT](LICENSE) | Henkilökohtainen käyttö, ei takuuta |

---

## Python-ajoympstäristö

| Komponentti | Versio (min) | Lisenssi | SPDX-tunnus |
|---|---|---|---|
| [Python](https://python.org) | 3.11 | PSF License | PSF-2.0 |

---

## Tuotantoriippuvuudet (`requirements.txt`)

| Paketti | Käyttö | Lisenssi | SPDX-tunnus |
|---|---|---|---|
| [python-dotenv](https://github.com/theskumar/python-dotenv) | `OURA_TOKEN`-ympstäristömuuttujan lataus `.env`-tiedostosta | MIT | MIT |
| [requests](https://requests.readthedocs.io) | Oura API v2 HTTP-kutsut (`oura_client.py`, #13) | Apache 2.0 | Apache-2.0 |

> Muut tuotantoriippuvuudet lisätään tähän kun `requirements.txt` luodaan (#13).

---

## Kehitysriippuvuudet (`requirements-dev.txt` tai `[dev]`-extras)

| Paketti | Käyttö | Lisenssi | SPDX-tunnus |
|---|---|---|---|
| [ruff](https://github.com/astral-sh/ruff) | Lint + format (`ci.yml`, #24) | MIT | MIT |
| [mypy](https://mypy-lang.org) | Staattinen tyyppitarkistus (`ci.yml`, #24) | MIT | MIT |
| [pytest](https://pytest.org) | Yksikkötestit (`ci.yml`, #24) | MIT | MIT |

---

## Ulkoiset palvelut ja API:t

| Palvelu | Käyttö | Ehdot |
|---|---|---|
| [Oura API v2](https://cloud.ouraring.com/v2/docs) | Fysiologinen lähdedata (uni, HRV, aktiivisuus, readiness) | [Oura Terms of Service](https://ouraring.com/terms-of-service) — henkilökohtainen käyttö, ei kaupallinen jakelu |
| [GitHub Actions](https://docs.github.com/en/actions) | CI-workflow (#24, #25) | [GitHub Terms of Service](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service) |
| [GitHub Pages](https://pages.github.com) | Arkkitehtuuridokumentin julkaisu (`index.html`, `architecture.html`) | [GitHub Terms of Service](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service) |

---

## Huomiot yhteensopivuudesta

- MIT + Apache 2.0 ovat yhteensopivia projektin MIT-lisenssin kanssa.
- PSF-lisenssi (Python itse) on yhteensopiva MIT:n kanssa.
- Oura API:n käyttöehdot rajoittavat datan kaupallisen jakelun — tämä projekti on henkilökohtainen tutkimustyökalu, joten rajoitus ei tule vastaan.

---

## Konventio: uudet riippuvuudet

Katso ohje: [`CONTRIBUTING.md`](CONTRIBUTING.md) — *Riippuvuuksien lisääminen*.
