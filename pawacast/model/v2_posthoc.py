"""Optional v2: country intercepts shrunk toward AMDA. Does not replace the headline.

Post-hoc — R-test has already been scored with the frozen model.
Fit and LOGO use TRAIN only. R-test is scored once afterwards and labelled
"post-hoc, test already seen".
"""
from __future__ import annotations

import json
import math
import pathlib

import numpy as np
import pandas as pd

from .loglinear import (
    RIDGE_LAMBDA,
    TEST_SITES,
    apply_imputation,
    apply_oof_interval,
    attach_features,
    calibrate_oof_interval,
    load_train_sites,
    ridge_beta,
    site_level_targets,
)
from .prior import Z90
from ..targets.renewvia import HeldOutError, final_eval_enabled, load_site_months

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "results"
COUNTRIES = ("KE", "NG")
NOTE = "post-hoc, test already seen"


def ape(pred, actual):
    return np.abs(pred - actual) / actual


def _metrics(p10, p50, p90, actual) -> dict:
    p10, p50, p90, actual = (np.asarray(x, dtype=float) for x in (p10, p50, p90, actual))
    inside = (actual >= p10) & (actual <= p90)
    return {
        "median_ape": float(np.median(ape(p50, actual))),
        "coverage_p10_p90": float(inside.mean()),
        "range_width": float(np.median(p90 / p10)),
        "bias": float(np.median(np.log(p50 / actual))),
        "n": int(len(actual)),
    }


def _py(x):
    if isinstance(x, dict):
        return {k: _py(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_py(v) for v in x]
    if isinstance(x, (np.floating, float)):
        return None if not math.isfinite(x) else float(x)
    if isinstance(x, (np.integer, int)):
        return int(x)
    if isinstance(x, (np.bool_, bool)):
        return bool(x)
    return x


def design_v2(df: pd.DataFrame) -> np.ndarray:
    dummies = np.column_stack([(df.iso.to_numpy() == c).astype(float) for c in COUNTRIES])
    x_bld = df.x_log_bld.to_numpy(float).reshape(-1, 1)
    return np.hstack([dummies, x_bld])


class V2Fit:
    def __init__(self, beta: np.ndarray, sigma: float, lam: float, n_sites: int):
        self.beta = np.asarray(beta, dtype=float)
        self.sigma = float(sigma)
        self.lam = float(lam)
        self.n_sites = int(n_sites)

    def predict_frame(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        X = design_v2(out)
        log_mu = np.log(out.amda.to_numpy(float)) + X @ self.beta
        out["p50"] = np.exp(log_mu)
        out["p10"] = out.p50 * math.exp(-Z90 * self.sigma)
        out["p90"] = out.p50 * math.exp(Z90 * self.sigma)
        out["x_country"] = np.exp(X[:, : len(COUNTRIES)] @ self.beta[: len(COUNTRIES)])
        out["x_mapped_buildings"] = np.exp(self.beta[-1] * out.x_log_bld)
        return out

    def coefs(self) -> dict:
        return {
            **{f"alpha_{c}": float(self.beta[i]) for i, c in enumerate(COUNTRIES)},
            "beta_bld": float(self.beta[-1]),
            "country_mult": {c: float(math.exp(self.beta[i])) for i, c in enumerate(COUNTRIES)},
        }


def fit_v2(sites: pd.DataFrame, lam: float = RIDGE_LAMBDA, sigma: float | None = None) -> V2Fit:
    X = design_v2(sites)
    y = np.log(sites.kwh.to_numpy(float)) - np.log(sites.amda.to_numpy(float))
    beta = ridge_beta(X, y, lam)
    resid = y - X @ beta
    if sigma is None:
        sigma = float(np.std(resid, ddof=1)) if len(resid) > 2 else 0.65
    return V2Fit(beta=beta, sigma=sigma, lam=lam, n_sites=len(sites))


def logo_v2(sites: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    rows = []
    for grp, held in sites.groupby("group"):
        model = fit_v2(sites[sites.group != grp])
        pred = model.predict_frame(held)
        for _, r in pred.iterrows():
            rows.append(
                {
                    "site": r.projectName,
                    "site_id": r.site_id,
                    "group": grp,
                    "country": r.iso,
                    "actual": float(r.kwh),
                    "p50": float(r.p50),
                    "ape": float(ape(r.p50, r.kwh)),
                    "x_country": float(r.x_country),
                    "x_mapped_buildings": float(r.x_mapped_buildings),
                }
            )
    cv = pd.DataFrame(rows).sort_values("site").reset_index(drop=True)
    cal = calibrate_oof_interval(cv.actual, cv.p50)
    p10, _, p90 = apply_oof_interval(cv.p50, cal)
    cv["p10"] = p10
    cv["p90"] = p90
    cv["inside"] = (cv.actual >= cv.p10) & (cv.actual <= cv.p90)
    return cv, cal


def load_r_test_sites() -> pd.DataFrame:
    sm = load_site_months(role="test")
    sm, _ = apply_imputation(sm)
    sites = attach_features(site_level_targets(sm, allow_test=True))
    extra = set(sites.projectName) - set(TEST_SITES)
    if extra:
        raise RuntimeError(f"non-test sites in R-test frame: {extra}")
    return sites


def _print(title: str, metrics: dict, sites: pd.DataFrame) -> None:
    print(f"\n{title}")
    print(
        f"  median APE {100 * metrics['median_ape']:.1f}%  "
        f"coverage {100 * metrics['coverage_p10_p90']:.0f}%  "
        f"width {metrics['range_width']:.2f}  "
        f"bias {metrics['bias']:+.2f}  n={metrics['n']}"
    )
    cols = ["site", "country", "actual", "p50", "p10", "p90", "inside", "ape"]
    print(sites[cols].round(3).to_string(index=False))


def run() -> dict:
    if not final_eval_enabled():
        raise HeldOutError("PAWACAST_FINAL_EVAL=1 is required to score R-test (post-hoc only)")
    train, _, _, _ = load_train_sites()
    if set(train.projectName) & set(TEST_SITES):
        raise RuntimeError("test sites in v2 TRAIN frame")
    cv, cal = logo_v2(train)
    full = fit_v2(train, sigma=cal["sigma"])
    rtest_sites = load_r_test_sites()
    rpred = full.predict_frame(rtest_sites)
    rtest = pd.DataFrame(
        {
            "site": rpred.projectName,
            "site_id": rpred.site_id,
            "country": rpred.iso,
            "actual": rpred.kwh,
            "p50": rpred.p50,
            "p10": rpred.p10,
            "p90": rpred.p90,
            "inside": (rpred.kwh >= rpred.p10) & (rpred.kwh <= rpred.p90),
            "ape": ape(rpred.p50, rpred.kwh),
            "x_country": rpred.x_country,
            "x_mapped_buildings": rpred.x_mapped_buildings,
        }
    ).sort_values("site").reset_index(drop=True)
    logo_m = _metrics(cv.p10, cv.p50, cv.p90, cv.actual)
    rtest_m = _metrics(rtest.p10, rtest.p50, rtest.p90, rtest.actual)
    v1 = json.loads((OUT / "cv_train.json").read_text(encoding="utf-8"))
    v1_rt = json.loads((OUT / "eval_final.json").read_text(encoding="utf-8"))
    payload = {
        "status": NOTE,
        "replaces_headline": False,
        "formula": (
            "log(kWh) = log(AMDA country) + alpha_country + beta_bld * log(bld_count/300); "
            "alpha_KE, alpha_NG and beta_bld ridge-shrunk toward 0 (AMDA) with lambda=2"
        ),
        "ridge_lambda": RIDGE_LAMBDA,
        "coefficients_full_train": full.coefs(),
        "n_train": int(len(train)),
        "interval": cal,
        "logo_cv": logo_m,
        "r_test": rtest_m,
        "r_test_note": NOTE,
        "v1_logo_pawacast_for_reference": v1["metrics"]["pawacast"],
        "v1_rtest_headline_unchanged": v1_rt["headline"],
        "logo_sites": cv.to_dict(orient="records"),
        "r_test_sites": rtest.to_dict(orient="records"),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "v2_posthoc.json").write_text(json.dumps(_py(payload), indent=2), encoding="utf-8")
    print("v2 POST-HOC  (does not replace headline)  " + NOTE)
    print("full-TRAIN coefficients:", json.dumps(full.coefs(), indent=2))
    _print("LOGO CV (TRAIN, 18 sites)", logo_m, cv)
    _print("R-test (" + NOTE + ")", rtest_m, rtest)
    print(f"\nwrote {OUT / 'v2_posthoc.json'}")
    return payload


if __name__ == "__main__":
    pd.set_option("display.width", 200)
    run()
