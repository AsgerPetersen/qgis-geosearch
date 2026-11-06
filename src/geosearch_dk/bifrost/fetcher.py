"""``BifrostFetcher``: the search and geometry fetching the plugin UI uses.

Same interface as the old ``GSearchFetcher``: ``fetch(term)``, the
``finished`` signal and ``get_result()``. Built on ``core`` and ``client``.

Works with Qt5 (QGIS 3) and Qt6 (QGIS 4).
"""

from collections import OrderedDict

from qgis.core import Qgis, QgsApplication
from qgis.PyQt.QtCore import QObject, pyqtSignal

from .client import BifrostClient
from .core import collect_rows, geometry_from_response, geometry_request, plan_search
from .transport import GEOMETRY_TIMEOUT_MS, SEARCH_TIMEOUT_MS

GEOMETRY_CACHE_SIZE = 50
LOG_TAG = "Geosearch DK"


def _log(message, level=Qgis.MessageLevel.Warning):
    QgsApplication.messageLog().logMessage(message, LOG_TAG, level)


def _geometry_cache_key(row):
    ref = row.get("ref") or {}
    return (ref.get("kind"), ref.get("id"), row.get("lifecycle"))


class BifrostFetcher(QObject):
    """Searches Bifrost for the settings' selected types.

    Signals:
      ``finished``        a search completed; read the rows with ``get_result()``
      ``not_authorized``  Bifrost rejected the key (401/403)
      ``missing_key``     no key in the settings, ``BIFROST_KEY`` or the plugin; nothing sent

    Only the newest search is reported: an older one still in flight is
    aborted when a new one starts, and its reply is ignored.
    """

    finished = pyqtSignal()
    not_authorized = pyqtSignal()
    missing_key = pyqtSignal()

    def __init__(self, settings, client=None, parent=None):
        QObject.__init__(self, parent)
        self.settings = settings
        self.client = client or BifrostClient(self.base_url, self.key, parent=self)
        self.client.not_authorized.connect(self.not_authorized)
        self.result = None
        self.hidden = {}
        self._search_id = 0
        self._search_call = None
        self._geometry_id = 0
        self._geometry_call = None
        self._geometry_cache = OrderedDict()

    # --- settings ---------------------------------------------------------

    def base_url(self):
        return self.settings.bifrost_url()

    def key(self):
        return self.settings.bifrost_key()

    def selected_keys(self):
        return self.settings.selected_type_keys()

    # --- search -----------------------------------------------------------

    def fetch(self, term):
        """Start a search. Returns its id, or None when nothing was sent."""
        # Kommunefilter is applied client-side from Step 5 (#11).
        plan = plan_search(term, self.selected_keys(), kommunefilter="")
        if not plan.requests:
            return None
        if not self.key():
            self.missing_key.emit()
            return None
        self._abort_search()
        self._search_id += 1
        search_id = self._search_id
        self._search_call = self.client.send(
            plan.requests,
            lambda responses: self._on_search(search_id, plan, responses),
            SEARCH_TIMEOUT_MS,
        )
        return search_id

    def get_result(self):
        return self.result

    def _abort_search(self):
        if self._search_call is not None:
            self._search_call.abort()
            self._search_call = None

    def _on_search(self, search_id, plan, responses):
        if search_id != self._search_id:
            return
        self._search_call = None
        for request, response in zip(plan.requests, responses):
            if isinstance(response, Exception):
                _log(
                    "Fejl i kald til Bifrost /{} ({}): {}".format(
                        request.endpoint, ", ".join(request.keys), response
                    )
                )
        result = collect_rows(plan, responses)
        for row in result.rows:
            if row["status"] == "error" and row.get("message"):
                _log("Fejl fra Bifrost for {}: {}".format(row["title"], row["message"]))
        self.result = result.rows
        self.hidden = result.hidden
        self.finished.emit()

    # --- geometry ---------------------------------------------------------

    def fetch_geometry(self, row, callback):
        """Fetch the full geometry of an ok row; calls ``callback(row, geojson)``.

        ``geojson`` is a GeoJSON geometry in EPSG:25832, or None when it could
        not be fetched (use ``row["point"]``). Starting another geometry fetch,
        or ``cancel_geometry()``, drops this one: its callback is not called.
        Geometries are cached by ref.
        """
        self.cancel_geometry()
        geometry_id = self._geometry_id
        cache_key = _geometry_cache_key(row)
        if row.get("geometry"):
            callback(row, row["geometry"])
            return
        if cache_key in self._geometry_cache:
            self._geometry_cache.move_to_end(cache_key)
            callback(row, self._geometry_cache[cache_key])
            return
        self._geometry_step(geometry_id, row, 0, callback)

    def cancel_geometry(self):
        self._geometry_id += 1
        if self._geometry_call is not None:
            self._geometry_call.abort()
            self._geometry_call = None

    def _geometry_step(self, geometry_id, row, attempt, callback):
        request = geometry_request(row, attempt)
        if request is None:
            callback(row, None)
            return
        self._geometry_call = self.client.send(
            [request],
            lambda responses: self._on_geometry(
                geometry_id, row, attempt, callback, responses[0]
            ),
            GEOMETRY_TIMEOUT_MS,
        )

    def _on_geometry(self, geometry_id, row, attempt, callback, response):
        if geometry_id != self._geometry_id:
            return
        self._geometry_call = None
        if isinstance(response, Exception):
            _log("Kunne ikke hente geometri for '{}': {}".format(row["text"], response))
            callback(row, None)
            return
        geojson = geometry_from_response(row, response)
        if geojson is None:
            self._geometry_step(geometry_id, row, attempt + 1, callback)
            return
        self._geometry_cache[_geometry_cache_key(row)] = geojson
        while len(self._geometry_cache) > GEOMETRY_CACHE_SIZE:
            self._geometry_cache.popitem(last=False)
        callback(row, geojson)

    def abort_all(self):
        self._search_id += 1
        self._abort_search()
        self.cancel_geometry()
        self.client.abort_all()
