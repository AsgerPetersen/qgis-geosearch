"""The compiled English translation (i18n/en.qt.qm) is up to date with en.qt.ts."""

import os
import xml.etree.ElementTree as ET

from qgis.PyQt.QtCore import QTranslator

from conftest import ROOT

I18N = os.path.join(ROOT, "src", "geosearch_dk", "i18n")


def test_qm_has_every_ts_translation():
    translator = QTranslator()
    assert translator.load(os.path.join(I18N, "en.qt.qm"))
    root = ET.parse(os.path.join(I18N, "en.qt.ts")).getroot()
    checked = 0
    for ctx in root.iter("context"):
        name = ctx.findtext("name")
        for message in ctx.iter("message"):
            source, translation = message.findtext("source"), message.findtext("translation")
            got = translator.translate(name.encode("utf-8"), source.encode("utf-8"))
            assert got == translation, (name, source)
            checked += 1
    assert checked > 0
