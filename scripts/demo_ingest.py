"""DEMO: Maji Moto prior + growth shifted by Olkiramatian-area shared records.

Does not refit frozen β. Labelled DEMO. Records are Tier 2 Renewvia TRAIN
(CC BY-SA 4.0), not simulated.
"""
from __future__ import annotations

import json
import math
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np

from pawacast.features import build_features
from pawacast.model.growth import observed_multiplier
from pawacast.model.loglinear import load_frozen
from pawacast.sharing.ingest import (
    blend_prior,
    growth_multiplier_path,
    growth_observations,
    haversine_km,
    load_records,
    nearby_records,
)
from pawacast.targets.demo import DEMO_SITES

OLKI = {"lat": -1.87170849, "lon": 36.150046876, "name": "Olkiramatian"}
OUT = ROOT / "results" / "sharing_ingest_demo.json"


def main() -> None:
    model, frozen = load_frozen()
    slope = float(frozen["growth_slope"])
    sigma = float(frozen["sigma"])
    maji = DEMO_SITES[DEMO_SITES.site_id == "demo_maji_moto"].iloc[0]
    feats = build_features(
        DEMO_SITES[DEMO_SITES.site_id == "demo_maji_moto"].copy(),
        name="demo_sites",
    ).iloc[0].to_dict()
    est = model.estimate(feats, maji.country)
    dist_km = haversine_km(maji.lat, maji.lon, OLKI["lat"], OLKI["lon"])
    radius_km = float(10 * math.ceil((dist_km + 1.0) / 10.0))
    records = load_records()
    nearby = nearby_records(records, maji.lat, maji.lon, radius_km=radius_km)
    blended = blend_prior(est, nearby, sigma)
    obs = growth_observations(nearby)
    path = growth_multiplier_path(obs, slope)
    k24 = float(observed_multiplier(24, slope))
    demo = {
        "label": "DEMO: Maji Moto prior shifted by Olkiramatian-area shared records",
        "note": (
            f"Olkiramatian is {dist_km:.1f} km from Maji Moto, so this demo uses "
            f"a {radius_km:.0f} km radius (not a single H3 res-6 cell). Frozen β "
            f"and σ are unchanged; only the P50 centre is blended in log space. "
            f"Tier 2 weight is 0.5. Compact proof is demo-no-proof."
        ),
        "site": {
            "name": maji["name"],
            "lat": float(maji.lat),
            "lon": float(maji.lon),
            "country": maji.country,
            "bld_count": feats.get("bld_count"),
        },
        "olkiramatian_distance_km": round(dist_km, 2),
        "radius_km": radius_km,
        "n_nearby_records": len(nearby),
        "n_nearby_cells": len({r["h3_res6"] for r in nearby}),
        "frozen_month18": {"p10": est.p10, "p50": est.p50, "p90": est.p90},
        "blended_month18": {
            "p10": blended["p10"],
            "p50": blended["p50"],
            "p90": blended["p90"],
            "shift_ratio": blended["shift_ratio"],
            "n_mature": blended["n_mature"],
            "w_data": blended["w_data"],
            "w_prior": blended.get("w_prior"),
            "mean_of_nearby": blended.get("mean_of_nearby"),
            "tiers": blended["tiers"],
        },
        "frozen_month24": {
            "p10": est.p10 * k24,
            "p50": est.p50 * k24,
            "p90": est.p90 * k24,
        },
        "blended_month24": {
            "p10": blended["p10"] * k24,
            "p50": blended["p50"] * k24,
            "p90": blended["p90"] * k24,
        },
        "growth_n_points": len(path),
        "growth_frozen_slope": slope,
        "growth_vs_frozen": {
            str(m): {
                "n": int(sum(1 for p in path if p["months_since_power_on"] == m)),
                "median_observed_multiplier": (
                    float(np.median([p["multiplier"] for p in path if p["months_since_power_on"] == m]))
                    if any(p["months_since_power_on"] == m for p in path)
                    else None
                ),
                "frozen_multiplier": float(observed_multiplier(m, slope)),
            }
            for m in (6, 12, 18, 24)
        },
    }
    OUT.write_text(
        json.dumps(demo, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(demo, indent=2), flush=True)
    print(f"wrote {OUT}", flush=True)


if __name__ == "__main__":
    main()
