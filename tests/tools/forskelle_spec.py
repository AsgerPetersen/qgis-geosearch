"""Sections, examples and descriptions for docs/forskelle-gsearch-bifrost.md.

The hits in the document come from the recordings in tests/fixtures/forskelle;
only the descriptions are written here. Write only what the recordings show.
Run tests/tools/forskelle_doc.py after editing.
"""

from typing import NamedTuple, Optional, Tuple


class Only:
    """Show only the hits whose text matches (exact name or prefix)."""

    def __init__(self, label, exact=None, prefix=None):
        self.label = label
        self.exact = exact
        self.prefix = prefix

    def __call__(self, text):
        if self.exact is not None:
            return text == self.exact
        return text.startswith(self.prefix)


def exact(name):
    return Only('"%s"' % name, exact=name)


def prefix(text):
    return Only('"%s…"' % text, prefix=text)


class View(NamedTuple):
    service: str  # "gs" (GSearch resource) or "bf" (Bifrost request name)
    source: str
    n: int = 3
    only: Optional[Only] = None
    kommuner: bool = False
    postnumre: bool = False
    confidence: bool = False
    parcels: bool = False
    in_filter: bool = False  # Bifrost: keep only hits in the recording's kommuner


def gs(source, n=3, **kw):
    return View("gs", source, n, **kw)


def bf(source, n=3, **kw):
    return View("bf", source, n, **kw)


class Example(NamedTuple):
    fixture: str
    views: Tuple[View, ...]
    text: str
    title: str = ""


class Section(NamedTuple):
    anchor: str
    title: str
    text: str
    examples: Tuple[Example, ...]
    issue: Optional[int] = None
    stats: str = ""


INTRO = """
# Forskelle mellem GSearch og Bifrost

GSearch lukker i november 2026, og Geosearch DK skifter til Bifrost. Begge tjenester
kommer fra Klimadatastyrelsen. Når GSearch er lukket, kan man ikke længere se, hvad den
svarede. Derfor er de samme søgestrenge optaget fra begge tjenester på samme tid, og
svarene er gemt. Dokumentet viser, hvor Bifrost svarer anderledes end GSearch, og hvor
Bifrost svarer lige så godt eller bedre.

**Sådan er det optaget.** {count} søgninger (søgestreng, evt. med kommunekoder) er
optaget mellem {first} og {last} (UTC). For hver søgning:

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
"""

OUTRO = """
## Om dokumentet

- Kun de optagne søgestrenge er sammenlignet. At en forskel ikke står her, betyder ikke,
  at den ikke findes.
- Optagelserne fra Bifrost er fra testmiljøet på optagelsestidspunktet. Bifrost kan
  have ændret sig siden. GSearch-svarene kan ikke optages igen.
- Nye eksempler tilføjes i `tests/tools/record_differences.py` (optagelse, kræver
  begge tjenester) og `tests/tools/forskelle_spec.py` (beskrivelse). Dokumentet
  genereres derefter offline med `uv run python tests/tools/forskelle_doc.py`.
"""

SECTIONS = (
    Section(
        "delord",
        "Delvise ord (fuldendelse mens man skriver)",
        """
GSearch fuldender et delvist ord: `nørrebrog` giver Nørrebrogade. Bifrost fuldender ikke
i de optagne eksempler. Et delvist ord giver i stedet hele ord, der ligner
(`nørrebrog` → Nørrebro). Med hele vejnavnet finder Bifrost vejene, se sidste eksempel
i afsnittet.
""",
        (
            Example(
                "noerrebrog",
                (gs("husnummer"), gs("navngivenvej"), bf("resolve"), bf("street")),
                "GSearch fuldender til Nørrebrogade, både som adresser og som veje. "
                "Bifrost giver vejen Nørrebro.",
            ),
            Example(
                "noerrebrog-1",
                (gs("husnummer"), bf("resolve")),
                "GSearch giver Nørrebrogade 1. Bifrost giver Nørrebro 1.",
            ),
            Example(
                "vangeb",
                (gs("husnummer"), gs("navngivenvej", 2), bf("resolve"), bf("stednavn")),
                "GSearch finder Vangeboled og Vangebovej i Holte. Bifrost giver navne, "
                "der ligner, fx vejen Vangen.",
            ),
            Example(
                "vangeb-77",
                (gs("husnummer"), bf("resolve", confidence=True)),
                "GSearch giver Vangebovej 77. Bifrost giver Vangen 77 i Nørresundby.",
            ),
            Example(
                "raadhuspl",
                (gs("husnummer"), bf("resolve", 4)),
                "GSearch giver adresser på Rådhuspladsen. Bifrosts `/resolve` giver kun "
                "vejene Rådhuspladsen (alle 10 hits er veje), ingen adresser.",
            ),
            Example(
                "skodsb",
                (gs("husnummer"), gs("navngivenvej"), bf("resolve", 5)),
                "GSearch fuldender til veje, der begynder med Skodsb. Bifrosts `/resolve` "
                "giver bl.a. byen Skodsborg, Skodsbølvej og Skodsborgvej. Skodsborg "
                "Strandvej er ikke blandt de 10 hits.",
            ),
            Example(
                "skodsborgvej-41",
                (gs("husnummer"), bf("resolve")),
                "GSearch fuldender også husnummeret. Bifrost giver husnumre, der ligner.",
            ),
            Example(
                "80",
                (gs("postnummer"), bf("postcode")),
                "GSearch fuldender postnummeret. Bifrost giver ingen postnumre.",
            ),
            Example(
                "koeb",
                (gs("kommune"), bf("kommune")),
                "GSearch giver Københavns Kommune. Bifrost giver Køge først.",
            ),
            Example(
                "162-vesterv",
                (gs("matrikel"), bf("ejendom")),
                "GSearch fuldender ejerlavet til Vestervold Kvarter. Bifrost giver "
                "matrikler i Vestervig.",
            ),
            Example(
                "noerrebrogade",
                (gs("navngivenvej"), bf("resolve"), bf("street")),
                "Til sammenligning: med hele vejnavnet finder Bifrost vejene "
                "Nørrebrogade.",
            ),
        ),
        issue=3,
    ),
    Section(
        "husnummer-foerst",
        "Husnummer før vejnavn",
        """
Nogle brugere skriver husnummeret først, fx `14 østerlund` for at finde Østerlund 14.
GSearch finder adresserne i alle de optagne eksempler. Bifrost finder dem i nogle af
eksemplerne, men ikke i alle. Optagelserne viser ikke, hvorfor.
""",
        (
            Example(
                "14-oesterlund",
                (gs("husnummer", 2), bf("resolve")),
                "GSearch finder begge adresser Østerlund 14. Bifrosts `/resolve` giver "
                "ingen hits.",
            ),
            Example(
                "oesterlund-14",
                (gs("husnummer", 2), bf("resolve", 2, confidence=True)),
                "Til sammenligning: med husnummeret sidst finder Bifrost begge adresser.",
            ),
            Example(
                "1-noerrebrogade",
                (gs("husnummer"), bf("resolve", confidence=True)),
                "GSearch finder Nørrebrogade 1. Bifrost giver Nørreballe, Nørre Snede "
                "og Aars, ingen adresser.",
            ),
            Example(
                "77-vangeb",
                (gs("husnummer"), bf("resolve")),
                "Husnummer først og et delvist vejnavn. GSearch finder Vangebovej 77. "
                "Bifrosts `/resolve` giver ingen hits.",
            ),
            Example(
                "77-vangebovej",
                (gs("husnummer"), bf("resolve", confidence=True)),
                "Her finder Bifrost adressen.",
            ),
        ),
        issue=33,
    ),
    Section(
        "stavemaade",
        "Navne stavet som de udtales",
        """
GSearch finder navne, der er stavet, som de udtales: `øenslæger` finder Oehlenschläger.
Bifrost giver først navne, der ligner i stavemåden (Øen, Øenslyst).
""",
        (
            Example(
                "oeenslaeger",
                (gs("stednavn"), gs("husnummer", 1), bf("stednavn", 5), bf("resolve", 5)),
                "GSearch finder stednavne og adresser med Oehlenschläger/Oehlenschlæger. "
                "Bifrost giver først Øenslyst og Øen. I `/resolve` kommer "
                "Oehlenschlægersvej som hit nr. 4.",
            ),
        ),
        issue=34,
    ),
    Section(
        "visningstekst",
        "Visningstekst: stednavnets undertype og lokalitet",
        """
GSearch leverer en færdig visningstekst. For stednavne er det navn, undertype og
lokalitet, fx "Skagen (By i Frederikshavn Kommune)". Bifrost leverer kun navnet. Flere
stednavne med samme navn kan derfor ikke skelnes på teksten alene. Pluginet sætter selv
Bifrosts stednavnetype og kommune på (se REPORT.md). Det er ikke de samme oplysninger
som GSearchs undertype og lokalitet.
""",
        (
            Example(
                "skagen",
                (gs("stednavn"), bf("stednavn")),
                "GSearch skelner mellem gården, byen og marken. Bifrost giver tre gange "
                "\"Skagen\".",
            ),
            Example(
                "anholt",
                (gs("stednavn", 5), bf("stednavn", 5)),
                "Bifrost giver fem gange \"Anholt\".",
            ),
            Example(
                "tivoli",
                (gs("stednavn"), bf("stednavn")),
                "GSearch viser forlystelsesparken i København V først. Bifrosts tekst "
                "skelner ikke mellem stednavnene.",
            ),
            Example(
                "raadhuspladsen",
                (gs("stednavn"), bf("stednavn", kommuner=True)),
                "GSearch skelner mellem seværdigheden og stationen i København V. Bifrost "
                "giver to gange \"Rådhuspladsen\" i kommune 0101.",
            ),
        ),
        issue=1,
    ),
    Section(
        "kommuner",
        "Kommuner og postnumre på stednavne og veje",
        """
I GSearch har et stednavn eller en navngiven vej alle de kommuner, det ligger i. I
Bifrost har et stednavn højst én kommune i optagelserne, også når det strækker sig over
flere. Nogle veje har også færre kommuner og postnumre end i GSearch, mens andre veje
har de samme. Optagelserne viser ikke, hvorfor.

Pluginets kommunefilter beholder et stednavn, hvis en af dets kommuner i Bifrost er
valgt. Et stednavn, der strækker sig over flere kommuner, bliver derfor skjult, når
filteret står på en af de kommuner, Bifrost ikke har på objektet. Pluginets testcase
`ste-gudenaa-kommunefilter-730` viser det for Gudenå og Randers (se REPORT.md).
""",
        (
            Example(
                "gudenaa-k730",
                (
                    gs("stednavn", 1, kommuner=True),
                    bf("stednavn", 1, only=exact("Gudenå"), kommuner=True),
                ),
                "Søgning med kommunefilter 730 (Randers). GSearch har otte kommuner på "
                "Gudenå, bl.a. 0730. Bifrost har kun 0740.",
            ),
            Example(
                "koebenhavn",
                (
                    gs("stednavn", 1, kommuner=True),
                    bf("stednavn", 5, only=exact("København"), kommuner=True),
                ),
                "GSearch har otte kommuner på byen København. Bifrosts stednavne "
                "København har hver én kommune.",
            ),
            Example(
                "furesoe",
                (
                    gs("stednavn", 1, kommuner=True),
                    bf("stednavn", 1, only=exact("Furesø"), kommuner=True),
                ),
                "GSearch har tre kommuner på søen. Bifrost har én.",
            ),
            Example(
                "lyngby-k230-173",
                (
                    gs("stednavn", 3, only=prefix("Lyngby"), kommuner=True),
                    bf("stednavn", 10, only=prefix("Lyngby"), kommuner=True),
                ),
                "GSearch har flere kommuner på Lyngby og Lyngby Sø. Bifrost har én "
                "kommune på hvert stednavn.",
            ),
            Example(
                "roskilde-fjord-k265",
                (
                    gs("stednavn", 1, kommuner=True),
                    bf("stednavn", 1, only=exact("Roskilde Fjord"), kommuner=True),
                ),
                "GSearch har fire kommuner på Roskilde Fjord. Bifrost har ingen.",
            ),
            Example(
                "skodsborg",
                (
                    gs("stednavn", 1, only=prefix("Skodsborg ("), kommuner=True),
                    bf("stednavn", 1, only=exact("Skodsborg"), kommuner=True),
                ),
                "Byen Skodsborg: GSearch har to kommuner, Bifrost én.",
            ),
            Example(
                "skodsborg-strandvej-k173",
                (
                    gs("navngivenvej", 1, kommuner=True),
                    bf(
                        "street",
                        1,
                        only=prefix("Skodsborg Strandvej"),
                        kommuner=True,
                        postnumre=True,
                    ),
                ),
                "Vejen Skodsborg Strandvej: GSearch har to kommuner og to postnumre "
                "(2942, 2950). Bifrost har én kommune og ét postnummer.",
            ),
            Example(
                "lyngby-hovedgade-k157",
                (
                    gs("navngivenvej", 1, kommuner=True),
                    bf(
                        "street",
                        1,
                        only=prefix("Lyngby Hovedgade"),
                        kommuner=True,
                        postnumre=True,
                    ),
                ),
                "GSearch har to kommuner på vejen. Bifrost har én.",
            ),
            Example(
                "noerrebrogade-2400",
                (
                    gs("navngivenvej", 1),
                    bf("street", 10, only=prefix("Nørrebrogade, 2"), postnumre=True),
                ),
                "GSearch har postnumrene 2200 og 2400 på Nørrebrogade i København. "
                "Bifrost har kun 2200.",
            ),
            Example(
                "skodsb",
                (
                    gs("navngivenvej", 1, only=prefix("Skodsborgvej ("), kommuner=True),
                    bf(
                        "street",
                        1,
                        only=exact("Skodsborgvej"),
                        kommuner=True,
                        postnumre=True,
                    ),
                ),
                "Til sammenligning: på Skodsborgvej har Bifrost de samme to kommuner "
                "som GSearch.",
            ),
        ),
        issue=35,
        stats="kommuner",
    ),
    Section(
        "kommunefilter",
        "Kommunefilter",
        """
GSearch kan filtrere på kommune i selve søgningen. Bifrost tilbyder det ikke på
`/search`. Pluginet filtrerer derfor selv blandt de hits, Bifrost sender. Optagelserne
har hentet 100 hits pr. target, og de ønskede hits er ikke altid blandt dem.
`/resolve` kan låses til en kommune.
""",
        (
            Example(
                "1a-k615",
                (gs("matrikel"), bf("ejendom", 3), bf("ejendom", 3, in_filter=True)),
                "GSearch giver matrikler 1a i kommune 615. Ingen af de 100 ejendomme, "
                "Bifrost sender, ligger i kommunen. Et filter på kommunen efterlader intet.",
            ),
            Example(
                "vor-frue-k101-851",
                (gs("stednavn"), bf("stednavn", 3), bf("stednavn", 3, in_filter=True)),
                "GSearch giver Vor Frue Kirke i de to kommuner. Bifrost sender stednavne "
                "fra hele landet. 5 af de 100 ligger i kommunerne, heriblandt to gange "
                "Vor Frue Kirke. Her finder et filter på kommunerne altså kirkerne.",
            ),
            Example(
                "vestergade-k751",
                (gs("navngivenvej", 1), bf("resolve", 1, confidence=True), bf("street", 3)),
                "`/resolve`, låst til kommunen, finder Vestergade i Aarhus. `/search` "
                "uden filter giver Vestergade i andre byer først.",
            ),
        ),
        issue=2,
    ),
    Section(
        "matrikel",
        "Matrikler og ejendomme",
        """
GSearchs `matrikel` giver jordstykker. Bifrost tilbyder ikke søgning i jordstykker. Det
nærmeste er `/search` med target `ejendom`, som giver ejendomme (BFE). En ejendom kan
bestå af mange jordstykker.
""",
        (
            Example(
                "3kg",
                (gs("matrikel", 5), bf("ejendom", 5, parcels=True)),
                "Bifrosts hits er ejendomme. \"3kg, Vangede\" er en ejendom med 27 "
                "jordstykker. Rækkefølgen er også forskellig.",
            ),
            Example(
                "3kg-soell",
                (gs("matrikel"), bf("ejendom", 4)),
                "GSearch finder 3kg i både Øverød By og Søllerød By. Bifrost giver kun "
                "Søllerød By og derefter matrikler, der ligner.",
            ),
            Example(
                "6033528",
                (gs("matrikel"), bf("ejendom", confidence=True)),
                "Søgning på BFE-nummer: begge finder ejendommen.",
            ),
        ),
        issue=4,
    ),
    Section(
        "navne",
        "Navne og rangering",
        """
Nogle objekter hedder noget andet i Bifrost end i GSearch. I nogle søgninger giver
Bifrosts `/resolve` en anden type først end den, man søgte efter.
""",
        (
            Example(
                "101",
                (gs("kommune"), bf("kommune")),
                "Begge finder kommune 101. GSearch kalder den \"Københavns Kommune\", "
                "Bifrost \"København\".",
            ),
            Example(
                "koebenhavn",
                (gs("politikreds", 2), bf("politikreds", 2)),
                "Politikredse hedder \"Politikreds\" i GSearch og \"Politi\" i Bifrost.",
            ),
            Example(
                "hovedstaden",
                (gs("region", 1), bf("resolve"), bf("region", 1)),
                "Begge finder regionen som region. Bifrosts `/resolve` giver veje "
                "først.",
            ),
            Example(
                "roskilde-fjord",
                (gs("stednavn", 1), bf("resolve"), bf("stednavn", 1, confidence=True)),
                "Begge finder fjorden som stednavn. Bifrosts `/resolve` giver veje "
                "først.",
            ),
        ),
    ),
    Section(
        "fejl",
        "Fejl under optagelsen",
        """
Enkelte opslag fejlede under optagelsen. De er gemt, som de var. De siger ikke noget om,
hvor ofte tjenesterne fejler.
""",
        (
            Example(
                "1a-soenderby",
                (gs("husnummer"), bf("resolve")),
                "Bifrosts `/resolve` svarede HTTP 504.",
            ),
            Example(
                "koebenhavn",
                (gs("adresse"), bf("resolve")),
                "GSearchs `adresse` svarede HTTP 502.",
            ),
        ),
    ),
    Section(
        "bifrost-bedre",
        "Hvor Bifrost er bedre eller lige så god",
        """
Bifrost finder meget af det samme som GSearch, når hele ord skrives. Bifrost har også
nye søgetyper, som GSearch ikke havde, fx byer (`city`) og ejerlav (se
[#6](https://github.com/AsgerPetersen/qgis-geosearch/issues/6)).
""",
        (
            Example(
                "noeddebogade-1-st-th",
                (gs("husnummer"), gs("adresse", 1), bf("resolve", 1, confidence=True)),
                "Bifrost finder lejligheden. GSearchs `husnummer`, som pluginet 3.x "
                "brugte, giver ingen hits. GSearchs `adresse` finder den.",
            ),
            Example(
                "1an-gentofte",
                (gs("matrikel_udgaaet"), bf("ejendom_retired", 1, confidence=True)),
                "Udgåede matrikler: begge finder 1an, Gentofte.",
            ),
            Example(
                "8000",
                (gs("postnummer"), bf("postcode", 1, confidence=True)),
                "Begge finder postnummeret.",
            ),
            Example(
                "aabenraa",
                (gs("postnummer", 1), bf("postcode", 1, confidence=True)),
                "Den gamle stavemåde Åbenrå: begge finder Aabenraa.",
            ),
            Example(
                "skodsb",
                (bf("city", 1, confidence=True),),
                "Ny type: Bifrosts `city` giver byen Skodsborg.",
            ),
        ),
    ),
)
