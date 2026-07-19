# Oura API v2 — MVP-päätökset

Tämä tiedosto kokoaa tikettien #14–#21 selvitystyön tulokset. Jokainen ratkaisu on vahvistettu ja tiketti suljettu `completed`-tilaan.

---

## #14 — Unidata ja kenttärakenne

**Endpoint:** `/v2/usercollection/sleep`

| Kenttä | Tyyppi | Käyttö MVP:ssä |
|---|---|---|
| `type` | string | `long_sleep` / `short_sleep` / `rest` — erottaa yöunen napin |
| `total_sleep_duration` | int (s) | Kokonaisunikesto |
| `rem_sleep_duration` | int (s) | REM-osuus |
| `deep_sleep_duration` | int (s) | Syvän unen osuus |
| `light_sleep_duration` | int (s) | Kevyen unen osuus |
| `sleep_phase_5_min` | list[str] | Hypnogrammi 5 min välein — `segment_sleep_night()`:lle |
| `onset_latency` | int (s) | Nukahtamisviive |
| `efficiency` | float | `total_sleep / time_in_bed * 100` |
| `awake_time` | int (s) | Hereilläoloaika yön aikana |
| `bedtime_start` | ISO 8601 | UTC-muunnos tehdään `pipeline.py`:ssä eksplisiittisesti |
| `bedtime_end` | ISO 8601 | |

**Biphasic-tunnistus:** `sleep_phase_5_min` -aikasarjassa > 30–60 min `Awake`-jakso kahden univaihejakson välissä → `sleep_mode: biphasic`.

---

## #15 — HRV-sarjan rakenne

**Endpoint:** `/v2/usercollection/sleep`

| Kenttä | Käyttö |
|---|---|
| `average_hrv` | MVP: yökohtainen RMSSD (ms) |
| `hrv` (list) | Post-MVP: 5 min aikasarja |

**Baseline:** Lasketaan itse `pipeline.py`:ssä. Liukuva 14 vrk:n mediaani.

```python
derived_hrv_delta_pct = (avg_hrv - baseline_14d_median) / baseline_14d_median
```

**Huomio:** `hrv_balance` `daily_readiness`-objektissa on Ouran oma suhteellinen arvo — baseline-metodia ei ole julkaistu. Älä käytä yksinään.

---

## #16 — Readiness-objektin rakenne

**Endpoint:** `/v2/usercollection/daily_readiness`

| Kenttä | Käyttö |
|---|---|
| `score` | `oura_readiness_score` — tallennetaan `raw_inputs`-namespaceen |
| `hrv_balance` | Ouran oma baseline-poikkeama, vain vertailuun |
| `recovery_index` | Saatavilla suoraan |
| `activity_balance` | Ouran versio `derived_days_since_last_high_load`:sta — post-MVP A/B |
| `temperature_deviation` | Saatavilla kentänä — käyttö post-MVP (#23) |

**MVP-ratkaisu:** `oura_readiness_score` tallennetaan, mutta se ei ohjaa rule engineä suoraan — vain verrokkidata.

---

## #17 — Aktiivisuusdata ja MET-arvot

**Endpoint:** `/v2/usercollection/daily_activity`

| Kenttä | Käyttö |
|---|---|
| `active_calories` | `derived_active_kcal` — MVP:n päälaskuri |
| `high_activity_time` | Ouran luokittelu, kynnys ~MET > 3 |
| `medium_activity_time` | Taustatieto |
| `steps` | Taustatieto |
| `met` (list) | Post-MVP: 5 min MET-aikasarja |

**`HIGH_LOAD_DAY`-tunnistus MVP:ssä:**
```python
active_calories >= 1000
# TAI
active_calories >= 800 and hrv_delta_pct <= -0.15
```

**Workout-endpoint** (`/v2/usercollection/workout`): Post-MVP.

---

## #19 — Päiväunien tunnistus

**Endpoint:** `/v2/usercollection/sleep` (sama kuin yöuni)

**Tunnistuslogiikka:**
1. `sleep.type in ["short_sleep", "rest"]` → päiväuni
2. Jos ei automaattitunnistusta: `heartrate.source == "rest"` -jakso jossa `steps == 0` ja kesto > 15–20 min → `unclassified_rest`
3. Manuaalinen fallback: `events.jsonl`-lokiin kirjattu `nap_session`

**Univaiheja** ei universaalisti saatavilla lyhyille napeille.

---

## #20 — Historiallinen data ja paginointi

**Kaikki endpointit:** tukevat `start_date` / `end_date` -parametreja.

**Paginointi:** `next_token` -kursori.

**MVP-haku `oura_client.py`:ssä:**
```python
# 1. Baseline-ikkuna ensin (30 vrk taaksepäin)
# 2. 7–14 vrk:n erät — throttling-suoja
# 3. Inkrementaalinen päivittäinen päivitys
```

**Datan valmistuminen:** tyypillisesti aamulla (ei realtimea). Cron-ajo tai manuaalinen trigger riittää MVP:ssä.

---

## #21 — Leposyke

**Endpoint:** `/v2/usercollection/sleep`

| Kenttä | Käyttö |
|---|---|
| `lowest_heart_rate` | MVP: yön minimi — päälaskuri |
| `average_heart_rate` | Taustatieto |

**Baseline:** Liukuva 30 vrk mediaani `pipeline.py`:ssä.

```python
derived_rhr_delta = lowest_heart_rate - baseline_30d_median
```

**Bonus:** `heartrate.source == "rest"` hereilläoloaikana = hiljainen palautumisjakso (linkki #19-logiikkaan).

---

## Tikettien tila

| Tiketti | Aihe | Tila |
|---|---|---|
| #14 | Sleep-kentät | ✅ Suljettu 2026-07-19 |
| #15 | HRV | ✅ Suljettu 2026-07-19 |
| #16 | Readiness | ✅ Suljettu 2026-07-19 |
| #17 | Aktiivisuus | ✅ Suljettu 2026-07-19 |
| #18 | Tagit | ⏳ Post-MVP |
| #19 | Päiväunet | ✅ Suljettu 2026-07-19 |
| #20 | Historiadatan haku | ✅ Suljettu 2026-07-19 |
| #21 | Leposyke | ✅ Suljettu 2026-07-19 |
| #23 | Lämpötilapoikkeama | ⏳ Post-MVP |
