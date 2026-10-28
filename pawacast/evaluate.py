"""Held-out validation against published measured sites (never used for fitting).

Compares the PawaCast range with three baselines:
  brief_midpoint : 20 kWh/customer/month (middle of the brief's 5-35 range)
  amda_country   : the country's AMDA average, no site features
  survey         : what the pre-connection household survey predicted (where published)
"""
from __future__ import annotations
import json, pathlib
import numpy as np
import pandas as pd
from .features import build_features
from .model.prior import estimate_frame, country_baseline
from .model.growth import to_month, ANCHOR_MONTH
from .targets.public import named_sites

OUT = pathlib.Path(__file__).resolve().parents[1] / "results"

def ape(pred, actual):
    return np.abs(pred - actual) / actual

def run(refresh=False) -> dict:
    # Pre-sprint: set A only. Set B must not be scored before the sprint (EVAL_PLAN.md).
    s = named_sites().query("eval_set == 'A'").dropna(subset=["lat"]).reset_index(drop=True)
    f = build_features(s, name="named_sites", refresh=refresh).merge(s[["site_id", "country"]], on="site_id")
    e = estimate_frame(f).merge(s, on="site_id")
    # move the mature (month-24) estimate to the month each site was measured
    k = e.apply(lambda r: to_month(1.0, r.months_since_connection) / to_month(1.0, ANCHOR_MONTH), axis=1)
    for c in ("p10", "p50", "p90"):
        e[c + "_t"] = e[c] * k
    e["amda_t"] = e.country.map(lambda c: country_baseline(c)[0]) * k
    a = e.kwh_cust_month
    res = pd.DataFrame({
        "site": e.site, "actual": a, "p10": e.p10_t, "p50": e.p50_t, "p90": e.p90_t,
        "inside": (a >= e.p10_t) & (a <= e.p90_t),
        "ape_pawacast": ape(e.p50_t, a), "ape_amda": ape(e.amda_t, a),
        "ape_brief20": ape(20.0, a), "ape_survey": ape(e.survey_kwh_cust_month, a),
        "geo_conf": e.geo_conf,
    })
    summary = {
        "n_sites": int(len(res)),
        "median_ape": {k: float(res[f"ape_{k}"].median()) for k in ("pawacast", "amda", "brief20", "survey")},
        "coverage_p10_p90": float(res.inside.mean()),
        "note": "Held-out published sites (Blodgett et al. 2017, Kenya). Not used to set any parameter.",
    }
    OUT.mkdir(exist_ok=True)
    res.to_csv(OUT / "validation_named_sites.csv", index=False)
    (OUT / "validation_summary.json").write_text(json.dumps(summary, indent=2))
    return {"table": res, "summary": summary}

if __name__ == "__main__":
    pd.set_option("display.width", 200)
    r = run()
    print(r["table"].round(2).to_string(index=False))
    print(json.dumps(r["summary"], indent=2))
