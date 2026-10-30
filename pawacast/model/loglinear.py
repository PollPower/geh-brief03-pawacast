"""Sprint log-linear demand model. TRAIN sites only.

  log(kWh/customer/month) = log(AMDA country baseline)
                            + β_bld * log(building_count / 300)
                            + ε

AMDA offset is a prior, not a fitted dummy: a typical village (~300 buildings
within 1 km) returns the country baseline. β is ridge-shrunk toward 0 (λ = 2).
One fitted predictor (at most 3 allowed). Mean footprint, grid distance, POIs
and night lights are omitted: on TRAIN, footprint is collinear with country,
grid distance is confounded with the Turkana refugee settlements, and POI/NTL
are near zero. P10/P90 width is the leave-one-group-out residual spread (OOF sigma of
log(actual/P50)), not in-sample residuals and not the v0 SIGMA.

Source of consumption: Renewvia (Zenodo 10.5281/zenodo.22149101, CC BY-SA 4.0).
AMDA baselines: BAM 2022 Table 1 (KE 2020 = 3.7, NG 2020 = 11.0).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .prior import Estimate, country_baseline, Z90
from ..targets.public import REGION
from ..targets.renewvia import TEST_SITES, final_eval_enabled, load_site_months

ISO = {
    "Kenya": "KE", "Nigeria": "NG", "Ethiopia": "ET",
    "KE": "KE", "NG": "NG", "ET": "ET",
}
WINDOW_LO, WINDOW_HI = 12, 24
REF_MONTH = 18
REF_BLD = 300.0          # typical rural village, buildings within 1 km (documented, not fitted)
RIDGE_LAMBDA = 2.0       # prior β ~ 0; λ chosen a priori, not by the reporting CV
IMPUTATION_SITES = ("Emereoke", "Kalobeyei Settlement")
IMPUTATION_THRESHOLD = 0.15
# Decision (Block 2, after reading the clean-product spec): profile/uniform slots
# redistribute the meter's cumulative `energy` register across comms gaps; the
# total is conserved. observed_only undercounts. Use gap-filled kwh_cust_month
# for every TRAIN site. See EVAL_PLAN.md Deviations.
FEATURES_PATH = (
    __import__("pathlib").Path(__file__).resolve().parents[2] / "data" / "features" / "renewvia.parquet"
)


def iso_of(country: str) -> str:
    return ISO[country]


def imputation_check(sm: pd.DataFrame) -> pd.DataFrame:
    """Median |observed_only / gapfilled - 1| per site. TRAIN frame only."""
    rows = []
    for site, g in sm.groupby("projectName"):
        a, b = g.kwh_cust_month, g.kwh_cust_month_observed_only
        rel = (b - a) / a.replace(0, np.nan)
        w = g[g.months_since_power_on.between(WINDOW_LO, WINDOW_HI)]
        win_rel = np.nan
        if len(w):
            win_rel = float(w.kwh_cust_month_observed_only.median() / w.kwh_cust_month.median() - 1)
        rows.append(
            {
                "projectName": site,
                "n_months": int(len(g)),
                "median_rel": float(rel.median()),
                "median_abs_rel": float(rel.abs().median()),
                "window_rel": win_rel,
                "candidate": site in IMPUTATION_SITES,
                # Always False: imputed energy is conserved register consumption.
                "use_observed_only": False,
            }
        )
    return pd.DataFrame(rows).sort_values("median_abs_rel", ascending=False).reset_index(drop=True)


def apply_imputation(sm: pd.DataFrame, check: pd.DataFrame | None = None) -> tuple[pd.DataFrame, list[str]]:
    """Always keep gap-filled kWh. `check` is retained as a diagnostic."""
    if check is None:
        check = imputation_check(sm)
    out = sm.copy()
    out["kwh_used"] = out.kwh_cust_month
    return out, []


def site_level_targets(sm: pd.DataFrame, *, allow_test: bool = False) -> pd.DataFrame:
    """One row per site: median kWh in months 12–24, else earliest 12 months.

    Test sites are refused unless allow_test=True and PAWACAST_FINAL_EVAL=1.
    """
    if sm.empty:
        raise ValueError("no site-months")
    bad = set(sm.projectName) & set(TEST_SITES)
    if bad and not (allow_test and final_eval_enabled()):
        raise RuntimeError(f"test sites leaked into site-level targets: {bad}")
    rows = []
    for site, g in sm.groupby("projectName"):
        w = g[g.months_since_power_on.between(WINDOW_LO, WINDOW_HI)]
        flag = "window_12_24"
        if w.empty:
            w = g.sort_values("months_since_power_on").head(12)
            flag = "earliest_12"
        iso = iso_of(g.country.iloc[0])
        amda, amda_src = country_baseline(iso)
        rows.append(
            {
                "site_id": g.site_id.iloc[0],
                "projectName": site,
                "country": g.country.iloc[0],
                "iso": iso,
                "region": REGION[iso],
                "group": g.group.iloc[0],
                "lat": float(g.lat.iloc[0]),
                "lon": float(g.lon.iloc[0]),
                "n_window": int(len(w)),
                "target_flag": flag,
                "min_month": int(w.months_since_power_on.min()),
                "max_month": int(w.months_since_power_on.max()),
                "kwh": float(w.kwh_used.median()),
                "kwh_gapfilled": float(w.kwh_cust_month.median()),
                "kwh_observed_only": float(w.kwh_cust_month_observed_only.median()),
                "amda": amda,
                "amda_src": amda_src,
                "n_months_all": int(len(g)),
            }
        )
    return pd.DataFrame(rows).reset_index(drop=True)


def attach_features(sites: pd.DataFrame, features: pd.DataFrame | None = None) -> pd.DataFrame:
    if features is None:
        features = pd.read_parquet(FEATURES_PATH)
    keep = [
        "site_id", "bld_count", "bld_mean_area_m2", "bld_large_count",
        "poi_count", "ntl_2024_5km", "grid_dist_km",
    ]
    out = sites.merge(features[keep], on="site_id", how="left")
    out["x_log_bld"] = np.log(out.bld_count.clip(lower=1) / REF_BLD)
    return out


def load_train_sites() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list[str]]:
    """Site-level TRAIN table, full site-month series, imputation check. Never opens test."""
    sm = load_site_months(role="train")
    if (sm.role == "test").any() or set(sm.projectName) & set(TEST_SITES):
        raise RuntimeError("held-out test consumption leaked into TRAIN load")
    check = imputation_check(sm)
    sm, switched = apply_imputation(sm, check)
    sites = attach_features(site_level_targets(sm))
    if set(sites.projectName) & set(TEST_SITES):
        raise RuntimeError("test sites in site-level frame")
    return sites, sm, check, switched


def design_matrix(df: pd.DataFrame) -> np.ndarray:
    return df.x_log_bld.to_numpy(float).reshape(-1, 1)


def ridge_beta(X: np.ndarray, y: np.ndarray, lam: float = RIDGE_LAMBDA) -> np.ndarray:
    p = X.shape[1]
    return np.linalg.solve(X.T @ X + lam * np.eye(p), X.T @ y)


def calibrate_oof_interval(actual, p50) -> dict:
    """Interval from out-of-fold log(actual/P50). n=18: OOF sigma, not raw percentiles."""
    e = np.log(np.asarray(actual, dtype=float) / np.asarray(p50, dtype=float))
    q10, q90 = (float(x) for x in np.percentile(e, [10, 90]))
    sigma = float(np.std(e, ddof=1))
    return {
        "method": "oof_sigma",
        "sigma": sigma,
        "q10": q10,
        "q90": q90,
        "n": int(len(e)),
        "width_from_percentiles": float(math.exp(q90 - q10)),
        "width_from_sigma": float(math.exp(2 * Z90 * sigma)),
        "mean_log_resid": float(np.mean(e)),
        "reason": (
            "n=18 makes empirical P10/P90 jumpy (≈2nd order statistic); "
            "use sd of LOGO log(actual/P50) with Z90."
        ),
    }


def apply_oof_interval(p50, cal: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    p50 = np.asarray(p50, dtype=float)
    if cal["method"] == "oof_percentiles":
        return p50 * math.exp(cal["q10"]), p50, p50 * math.exp(cal["q90"])
    s = float(cal["sigma"])
    return p50 * math.exp(-Z90 * s), p50, p50 * math.exp(Z90 * s)


@dataclass
class LogLinearFit:
    beta: np.ndarray
    sigma: float
    lam: float = RIDGE_LAMBDA
    n_sites: int = 0
    interval_method: str = "oof_sigma"
    drivers_names: tuple = ("Mapped buildings",)

    def estimate(self, features: dict, country: str = "KE") -> Estimate:
        iso = iso_of(country)
        base, src = country_baseline(iso)
        bld = max(float(features.get("bld_count") or 1), 1.0)
        x_bld = math.log(bld / REF_BLD)
        xb = float(math.exp(self.beta[0] * x_bld))
        p50 = base * xb
        drivers = [
            ("Country baseline", 1.0, f"{base:.1f} kWh/customer/month — {src}"),
            ("Mapped buildings", xb,
             f"{int(bld)} buildings within 1 km vs a typical village of {int(REF_BLD)}"),
        ]
        return Estimate(
            p10=p50 * math.exp(-Z90 * self.sigma),
            p50=p50,
            p90=p50 * math.exp(Z90 * self.sigma),
            baseline=base,
            drivers=drivers,
        )

    def predict_frame(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        X = design_matrix(out)
        log_mu = np.log(out.amda.to_numpy(float)) + X @ self.beta
        out["p50"] = np.exp(log_mu)
        out["p10"] = out.p50 * math.exp(-Z90 * self.sigma)
        out["p90"] = out.p50 * math.exp(Z90 * self.sigma)
        out["x_mapped_buildings"] = np.exp(self.beta[0] * out.x_log_bld)
        return out


def fit(sites: pd.DataFrame, lam: float = RIDGE_LAMBDA, sigma: float | None = None,
        interval_method: str = "oof_sigma") -> LogLinearFit:
    X = design_matrix(sites)
    y = np.log(sites.kwh.to_numpy(float)) - np.log(sites.amda.to_numpy(float))
    beta = ridge_beta(X, y, lam)
    resid = y - X @ beta
    if sigma is None:
        sigma = float(np.std(resid, ddof=1)) if len(resid) > 2 else 0.65
    return LogLinearFit(
        beta=beta, sigma=float(sigma), lam=lam, n_sites=len(sites),
        interval_method=interval_method,
    )


def load_frozen(path=None) -> tuple[LogLinearFit, dict]:
    """Load coefficients from results/model_frozen.json. Does not refit."""
    import json
    import pathlib

    p = pathlib.Path(path) if path else (
        pathlib.Path(__file__).resolve().parents[2] / "results" / "model_frozen.json"
    )
    d = json.loads(p.read_text(encoding="utf-8"))
    model = LogLinearFit(
        beta=np.array([float(d["beta_bld"])], dtype=float),
        sigma=float(d["sigma"]),
        lam=float(d["ridge_lambda"]),
        interval_method=str(d["interval_method"]),
    )
    return model, d
