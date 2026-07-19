# Arkkitehtuuri — weekly-cycle-oura-skill

## Yleiskuva

Skill on Python-pohjainen analyysikerros, joka lukee Oura API v2:sta fysiologisen datan, rikastaa sen johdetuilla muuttujilla, luokittelee päivän ja tuottaa lyhyen taktisen suositustekstin. Järjestelmä altistaa toimintansa MCP-protokollan kautta AI-assistenteille (Antigravity, Perplexity).

Katso taustat ja tavoitteet: [DESIGN.md](DESIGN.md) — Oura API -kenttävalinnat: [OURA-API-DECISIONS.md](OURA-API-DECISIONS.md)

```
┌────────────────────────────────────────────────────────┐
│                    AI-asiakkaat                          │
│            Antigravity         Perplexity                │
└──────────────────┬──────────────────┬────────────────────┘
                   │ stdio            │ stdio
                   ▼                  ▼
         ┌────────────────────────────────┐
         │         mcp_server.py          │
         │  run_pipeline / log_event /    │
         │  get_daily_report / get_status │
         └──────────────┬────────────────┘
                        │
                        ▼
         ┌────────────────────────────────┐
         │           pipeline.py          │
         │  orchestroija — fetch, enrich, │
         │  classify, recommend, write    │
         └────┬───────────────────────┬───┘
              │                      │
     ┌────────┴───┐           ┌──────┴──────────────┐
     │oura_       │           │ event_              │
     │client.py   │           │ manager.py          │
     └───────┬────┘           └────┬────────────────┘
             │                    │
             ▼                    ▼
         ┌────────────────────────────────┐
         │          features.py           │
         │  derived-muuttujat             │
         └──────────────┬────────────────┘
                        │
             ┌──────────┴──────────────────┐
             ▼                             ▼
     ┌───────────────┐   ┌──────────────────────┐
     │ rule_engine   │   │ recommendation_      │
     │ .py           │   │ engine.py            │
     │ classify_day  │   │ generate(class,      │
     │ get_state     │   │   state, features,   │
     └───────────────┘   │   tactical)          │
                         └──────────────────────┘
```

## Moduulit

### `src/oura_client.py` — Oura API v2 client

Puhdas I/O-rajapinta ilman sivuvaikutuksia. Hakee MVP-endpointit ja hallinnoi paginoinnin.

**MVP-endpointit:**
- `/v2/usercollection/sleep`
- `/v2/usercollection/daily_readiness`
- `/v2/usercollection/daily_activity`
- `/v2/usercollection/heartrate` — nap-tunnistus (`source == 'rest'`)
- `/v2/usercollection/tag` — manuaalitapahtumat (kofeiini, alkoholi, ateria, nap)

**Tärkeää:**
- Ei kirjoita `data/`-kansioon — kirjoitusvastuu on `pipeline.py`:llä
- `fetch_range()` palauttaa aina kaikki avaimet jokaiselle päivälle (missing-data contract)
- `MAX_PAGES_PER_ENDPOINT = 10` — turvaraja paginointisilmukkaan

**Testaus:** `requests-mock` tai `responses`-kirjasto, ei `tmp_path`-fixturea.

---

### `src/event_manager.py` — manuaalisten tapahtumien loki

Lukee, kirjoittaa ja validoi `data/events.jsonl`-tiedoston.

**Tapahtumatyypit:** `caffeine`, `alcohol`, `meal`, `nap`

**Aikavyöhykelogiikka:**
- Tallennus aina UTC:ssä (`Z`-suffiksi)
- `get_events_for_date()` tulkitsee päivän `config["timezone"]`-asetuksen mukaan (oletus `Europe/Helsinki`)
- `get_events_range(start, end)` ottaa merkkijonot `"YYYY-MM-DD"` — **ei** `datetime`-objekteja
- Jokainen päivä on **aina** palautusrakenteessa, vaikka lista olisi tyhjä

**Testaus:** `tmp_path`-fixture, ei oikeaa `data/`-kansiota.

---

### `src/features.py` — derived-muuttujat

Laskee kaikki `derived`-nimiavaruuden muuttujat Oura-raakadatasta ja event_manager-tapahtumista.

**Nimiavaruudet:**
- `derived.*` — skillin laskema (esim. `hrv_delta_pct`, `caffeine_sleep_gap`)
- `oura.*` — Ouran natiivit scorerit (esim. `readiness_score`, `recovery_index`)
- `raw.*` — kaikki muut API-kentät

Katso täydellinen feature-schema: [tiketti #2](https://github.com/jaakkokorhonen/weekly-cycle-oura-skill/issues/2).

---

### `src/rule_engine.py` — luokittelu ja tilakone

Puhdas, taulupohjainen rule engine ilman API-kutsuja.

**Funktiot:**

```python
classify_day(features: dict) -> Literal["HIGH_LOAD_DAY", "INTEGRATION_DAY", "BASELINE_DAY"]
get_state(history: list[DayRecord]) -> Literal["Expansion", "Reset Confirmed", "Incomplete Reset", "Neutral"]
get_tactical_suggestion(features: dict) -> str | None
```

**Luokittelusäännöt:**

| Luokka | Ehdot |
|---|---|
| `HIGH_LOAD_DAY` | `active_kcal >= high_load_kcal_hard` TAI `active_kcal >= high_load_kcal_soft AND hrv_delta_pct <= high_load_hrv_delta` |
| `INTEGRATION_DAY` | `active_kcal < 500 AND hrv_delta >= 0 AND deep_sleep_vs_30d > 0 AND rhr_vs_30d < 0` |
| `BASELINE_DAY` | kaikki muut tapaukset |

**Tilakoneen tilat:**

| Tila | Ehto |
|---|---|
| `Expansion` | Edellinen päivä HIGH_LOAD_DAY + HRV ei vielä palautunut |
| `Reset Confirmed` | HRV noussut baselineen HIGH_LOAD_DAYn jälkeen |
| `Incomplete Reset` | HRV alle baseline ≥ 3 peräkkäistä päivää |
| `Neutral` | Muut tapaukset |

**Insufficient evidence -sääntö:** Engine ei muuta kapasiteettiarviota yksittäisen yön poikkeaman perusteella. Muutos vasta ≥ 3 peräkkäistä yötä samaan suuntaan.

Kaikki kynnykset `config["thresholds"]`-aliavaimista — ei hardkoodattu.

---

### `src/recommendation_engine.py` — taktinen tekstigeneraattori

Generoi lyhyet, taktiset suositustekstit 3×4 kombinaatiomatriisista.

**Paluuarvo:** enintään 3 virkettä sisältävä merkkijono.

**Kombinaatiomatriisi:** 3 luokkaa × 4 tilaa = 12 tekstimallia + 3 taktista lisäystä.

Ei LLM-kutsuja — kaikki tekstit staattisia malleja. Toimii offline.

Katso täydellinen matriisi: [tiketti #30](https://github.com/jaakkokorhonen/weekly-cycle-oura-skill/issues/30).

---

### `src/pipeline.py` — pääorkestroija

Yhdistää kaikki moduulit ja kirjoittaa `data/records/YYYY-MM-DD.json`.

**Askeleet järjestyksessä:**
1. Fetch: `OuraClient.fetch_range()` + `EventManager.get_events_range()`
2. Write raw: `_write_raw(raw, raw_dir)` — pipeline.py:n oma funktio
3. Normalize + Enrich
4. Compute features (`features.py`)
5. Baseline (14d HRV-mediaani, 30d RHR-mediaani)
6. Classify: `rule_engine.classify_day()` + `rule_engine.get_state()`
7. Recommend: `recommendation_engine.generate()`
8. Write record: atominen kirjoitus (temp → rename)

**MVP-stubs** (palautetaan vakioarvo, toteutetaan post-MVP):
- `segment_sleep_night()` → aina `"monophasic"`
- `detect_work_block()` → aina `None`

**Tietueformaatti:**
```json
{
  "date": "2026-07-18",
  "raw": {
    "sleep": {},
    "readiness": {"score": 78, "temperature_deviation": 0.0},
    "activity": {"active_calories": 198},
    "heartrate": []
  },
  "derived": {
    "hrv_delta_pct": -0.08,
    "caffeine_sleep_gap": 9.5,
    "recovery_cost": 0.12,
    "sleep_mode": "monophasic"
  },
  "oura": {},
  "events": [],
  "classification": "BASELINE_DAY",
  "load_state": "Neutral",
  "recommendation": "...",
  "triggered_rule": "...",
  "feature_engine_version": "1",
  "partial_baseline": false
}
```

> **MVP-huomio:** `oura`-lohko on MVP:ssä tyhjä `{}`. `readiness_score` ja `recovery_index` lisätään post-MVP:ssä (#28).

**Ensikäynnistys:** Pipeline hakee automaattisesti 30 päivää historiadataa baseline-bootstrappingia varten.

---

### `src/mcp_server.py` — MCP-rajapinta

Altistaa skillin toiminnot AI-assistenteille MCP-protokollan kautta. Käyttää `mcp`-kirjastoa (`mcp>=1.0`).

**MVP-työkalut:**

| Työkalunimi | Kuvaus |
|---|---|
| `run_pipeline(date?)` | Hae Oura-data, laske piirteet, palauta suositus |
| `log_event(type, amount?, unit?, note)` | Kirjaa manuaalinen tapahtuma |
| `get_daily_report(date?)` | Palauta tallennettu tietue — ei API-kutsua |
| `get_status()` | Palauta viimeisin kuormitustila nopeasti |

**Käynnistys:**
```bash
uv run python src/mcp_server.py
# tai pyproject.toml-skriptillä:
uv run weekly-cycle-mcp
```

**Transport:** stdio — jokainen asiakas käynnistää oman prosessin, ei porttikonflikteja.

## Datavirta

```
Oura API v2
    │
    ▼ fetch_range()
oura_client.py
    │  palauttaa: {"sleep": [], "daily_readiness": dict|None, ...}
    │
    ▼ _write_raw()
pipeline.py  ──────────────────────────────── data/raw/YYYY-MM-DD.json
    │
    ▼ get_events_range()
event_manager.py
    │  lukee: data/events.jsonl
    │
    ▼ compute_features()
features.py
    │  tuottaa: derived.hrv_delta_pct, derived.caffeine_sleep_gap, ...
    │
    ▼ classify_day() + get_state()
rule_engine.py
    │  palauttaa: "BASELINE_DAY", "Neutral"
    │
    ▼ generate()
recommendation_engine.py
    │  palauttaa: "Baseline range. No special action indicated."
    │
    ▼ _write_record()
pipeline.py  ──────────────────────────────── data/records/YYYY-MM-DD.json
```

## Hakemistorakenne

```
weekly-cycle-oura-skill/
├── config.yaml.example     # versionhallinnassa — kopioi config.yaml:ksi
├── config.yaml             # gitignore:ssa — sisältää oikean tokenin
├── pyproject.toml
├── README.md
├── CONTRIBUTING.md
├── ARCHITECTURE.md         # tämä tiedosto
├── DESIGN.md
├── OURA-API-DECISIONS.md
├── src/
│   ├── oura_client.py
│   ├── event_manager.py
│   ├── features.py
│   ├── rule_engine.py
│   ├── recommendation_engine.py
│   ├── pipeline.py
│   └── mcp_server.py
├── tests/
│   ├── unit/
│   │   ├── conftest.py
│   │   ├── test_oura_client.py
│   │   ├── test_event_manager.py
│   │   ├── test_pipeline.py
│   │   ├── test_rule_engine.py
│   │   ├── test_features.py
│   │   ├── test_rec_engine.py
│   │   └── test_mcp_server.py
│   └── post_mvp/
│       └── test_cli.py
└── data/
    ├── events.jsonl        # gitignore:ssa
    ├── raw/                # gitignore:ssa
    └── records/            # gitignore:ssa
```

## Post-MVP laajennukset

Seuraavat moduulit on siirretty post-MVP-vaiheeseen:

- `src/cli.py` (#32) — komentorivisrajapinta
- `src/experiment_manager.py` (#31) — N-of-1-kokeilujen orkestroija
- `segment_sleep_night()` — täysi bifaasinen unisegmentointi
- `detect_work_block()` — työjakson tunnistus
- `analyze_experiment()` MCP-työkalu — lisätään `mcp_server.py`:hen tiketti #31:n yhteydessä
