"""The English translation (i18n/en.qt.ts) covers the tr() strings of the Python files."""

import ast
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[2] / "src" / "geosearch_dk"
TS = PLUGIN / "i18n" / "en.qt.ts"
# The Python files whose tr() strings are translated, and their .ts context.
FILES = {"searchbox.py": "SearchBox", "whatsnew.py": "WhatsNewDialog"}


def tr_strings(path):
    found = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "tr"
            and node.args
            and isinstance(node.args[0], ast.Constant)
        ):
            found.add(node.args[0].value)
    return found


def ts_messages(context):
    root = ET.parse(TS).getroot()
    for ctx in root.iter("context"):
        if ctx.findtext("name") == context:
            return {m.findtext("source"): m.findtext("translation") for m in ctx.iter("message")}
    return {}


@pytest.mark.parametrize("filename", sorted(FILES))
def test_ts_matches_the_tr_strings(filename):
    messages = ts_messages(FILES[filename])
    assert set(messages) == tr_strings(PLUGIN / filename)
    assert all(messages.values())


def test_no_stale_dataforsyningen_strings():
    for context in FILES.values():
        assert not [s for s in ts_messages(context) if "ataforsyningen" in s]
