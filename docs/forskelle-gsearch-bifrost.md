<!-- Genereret af tests/tools/forskelle_doc.py ud fra tests/fixtures/forskelle. Ret i tests/tools/forskelle_spec.py, ikke her. -->

# Forskelle mellem GSearch og Bifrost

GSearch lukker i november 2026, og Geosearch DK skifter til Bifrost. Begge tjenester
kommer fra Klimadatastyrelsen. Når GSearch er lukket, kan man ikke længere se, hvad den
svarede. Derfor er de samme søgestrenge optaget fra begge tjenester på samme tid, og
svarene er gemt. Dokumentet viser, hvor Bifrost svarer anderledes end GSearch, og hvor
Bifrost svarer lige så godt eller bedre.

**Sådan er det optaget.** 71 søgninger (søgestreng, evt. med kommunekoder) er
optaget mellem 2026-11-06T19:48:12+00:00 og 2026-11-08T21:46:00+00:00 (UTC). For hver søgning:

- **GSearch** v2.0 er spurgt direkte i alle 13 ressourcer, også dem pluginet ikke
  bruger (fx `navngivenvej`). Grænsen er 10 hits pr. ressource.
- **Bifrost** (testmiljøet `bifrost.test42.dataforsyningen.dk`) er spurgt med `/resolve`
  og med `/search` for hvert target.
- **Med kommunekoder** bruger GSearch sit kommunefilter. Bifrost har intet
  kommunefilter på `/search`, så der er hentet 100 hits pr. target. `/resolve` er låst
  til kommunen.

De rå svar ligger i [`tests/fixtures/forskelle/`](../tests/fixtures/forskelle/), med
tidspunkt og URL (nøgler er fjernet). Hvert eksempel nedenfor linker til sin optagelse.

**Sådan læses tabellerne.** Hver tabel viser de øverste hits fra den pågældende
GSearch-ressource eller det pågældende Bifrost-endpoint, i den rækkefølge tjenesten
svarede:

- For GSearch er det feltet `visningstekst`.
- For Bifrost er det feltet `result`.
- I firkantede parenteser står udvalgte felter fra svaret, fx kommunekoder og
  Bifrosts `confidence` (sikkerhed A–C).

Dokumentet beskriver kun det, som optagelserne viser. Hvor årsagen ikke fremgår af
optagelserne, står det der.

Dokumentet er genereret af `tests/tools/forskelle_doc.py`. Søgestrengene er optaget
med `tests/tools/record_differences.py`.

Pluginets egne testcases (`tests/cases.yaml`) er optaget fra begge tjenester på samme
måde, som pluginet søger. Resultaterne står side om side i
[`tests/fixtures/bifrost/cases/REPORT.md`](../tests/fixtures/bifrost/cases/REPORT.md).
GSearch-baseline står i [`tests/fixtures/gsearch/BASELINE.md`](../tests/fixtures/gsearch/BASELINE.md).

## Indhold

- [Delvise ord (fuldendelse mens man skriver)](#delord)
- [Husnummer før vejnavn](#husnummer-foerst)
- [Navne stavet som de udtales](#stavemaade)
- [Visningstekst: stednavnets undertype og lokalitet](#visningstekst)
- [Kommuner og postnumre på stednavne og veje](#kommuner)
- [Kommunefilter](#kommunefilter)
- [Matrikler og ejendomme](#matrikel)
- [Navne og rangering](#navne)
- [Fejl under optagelsen](#fejl)
- [Hvor Bifrost er bedre eller lige så god](#bifrost-bedre)

<a id="delord"></a>

## Delvise ord (fuldendelse mens man skriver)

Issue: [#3](https://github.com/AsgerPetersen/qgis-geosearch/issues/3)

GSearch fuldender et delvist ord: `nørrebrog` giver Nørrebrogade. Bifrost fuldender ikke
i de optagne eksempler. Et delvist ord giver i stedet hele ord, der ligner
(`nørrebrog` → Nørrebro). Med hele vejnavnet finder Bifrost vejene, se sidste eksempel
i afsnittet.

#### `nørrebrog`

| Tjeneste | Øverste hits |
|---|---|
| GSearch `husnummer` | Nørrebrogade 1, 2200 København N<br>Nørrebrogade 1, 4930 Maribo<br>Nørrebrogade 1, 7500 Holstebro |
| GSearch `navngivenvej` | Nørrebrogade (8700 Horsens)<br>Nørrebrogade (7000 Fredericia)<br>Nørrebrogade (8900 Randers C, 8930 Randers NØ) |
| Bifrost `/resolve` | Nørrebro, 4653 Karise<br>Nørrebro, 9700 Brønderslev<br>Nørrebro, 9800 Hjørring |
| Bifrost `/search` street | Nørrebro, 4653 Karise<br>Nørrebro, 9700 Brønderslev<br>Nørrebro, 9800 Hjørring |

GSearch fuldender til Nørrebrogade, både som adresser og som veje. Bifrost giver vejen Nørrebro.

Optaget 2026-11-06T19:48:17+00:00 · [rå optagelse](../tests/fixtures/forskelle/noerrebrog.json)

#### `nørrebrog 1`

| Tjeneste | Øverste hits |
|---|---|
| GSearch `husnummer` | Nørrebrogade 1, 2200 København N<br>Nørrebrogade 1, 4930 Maribo<br>Nørrebrogade 1, 7500 Holstebro |
| Bifrost `/resolve` | Nørrebro 1, 4653 Karise<br>Nørrebro 1, 5900 Rudkøbing<br>Nørrebro 1, 5985 Søby Ærø |

GSearch giver Nørrebrogade 1. Bifrost giver Nørrebro 1.

Optaget 2026-11-06T19:48:16+00:00 · [rå optagelse](../tests/fixtures/forskelle/noerrebrog-1.json)

#### `vangeb`

| Tjeneste | Øverste hits |
|---|---|
| GSearch `husnummer` | Vangeboled 1, Søllerød, 2840 Holte<br>Vangeboled 2, Søllerød, 2840 Holte<br>Vangebovej 2, Søllerød, 2840 Holte |
| GSearch `navngivenvej` | Vangeboled (2840 Holte)<br>Vangebovej (2840 Holte) |
| Bifrost `/resolve` | Vangen, 6715 Esbjerg N<br>Vangen, 9460 Brovst<br>Vangen, 4281 Gørlev |
| Bifrost `/search` stednavn | Vangebo<br>Vange<br>Vangen |

GSearch finder Vangeboled og Vangebovej i Holte. Bifrost giver navne, der ligner, fx vejen Vangen.

Optaget 2026-11-06T19:48:49+00:00 · [rå optagelse](../tests/fixtures/forskelle/vangeb.json)

#### `vangeb 77`

| Tjeneste | Øverste hits |
|---|---|
| GSearch `husnummer` | Vangebovej 77, Søllerød, 2840 Holte |
| Bifrost `/resolve` | Vangen 77, 9400 Nørresundby [sikkerhed B]<br>Vangen 177, 1., 9400 Nørresundby [sikkerhed C]<br>Vangen 277, 9400 Nørresundby [sikkerhed C] |

GSearch giver Vangebovej 77. Bifrost giver Vangen 77 i Nørresundby.

Optaget 2026-11-06T19:48:50+00:00 · [rå optagelse](../tests/fixtures/forskelle/vangeb-77.json)

#### `rådhuspl`

| Tjeneste | Øverste hits |
|---|---|
| GSearch `husnummer` | Rådhuspladsen 1, 1550 København V<br>Rådhuspladsen 1, 3300 Frederiksværk<br>Rådhuspladsen 1, 4200 Slagelse |
| Bifrost `/resolve` | Rådhuspladsen<br>Rådhuspladsen, 4660 Store Heddinge<br>Rådhuspladsen, 4300 Holbæk<br>Rådhuspladsen, 5450 Otterup |

GSearch giver adresser på Rådhuspladsen. Bifrosts `/resolve` giver kun vejene Rådhuspladsen (alle 10 hits er veje), ingen adresser.

Optaget 2026-11-06T19:48:55+00:00 · [rå optagelse](../tests/fixtures/forskelle/raadhuspl.json)

#### `skodsb`

| Tjeneste | Øverste hits |
|---|---|
| GSearch `husnummer` | Skodsborg Strandvej 1, 2942 Skodsborg<br>Skodsborgparken 1, 2942 Skodsborg<br>Skodsborgparken 3, 2942 Skodsborg |
| GSearch `navngivenvej` | Skodsborg Strandvej (2942 Skodsborg, 2950 Vedbæk)<br>Skodsborgparken (2942 Skodsborg)<br>Skodsborgvej (2830 Virum, 2840 Holte, 2850 Nærum, 2942 Skodsborg) |
| Bifrost `/resolve` | Skodsborg<br>Skodsbølvej, 6310 Broager<br>Skodsbølvej, 6880 Tarm<br>Skodsborgvej<br>Skodsborgvej, 9270 Klarup |

GSearch fuldender til veje, der begynder med Skodsb. Bifrosts `/resolve` giver bl.a. byen Skodsborg, Skodsbølvej og Skodsborgvej. Skodsborg Strandvej er ikke blandt de 10 hits.

Optaget 2026-11-06T19:48:12+00:00 · [rå optagelse](../tests/fixtures/forskelle/skodsb.json)

#### `skodsborgvej 41`

| Tjeneste | Øverste hits |
|---|---|
| GSearch `husnummer` | Skodsborgvej 41, 2830 Virum<br>Skodsborgvej 41, 9270 Klarup<br>Skodsborgvej 410, 2942 Skodsborg |
| Bifrost `/resolve` | Skodsborgvej 41, 2830 Virum<br>Skodsborgvej 41, 9270 Klarup<br>Skodsborgvej 341, 2850 Nærum |

GSearch fuldender også husnummeret. Bifrost giver husnumre, der ligner.

Optaget 2026-11-06T19:48:12+00:00 · [rå optagelse](../tests/fixtures/forskelle/skodsborgvej-41.json)

#### `80`

| Tjeneste | Øverste hits |
|---|---|
| GSearch `postnummer` | 8000 Aarhus C |
| Bifrost `/search` postcode | *ingen hits* |

GSearch fuldender postnummeret. Bifrost giver ingen postnumre.

Optaget 2026-11-06T19:48:23+00:00 · [rå optagelse](../tests/fixtures/forskelle/80.json)

#### `køb`

| Tjeneste | Øverste hits |
|---|---|
| GSearch `kommune` | Københavns Kommune |
| Bifrost `/search` kommune | Køge<br>København<br>Kolding |

GSearch giver Københavns Kommune. Bifrost giver Køge først.

Optaget 2026-11-06T19:48:29+00:00 · [rå optagelse](../tests/fixtures/forskelle/koeb.json)

#### `162 vesterv`

| Tjeneste | Øverste hits |
|---|---|
| GSearch `matrikel` | 162, Vestervold Kvarter, København |
| Bifrost `/search` ejendom | 16a, Vestervig By, Vestervig<br>16f, Vestervig By, Vestervig<br>16i, Vestervig By, Vestervig |

GSearch fuldender ejerlavet til Vestervold Kvarter. Bifrost giver matrikler i Vestervig.

Optaget 2026-11-06T19:50:01+00:00 · [rå optagelse](../tests/fixtures/forskelle/162-vesterv.json)

#### `nørrebrogade`

| Tjeneste | Øverste hits |
|---|---|
| GSearch `navngivenvej` | Nørrebrogade (8700 Horsens)<br>Nørrebrogade (7000 Fredericia)<br>Nørrebrogade (8900 Randers C, 8930 Randers NØ) |
| Bifrost `/resolve` | Nørrebrogade, 8700 Horsens<br>Nørrebrogade, 7000 Fredericia<br>Nørrebrogade |
| Bifrost `/search` street | Nørrebrogade, 8700 Horsens<br>Nørrebrogade, 7000 Fredericia<br>Nørrebrogade |

Til sammenligning: med hele vejnavnet finder Bifrost vejene Nørrebrogade.

Optaget 2026-11-06T19:48:43+00:00 · [rå optagelse](../tests/fixtures/forskelle/noerrebrogade.json)

<a id="husnummer-foerst"></a>

## Husnummer før vejnavn

Issue: [#33](https://github.com/AsgerPetersen/qgis-geosearch/issues/33)

Nogle brugere skriver husnummeret først, fx `14 østerlund` for at finde Østerlund 14.
GSearch finder adresserne i alle de optagne eksempler. Bifrost finder dem i nogle af
eksemplerne, men ikke i alle. Optagelserne viser ikke, hvorfor.

#### `14 østerlund`

| Tjeneste | Øverste hits |
|---|---|
| GSearch `husnummer` | Østerlund 14, 9870 Sindal<br>Østerlund 14, Gjellerup, 7400 Herning |
| Bifrost `/resolve` | *ingen hits* |

GSearch finder begge adresser Østerlund 14. Bifrosts `/resolve` giver ingen hits.

Optaget 2026-11-06T19:48:50+00:00 · [rå optagelse](../tests/fixtures/forskelle/14-oesterlund.json)

#### `østerlund 14`

| Tjeneste | Øverste hits |
|---|---|
| GSearch `husnummer` | Østerlund 14, 9870 Sindal<br>Østerlund 14, Gjellerup, 7400 Herning |
| Bifrost `/resolve` | Østerlund 14, Gjellerup, 7400 Herning [sikkerhed C]<br>Østerlund 14, 9870 Sindal [sikkerhed C] |

Til sammenligning: med husnummeret sidst finder Bifrost begge adresser.

Optaget 2026-11-06T19:52:30+00:00 · [rå optagelse](../tests/fixtures/forskelle/oesterlund-14.json)

#### `1 nørrebrogade`

| Tjeneste | Øverste hits |
|---|---|
| GSearch `husnummer` | Nørrebrogade 1, 2200 København N<br>Nørrebrogade 1, 4930 Maribo<br>Nørrebrogade 1, 7500 Holstebro |
| Bifrost `/resolve` | Nørreballe [sikkerhed C]<br>Nørre Snede [sikkerhed C]<br>Aars [sikkerhed C] |

GSearch finder Nørrebrogade 1. Bifrost giver Nørreballe, Nørre Snede og Aars, ingen adresser.

Optaget 2026-11-06T19:58:27+00:00 · [rå optagelse](../tests/fixtures/forskelle/1-noerrebrogade.json)

#### `77 vangeb`

| Tjeneste | Øverste hits |
|---|---|
| GSearch `husnummer` | Vangebovej 77, Søllerød, 2840 Holte |
| Bifrost `/resolve` | *ingen hits* |

Husnummer først og et delvist vejnavn. GSearch finder Vangebovej 77. Bifrosts `/resolve` giver ingen hits.

Optaget 2026-11-06T19:48:48+00:00 · [rå optagelse](../tests/fixtures/forskelle/77-vangeb.json)

#### `77 vangebovej`

| Tjeneste | Øverste hits |
|---|---|
| GSearch `husnummer` | Vangebovej 77, Søllerød, 2840 Holte |
| Bifrost `/resolve` | Vangebovej 77, Søllerød, 2840 Holte [sikkerhed A]<br>Vangebovej 17, Søllerød, 2840 Holte [sikkerhed C]<br>Vangebovej 57, Søllerød, 2840 Holte [sikkerhed C] |

Her finder Bifrost adressen.

Optaget 2026-11-06T19:58:26+00:00 · [rå optagelse](../tests/fixtures/forskelle/77-vangebovej.json)

<a id="stavemaade"></a>

## Navne stavet som de udtales

Issue: [#34](https://github.com/AsgerPetersen/qgis-geosearch/issues/34)

GSearch finder navne, der er stavet, som de udtales: `øenslæger` finder Oehlenschläger.
Bifrost giver først navne, der ligner i stavemåden (Øen, Øenslyst).

#### `øenslæger`

| Tjeneste | Øverste hits |
|---|---|
| GSearch `stednavn` | Oehlenschlägers Bøg (Løvtræ i Tranekær)<br>Adam Oehlenschläger (Seværdighed i København K)<br>Oehlenschlægersgades Skole (Folkeskole i København V) |
| GSearch `husnummer` | Oehlenschlægersgade 1, 1663 København V |
| Bifrost `/search` stednavn | Øenslyst<br>Øen<br>Øen<br>Øen<br>Øen |
| Bifrost `/resolve` | Øen, 8560 Kolind<br>Øen, 6880 Tarm<br>Øen, 6710 Esbjerg V<br>Oehlenschlægersvej, 8230 Åbyhøj<br>Oehlenschlægersvej, 5230 Odense M |

GSearch finder stednavne og adresser med Oehlenschläger/Oehlenschlæger. Bifrost giver først Øenslyst og Øen. I `/resolve` kommer Oehlenschlægersvej som hit nr. 4.

Optaget 2026-11-06T19:51:02+00:00 · [rå optagelse](../tests/fixtures/forskelle/oeenslaeger.json)

<a id="visningstekst"></a>

## Visningstekst: stednavnets undertype og lokalitet

Issue: [#1](https://github.com/AsgerPetersen/qgis-geosearch/issues/1)

GSearch leverer en færdig visningstekst. For stednavne er det navn, undertype og
lokalitet, fx "Skagen (By i Frederikshavn Kommune)". Bifrost leverer kun navnet. Flere
stednavne med samme navn kan derfor ikke skelnes på teksten alene. Pluginet sætter selv
Bifrosts stednavnetype og kommune på (se REPORT.md). Det er ikke de samme oplysninger
som GSearchs undertype og lokalitet.

#### `skagen`

| Tjeneste | Øverste hits |
|---|---|
| GSearch `stednavn` | Skagen (Gård i Brønderslev)<br>Skagen (By i Frederikshavn Kommune)<br>Skagen (Mark i Agersø) |
| Bifrost `/search` stednavn | Skagen<br>Skagen<br>Skagen |

GSearch skelner mellem gården, byen og marken. Bifrost giver tre gange "Skagen".

Optaget 2026-11-06T19:48:58+00:00 · [rå optagelse](../tests/fixtures/forskelle/skagen.json)

#### `anholt`

| Tjeneste | Øverste hits |
|---|---|
| GSearch `stednavn` | Anholt (Anholt Havn, Lystbådehavn i Danmark)<br>Anholt (Anholt Flyveplads, Flyveplads i Region Midtjylland)<br>Anholt (Gård i Østervrå)<br>Anholt (By i Augustenborg)<br>Anholt (By i Vamdrup) |
| Bifrost `/search` stednavn | Anholt<br>Anholt<br>Anholt<br>Anholt<br>Anholt |

Bifrost giver fem gange "Anholt".

Optaget 2026-11-06T19:49:06+00:00 · [rå optagelse](../tests/fixtures/forskelle/anholt.json)

#### `tivoli`

| Tjeneste | Øverste hits |
|---|---|
| GSearch `stednavn` | Tivoli (Forlystelsespark i København V)<br>Tivoli (By i Birkerød)<br>Tivoli (Skov i Kjellerup) |
| Bifrost `/search` stednavn | Tivoli<br>Tivoli<br>Tivoli |

GSearch viser forlystelsesparken i København V først. Bifrosts tekst skelner ikke mellem stednavnene.

Optaget 2026-11-06T19:49:05+00:00 · [rå optagelse](../tests/fixtures/forskelle/tivoli.json)

#### `rådhuspladsen`

| Tjeneste | Øverste hits |
|---|---|
| GSearch `stednavn` | Rådhuspladsen (Seværdighed i København V)<br>Rådhuspladsen (Standsningssted, tog i København V)<br>Rådhuspladsen (Seværdighed i Søborg) |
| Bifrost `/search` stednavn | Rådhuspladsen [kommuner: 0101]<br>Rådhuspladsen [kommuner: 0159]<br>Rådhuspladsen [kommuner: 0101] |

GSearch skelner mellem seværdigheden og stationen i København V. Bifrost giver to gange "Rådhuspladsen" i kommune 0101.

Optaget 2026-11-06T19:48:18+00:00 · [rå optagelse](../tests/fixtures/forskelle/raadhuspladsen.json)

<a id="kommuner"></a>

## Kommuner og postnumre på stednavne og veje

Issue: [#35](https://github.com/AsgerPetersen/qgis-geosearch/issues/35)

I GSearch har et stednavn eller en navngiven vej alle de kommuner, det ligger i. I
Bifrost har et stednavn højst én kommune i optagelserne, også når det strækker sig over
flere. Nogle veje har også færre kommuner og postnumre end i GSearch, mens andre veje
har de samme. Optagelserne viser ikke, hvorfor.

Pluginets kommunefilter beholder et stednavn, hvis en af dets kommuner i Bifrost er
valgt. Et stednavn, der strækker sig over flere kommuner, bliver derfor skjult, når
filteret står på en af de kommuner, Bifrost ikke har på objektet. Pluginets testcase
`ste-gudenaa-kommunefilter-730` viser det for Gudenå og Randers (se REPORT.md).

Optællingen nedenfor dækker alle objekter i alle optagelser (hvert objekt tælles én gang):

| | Objekter | Med 0 kommuner | Med 1 kommune | Med flere kommuner |
|---|---|---|---|---|
| GSearch stednavne | 197 | 7 | 169 | 21 (højst 8) |
| Bifrost stednavne | 1257 | 29 | 1228 | 0 |
| Bifrost veje (`street`) | 1284 | 21 | 1242 | 21 |

Bifrost-veje med mere end ét postnummer: 59 af 1284.

#### `gudenå` med kommunefilter 730

| Tjeneste | Øverste hits |
|---|---|
| GSearch `stednavn` | Gudenå (Vandløb i Vonge) [kommuner: 0630, 0740, 0791, 0730, 0710, 0766, 0615, 0746] |
| Bifrost `/search` stednavn (kun "Gudenå") | Gudenå [kommuner: 0740] |

Søgning med kommunefilter 730 (Randers). GSearch har otte kommuner på Gudenå, bl.a. 0730. Bifrost har kun 0740.

Optaget 2026-11-06T19:56:56+00:00 · [rå optagelse](../tests/fixtures/forskelle/gudenaa-k730.json)

#### `københavn`

| Tjeneste | Øverste hits |
|---|---|
| GSearch `stednavn` | København (By i Københavns Kommune) [kommuner: 0101, 0157, 0147, 0159, 0175, 0167, 0163, 0185] |
| Bifrost `/search` stednavn (kun "København") | København [kommuner: 0751]<br>København [kommuner: 0766]<br>København [kommuner: 0615]<br>København [kommuner: 0101] |

GSearch har otte kommuner på byen København. Bifrosts stednavne København har hver én kommune.

Optaget 2026-11-06T19:51:33+00:00 · [rå optagelse](../tests/fixtures/forskelle/koebenhavn.json)

#### `furesø`

| Tjeneste | Øverste hits |
|---|---|
| GSearch `stednavn` | Furesø (Sø i Region Hovedstaden) [kommuner: 0230, 0173, 0190] |
| Bifrost `/search` stednavn (kun "Furesø") | Furesø [kommuner: 0190] |

GSearch har tre kommuner på søen. Bifrost har én.

Optaget 2026-11-06T19:56:57+00:00 · [rå optagelse](../tests/fixtures/forskelle/furesoe.json)

#### `lyngby` med kommunefilter 230, 173

| Tjeneste | Øverste hits |
|---|---|
| GSearch `stednavn` (kun "Lyngby…") | Lyngby (Kongens Lyngby, By i Lyngby-Taarbæk Kommune) [kommuner: 0157, 0159, 0173]<br>Lyngby (Standsningssted, tog i Kongens Lyngby) [kommuner: 0173]<br>Lyngby Sø (Sø i Kongens Lyngby) [kommuner: 0159, 0173] |
| Bifrost `/search` stednavn (kun "Lyngby…") | Lyngby [kommuner: 0840]<br>Lyngby [kommuner: 0860]<br>Lyngby [kommuner: 0787]<br>Lyngby [kommuner: 0173]<br>Lyngby [kommuner: 0760]<br>Lyngby [kommuner: 0630]<br>Lyngby [kommuner: 0751]<br>Lyngby [kommuner: 0710]<br>Lyngby [kommuner: 0707]<br>Lyngby [kommuner: 0173] |

GSearch har flere kommuner på Lyngby og Lyngby Sø. Bifrost har én kommune på hvert stednavn.

Optaget 2026-11-06T19:48:40+00:00 · [rå optagelse](../tests/fixtures/forskelle/lyngby-k230-173.json)

#### `roskilde fjord` med kommunefilter 265

| Tjeneste | Øverste hits |
|---|---|
| GSearch `stednavn` | Roskilde Fjord (Fjord i Isefjord) [kommuner: 0265, 0260, 0350, 0250] |
| Bifrost `/search` stednavn (kun "Roskilde Fjord") | Roskilde Fjord [kommuner: ingen] |

GSearch har fire kommuner på Roskilde Fjord. Bifrost har ingen.

Optaget 2026-11-06T19:56:59+00:00 · [rå optagelse](../tests/fixtures/forskelle/roskilde-fjord-k265.json)

#### `skodsborg`

| Tjeneste | Øverste hits |
|---|---|
| GSearch `stednavn` (kun "Skodsborg (…") | Skodsborg (By i Rudersdal Kommune) [kommuner: 0173, 0230] |
| Bifrost `/search` stednavn (kun "Skodsborg") | Skodsborg [kommuner: 0230] |

Byen Skodsborg: GSearch har to kommuner, Bifrost én.

Optaget 2026-11-06T19:48:21+00:00 · [rå optagelse](../tests/fixtures/forskelle/skodsborg.json)

#### `skodsborg strandvej` med kommunefilter 173

| Tjeneste | Øverste hits |
|---|---|
| GSearch `navngivenvej` | Skodsborg Strandvej (2942 Skodsborg, 2950 Vedbæk) [kommuner: 0230, 0173] |
| Bifrost `/search` street (kun "Skodsborg Strandvej…") | Skodsborg Strandvej, 2942 Skodsborg [kommuner: 0230; postnumre: 2942] |

Vejen Skodsborg Strandvej: GSearch har to kommuner og to postnumre (2942, 2950). Bifrost har én kommune og ét postnummer.

Optaget 2026-11-06T19:57:01+00:00 · [rå optagelse](../tests/fixtures/forskelle/skodsborg-strandvej-k173.json)

#### `lyngby hovedgade` med kommunefilter 157

| Tjeneste | Øverste hits |
|---|---|
| GSearch `navngivenvej` | Lyngby Hovedgade (2800 Kongens Lyngby) [kommuner: 0173, 0157] |
| Bifrost `/search` street (kun "Lyngby Hovedgade…") | Lyngby Hovedgade, 2800 Kongens Lyngby [kommuner: 0173; postnumre: 2800] |

GSearch har to kommuner på vejen. Bifrost har én.

Optaget 2026-11-06T19:56:59+00:00 · [rå optagelse](../tests/fixtures/forskelle/lyngby-hovedgade-k157.json)

#### `nørrebrogade 2400`

| Tjeneste | Øverste hits |
|---|---|
| GSearch `navngivenvej` | Nørrebrogade (2200 København N, 2400 København NV) |
| Bifrost `/search` street (kun "Nørrebrogade, 2…") | Nørrebrogade, 2200 København N [postnumre: 2200] |

GSearch har postnumrene 2200 og 2400 på Nørrebrogade i København. Bifrost har kun 2200.

Optaget 2026-11-06T19:57:02+00:00 · [rå optagelse](../tests/fixtures/forskelle/noerrebrogade-2400.json)

#### `vesterbrogade`

| Tjeneste | Øverste hits |
|---|---|
| GSearch `navngivenvej` (kun "Vesterbrogade (1550…") | Vesterbrogade (1550 København V, 1570 København V, 1610 København V, 1613 København V, 1614 København V, 1620 København V, 1751 København V, 1800 Frederiksberg C, 1810 Frederiksberg C) [kommuner: 0147, 0101] |
| Bifrost `/search` street (kun "Vesterbrogade") | Vesterbrogade [kommuner: 0101, 0147; postnumre: 1620, 1800] |

Vesterbrogade i København og Frederiksberg: GSearch har ni postnumre. Bifrost har to (1620 og 1800). Begge har de to kommuner.

Optaget 2026-11-08T21:45:11+00:00 · [rå optagelse](../tests/fixtures/forskelle/vesterbrogade.json)

#### `jagtvej` med kommunefilter 147

| Tjeneste | Øverste hits |
|---|---|
| GSearch `navngivenvej` | Jagtvej (2000 Frederiksberg, 2100 København Ø, 2200 København N) [kommuner: 0147, 0101] |
| Bifrost `/resolve` | Jasminvej, 2000 Frederiksberg<br>Vagtelvej, 2000 Frederiksberg<br>Solsortvej, 2000 Frederiksberg |
| Bifrost `/search` street (kun "Jagtvej") | Jagtvej [kommuner: 0101; postnumre: 2100, 2200] |

Søgning med kommunefilter 147 (Frederiksberg). GSearch har Jagtvej med kommunerne 0147 og 0101 og finder den. Bifrost har kun 0101 på Jagtvej, og `/resolve` låst til 0147 giver andre veje på Frederiksberg. Pluginet bruger `/resolve` til husnumre og veje, så det viser ikke Jagtvej med kommunefilter 147.

Optaget 2026-11-08T21:46:00+00:00 · [rå optagelse](../tests/fixtures/forskelle/jagtvej-k147.json)

#### `skodsb`

| Tjeneste | Øverste hits |
|---|---|
| GSearch `navngivenvej` (kun "Skodsborgvej (…") | Skodsborgvej (2830 Virum, 2840 Holte, 2850 Nærum, 2942 Skodsborg) [kommuner: 0230, 0173] |
| Bifrost `/search` street (kun "Skodsborgvej") | Skodsborgvej [kommuner: 0173, 0230; postnumre: 2830, 2840, 2850, 2942] |

Til sammenligning: på Skodsborgvej har Bifrost de samme to kommuner som GSearch.

Optaget 2026-11-06T19:48:12+00:00 · [rå optagelse](../tests/fixtures/forskelle/skodsb.json)

<a id="kommunefilter"></a>

## Kommunefilter

Issue: [#2](https://github.com/AsgerPetersen/qgis-geosearch/issues/2)

GSearch kan filtrere på kommune i selve søgningen. Bifrost tilbyder det ikke på
`/search`. Pluginet filtrerer derfor selv blandt de hits, Bifrost sender. Optagelserne
har hentet 100 hits pr. target, og de ønskede hits er ikke altid blandt dem.
`/resolve` kan låses til en kommune.

#### `1a` med kommunefilter 615

| Tjeneste | Øverste hits |
|---|---|
| GSearch `matrikel` | 1a, Bolund, Nim<br>1a, Nim By, Nim<br>1a, Uth By, Uth |
| Bifrost `/search` ejendom | 1a, Frederiksberg<br>1a, Gentofte<br>1a, Gladsaxe |
| Bifrost `/search` ejendom (kun hits i kommunefilteret) | *0 af 100 hits har kommune 0615* |

GSearch giver matrikler 1a i kommune 615. Ingen af de 100 ejendomme, Bifrost sender, ligger i kommunen. Et filter på kommunen efterlader intet.

Optaget 2026-11-06T19:48:38+00:00 · [rå optagelse](../tests/fixtures/forskelle/1a-k615.json)

#### `vor frue` med kommunefilter 101, 851

| Tjeneste | Øverste hits |
|---|---|
| GSearch `stednavn` | Vor Frue Kirke (Kirke i København K)<br>Vor Frue Kirke (Kirke i Aalborg) |
| Bifrost `/search` stednavn | Vor Frue<br>Vor Frue Kilde<br>Vor Frue Kilde |
| Bifrost `/search` stednavn (kun hits i kommunefilteret) | *5 af 100 hits har kommune 0101, 0851*<br>Vor Frue Kirke<br>Vor Frue Kirke<br>Frue Plads |

GSearch giver Vor Frue Kirke i de to kommuner. Bifrost sender stednavne fra hele landet. 5 af de 100 ligger i kommunerne, heriblandt to gange Vor Frue Kirke. Her finder et filter på kommunerne altså kirkerne.

Optaget 2026-11-06T19:48:37+00:00 · [rå optagelse](../tests/fixtures/forskelle/vor-frue-k101-851.json)

#### `vestergade` med kommunefilter 751

| Tjeneste | Øverste hits |
|---|---|
| GSearch `navngivenvej` | Vestergade (8000 Aarhus C) |
| Bifrost `/resolve` | Vestergade, 8000 Aarhus C [sikkerhed A] |
| Bifrost `/search` street | Vestergade, 8550 Ryomgård<br>Vestergade, 6650 Brørup<br>Vestergade, 8990 Fårup |

`/resolve`, låst til kommunen, finder Vestergade i Aarhus. `/search` uden filter giver Vestergade i andre byer først.

Optaget 2026-11-06T19:50:37+00:00 · [rå optagelse](../tests/fixtures/forskelle/vestergade-k751.json)

<a id="matrikel"></a>

## Matrikler og ejendomme

Issue: [#4](https://github.com/AsgerPetersen/qgis-geosearch/issues/4)

GSearchs `matrikel` giver jordstykker. Bifrost tilbyder ikke søgning i jordstykker. Det
nærmeste er `/search` med target `ejendom`, som giver ejendomme (BFE). En ejendom kan
bestå af mange jordstykker.

#### `3kg`

| Tjeneste | Øverste hits |
|---|---|
| GSearch `matrikel` | 3kg, Aaker<br>3kg, Struer<br>3kg, Vangede<br>3kg, Buddinge<br>3kg, Aars By, Aars |
| Bifrost `/search` ejendom | 3kg, Buddinge [ejendom med 1 jordstykke]<br>3kg, Søllerød By, Søllerød [ejendom med 1 jordstykke]<br>3kg, Øverød By, Søllerød [ejendom med 1 jordstykke]<br>3kg, Virum By, Lundtofte [ejendom med 1 jordstykke]<br>3kg, Vangede [ejendom med 27 jordstykker] |

Bifrosts hits er ejendomme. "3kg, Vangede" er en ejendom med 27 jordstykker. Rækkefølgen er også forskellig.

Optaget 2026-11-06T19:48:22+00:00 · [rå optagelse](../tests/fixtures/forskelle/3kg.json)

#### `3kg søll`

| Tjeneste | Øverste hits |
|---|---|
| GSearch `matrikel` | 3kg, Øverød By, Søllerød<br>3kg, Søllerød By, Søllerød |
| Bifrost `/search` ejendom | 3kg, Søllerød By, Søllerød<br>2kg, Søllerød By, Søllerød<br>3g, Søllerød By, Søllerød<br>3k, Søllerød By, Søllerød |

GSearch finder 3kg i både Øverød By og Søllerød By. Bifrost giver kun Søllerød By og derefter matrikler, der ligner.

Optaget 2026-11-06T19:48:21+00:00 · [rå optagelse](../tests/fixtures/forskelle/3kg-soell.json)

#### `6033528`

| Tjeneste | Øverste hits |
|---|---|
| GSearch `matrikel` | 162, Vestervold Kvarter, København |
| Bifrost `/search` ejendom | 162, Vestervold Kvarter, København [sikkerhed A] |

Søgning på BFE-nummer: begge finder ejendommen.

Optaget 2026-11-06T19:50:02+00:00 · [rå optagelse](../tests/fixtures/forskelle/6033528.json)

<a id="navne"></a>

## Navne og rangering

Nogle objekter hedder noget andet i Bifrost end i GSearch. I nogle søgninger giver
Bifrosts `/resolve` en anden type først end den, man søgte efter.

#### `101`

| Tjeneste | Øverste hits |
|---|---|
| GSearch `kommune` | Københavns Kommune |
| Bifrost `/search` kommune | København |

Begge finder kommune 101. GSearch kalder den "Københavns Kommune", Bifrost "København".

Optaget 2026-11-06T19:50:03+00:00 · [rå optagelse](../tests/fixtures/forskelle/101.json)

#### `københavn`

| Tjeneste | Øverste hits |
|---|---|
| GSearch `politikreds` | Københavns Politikreds<br>Københavns Vestegns Politikreds |
| Bifrost `/search` politikreds | Københavns Politi<br>Københavns Vestegns Politi |

Politikredse hedder "Politikreds" i GSearch og "Politi" i Bifrost.

Optaget 2026-11-06T19:51:33+00:00 · [rå optagelse](../tests/fixtures/forskelle/koebenhavn.json)

#### `hovedstaden`

| Tjeneste | Øverste hits |
|---|---|
| GSearch `region` | Region Hovedstaden |
| Bifrost `/resolve` | Hovedgaden, 8410 Rønde<br>Hovedgaden, 5853 Ørbæk<br>Hovedgaden, 9330 Dronninglund |
| Bifrost `/search` region | Region Hovedstaden |

Begge finder regionen som region. Bifrosts `/resolve` giver veje først.

Optaget 2026-11-06T19:50:36+00:00 · [rå optagelse](../tests/fixtures/forskelle/hovedstaden.json)

#### `roskilde fjord`

| Tjeneste | Øverste hits |
|---|---|
| GSearch `stednavn` | Roskilde Fjord (Fjord i Isefjord) |
| Bifrost `/resolve` | Roskildevej, 7400 Herning<br>Roskildevej, 3330 Gørløse<br>Roskildevej, 4480 Store Fuglede |
| Bifrost `/search` stednavn | Roskilde Fjord [sikkerhed A] |

Begge finder fjorden som stednavn. Bifrosts `/resolve` giver veje først.

Optaget 2026-11-06T19:49:07+00:00 · [rå optagelse](../tests/fixtures/forskelle/roskilde-fjord.json)

<a id="fejl"></a>

## Fejl under optagelsen

Enkelte opslag fejlede under optagelsen. De er gemt, som de var. De siger ikke noget om,
hvor ofte tjenesterne fejler.

#### `1a sønderby`

| Tjeneste | Øverste hits |
|---|---|
| GSearch `husnummer` | Sønderbyvej 1A, 7270 Stakroge<br>Sønderbyvej 1A, Møgeltønder, 6270 Tønder<br>Bredvigvej 1A, Sønderby, 4050 Skibby |
| Bifrost `/resolve` | fejl: HTTP 504 |

Bifrosts `/resolve` svarede HTTP 504.

Optaget 2026-11-06T19:51:02+00:00 · [rå optagelse](../tests/fixtures/forskelle/1a-soenderby.json)

#### `københavn`

| Tjeneste | Øverste hits |
|---|---|
| GSearch `adresse` | fejl: HTTP 502 |
| Bifrost `/resolve` | København K<br>København N<br>København S |

GSearchs `adresse` svarede HTTP 502.

Optaget 2026-11-06T19:51:33+00:00 · [rå optagelse](../tests/fixtures/forskelle/koebenhavn.json)

<a id="bifrost-bedre"></a>

## Hvor Bifrost er bedre eller lige så god

Bifrost finder meget af det samme som GSearch, når hele ord skrives. Bifrost har også
nye søgetyper, som GSearch ikke havde, fx byer (`city`) og ejerlav (se
[#6](https://github.com/AsgerPetersen/qgis-geosearch/issues/6)).

#### `nøddebogade 1 st th`

| Tjeneste | Øverste hits |
|---|---|
| GSearch `husnummer` | *ingen hits* |
| GSearch `adresse` | Nøddebogade 1, st. th, 2200 København N |
| Bifrost `/resolve` | Nøddebogade 1, st. th, 2200 København N [sikkerhed A] |

Bifrost finder lejligheden. GSearchs `husnummer`, som pluginet 3.x brugte, giver ingen hits. GSearchs `adresse` finder den.

Optaget 2026-11-06T19:48:15+00:00 · [rå optagelse](../tests/fixtures/forskelle/noeddebogade-1-st-th.json)

#### `1an gentofte`

| Tjeneste | Øverste hits |
|---|---|
| GSearch `matrikel_udgaaet` | 1an, Gentofte |
| Bifrost `/search` ejendom (udgåede) | 1an, Gentofte [sikkerhed A] |

Udgåede matrikler: begge finder 1an, Gentofte.

Optaget 2026-11-06T19:48:32+00:00 · [rå optagelse](../tests/fixtures/forskelle/1an-gentofte.json)

#### `8000`

| Tjeneste | Øverste hits |
|---|---|
| GSearch `postnummer` | 8000 Aarhus C |
| Bifrost `/search` postcode | Aarhus C [sikkerhed A] |

Begge finder postnummeret.

Optaget 2026-11-06T19:49:09+00:00 · [rå optagelse](../tests/fixtures/forskelle/8000.json)

#### `åbenrå`

| Tjeneste | Øverste hits |
|---|---|
| GSearch `postnummer` | 6200 Aabenraa |
| Bifrost `/search` postcode | Aabenraa [sikkerhed A] |

Den gamle stavemåde Åbenrå: begge finder Aabenraa.

Optaget 2026-11-06T19:49:19+00:00 · [rå optagelse](../tests/fixtures/forskelle/aabenraa.json)

#### `skodsb`

| Tjeneste | Øverste hits |
|---|---|
| Bifrost `/search` city | Skodsborg [sikkerhed B] |

Ny type: Bifrosts `city` giver byen Skodsborg.

Optaget 2026-11-06T19:48:12+00:00 · [rå optagelse](../tests/fixtures/forskelle/skodsb.json)

## Om dokumentet

- Kun de optagne søgestrenge er sammenlignet. At en forskel ikke står her, betyder ikke,
  at den ikke findes.
- Optagelserne fra Bifrost er fra testmiljøet på optagelsestidspunktet. Bifrost kan
  have ændret sig siden. GSearch-svarene kan ikke optages igen.
- Nye eksempler tilføjes i `tests/tools/record_differences.py` (optagelse, kræver
  begge tjenester) og `tests/tools/forskelle_spec.py` (beskrivelse). Dokumentet
  genereres derefter offline med `uv run python tests/tools/forskelle_doc.py`.
