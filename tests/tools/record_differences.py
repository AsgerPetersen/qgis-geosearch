# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6"]
# ///
"""Record GSearch and Bifrost side by side, per resource, for every search string.

GSearch closes in November 2026. This records the evidence for
docs/forskelle-gsearch-bifrost.md while both services still answer: for each
search string, every GSearch resource (also those the plugin does not use, such
as ``navngivenvej``) and the matching Bifrost endpoints, at the same time.

The search strings are the examples on the comparison site
(https://asgerpetersen.github.io/gsearch-bifrost-compare/, ``index.html`` and
``direct.html``) and every input in ``tests/cases.yaml``, with the plugin
prefix (``mat:`` ...) removed. One fixture per (search string, kommunekoder) is
written to ``tests/fixtures/forskelle/<id>.json``. Secrets are never written:
the GSearch token is replaced by ``REDACTED`` and the Bifrost key is only sent
in a header.

    GSEARCH_TOKEN=... BIFROST_KEY=... uv run tests/tools/record_differences.py record [id ...]
    uv run tests/tools/record_differences.py list

Environment:
    GSEARCH_TOKEN  GSearch token (the public token in Geosearch DK 3.x)
    BIFROST_KEY    Bifrost API key
    BIFROST_URL    default https://bifrost.test42.dataforsyningen.dk
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
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

from record_gsearch import compact_row, qurl_encode  # noqa: E402

FIXTURE_DIR = ROOT / "tests" / "fixtures" / "forskelle"
CASES_FILE = ROOT / "tests" / "cases.yaml"
GS_URL = "https://api.dataforsyningen.dk/rest/gsearch/v2.0/"
DEFAULT_BF_URL = "https://bifrost.test42.dataforsyningen.dk"
REDACTED = "REDACTED"
LIMIT = 10
# Bifrost /search has no kommune filter; with kommunekoder the comparison site
# fetches this many hits per type and filters them on components.kommuner.
BF_OVERFETCH = 100

# GSearch resource -> Bifrost endpoint/target, as on direct.html (direct.js DTYPES).
GS_RESOURCES = [
    "adresse",
    "husnummer",
    "navngivenvej",
    "postnummer",
    "matrikel",
    "matrikel_udgaaet",
    "stednavn",
    "kommune",
    "sogn",
    "region",
    "retskreds",
    "politikreds",
    "opstillingskreds",
]
BF_SEARCHES = [
    # (name, body without input/limit)
    ("street", {"target": "street"}),
    ("postcode", {"target": "postcode"}),
    ("city", {"target": "city"}),
    ("ejendom", {"target": "ejendom"}),
    ("ejendom_retired", {"target": "ejendom", "lifecycle": ["retired"]}),
    ("ejerlav", {"target": "ejerlav"}),
    ("stednavn", {"target": "stednavn"}),
    ("kommune", {"target": "kommune"}),
    ("sogn", {"target": "sogn"}),
    ("region", {"target": "region"}),
    ("retskreds", {"target": "retskreds"}),
    ("politikreds", {"target": "politikreds"}),
    ("opstillingskreds", {"target": "opstillingskreds"}),
]

# The example buttons on the comparison site (commit 4088061 of
# AsgerPetersen/gsearch-bifrost-compare): plugin.js CASES and direct.js CASES.
SITE_PLUGIN = [
    "skodsb", "skodsborgvej 41", "skodsborgvej 414", "nøddebogade 1 st th", "nørrebrog 1", "nørrebrog",
    "ste: rådhuspladsen", "ste: vendsyssel", "ste: skodsborg", "mat: 3kg søll", "mat: 3kg",
    "pos: 80", "pos: aar", "kom: køb", "ops: aar", "udg: 1an gentofte",
]  # fmt: skip
SITE_DIRECT = [
    ("skodsb", ""),
    ("skodsborgvej 414", ""),
    ("nøddebogade 1 st th", ""),
    ("nørrebrog 1", ""),
    ("vestergade 1", "101"),
    ("Vangebovej 71", ""),
    ("nørrebrog", ""),
    ("rådhuspladsen", ""),
    ("vendsyssel", ""),
    ("skodsborg", ""),
    ("vor frue", "101,851"),
    ("3kg søll", ""),
    ("3kg", ""),
    ("1a", "615"),
    ("1an gentofte", ""),
    ("80", ""),
    ("aar", ""),
    ("køb", ""),
    ("lyngby", "230,173"),
]
# Extra search strings that show a difference not covered above.
EXTRA = [
    ("nørrebrogade", ""),
    ("nørrebrogade 1", ""),
    ("nørrebrogade 1 københavn", ""),
    ("rådhuspladsen 1 københavn", ""),
    # From the user: partial street names and house number first.
    ("77 vangeb", ""),
    ("vangeb", ""),
    ("vangeb 77", ""),
    ("14 østerlund", ""),
    ("østerlund 14", ""),
    ("vangebovej 77", ""),
    ("ste: øenslæger", ""),
    # Kommuner on stednavne and veje: GSearch lists every kommune the object
    # touches; Bifrost lists fewer, which matters for the kommunefilter.
    ("gudenå", "730"),
    ("furesø", ""),
    ("furesø", "230"),
    ("roskilde fjord", "265"),
    ("lyngby hovedgade", "157"),
    ("skodsborg strandvej", ""),
    ("skodsborg strandvej", "173"),
    ("nørrebrogade 2400", ""),
    # Husnummer først with the full street name (separates it from #3).
    ("77 vangebovej", ""),
    ("1 nørrebrogade", ""),
]
PREFIXES = {"adr", "ste", "pos", "mat", "kom", "ops", "pol", "reg", "enh", "vej", "sog", "ret", "udg"}

ASCII = str.maketrans({"æ": "ae", "ø": "oe", "å": "aa", "é": "e", "ü": "u"})


def strip_prefix(text: str) -> tuple[str, str]:
    """('mat: 3kg') -> ('mat', '3kg'), as the plugin and the comparison site do."""
    split = text.split(":")
    if len(split) > 1 and split[0][0:3].lower() in PREFIXES:
        return split[0][0:3].lower(), split[1].lstrip()
    return "", text


def slug(term: str, kommuner: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", term.lower().translate(ASCII)).strip("-")
    if term != term.lower() and term == term.upper():
        s += "-versaler"
    if kommuner:
        s += "-k" + "-".join(kommuner.split(","))
    return s


def search_strings() -> list[dict]:
    """Every (term, kommunekoder) to record, with where it comes from."""
    found: dict[str, dict] = {}

    def add(raw: str, kommuner: str, source: str):
        _, term = strip_prefix(raw)
        term = term.strip()
        if not term:
            return
        kommuner = ",".join(str(int(k)) for k in re.findall(r"\d+", kommuner or ""))
        sid = slug(term, kommuner)
        entry = found.setdefault(
            sid, {"id": sid, "term": term, "kommuner": kommuner, "sources": []}
        )
        if source not in entry["sources"]:
            entry["sources"].append(source)

    for raw in SITE_PLUGIN:
        add(raw, "", "sammenligningssiden index.html: " + raw)
    for raw, k in SITE_DIRECT:
        add(raw, k, "sammenligningssiden direct.html: " + raw + (f" (kommune {k})" if k else ""))
    for raw, k in EXTRA:
        add(raw, k, "supplerende")
    cases = yaml.safe_load(CASES_FILE.read_text(encoding="utf-8"))
    for c in cases:
        add(c["input"], ",".join(c.get("kommuner") or []), "tests/cases.yaml: " + c["id"])
    return list(found.values())


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------
def gs_fetch(resource: str, term: str, kommuner: str, token: str) -> dict:
    params = {"token": token, "q": term, "limit": LIMIT}
    codes = [k.zfill(4) for k in kommuner.split(",") if k]
    if codes:
        params["filter"] = " or ".join(f"kommunekode like '%{c}%'" for c in codes)
    url = GS_URL + resource + "?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    req = urllib.request.Request(
        url, headers={"Accept-Encoding": "identity", "User-Agent": "geosearch-dk-differences-recorder"}
    )
    t0 = time.monotonic()
    entry = {"resource": resource, "url": url.replace(f"token={token}", f"token={REDACTED}")}
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            status, body = resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        status, body = e.code, e.read().decode("utf-8", "replace")
    except (urllib.error.URLError, OSError) as e:
        return {**entry, "ok": False, "http_status": None, "error": str(e)}
    entry["http_status"] = status
    entry["elapsed_ms"] = round((time.monotonic() - t0) * 1000)
    if status != 200:
        return {**entry, "ok": False, "error": body[:2000]}
    try:
        rows = json.loads(body)
    except ValueError as e:
        return {**entry, "ok": False, "error": str(e)}
    return {**entry, "ok": True, "row_count": len(rows), "rows": [compact_row(r) for r in rows]}


def bf_post(url: str, key: str, endpoint: str, body) -> dict:
    req = urllib.request.Request(
        f"{url.rstrip('/')}/{endpoint}",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + key,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "geosearch-dk-differences-recorder",
        },
        method="POST",
    )
    entry = {"endpoint": endpoint, "url": f"{url.rstrip('/')}/{endpoint}", "body": body}
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            status, raw = resp.status, resp.read()
    except urllib.error.HTTPError as e:
        status, raw = e.code, e.read()
    except (urllib.error.URLError, OSError) as e:
        return {**entry, "ok": False, "http_status": None, "error": str(e)}
    entry["http_status"] = status
    entry["elapsed_ms"] = round((time.monotonic() - t0) * 1000)
    try:
        response = json.loads(raw.decode("utf-8") or "null")
    except ValueError:
        response = raw.decode("utf-8", "replace")[:2000]
    return {**entry, "ok": status == 200, "response": response}


def bifrost_requests(term: str, kommuner: str) -> list[tuple[str, str, object]]:
    codes = [k.zfill(4) for k in kommuner.split(",") if k]
    out = []
    if codes:
        out.append(
            ("resolve", "resolve", [{"input": term, "components": {"kommune": c}, "limit": LIMIT} for c in codes])
        )
    else:
        out.append(("resolve", "resolve", {"input": term, "limit": LIMIT}))
    for name, extra in BF_SEARCHES:
        out.append((name, "search", {"input": term, **extra, "limit": BF_OVERFETCH if codes else LIMIT}))
    return out


def record_one(s: dict, token: str, bf_url: str, key: str) -> dict:
    term, kommuner = s["term"], s["kommuner"]
    bf_reqs = bifrost_requests(term, kommuner)
    recorded_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    with ThreadPoolExecutor(max_workers=8) as pool:
        gs = list(pool.map(lambda r: gs_fetch(r, term, kommuner, token), GS_RESOURCES))
        bf = list(pool.map(lambda r: {"name": r[0], **bf_post(bf_url, key, r[1], r[2])}, bf_reqs))
    return {
        "id": s["id"],
        "term": term,
        "kommuner": kommuner,
        "sources": s["sources"],
        "recorded_at": recorded_at,
        "limit": LIMIT,
        "gsearch": {"service": "GSearch v2.0 (api.dataforsyningen.dk)", "requests": gs},
        "bifrost": {"service": "Bifrost (" + bf_url + ")", "requests": bf},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["record", "list"])
    parser.add_argument("ids", nargs="*", help="only these ids")
    args = parser.parse_args()
    strings = search_strings()
    if args.command == "list":
        for s in strings:
            print(f"{s['id']:40} {s['term']!r:32} {s['kommuner']:10} {len(s['sources'])} kilde(r)")
        print(len(strings), "search strings")
        return 0
    token = os.environ.get("GSEARCH_TOKEN")
    key = os.environ.get("BIFROST_KEY")
    if not token or not key:
        sys.exit("Set GSEARCH_TOKEN and BIFROST_KEY")
    bf_url = os.environ.get("BIFROST_URL", DEFAULT_BF_URL)
    unknown = set(args.ids) - {s["id"] for s in strings}
    if unknown:
        sys.exit(f"Unknown ids: {sorted(unknown)}")
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    for s in strings:
        if args.ids and s["id"] not in args.ids:
            continue
        data = record_one(s, token, bf_url, key)
        text = json.dumps(data, ensure_ascii=False, indent=1)
        if token in text or key in text:
            sys.exit(f"{s['id']}: a secret leaked into the fixture")
        (FIXTURE_DIR / f"{s['id']}.json").write_text(text + "\n", encoding="utf-8")
        gs_err = [r["resource"] for r in data["gsearch"]["requests"] if not r["ok"]]
        bf_err = [r["name"] for r in data["bifrost"]["requests"] if not r["ok"]]
        print(
            f"{s['id']:40} gs {sum(r.get('row_count', 0) for r in data['gsearch']['requests']):4} rows"
            f"  bf {sum(len((r.get('response') or {}).get('matches') or []) if isinstance(r.get('response'), dict) else 0 for r in data['bifrost']['requests']):4} matches"
            + (f"  GS errors {gs_err}" if gs_err else "")
            + (f"  BF errors {bf_err}" if bf_err else "")
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
