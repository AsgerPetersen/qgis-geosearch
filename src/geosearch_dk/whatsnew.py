# -*- coding: utf-8 -*-
"""
"Hvad er nyt" – what changed in Geosearch DK 4.0 (Bifrost), and why.

The text is help/hvad_er_nyt.html. Public API:

    show_whats_new(parent=None, anchor=None, settings=None)
        Open the dialog, optionally scrolled to an anchor in the text,
        e.g. "kommunefilter". Returns the dialog (non-modal).

The dialog is shown by itself once per NOTICE_VERSION (setting
``notice_seen_version``), see maybe_show_on_startup().
"""

import os

from qgis.PyQt.QtCore import Qt, QTimer, QUrl
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QTextBrowser,
    QVBoxLayout,
)

# Bump to show the dialog again after an upgrade (and update the text).
NOTICE_VERSION = "4.0.0"
HELP_FILE = os.path.join(os.path.dirname(__file__), "help", "hvad_er_nyt.html")

_dialog = None


class WhatsNewDialog(QDialog):
    def __init__(self, settings, parent=None, anchor=None, dont_show_again=None):
        super().__init__(parent)
        self.settings = settings
        self.setObjectName("geosearchWhatsNew")
        self.setWindowTitle(self.tr("Geosearch DK – hvad er nyt"))
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.resize(600, 640)

        self.browser = QTextBrowser(self)
        self.browser.setObjectName("whatsNewBrowser")
        self.browser.setOpenExternalLinks(True)
        self.browser.setSource(QUrl.fromLocalFile(HELP_FILE))

        if dont_show_again is None:
            dont_show_again = notice_seen(settings)
        self.dontShowAgain = QCheckBox(self.tr("Vis ikke igen"), self)
        self.dontShowAgain.setObjectName("dontShowAgain")
        self.dontShowAgain.setToolTip(
            self.tr("Fjern fluebenet for at se denne besked igen næste gang QGIS starter")
        )
        self.dontShowAgain.setChecked(dont_show_again)
        self.dontShowAgain.toggled.connect(self._save)
        self._save(dont_show_again)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        buttons.button(QDialogButtonBox.StandardButton.Close).setText(self.tr("Luk"))
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.browser)
        layout.addWidget(self.dontShowAgain)
        layout.addWidget(buttons)

        self.scroll_to(anchor)

    def scroll_to(self, anchor=None):
        # Deferred: the document has no layout before the dialog is shown.
        if anchor:
            QTimer.singleShot(0, lambda: self.browser.scrollToAnchor(anchor))
        else:
            QTimer.singleShot(
                0, lambda: self.browser.verticalScrollBar().setValue(0)
            )

    def _save(self, checked):
        # Saved at once, so the choice holds even if QGIS quits with the dialog open.
        self.settings.set_value(
            "notice_seen_version", NOTICE_VERSION if checked else ""
        )


def notice_seen(settings):
    return settings.value("notice_seen_version") == NOTICE_VERSION


def show_whats_new(parent=None, anchor=None, settings=None):
    """Open "Hvad er nyt", optionally at an anchor in help/hvad_er_nyt.html.

    From a modal dialog (e.g. the settings page), pass a widget in that dialog
    as parent, so the new dialog is not blocked by it.
    """
    return _show(parent, anchor, settings, dont_show_again=None)


def maybe_show_on_startup(parent, settings):
    """Show the notice if this NOTICE_VERSION has not been seen. Returns the dialog or None."""
    if notice_seen(settings):
        return None
    # Pre-ticked: shown once unless the user asks to see it again.
    return _show(parent, None, settings, dont_show_again=True)


def close_whats_new():
    global _dialog
    if _dialog is not None:
        try:
            _dialog.close()
        except RuntimeError:
            pass  # already deleted
    _dialog = None


def _show(parent, anchor, settings, dont_show_again):
    global _dialog
    if settings is None:
        from .config import Settings

        settings = Settings()
    close_whats_new()
    _dialog = WhatsNewDialog(
        settings, parent, anchor=anchor, dont_show_again=dont_show_again
    )
    _dialog.show()
    _dialog.raise_()
    _dialog.activateWindow()
    return _dialog
