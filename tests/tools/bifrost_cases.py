"""Run the case catalogue (tests/cases.yaml) through the Bifrost core.

Shared by ``record_bifrost.py --cases`` (records fixtures and the report),
the live suite (``pytest -m live``, tests/live/) and the offline regression
test (tests/unit/test_case_fixtures.py). A case runs the way the plugin
searches:

1. ``plan_search`` with the case's input, types and kommunefilter;
2. the kommune refs and /project memberships the kommune filter needs;
3. ``collect_rows`` -> the popup rows;
4. the full geometry of the expected hit (what clicking it fetches).

``send(request)`` does the HTTP: ``LiveSender`` against Bifrost, or
``ReplaySender`` from a recorded fixture. Expectations are the GSearch ones
(``check_expect`` in record_gsearch.py), with one relaxation: a stednavn
cannot get GSearch's text (#1), so a ``ste`` row matches on the name
before " (".
"""

import datetime as dt
import json
import math
import os
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
for p in (os.path.join(ROOT, "src"), os.path.join(ROOT, "tests"), HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

from geosearch_dk.bifrost import (  # noqa: E402
    STATUS_OK,
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
from mock_bifrost import FixtureIndex, iter_exchanges  # noqa: E402
from record_gsearch import (  # noqa: E402
    check_expect,
    geometry_kind,
    load_cases,
    load_fixture,
)

CASES_FIXTURES = os.path.join(ROOT, "tests", "fixtures", "bifrost", "cases")
REPORT_FILE = os.path.join(CASES_FIXTURES, "REPORT.md")
DEFAULT_URL = "https://bifrost.test42.dataforsyningen.dk"
ALL_KEYS = [t.key for t in TYPES]
MAX_MEMBERSHIP_PAGES = 10
MAX_VERTICES = 250  # recorded geometries are thinned to about this many vertices
REPORT_ROWS = 10

PASS, FAIL, XFAIL, XPASS, NONE = "pass", "fail", "xfail", "xpass", "none"
ICONS = {PASS: "✅", FAIL: "❌", XFAIL: "⚠️", XPASS: "🎉", NONE: "➖"}
OUTCOME_TEXT = {
    PASS: "pass",
    FAIL: "FAIL",
    XFAIL: "known gap",
    XPASS: "passes despite known gap",
    NONE: "no expectation",
}

__all__ = [
    "ALL_KEYS",
    "CASES_FIXTURES",
    "LiveSender",
    "ReplaySender",
    "case_plan",
    "load_case_fixture",
    "load_cases",
    "run_case",
    "write_report",
]


class BifrostHTTPError(Exception):
    def __init__(self, status, response):
        super().__init__("HTTP %s: %s" % (status, json.dumps(response, ensure_ascii=False)[:200]))
        self.status = status
        self.response = response


# --- senders ----------------------------------------------------------------


class LiveSender:
    """POST the request to Bifrost; returns an exchange dict (never the key)."""

    def __init__(self, url, key, timeout=60):
        self.url = url.rstrip("/")
        self.key = key
        self.timeout = timeout

    def __call__(self, request):
        req = urllib.request.Request(
            "%s/%s" % (self.url, request.endpoint),
            data=json.dumps(request.body).encode("utf-8"),
            headers={
                "Authorization": "Bearer " + self.key,
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "geosearch-dk-tests",
            },
            method="POST",
        )
        t0 = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                status, raw = resp.status, resp.read()
        except urllib.error.HTTPError as e:
            status, raw = e.code, e.read()
        except (urllib.error.URLError, OSError) as e:
            return _exchange(request, None, None, None, str(e))
        elapsed = round((time.monotonic() - t0) * 1000)
        try:
            response = json.loads(raw.decode("utf-8") or "null")
        except ValueError:
            response = raw.decode("utf-8", "replace")[:2000]
        return _exchange(request, status, response, elapsed)


class ReplaySender:
    """Answer from a recorded case fixture; unrecorded requests raise KeyError."""

    def __init__(self, fixture):
        self.index = FixtureIndex(directory=os.devnull)
        self.index.add_fixture(fixture)
        self.elapsed = {}
        for ex in iter_exchanges(fixture):
            self.elapsed[_ex_key(ex)] = ex.get("elapsed_ms")

    def __call__(self, request):
        status, response, _how = self.index.lookup(request.endpoint, request.body, strict=True)
        key = _ex_key({"endpoint": request.endpoint, "body": request.body})
        return _exchange(request, status, response, self.elapsed.get(key))


def _exchange(request, status, response, elapsed_ms, error=None):
    ex = {
        "endpoint": request.endpoint,
        "body": request.body,
        "keys": list(request.keys),
        "status": status,
        "elapsed_ms": elapsed_ms,
        "response": response,
    }
    if error:
        ex["error"] = error
    return ex


def _ex_key(ex):
    return (ex["endpoint"], json.dumps(ex["body"], sort_keys=True, ensure_ascii=False))


def _response(ex):
    """The decoded response, or the exception ``collect_rows`` expects."""
    if ex["status"] == 200:
        return ex["response"]
    if ex["status"] is None:
        return ConnectionError(ex.get("error") or "no response")
    return BifrostHTTPError(ex["status"], ex["response"])


# --- running a case -----------------------------------------------------------


def case_plan(case):
    kommunefilter = ",".join(str(k) for k in case.get("kommuner") or [])
    return plan_search(case["input"], case.get("types") or ALL_KEYS, kommunefilter)


def loose_name(text):
    return (text or "").split(" (")[0].strip().casefold()


def display_rows(rows):
    return [
        {
            "rank": i,
            "key": r["key"],
            "text": r["text"],
            "status": r["status"],
            "kind": r.get("kind"),
            "geometry": None,
        }
        for i, r in enumerate(rows, 1)
    ]


def find_hit(case, display):
    """``(index, how)`` of the expected hit in ``display``; how = exact | loose."""
    text = (case.get("expect") or {}).get("text")
    if not text:
        return None, None
    for i, row in enumerate(display):
        if row["text"] == text:
            return i, "exact"
    for i, row in enumerate(display):
        if row["key"] == "ste" and row["status"] == STATUS_OK:
            if loose_name(row["text"]) == loose_name(text):
                return i, "loose"
    return None, None


def evaluate(case, display, hit_index, how):
    """``(ok, why)`` with ``check_expect`` semantics; None = no expectation."""
    if how == "loose":
        display = [dict(r) for r in display]
        display[hit_index]["text"] = case["expect"]["text"]
    ok, why = check_expect(case, {"display": display})
    if how == "loose":
        why += " (name only, #1)"
    return ok, why


DISPLAY_TEXT_GAP = 1

# Cases that fail against Bifrost with no issue to explain them yet. The tests
# xfail them (the report still shows them as failures); give them a
# ``known_gap`` in cases.yaml once there is an issue.
KNOWN_FAILURES = {}


def bifrost_case(case):
    """The case as Bifrost should meet it: ``bifrost.expect`` replaces ``expect``."""
    override = case.get("bifrost")
    if not override or "expect" not in override:
        return case
    case = dict(case)
    if override["expect"] is None:
        case.pop("expect", None)
    else:
        case["expect"] = override["expect"]
    return case


def outcome(case, ok, how=None):
    if ok is None:
        return NONE
    gap = case.get("known_gap")
    if gap == DISPLAY_TEXT_GAP and how == "loose" and ok:
        # The name-only match is how #1 is accommodated, so this is a pass.
        return PASS
    if gap:
        return XPASS if ok else XFAIL
    return PASS if ok else FAIL


def _thin(coords, step):
    if not coords:
        return coords
    if isinstance(coords[0], (int, float)):
        return coords
    if isinstance(coords[0][0], (int, float)):
        kept = coords[::step]
        closed = coords[0] == coords[-1]
        if kept[-1] != coords[-1]:
            kept.append(coords[-1])
        if closed and len(kept) < 4:
            kept = coords[:3] + [coords[0]] if len(coords) >= 4 else coords
        return kept
    return [_thin(c, step) for c in coords]


def _count(coords):
    if not coords:
        return 0
    if isinstance(coords[0], (int, float)):
        return 1
    return sum(_count(c) for c in coords)


def thin_geojson(geojson):
    """Keep every n-th vertex so a recorded geometry stays small. None if unchanged."""
    if not isinstance(geojson, dict) or "coordinates" not in geojson:
        return None
    n = _count(geojson["coordinates"])
    if n <= MAX_VERTICES:
        return None
    step = math.ceil(n / MAX_VERTICES)
    return dict(geojson, coordinates=_thin(geojson["coordinates"], step)), n


def compact_geometry_exchange(ex, row):
    """Keep only the stednavn we asked for, and thin big geometries."""
    response = ex.get("response")
    if not isinstance(response, dict):
        return
    matches = response.get("matches") or []
    if row["kind"] == "stednavn":
        kept = [m for m in matches if (m.get("ref") or {}).get("id") == row["ref"]["id"]]
        if len(kept) != len(matches):
            ex["trimmed"] = "kept %d of %d matches (same ref id)" % (len(kept), len(matches))
        response["matches"] = matches = kept
    for m in matches:
        geometry = m.get("geometry") or {}
        thinned = thin_geojson(geometry.get("geojson"))
        if thinned:
            geometry["geojson"], n = thinned
            ex["thinned"] = "geometry thinned from %d vertices" % n


def _memberships(plan, send, out):
    members = {t: set() for t in plan.membership_targets}
    for code in plan.kommuner:
        ref_ex = send(kommune_ref_request(code))
        out["kommune_refs"][code] = ref_ex
        if ref_ex["status"] != 200:
            continue
        try:
            ref = kommune_ref_from_response(code, ref_ex["response"])
        except UnknownKommune:
            continue
        for target in plan.membership_targets:
            pages, cursor = [], None
            for _ in range(MAX_MEMBERSHIP_PAGES):
                ex = send(membership_request(ref, target, cursor))
                pages.append(ex)
                if ex["status"] != 200:
                    break
                ids, cursor = membership_from_response(ex["response"])
                members[target] |= ids
                if not cursor:
                    break
            out["memberships"].setdefault(code, {})[target] = pages
    return members


def run_case(case, send, compact=False):
    """Run one case. Returns the exchanges (fixture format) plus the outcome.

    With ``compact`` the geometry exchanges are trimmed for storage (after
    they have been used).
    """
    plan = case_plan(case)
    case = bifrost_case(case)
    out = {
        "case_id": case["id"],
        "input": case["input"],
        "term": plan.term,
        "keys": list(plan.keys),
        "kommuner": list(plan.kommuner),
        "requests": [send(r) for r in plan.requests],
        "kommune_refs": {},
        "memberships": {},
        "geometry": None,
    }
    # Kommune refs and memberships are only needed for /project-filtered types.
    members = _memberships(plan, send, out) if plan.membership_targets else None
    responses = [_response(ex) for ex in out["requests"]]
    result = collect_rows(plan, responses, members)
    display = display_rows(result.rows)
    hit_index, how = find_hit(case, display)

    if hit_index is not None:
        row = result.rows[hit_index]
        attempts, geojson, attempt = [], None, 0
        request = geometry_request(row, attempt)
        while request:
            ex = send(request)
            attempts.append(ex)
            if ex["status"] == 200:
                geojson = geometry_from_response(row, ex["response"])
            if geojson:
                break
            attempt += 1
            request = geometry_request(row, attempt)
        geojson = geojson or row["point"]
        fallback = geojson is row["point"]
        display[hit_index]["geometry"] = geometry_kind((geojson or {}).get("type"))
        out["geometry"] = {
            "row_index": hit_index,
            "ref": row["ref"],
            "type": (geojson or {}).get("type"),
            "fallback_to_point": fallback,
            "attempts": attempts,
        }
        if compact:
            for ex in attempts:
                compact_geometry_exchange(ex, row)

    ok, why = evaluate(case, display, hit_index, how)
    out.update(
        {
            "display": display,
            "hidden": result.hidden,
            "match": how,
            "ok": ok,
            "why": why,
            "outcome": outcome(case, ok, how),
            "known_gap": case.get("known_gap"),
        }
    )
    return out


# --- fixtures -----------------------------------------------------------------

FIXTURE_KEYS = ("requests", "kommune_refs", "memberships", "geometry")


def fixture_from_result(case, result, url):
    data = {
        "case": {
            "id": case["id"],
            "input": case["input"],
            "types": case.get("types"),
            "kommuner": case.get("kommuner"),
        },
        "recorded_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "service": url,
    }
    for k in FIXTURE_KEYS:
        data[k] = result[k]
    return data


def case_fixture_path(case_id):
    return os.path.join(CASES_FIXTURES, case_id + ".json")


def load_case_fixture(case_id):
    path = case_fixture_path(case_id)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def replay_case(case):
    """Run a case from its recorded fixture, or None if it was not recorded."""
    fixture = load_case_fixture(case["id"])
    if fixture is None:
        return None
    return run_case(case, ReplaySender(fixture))


# --- report -------------------------------------------------------------------


def _md(text):
    return str(text).replace("|", "\\|") if text is not None else "–"


def _expected(exp):
    if exp.get("empty"):
        return "(no rows)"
    return _md(exp.get("text")) + (" (top %d)" % exp["within"] if exp.get("within", 1) > 1 else "")


def _gsearch(case):
    fixture = load_fixture(case["id"])
    if fixture is None:
        return None, None, "not recorded"
    ok, why = check_expect(case, fixture)
    return fixture, ok, why


def _slowest(result):
    times = [
        ex.get("elapsed_ms")
        for ex in result["requests"]
        if ex.get("elapsed_ms") is not None
    ]
    return max(times) if times else None


def summarize(results):
    counts = {k: 0 for k in ICONS}
    for r in results.values():
        counts[r["outcome"] if r else FAIL] += 1
    return counts


def write_report(cases, results, path, source):
    """Write a before/after markdown report; returns the outcome counts.

    ``results`` maps case id to a ``run_case`` result (None = not run).
    """
    counts = summarize({c["id"]: results.get(c["id"]) for c in cases})
    g_ok = 0
    summary, details = [], []
    for case in cases:
        cid = case["id"]
        result = results.get(cid)
        g_fixture, g_ok_case, g_why = _gsearch(case)
        g_ok += bool(g_ok_case)
        g_icon = {True: "✅", False: "❌", None: "➖"}[g_ok_case]
        exp = case.get("expect") or {}
        expected = _expected(exp)
        b_exp = bifrost_case(case).get("expect") or {}
        if case.get("bifrost"):
            expected += " → Bifrost: " + (_expected(b_exp) if b_exp else "none")
        gap = "#%s" % case["known_gap"] if case.get("known_gap") else ""
        if result is None:
            b_cell = "❓ not run"
        else:
            b_cell = "%s %s" % (ICONS[result["outcome"]], _md(result["why"]))
        summary.append(
            "| [%s](#%s) | `%s` | %s | %s %s | %s | %s |"
            % (cid, cid, _md(case["input"]), expected, g_icon, _md(g_why), b_cell, gap)
        )

        d = ["### %s" % cid, "", "*%s*" % case["story"], ""]
        d.append("- Typed: `%s`" % _md(case["input"]))
        if case.get("kommuner"):
            d.append("- Kommunefilter: %s" % ", ".join(str(k) for k in case["kommuner"]))
        d.append("- Expected: %s" % expected + (" (%s)" % exp["geometry"] if exp.get("geometry") else ""))
        if case.get("bifrost"):
            d.append("- Bifrost differs on purpose: %s" % _md(case["bifrost"].get("reason")))
        d.append("- GSearch: %s %s" % (g_icon, _md(g_why)))
        if result:
            d.append(
                "- Bifrost: %s %s — %s"
                % (ICONS[result["outcome"]], OUTCOME_TEXT[result["outcome"]], _md(result["why"]))
            )
            hidden = {k: v for k, v in (result.get("hidden") or {}).items() if v}
            if hidden:
                d.append(
                    "- Hidden by the kommune filter: "
                    + ", ".join("%s %d" % kv for kv in hidden.items())
                )
            geom = result.get("geometry")
            if geom:
                d.append(
                    "- Geometry of the hit: %s%s"
                    % (geom["type"], " (point fallback)" if geom["fallback_to_point"] else "")
                )
            slowest = _slowest(result)
            if slowest is not None:
                d.append("- Slowest search request: %d ms" % slowest)
        if gap:
            d.append("- Known gap: %s" % gap)
        d.append("")
        g_rows = (g_fixture or {}).get("display") or []
        b_rows = (result or {}).get("display") or []
        if g_rows or b_rows:
            d.append("| # | GSearch | Bifrost |")
            d.append("|---|---|---|")
            n = min(REPORT_ROWS, max(len(g_rows), len(b_rows)))
            for i in range(n):
                cells = []
                for rows in (g_rows, b_rows):
                    if i < len(rows):
                        r = rows[i]
                        text = _md(r["text"])
                        want = (exp if rows is g_rows else b_exp).get("text")
                        if want and (
                            r["text"] == want
                            or (r["key"] == "ste" and loose_name(r["text"]) == loose_name(want))
                        ):
                            text = "**%s**" % text
                        cells.append("%s: %s" % (r["key"], text))
                    else:
                        cells.append("")
                d.append("| %d | %s | %s |" % (i + 1, cells[0], cells[1]))
            more = max(len(g_rows), len(b_rows)) - n
            if more > 0:
                d.append(
                    "| | … %d more | … %d more |"
                    % (max(0, len(g_rows) - n), max(0, len(b_rows) - n))
                )
        else:
            d.append("*No rows in either.*")
        d.append("")
        details.extend(d)

    head = [
        "# Bifrost vs GSearch: case catalogue",
        "",
        "Every case in [`tests/cases.yaml`](%s) run through the Bifrost core and compared with"
        % os.path.relpath(os.path.join(ROOT, "tests", "cases.yaml"), os.path.dirname(path)),
        "the GSearch baseline (`tests/fixtures/gsearch/`). The expectation is what GSearch showed;",
        "stednavne match on the name before \" (\" because Bifrost cannot give GSearch's text (#1).",
        "",
        "- Source: %s" % source,
        "- Generated: %s" % dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "- Cases: %d. GSearch meets %d expectations." % (len(cases), g_ok),
        "- Bifrost: %d pass, %d known gaps (xfail), %d pass despite a known gap (xpass), %d fail, %d without expectation."
        % (counts[PASS], counts[XFAIL], counts[XPASS], counts[FAIL], counts[NONE]),
        "",
        "✅ pass · ⚠️ known gap · 🎉 passes despite a known gap · ❌ unexpected failure",
        "",
        "| Case | Typed | Expected | GSearch | Bifrost | Known gap |",
        "|---|---|---|---|---|---|",
    ]
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(head + summary + ["", "## Cases", ""] + details).rstrip() + "\n")
    return counts
