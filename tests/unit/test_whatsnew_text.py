"""The "Hvad er nyt" text (help/hvad_er_nyt.html) and the copies of its bullets."""

from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HTML = ROOT / "src" / "geosearch_dk" / "help" / "hvad_er_nyt.html"
WHY = "Bifrost tilbyder det ikke – vi har bedt Klimadatastyrelsen om det"

# Used by whatsnew.show_whats_new(parent, anchor=...), e.g. from the kommunefilter (#11).
ANCHORS = [
    "nyt",
    "anderledes",
    "visningstekst",
    "matrikel",
    "geometri",
    "kommunefilter",
    "virker-ikke",
    "delord",
    "kommunefilter-server",
    "undertype",
    "sammenlign",
]


class _Anchors(HTMLParser):
    def __init__(self):
        super().__init__()
        self.names, self.ids, self.hrefs = set(), set(), []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.add(attrs["id"])
        if tag == "a" and "name" in attrs:
            self.names.add(attrs["name"])
        if tag == "a" and "href" in attrs:
            self.hrefs.append(attrs["href"])


def _parse():
    p = _Anchors()
    p.feed(HTML.read_text(encoding="utf-8"))
    return p


def test_anchors_exist_for_qtextbrowser_and_browsers():
    p = _parse()
    for anchor in ANCHORS:
        assert anchor in p.names, anchor  # QTextBrowser.scrollToAnchor
        assert anchor in p.ids, anchor


def test_internal_links_point_to_anchors():
    p = _parse()
    for href in p.hrefs:
        if href.startswith("#"):
            assert href[1:] in p.names, href
        else:
            assert href.startswith("https://"), href


def _flat(path):
    return " ".join(path.read_text(encoding="utf-8").split())


def test_why_is_given_for_each_lost_feature_in_all_copies():
    for path in (HTML, ROOT / "README.md", ROOT / "docs" / "pr-description.md"):
        text = _flat(path)
        assert text.count(WHY) == 3, path
        for phrase in ("rådhuspl", "Stednavnets undertype", "Kommunefilter i søgetjenesten"):
            assert phrase in text, (path, phrase)
