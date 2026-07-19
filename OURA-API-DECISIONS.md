# Oura API v2 — päätökset ja kenttävalinta

Tämä dokumentti kuvaa, mitkä Oura API v2 -endpointit ja kentät valittiin MVP:hen ja miksi.

## MVP-endpointit

| Endpoint | Käyttö |
|---|---|
| `/v2/usercollection/sleep` | Uni, HRV, RHR, univaiheet |
| `/v2/usercollection/daily_readiness` | Haetaan, mutta kenttiä ei käytetä luokitteluun |
| `/v2/usercollection/daily_activity` | Aktiivisuuskalorerit (active_calories) |
| `/v2/usercollection/heartrate` | Sykeaikasarja nap-tunnistukseen (`source == 'rest'`) |

### Miksi `/heartrate` jo MVP:ssä

Nap-tunnistus (`segment_sleep_night()`) on post-MVP, mutta `/heartrate`-data haetaan jo MVP:ssä, koska:
1. Datan keräys retrospektiivisesti on mahdotonta (Oura ei palauta vanhaa dataa jälkikäteen kaikille pyynnöille)
2. Heartrate-data tarvitaan baseline-bootstrappingin yhteydessä 30 päivän historiadataan
3. Päiväunien havaitseminen `source == 'rest'` -suodatuksella on yksinkertainen taktinen lisä

### Miksi `/workout` ei ole MVP:ssä

`/workout`-endpoint lisätään post-MVP:ssä harjoituspäivien tunnistamiseen. MVP käyttää `active_calories`-arvoa riittävänä HIGH_LOAD_DAY-signaalina.

### Miksi `/tag` ei ole MVP:ssä

Ouran tagit ovat epäluotettavia (käyttäjän kirjaus vaihtelee). Kaikki manuaalinen tapahtumakirjaus tapahtuu `event_manager.py`:n kautta `events.jsonl`-tiedostoon.

## Kenttävalinta per endpoint

### `/v2/usercollection/sleep`

```json
{
  "id": "...",
  "day": "2026-07-18",
  "type": "long_sleep",
  "bedtime_start": "2026-07-17T22:45:00+03:00",
  "bedtime_end": "2026-07-18T06:30:00+03:00",
  "total_sleep_duration": 27300,
  "time_in_bed": 31500,
  "average_hrv": 28,
  "average_heart_rate": 52,
  "deep_sleep_duration": 4800,
  "rem_sleep_duration": 6000,
  "light_sleep_duration": 16500
}
```

**Käytetyt kentät MVP:ssä:**
- `type` — suodatus: `long_sleep`, `short_sleep`, `rest`
- `bedtime_start` / `bedtime_end` — nukahtamisajankohta kofeiini/alkoholi-ikkunan laskentaan
- `total_sleep_duration` — taktinen nap-suositus (`< 6.5 h → nap`)
- `average_hrv` — HRV-baseline-laskenta (14d mediaani)
- `average_heart_rate` — RHR-baseline-laskenta (30d mediaani)
- `deep_sleep_duration` — INTEGRATION_DAY-ehto (`deep_sleep_vs_30d > 0`)

**Ei käytetä MVP:ssä:** `latency`, `restless_periods`, `sleep_phase_5_min`

### `/v2/usercollection/daily_readiness`

```json
{
  "id": "...",
  "day": "2026-07-18",
  "score": 78,
  "hrv_balance_status": "good",
  "contributors": {
    "hrv_balance": 80,
    "resting_heart_rate": 85
  }
}
```

**Käytetyt kentät MVP:ssä:** —

> **MVP-päätös (2026-07-19):** `daily_readiness`-endpoint haetaan ja tallennetaan `raw`-nimiavaruuteen, mutta **yhtään kenttää ei käytetä luokitteluun eikä rikastukseen MVP:ssä.**
>
> - `score` (`oura.readiness_score`) — poistettu MVP-scopesta. Tallennetaan `raw`:iin läpinäkyvyyttä varten, mutta `rule_engine.py` ei lue sitä.
> - `contributors.hrv_balance` — poistettu MVP-scopesta. HRV-trendisignaali lasketaan `sleep.average_hrv`-pohjaisesta 14d-mediaanista (`derived_hrv_delta_pct`), ei Ouran omasta `hrv_balance`-luvusta.
>
> **Rationale:** MVP:n luokittelu perustuu yksinomaan `derived.*`-nimiavaruuteen. Kaksi lähdettä samalle signaalille (Ouran `hrv_balance` ja oma `derived_hrv_delta_pct`) aiheuttaisivat ristiriidan säännöissä ja monimutkaistuisivat testit. Post-MVP:ssä `hrv_balance_status` voidaan lisätä `rule_engine`:en lisäehtona tai `recommendation_engine`:en selitystekstiin.

**Ei käytetä MVP:ssä:** `score`, `hrv_balance_status`, `contributors.*`

### `/v2/usercollection/daily_activity`

```json
{
  "id": "...",
  "day": "2026-07-18",
  "active_calories": 198,
  "total_calories": 2350,
  "steps": 8200,
  "equivalent_walking_distance": 6100
}
```

**Käytetyt kentät MVP:ssä:**
- `active_calories` → `derived_active_kcal` — HIGH_LOAD_DAY-luokittelun pääsignaali

**Ei käytetä MVP:ssä:** `steps`, `equivalent_walking_distance`, `met` (post-MVP)

### `/v2/usercollection/heartrate`

```json
{"timestamp": "2026-07-18T13:45:00+03:00", "bpm": 58, "source": "rest"}
{"timestamp": "2026-07-18T14:15:00+03:00", "bpm": 62, "source": "awake"}
```

**Käytetyt kentät MVP:ssä:**
- `timestamp` — päivän derivointi (`ts[:10]`)
- `bpm` — sykearvo
- `source` — suodatus: `rest` = mahdollinen päiväuni tai lepo

## Missing-data contract

`oura_client.fetch_range()` takaa, että jokainen päivä sisältää kaikki avaimet:

| Endpoint | Puuttuva data | Paluuarvo |
|---|---|---|
| `sleep` | Ei unta päivälle | `[]` |
| `daily_readiness` | Ei tietuetta | `None` |
| `daily_activity` | Ei tietuetta | `None` |
| `heartrate` | Ei mittauksia | `[]` |

`pipeline.py` ei tee `dict.get()`-tarkistuksia — client takaa rakenteen.

## Nimiavaruuskäytäntö

```
derived.*   — skillin laskema (esim. derived_hrv_delta_pct)
oura.*      — Ouran natiivit scorerit (esim. oura_readiness_score)
raw.*       — API:n muut alkuperäiskentät
```

Luokittelusäännöt ja testit käyttävät **ainoastaan** `derived.*`-muuttujia. Tämä eristää logiikan Ouran mahdollisista API-muutoksista.

## Baseline-laskenta

| Baseline | Ikkuna | Lähdekenttä | Käyttö |
|---|---|---|---|
| HRV-baseline | 14 päivää | `sleep.average_hrv` | `derived_hrv_delta_pct` |
| RHR-baseline | 30 päivää | `sleep.average_heart_rate` | `derived_rhr_vs_30d` |
| Deep sleep -baseline | 30 päivää | `sleep.deep_sleep_duration` | `derived_deep_sleep_vs_30d` |

**Ensikäynnistys:** Pipeline hakee 30 päivää historiadataa baseline-bootstrappingia varten.

**Partial baseline:** Kun historiaa on alle `min_data_points` (oletus: 5), tietueeseen merkitään `partial_baseline: true` ja `rule_engine` palauttaa `"Neutral"` tilakoneesta — ei `"Incomplete Reset"`-päätöstä.

## Pagination

```python
MAX_PAGES_PER_ENDPOINT = 10  # turvaraja — estää syklisen kursorin jumiuttamasta MCP-palvelinta
```

Paginointi toteutetaan `next_token`-parametrilla. Kukin endpoint sivutetaan erikseen.
