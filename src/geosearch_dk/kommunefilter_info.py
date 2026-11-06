"""User-facing texts about the client-side kommune filter (#11).

Shown in the settings page, in the explanation behind the grey "skjult" row
and in the migration notice. Pure Python: must not import qgis or PyQt.
"""

INFO_TITLE = "Sådan virker kommunefilteret nu – og hvad du skal være opmærksom på"

INFO_BODY_HTML = (
    "<p>Den nye søgetjeneste (Bifrost) kan ikke filtrere på kommune. Når du "
    "slår filteret til, henter pluginet derfor flere resultater og skjuler "
    "dem, der ligger uden for dine kommuner. Det betyder:</p>"
    "<ul>"
    "<li><b>Du kan gå glip af resultater.</b> Pluginet ser kun på Bifrosts "
    "100 bedste hits for hele landet. Ligger det, du leder efter, længere "
    "nede, bliver det ikke vist. Eksempel: matrikel \"1a\" med filter "
    "på Horsens (615) giver <i>ingen</i> resultater, selvom der findes "
    "mange.</li>"
    "<li><b>Adresser virker bedst.</b> For adresser sender pluginet kommunen "
    "med til Bifrost, så adresser i kommunen kommer først.</li>"
    "<li><b>Stednavne</b> vurderes ud fra ét punkt. Store områder (fx en "
    "landsdel eller en å), som strækker sig over flere kommuner, kan blive "
    "skjult.</li>"
    "<li><b>Regioner, kredse og byer</b> vises, hvis de overlapper din "
    "kommune.</li>"
    "<li><b>Søgningen kan blive lidt langsommere</b>, fordi der hentes flere "
    "resultater.</li>"
    "<li>Tip: Skriv bynavn eller postnummer med i søgningen "
    "(\"vestergade 1 horsens\"). Det virker godt for adresser. For "
    "matrikler matcher bynavnet derimod ejerlavet, så \"1a horsens\" "
    "giver Horsens By i Aalborg Kommune.</li>"
    "<li>Resultater, der er skjult af filteret, vises som en grå linje nederst "
    "i listen: \"12 resultater uden for kommunefilteret er skjult\".</li>"
    "</ul>"
)

INFO_HTML = "<p><b>" + INFO_TITLE + "</b></p>" + INFO_BODY_HTML

MIGRATION_TEXT = "Kommunefilteret virker nu anderledes – læs hvorfor"

# Section in help/hvad_er_nyt.html that explains the filter.
WHATSNEW_ANCHOR = "kommunefilter"


def hidden_row_text(count):
    """Text of the grey last row in the result list, or None for ``count`` 0."""
    if count <= 0:
        return None
    noun = "resultat" if count == 1 else "resultater"
    return "%d %s uden for kommunefilteret er skjult" % (count, noun)
