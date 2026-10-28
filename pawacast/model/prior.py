"""Day-one demand range for an unmetered site: the PawaCast prior.

No open site-level metered data exists to train on, so this is a *calibrated structural*
model, not a fitted ML model:

  kWh/customer/month (mature, ~24 months after connection)
      = country baseline (AMDA benchmarks)
      x business-mix multiplier   (share of large buildings / business POIs)
      x prosperity multiplier     (mean building footprint)
      x activity multiplier       (VIIRS night lights)

Every multiplier is reported back, so a lender can see exactly why the number moved.
Uncertainty is lognormal; its width (SIGMA) reflects the spread between sites in AMDA's
benchmarks. The named published sites are kept for validation only and never used here.
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field
import numpy as np
import pandas as pd
from ..targets.public import AMDA, SEGMENTS, REGION

Z90 = 1.2816  # P10/P90 of a normal

# --- assumptions (documented; change here, not in code below) -----------------
SIGMA = 0.65             # lognormal sd between sites; AMDA East/Southern country spread 1.5-8 kWh
REF_LARGE_SHARE = 0.10   # typical share of footprints >= 100 m2 in a rural village
REF_MEAN_AREA = 55.0     # typical mean footprint, m2
AREA_ELASTICITY = 0.5    # +10% mean footprint -> ~+5% demand
NTL_ELASTICITY = 0.15    # per unit of log(1 + radiance)
MAX_BUSINESS_SHARE = 0.40

@dataclass
class Estimate:
    p10: float
    p50: float
    p90: float
    baseline: float
    drivers: list = field(default_factory=list)   # (name, multiplier, plain-language reason)

def country_baseline(country: str) -> tuple[float, str]:
    """Latest AMDA kWh/customer/month for the country, else its region."""
    c = AMDA[AMDA.area == country].sort_values("year")
    if len(c):
        r = c.iloc[-1]
        return float(r.kwh_cust_month), f"AMDA {country} {int(r.year)} average ({r.source})"
    reg = REGION.get(country, "EAST_SOUTH")
    r = AMDA[AMDA.area == reg].iloc[-1]
    return float(r.kwh_cust_month), f"AMDA {reg.replace('_', '/').title()} {int(r.year)} average"

def _business_share(f) -> float:
    n = max(f.get("bld_count", 0) or 0, 1)
    large = (f.get("bld_large_count", 0) or 0) / n
    poi_biz = sum((f.get(k, 0) or 0) for k in ("poi_commerce", "poi_food", "poi_services", "poi_productive"))
    share = 0.05 + 0.6 * large + 0.5 * poi_biz / n
    return float(min(max(share, 0.05), MAX_BUSINESS_SHARE))

def estimate(features: dict, country: str = "KE") -> Estimate:
    base, base_src = country_baseline(country)
    region = REGION.get(country, "EAST_SOUTH")
    seg = SEGMENTS[SEGMENTS.region == region].set_index("segment").kwh_cust_month
    drivers = [("Country baseline", 1.0, f"{base:.1f} kWh/customer/month — {base_src}")]

    # business mix, relative to a typical village
    b = _business_share(features)
    b_ref = 0.05 + 0.6 * REF_LARGE_SHARE
    mix = ((1 - b) * seg.residential + b * seg.commercial) / ((1 - b_ref) * seg.residential + b_ref * seg.commercial)
    drivers.append(("Business activity", mix,
                    f"estimated {b:.0%} of customers are businesses (typical {b_ref:.0%}), "
                    f"from {int(features.get('bld_large_count', 0) or 0)} large buildings and "
                    f"{int(features.get('poi_count', 0) or 0)} mapped businesses/services"))

    # prosperity: bigger homes use more
    area = features.get("bld_mean_area_m2") or REF_MEAN_AREA
    pros = (area / REF_MEAN_AREA) ** AREA_ELASTICITY
    drivers.append(("Building size", pros, f"mean footprint {area:.0f} m2 vs typical {REF_MEAN_AREA:.0f} m2"))

    # existing night-time activity (diesel, solar, partial grid)
    ntl = features.get("ntl_2024_5km") or 0.0
    act = math.exp(NTL_ELASTICITY * math.log1p(max(ntl, 0)))
    drivers.append(("Night-time lights", act,
                    "no measurable night lights (typical before power)" if ntl < 0.05
                    else f"night-light radiance {ntl:.2f} nW/cm2/sr within ~2.5 km"))

    p50 = base * mix * pros * act
    return Estimate(p10=p50 * math.exp(-Z90 * SIGMA), p50=p50, p90=p50 * math.exp(Z90 * SIGMA),
                    baseline=base, drivers=drivers)

def estimate_frame(feats: pd.DataFrame, country_col: str = "country") -> pd.DataFrame:
    rows = []
    for _, r in feats.iterrows():
        e = estimate(r.to_dict(), r.get(country_col, "KE"))
        rows.append({"site_id": r.site_id, "p10": e.p10, "p50": e.p50, "p90": e.p90, "baseline": e.baseline,
                     **{f"x_{n.lower().replace(' ', '_').replace('-', '_')}": m for n, m, _ in e.drivers[1:]}})
    return pd.DataFrame(rows)
