"""The "Hvad er nyt" notice (whatsnew.py): once per notice version, the ⓘ button, anchors."""

import time

import pytest
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtWidgets import QApplication


def wait_for(condition, timeout=5):
    end = time.monotonic() + timeout
    while not condition():
        if time.monotonic() > end:
            raise TimeoutError("timed out")
        QCoreApplication.processEvents()
        time.sleep(0.01)


def process_events(seconds=0.2):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        QCoreApplication.processEvents()
        time.sleep(0.01)


def dialogs():
    return [
        w
        for w in QApplication.topLevelWidgets()
        if w.objectName() == "geosearchWhatsNew" and w.isVisible()
    ]


@pytest.fixture
def whatsnew():
    from geosearch_dk import whatsnew

    yield whatsnew
    whatsnew.close_whats_new()
    process_events(0.05)


def test_shown_after_start_once_per_notice_version(iface, whatsnew):
    from geosearch_dk import classFactory
    from geosearch_dk.config import Settings

    window = iface.mainWindow()
    window.show()  # QGIS is up: the notice follows shortly after initGui
    try:
        for expected in (1, 0):  # first start after the upgrade, then the next start
            plugin = classFactory(iface)
            plugin.initGui()
            try:
                if expected:
                    wait_for(lambda: len(dialogs()) == 1)
                    assert dialogs()[0].dontShowAgain.isChecked()
                else:
                    process_events(1.0)
                    assert dialogs() == []
                assert Settings().value("notice_seen_version") == whatsnew.NOTICE_VERSION
            finally:
                plugin.unload()
            assert dialogs() == []  # unload closes it
    finally:
        window.hide()


def test_a_new_notice_version_is_shown_again(plugin, whatsnew):
    plugin.settings.set_value("notice_seen_version", "3.9.9")
    assert whatsnew.maybe_show_on_startup(None, plugin.settings) is not None
    assert len(dialogs()) == 1


def test_unticking_shows_it_at_next_start(plugin, whatsnew):
    dialog = whatsnew.maybe_show_on_startup(None, plugin.settings)
    assert plugin.settings.value("notice_seen_version") == whatsnew.NOTICE_VERSION
    dialog.dontShowAgain.setChecked(False)
    assert plugin.settings.value("notice_seen_version") == ""
    whatsnew.close_whats_new()
    assert whatsnew.maybe_show_on_startup(None, plugin.settings) is not None


def test_info_button_opens_it(plugin, whatsnew):
    plugin.settings.set_value("notice_seen_version", whatsnew.NOTICE_VERSION)
    button = plugin.searchwidget.infoButton
    assert not button.icon().isNull()
    assert button.toolTip()
    button.click()
    wait_for(lambda: len(dialogs()) == 1)
    dialog = dialogs()[0]
    assert dialog.dontShowAgain.isChecked()
    assert "Bifrost" in dialog.browser.toPlainText()
    button.click()  # a second click replaces it, it does not open another
    wait_for(lambda: len(dialogs()) == 1)


def test_anchor_and_links(whatsnew):
    dialog = whatsnew.show_whats_new(anchor="kommunefilter")
    browser = dialog.browser
    assert browser.openExternalLinks()
    wait_for(lambda: browser.verticalScrollBar().value() > 0)
    top = whatsnew.show_whats_new()
    process_events()
    assert top.browser.verticalScrollBar().value() == 0
