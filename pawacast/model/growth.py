"""Demand growth after connection: a range, not a line.

Published observations of annual growth in kWh/customer (targets.public.GROWTH):
  8% (Kenya, 8 sites), ~47% (Ethiopia, Tum), ~21% (Tanzania high users).
We model growth as a lognormal annual rate with median ~18% and the published values
inside its P10-P90, and scale the mature (month-24) estimate back to month 0.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from .prior import Z90

G_MEDIAN = 0.18
G_SIGMA = 0.6          # lognormal sd of the growth rate itself: P10 ~8%, P90 ~39%
ANCHOR_MONTH = 24      # the prior estimates demand at ~24 months (AMDA sites are mostly mature)

def demand_at(month, level_at_anchor, g):
    return level_at_anchor * (1 + g) ** ((np.asarray(month) - ANCHOR_MONTH) / 12)

def growth_curve(p50_anchor: float, sigma_level: float, months=range(0, 25), n=4000, seed=0) -> pd.DataFrame:
    """Monte Carlo over level and growth-rate uncertainty -> P10/P50/P90 per month."""
    rng = np.random.default_rng(seed)
    level = p50_anchor * np.exp(rng.normal(0, sigma_level, n))
    g = G_MEDIAN * np.exp(rng.normal(0, G_SIGMA, n))
    m = np.array(list(months))
    sims = level[:, None] * (1 + g[:, None]) ** ((m[None, :] - ANCHOR_MONTH) / 12)
    q = np.percentile(sims, [10, 50, 90], axis=0)
    return pd.DataFrame({"month": m, "p10": q[0], "p50": q[1], "p90": q[2]})

def to_month(p50_anchor: float, month: float) -> float:
    """Median estimate at a given month after connection."""
    return float(demand_at(month, p50_anchor, G_MEDIAN))


# --- observed growth on TRAIN site-months (site intercept + common log1p slope) ---
REF_MONTH = 18  # mid-point of the 12–24 month day-one window


def _x_month(months) -> np.ndarray:
    m = np.asarray(months, dtype=float)
    return np.log1p(m) - np.log1p(REF_MONTH)


def fit_observed_growth(site_months: pd.DataFrame, kwh_col: str = "kwh_used") -> dict:
    """Hierarchical log-linear growth: log(kWh) = a_site + b * (log1p(m) - log1p(18)).

    Within-site slope (common b), site intercepts as random effects. TRAIN only.
    """
    d = site_months[["site_id", "projectName", "months_since_power_on", kwh_col]].copy()
    d = d[d[kwh_col] > 0].dropna()
    d = d[d.months_since_power_on >= 0]
    d["x"] = _x_month(d.months_since_power_on)
    d["y"] = np.log(d[kwh_col])
    d["x_d"] = d.x - d.groupby("site_id").x.transform("mean")
    d["y_d"] = d.y - d.groupby("site_id").y.transform("mean")
    den = float((d.x_d ** 2).sum())
    slope = float((d.x_d * d.y_d).sum() / den) if den else 0.0
    d["a_hat"] = d.y - slope * d.x
    a_site = d.groupby("site_id").a_hat.mean()
    d["resid"] = d.y - (d.site_id.map(a_site) + slope * d.x)
    sigma_within = float(d.resid.std(ddof=1))
    tau_site = float(a_site.std(ddof=1)) if len(a_site) > 1 else 0.0
    # per-site slopes for a growth-rate band (sites with ≥12 months)
    site_slopes = []
    for _, g in d.groupby("site_id"):
        if len(g) < 12:
            continue
        xd, yd = g.x_d.to_numpy(), g.y_d.to_numpy()
        dd = float((xd ** 2).sum())
        if dd > 0:
            site_slopes.append(float((xd * yd).sum() / dd))
    site_slopes = np.array(site_slopes) if site_slopes else np.array([slope])
    g12_24 = math_annual(slope, 12, 24)
    g0_24 = math_annual(slope, 0, 24)
    g0_12 = math_annual(slope, 0, 12)
    return {
        "slope": slope,
        "intercept_log_at_18": float(a_site.median()),
        "sigma_within": sigma_within,
        "tau_site": tau_site,
        "n_sites": int(d.site_id.nunique()),
        "n_rows": int(len(d)),
        "site_slope_p10": float(np.percentile(site_slopes, 10)),
        "site_slope_p50": float(np.percentile(site_slopes, 50)),
        "site_slope_p90": float(np.percentile(site_slopes, 90)),
        "annual_0_12": g0_12,
        "annual_12_24": g12_24,
        "annual_0_24": g0_24,
        "a_site": a_site.to_dict(),
    }


def math_annual(slope: float, m0: float, m1: float) -> float:
    """Annualised growth implied by the log1p slope between two months."""
    years = (m1 - m0) / 12.0
    if years <= 0:
        return 0.0
    ratio = float(np.exp(slope * (_x_month(m1) - _x_month(m0))))
    return ratio ** (1.0 / years) - 1.0


def observed_multiplier(month, slope: float, ref: float = REF_MONTH) -> np.ndarray:
    return np.exp(slope * (np.log1p(np.asarray(month, dtype=float)) - np.log1p(ref)))


def observed_curve(fit: dict, months=range(0, 49)) -> pd.DataFrame:
    """kWh/customer/month curve for a typical site (median intercept) plus within-site band."""
    m = np.array(list(months), dtype=float)
    x = _x_month(m)
    log_p50 = fit["intercept_log_at_18"] + fit["slope"] * x
    band = Z90 * fit["sigma_within"]
    return pd.DataFrame({
        "month": m,
        "p10": np.exp(log_p50 - band),
        "p50": np.exp(log_p50),
        "p90": np.exp(log_p50 + band),
        "multiplier": np.exp(fit["slope"] * x),
    })
