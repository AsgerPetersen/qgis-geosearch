#!/usr/bin/env python3
"""Record Bifrost responses for the unit tests into tests/fixtures/bifrost/.

Each case is run through the core (``plan_search`` etc.), so the recorded
request bodies are exactly what the plugin sends; the unit tests check that
they still are. The key is read from the environment and is never written.

    BIFROST_KEY=... uv run python tests/tools/record_bifrost.py [case ...]

Environment:
    BIFROST_KEY   API key (required)
    BIFROST_URL   default https://bifrost.test42.dataforsyningen.dk
"""

import json
import os
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "src"))

from geosearch_dk.bifrost import (  # noqa: E402
    PROPOSED_TYPES,
    TYPES,
    UnknownKommune,
    collect_rows,
    geometry_from_response,
    geometry_request,
    kommune_ref_from_response,
    kommune_ref_request,
    membership_from_response,
    membership_request,
    plan_search,
)

FIXTURES = os.path.join(ROOT, "tests", "fixtures", "bifrost")
DEFAULT_URL = "https://bifrost.test42.dataforsyningen.dk"
ALL = [t.key for t in TYPES]
MAX_MEMBERSHIP_PAGES = 10

# name: (text, selected keys, kommunefilter, record geometry of the first row,
#        use the proposed (#6) types as well)
CASES = {
    "adr_vangebovej_71": ("Vangebovej 71", ["adr"], "", True, False),
    "adr_noeddebogade_1_st_th": ("Nøddebogade 1 st th", ["adr"], "", False, False),
    "adr_vestergade_1_kbh": ("Vestergade 1", ["adr"], "101", False, False),
    "adr_vestergade_1_kbh_aarhus": ("Vestergade 1", ["adr"], "101, 751", False, False),
    "all_skodsborg": ("skodsborg", ALL, "", False, False),
    "ste_pos_reg_skodsborg_rudersdal": (
        "skodsborg",
        ["ste", "pos", "reg"],
        "230",
        False,
        False,
    ),
    "all_aarhus": ("aarhus", ALL, "", False, False),
    "all_aarhus_kommune_751": ("aarhus", ALL, "751", False, False),
    "ste_skodsborg": ("ste: skodsborg", ALL, "", True, False),
    "mat_3kg_soell": ("mat: 3kg søll", ALL, "", True, False),
    "pos_8000": ("pos: 8000", ALL, "", False, False),
    "kom_koebenhavn": ("kom:københavn", ALL, "", False, False),
    "unknown_kommune": ("skodsborg", ["ste"], "9999", False, False),
    "proposed_vor_frue": ("vor frue", ["sog"], "", False, True),
    "proposed_skodsborgvej": ("skodsborgvej", ["vej"], "", False, True),
    "proposed_lyngby_retskreds": ("lyngby", ["ret"], "", False, True),
    "proposed_1an_gentofte_udgaaet": ("1an gentofte", ["udg"], "", False, True),
}


def post(url, key, request):
    data = json.dumps(request.body).encode("utf-8")
    req = urllib.request.Request(
        "%s/%s" % (url.rstrip("/"), request.endpoint),
        data=data,
        headers={
            "Authorization": "Bearer " + key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8") or "null")


def exchange(url, key, request):
    status, response = post(url, key, request)
    return {
        "endpoint": request.endpoint,
        "body": request.body,
        "keys": list(request.keys),
        "status": status,
        "response": response,
    }


def trim_to_ref(ex, ref_id):
    """Stednavn geometry searches return up to 100 whole geometries; keep the one we use."""
    matches = ex["response"].get("matches") or []
    kept = [m for m in matches if m["ref"]["id"] == ref_id]
    ex["response"]["matches"] = kept
    ex["trimmed"] = "kept %d of %d matches (same ref id)" % (len(kept), len(matches))


def record(name, url, key):
    text, selected, kommunefilter, want_geometry, proposed = CASES[name]
    types = TYPES + PROPOSED_TYPES if proposed else TYPES
    plan = plan_search(text, selected, kommunefilter, types=types)
    out = {
        "case": {
            "text": text,
            "selected": selected,
            "kommunefilter": kommunefilter,
            "proposed": proposed,
        },
        "requests": [exchange(url, key, r) for r in plan.requests],
        "kommune_refs": {},
        "memberships": {},
        "geometry": None,
    }
    # geometry: {"row_index": i, "attempts": [exchange, ...]} for the first ok row

    members = {t: set() for t in plan.membership_targets}
    for code in plan.kommuner:
        ref_ex = exchange(url, key, kommune_ref_request(code))
        out["kommune_refs"][code] = ref_ex
        try:
            ref = kommune_ref_from_response(code, ref_ex["response"])
        except UnknownKommune:
            continue
        for target in plan.membership_targets:
            pages = []
            cursor = None
            for _ in range(MAX_MEMBERSHIP_PAGES):
                ex = exchange(url, key, membership_request(ref, target, cursor))
                pages.append(ex)
                ids, cursor = membership_from_response(ex["response"])
                members[target] |= ids
                if not cursor:
                    break
            out["memberships"].setdefault(code, {})[target] = pages

    if want_geometry:
        responses = [ex["response"] for ex in out["requests"]]
        rows = collect_rows(plan, responses, members).rows
        ok = [r for r in rows if r["status"] == "ok"]
        if ok:
            row = ok[0]
            attempts = []
            attempt = 0
            request = geometry_request(row, attempt)
            while request:
                ex = exchange(url, key, request)
                found = geometry_from_response(row, ex["response"])
                if row["kind"] == "stednavn":
                    trim_to_ref(ex, row["ref"]["id"])
                attempts.append(ex)
                if found:
                    break
                attempt += 1
                request = geometry_request(row, attempt)
            out["geometry"] = {"row_index": rows.index(row), "attempts": attempts}
    return out


def main(argv):
    key = os.environ.get("BIFROST_KEY")
    if not key:
        sys.exit("Set BIFROST_KEY")
    url = os.environ.get("BIFROST_URL", DEFAULT_URL)
    names = argv or list(CASES)
    os.makedirs(FIXTURES, exist_ok=True)
    for name in names:
        data = record(name, url, key)
        text = json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True)
        if key in text:
            sys.exit("Refusing to write %s: it contains the key" % name)
        with open(os.path.join(FIXTURES, name + ".json"), "w", encoding="utf-8") as f:
            f.write(text + "\n")
        print("%-34s %7d bytes" % (name, len(text)))


if __name__ == "__main__":
    main(sys.argv[1:])
