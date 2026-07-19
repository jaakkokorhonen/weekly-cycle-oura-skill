# Weekly Cycle Oura Skill

## Arkkitehtuuri

[![Architecture](https://img.shields.io/badge/docs-Architecture%20Document-01696f?style=flat-square&logo=github)](https://jaakkokorhonen.github.io/weekly-cycle-oura-skill/architecture.html)

Interaktiivinen data-pipeline-dokumentti dark/light-togglella:

- [Arkkitehtuuridokumentti →](https://jaakkokorhonen.github.io/weekly-cycle-oura-skill/architecture.html)

Dokumentti kattaa:
- 4-vaiheinen pipeline (Ingest → Normalize → Features → Classify)
- `derived_*` vs `oura_*` feature-nimiavaruudet (A/B-koeasetelma)
- Signaalihierarkia: Trend / Tactical / Insufficient evidence
- `data/records/YYYY-MM-DD.json` -tietuerakenne
- Moduulit × Issues -matriisi (MVP vs post-MVP)

---

## Käyttöönotto

### Oura Personal Access Token

Skill hakee datan Oura API v2:sta. Tarvitset Personal Access Tokenin:

1. Kirjaudu [cloud.ouraring.com](https://cloud.ouraring.com) → **Personal Access Tokens** → **Create New Token**
2. Luo projektin juureen `.env`-tiedosto:

```bash
OURA_TOKEN=your_token_here
```

3. `.env` on jo `.gitignore`-listalla — varmista että se pysyy siellä.

Vaihtoehtoisesti voit asettaa muuttujan suoraan shellistä:

```bash
export OURA_TOKEN=your_token_here
```

Koodi lukee tokenin `oura_client.py`:ssä ([tiketti #13](https://github.com/jaakkokorhonen/weekly-cycle-oura-skill/issues/13)) seuraavasti:

```python
import os
from dotenv import load_dotenv

load_dotenv()
OURA_TOKEN = os.environ["OURA_TOKEN"]  # KeyError jos puuttuu — tarkoituksellista
```

> **Huom:** `python-dotenv` lisätään `requirements.txt`:ään kun `oura_client.py` toteutetaan.

---

## Tausta ja tarkoitus

Tämä skill on rakennettu tarpeeseen seurata hyvinvointia, suorituskykykapasiteettia ja unta viikkotasolla siten, että rytmi rakennetaan vahvuuksien ja empiirisen näytön kautta, ei valmiin unihygieniadoktriinin normeista käsin. Lähtökohta on, että uni ei ole itseisarvo, jota tulisi maksimoida jokaisena yksittäisenä yönä, vaan väline, joka mahdollistaa työn tekemisen, rajojen kokeilun ja palautumisen vuorottelun laajemmassa, viikon mittaisessa syklissä.

Tausta-ajattelu perustuu kolmeen havaintoon, jotka on käyty läpi tämän projektin taustakeskusteluissa:

1. Moni yksittäinen unihygieniaohje (esim. "välttää päiväunia", "elä koskaan käytä alkoholia illalla", "nuku yhteinäisesti") on rakennettu implisiittisen normin varaan, jossa tavoitteena on aina maksimoida yhteinäinen, mahdollisimman palauttava uni. Tämä normi ei ole itsessään väärä, mutta se ei ole myöskään ainoa mahdollinen tavoite, ja sen sekoittaminen kuvailevaan dataan johtaa helposti siihen, että konteksti- ja annosriippuvaiset ilmiöt (esim. päiväunet, viikonlopun korvausuni) tulkitaan yksioikoisesti "hyväksi" tai "pahaksi".
2. Historiallinen näyttö (Ekirch, esiteollinen "first sleep / second sleep" -malli) osoittaa, että kahden unijakson rakenne on ollut ihmislajille pitkään normaali, mutta tästä ei seuraa suoraan, että se olisi nykyaikaisessa ympäristössä yliveertainen — tätä ei ole kontrolloidusti testattu [PMC4763365].
3. Kofeiinin, alkoholin, ruokailun ja viikonlopun rytmin vaikutukset uneen ja palautumiseen ovat annos- ja ajoitusriippuvaisia, ja niiden hyöty/haitta-suhde vaihtelee sen mukaan, mikä on kunkin hetken tavoite (työ, kokeilu, palautuminen).

Skillin tarkoitus on tarjota työkalu, jolla näitä ilmiöitä voidaan seurata yksilön omalla datalla (Oura Ring: uni, valmiustila, aktiivisuus, HRV) ja testata systemaattisesti, mikä rytmi toimii juuri tälle käyttäjälle — sen sijaan että nojattaisiin yleisiin, kontekstista irrotettuihin unihygieniasuosituksiin.

## Tieteellinen pohja

Skillin taustalla oleva näyttö on koottu useista, keskenään eri vahvuustasoisista lähteistä, ja niitä käsitellään tässä eksplisiittisesti eri luottamustasoilla sen sijaan, että ne esitettäisiin yhtendä yhteinäisenä doktriinina:

- **Vahva, annosvasteeseen perustuva näyttö**: Kofeiinin vaikutus nukahtamisviiveeseen on osoitettu kontrolloiduissa kokeissa annos- ja ajoitusriippuvaiseksi, puoliintumisajan ollessa noin 4–7 tuntia. Alkoholin annos-vastesuhde palautumiseen (HRV, syvä/REM-uni) on osoitettu suomalaisessa kohorttitutkimuksessa lineaarisesti negatiiviseksi jo pienillä annoksilla.
- **Kohtalainen, suuriin kohortteihin perustuva näyttö**: Viikonlopun korvausuni yli 90 minuuttia on yhdistetty pienempaan sepelvaltimoiden kalkkiutumisriskiin viiden vuoden seurannassa niillä, joiden arkiuni on jäänyt vajaaksi, mutta yli 120 minuutin korvausuni on nuorilla yhdistetty heikompaan subjektiiviseen hyvinvointiin — ilmiö on kynnysarvoinen ja ehdollinen, ei monotoninen.
- **Kohtalainen, mekanistinen mutta osin puutteellisesti optimoitu näyttö**: Lyhyiden päiväunien (10–20 min) hyöty univajeen paikkaajana on todennettu, mutta tarkkaa kestoa koskeva optimointinäyttö on epäyhteinäistä.
- **Historiallis-antropologinen, ei-kokeellinen näyttö**: Kaksivaiheisen yöunen (first/second sleep) esiintyvyys esiteollisena aikana on hyvin dokumentoitu, mutta sen ylivertaisuutta nykyaikaisessa ympäristössä ei ole osoitettu kontrolloiduissa kokeissa [PMC4763365].

Tämä kerrostettu näyttöpohja on tietoinen valinta: skill ei esitä yhtä "oikeaa" rytmiä, vaan tarjoaa kehyksen, jossa käyttäjä voi itse testata, mikä osa näytöstä pätee hänen omassa elämässään.

## Metodologia: N-of-1-kokeilu

Skillin toiminnallinen ydin on N-of-1-kokeilumenetelmä, jossa yksi käyttäjä on oma koehenkilönsä, ja interventioita testataan systemaattisesti yksi muuttuja kerrallaan verrattuna omaan lähtötasoon. Menetelmä valittiin siksi, että se mahdollistaa kausaalisen päättelyn yksilötasolla ilman, että tarvitaan suurta koehenkilöjoukkoa, ja koska se sopii erityisen hyvin tilanteisiin, joissa väestötason näyttö on ehdollista tai ristiriitaista.

Kokeilun perusrakenne on aina:

1. **Baseline-vaihe** (1–2 viikkoa): mitään parametria ei tarkoituksella muuteta, jotta saadaan yksilöllinen vertailutaso.
2. **Interventiovaihe** (1–2 viikkoa): yhtä muuttujaa muutetaan, kaikki muu pideytään vakiona.
3. **Vertailu**: skill laskee tulosmuuttujien (nukahtamisviive, heräämisten määrä, HRV, readiness-score) erot baseline- ja interventiovaiheiden välillä.
4. **Iterointi**: seuraava muuttuja testataan vasta, kun edellisen vaikutus on arvioitu — päällekkäisiä muutoksia vältetään, jotta kausaalipäätelmä ei sekoitu.

## Miten skill toimii

Skill koostuu erillisistä data-tapahtumia keräävistä osista (skills) ja niitä hyödyntävistä päivittäisistä analyyseistä (use cases):

- **Weekly baseline recorder**: kerää Ouran Sleep-, Readiness- ja Activity-datan ja muodostaa yksilöllisen lähtötason.
- **One-work-block day classifier**: tunnistaa, toteutuuko päivässä yksi selkeä hereilläolon työjakso vai useampi.
- **Meal anchor detector**: paikantaa päivän pääaterian ajankohdan ja sen etäisyyden unijaksoon.
- **Caffeine & alcohol window tracker**: laskee kofeiinin ja alkoholin ajoituksen etäisyyden unijaksoon ja yhdistää sen HRV- ja nukahtamisdataan.
- **Weekend cycle classifier**: luokittelee lauantain aktiivisuuden ja sunnuntain korvausunen suhteessa arkiviikon baselineihin.

## Ouran unihygienialogiikan kritiikki

Tämän skillin suunnittelua motivoi eksplisiittinen kritiikki siitä, miten kaupalliset uniseurantasovellukset — Oura mukaan lukien — yleensä kehystävät unidataa. Kritiikki jakautuu kolmeen tasoon:

### 1. Implisiittinen normi esitetään neutraalina mittarina

Oura ja vastaavat palvelut laskevat "readiness"- ja "sleep score" -lukuja, jotka perustuvat oletukseen, että paras mahdollinen tila on yksi yhteinäinen, mahdollisimman pitkä ja katkeamaton uni. Tämä on normatiivinen valinta, ei neutraali mitta — se olettaa, että unen tehtävä on itsessään maksimoitava suure, ei väline muun elämän (työ, sosiaalisuus, rajojen kokeilu) mahdollistamiseksi.

### 2. Annosvasteen ja kynnysarvojen sekoittaminen blanket-suosituksiin

Empiirinen tutkimus osoittaa toistuvasti käänteisen U:n muotoisia, ehdollisia vaikutuksia: kohtuullinen korvausuni suojaa, liiallinen ei. Kaupalliset unisovellusten tulkinnat taipuvat usein yksinkertaistamaan tämän muotoon "välttää poikkeamia normaalista unirytmistä", mikä hukkaa juuri sen tiedon, että ehdollisuus ratkaisee, ei poikkeama itsessään.

### 3. Käyttäytymisprotokolla vahvistaa doktriinia mittausasetelmassa

Kun unen laaduta mitataan tilanteessa, jossa käyttäjää on ohjeistettu pysymään sängysä ja yrittämään nukahtaa heti heräämisen jälkeen, mittaus vahvistaa väistämättä sitä käsitystä, että herääminen keskellä yötä on ongelma.

### Kritiikin looginen rakenne

Tiivistetynä: Ouran ja vastaavien palveluiden tuottama data (syke, HRV, univaiheet) on itsessään luotettavaa ja hyödyllista, mutta sen tulkinta nojaa piilevaan arvopremissiin ("yhteinäinen, maksimoitu uni on aina parempi"), joka ei seuraa suoraan datasta itsestään [Humen periaate: havainnosta ei voida johtaa normia ilman erillistä arvovalintaa]. Tämän skillin tarkoitus on erottaa nämä kaksi tasoa toisistaan.

## Lähteet

Kaikki tässä dokumentissa mainitut väitteet perustuvat aiemmin käytyyn, lähteisiin viittaavaan keskusteluun kofeiinin, alkoholin, päiväunien, kahden unijakson mallin ja viikkosyklin empiirisestä näytöstä. Yksityiskohtaiset viitteet on merkitty tekstin sisään hakasulkeissa kunkin väitteen kohdalle.
