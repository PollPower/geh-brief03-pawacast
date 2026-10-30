"""Nearby-record ingest shifts the prior; frozen β is not touched."""
from __future__ import annotations

from pawacast.model.prior import Estimate
from pawacast.sharing.ingest import blend_prior, haversine_km, nearby_records
from pawacast.sharing.validate import h3_res6


def test_olkiramatian_is_about_70km_from_maji_moto():
    d = haversine_km(-1.33866, 35.71253, -1.87170849, 36.150046876)
    assert 60 < d < 90


def test_radius_includes_olkiramatian_cell():
    olki = h3_res6(-1.87170849, 36.150046876)
    recs = [
        {
            "h3_res6": olki,
            "month": "2022-06",
            "months_since_power_on": 18,
            "n_customers": 50,
            "mean_kwh_cust": 8.0,
            "p10_kwh_cust": 2.0,
            "p50_kwh_cust": 7.0,
            "p90_kwh_cust": 16.0,
            "business_share": 0.2,
            "tier": 2,
            "proof_ref": "demo-no-proof:train:renewvia_olkiramatian:2022-06",
            "epsilon": 1.0,
        }
    ]
    near80 = nearby_records(recs, -1.33866, 35.71253, radius_km=80)
    near20 = nearby_records(recs, -1.33866, 35.71253, radius_km=20)
    assert len(near80) == 1
    assert near20 == []


def test_blend_shifts_p50_toward_nearby_mean():
    est = Estimate(p10=1.0, p50=4.0, p90=16.0, baseline=3.7, drivers=[])
    olki = h3_res6(-1.87170849, 36.150046876)
    nearby = [
        {
            "h3_res6": olki,
            "month": "2022-06",
            "months_since_power_on": 18,
            "n_customers": 50,
            "mean_kwh_cust": 8.0,
            "tier": 2,
        }
    ]
    out = blend_prior(est, nearby, sigma=0.6994248481546623)
    assert est.p50 < out["p50"] < 8.0
    assert out["n_mature"] == 1
    assert out["tiers"] == [2]


def test_empty_nearby_leaves_prior():
    est = Estimate(p10=1.0, p50=4.0, p90=16.0, baseline=3.7, drivers=[])
    out = blend_prior(est, [], sigma=0.7)
    assert out["p50"] == 4.0
    assert out["n_mature"] == 0
