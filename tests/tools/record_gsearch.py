# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6"]
# ///
"""Record how Geosearch DK 3.x behaves against SDFI's GSearch.

Every case in ``tests/cases.yaml`` is sent to GSearch exactly the way the
plugin does it (see ``src/geosearch_dk/gsearchfetcher.py``): the same
resources, ``limit = 40 // len(resources)``, prefix handling and kommunefilter.
The responses are stored in ``tests/fixtures/gsearch/<case-id>.json``, and a
readable report is written to ``tests/fixtures/gsearch/BASELINE.md``.

Usage::

    uv run tests/tools/record_gsearch.py record            # all cases (network)
    uv run tests/tools/record_gsearch.py record adr-raadhuspl ste-skagen
    uv run tests/tools/record_gsearch.py report            # offline, from fixtures
    uv run tests/tools/record_gsearch.py check             # offline, exit 1 on mismatch

``record`` also regenerates the report. GSearch closes in November 2026, so
after that only ``report`` and ``check`` are useful.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from itertools import pairwise
from pathlib import Path

from bifrost_cases import check_expect, geometry_kind, load_cases

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "gsearch"
REPORT_FILE = FIXTURE_DIR / "BASELINE.md"
METADATA_FILE = ROOT / "src" / "geosearch_dk" / "metadata.txt"
SETTINGS_FILE = ROOT / "src" / "geosearch_dk" / "config" / "settings.py"

# Copied from src/geosearch_dk/config/settings.py (Settings.__init__).
BASEURL = (
    "https://api.dataforsyningen.dk/rest/gsearch/v2.0/"
    "{resource}?token={token}&q={query}&limit={limit}"
)
# The order here is the order results are displayed in.
RESOURCES = {
    "adr": {"id": "husnummer", "titel": "Husnumre"},
    "ste": {"id": "stednavn", "titel": "Stednavne"},
    "pos": {"id": "postnummer", "titel": "Postdistrikter"},
    "mat": {"id": "matrikel", "titel": "Matrikelnumre"},
    "kom": {"id": "kommune", "titel": "Kommuner"},
    "ops": {"id": "opstillingskreds", "titel": "Opstillingskredse"},
    "pol": {"id": "politikreds", "titel": "Politikredse"},
    "reg": {"id": "region", "titel": "Regioner"},
}
TOTAL_LIMIT = 40
REDACTED = "REDACTED"

# Geometries with more vertices than this are stored as a summary
# (type, bbox, vertex count, area/length) instead of full coordinates.
MAX_FULL_VERTICES = 250
REPORT_ROWS = 15  # the plugin's popup shows 15 rows before it scrolls


def default_token() -> str:
    token = os.environ.get("GSEARCH_TOKEN")
    if token:
        return token
    m = re.search(
        r'DEFAULT_DATAFORSYNING_TOKEN\s*=\s*"([^"]+)"',
        SETTINGS_FILE.read_text(),
    )
    if not m:
        sys.exit(
            f"Set GSEARCH_TOKEN (DEFAULT_DATAFORSYNING_TOKEN is not in {SETTINGS_FILE})"
        )
    return m.group(1)


def plugin_version() -> str:
    m = re.search(r"^version=(.+)$", METADATA_FILE.read_text(), re.MULTILINE)
    return m.group(1).strip() if m else "unknown"


# --------------------------------------------------------------------------
# Request building: a copy of GSearchFetcher.geturls()
# --------------------------------------------------------------------------
def selected_resources(case: dict) -> dict:
    types = case.get("types")
    if not types:
        return dict(RESOURCES)
    unknown = set(types) - set(RESOURCES)
    if unknown:
        raise ValueError(f"{case['id']}: unknown types {sorted(unknown)}")
    return {k: v for k, v in RESOURCES.items() if k in types}


def geturls(case: dict, token: str) -> tuple[str, dict, int, list[str]]:
    """Return (term, {key: url}, limit, kommunekoder) as the plugin computes them."""
    searchterm = case["input"]
    resources = selected_resources(case)
    # The plugin stores the kommunefilter as free text and extracts the digits.
    kommunefilter = ",".join(str(k) for k in case.get("kommuner") or [])
    urls: dict[str, str] = {}
    limit = TOTAL_LIMIT
    split = searchterm.split(":")
    if len(split) > 1:
        first3letters_lowerCase = split[0][0:3].lower()
        if first3letters_lowerCase in RESOURCES:
            resources = {
                first3letters_lowerCase: RESOURCES[first3letters_lowerCase]
            }
            searchterm = split[1].lstrip()
    kommunekoder = re.findall(r"\d+", kommunefilter)
    if not searchterm or not resources:
        return searchterm, urls, limit, kommunekoder
    limit = limit // len(resources)
    filter = "%20or%20".join(
        [
            "kommunekode%20like%20%27%25" + str(k) + "%25%27"
            for k in kommunekoder
        ]
    )
    for key, resource in resources.items():
        url = BASEURL.format(
            resource=resource["id"], limit=limit, token=token, query=searchterm
        )
        if len(kommunekoder) > 0:
            url = url + "&filter=" + filter
        urls[key] = url
    return searchterm, urls, limit, kommunekoder


def qurl_encode(url: str) -> str:
    """Approximate QUrl(url) in TolerantMode: percent-encode what is not URL-safe
    (spaces, non-ASCII ...) and leave existing %XX escapes alone."""
    return urllib.parse.quote(url, safe="!#$%&'()*+,/:;=?@[]~")


def redact(url: str, token: str) -> str:
    return url.replace(f"token={token}", f"token={REDACTED}")


# --------------------------------------------------------------------------
# Geometry helpers
# --------------------------------------------------------------------------
def _positions(coords):
    if coords and isinstance(coords[0], (int, float)):
        yield coords
    else:
        for c in coords or []:
            yield from _positions(c)


def _ring_area(ring) -> float:
    return 0.5 * sum(
        x1 * y2 - x2 * y1
        for (x1, y1, *_), (x2, y2, *_) in zip(ring, ring[1:] + ring[:1])
    )


def _polygon_area(polygon) -> float:
    if not polygon:
        return 0.0
    return abs(_ring_area(polygon[0])) - sum(
        abs(_ring_area(r)) for r in polygon[1:]
    )


def _line_length(line) -> float:
    return sum(
        ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        for (x1, y1, *_), (x2, y2, *_) in pairwise(line)
    )


def summarize_geometry(geom: dict) -> dict:
    gtype = geom.get("type")
    coords = geom.get("coordinates")
    pts = list(_positions(coords))
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    summary = {
        "type": gtype,
        "summarized": True,
        "vertex_count": len(pts),
        "bbox": [
            round(min(xs), 2),
            round(min(ys), 2),
            round(max(xs), 2),
            round(max(ys), 2),
        ]
        if pts
        else None,
    }
    if gtype == "Polygon":
        summary["part_count"] = 1
        summary["area_m2"] = round(_polygon_area(coords))
    elif gtype == "MultiPolygon":
        summary["part_count"] = len(coords)
        summary["area_m2"] = round(sum(_polygon_area(p) for p in coords))
    elif gtype == "LineString":
        summary["part_count"] = 1
        summary["length_m"] = round(_line_length(coords))
    elif gtype == "MultiLineString":
        summary["part_count"] = len(coords)
        summary["length_m"] = round(sum(_line_length(line) for line in coords))
    return summary


def is_geojson(value) -> bool:
    return (
        isinstance(value, dict) and "type" in value and "coordinates" in value
    )


def compact_row(row: dict) -> dict:
    out = {}
    for k, v in row.items():
        if (
            is_geojson(v)
            and len(list(_positions(v["coordinates"]))) > MAX_FULL_VERTICES
        ):
            out[k] = summarize_geometry(v)
        else:
            out[k] = v
    return out


def geometry_info(geom: dict | None) -> dict | None:
    if not is_geojson(geom) and not (
        isinstance(geom, dict) and geom.get("summarized")
    ):
        return None
    if geom.get("summarized"):
        return {k: geom.get(k) for k in ("type", "vertex_count", "bbox")}
    return {
        k: summarize_geometry(geom)[k]
        for k in ("type", "vertex_count", "bbox")
    }


# --------------------------------------------------------------------------
# Recording
# --------------------------------------------------------------------------
def fetch(url: str) -> dict:
    request = urllib.request.Request(
        qurl_encode(url),
        headers={
            "Accept-Encoding": "identity",
            "User-Agent": "geosearch-dk-baseline-recorder",
        },
    )
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=60) as resp:
            body = resp.read().decode("utf-8")
            status = resp.status
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        status = e.code
    except urllib.error.URLError as e:
        return {
            "ok": False,
            "http_status": None,
            "elapsed_ms": None,
            "error": str(e.reason),
        }
    elapsed = round((time.monotonic() - t0) * 1000)
    if status != 200:
        return {
            "ok": False,
            "http_status": status,
            "elapsed_ms": elapsed,
            "error": body[:2000],
        }
    try:
        data = json.loads(body)
    except ValueError as e:
        return {
            "ok": False,
            "http_status": status,
            "elapsed_ms": elapsed,
            "error": str(e),
        }
    return {
        "ok": True,
        "http_status": status,
        "elapsed_ms": elapsed,
        "data": data,
    }


def display_rows(requests: list[dict]) -> list[dict]:
    """The rows in the plugin's popup, in order (Suggester.showResultRows)."""
    rows = []
    for req in requests:
        if req["ok"]:
            for row in req["rows"]:
                geom = row.get("geometri") or {}
                rows.append(
                    {
                        "key": req["key"],
                        "text": row.get("visningstekst"),
                        "geometry": geometry_kind(geom.get("type")),
                        "geometry_type": geom.get("type"),
                    }
                )
        else:
            rows.append(
                {
                    "key": req["key"],
                    "text": RESOURCES[req["key"]]["titel"]
                    + " - Der skete en fejl",
                    "geometry": None,
                    "geometry_type": None,
                    "error": True,
                }
            )
    for i, row in enumerate(rows, 1):
        row["rank"] = i
    return rows


def record_case(
    case: dict, token: str, recorded_at: str, version: str
) -> dict:
    term, urls, limit, kommunekoder = geturls(case, token)
    with ThreadPoolExecutor(max_workers=max(1, len(urls))) as pool:
        results = dict(zip(urls, pool.map(fetch, urls.values())))
    requests = []
    for key, url in urls.items():
        res = results[key]
        entry = {
            "key": key,
            "resource": RESOURCES[key]["id"],
            "url": redact(qurl_encode(url), token),
            "ok": res["ok"],
            "http_status": res["http_status"],
            "elapsed_ms": res["elapsed_ms"],
        }
        if res["ok"]:
            data = res["data"]
            entry["row_count"] = len(data)
            entry["rows"] = [compact_row(r) for r in data]
        else:
            entry["error"] = res["error"]
        requests.append(entry)
    return {
        "case_id": case["id"],
        "recorded_at": recorded_at,
        "service": "GSearch v2.0 (api.dataforsyningen.dk)",
        "plugin_version": version,
        "input": case["input"],
        "term": term,
        "keys": list(urls),
        "limit": limit,
        "kommunekoder": kommunekoder,
        "max_full_vertices": MAX_FULL_VERTICES,
        "requests": requests,
        "display": display_rows(requests),
    }


# --------------------------------------------------------------------------
# Expectations and report
# --------------------------------------------------------------------------
def md_escape(text) -> str:
    return str(text).replace("|", "\\|") if text is not None else "–"


def fmt_geom(geom: dict | None) -> str:
    info = geometry_info(geom)
    if not info:
        return "–"
    if info["vertex_count"] == 1 and info["bbox"]:
        x, y = info["bbox"][:2]
        return f"{info['type']} ({x:.0f}, {y:.0f})"
    return f"{info['type']}, {info['vertex_count']} pkt"


def load_fixture(case_id: str) -> dict | None:
    path = FIXTURE_DIR / f"{case_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_report(cases: list[dict]) -> list[str]:
    """Write BASELINE.md and return a list of failed expectations."""
    failures = []
    summary = []
    details = []
    recorded = set()
    for case in cases:
        fixture = load_fixture(case["id"])
        types = ", ".join(case.get("types") or ["alle"])
        komm = ", ".join(str(k) for k in case.get("kommuner") or [])
        gap = f"#{case['known_gap']}" if case.get("known_gap") else ""
        exp = case.get("expect") or {}
        expected = (
            "(no rows)" if exp.get("empty") else md_escape(exp.get("text"))
        )
        if fixture is None:
            failures.append(f"{case['id']}: not recorded")
            summary.append(
                f"| [{case['id']}](#{case['id']}) | `{md_escape(case['input'])}` | {types} | {komm} | {expected} | ❓ not recorded | {gap} |"
            )
            continue
        recorded.add(fixture["recorded_at"][:10])
        ok, why = check_expect(case, fixture)
        if ok is False:
            failures.append(f"{case['id']}: {why}")
        icon = {True: "✅", False: "❌", None: "➖"}[ok]
        summary.append(
            f"| [{case['id']}](#{case['id']}) | `{md_escape(case['input'])}` | {types} | {komm} | {expected} | {icon} {why} | {gap} |"
        )

        d = [f"### {case['id']}", "", f"*{case['story']}*", ""]
        d.append(f"- Typed: `{md_escape(case['input'])}`")
        d.append(f"- Search term sent: `{md_escape(fixture['term'])}`")
        d.append(
            f"- Resources: {', '.join(fixture['keys']) or '(none, no request is sent)'}"
            + (f" · limit {fixture['limit']}" if fixture["keys"] else "")
        )
        if fixture["kommunekoder"]:
            d.append(f"- Kommunefilter: {', '.join(fixture['kommunekoder'])}")
        if exp:
            if exp.get("empty"):
                d.append("- Expected: no rows")
            else:
                d.append(
                    f"- Expected: **{md_escape(exp.get('text'))}** within top {exp.get('within', 1)}"
                    + (f" ({exp['geometry']})" if exp.get("geometry") else "")
                )
        d.append(f"- Today: {icon} {why}")
        if gap:
            d.append(f"- Known gap in Bifrost: {gap}")
        if case.get("notes"):
            d.append(f"- Notes: {md_escape(case['notes']).strip()}")
        times = [
            r["elapsed_ms"]
            for r in fixture["requests"]
            if r["elapsed_ms"] is not None
        ]
        if times:
            d.append(f"- Slowest request: {max(times)} ms")
        d.append("")
        rows = fixture["display"]
        if rows:
            raw = {}
            for req in fixture["requests"]:
                for i, r in enumerate(req.get("rows") or []):
                    raw[(req["key"], i)] = r
            counters: dict[str, int] = {}
            d.append("| # | Type | Visningstekst | Geometri |")
            d.append("|---|---|---|---|")
            for row in rows[:REPORT_ROWS]:
                idx = counters.get(row["key"], 0)
                counters[row["key"]] = idx + 1
                geom = raw.get((row["key"], idx), {}).get("geometri")
                text = md_escape(row["text"])
                if exp.get("text") and row["text"] == exp.get("text"):
                    text = f"**{text}**"
                d.append(
                    f"| {row['rank']} | {row['key']} | {text} | {fmt_geom(geom)} |"
                )
            if len(rows) > REPORT_ROWS:
                d.append(
                    f"| | | … {len(rows) - REPORT_ROWS} more rows in the fixture | |"
                )
        else:
            d.append("*No rows: the popup does not open.*")
        d.append("")
        details.extend(d)

    head = [
        "# GSearch baseline",
        "",
        "What a Geosearch DK 3.x user sees **today** for each case in",
        "[`tests/cases.yaml`](../../cases.yaml), recorded against SDFI's GSearch v2.0 before it",
        "closes in November 2026. The raw responses are in `<case-id>.json` next to this file.",
        "",
        "Generated by `uv run tests/tools/record_gsearch.py report`. Do not edit by hand.",
        "The `expect` of each case in `tests/cases.yaml` was written from this baseline;",
        "`uv run tests/tools/record_gsearch.py check` checks the recordings against them (offline).",
        "",
        f"- Recorded: {', '.join(sorted(recorded)) or '–'}",
        f"- Plugin version: {plugin_version()}",
        f"- Cases: {len(cases)}, expectation failures: {len(failures)}",
        "",
        "The plugin sends one request per selected resource with `limit = 40 // number of resources`,",
        "and shows the rows in resource order: adr, ste, pos, mat, kom, ops, pol, reg.",
        "`#` is the row in the popup. *Known gap* is the issue that explains why Bifrost is expected to differ.",
        f"Geometries with more than {MAX_FULL_VERTICES} vertices are stored as a summary (type, bbox, vertex count, area/length).",
        "",
        "| Case | Typed | Types | Kommuner | Expected | Today | Known gap |",
        "|---|---|---|---|---|---|---|",
    ]
    REPORT_FILE.write_text(
        "\n".join(head + summary + ["", "## Cases", ""] + details).rstrip()
        + "\n",
        encoding="utf-8",
    )
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("command", choices=["record", "report", "check"])
    parser.add_argument("ids", nargs="*", help="only record these case ids")
    args = parser.parse_args()

    cases = load_cases()
    if args.command == "record":
        token = default_token()
        version = plugin_version()
        recorded_at = (
            dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
        )
        missing = set(args.ids) - {c["id"] for c in cases}
        if missing:
            sys.exit(f"Unknown case ids: {sorted(missing)}")
        FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
        for case in cases:
            if args.ids and case["id"] not in args.ids:
                continue
            fixture = record_case(case, token, recorded_at, version)
            text = json.dumps(fixture, ensure_ascii=False, indent=1)
            if token in text:
                sys.exit(f"{case['id']}: token leaked into fixture")
            (FIXTURE_DIR / f"{case['id']}.json").write_text(
                text + "\n", encoding="utf-8"
            )
            errors = [r["key"] for r in fixture["requests"] if not r["ok"]]
            print(
                f"{case['id']}: {len(fixture['display'])} rows"
                + (f", errors in {errors}" if errors else "")
            )

    failures = write_report(cases)
    print(f"Wrote {REPORT_FILE.relative_to(ROOT)}")
    for f in failures:
        print(f"  ✗ {f}")
    return 1 if (failures and args.command == "check") else 0


if __name__ == "__main__":
    sys.exit(main())
