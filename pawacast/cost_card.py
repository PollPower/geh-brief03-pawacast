"""Read Maji Moto cost figures the same way the Streamlit app does.

Headline is (b) all-in cost per connection. (a) is generation sized to
forecast demand. Never sum them: both views attribute the same capex.
"""
from __future__ import annotations

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_PATH = ROOT / "results" / "cost_estimate.json"


def load_cost_estimate(path: pathlib.Path | None = None) -> dict:
    p = pathlib.Path(path) if path else DEFAULT_PATH
    return json.loads(p.read_text(encoding="utf-8"))


def maji_moto_cost(path: pathlib.Path | None = None) -> dict:
    """Headline (b) + secondary (a). Raises if the current JSON keys are missing."""
    raw = load_cost_estimate(path)
    if "maji_moto" not in raw:
        raise KeyError("cost_estimate.json has no maji_moto block")
    m = raw["maji_moto"]
    if "size_p50" not in m:
        raise KeyError("maji_moto is missing size_p50")
    size = m["size_p50"]
    try:
        a = size["a_generation_and_storage_sized_to_demand"]
        b = size["b_all_in_per_connection_from_actuals"]
    except KeyError as e:
        raise KeyError(
            "cost_estimate.json uses the post-correction keys "
            "a_generation_and_storage_sized_to_demand and "
            "b_all_in_per_connection_from_actuals"
        ) from e
    households = int(size.get("households") or m.get("households") or 100)
    return {
        "households": households,
        "headline": "all-in per connection",
        "b_usd_per_connection": float(b["usd_per_connection"]),
        "b_cost_usd": float(b["cost_usd"]),
        "a_kwp": float(a["kwp"]),
        "a_usd_per_kwp": float(a["usd_per_kwp_all_in"]),
        "a_cost_usd": float(a["cost_usd"]),
        "do_not_sum": True,
    }
