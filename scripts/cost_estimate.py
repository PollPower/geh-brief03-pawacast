"""USD unit costs from Renewvia minigridprojects capex. No consumption files.

capex is labelled local currency in the data dictionary, but magnitudes match USD
(Kalobeyei Settlement 541 kWp at 967,872 would be ~$7k if KES). Renewvia's own
carbon figure treats capex as USD (kUSD). We follow that. Kakuma capex=0 and
Emakalakala's 648 kWh / 13.5 kWp battery outlier are dropped from unit-cost stats.

Source: Renewvia (Zenodo 10.5281/zenodo.22149101, CC BY-SA 4.0).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from pawacast.features import build_features
from pawacast.model.growth import observed_multiplier
from pawacast.model.loglinear import load_frozen
from pawacast.targets.demo import DEMO_SITES
from pawacast.targets.renewvia import tariff_class

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results"
# Kenya equatorial PV: ~4.5 kWh/kWp/day (NREL PVWatts-class assumption, documented)
KWH_PER_KWP_DAY = 4.5
PERF = 0.85  # inverter/soiling/availability
DAYS = 30.44


def _stats(s: pd.Series) -> dict:
    s = s.replace([np.inf, -np.inf], np.nan).dropna()
    s = s[s > 0]
    if s.empty:
        return {"n": 0, "median": None, "p10": None, "p90": None, "min": None, "max": None}
    return {
        "n": int(len(s)),
        "median": float(s.median()),
        "p10": float(s.quantile(0.10)),
        "p90": float(s.quantile(0.90)),
        "min": float(s.min()),
        "max": float(s.max()),
    }


def main():
    proj = pd.read_parquet(ROOT / "data/raw/renewvia/minigridprojects.parquet")
    cust = pd.read_parquet(
        ROOT / "data/raw/renewvia/customers.parquet",
        columns=["projectName", "meterRole"],
    )
    n_cust = (
        cust[cust.meterRole == "Customer Meter"]
        .groupby("projectName")
        .size()
        .rename("n_customer_meters")
    )
    d = proj.merge(n_cust, left_on="projectName", right_index=True, how="left")
    d["usd_per_kwp"] = d.capex / d.sizePv
    d["usd_per_kwh_storage"] = d.capex / d.sizeBattery
    d["usd_per_connection"] = d.capex / d.n_customer_meters
    d["kwh_storage_per_kwp"] = d.sizeBattery / d.sizePv
    d["kwp_per_connection"] = d.sizePv / d.n_customer_meters

    drop = (d.capex <= 0) | (d.projectName == "Emakalakala")
    use = d.loc[~drop].copy()
    dropped = d.loc[drop, "projectName"].tolist()

    by = {}
    for country, g in use.groupby("country"):
        by[country] = {
            "usd_per_kwp": _stats(g.usd_per_kwp),
            "usd_per_kwh_storage": _stats(g.usd_per_kwh_storage),
            "usd_per_connection": _stats(g.usd_per_connection),
            "kwh_storage_per_kwp": _stats(g.kwh_storage_per_kwp),
            "kwp_per_connection": _stats(g.kwp_per_connection),
            "n_sites": int(len(g)),
        }
    overall = {
        "usd_per_kwp": _stats(use.usd_per_kwp),
        "usd_per_kwh_storage": _stats(use.usd_per_kwh_storage),
        "usd_per_connection": _stats(use.usd_per_connection),
    }

    model, frozen = load_frozen()
    demo = DEMO_SITES.copy()
    feats = build_features(demo, name="demo_sites")
    maji = demo[demo.site_id == "demo_maji_moto"].iloc[0]
    f = feats[feats.site_id == "demo_maji_moto"].iloc[0].to_dict()
    est18 = model.estimate(f, maji.country)
    m24 = float(observed_multiplier(24, frozen["growth_slope"], ref=18))
    p50_24 = est18.p50 * m24
    p90_24 = est18.p90 * m24
    p10_24 = est18.p10 * m24
    n_hh = 100
    kwh_per_kwp_month = KWH_PER_KWP_DAY * DAYS * PERF
    ke = by["Kenya"]
    usd_kwp = ke["usd_per_kwp"]["median"]
    usd_batt = ke["usd_per_kwh_storage"]["median"]
    usd_conn = ke["usd_per_connection"]["median"]
    batt_ratio = ke["kwh_storage_per_kwp"]["median"]

    def size_at(kwh_cust: float) -> dict:
        site_kwh = n_hh * kwh_cust
        kwp = site_kwh / kwh_per_kwp_month
        batt = kwp * batt_ratio
        return {
            "kwh_cust_month": kwh_cust,
            "site_kwh_month": site_kwh,
            "kwp": kwp,
            "battery_kwh": batt,
            "cost_usd_from_kwp_and_storage": kwp * usd_kwp + batt * usd_batt,
            "cost_usd_from_per_connection": n_hh * usd_conn,
        }

    payload = {
        "source": "Renewvia minigridprojects + customers (meterRole=Customer Meter). Zenodo 10.5281/zenodo.22149101, CC BY-SA 4.0.",
        "capex_unit": (
            "Treated as USD. Dictionary says local currency; values and Renewvia's "
            "own kUSD carbon chart only make sense as USD (Kalobeyei Settlement "
            "541 kWp at 967,872 KES would be ~$7k)."
        ),
        "dropped_from_unit_costs": dropped,
        "overall": overall,
        "by_country": by,
        "sites": use[["projectName", "country", "sizePv", "sizeBattery", "capex",
                      "n_customer_meters", "usd_per_kwp", "usd_per_kwh_storage",
                      "usd_per_connection"]].to_dict(orient="records"),
        "maji_moto": {
            "households": n_hh,
            "country": "KE",
            "features": {"bld_count": f.get("bld_count"), "grid_dist_km": f.get("grid_dist_km")},
            "frozen_p10_p50_p90_month18": [est18.p10, est18.p50, est18.p90],
            "frozen_p10_p50_p90_month24": [p10_24, p50_24, p90_24],
            "drivers": [{"name": n, "multiplier": m, "reason": r} for n, m, r in est18.drivers],
            "pv_yield_assumption": (
                f"{KWH_PER_KWP_DAY} kWh/kWp/day × {DAYS} days × {PERF} performance "
                f"= {kwh_per_kwp_month:.1f} kWh/kWp/month (NREL PVWatts-class, documented)"
            ),
            "kenya_unit_costs_used": {
                "usd_per_kwp_median": usd_kwp,
                "usd_per_kwh_storage_median": usd_batt,
                "usd_per_connection_median": usd_conn,
                "kwh_storage_per_kwp_median": batt_ratio,
            },
            "size_p50": size_at(p50_24),
            "size_p90": size_at(p90_24),
        },
    }
    path = OUT / "cost_estimate.json"
    path.write_text(json.dumps(payload, indent=2, default=float), encoding="utf-8")
    print("Kenya median USD/kWp", round(usd_kwp), "USD/kWh-storage", round(usd_batt),
          "USD/connection", round(usd_conn))
    print("Nigeria median USD/kWp", round(by["Nigeria"]["usd_per_kwp"]["median"]),
          "USD/connection", round(by["Nigeria"]["usd_per_connection"]["median"]))
    print("Maji Moto P50@24", round(p50_24, 2), "P90@24", round(p90_24, 2))
    print("size P50 kWp", round(payload["maji_moto"]["size_p50"]["kwp"], 2),
          "cost_kwp+batt", round(payload["maji_moto"]["size_p50"]["cost_usd_from_kwp_and_storage"]),
          "cost_per_conn", round(payload["maji_moto"]["size_p50"]["cost_usd_from_per_connection"]))
    print("size P90 kWp", round(payload["maji_moto"]["size_p90"]["kwp"], 2),
          "cost_kwp+batt", round(payload["maji_moto"]["size_p90"]["cost_usd_from_kwp_and_storage"]))
    print("wrote", path)


if __name__ == "__main__":
    main()
