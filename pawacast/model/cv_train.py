"""Leave-one-group-out CV of the sprint log-linear model on TRAIN Renewvia sites.

Never loads held-out test consumption. Model is not frozen.
"""
from __future__ import annotations

import json
import math
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .growth import ANCHOR_MONTH, fit_observed_growth, observed_curve, to_month
from .loglinear import (
    IMPUTATION_SITES,
    REF_MONTH,
    apply_oof_interval,
    calibrate_oof_interval,
    fit,
    load_train_sites,
)
from .prior import SIGMA, Z90, estimate as estimate_v0
from ..targets.public import GROWTH
from ..targets.renewvia import TEST_SITES

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "results"
SUN, FLARE, PLASMA, ASH = "#FFD93D", "#FF6B35", "#FF3366", "#0D0D0D"


def ape(pred, actual):
    return np.abs(pred - actual) / actual


def _range_from_sigma(p50, sigma):
    return p50 * math.exp(-Z90 * sigma), p50, p50 * math.exp(Z90 * sigma)


def _metrics(p10, p50, p90, actual) -> dict:
    p10, p50, p90, actual = map(np.asarray, (p10, p50, p90, actual))
    inside = (actual >= p10) & (actual <= p90)
    return {
        "median_ape": float(np.median(ape(p50, actual))),
        "coverage_p10_p90": float(inside.mean()),
        "range_width": float(np.median(p90 / p10)),
        "bias": float(np.median(np.log(p50 / actual))),
        "n": int(len(actual)),
    }


def v0_at_ref(row: pd.Series) -> tuple[float, float, float]:
    e = estimate_v0(row.to_dict(), row.iso)
    k = to_month(1.0, REF_MONTH) / to_month(1.0, ANCHOR_MONTH)
    return e.p10 * k, e.p50 * k, e.p90 * k


def logo_cv(sites: pd.DataFrame, switched: list[str] | None = None) -> tuple[pd.DataFrame, dict]:
    switched = set(switched or [])
    rows = []
    for grp, held in sites.groupby("group"):
        train = sites[sites.group != grp]
        model = fit(train)
        pred = model.predict_frame(held)
        for _, r in pred.iterrows():
            p10_v0, p50_v0, p90_v0 = v0_at_ref(r)
            a10, a50, a90 = _range_from_sigma(r.amda, SIGMA)
            b10, b50, b90 = _range_from_sigma(20.0, SIGMA)
            actual = float(r.kwh)
            rows.append(
                {
                    "site": r.projectName,
                    "site_id": r.site_id,
                    "group": grp,
                    "country": r.iso,
                    "target_flag": r.target_flag,
                    "used_observed_only": r.projectName in switched,
                    "n_window": int(r.n_window),
                    "actual": actual,
                    "p50": float(r.p50),
                    "ape_pawacast": float(ape(r.p50, actual)),
                    "p10_amda": a10, "p50_amda": a50, "p90_amda": a90,
                    "ape_amda": float(ape(a50, actual)),
                    "p10_v0": p10_v0, "p50_v0": p50_v0, "p90_v0": p90_v0,
                    "ape_v0": float(ape(p50_v0, actual)),
                    "p10_brief20": b10, "p50_brief20": b50, "p90_brief20": b90,
                    "ape_brief20": float(ape(b50, actual)),
                    "x_mapped_buildings": float(r.x_mapped_buildings),
                    "bld_count": int(r.bld_count),
                    "bld_mean_area_m2": float(r.bld_mean_area_m2),
                    "amda": float(r.amda),
                }
            )
    cv = pd.DataFrame(rows).sort_values("site").reset_index(drop=True)
    cal = calibrate_oof_interval(cv.actual, cv.p50)
    p10, _, p90 = apply_oof_interval(cv.p50, cal)
    cv["p10"] = p10
    cv["p90"] = p90
    cv["inside"] = (cv.actual >= cv.p10) & (cv.actual <= cv.p90)
    return cv, cal


def plot_growth(sm: pd.DataFrame, gfit: dict, curve: pd.DataFrame, path: pathlib.Path) -> None:
    fig, ax = plt.subplots(figsize=(9.5, 5.4), dpi=140)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    smp = sm[sm.months_since_power_on >= 0]
    for _, g in smp.groupby("projectName"):
        gg = g.sort_values("months_since_power_on")
        ax.plot(gg.months_since_power_on, gg.kwh_used, color="#bbbbbb", lw=0.8, alpha=0.7)
    med = (
        smp.groupby("months_since_power_on")["kwh_used"]
        .median()
        .reset_index()
    )
    med = med[med.months_since_power_on.between(0, 48)]
    ax.scatter(med.months_since_power_on, med.kwh_used, s=18, c=ASH, zorder=4, label="median observed (TRAIN)")
    c = curve[curve.month <= 48]
    ax.fill_between(c.month, c.p10, c.p90, color=FLARE, alpha=0.28, linewidth=0, label="P10–P90 (within-site)")
    ax.plot(c.month, c.p50, color=PLASMA, lw=2.4, label="fitted median (within-site slope)")
    level = math.exp(gfit["intercept_log_at_18"])
    m = np.arange(0, 49)
    for _, row in GROWTH.iterrows():
        y = level * (1 + row.annual_growth) ** ((m - REF_MONTH) / 12)
        ax.plot(m, y, ls="--", lw=1.1, color=SUN, alpha=0.9)
    ax.text(36, level * (1 + GROWTH.annual_growth.iloc[0]) ** ((36 - REF_MONTH) / 12),
            " published rates\n (8% / 21% / 47% yr)", color="#8a6a00", fontsize=8, va="bottom")
    ax.set_xlim(0, 48)
    ax.set_ylim(0, max(18, float(sm.kwh_used.quantile(0.98))))
    ax.set_xlabel("months since power-on")
    ax.set_ylabel("kWh per customer per month")
    ax.set_title("TRAIN growth curve  ·  site intercepts + common log1p slope")
    ax.legend(frameon=False, loc="upper left")
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=140)
    plt.close(fig)


def _py(x):
    if isinstance(x, dict):
        return {str(k): _py(v) for k, v in x.items() if k != "a_site"}
    if isinstance(x, (float, np.floating)):
        return float(x)
    if isinstance(x, (int, np.integer)):
        return int(x)
    if isinstance(x, (bool, np.bool_)):
        return bool(x)
    return x


def _json_default(o):
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    raise TypeError(type(o))


def run() -> dict:
    sites, sm, check, switched = load_train_sites()
    sealed = sorted(TEST_SITES)
    print("sealed (not used):", ", ".join(sealed), flush=True)
    print("observed_only sites:", switched, flush=True)
    print(check[check.candidate].to_string(index=False), flush=True)

    cv, cal = logo_cv(sites, switched)
    if set(cv.site) & set(TEST_SITES):
        raise RuntimeError("CV scored a sealed test site")
    full = fit(sites, sigma=cal["sigma"], interval_method=cal["method"])
    gfit = fit_observed_growth(sm)
    curve = observed_curve(gfit, months=range(0, 49))

    methods = {
        "pawacast": _metrics(cv.p10, cv.p50, cv.p90, cv.actual),
        "amda": _metrics(cv.p10_amda, cv.p50_amda, cv.p90_amda, cv.actual),
        "v0": _metrics(cv.p10_v0, cv.p50_v0, cv.p90_v0, cv.actual),
        "brief20": _metrics(cv.p10_brief20, cv.p50_brief20, cv.p90_brief20, cv.actual),
    }

    def slope_to_annual_0_24(s):
        ratio = float(np.exp(s * (np.log1p(24) - np.log1p(0))))
        return ratio ** 0.5 - 1.0

    ann_p10 = slope_to_annual_0_24(gfit["site_slope_p10"])
    ann_p50 = slope_to_annual_0_24(gfit["site_slope_p50"])
    ann_p90 = slope_to_annual_0_24(gfit["site_slope_p90"])
    published = []
    for _, row in GROWTH.iterrows():
        g = float(row.annual_growth)
        published.append({
            "source": row.source,
            "observation": row.observation,
            "annual_growth": g,
            "inside_train_p10_p90": bool(ann_p10 <= g <= ann_p90),
        })

    drivers_example = []
    sample = sites.sort_values("projectName").iloc[0]
    est = full.estimate(sample.to_dict(), sample.iso)
    drivers_example = [{"name": n, "multiplier": m, "reason": why} for n, m, why in est.drivers]

    summary = {
        "note": "TRAIN leave-one-group-out only. Not an R-test / set-B score. Model not frozen.",
        "n_sites": int(len(sites)),
        "n_groups": int(sites.group.nunique()),
        "sealed_test_sites": sealed,
        "imputation": {
            "decision": "gap_filled_for_all_train_sites",
            "reason": (
                "profile/uniform slots redistribute the cumulative energy register "
                "across communication gaps (conserved to 1e-5). observed_only undercounts."
            ),
            "threshold": 0.15,
            "candidates": list(IMPUTATION_SITES),
            "switched_to_observed_only": switched,
            "per_site": check[check.candidate].to_dict(orient="records"),
            "emereoke_window_12_24": {
                "gapfilled": float(
                    sites.loc[sites.projectName == "Emereoke", "kwh_gapfilled"].iloc[0]
                ),
                "observed_only": float(
                    sites.loc[sites.projectName == "Emereoke", "kwh_observed_only"].iloc[0]
                ),
                "used": float(sites.loc[sites.projectName == "Emereoke", "kwh"].iloc[0]),
            },
        },
        "predictors": [
            "AMDA country baseline (offset / prior)",
            "log(building count / 300)",
        ],
        "ridge_lambda": full.lam,
        "beta_log_bld": float(full.beta[0]),
        "interval": cal,
        "sigma_log_residual": float(full.sigma),
        "range_width_from_sigma": float(math.exp(2 * Z90 * full.sigma)),
        "metrics": methods,
        "growth": {
            **{k: _py(v) for k, v in gfit.items() if k != "a_site"},
            "published_rates": published,
            "annual_band_0_24_p10_p50_p90": [ann_p10, ann_p50, ann_p90],
        },
        "example_drivers": drivers_example,
        "target_flags": sites.target_flag.value_counts().to_dict(),
    }

    frozen = {
        "formula": "log(kWh) = log(AMDA country) + beta_bld * log(bld_count / 300)",
        "beta_bld": float(full.beta[0]),
        "ref_bld": 300.0,
        "ridge_lambda": float(full.lam),
        "interval_method": cal["method"],
        "sigma": float(full.sigma),
        "z90": float(Z90),
        "ref_month": REF_MONTH,
        "window_lo": 12,
        "window_hi": 24,
        "target": "gap-filled kWh/customer/month, median of site-months with months_since_power_on in [12, 24]",
        "growth_form": "log(kWh) = a_site + slope * (log1p(month) - log1p(18))",
        "growth_slope": float(gfit["slope"]),
        "growth_annual_0_24": float(gfit["annual_0_24"]),
        "growth_annual_12_24": float(gfit["annual_12_24"]),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "model_frozen.json").write_text(
        json.dumps(frozen, indent=2), encoding="utf-8"
    )
    cv.to_csv(OUT / "cv_train_sites.csv", index=False, encoding="utf-8", lineterminator="\n")
    (OUT / "cv_train.json").write_text(
        json.dumps(summary, indent=2, default=_json_default), encoding="utf-8"
    )
    curve.to_csv(OUT / "growth_curve.csv", index=False, encoding="utf-8", lineterminator="\n")
    plot_growth(sm, gfit, curve, OUT / "growth_curve.png")
    print(json.dumps(methods, indent=2))
    print(cv[["site", "group", "country", "actual", "p50", "p10", "p90", "inside",
              "ape_pawacast", "ape_amda", "ape_v0", "ape_brief20"]].round(3).to_string(index=False))
    return {"summary": summary, "cv": cv, "curve": curve, "sites": sites, "sm": sm}


def main() -> None:
    run()


if __name__ == "__main__":
    main()
