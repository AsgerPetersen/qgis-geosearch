#!/usr/bin/env python3
"""Generate docs/forskelle-gsearch-bifrost.md from tests/fixtures/forskelle.

Offline and reproducible: it only reads the recordings made by
record_differences.py. The sections, examples and descriptions are in
forskelle_spec.py; the hits shown are taken from the recordings.

    uv run python tests/tools/forskelle_doc.py            # write the document
    uv run python tests/tools/forskelle_doc.py --check    # exit 1 if out of date
    uv run python tests/tools/forskelle_doc.py show ID    # print the top hits of one recording
"""

import argparse
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import forskelle_spec as spec  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures" / "forskelle"
DOC = ROOT / "docs" / "forskelle-gsearch-bifrost.md"
REPO_URL = "https://github.com/AsgerPetersen/qgis-geosearch"
DOC_LINK_PREFIX = "../tests/fixtures/forskelle/"


def load(fixture_id):
    with open(FIXTURES / ("%s.json" % fixture_id), encoding="utf-8") as f:
        return json.load(f)


def bifrost_matches(response):
    """All matches of a response; a batch (list) is flattened in order."""
    if isinstance(response, list):
        out = []
        for part in response:
            out.extend(bifrost_matches(part))
        return out
    if isinstance(response, dict):
        return list(response.get("matches") or [])
    return []


def gs_codes(row):
    return [c for c in (row.get("kommunekode") or "").split(",") if c]


def bf_codes(match):
    kommuner = (match.get("components") or {}).get("kommuner") or []
    return [k.get("kommunekode") for k in kommuner if k.get("kommunekode")]


def bf_postcodes(match):
    postcodes = (match.get("components") or {}).get("postcodes") or []
    return [p.get("postcode") for p in postcodes if p.get("postcode")]


def gs_request(data, resource):
    for r in data["gsearch"]["requests"]:
        if r["resource"] == resource:
            return r
    raise KeyError("%s: no GSearch resource %s" % (data["id"], resource))


def bf_request(data, name):
    for r in data["bifrost"]["requests"]:
        if r["name"] == name:
            return r
    raise KeyError("%s: no Bifrost request %s" % (data["id"], name))


def _error(request):
    status = request.get("http_status")
    return "fejl: HTTP %s" % status if status else "fejl: intet svar"


def gs_hits(data, view):
    """Return (texts, failed) for a GSearch view."""
    r = gs_request(data, view.source)
    if not r.get("ok"):
        return [_error(r)], True
    rows = r.get("rows") or []
    if view.only:
        rows = [row for row in rows if view.only(row.get("visningstekst") or "")]
    texts = []
    for row in rows[: view.n]:
        text = row.get("visningstekst") or ""
        if view.kommuner:
            text += " [kommuner: %s]" % (", ".join(gs_codes(row)) or "ingen")
        texts.append(text)
    return texts, False


def bf_hits(data, view):
    r = bf_request(data, view.source)
    if not r.get("ok"):
        return [_error(r)], True
    matches = bifrost_matches(r.get("response"))
    if view.only:
        matches = [m for m in matches if view.only(m.get("result") or "")]
    total = len(matches)
    if view.in_filter:
        codes = set(fixture_codes(data))
        matches = [m for m in matches if codes & set(bf_codes(m))]
    texts = []
    for m in matches[: view.n]:
        text = m.get("result") or ""
        extra = []
        if view.kommuner:
            extra.append("kommuner: %s" % (", ".join(bf_codes(m)) or "ingen"))
        if view.postnumre:
            extra.append("postnumre: %s" % (", ".join(bf_postcodes(m)) or "ingen"))
        if view.parcels:
            parcels = ((m.get("ejendom") or {}).get("parcels") or {}).get("items") or []
            extra.append(
                "ejendom med %d jordstykke%s" % (len(parcels), "" if len(parcels) == 1 else "r")
            )
        if view.confidence:
            conf = (m.get("meta") or {}).get("confidence")
            if conf:
                extra.append("sikkerhed %s" % conf)
        if extra:
            text += " [%s]" % "; ".join(extra)
        texts.append(text)
    if view.in_filter:
        texts.insert(
            0,
            "*%d af %d hits har kommune %s*"
            % (len(matches), total, ", ".join(sorted(fixture_codes(data)))),
        )
    return texts, False


def fixture_codes(data):
    return ["%04d" % int(c) for c in (data.get("kommuner") or "").split(",") if c]


def bf_label(data, name):
    r = bf_request(data, name)
    if r["endpoint"] == "resolve":
        return "Bifrost `/resolve`"
    target = (r.get("body") or {}).get("target") if isinstance(r.get("body"), dict) else None
    if target is None and isinstance(r.get("body"), list) and r["body"]:
        target = r["body"][0].get("target")
    label = "Bifrost `/search` %s" % (target or name)
    if name.endswith("_retired"):
        label += " (udgåede)"
    return label


def md_escape(text):
    return text.replace("|", "\\|")


def render_example(ex):
    data = load(ex.fixture)
    lines = []
    title = "`%s`" % data["term"]
    if data.get("kommuner"):
        title += " med kommunefilter %s" % ", ".join(data["kommuner"].split(","))
    if ex.title:
        title += " – %s" % ex.title
    lines.append("#### %s" % title)
    lines.append("")
    lines.append("| Tjeneste | Øverste hits |")
    lines.append("|---|---|")
    for view in ex.views:
        if view.service == "gs":
            texts, _ = gs_hits(data, view)
            label = "GSearch `%s`" % view.source
        else:
            texts, _ = bf_hits(data, view)
            label = bf_label(data, view.source)
        if view.only:
            label += " (kun %s)" % view.only.label
        if view.in_filter:
            label += " (kun hits i kommunefilteret)"
        shown = "<br>".join(md_escape(t) for t in texts) if texts else "*ingen hits*"
        lines.append("| %s | %s |" % (label, shown))
    lines.append("")
    lines.append(ex.text.strip())
    lines.append("")
    lines.append(
        "Optaget %s · [rå optagelse](%s%s.json)"
        % (data["recorded_at"], DOC_LINK_PREFIX, ex.fixture)
    )
    lines.append("")
    return lines


def kommune_stats():
    """Number of kommuner per stednavn/street object over all recordings."""
    gs_sted = {}
    bf_sted = {}
    bf_street = {}
    for path in sorted(FIXTURES.glob("*.json")):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for r in data["gsearch"]["requests"]:
            if r["resource"] == "stednavn":
                for row in r.get("rows") or []:
                    gs_sted[row.get("id")] = len(gs_codes(row))
        for r in data["bifrost"]["requests"]:
            for m in bifrost_matches(r.get("response")):
                ref = m.get("ref") or {}
                if ref.get("kind") == "stednavn":
                    bf_sted[ref.get("id")] = len(bf_codes(m))
                elif ref.get("kind") == "street":
                    bf_street[ref.get("id")] = (len(bf_codes(m)), len(bf_postcodes(m)))
    return {
        "gs_sted": collections.Counter(gs_sted.values()),
        "bf_sted": collections.Counter(bf_sted.values()),
        "bf_street_kommuner": collections.Counter(k for k, _ in bf_street.values()),
        "bf_street_postnumre": collections.Counter(p for _, p in bf_street.values()),
    }


def _count(counter, pred):
    return sum(n for k, n in counter.items() if pred(k))


def render_kommune_stats():
    s = kommune_stats()
    return [
        "Optællingen nedenfor dækker alle objekter i alle optagelser "
        "(hvert objekt tælles én gang):",
        "",
        "| | Objekter | Med 0 kommuner | Med 1 kommune | Med flere kommuner |",
        "|---|---|---|---|---|",
        "| GSearch stednavne | %d | %d | %d | %d (højst %d) |"
        % (
            sum(s["gs_sted"].values()),
            s["gs_sted"][0],
            s["gs_sted"][1],
            _count(s["gs_sted"], lambda k: k > 1),
            max(s["gs_sted"]),
        ),
        "| Bifrost stednavne | %d | %d | %d | %d |"
        % (
            sum(s["bf_sted"].values()),
            s["bf_sted"][0],
            s["bf_sted"][1],
            _count(s["bf_sted"], lambda k: k > 1),
        ),
        "| Bifrost veje (`street`) | %d | %d | %d | %d |"
        % (
            sum(s["bf_street_kommuner"].values()),
            s["bf_street_kommuner"][0],
            s["bf_street_kommuner"][1],
            _count(s["bf_street_kommuner"], lambda k: k > 1),
        ),
        "",
        "Bifrost-veje med mere end ét postnummer: %d af %d."
        % (
            _count(s["bf_street_postnumre"], lambda k: k > 1),
            sum(s["bf_street_postnumre"].values()),
        ),
        "",
    ]


def recording_period():
    stamps = []
    for path in FIXTURES.glob("*.json"):
        with open(path, encoding="utf-8") as f:
            stamps.append(json.load(f)["recorded_at"])
    return min(stamps), max(stamps), len(stamps)


def render():
    first, last, count = recording_period()
    lines = [
        "<!-- Genereret af tests/tools/forskelle_doc.py ud fra tests/fixtures/forskelle. "
        "Ret i tests/tools/forskelle_spec.py, ikke her. -->",
        "",
    ]
    lines.extend(spec.INTRO.strip().format(count=count, first=first, last=last).splitlines())
    lines.append("")
    lines.append("## Indhold")
    lines.append("")
    for section in spec.SECTIONS:
        lines.append("- [%s](#%s)" % (section.title, section.anchor))
    lines.append("")
    for section in spec.SECTIONS:
        lines.append('<a id="%s"></a>' % section.anchor)
        lines.append("")
        lines.append("## %s" % section.title)
        lines.append("")
        if section.issue:
            lines.append(
                "Issue: [#%d](%s/issues/%d)" % (section.issue, REPO_URL, section.issue)
            )
            lines.append("")
        lines.extend(section.text.strip().splitlines())
        lines.append("")
        if section.stats == "kommuner":
            lines.extend(render_kommune_stats())
        for ex in section.examples:
            lines.extend(render_example(ex))
    lines.extend(spec.OUTRO.strip().splitlines())
    lines.append("")
    return "\n".join(lines)


def show(fixture_id, n):
    data = load(fixture_id)
    print("%s %r kommuner=%r %s" % (data["id"], data["term"], data["kommuner"], data["recorded_at"]))
    for r in data["gsearch"]["requests"]:
        if not r.get("ok"):
            print("  GS %-18s HTTP %s" % (r["resource"], r.get("http_status")))
            continue
        for row in (r.get("rows") or [])[:n]:
            print("  GS %-18s %s [%s]" % (r["resource"], row.get("visningstekst"), row.get("kommunekode")))
    for r in data["bifrost"]["requests"]:
        if not r.get("ok"):
            print("  BF %-18s HTTP %s" % (r["name"], r.get("http_status")))
            continue
        for m in bifrost_matches(r.get("response"))[:n]:
            print(
                "  BF %-18s %s [%s] %s"
                % (r["name"], m.get("result"), ",".join(bf_codes(m)), (m.get("meta") or {}).get("confidence"))
            )


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="exit 1 if the document is out of date")
    parser.add_argument("command", nargs="?", choices=("show",))
    parser.add_argument("ids", nargs="*")
    parser.add_argument("-n", type=int, default=5)
    args = parser.parse_args(argv)
    if args.command == "show":
        for fixture_id in args.ids:
            show(fixture_id, args.n)
        return 0
    text = render()
    if args.check:
        current = DOC.read_text(encoding="utf-8") if DOC.exists() else ""
        if current != text:
            print("%s is out of date; run tests/tools/forskelle_doc.py" % DOC.relative_to(ROOT))
            return 1
        return 0
    DOC.write_text(text, encoding="utf-8")
    print("Wrote %s" % DOC.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
