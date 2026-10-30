"""Cost card reads cost_estimate.json the same way the Streamlit app does."""
from __future__ import annotations

import pytest

from pawacast.cost_card import load_cost_estimate, maji_moto_cost


def test_maji_moto_headline_is_all_in_per_connection():
    c = maji_moto_cost()
    assert c["headline"] == "all-in per connection"
    assert c["do_not_sum"] is True
    assert c["households"] == 100
    assert c["b_usd_per_connection"] == pytest.approx(1040.851, rel=1e-3)
    assert c["b_cost_usd"] == pytest.approx(104085, rel=1e-3)
    assert c["a_kwp"] == pytest.approx(3.335, rel=1e-3)
    assert c["a_cost_usd"] == pytest.approx(27447, rel=1e-3)
    assert c["a_cost_usd"] + c["b_cost_usd"] != pytest.approx(c["b_cost_usd"])


def test_load_matches_app_helper():
    raw = load_cost_estimate()
    size = raw["maji_moto"]["size_p50"]
    assert "a_generation_and_storage_sized_to_demand" in size
    assert "b_all_in_per_connection_from_actuals" in size
    a = size["a_generation_and_storage_sized_to_demand"]
    b = size["b_all_in_per_connection_from_actuals"]
    c = maji_moto_cost()
    assert c["b_cost_usd"] == b["cost_usd"]
    assert c["a_cost_usd"] == a["cost_usd"]
