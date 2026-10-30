"""Per-customer monthly totals → public shared record.

TRAIN Renewvia sites only. Test-site consumption is never opened (iter_build_jobs
with the final-eval flag off). Published statistics get Laplace noise; ε is in
the record. Compact proves the exact sum and count; the published mean is that
sum/count after noise and rounding.

Source: Renewvia (Zenodo 10.5281/zenodo.22149101, CC BY-SA 4.0).
"""
from __future__ import annotations

import hashlib
import json
import pathlib

import numpy as np
import pandas as pd

from pawacast.targets.public import DAYS_PER_MONTH
from pawacast.targets.renewvia import (
    MIN_DAYS,
    HeldOutError,
    SiteJob,
    iter_build_jobs,
    load_meter_months,
    site_id_of,
    tariff_class,
)

from .validate import (
    EPSILON_PERIOD,
    MIN_CUSTOMERS,
    h3_res6,
    round_business_share,
    round_n_customers,
    validate_record,
)

ROOT = pathlib.Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT / "data" / "targets" / "_share_cust_months"
DEFAULT_EPSILON = 1.0
KWH_CLIP = 20.0
TIER2_RENEWVIA_LABEL = (
    "Tier 2 demo built from Renewvia open data (CC BY-SA 4.0)"
)
KWH_KEYS = ("mean_kwh_cust", "p10_kwh_cust", "p50_kwh_cust", "p90_kwh_cust")


def _seed(site_id: str, month: str) -> int:
    h = hashlib.sha256(f"{site_id}|{month}".encode("utf-8")).hexdigest()
    return int(h[:8], 16)


def laplace_scale_mean(n: int, clip: float = KWH_CLIP, epsilon: float = DEFAULT_EPSILON) -> float:
    """Global sensitivity of the clipped mean is clip/n; Laplace scale is Δ/ε."""
    if n < 1 or epsilon <= 0:
        raise ValueError("n and epsilon must be positive")
    return (clip / n) / epsilon


def noise_table(
    ns: tuple[int, ...] = (10, 25, 50, 200),
    typical_mean: float = 5.0,
    clip: float = KWH_CLIP,
    epsilon: float = DEFAULT_EPSILON,
) -> list[dict]:
    """How far Laplace noise typically moves the published mean, by site size."""
    rows = []
    for n in ns:
        scale = laplace_scale_mean(n, clip=clip, epsilon=epsilon)
        # E[|Laplace(0, b)|] = b; sd = b * sqrt(2)
        rows.append(
            {
                "n_customers": n,
                "epsilon": epsilon,
                "kwh_clip": clip,
                "laplace_scale": round(scale, 4),
                "typical_abs_noise_kwh": round(scale, 4),
                "typical_mean_kwh": typical_mean,
                "typical_abs_noise_over_mean": round(scale / typical_mean, 3),
            }
        )
    return rows


def _active_customers(mm: pd.DataFrame, days: pd.DataFrame) -> pd.DataFrame:
    if mm.empty:
        return pd.DataFrame()
    mm = mm.copy()
    mm["month_start"] = pd.to_datetime(mm["month_start"]).dt.normalize()
    active = mm[mm.n_observed_slots >= 1].copy()
    if active.empty:
        return active
    active = active[(active.n_days >= 1) & (active.n_days_observed >= 1)]
    active["kwh_cust_month"] = (active.kwh / active.n_days) * DAYS_PER_MONTH
    active["tariff_class"] = active.tariff.map(tariff_class)
    if days.empty:
        obs_map: dict[pd.Timestamp, int] = {}
    else:
        d = days.copy()
        d["month_start"] = pd.to_datetime(d["month_start"]).dt.normalize()
        obs_map = {
            pd.Timestamp(k): int(v)
            for k, v in (
                d.loc[d.has_observed.astype(bool)]
                .groupby("month_start")["local_date"]
                .nunique()
                .items()
            )
        }
    active["days_covered"] = active.month_start.map(
        lambda m: int(obs_map.get(pd.Timestamp(m), 0))
    )
    return active


def publish_from_customers(
    kwh: np.ndarray,
    is_business: np.ndarray,
    *,
    lat: float,
    lon: float,
    month: str,
    months_since_power_on: int,
    site_id: str,
    epsilon: float = DEFAULT_EPSILON,
    clip: float = KWH_CLIP,
    tier: int = 2,
    label: str = TIER2_RENEWVIA_LABEL,
) -> dict:
    """k-anonymity, clip, Laplace noise, rounding. Raises if true n < 25."""
    kwh = np.asarray(kwh, dtype=float)
    is_business = np.asarray(is_business, dtype=bool)
    n_true = int(kwh.size)
    if n_true < MIN_CUSTOMERS:
        raise ValueError(f"n={n_true} < {MIN_CUSTOMERS}; record not published")
    if is_business.size != n_true:
        raise ValueError("is_business length must match kwh")

    clipped = np.clip(kwh, 0.0, clip)
    n_pub = round_n_customers(n_true)
    if n_pub < MIN_CUSTOMERS:
        raise ValueError(f"rounded n={n_pub} < {MIN_CUSTOMERS}; record not published")

    mean = float(clipped.mean())
    p10, p50, p90 = (float(x) for x in np.percentile(clipped, [10, 50, 90]))
    share = float(is_business.mean())
    scale = laplace_scale_mean(n_true, clip=clip, epsilon=epsilon)
    share_scale = (1.0 / n_true) / epsilon
    rng = np.random.default_rng(_seed(site_id, month))

    mean_n = max(0.0, mean + float(rng.laplace(0.0, scale)))
    pct = sorted(
        max(0.0, v + float(rng.laplace(0.0, scale)))
        for v in (p10, p50, p90)
    )
    share_n = round_business_share(share + float(rng.laplace(0.0, share_scale)))

    rec = {
        "h3_res6": h3_res6(lat, lon),
        "month": month,
        "months_since_power_on": int(months_since_power_on),
        "n_customers": int(n_pub),
        "mean_kwh_cust": round(mean_n, 2),
        "p10_kwh_cust": round(pct[0], 2),
        "p50_kwh_cust": round(pct[1], 2),
        "p90_kwh_cust": round(pct[2], 2),
        "business_share": share_n,
        "tier": int(tier),
        "proof_ref": f"demo-no-proof:train:{site_id}:{month}",
        "epsilon": float(epsilon),
        "epsilon_period": EPSILON_PERIOD,
        "yearly_epsilon_budget": float(12.0 * epsilon),
        "kwh_clip": float(clip),
        "label": label,
    }
    return validate_record(rec)


def _job_cache_path(job: SiteJob) -> pathlib.Path:
    return CACHE_DIR / f"{site_id_of(job.project_name)}.parquet"


def _load_or_build_active(job: SiteJob, refresh: bool = False) -> pd.DataFrame:
    if job.role == "test":
        raise HeldOutError(f"sharing aggregator refuses test site {job.project_name}")
    path = _job_cache_path(job)
    if path.exists() and not refresh:
        return pd.read_parquet(path)
    mm, days, _n = load_meter_months(job)
    active = _active_customers(mm, days)
    if active.empty:
        return active
    keep = [
        "meter_customer_code",
        "month_start",
        "kwh_cust_month",
        "tariff_class",
        "days_covered",
        "n_observed_slots",
    ]
    active = active[keep]
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    active.to_parquet(path, index=False)
    return active


def records_from_job(job: SiteJob, refresh: bool = False) -> list[dict]:
    if job.role == "test":
        raise HeldOutError(f"sharing aggregator refuses test site {job.project_name}")
    active = _load_or_build_active(job, refresh=refresh)
    if active.empty:
        return []
    site_id = site_id_of(job.project_name)
    po = pd.Timestamp(job.power_on)
    out: list[dict] = []
    for month_start, g in active.groupby("month_start"):
        n_active = int(len(g))
        dc = int(g.days_covered.iloc[0]) if len(g) else 0
        if n_active < MIN_CUSTOMERS or dc < MIN_DAYS:
            continue
        ms = pd.Timestamp(month_start)
        months_since = (ms.year - po.year) * 12 + (ms.month - po.month)
        if months_since < 0:
            continue
        month = ms.strftime("%Y-%m")
        rec = publish_from_customers(
            g.kwh_cust_month.to_numpy(),
            (g.tariff_class == "commercial").to_numpy(),
            lat=job.lat,
            lon=job.lon,
            month=month,
            months_since_power_on=int(months_since),
            site_id=site_id,
        )
        out.append(rec)
    return out


def build_train_records(refresh: bool = False) -> list[dict]:
    """Published records for every TRAIN Renewvia site-month that passes k ≥ 25."""
    records: list[dict] = []
    for job in iter_build_jobs(final_eval=False):
        if job.role == "test":
            raise HeldOutError("iter_build_jobs listed a test site with flag off")
        recs = records_from_job(job, refresh=refresh)
        print(f"  share {job.project_name}: {len(recs)} records", flush=True)
        records.extend(recs)
    records.sort(key=lambda r: (r["h3_res6"], r["month"]))
    return records


def write_records(records: list[dict], path: pathlib.Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(records, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
