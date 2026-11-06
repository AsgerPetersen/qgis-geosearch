# -*- coding: utf-8 -*-
"""
/***************************************************************************
Name                 : geosearch_dk
Description          : Search suggestions in QGIS using SDFI's Gsearch service
Date                 : 09-04-2019
copyright            : (C) 2019 by Septima
author               : asger@septima.dk
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 3 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os

from qgis.PyQt import QtCore
from qgis.PyQt.QtCore import QSettings

from ..bifrost import settings_model as model
from ..bifrost.transport import DEFAULT_BASE_URL
from ..bifrost.types import TYPES
from .qgissettingmanager import *

# Bundled Bifrost key: used when neither the setting nor the BIFROST_KEY
# environment variable gives a key. Empty until Klimadatastyrelsen has said
# whether the plugin may ship a shared key (#5).
DEFAULT_BIFROST_KEY = ""
# Used when the "Bifrost URL" setting is empty. Pending the production URL (#5).
DEFAULT_BIFROST_URL = DEFAULT_BASE_URL
# How to get a key. Pending #5; until then the Bifrost docs.
BIFROST_KEY_HELP_URL = (
    "https://bifrost.test42.dataforsyningen.dk/docs/da/#authentication"
)


class _QSettingsStore:
    """``contains``/``remove`` on QSettings, for ``settings_model.migrate``."""

    def __init__(self, qsettings, prefix=""):
        self.qsettings = qsettings
        self.prefix = prefix

    def contains(self, name):
        return self.qsettings.contains(self.prefix + name)

    def remove(self, name):
        self.qsettings.remove(self.prefix + name)


class Settings(SettingManager):
    settings_updated = QtCore.pyqtSignal()

    def __init__(self):
        SettingManager.__init__(self, "Geosearch DK")

        self.add_setting(String("kommunefilter", Scope.Global, ""))
        # Empty: DEFAULT_BIFROST_URL. The default is not stored, so a new
        # default (#5) reaches everyone who has not set a URL.
        self.add_setting(String(model.URL_SETTING, Scope.Global, ""))
        # Empty: the BIFROST_KEY environment variable, else DEFAULT_BIFROST_KEY.
        self.add_setting(String(model.KEY_SETTING, Scope.Global, ""))

        # The order of TYPES is the order results are displayed in
        for t in TYPES:
            self.add_setting(
                Bool(
                    model.type_setting(t.key),
                    Scope.Global,
                    model.type_default(t.key),
                )
            )

        self._migratesettings()

    def bifrost_url(self):
        return model.base_url(self.value(model.URL_SETTING))

    def bifrost_key(self, environ=None):
        return model.api_key(
            self.value(model.KEY_SETTING), DEFAULT_BIFROST_KEY, environ
        )

    def selected_type_keys(self):
        return model.selected_type_keys(self.value, TYPES)

    def emit_updated(self):
        self.settings_updated.emit()

    def _migratesettings(self):
        """Migrate settings from 3.x, see ``settings_model.migrate``."""
        # Where qgissettingmanager stores global settings, and where its
        # older versions did.
        model.migrate(_QSettingsStore(QSettings(), f"plugins/{self.plugin_name}/"))
        model.migrate(_QSettingsStore(QSettings(self.plugin_name, self.plugin_name)))
