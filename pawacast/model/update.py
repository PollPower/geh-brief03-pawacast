"""Forecast first, meters correct: Bayesian update of a site's demand from meter readings.

Prior on the site's log demand level (at the anchor month): N(log p50, SIGMA^2).
Each metered month m gives log(kWh/cust) = level + growth(m) + noise, noise sd = OBS_SIGMA.
Conjugate normal update -> posterior P10/P50/P90. With PollPower meters every reading is
hardware-signed, so the update can be trusted by a lender without seeing customer data.
"""
from __future__ import annotations
import math
import numpy as np
from .growth import G_MEDIAN, ANCHOR_MONTH
from .prior import SIGMA, Z90

OBS_SIGMA = 0.30   # month-to-month variation of a site's mean kWh/customer (log scale)

def update(p50_prior: float, readings: list[tuple[float, float]], sigma_prior: float = SIGMA,
           g: float = G_MEDIAN) -> dict:
    """readings: [(month_since_connection, kWh_per_customer), ...]."""
    mu0, v0 = math.log(p50_prior), sigma_prior ** 2
    if not readings:
        mu, v = mu0, v0
    else:
        adj = [math.log(k) - ((m - ANCHOR_MONTH) / 12) * math.log1p(g) for m, k in readings]
        n, ybar = len(adj), float(np.mean(adj))
        v = 1 / (1 / v0 + n / OBS_SIGMA ** 2)
        mu = v * (mu0 / v0 + n * ybar / OBS_SIGMA ** 2)
    s = math.sqrt(v)
    return {"p10": math.exp(mu - Z90 * s), "p50": math.exp(mu), "p90": math.exp(mu + Z90 * s),
            "sigma": s, "n_readings": len(readings),
            "width_ratio": (math.exp(Z90 * s) - math.exp(-Z90 * s)) / (math.exp(Z90 * sigma_prior) - math.exp(-Z90 * sigma_prior))}
