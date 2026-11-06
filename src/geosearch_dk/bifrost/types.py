"""The search types the plugin offers, as data.

Adding a type means adding a ``SearchType`` to ``TYPES`` (or moving one from
``PROPOSED_TYPES``). Request building, normalisation, display texts and the
kommune filter are all driven by the fields below.

Pure Python: must not import qgis or PyQt.
"""

from collections import OrderedDict
from typing import NamedTuple, Optional, Tuple

RESOLVE = "resolve"
SEARCH = "search"
PROJECT = "project"

# How the kommune filter decides whether a hit lies in a kommune (#11).
# FILTER_COMPONENTS: the hit's own components.kommuner.
# FILTER_PROJECT: membership in /project(kommune ref -> target), fetched per session.
FILTER_COMPONENTS = "components"
FILTER_PROJECT = "project"

# "mat" now finds whole properties (BFE), not parcels, and the label is
# undecided (#4). Keep the user-facing wording here only.
MAT_TITLE = "Matrikelnumre"


class SearchType(NamedTuple):
    # Prefix ("adr:") and settings suffix ("search_adr").
    key: str
    # Plural label for settings and error rows.
    title: str
    # RESOLVE or SEARCH.
    endpoint: str
    # Bifrost ref kind of the rows this type produces; also the /search target.
    target: str
    # Sent as "lifecycle" when set. Bifrost defaults to ["current"].
    lifecycle: Optional[Tuple[str, ...]] = None
    kommune_filter: str = FILTER_COMPONENTS
    # RESOLVE only: also show apartments (units with floor/door) under this type.
    accept_units: bool = False


# Today's eight types, in display order (the order of the old settings.resources).
TYPES = (
    SearchType("adr", "Husnumre", RESOLVE, "entrance", accept_units=True),
    SearchType("ste", "Stednavne", SEARCH, "stednavn"),
    SearchType("pos", "Postdistrikter", SEARCH, "postcode"),
    SearchType("mat", MAT_TITLE, SEARCH, "ejendom"),
    SearchType("kom", "Kommuner", SEARCH, "kommune"),
    SearchType(
        "ops",
        "Opstillingskredse",
        SEARCH,
        "opstillingskreds",
        kommune_filter=FILTER_PROJECT,
    ),
    SearchType(
        "pol", "Politikredse", SEARCH, "politikreds", kommune_filter=FILTER_PROJECT
    ),
    SearchType("reg", "Regioner", SEARCH, "region", kommune_filter=FILTER_PROJECT),
)

# The types 3.x offered are searched by default. A type added later (e.g. from
# PROPOSED_TYPES) starts switched off, also for users upgrading from 3.x.
DEFAULT_ON_KEYS = frozenset(("adr", "ste", "pos", "mat", "kom", "ops", "pol", "reg"))

# Candidates from #6 (undecided). Not offered in the UI; kept here so that
# deciding #6 is a data change. They go through exactly the same code paths.
PROPOSED_TYPES = (
    SearchType("sog", "Sogne", SEARCH, "sogn"),
    SearchType("vej", "Navngivne veje", SEARCH, "street"),
    SearchType("ret", "Retskredse", SEARCH, "retskreds", kommune_filter=FILTER_PROJECT),
    SearchType("udg", "Udgåede matrikler", SEARCH, "ejendom", lifecycle=("retired",)),
    SearchType(
        "by",
        "Byer (postdistriktsnavne)",
        SEARCH,
        "city",
        kommune_filter=FILTER_PROJECT,
    ),
    SearchType("ejl", "Ejerlav", SEARCH, "ejerlav", kommune_filter=FILTER_PROJECT),
)


class BifrostRequest(NamedTuple):
    """One HTTP request: ``POST {base_url}/{endpoint}`` with ``body`` as JSON.

    ``body`` is a dict, or a list of dicts for a Bifrost batch (the response is
    then a list in the same order). ``keys`` are the type keys whose rows come
    from this request: for a /search batch, ``keys[i]`` belongs to ``body[i]``.
    """

    endpoint: str
    body: object
    keys: Tuple[str, ...] = ()


def types_by_key(types=TYPES):
    """Ordered ``{key: SearchType}``."""
    return OrderedDict((t.key, t) for t in types)
