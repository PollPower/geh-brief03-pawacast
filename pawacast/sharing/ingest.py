"""Load shared records as a nearby-sites signal. Frozen β is never refit.

Nearby published means shift the day-one P50 in log space (spatial pooling).
Tier 2 records get half the weight of Tier 1. Growth observations are the
(months_since_power_on, mean) series from those records.

Source of demo records: Renewvia TRAIN (Zenodo 10.5281/zenodo.22149101, CC BY-SA 4.0).
"""
from __future__ import annotations

import json
import math
import pathlib

import h3
import numpy as np

from pawacast.model.growth import observed_multiplier
from pawacast.model.prior import Estimate, Z90
from pawacast.sharing.validate import H3_RES, validate_records

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_RECORDS = ROOT / "results" / "sharing_records.json"
TIER_WEIGHT = {1: 1.0, 2: 0.5}
PRIOR_PSEUDO_SITES = 4.0
MATURE_LO, MATURE_HI = 12, 24


def load_records(path: pathlib.Path | None = None) -> list[dict]:
    p = pathlib.Path(path) if path else DEFAULT_RECORDS
    raw = json.loads(p.read_text(encoding="utf-8"))
    return validate_records(raw)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def nearby_records(
    records: list[dict],
    lat: float,
    lon: float,
    *,
    radius_km: float | None = 80.0,
    k_ring: int | None = None,
) -> list[dict]:
    """Records whose H3 cell centre is within radius_km, or in an H3 k-ring.

    Maji Moto vs Olkiramatian is ~70 km, so the sprint demo uses radius_km=80
    (not a single res-6 cell). That choice is labelled DEMO.
    """
    if k_ring is not None:
        origin = h3.latlng_to_cell(float(lat), float(lon), H3_RES)
        disk = set(h3.grid_disk(origin, int(k_ring)))
        return [r for r in records if r["h3_res6"] in disk]
    if radius_km is None:
        raise ValueError("set radius_km or k_ring")
    out = []
    for r in records:
        clat, clon = h3.cell_to_latlng(r["h3_res6"])
        if haversine_km(lat, lon, clat, clon) <= radius_km:
            out.append(r)
    return out


def _site_weight(rec: dict) -> float:
    return TIER_WEIGHT.get(int(rec["tier"]), 0.5) * (int(rec["n_customers"]) / 50.0)


def blend_prior(est: Estimate, nearby: list[dict], sigma: float) -> dict:
    """Shift P50 toward nearby mature means. Do not change frozen β or σ."""
    mature = [
        r
        for r in nearby
        if MATURE_LO <= int(r["months_since_power_on"]) <= MATURE_HI
        and float(r["mean_kwh_cust"]) > 0
    ]
    w_prior = PRIOR_PSEUDO_SITES
    log_prior = math.log(est.p50)
    if not mature:
        return {
            "p10": est.p10,
            "p50": est.p50,
            "p90": est.p90,
            "n_nearby": 0,
            "n_mature": 0,
            "w_data": 0.0,
            "shift_ratio": 1.0,
            "cells": [],
            "tiers": [],
        }
    w_data = 0.0
    acc = 0.0
    for r in mature:
        w = _site_weight(r)
        w_data += w
        acc += w * math.log(float(r["mean_kwh_cust"]))
    log_p50 = (w_prior * log_prior + acc) / (w_prior + w_data)
    p50 = float(math.exp(log_p50))
    p10 = p50 * math.exp(-Z90 * sigma)
    p90 = p50 * math.exp(Z90 * sigma)
    cells = sorted({r["h3_res6"] for r in mature})
    tiers = sorted({int(r["tier"]) for r in mature})
    return {
        "p10": p10,
        "p50": p50,
        "p90": p90,
        "n_nearby": len(nearby),
        "n_mature": len(mature),
        "w_data": float(w_data),
        "w_prior": float(w_prior),
        "shift_ratio": p50 / est.p50,
        "cells": cells,
        "tiers": tiers,
        "mean_of_nearby": float(np.exp(acc / w_data)) if w_data else None,
    }


def growth_observations(nearby: list[dict]) -> list[dict]:
    """One point per record: month since power-on vs published mean."""
    rows = []
    for r in nearby:
        rows.append(
            {
                "h3_res6": r["h3_res6"],
                "month": r["month"],
                "months_since_power_on": int(r["months_since_power_on"]),
                "mean_kwh_cust": float(r["mean_kwh_cust"]),
                "n_customers": int(r["n_customers"]),
                "tier": int(r["tier"]),
            }
        )
    rows.sort(key=lambda d: (d["h3_res6"], d["months_since_power_on"]))
    return rows


def growth_multiplier_path(obs: list[dict], slope: float) -> list[dict]:
    """Normalise each H3 cell to its month-18 mean (or nearest mature month)."""
    by_cell: dict[str, list[dict]] = {}
    for r in obs:
        by_cell.setdefault(r["h3_res6"], []).append(r)
    out = []
    for cell, rows in by_cell.items():
        mature = [r for r in rows if MATURE_LO <= r["months_since_power_on"] <= MATURE_HI]
        if not mature:
            continue
        ref = min(mature, key=lambda r: abs(r["months_since_power_on"] - 18))
        ref_mean = ref["mean_kwh_cust"]
        if ref_mean <= 0:
            continue
        for r in rows:
            out.append(
                {
                    **r,
                    "ref_mean": ref_mean,
                    "multiplier": r["mean_kwh_cust"] / ref_mean,
                    "frozen_multiplier": float(
                        observed_multiplier(r["months_since_power_on"], slope)
                    ),
                }
            )
    return out
