"""Meters correct: how the range narrows as monthly readings arrive.

LABELLED SIMULATION. The published sites report one annual average, not monthly
readings, so the monthly readings here are SIMULATED around each site's measured
annual average (log-normal noise, sd = OBS_SIGMA). The point is to show the mechanism,
not to claim measured monthly data.
"""
from __future__ import annotations
import json, pathlib
import numpy as np
import pandas as pd
from .model.update import update, OBS_SIGMA
from .model.growth import G_MEDIAN, ANCHOR_MONTH

OUT = pathlib.Path(__file__).resolve().parents[1] / "results"

def run(seed=7):
    v = pd.read_csv(OUT / "validation_named_sites.csv")
    s = pd.read_parquet(OUT.parent / "data" / "features" / "named_sites.parquet")  # noqa: F841 (features cached)
    from .targets.public import named_sites
    meta = named_sites().set_index("site")
    rng = np.random.default_rng(seed)
    rows = []
    for _, r in v.iterrows():
        m0 = meta.loc[r.site, "months_since_connection"]
        # prior p50 at anchor month, recovered from the month-adjusted p50
        p50_anchor = r.p50 / (1 + G_MEDIAN) ** ((m0 - ANCHOR_MONTH) / 12)
        for n in (0, 1, 3, 6, 12):
            months = [m0 - 6 + i for i in range(n)]
            reads = [(m, r.actual * float(np.exp(rng.normal(0, OBS_SIGMA)))) for m in months]   # SIMULATED
            u = update(p50_anchor, reads)
            k = (1 + G_MEDIAN) ** ((m0 - ANCHOR_MONTH) / 12)
            rows.append({"site": r.site, "months_of_readings": n, "actual": r.actual,
                         "p10": u["p10"] * k, "p50": u["p50"] * k, "p90": u["p90"] * k,
                         "ape": abs(u["p50"] * k - r.actual) / r.actual, "range_width_vs_prior": u["width_ratio"]})
    df = pd.DataFrame(rows)
    summ = df.groupby("months_of_readings").agg(median_ape=("ape", "median"),
                                                width_vs_prior=("range_width_vs_prior", "median")).reset_index()
    df.to_csv(OUT / "meter_update_simulated.csv", index=False)
    (OUT / "meter_update_summary.json").write_text(json.dumps(
        {"label": "SIMULATED monthly readings around measured annual averages",
         "by_months": summ.to_dict(orient="records")}, indent=2))
    return df, summ

if __name__ == "__main__":
    df, summ = run()
    print(summ.round(3).to_string(index=False))
