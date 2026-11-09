"""docs/pr-description.md (the draft upstream PR description) repeats the "Hvad er nyt" bullets."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WHY = "Hvorfor: Bifrost tilbyder det ikke."


def test_why_is_given_for_each_lost_feature():
    text = " ".join((ROOT / "docs" / "pr-description.md").read_text(encoding="utf-8").split())
    assert text.count(WHY) == 3
    for phrase in ("nørrebrog", "Stednavnets undertype", "Kommunefilter i søgetjenesten"):
        assert phrase in text, phrase
