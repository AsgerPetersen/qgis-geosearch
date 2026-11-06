"""Client-side kommune filter (#11).

Bifrost has no filter parameter on /search, so the plugin filters the hits
itself:

* /resolve pins the kommune (``components.kommune``), one batch element per code.
* Types with ``kommune_filter == FILTER_COMPONENTS`` are kept when one of the
  hit's ``components.kommuner`` is selected.
* Types with ``kommune_filter == FILTER_PROJECT`` (regions, kredse, ...) carry
  no kommune in their components. They are kept when their ref id is a member
  of /project(kommune ref -> target). The caller fetches the members once per
  kommune and target and caches them; this module only builds the requests and
  reads the responses.

Pure Python: must not import qgis or PyQt.
"""

import re

from .types import FILTER_PROJECT, PROJECT, SEARCH, BifrostRequest

PROJECT_MAX_LIMIT = 500


class UnknownKommune(ValueError):
    """A kommunekode in the filter that Bifrost does not know."""

    def __init__(self, code):
        super().__init__("Ukendt kommunekode %s" % code)
        self.code = code


def parse_kommunekoder(text):
    """Kommunekoder in a free-text setting, as 4-digit strings in input order.

    Like the GSearch plugin, every group of digits is a code; separators are
    free. Three-digit codes are padded ("101" -> "0101"). Duplicates are dropped.
    """
    codes = []
    for group in re.findall(r"\d+", text or ""):
        code = group.zfill(4)
        if code not in codes:
            codes.append(code)
    return tuple(codes)


def kommune_ref_request(code):
    """Request that looks up the Bifrost ref of kommune ``code``."""
    return BifrostRequest(SEARCH, {"input": code, "target": "kommune", "limit": 1})


def kommune_ref_from_response(code, response):
    """The ``{"kind", "id"}`` ref from a ``kommune_ref_request`` response.

    Raises ``UnknownKommune`` when the top hit is not kommune ``code``.
    """
    matches = (response or {}).get("matches") or []
    if matches:
        match = matches[0]
        kommuner = (match.get("components") or {}).get("kommuner") or []
        if any(k.get("kommunekode") == code for k in kommuner):
            return dict(match["ref"])
    raise UnknownKommune(code)


def membership_request(ref, target, cursor=None, limit=PROJECT_MAX_LIMIT):
    """One page of the ``target`` refs inside the kommune ``ref``."""
    body = {"input": dict(ref), "target": target, "limit": limit}
    if cursor:
        body["cursor"] = cursor
    return BifrostRequest(PROJECT, body)


def membership_from_response(response):
    """``(ids, next_cursor)`` from a ``membership_request`` response.

    ``next_cursor`` is None on the last page; otherwise request the next page
    with ``membership_request(ref, target, cursor=next_cursor)``.
    """
    response = response or {}
    ids = {m["ref"]["id"] for m in response.get("matches") or []}
    return ids, response.get("next") or None


def membership_targets(types):
    """Targets whose filter needs /project memberships, in type order."""
    targets = []
    for t in types:
        if t.kommune_filter == FILTER_PROJECT and t.target not in targets:
            targets.append(t.target)
    return tuple(targets)


def in_kommuner_by_components(row, codes):
    kommuner = (row.get("components") or {}).get("kommuner") or []
    return any(k.get("kommunekode") in codes for k in kommuner)


def in_kommuner_by_membership(row, member_ids):
    return (row.get("ref") or {}).get("id") in member_ids


class MissingMembership(KeyError):
    """``apply_kommunefilter`` needs memberships for a target it was not given."""


def apply_kommunefilter(rows, codes, members, search_type):
    """Split ``rows`` of one type into ``(kept, hidden_count)``.

    ``members`` maps a target to the set of ref ids inside any of ``codes``
    (the union over the selected kommuner). It is only read for types with
    ``FILTER_PROJECT``. Error rows are always kept. With no codes, everything
    is kept.
    """
    if not codes:
        return list(rows), 0
    codes = set(codes)
    if search_type.kommune_filter == FILTER_PROJECT:
        if members is None or search_type.target not in members:
            raise MissingMembership(search_type.target)
        member_ids = members[search_type.target]

        def keep(row):
            return in_kommuner_by_membership(row, member_ids)

    else:

        def keep(row):
            return in_kommuner_by_components(row, codes)

    kept = []
    hidden = 0
    for row in rows:
        if row.get("status") != "ok" or keep(row):
            kept.append(row)
        else:
            hidden += 1
    return kept, hidden
