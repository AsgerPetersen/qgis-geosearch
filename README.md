Geosearch DK
==============

QGIS-plugin der tilføjer en søgeboks der anvender offentlige data, som tillader brugeren lynhurtigt at zoome til navngivne steder i Danmark - f.eks. adresser, stednavne, kommuner.

Pluginet er udviklet af [Septima](http://www.septima.dk) og stilles frit og gratis til rådighed for QGIS-brugere under GNU General Public License v3.0, se nærmere i afsnittet [Ophavsret og videredistribution](#ophavsret-og-videredistribution).

Overgang til Bifrost
--------------
Klimadatastyrelsen lukker søgetjenesten [GSearch](https://github.com/Klimadatastyrelsen/gsearch) i november 2026. Fra version 4.0 bruger Geosearch DK derfor Klimadatastyrelsens nye søgetjeneste, **Bifrost**. Det meste virker som før, men der er nogle forskelle. Efter opdateringen viser søgepanelet en lille blå bjælke med et link til forskellene, og du kan altid finde dem igen under ⓘ-knappen i søgepanelet.

**Du skal bruge en nøgle til Bifrost**\
Bifrost kræver sin egen API-nøgle. Et token til Dataforsyningen kan ikke bruges, så pluginet har fjernet det token, du måske havde angivet i den gamle version.
Pluginet har endnu ingen indbygget nøgle. Så længe der ingen nøgle er, viser søgepanelet en gul bjælke. Indtil videre skal du selv indtaste en nøgle: Klik på *Indtast nøgle* i den gule bjælke eller på skruenøglen i søgepanelet (eller vælg *Indstillinger → Indstillinger → Geosearch DK*), og indsæt den under **Bifrost API-nøgle**. [Sådan opretter du en bruger på Dataforsyningen](https://www.klimadatastyrelsen.dk/data/dataforsyningen/vi-fremtidssikrer-dataforsyningen). Din IT-afdeling kan også sætte nøglen for alle med miljøvariablen `BIFROST_KEY`.

**Nyt**
- **Lejligheder:** Du kan nu finde adresser med etage og dør.

**Virker anderledes**
- **Teksten i resultatlisten** laves nu af pluginet. Stednavne vises som *navn (type, kommune)*, fx *Skodsborg (bebyggelse, Rudersdal)*.
- **Matrikelnumre** finder nu hele ejendommen (BFE), som matriklen hører til, og kortet viser hele ejendommen. Det præcise matrikelnummer står øverst i listen.
- **Kortet** zoomer først til et punkt. Den fulde geometri, fx en vej eller en ejendom, kommer et øjeblik efter.
- **Kommunefilteret** er nu et valg, du selv slår til i indstillingerne. Bifrost kan ikke filtrere på kommune, så pluginet henter resultater for hele landet og skjuler dem uden for dine kommuner. Du kan derfor gå glip af resultater: pluginet ser kun på Bifrosts 100 bedste hits for hele landet. Adresser virker bedst. Brugte du kommunefilteret i den gamle version, er det slået til.

**Virker ikke længere – og hvorfor**
- **Søgning på dele af ord.** *nørrebrog* finder ikke længere Nørrebrogade. Skriv hele ord, fx *nørrebrogade 1 københavn*. Til gengæld retter Bifrost små stavefejl.\
  *Hvorfor: Bifrost tilbyder det ikke.*
- **Kommunefilter i søgetjenesten.** GSearch filtrerede på kommune, så du fik alle hits i dine kommuner. Nu filtrerer pluginet selv, og det kan give færre resultater (se Kommunefilteret ovenfor).\
  *Hvorfor: Bifrost tilbyder det ikke.*
- **Stednavnets undertype.** GSearch viste fx *Skodsborg (By i Rudersdal Kommune)*. Nu vises kun en overordnet type, fx *bebyggelse* eller *naturareal*, så steder med samme navn kan være svære at skelne.\
  *Hvorfor: Bifrost tilbyder det ikke.*

På [sammenligningssiden](https://asgerpetersen.github.io/gsearch-bifrost-compare/) kan du søge i GSearch og Bifrost side om side.

Teksten i pluginet findes i [src/geosearch_dk/help/hvad_er_nyt.html](src/geosearch_dk/help/hvad_er_nyt.html).

Installation af pluginet
--------------
Pluginet er tilgængeligt fra QGIS' officielle plugin repository, dermed finder en installation af QGIS selv en kompatibel version af pluginet.

Det letteste er at installere pluginet via QGIS. Dette gør du således:
   * Under menuen 'Plugins', vælg 'Administrér og Installér Plugins...' (I den engelske version af QGIS hedder denne menu 'Manage and Install Plugins...')
   * I Plugins-dialogen, søg efter 'Geosearch DK'
   * Vælg 'Geosearch DK' i listen (så denne bliver markeret med blå)
   * Klik på 'Installér Plugin'. Derefter installeres pluginet.

![Install-geosearchdk](https://github.com/Septima/qgis-geosearch/assets/16276034/3b5a5d6c-70fe-49a0-9372-1fdb18585831)


Pluginet installerer et QGIS-panel med en søgeboks, der som udgangspunkt lægger sig oven for kortvinduet. Panelet kan flyttes, så det f.eks. ligger oven for lagpanelet i stedet. På denne placering fylder det ikke så meget, men er stadig let tilgængeligt.

Hvis man trykker på krydset i Geosearch DK-panelet bliver det deaktiveret og forsvinder helt fra visningen, men kan nemt genaktiveres ved at sætte flueben ved det under menupunktet Visning->Paneler (på engelsk View->Panels).

Pluginet kræver en API-nøgle til Bifrost (se [Overgang til Bifrost](#overgang-til-bifrost)). Nøglen angives under pluginets indstillinger, som findes ved at gå til menupunktet Indstillinger->Indstillinger->Geosearch DK (engelsk Settings->Options) eller bruge genvejen via skruenøgle-ikonet i panelet.

Opdatering af pluginet
--------------
Nye versioner af pluginet udstilles via QGIS' officielle plugin repository. I Plugin Manageren vil opdateringer fremgå under punktet Upgradeable. Automatisk advisering om opgraderbare plugins kan aktiveres under Settings i Plugin Manageren.

Vil du selv opdatere dit plugin, så gør således:
   * Åbn pluginsdialogen
   * Søg efter 'GeosearchDK'
   * Vælg GeosearchDK i listen
   * Klik på 'Opgradér Plugin'. Derefter opgraderes pluginet til den nyeste version.

![geosearchopgraderplugin](https://github.com/Septima/qgis-geosearch/assets/16276034/7ec1bf18-a5d4-4ba2-ae4d-089f93d6e3bc)


Indstillinger
-----------------
Du kan lave en række indstillinger i pluginets indstillingsfane, som du kan åbne ved at klikke på skruenøgle-ikonet (eller gå til menupunktet Indstillinger->Indstillinger->Geosearch DK (engelsk Settings->Options)):
![geosearchdk-opensettings](https://github.com/Septima/qgis-geosearch/assets/16276034/3f56d335-7397-4779-b7b0-c39e811fd9eb)

Følgende indstillinger kan foretages i pluginets indstillingsdialog:
- Bifrost API-nøgle. Se [Sådan opretter du en bruger på Dataforsyningen](https://www.klimadatastyrelsen.dk/data/dataforsyningen/vi-fremtidssikrer-dataforsyningen). Står feltet tomt, bruges miljøvariablen `BIFROST_KEY`. Et token til Dataforsyningen kan ikke bruges.
- Kommunefilter. Indtast et eller flere kommunenumre adskilt af komma. Pluginet skjuler så søgeresultater uden for de listede kommuner. Læs om begrænsningerne under [Overgang til Bifrost](#overgang-til-bifrost).
- Typefilter. Vis kun søgeresultater af bestemte typer, f.eks. adresser, matrikelnumre, stednavne etc.

![geosearchsettings](https://github.com/Septima/qgis-geosearch/assets/16276034/ffcfe419-38af-4ed1-80f8-bc2264919fb0)


Oplever du fejl eller har du ønsker til forbedringer eller ny funktionalitet?
-----------------
Der er allerede en række forslag til forbedringer i projektets [Issuetracker](../../issues).

Har du en idé til en forbedring eller har du måske opdaget en bug i pluginet, så vil Septima med glæde tilbyde sin bistand.

Du kan registrere din idé eller bug i projektets [Issuetracker](../../issues). Her kan du også se eksisterende registreringer af idéer og bugs.

Udvikling
-----------------
Se [docs/development.md](docs/development.md) for hvordan pluginet køres fra en checkout i en separat QGIS-profil (`make dev`), og for den visuelle kørsel og den manuelle tjekliste.

Ophavsret og videredistribution
-------------------------------
Pluginet er udviklet af [Septima](http://www.septima.dk), som er primær ophavsretsindehaver men som har givet tilladelse til distribution under betingelserne i Open Source/Fri Software-licensen [GNU General Public License v3.0](http://www.gnu.org/licenses/gpl.html) eller senere ([GPL3.0-or-later](https://spdx.org/licenses/GPL-3.0-or-later)).

Det indeholder dog også kode fra projektet [QGIS Setting Manager](https://opengisch.github.io/qgis_setting_manager/) (under stien `src/geosearch_dk/config/qgissettingmanager/`) som kan distribueres under licensen [GNU General Public License v2.0](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html) eller senere ([GPL2.0-or-later](https://spdx.org/licenses/GPL-2.0-or-later)).

Ophavsretsinformation og licensbetingelser for en konkret fil kan altid ses i toppen af den enkelte fil.
