# Draft: upstream PR description (Septima/qgis-geosearch)

<!--
  Draft of the description for the PR from the bifrost branch to
  Septima/qgis-geosearch. The bullets are the same as in
  src/geosearch_dk/help/hvad_er_nyt.html and README.md ("Overgang til Bifrost");
  update them together.
-->

## Geosearch DK 4.0: fra GSearch til Bifrost

Klimadatastyrelsen lukker søgetjenesten GSearch i november 2026. Denne PR
flytter Geosearch DK over på Klimadatastyrelsens nye søgetjeneste, **Bifrost**,
så pluginet kan bruges, efter at GSearch er lukket. Pluginet understøtter både
QGIS 3 (Qt5) og QGIS 4 (Qt6).

Brugerne får forskellene at vide i en "Hvad er nyt"-dialog, som kun åbner, når
brugeren klikker. Brugere, der opdaterer fra 3.x, ser en lille blå bjælke i
søgepanelet med et link til dialogen og en rød prik på ⓘ-knappen, indtil de har
åbnet den. Bjælken kan lukkes, og dialogen kan altid åbnes med ⓘ-knappen. Nye
brugere ser hverken bjælken eller prikken. Teksten er
`src/geosearch_dk/help/hvad_er_nyt.html`, og på engelsk
`hvad_er_nyt.en.html`. Kører QGIS på engelsk (fx `en_DK`), er hele pluginet på
engelsk; ellers er det på dansk.

### Nøgle til Bifrost
Bifrost kræver sin egen API-nøgle; et token til Dataforsyningen kan ikke
bruges, så opdateringen fjerner et gemt token. Pluginet har endnu ingen
indbygget nøgle (`DEFAULT_BIFROST_KEY` er tom). Det er endnu ikke afklaret med
Klimadatastyrelsen, om pluginet må få en fælles nøgle. Indtil da indtaster
brugerne selv en nøgle i indstillingerne eller i miljøvariablen `BIFROST_KEY`.
Så længe der ingen nøgle er, viser søgepanelet en gul bjælke med et link til
nøglefeltet i indstillingerne.

### Nyt
- **Lejligheder:** Man kan nu finde adresser med etage og dør.

### Virker anderledes
- **Teksten i resultatlisten** laves nu af pluginet. Stednavne vises som
  *navn (type, kommune)*, fx *Skodsborg (bebyggelse, Rudersdal)*.
- **Matrikelnumre** finder nu hele ejendommen (BFE), som matriklen hører til,
  og kortet viser hele ejendommen. Det præcise matrikelnummer står øverst i
  listen.
- **Kortet** zoomer først til et punkt. Den fulde geometri, fx en vej eller en
  ejendom, kommer et øjeblik efter.
- **Kommunefilteret** er nu et valg, man selv slår til i indstillingerne.
  Pluginet henter resultater for hele landet og skjuler dem uden for de valgte
  kommuner. Man kan derfor gå glip af resultater, fordi pluginet kun ser på
  Bifrosts 100 bedste hits for hele landet. Adresser virker bedst. Brugere, der
  havde et kommunefilter i den gamle version, får det slået til og får en
  besked om det.

### Hvad den nye version IKKE kan, og hvorfor

Det følgende kunne ikke porteres. Pluginet kan ikke arbejde uden om det, fordi
det sker i søgetjenesten.

- **Søgning på dele af ord.** GSearch matchede på begyndelsen af ord, så
  *nørrebrog* fandt Nørrebrogade. Bifrost matcher hele ord med tolerance for
  stavefejl, så et halvt ord bliver rettet til det nærmeste hele ord i stedet
  for at blive fuldført. Brugerne skal skrive hele ord, fx
  *nørrebrogade 1 københavn*. Dette er den største ændring for brugerne.
  [Prøv selv](https://asgerpetersen.github.io/gsearch-bifrost-compare/direct.html?q=n%C3%B8rrebrog)\
  *Hvorfor: Bifrost tilbyder det ikke.*
- **Kommunefilter i søgetjenesten.** GSearch filtrerede på kommune på serveren,
  så man fik alle hits i de valgte kommuner. Bifrost har ingen kommunefilter
  på `/search`, så pluginet filtrerer selv i Bifrosts 100 bedste hits for hele
  landet. Fx giver matrikel *1a* med filter på Horsens (615) ingen resultater.
  [Prøv selv](https://asgerpetersen.github.io/gsearch-bifrost-compare/direct.html?q=1a&t=matrikel&n=10&k=615)\
  *Hvorfor: Bifrost tilbyder det ikke.*
- **Stednavnets undertype.** GSearch viste fx *Skodsborg (By i Rudersdal
  Kommune)*. Bifrost giver kun en overordnet type, fx *bebyggelse* eller
  *naturareal*, og én kommune, så steder med samme navn kan være svære at
  skelne. [Prøv selv](https://asgerpetersen.github.io/gsearch-bifrost-compare/direct.html?q=vendsyssel&t=stednavn)\
  *Hvorfor: Bifrost tilbyder det ikke.*

På [sammenligningssiden](https://asgerpetersen.github.io/gsearch-bifrost-compare/)
kan man søge i GSearch og Bifrost side om side.
