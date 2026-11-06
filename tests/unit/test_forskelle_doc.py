"""docs/forskelle-gsearch-bifrost.md is generated from the recordings and must be up to date."""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "forskelle-gsearch-bifrost.md"


def _generator():
    path = ROOT / "tests" / "tools" / "forskelle_doc.py"
    spec = importlib.util.spec_from_file_location("forskelle_doc", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_document_matches_recordings():
    assert DOC.read_text(encoding="utf-8") == _generator().render(), (
        "Run: uv run python tests/tools/forskelle_doc.py"
    )


def test_every_example_links_an_existing_recording():
    gen = _generator()
    for section in gen.spec.SECTIONS:
        for example in section.examples:
            assert (gen.FIXTURES / ("%s.json" % example.fixture)).is_file(), example.fixture


def test_recordings_contain_no_secrets():
    for path in sorted((ROOT / "tests" / "fixtures" / "forskelle").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for request in data["gsearch"]["requests"]:
            assert "token=REDACTED" in request["url"], path.name
