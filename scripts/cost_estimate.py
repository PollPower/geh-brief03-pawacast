"""USD unit costs from Renewvia minigridprojects capex. No consumption files.

capex is labelled local currency in the data dictionary, but magnitudes match USD
(Kalobeyei Settlement 541 kWp at 967,872 would be ~$7k if KES). Renewvia's own
carbon figure treats capex as USD (kUSD). We follow that. Kakuma capex=0 and
Emakalakala's 648 kWh / 13.5 kWp battery outlier are dropped from unit-cost stats.

Source: Renewvia (Zenodo 10.5281/zenodo.22149101, CC BY-SA 4.0).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from pawacast.features import build_features
from pawacast.model.growth import observed_multiplier
from pawacast.model.loglinear import load_frozen
from pawacast.targets.demo import DEMO_SITES

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
    kwp_per_conn = ke["kwp_per_connection"]["median"]

    def size_at(kwh_cust: float, label: str) -> dict:
        site_kwh_month = n_hh * kwh_cust
        daily_kwh = site_kwh_month / DAYS
        kwp = site_kwh_month / kwh_per_kwp_month
        batt_kwh = kwp * batt_ratio
        days_autonomy = batt_kwh / daily_kwh if daily_kwh else None
        cost_a = kwp * usd_kwp
        cost_b = n_hh * usd_conn
        # The previous $54k / $133k added (a) to battery×(capex/battery). Both
        # ratios already spend 100% of the same capex. Do not add them.
        double_count = kwp * usd_kwp + batt_kwh * usd_batt
        return {
            "label": label,
            "kwh_cust_month": kwh_cust,
            "households": n_hh,
            "site_kwh_month": site_kwh_month,
            "daily_kwh": daily_kwh,
            "a_generation_and_storage_sized_to_demand": {
                "kwp": kwp,
                "battery_kwh": batt_kwh,
                "days_of_autonomy": days_autonomy,
                "usd_per_kwp_all_in": usd_kwp,
                "cost_usd": cost_a,
                "arithmetic": (
                    f"{n_hh} × {kwh_cust:.4f} kWh/cust/mo = {site_kwh_month:.2f} kWh/mo; "
                    f"kWp = {site_kwh_month:.2f} / ({KWH_PER_KWP_DAY} × {DAYS} × {PERF}) "
                    f"= {site_kwh_month:.2f} / {kwh_per_kwp_month:.3f} = {kwp:.3f} kWp; "
                    f"battery = {kwp:.3f} × {batt_ratio:.3f} kWh/kWp = {batt_kwh:.2f} kWh "
                    f"({days_autonomy:.2f} days of daily {daily_kwh:.2f} kWh); "
                    f"cost (a) = {kwp:.3f} kWp × ${usd_kwp:,.2f}/kWp = ${cost_a:,.0f}. "
                    f"All-in $/kWp already includes PV, storage and distribution as built; "
                    f"do not add ${usd_batt:,.0f}/kWh-storage or ${usd_conn:,.0f}/connection."
                ),
            },
            "b_all_in_per_connection_from_actuals": {
                "usd_per_connection": usd_conn,
                "cost_usd": cost_b,
                "equivalent_kwp_if_built_like_median_ke": n_hh * kwp_per_conn,
                "arithmetic": (
                    f"cost (b) = {n_hh} × ${usd_conn:,.2f}/connection = ${cost_b:,.0f}. "
                    f"Median Kenya Renewvia site is {kwp_per_conn:.3f} kWp/customer, so "
                    f"100 connections would be {n_hh * kwp_per_conn:.1f} kWp; "
                    f"{n_hh * kwp_per_conn:.2f} × ${usd_kwp:,.2f}/kWp = "
                    f"${n_hh * kwp_per_conn * usd_kwp:,.0f}. Close to (b) ${cost_b:,.0f}; "
                    f"not identical because median(capex/n) ≠ median(kWp/n)×median(capex/kWp)."
                ),
            },
            "error_withdrawn": {
                "was_usd": double_count,
                "why": (
                    f"kWp × $/kWp + battery_kWh × (capex/sizeBattery) = "
                    f"{kwp:.3f}×{usd_kwp:.2f} + {batt_kwh:.2f}×{usd_batt:.2f} = "
                    f"${double_count:,.0f}. Both unit costs attribute 100% of capex, so "
                    f"this double-counts. Withdrawn."
                ),
            },
            "why_a_differs_from_b": (
                f"(a) sizes PV to PawaCast demand ({kwp:.2f} kWp). "
                f"(b) copies how Kenya Renewvia sites were actually built "
                f"({n_hh * kwp_per_conn:.1f} kWp for 100 connections). "
                f"Demand-sized (a) is smaller because AMDA/PawaCast Kenya use is "
                f"~{kwh_cust:.1f} kWh/customer/month."
            ),
        }

    size_p50 = size_at(p50_24, "P50")
    size_p90 = size_at(p90_24, "P90")

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
            "assumptions": {
                "kwh_per_kwp_day": KWH_PER_KWP_DAY,
                "days_per_month": DAYS,
                "pv_performance_ratio": PERF,
                "kwh_per_kwp_month": kwh_per_kwp_month,
                "kwh_per_kwp_day_source": (
                    "4.5 kWh/kWp/day is an NREL PVWatts-class Kenya equatorial figure, "
                    "documented here, not fitted. 0.85 performance is inverter/soiling/"
                    "availability, also documented, not fitted."
                ),
                "battery_days_of_autonomy": (
                    "Not chosen as a free parameter. Storage is sized at the Kenya median "
                    f"{batt_ratio:.2f} kWh-battery per kWp (Renewvia sizeBattery/sizePv). "
                    "Implied days of autonomy = that battery / (site daily kWh)."
                ),
                "distribution_cost_per_connection": (
                    "Renewvia capex is all-in (generation + storage + distribution + "
                    "other). We cannot isolate distribution. Median Kenya all-in is "
                    f"${usd_conn:,.0f}/connection and ${usd_kwp:,.0f}/kWp; those are two "
                    "views of the same capex, not additive line items. No separate "
                    "distribution add-on is applied."
                ),
                "unit_cost_warning": (
                    "usd_per_kwp, usd_per_kwh_storage and usd_per_connection each divide "
                    "the SAME capex by a different denominator. Never add them."
                ),
            },
            "kenya_unit_costs_used": {
                "usd_per_kwp_median_all_in": usd_kwp,
                "usd_per_kwh_storage_median_all_in_do_not_add": usd_batt,
                "usd_per_connection_median_all_in": usd_conn,
                "kwh_storage_per_kwp_median": batt_ratio,
                "kwp_per_connection_median": kwp_per_conn,
            },
            "size_p50": size_p50,
            "size_p90": size_p90,
            "headline": {
                "p50_a_demand_sized_usd": size_p50["a_generation_and_storage_sized_to_demand"]["cost_usd"],
                "p90_a_demand_sized_usd": size_p90["a_generation_and_storage_sized_to_demand"]["cost_usd"],
                "p50_and_p90_b_all_in_per_connection_usd": size_p50["b_all_in_per_connection_from_actuals"]["cost_usd"],
                "withdrawn": "P50 $54k and P90 $133k (kWp×$/kWp + battery×$/kWh-storage double-count)",
            },
        },
    }
    path = OUT / "cost_estimate.json"
    path.write_text(json.dumps(payload, indent=2, default=float), encoding="utf-8")
    a50 = size_p50["a_generation_and_storage_sized_to_demand"]
    a90 = size_p90["a_generation_and_storage_sized_to_demand"]
    b50 = size_p50["b_all_in_per_connection_from_actuals"]
    print("Kenya median USD/kWp", round(usd_kwp), "USD/connection", round(usd_conn))
    print("Maji Moto P50@24", round(p50_24, 2), "P90@24", round(p90_24, 2))
    print("(a) P50", round(a50["kwp"], 2), "kWp  $", round(a50["cost_usd"]))
    print("(a) P90", round(a90["kwp"], 2), "kWp  $", round(a90["cost_usd"]))
    print("(b) 100 × $/connection  $", round(b50["cost_usd"]))
    print("withdrawn double-count P50 $", round(size_p50["error_withdrawn"]["was_usd"]))
    print(a50["arithmetic"])
    print(b50["arithmetic"])
    print("wrote", path)


if __name__ == "__main__":
    main()
