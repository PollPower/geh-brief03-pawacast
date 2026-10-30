"""Streamlit AppTest smoke: every demo site, a dropped pin, and Nigeria."""
from __future__ import annotations

import pathlib

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from pawacast.features import build_features as real_build_features
from pawacast.targets.demo import DEMO_SITES

APP = pathlib.Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"
TIMEOUT = 60


def _fake_folium(tooltip=None, click=None):
    def _inner(*_a, **_k):
        return {
            "last_object_clicked_tooltip": tooltip,
            "last_clicked": click,
        }

    return _inner


def _fake_build_features(sites, name=None, refresh=False):
    if name == "demo_sites":
        return real_build_features(sites, name=name, refresh=refresh)
    row = sites.iloc[0]
    return pd.DataFrame(
        [
            {
                "site_id": row["site_id"],
                "lat": float(row["lat"]),
                "lon": float(row["lon"]),
                "bld_count": 300,
                "grid_dist_km": 5.0,
            }
        ]
    )


def _launch(monkeypatch, tooltip=None, click=None) -> AppTest:
    monkeypatch.setattr("streamlit_folium.st_folium", _fake_folium(tooltip, click))
    monkeypatch.setattr("pawacast.features.build_features", _fake_build_features)
    at = AppTest.from_file(str(APP), default_timeout=TIMEOUT)
    at.run(timeout=TIMEOUT)
    return at


def _by_label(widgets, label: str):
    found = [w for w in widgets if getattr(w, "label", None) == label]
    assert found, (
        f"no widget labelled {label!r}; "
        f"have {[getattr(w, 'label', None) for w in widgets]}"
    )
    return found[0]


def _assert_ok(at: AppTest) -> None:
    assert not at.exception, f"app exception: {at.exception}"
    assert not at.error, f"app error: {at.error}"


def _open_how_tested(at: AppTest) -> None:
    how = _by_label(at.expander, "How tested")
    body = " ".join(m.value for m in how.markdown)
    assert "TRAIN" in body
    assert "R-test" in body


def _exercise(at: AppTest) -> AppTest:
    _assert_ok(at)
    _by_label(at.number_input, "Customers").set_value(120).run(timeout=TIMEOUT)
    _assert_ok(at)
    _by_label(at.number_input, "month").set_value(3).run(timeout=TIMEOUT)
    _by_label(at.number_input, "kWh / household").set_value(4.2).run(timeout=TIMEOUT)
    _by_label(at.button, "Add").click().run(timeout=TIMEOUT)
    _assert_ok(at)
    assert at.session_state.readings
    _open_how_tested(at)
    _assert_ok(at)
    return at


@pytest.mark.parametrize("site_name", list(DEMO_SITES["name"]))
def test_each_demo_site(monkeypatch, site_name):
    at = _launch(monkeypatch, tooltip=site_name)
    row = DEMO_SITES[DEMO_SITES["name"] == site_name].iloc[0]
    assert at.session_state.site_id == row.site_id
    assert at.session_state.customers == 100
    _exercise(at)


def test_dropped_pin_mocked_features(monkeypatch):
    pin = {"lat": -1.50, "lng": 36.08}
    at = _launch(monkeypatch, click=pin)
    assert at.session_state.site_id == "click"
    assert at.session_state.name == "Dropped pin"
    assert at.session_state.feats["bld_count"] == 300
    _exercise(at)


def test_nigeria_country(monkeypatch):
    at = _launch(monkeypatch, tooltip="Maji Moto, Narok (PollPower pilot)")
    _by_label(at.selectbox, "Country").select("NG").run(timeout=TIMEOUT)
    _assert_ok(at)
    assert at.session_state.country == "NG"
    table = at.table[0].value
    kwhs = [str(v) for v in table["kwh"].tolist()]
    assert any(v.startswith("11") for v in kwhs)
    _exercise(at)
