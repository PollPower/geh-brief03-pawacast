"""Meter-update v2: predictive sigma includes AR(1) monthly noise and projection error.

Calibrated on TRAIN site-months only. Does not change the frozen day-one model.
OBS_SIGMA = 0.30 in update.py is left as the frozen (overconfident) update.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .growth import observed_multiplier
from .loglinear import REF_MONTH
from .prior import Z90

KS = (1, 3, 6)


def y_at_18(month: float, kwh: float, slope: float) -> float:
    m = max(float(month), 0.0)
    return math.log(float(kwh)) - math.log(float(observed_multiplier(m, slope, ref=REF_MONTH)))


def ar1_mean_var(sig2: float, rho: float, k: int) -> float:
    """Variance of the mean of k consecutive AR(1) months."""
    k = int(k)
    if k <= 1:
        return float(sig2)
    s = 1.0
    for j in range(1, k):
        s += 2.0 * (1.0 - j / k) * (rho ** j)
    return float(sig2) / k * s


def estimate_noise(sm: pd.DataFrame, slope: float) -> dict:
    """(a) within-site month-to-month sd and lag-1 autocorrelation. TRAIN only."""
    d = sm[sm.kwh_cust_month > 0].copy()
    d["y"] = [y_at_18(r.months_since_power_on, r.kwh_cust_month, slope) for r in d.itertuples()]
    resid = []
    pairs = []
    for _, g in d.groupby("projectName"):
        g = g.sort_values(["months_since_power_on", "month"])
        yy = g.y.to_numpy() - g.y.mean()
        mm = g.months_since_power_on.to_numpy()
        resid.extend(yy.tolist())
        for a, b, m0, m1 in zip(yy[:-1], yy[1:], mm[:-1], mm[1:]):
            if int(m1) - int(m0) == 1:
                pairs.append((float(a), float(b)))
    resid = np.asarray(resid, dtype=float)
    sigma_month = float(resid.std(ddof=1))
    if len(pairs) >= 10:
        a, b = np.array(pairs).T
        rho = float(np.corrcoef(a, b)[0, 1])
    else:
        rho = 0.0
    return {
        "sigma_month": sigma_month,
        "rho": rho,
        "n_resid": int(len(resid)),
        "n_lag1": int(len(pairs)),
    }


def estimate_projection(sm: pd.DataFrame, targets: pd.DataFrame, slope: float, noise: dict) -> dict:
    """(b) extra error of first-k mean vs months 12–24, beyond AR(1) sampling. TRAIN only."""
    sig2 = noise["sigma_month"] ** 2
    rho = noise["rho"]
    out = {}
    for k in KS:
        errs = []
        for _, t in targets.iterrows():
            g = sm[sm.projectName == t.site].sort_values("month").head(int(k))
            g = g[g.kwh_cust_month > 0]
            if len(g) < k:
                continue
            ybar = float(np.mean([
                y_at_18(r.months_since_power_on, r.kwh_cust_month, slope) for r in g.itertuples()
            ]))
            errs.append(ybar - math.log(float(t.actual)))
        e = np.asarray(errs, dtype=float)
        emp_sd = float(e.std(ddof=1))
        v_ar1 = ar1_mean_var(sig2, rho, k)
        tau2 = max(0.0, emp_sd ** 2 - v_ar1)
        out[str(k)] = {
            "n": int(len(e)),
            "mean_log_error": float(e.mean()),
            "emp_sd": emp_sd,
            "var_ar1_mean": float(v_ar1),
            "tau_proj2": tau2,
            "sigma_like": float(math.sqrt(v_ar1 + tau2)),
        }
    return out


def sigma_like(k: int, cal: dict) -> float:
    k = max(int(k), 1)
    key = str(k)
    if key in cal["projection"]:
        return float(cal["projection"][key]["sigma_like"])
    # interpolate / nearest for other k (app readings)
    sig2 = cal["noise"]["sigma_month"] ** 2
    rho = cal["noise"]["rho"]
    v_ar1 = ar1_mean_var(sig2, rho, k)
    # use tau from nearest calibrated k
    nearest = min(KS, key=lambda t: abs(t - k))
    tau2 = cal["projection"][str(nearest)]["tau_proj2"]
    return float(math.sqrt(v_ar1 + tau2))


def update_v2(p50_prior: float, readings: list[tuple[float, float]], cal: dict,
              sigma_prior: float, slope: float) -> dict:
    """Posterior at month 18. Predictive sd = scale * sqrt(posterior var)."""
    mu0 = math.log(float(p50_prior))
    v0 = float(sigma_prior) ** 2
    scale = float(cal.get("scale", 1.0))
    if not readings:
        s = float(sigma_prior)
        return {
            "p10": math.exp(mu0 - Z90 * s),
            "p50": math.exp(mu0),
            "p90": math.exp(mu0 + Z90 * s),
            "sigma": s,
            "n_readings": 0,
            "sigma_like": None,
            "ybar": None,
        }
    ys = [y_at_18(m, kwh, slope) for m, kwh in readings]
    ybar = float(np.mean(ys))
    sl = sigma_like(len(readings), cal)
    v = 1.0 / (1.0 / v0 + 1.0 / sl ** 2)
    mu = v * (mu0 / v0 + ybar / sl ** 2)
    s = scale * math.sqrt(v)
    return {
        "p10": math.exp(mu - Z90 * s),
        "p50": math.exp(mu),
        "p90": math.exp(mu + Z90 * s),
        "sigma": s,
        "n_readings": len(readings),
        "sigma_like": sl,
        "ybar": ybar,
        "posterior_sd_unscaled": math.sqrt(v),
    }


def choose_scale(rows: pd.DataFrame, target: float = 0.80) -> float:
    """One TRAIN-LOGO scale so |z| coverage at k=1,3,6 is about `target`."""
    g = rows[(rows.group == "TRAIN-LOGO") & (rows.k.isin(KS))]
    z = np.abs(g.z_unscaled.to_numpy(float))
    z = z[np.isfinite(z)]
    if len(z) < 5:
        return 1.0
    p = float(np.quantile(z, target))
    return float(p / Z90)
