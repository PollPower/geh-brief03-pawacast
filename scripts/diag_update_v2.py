"""TRAIN-only diagnostics for meter-update v2. No R-test. No day-one refit."""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from pawacast.model.growth import observed_multiplier
from pawacast.model.loglinear import REF_MONTH, load_frozen
from pawacast.targets.renewvia import load_site_months

KS = (1, 3, 6)


def y18(m, kwh, slope):
    m = max(float(m), 0.0)
    return math.log(kwh) - math.log(float(observed_multiplier(m, slope, ref=REF_MONTH)))


def ar1_mean_var(sig2: float, rho: float, k: int) -> float:
    if k <= 1:
        return float(sig2)
    s = 1.0
    for j in range(1, k):
        s += 2.0 * (1.0 - j / k) * (rho ** j)
    return float(sig2 / k * s)


def main():
    _, frozen = load_frozen()
    slope = float(frozen["growth_slope"])
    sm = load_site_months(role="train")
    sm = sm[sm.kwh_cust_month > 0].copy()
    sm["y"] = [
        y18(r.months_since_power_on, r.kwh_cust_month, slope) for r in sm.itertuples()
    ]
    resid = []
    pairs = []
    for site, g in sm.groupby("projectName"):
        g = g.sort_values(["months_since_power_on", "month"])
        yy = g.y.to_numpy()
        mm = g.months_since_power_on.to_numpy()
        yy = yy - yy.mean()
        resid.extend(yy.tolist())
        for a, b, m0, m1 in zip(yy[:-1], yy[1:], mm[:-1], mm[1:]):
            if int(m1) - int(m0) == 1:
                pairs.append((a, b))
    resid = np.array(resid)
    sig = float(resid.std(ddof=1))
    if pairs:
        a, b = np.array(pairs).T
        rho = float(np.corrcoef(a, b)[0, 1])
    else:
        rho = 0.0
    print(f"n_resid={len(resid)}  sigma_month={sig:.4f}  n_lag1={len(pairs)}  rho={rho:.3f}")
    for k in KS:
        print(f"  AR1 var of mean k={k}: {ar1_mean_var(sig**2, rho, k):.4f}  sd={ar1_mean_var(sig**2, rho, k)**0.5:.3f}")

    targets = pd.read_csv("results/cv_train_sites.csv", encoding="utf-8")
    print("\nprojection error  ybar_k - log(actual 12-24)")
    for k in KS:
        errs = []
        for _, t in targets.iterrows():
            g = sm[sm.projectName == t.site].sort_values("month").head(k)
            if len(g) < k:
                continue
            ybar = float(np.mean([y18(r.months_since_power_on, r.kwh_cust_month, slope) for r in g.itertuples()]))
            errs.append(ybar - math.log(t.actual))
        e = np.array(errs)
        print(
            f"  k={k} n={len(e)} mean={e.mean():+.3f} sd={e.std(ddof=1):.3f} "
            f"mae={np.median(np.abs(e)):.3f}"
        )


if __name__ == "__main__":
    main()
