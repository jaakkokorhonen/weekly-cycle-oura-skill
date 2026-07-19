# Weekly Cycle Oura Skill — Design

## Tausta

Tämä skill on suunniteltu seuraamaan viikkotasolla hyvinvointia, suorituskykykapasiteettia ja unta tavalla, joka ei oleta yhden yhtenäisen, maksimoidun yöunen olevan aina paras mahdollinen tavoitetila. Lähtökohta on, että uni, palautuminen, työkuorma, kofeiini, alkoholi, ruokailu ja viikonloppujen rytmi muodostavat yhdessä syklisen järjestelmän, jonka tehtävä on mahdollistaa elämä, työ, kokeilu ja toipuminen eikä vain optimoida yksittäistä uniscorea.

Skill käyttää Oura-datan tarjoamaa fysiologista mittauspohjaa, mutta lisää sen päälle oman logiikkakerroksen, joka arvioi ilmiöitä viikko- eikä vain vuorokausitasolla, sekä testaa hypoteeseja yksi muuttuja kerrallaan N-of-1-menetelmällä. Tavoitteena ei ole tuottaa universaaleja sääntöjä, vaan luoda järjestelmä, jolla käyttäjä voi empiirisesti selvittää, mikä rytmi tukee parhaiten juuri hänen omaa hyvinvointiaan ja suorituskykyään.

## Tavoite

Skillin päätavoite on yhdistää kolme näkökulmaa samaan analyysiin: hyvinvointi, suorituskykykapasiteetti ja uni. Hyvinvointi tarkoittaa tässä viikkotason palautumista ja kuormituksen hallintaa; suorituskykykapasiteetti tarkoittaa kykyä tehdä yksi pitkä, selkeä työjakso tai aktiivinen viikonloppujakso ilman että järjestelmä romahtaa; uni taas nähdään järjestelmän säätömuuttujana, ei itseisarvona.

Käytännössä skill pyrkii vastaamaan kysymyksiin kuten: miten kofeiinin ajoitus vaikuttaa työjakson laatuun ja yöuneen, miten alkoholi muuttaa nukahtamista ja palautumista, miten viikonlopun aktiivisuus ja sunnuntain korvausuni näkyvät maanantain readinessissä, ja milloin lyhyt päiväuni toimii korjausliikkeenä eikä häiriönä.

## Oura-pohja

Skill nojaa Ouran tarjoamiin perusmittareihin, joita käytetään raakadatan lähteinä eikä lopullisina totuuksina. Olennaiset Oura-pohjaiset tietolähteet ovat yöuni, päiväunet, HRV, leposyke, readiness-score, aktiivisuuskuorma, aktiivisuusaika, mahdolliset tagit sekä ajallinen rakenne, josta voidaan johtaa rytmin jaksot.

Oura toimii tässä järjestelmässä fysiologisen kerroksen mittarina: se kertoo, mitä kehossa on tapahtunut. Skillin lisälogiikka taas pyrkii tulkitsemaan, miksi näin tapahtui ja mihin viikkorakenteen osaan muutos liittyy. Tämä ero on tärkeä, koska sama yödata voi tarkoittaa eri asioita riippuen siitä, oliko edeltävä päivä normaali arkipäivä, lauantain aktiivinen jakso vai sunnuntain palautusjakso.

## Data

Skillin data jaetaan viiteen pääluokkaan: unidata, palautumisdata, aktiivisuusdata, käyttäjän tapahtumadata ja johdettu sykli-data. Unidataan kuuluvat pääunijakson kesto, nukahtamisviive, heräämisten määrä, univaiheiden jakauma sekä päiväunet. Palautumisdataan kuuluvat readiness-score, yöaikainen HRV, leposyke ja mahdollinen lämpötilapoikkeama. Aktiivisuusdataan kuuluvat päivittäinen kuorma, askeleet, aktiivisuusminuutit ja harjoitusvaikutukset. Käyttäjän tapahtumadataan kuuluvat manuaalisesti kirjatut kofeiini-, alkoholi-, ateria- ja juomataukotapahtumat. Johdettu sykli-data koostuu skillin laskemista jaksoista kuten työjakso, iltajakso, ensimmäinen unijakso, toinen unijakso, lauantain aktiivisuusikkuna ja sunnuntain palautusikkuna.

Tämä viimeinen luokka on skillin varsinainen lisäarvo: se ei vain lue mittareita, vaan rakentaa niistä mallin viikon rytmistä. Ilman tätä kerrosta Oura jää helposti päiväkohtaiseksi numeronäytöksi; tämän mallin avulla datasta tulee hypoteeseja testaava aikarakenteinen järjestelmä.

## Tekniikka

Teknisesti skill toimii tapahtumavetoisena analyysikerroksena, joka lukee Oura-datan päivä- ja viikkotasolla, normalisoi sen, rikastaa sen johdetuilla muuttujilla ja suorittaa analyysifunktioita jokaisen päivän sekä viikon lopussa. Järjestelmä voidaan ajatella neljänä putkena: ingest, normalisointi, rikastus, analyysi.

### Kehitysympäristö ja riippuvuudet

Projektissa käytetään yksinomaan **uv**-työkalua virtuaaliympäristön (virtualenv) luomiseen sekä kaikkien riippuvuuksien (kuten `pytest`, `responses`, `click`/`argparse`) hallintaan. Tämä takaa nopean ja yhdenmukaisen suoritusympäristön testaukselle ja ajolle.

### 1. Ingest

Ingest-vaiheessa haetaan Ourasta tai integroiduista lokilähteistä seuraavat tapahtumat:

- `sleep_session`
- `nap_session`
- `readiness_snapshot`
- `activity_summary`
- `hrv_series`
- `resting_heart_rate_series`
- `tag_event`
- `manual_event`

`manual_event` on välttämätön lisä, koska Oura ei yksin tiedä, milloin käyttäjä joi kahvia, alkoholia, vettä tai söi päivän lämpimän aterian. Tämän vuoksi skillin käyttö edellyttää kevyttä käyttäjän omaa tapahtumakirjausta tai integraatiota muuhun päiväkirjaan.

### 2. Normalisointi

Normalisointivaihe muuntaa eri lähteistä tulevan datan yhdeksi aikajärjestetyksi tapahtumasarjaksi. Aikavyöhykkeiden käsittelyssä säilytetään tapahtumien alkuperäiset aikavyöhykkeiden offset-tiedot (esim. `+03:00` tai `Z`) eikä niitä pakoteta UTC-muotoon, mikä helpottaa ilta- ja yörajojen hahmottamista laskentalogiikassa.

Tässä vaiheessa kaikki tapahtumat saavat ainakin seuraavat kentät:

- `timestamp_start`
- `timestamp_end`
- `event_type`
- `source`
- `value`
- `unit`
- `confidence`

Normalisointi mahdollistaa sen, että esimerkiksi alkoholitapahtuma, Oura-yöuni ja lämmin ateria voidaan käsitellä saman ajallisen mallin sisällä. Lisäksi tässä vaiheessa tehdään päivä- ja viikkorajat paikallisen aikavyöhykkeen mukaan, jotta lauantai–sunnuntai-sykli voidaan tunnistaa oikein.

### 3. Rikastusfunktiot

Rikastusvaiheessa raakadatasta lasketaan johdetut muuttujat, joita tarvitaan varsinaiseen analyysiin. Keskeiset funktiot ovat:

#### `detect_work_block(day_events)` *(post-MVP — #32)*

Tunnistaa päivän yhden pääasiallisen hereilläolon työjakson aktiivisuus- ja käyttäjätapahtumien perusteella. Funktio hyödyntää aktiivisuuden tiheyttä, mahdollisia fokustageja ja pitkien inaktiivisuusjaksojen puuttumista. Tulos on:

- `work_block_start`
- `work_block_end`
- `work_block_duration`
- `work_block_integrity_score`

**MVP-stub:** palauttaa aina `None` — ei kaada pipelinea.

#### `detect_main_meal(day_events)` *(post-MVP)*

Paikantaa päivän pääaterian, joko manuaalisesta merkinnästä tai ajallisesta heuristiikasta. Tulos:

- `main_meal_time`
- `main_meal_type` (`weekday_dinner` / `weekend_supper`)
- `meal_to_sleep_gap`

Tätä käytetään arvioimaan, miten ruokailun ajoitus liittyy nukahtamiseen ja yöheräilyyn.

#### `compute_caffeine_window(day_events, sleep_sessions)` *(MVP)*

Laskee viimeisen kofeiinitapahtuman ja pääunijakson alun välisen ajan sekä mahdolliset annostasot. Tulos:

- `last_caffeine_time`
- `caffeine_sleep_gap_hours`
- `caffeine_total_mg_estimate`

Tämä funktio perustuu tietoon siitä, että kofeiinin huippuvaikutus syntyy noin 30–45 minuutissa ja puoliintumisaika on noin 4–7 tuntia.

#### `compute_alcohol_window(day_events, sleep_sessions)` *(MVP)*

Laskee alkoholin ajoituksen suhteessa nukahtamiseen ja yön rakenteeseen. Tulos:

- `last_alcohol_time`
- `alcohol_sleep_gap_hours`
- `alcohol_total_units`
- `alcohol_flag_before_first_sleep`

Tätä käytetään mallintamaan tilannetta, jossa alkoholi toimii mahdollisena ensimmäisen unijakson käynnistäjänä mutta samalla näkyy HRV:n ja univaiheiden muutoksina.

#### `segment_sleep_night(sleep_session)` *(post-MVP)*

Jakaa yön yhteen tai kahteen unijaksoon sen perusteella, onko pääunen keskellä riittävän pitkä valveikkuna. Tulos:

- `sleep_mode` (`monophasic` / `biphasic`)
- `first_sleep_duration`
- `mid_wake_duration`
- `second_sleep_duration`

**MVP-stub:** palauttaa aina `("monophasic", 0)` — ei kaada pipelinea.

#### `compute_recovery_cost(day_data)` *(MVP)*

Arvioi päivän fysiologisen hinnan yhdistämällä seuraavat tekijät:

- HRV-poikkeama baselineen
- leposykkeen poikkeama baselineen
- unen katkonaisuus
- alkoholi- ja kofeiini-ikkunat
- aktiivisuuskuorma

Tulos:

- `recovery_cost_score`
- `recovery_cost_components`

Tämä funktio on tärkeä, koska se ei oleta kaikkien poikkeamien olevan automaattisesti huonoja, vaan auttaa kysymään: oliko fysiologinen hinta suhteessa siihen, mitä päivän aktiivinen jakso mahdollisti?

#### `compute_capacity_signal(week_data)` *(post-MVP)*

Tuottaa viikkotason arvion suorituskykykapasiteetista. Se ei mittaa pelkästään palautumista vaan kykyä kantaa kuormaa viikon rakenteessa. Tulos:

- `capacity_signal`
- `capacity_vs_recovery_balance`
- `monday_recovery_after_weekend`

Tässä funktiossa lauantain aktiivisuus ja sunnuntain palautuminen ovat erityisen tärkeitä, koska tutkimus tukee kohtuullisen viikonlopun korvausunen hyötyä arkiunivajeen yhteydessä.

## Analyysifunktiot

Varsinaiset analyysit tehdään päivittäisillä ja viikoittaisilla funktioilla.

### Päivittäiset analyysit

#### `analyze_day_structure(day_data)`

Tuottaa narratiivisen yhteenvedon siitä, toteutuiko yksi työjakso, miten juomatauot sijoittuivat, milloin pääateria oli ja miten ilta siirtyi kohti unta.

#### `analyze_sleep_transition(day_data)`

Arvioi, miten päivän kofeiini, alkoholi, ateria ja mahdollinen päiväuni näkyivät nukahtamisessa, ensimmäisessä unijaksossa, väliheräämisessä ja toisessa unijaksossa.

#### `analyze_recovery_vs_output(day_data)`

Vertaa saman päivän aktiivisuuskuormaa ja seuraavan yön palautumista. Tällä vältetään yksipuolinen ajattelu, jossa vain palautuminen olisi tärkeää.

### Viikoittaiset analyysit

#### `analyze_week_cycle(week_data)`

Tunnistaa viikon rytmin: olivatko arkipäivät vakaita, kasaantuiko kuormitus lauantaille ja palautuminen sunnuntaille, ja miten tämä näkyi maanantain lähtötilanteessa.

#### `compare_to_baseline(current_week, baseline_week)`

Vertaa kokeiluviikkoa baselineen yhden hypoteesin osalta. Tämä on N-of-1-menetelmän ydin: esimerkiksi siirtyikö viimeinen kofeiini aiemmaksi, ja muuttuiko nukahtamisviive tai HRV tämän seurauksena.

#### `score_experiment_outcome(experiment_block)`

Laskee kokeen lopputuloksen usean mittarin perusteella:

- unimuuttujat
- palautumismuuttujat
- kapasiteettimuuttujat
- käyttäjän oma subjektiivinen arvio

Tämä estää sen, että yksi mittari kuten readiness tai sleep score dominoisi kaikkea tulkintaa.

## Lisättävä logiikka verrattuna Ouraan

Ouran oma logiikka on hyödyllinen fysiologisen tilan mittaamisessa, mutta tähän skilliin lisätään useita tasoja, joita Oura ei käsittele riittävästi:

1. **Viikkotason sykliikka**: Oura tarkastelee usein yötä ja päivää yksikköinä. Tämä skill tarkastelee laajemmin viikon rytmiä, erityisesti lauantain aktiivista ja sunnuntain palauttavaa vaihetta.
2. **Yhden työjakson logiikka**: Oura ei mallinna työn rakennetta, mutta tämän skillin keskeinen hypoteesi perustuu siihen, että yksi selkeä työjakso voi olla fysiologisesti ja käytännöllisesti realistisempi kuin useat intensiiviset blokit.
3. **Kahden unen mahdollisuus**: Oura tulkitsee väliheräämisen lähinnä katkoksena; tämä skill sallii sen hypoteesin, että joissain tilanteissa yö jakautuu tarkoituksellisesti kahteen toimivaan unijaksoon.
4. **Tavoitefunktion eriyttäminen**: Oura implikoi usein, että optimaalinen uni on paras päämäärä. Tämä skill erottaa tavoitefunktion datasta: joskus viikon tavoite voi olla suorituskyvyn, sosiaalisuuden tai rajojen kokeilun mahdollistaminen, jolloin palautumishintaa ei automaattisesti tulkita epäonnistumiseksi.
5. **N-of-1-kokeilun hallinta (yksinkertaistettu MVP-tasolla)**: MVP-vaiheessa kokeilujaksoja vertaillaan suoraan CLI-analyysityökalulla annettujen päivämäärävälien perusteella. Muuttujien lukitus ja kokeilun käytännön noudattaminen jätetään käyttäjän manuaalisesti hallinnoitavaksi, ja monimutkaisempi automaattinen tilakoneellinen orkestroija on siirretty post-MVP-vaiheeseen.

## Käyttötapaukset

### 1. Kofeiini-ikkunan optimointi *(MVP)*

Käyttäjä testaa, parantaako kofeiinin rajaaminen aamupäivään verrattuna iltapäiväannokseen nukahtamista ja yöpalautumista. Skill seuraa kofeiini-ikkunaa, nukahtamisviivettä ja HRV:tä.

### 2. Alkoholi ensimmäisen unijakson käynnistäjänä *(MVP)*

Käyttäjä testaa, toimiiko pieni alkoholiannos joissain tilanteissa ensimmäisen unijakson käynnistäjänä ja millä fysiologisella hinnalla. Skill vertailee nukahtamista, väliheräämistä, HRV:tä ja seuraavan päivän kapasiteettia.

### 3. Päiväuni ehdollisena korjausliikkeenä *(MVP — nap-tunnistus stub, täysi logiikka post-MVP)*

Käyttäjä testaa, auttaako 10–20 minuutin päiväuni päivinä, jolloin kokonaisuni on jäänyt lyhyeksi. Skill vertailee seuraavan yön unta ja seuraavan päivän readinessia.

### 4. Yhden työjakson malli *(post-MVP — #32)*

Käyttäjä testaa, tuottaako yksi pitkä työjakso paremman palautumis–kapasiteetti-tasapainon kuin useat pirstaleiset työblokit. Skill käyttää aktiivisuusdataa, palautumista ja omaa työkuvan luokittelua.

### 5. Lauantai–sunnuntai-sykli *(MVP)*

Käyttäjä testaa, tukevatko lauantain aktiivinen jakso ja sunnuntain kohtuullinen korvausuni paremmin koko viikon kapasiteettia kuin tasainen mutta jatkuvasti vajaa unirytmi. Skill seuraa lauantain kuormaa, sunnuntain korvausunta ja maanantain valmiutta.

### 6. Lämmin ateria rytmin ankkurina *(post-MVP — detect_main_meal)*

Käyttäjä testaa, toimiiko päivällinen viikolla tai myöhempi illallinen viikonloppuna vakaana siirtymänä työstä palautumiseen. Skill yhdistää ateria-ajan, yöheräilyt ja nukahtamisen.

## Miksi tämä toimii

Skill toimii, koska se ei yritä arvata yhtä universaalia sääntöä, vaan rakentaa yksilöllisen mallin toistuvista sykleistä ja testaa niitä järjestelmällisesti. Oura tarjoaa tähän hyvän fysiologisen mittauspohjan, mutta vasta viikkotason sykliikka, ajallinen rikastus ja N-of-1-kokeilu tekevät datasta toimintakykyistä tietoa.

Tieteellinen logiikka on yhdistelmä mittausta, hypoteesinmuodostusta, yhden muuttujan kokeita ja viikkotason tulkintaa. Tämä on vahvempi lähestymistapa kuin joko puhdas uniscore-seuranta tai pelkkä intuitiivinen itseseuranta, koska se yhdistää objektiivisen datan ja eksplisiittisen kokeellisen metodin samaan järjestelmään.
