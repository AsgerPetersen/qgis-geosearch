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

import json
import os
import re
import sys
import time

from osgeo import ogr

from qgis.PyQt.QtWidgets import QFrame, QMessageBox, QPushButton, QApplication
from qgis.PyQt.QtGui import QColor, QIcon
from qgis.PyQt.QtCore import QSettings, QSize
from qgis.PyQt import uic
from qgis.core import (
    QgsApplication,
    QgsWkbTypes,
    QgsGeometry,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProject,
    QgsRectangle,
    Qgis,
)
from qgis.gui import QgsVertexMarker, QgsRubberBand

from . import qgisutils, whatsnew
from .suggester import Suggester
from .config import Settings

# Seconds a not-authorised/missing-key message stays and is not repeated.
MESSAGE_DURATION = 15
ZOOM_BUFFER = 200.0

FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "ui_search.ui")
)


class SearchBox(QFrame, FORM_CLASS):

    def __init__(self, qgisIface, settings):
        QFrame.__init__(self, qgisIface.mainWindow())
        self.setupUi(self)

        self.qgisIface = qgisIface
        self.settings = settings
        self.markers = []
        self._last_message = {}
        self._zoomed_extent = None
        self.readconfig()  # old config

        self.setFrameStyle(QFrame.Shape.StyledPanel + QFrame.Shadow.Raised)

        self.suggester = Suggester(
            settings=settings,
            searchbox_widget=self.searchEdit,
            notauthorized_func=self.handleNotAuthorized,
            missingkey_func=self.handleMissingKey,
        )
        self.setupCrsTransform()

        self.searchEdit.returnPressed.connect(self.showSelected)
        self.searchEdit.cleared.connect(self.clearSelection)
        self.searchEdit.textEdited.connect(self.clearSelection)
        if hasattr(self.searchEdit, "setPlaceholderText"):
            self.searchEdit.setPlaceholderText(
                self.tr("Søg adresse, stednavn, postnummer, matrikel m.m.")
            )

        # Listen to crs changes
        self.qgisIface.mapCanvas().destinationCrsChanged.connect(
            self.setupCrsTransform
        )

        self.adjustSize()
        self.resize(50, self.height())
        self.searchEdit.setFocus()

        self.settingsButton = self.settingsButton
        settings_icon = QIcon(
            ":images/themes/default/console/iconSettingsConsole.svg"
        )
        self.settingsButton.setIcon(settings_icon)
        self.settingsButton.setIconSize(QSize(16, 16))
        # self.settingsButton.setStyleSheet('border: none;')
        self.settingsButton.setFixedSize(20, 20)

        self.settingsButton.clicked.connect(self.show_settings)

        self.infoButton.setIcon(
            QIcon(os.path.join(os.path.dirname(__file__), "icons", "info.svg"))
        )
        self.infoButton.setIconSize(QSize(16, 16))
        self.infoButton.setFixedSize(20, 20)
        self.infoButton.clicked.connect(self.show_whats_new)

    def show_whats_new(self):
        whatsnew.show_whats_new(self.qgisIface.mainWindow(), settings=self.settings)

    def show_settings(self):
        self.qgisIface.showOptionsDialog(currentPage="geosearchOptions")

    def readconfig(self):
        settings = Settings()  # new config
        # Old way was storing settings in global scope. Leave advanced options there for now
        s = QSettings()
        k = __package__

        # prefix muncodes
        # muncodes = re.findall(r'\d+', settings.value('kommunefilter'))
        # areafilter = ','.join(['muncode0'+str(k) for k in muncodes])

        self.config = {
            #'token' : settings.value('token'),
            #'resources': settings.resources,
            #'resourcesfilter': ",".join(settings.selected_resources()),
            "maxresults": s.value(k + "/maxresults", 25, type=int),
            #'callback': str(s.value(k + "/callback", "callback", type=str)),
            #'areafilter': areafilter,
            "rubber_color": str(
                s.value(k + "/rubber_color", "#FF0000", type=str)
            ),
            "rubber_width": s.value(k + "/rubber_width", 4, type=int),
            "marker_color": str(
                s.value(k + "/marker_color", "#FF0000", type=str)
            ),
            "marker_icon": s.value(
                k + "/marker_icon",
                QgsVertexMarker.IconType.ICON_CROSS,
                type=int,
            ),
            "marker_width": s.value(k + "/marker_width", 4, type=int),
            "marker_size": s.value(k + "/marker_size", 30, type=int),
        }

    def handleNotAuthorized(self):
        self._pushSettingsMessage(
            "notauthorized",
            self.tr("Afvist af Bifrost"),
            self.tr("Nøglen til Bifrost mangler eller er ugyldig."),
        )

    def handleMissingKey(self):
        self._pushSettingsMessage(
            "missingkey",
            self.tr("Bifrost-nøgle mangler"),
            self.tr(
                "Geosearch DK kræver en nøgle til Bifrost. Angiv den i "
                "indstillingerne eller i miljøvariablen BIFROST_KEY."
            ),
        )

    def _pushSettingsMessage(self, kind, title, message):
        # Searches run as the user types; show each message once per duration.
        now = time.monotonic()
        last = self._last_message.get(kind)
        if last is not None and now - last < MESSAGE_DURATION:
            return
        self._last_message[kind] = now
        button_text = self.tr("Åbn settings")
        widget = self.qgisIface.messageBar().createMessage(title, message)
        button = QPushButton(widget)
        button.setText(button_text)
        button.pressed.connect(
            lambda: self.qgisIface.showOptionsDialog(
                currentPage="geosearchOptions"
            )
        )
        widget.layout().addWidget(button)
        self.qgisIface.messageBar().pushWidget(
            widget, level=Qgis.MessageLevel.Warning, duration=MESSAGE_DURATION
        )

    def setupCrsTransform(self):
        if QgsCoordinateReferenceSystem is not None:
            srcCrs = QgsCoordinateReferenceSystem.fromEpsgId(25832)
            dstCrs = qgisutils.getCurrentCrs(self.qgisIface)
            self.crsTransform = QgsCoordinateTransform(
                srcCrs, dstCrs, QgsProject.instance()
            )

    def setMarkerGeom(self, geom):
        # Show geometry
        self.clearMarkerGeom()
        self._setMarkerGeom(geom)

    def _setMarkerGeom(self, geom):
        if geom.isMultipart():
            geometries = self._extractAsSingle(geom)
            for g in geometries:
                self._setMarkerGeom(g)
        else:
            if (
                QgsWkbTypes.geometryType(geom.wkbType())
                == QgsWkbTypes.GeometryType.PointGeometry
            ):
                m = self._setPointMarker(geom)
            elif QgsWkbTypes.geometryType(geom.wkbType()) in (
                QgsWkbTypes.GeometryType.LineGeometry,
                QgsWkbTypes.GeometryType.PolygonGeometry,
            ):
                m = self._setRubberBandMarker(geom)
            self.markers.append(m)

    def _setPointMarker(self, pointgeom):
        m = QgsVertexMarker(self.qgisIface.mapCanvas())
        m.setColor(QColor(self.config["marker_color"]))
        m.setIconType(self.config["marker_icon"])
        m.setPenWidth(self.config["marker_width"])
        m.setIconSize(self.config["marker_size"])
        m.setCenter(pointgeom.asPoint())
        return m

    def _setRubberBandMarker(self, geom):
        m = QgsRubberBand(self.qgisIface.mapCanvas())  # not polygon
        if (
            QgsWkbTypes.geometryType(geom.wkbType())
            == QgsWkbTypes.GeometryType.LineGeometry
        ):
            linegeom = geom
        elif (
            QgsWkbTypes.geometryType(geom.wkbType())
            == QgsWkbTypes.GeometryType.PolygonGeometry
        ):
            linegeom = QgsGeometry.fromPolylineXY(geom.asPolygon()[0])
        m.setToGeometry(linegeom, None)
        m.setColor(QColor(self.config["rubber_color"]))
        m.setWidth(self.config["rubber_width"])
        return m

    def clearMarkerGeom(self):
        if self.markers:
            for m in self.markers:
                self.qgisIface.mapCanvas().scene().removeItem(m)
        self.markers = []

    def clearSelection(self):
        """A new search or a cleared box: drop the marker and any pending geometry."""
        self.suggester.fetcher.cancel_geometry()
        self._zoomed_extent = None
        self.clearMarkerGeom()

    def clear(self):
        self.clearSelection()
        self.ui.searchEdit.clear()

    def showSelected(self):
        try:
            self.suggester.preventSuggest()
            self.clearSelection()

            row = self.suggester.selectedObject[0]
            if not row:
                return
            if row["status"] == "error":
                QMessageBox.information(
                    self.qgisIface.mainWindow(),
                    "Geosearch DK - Fejl",
                    row.get("message") or row["text"],
                )
                return

            # Zoom to the point now; the full geometry follows when fetched.
            point = self._geojsonToGeometry(row.get("point"))
            if point:
                self._zoomTo(point)
                self._showGeometry(point)
            self.suggester.fetcher.fetch_geometry(row, self._onGeometry)
        except Exception as e:
            QgsApplication.messageLog().logMessage(
                "Kunne ikke vise valgt objekt: " + str(e),
                "Geosearch DK",
                Qgis.MessageLevel.Warning,
            )

    def _onGeometry(self, row, geojson):
        # Only called for the current selection (see BifrostFetcher.fetch_geometry).
        geom = self._geojsonToGeometry(geojson)
        if not geom:
            if self._zoomed_extent is None:
                point = self._geojsonToGeometry(row.get("point"))
                if point:
                    self._zoomTo(point)
                    self._showGeometry(point)
            return
        # Follow with the zoom only if the user has not moved the map meanwhile.
        if self._zoomed_extent is None or self._mapUnmoved():
            self._zoomTo(geom)
        self._showGeometry(geom)

    def _geojsonToGeometry(self, geojson):
        """QgsGeometry in EPSG:25832 from a GeoJSON geometry, or None."""
        if not geojson:
            return None
        ogr_geom = ogr.CreateGeometryFromJson(json.dumps(geojson))
        if ogr_geom is None:
            return None
        geom = QgsGeometry.fromWkt(ogr_geom.ExportToWkt())
        return None if geom.isNull() else geom

    def _zoomTo(self, geom):
        bufgeom = geom.buffer(ZOOM_BUFFER, 2)
        bufgeom.transform(self.crsTransform)
        mc = self.qgisIface.mapCanvas()
        mc.setExtent(bufgeom.boundingBox())
        mc.refresh()
        self._zoomed_extent = QgsRectangle(mc.extent())

    def _mapUnmoved(self):
        current = self.qgisIface.mapCanvas().extent()
        tolerance = max(current.width(), current.height()) * 1e-6
        return (
            abs(current.xMinimum() - self._zoomed_extent.xMinimum()) <= tolerance
            and abs(current.yMinimum() - self._zoomed_extent.yMinimum()) <= tolerance
            and abs(current.xMaximum() - self._zoomed_extent.xMaximum()) <= tolerance
            and abs(current.yMaximum() - self._zoomed_extent.yMaximum()) <= tolerance
        )

    def _showGeometry(self, geom):
        geom = QgsGeometry(geom)
        geom.transform(self.crsTransform)
        self.setMarkerGeom(geom)
        self.qgisIface.mapCanvas().refresh()

    def show_about_dialog(self):
        infoString = self.tr(
            "Geosearch DK lader brugeren zoome til navngivne steder i Danmark.<br />"
            "Pluginet benytter Klimadatastyrelsens søgetjeneste Bifrost, som afløser GSearch.<br />"
            'Pluginets webside: <a href="http://github.com/Septima/qgis-geosearch">github.com/Septima/qgis-geosearch</a><br />'
            "Udviklet af: Septima<br />"
            'Mail: <a href="mailto:kontakt@septima.dk">kontakt@septima.dk</a><br />'
            'Web: <a href="http://www.septima.dk">www.septima.dk</a>\n'
        )
        QMessageBox.information(
            self.qgisIface.mainWindow(), "Om Geosearch DK", infoString
        )

    def unload(self):
        self.suggester.unload()
        self.clearMarkerGeom()

    def _extractAsSingle(self, geom):
        multiGeom = QgsGeometry()
        geometries = []
        if geom.type() == QgsWkbTypes.GeometryType.PointGeometry:
            if geom.isMultipart():
                multiGeom = geom.asMultiPoint()
                for i in multiGeom:
                    geometries.append(QgsGeometry().fromPointXY(i))
            else:
                geometries.append(geom)
        elif geom.type() == QgsWkbTypes.GeometryType.LineGeometry:
            if geom.isMultipart():
                multiGeom = geom.asMultiPolyline()
                for i in multiGeom:
                    geometries.append(QgsGeometry().fromPolylineXY(i))
            else:
                geometries.append(geom)
        elif geom.type() == QgsWkbTypes.GeometryType.PolygonGeometry:
            if geom.isMultipart():
                multiGeom = geom.asMultiPolygon()
                for i in multiGeom:
                    geometries.append(QgsGeometry().fromPolygonXY(i))
            else:
                geometries.append(geom)
        return geometries


if __name__ == "__main__":

    app = QApplication(sys.argv)

    suggest = SearchBox()
    suggest.show()

    exec_func = getattr(app, "exec", None) or getattr(app, "exec_")
    sys.exit(exec_func())
