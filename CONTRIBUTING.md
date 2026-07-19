# Contributing — weekly-cycle-oura-skill

Tämä dokumentti kuvaa TDD-pohjaisen kehitystyönkulun MVP-vaiheelle.

## Kehitysympäristö

### Vaatimukset

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) — ainoa hyväksytty paketinhallintaratkaisu

### Asennus

```bash
# Kloonaa repo
git clone https://github.com/jaakkokorhonen/weekly-cycle-oura-skill.git
cd weekly-cycle-oura-skill

# Luo virtualenv ja asenna riippuvuudet
uv sync

# Kopioi konfiguraatio
cp config.yaml.example config.yaml
# Täytä config.yaml:iin oikea OURA_TOKEN
```

### Testien ajaminen

```bash
# Kaikki yksikkötestit
uv run pytest

# Yksittäinen testitiedosto
uv run pytest tests/unit/test_rule_engine.py -v

# Linter
uv run ruff check src/ tests/
```

> **Huom:** `tests/unit/` ajetaan automaattisesti. `tests/post_mvp/` ei aja automaattisesti — ne testataan erikseen kun vastaavat moduulit toteutetaan.

## Tiedostorakenne ja nimeämiskäytännöt

**Kaikki dokumentaatiotiedostot ovat repojuuressa** — ei `docs/`-alikansioita.

Käytännöt:
- Uusi `.md`-tiedosto luodaan aina juureen, ei alikansioon.
- Tiedostonimi kirjoitetaan **kokonaan isoilla kirjaimilla** (`CAPS.md`), esimerkiksi `ARCHITECTURE.md`, `DESIGN.md`, `OURA-API-DECISIONS.md`.
- Poikkeuksia ovat ainoastaan GitHubin tunnistamia vakiotiedostoja: `README.md`, `CONTRIBUTING.md`, `LICENSE`.

```
weekly-cycle-oura-skill/
├── README.md
├── CONTRIBUTING.md        ← tämä tiedosto
├── ARCHITECTURE.md        ← moduulit, datavirta, hakemistorakenne
├── DESIGN.md              ← tausta, tavoite, analyysifunktiot
├── OURA-API-DECISIONS.md  ← endpoint- ja kenttävalinnat
├── config.yaml.example
├── pyproject.toml
├── src/
├── tests/
└── data/
```

## MVP-toteutusjärjestys (TDD-polku)

Riippuvuusgraafin mukainen eteneminen. Jokainen moduuli toteutetaan punainen–vihreä–refaktoroi -syklillä.

```
1. config.yaml.example   ← jo repossa — kopioi config.yaml:ksi ennen pytest-ajoa
2. src/oura_client.py    (#26) — ei riippuvuuksia
3. src/event_manager.py  (#27) — ei riippuvuuksia, rinnakkain #26:n kanssa
4. src/features.py       (#2)  — ei riippuvuuksia
5. src/rule_engine.py    (#29) — riippuu #2:sta
6. src/recommendation_engine.py (#30) — riippuu #29:stä
7. src/pipeline.py       (#28) — riippuu kaikista yllä
8. src/mcp_server.py     (#33) — riippuu #28 + #27
```

Kaikki testiskeletot ovat valmiina `tests/unit/`-kansiossa ja **epäonnistuvat tarkoituksella** ennen toteutusta.

## Konfiguraatio

`config.yaml` on `.gitignore`:ssa. Versionhallinnassa on `config.yaml.example`, joka sisältää kaikki kentät tyhjillä arvoilla.

Yksikkötestit **eivät koskaan** lue oikeaa `config.yaml`:ia — ne käyttävät inline-dict-fixtureita tai `tmp_path`-fixturea.

## Tunnetut ongelmat ennen toteutusta

Katso [PR #35](https://github.com/jaakkokorhonen/weekly-cycle-oura-skill/pull/35) — "Tunnetut ongelmat ja puutteet" -osio:

- `test_rule_engine.py` käyttää litistettyä config-rakennetta → korjattava ennen `rule_engine.py`:n toteutusta
- `test_pipeline.py` käyttää vääriä avainnimiä (`readiness`/`activity`) → korjattava ennen `pipeline.py`:n toteutusta
- `test_cli.py` kuuluu `tests/post_mvp/`-kansioon

## Commit-käytännöt

```
feat: lyhyt kuvaus
fix: lyhyt kuvaus
docs: lyhyt kuvaus
test: lyhyt kuvaus
refactor: lyhyt kuvaus
```

Komitit liitetään tikettiin viittaamalla numeron kautta: `feat: implement oura_client.fetch_range() closes #26`
