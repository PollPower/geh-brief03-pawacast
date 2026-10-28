"""Demand growth after connection: a range, not a line.

Published observations of annual growth in kWh/customer (targets.public.GROWTH):
  8% (Kenya, 8 sites), ~47% (Ethiopia, Tum), ~21% (Tanzania high users).
We model growth as a lognormal annual rate with median ~18% and the published values
inside its P10-P90, and scale the mature (month-24) estimate back to month 0.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

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
