# -*- coding: utf-8 -*-
"""
/***************************************************************************
Name                 : geosearch_dk
Description          : Search suggestions in QGIS using SDFI's Gsearch service
Date                 : 24-05-2013
copyright            : (C) 2013 by Septima
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

from builtins import object

from qgis.PyQt.QtCore import QFileInfo, QSettings, QTimer, QTranslator, qVersion, Qt
from qgis.PyQt.QtWidgets import QDockWidget, QAction
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsApplication

from .config import Settings, OptionsFactory

from .searchbox import SearchBox
from . import whatsnew


class SeptimaGeoSearch(object):

    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.iface = iface

        # initialize plugin directory
        self.plugin_dir = (
            QFileInfo(QgsApplication.qgisUserDatabaseFilePath()).path()
            + "/python/plugins/"
            + __package__
        )

        # initialize locale. Default to Danish
        self.config = QSettings()
        localePath = ""
        try:
            locale = self.config.value("locale/userLocale")[0:2]
        except:
            locale = "da"

        if QFileInfo(self.plugin_dir).exists():
            localePath = self.plugin_dir + "/i18n/" + locale + ".qt.qm"

        if QFileInfo(localePath).exists():
            self.translator = QTranslator()
            self.translator.load(localePath)

            if qVersion() > "4.3.3":
                QgsApplication.installTranslator(self.translator)

        # new config method
        self.settings = Settings()
        self.options_factory = OptionsFactory(self.settings)
        self.options_factory.setTitle("Geosearch DK")
        iface.registerOptionsWidgetFactory(self.options_factory)

    def initGui(self):
        # create the widget to display information
        self.searchwidget = SearchBox(self.iface, self.settings)
        # create the dockwidget with the correct parent and add the valuewidget
        self.searchdockwidget = QDockWidget(
            "Geosearch DK", self.iface.mainWindow()
        )
        self.searchdockwidget.setObjectName("Geosearch DK")
        self.searchdockwidget.setWidget(self.searchwidget)
        # add the dockwidget to iface
        self.iface.addDockWidget(
            Qt.DockWidgetArea.TopDockWidgetArea, self.searchdockwidget
        )
        # Make changed settings apply immediately
        self.settings.settings_updated.connect(self.searchwidget.readconfig)
        if self.settings.kommunefilter_migrated_now:
            self.settings.kommunefilter_migrated_now = False
            self.searchwidget.showKommunefilterMigrationNotice()

        # "Hvad er nyt" once after an upgrade, when the main window is up.
        self.notice_timer = QTimer()
        self.notice_timer.setSingleShot(True)
        self.notice_timer.timeout.connect(self._show_notice)
        if self.iface.mainWindow().isVisible():
            self.notice_timer.start(500)
        else:
            self.iface.initializationCompleted.connect(self._start_notice_timer)

    def _start_notice_timer(self):
        self.notice_timer.start(500)

    def _show_notice(self):
        whatsnew.maybe_show_on_startup(self.iface.mainWindow(), self.settings)

    def unload(self):
        self.notice_timer.stop()
        try:
            self.iface.initializationCompleted.disconnect(self._start_notice_timer)
        except (TypeError, RuntimeError):
            pass
        whatsnew.close_whats_new()
        self.searchwidget.unload()  # try to avoid processing events, when QGIS is closing
        self.iface.removeDockWidget(self.searchdockwidget)
        self.iface.unregisterOptionsWidgetFactory(self.options_factory)
