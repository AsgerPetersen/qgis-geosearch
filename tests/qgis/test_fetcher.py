"""The plugin's Bifrost fetcher (QGIS networking) against the mock Bifrost.

The ``bifrost_mock`` fixture points the ``bifrost_url``/``bifrost_key``
settings at the mock; see conftest.py. More fetcher and selection tests go here.
"""

import time

import pytest
from qgis.PyQt.QtCore import QCoreApplication

import bifrost_cases as bc


def wait_for(condition, timeout=10):
    end = time.monotonic() + timeout
    while not condition():
        if time.monotonic() > end:
            raise TimeoutError("timed out")
        QCoreApplication.processEvents()
        time.sleep(0.01)


@pytest.fixture
def fetcher(bifrost_mock):
    from geosearch_dk.bifrost.fetcher import BifrostFetcher
    from geosearch_dk.config import Settings

    f = BifrostFetcher(Settings())
    events = []
    f.finished.connect(lambda: events.append("finished"))
    f.not_authorized.connect(lambda: events.append("not_authorized"))
    f.missing_key.connect(lambda: events.append("missing_key"))
    f.events = events
    yield f
    f.abort_all()


def test_fetcher_uses_the_mock(fetcher, bifrost_mock):
    assert fetcher.base_url() == bifrost_mock.url


def test_search_is_answered_from_the_recording(fetcher, bifrost_mock):
    case = next(c for c in bc.load_cases() if c["id"] == "adr-vangebovej-71-alle-typer")
    assert fetcher.fetch(case["input"]) is not None
    wait_for(lambda: fetcher.events)
    assert fetcher.events == ["finished"]
    texts = [r["text"] for r in fetcher.get_result() if r["status"] == "ok"]
    assert texts[0] == case["expect"]["text"]
    assert {e["fixture"] for e in bifrost_mock.request_log()} == {"exact"}


def test_geometry_of_a_hit(fetcher):
    fetcher.fetch("Vangebovej 71")
    wait_for(lambda: fetcher.events)
    row = next(r for r in fetcher.get_result() if r["status"] == "ok")
    got = []
    fetcher.fetch_geometry(row, lambda r, geojson: got.append(geojson))
    wait_for(lambda: got)
    assert got[0] and got[0]["type"] == "Point"


def test_not_authorized(fetcher, bifrost_mock):
    bifrost_mock.configure(error="401")
    fetcher.fetch("Vangebovej 71")
    wait_for(lambda: "not_authorized" in fetcher.events)


def test_503_is_retried_after_retry_after(fetcher, bifrost_mock):
    bifrost_mock.configure(error="503", error_count=1, retry_after=1)
    fetcher.fetch("Vangebovej 71")
    wait_for(lambda: fetcher.events, timeout=15)
    statuses = [e["status"] for e in bifrost_mock.request_log()]
    assert statuses[0] == 503 and 200 in statuses
    assert all(r["status"] == "ok" for r in fetcher.get_result())


def test_service_unavailable_gives_error_rows(fetcher, bifrost_mock):
    bifrost_mock.configure(error="503", retry_after=600)  # too long to wait for: no retry
    fetcher.fetch("Vangebovej 71")
    wait_for(lambda: fetcher.events)
    assert fetcher.get_result()
    assert all(r["status"] == "error" for r in fetcher.get_result())
