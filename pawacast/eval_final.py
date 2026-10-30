"""One-time held-out score. Loads frozen coefficients; does not refit.

Requires PAWACAST_FINAL_EVAL=1. Headline set is R-test (Amendment 1).
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

from .features import build_features
from .model.growth import ANCHOR_MONTH, observed_multiplier, to_month
from .model.loglinear import (
    REF_BLD,
    REF_MONTH,
    TEST_SITES,
    apply_imputation,
    attach_features,
    iso_of,
    load_frozen,
    site_level_targets,
)
from .model.prior import SIGMA, Z90, country_baseline, estimate as estimate_v0
from .targets.public import UNLOCATED, named_sites
from .targets.renewvia import HeldOutError, final_eval_enabled, load_site_months, site_id_of

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "results"
SUN, FLARE, PLASMA, ASH = "#FFD93D", "#FF6B35", "#FF3366", "#0D0D0D"
FREEZE_COMMIT = "c3df2c84b019cea36c6fb8d7ef4b671e0dffc30d"


def ape(pred, actual):
    return np.abs(pred - actual) / actual


def _range_from_sigma(p50, sigma):
    p50 = np.asarray(p50, dtype=float)
    return p50 * math.exp(-Z90 * sigma), p50, p50 * math.exp(Z90 * sigma)


def _metrics(p10, p50, p90, actual) -> dict:
    p10, p50, p90, actual = (np.asarray(x, dtype=float) for x in (p10, p50, p90, actual))
    ok = np.isfinite(p50) & np.isfinite(actual) & (actual > 0)
    p10, p50, p90, actual = p10[ok], p50[ok], p90[ok], actual[ok]
    if len(actual) == 0:
        return {"median_ape": None, "coverage_p10_p90": None, "range_width": None, "bias": None, "n": 0}
    inside = (actual >= p10) & (actual <= p90)
    return {
        "median_ape": float(np.median(ape(p50, actual))),
        "coverage_p10_p90": float(inside.mean()),
        "range_width": float(np.median(p90 / p10)),
        "bias": float(np.median(np.log(p50 / actual))),
        "n": int(len(actual)),
    }


def _method_metrics(df: pd.DataFrame) -> dict:
    return {
        "pawacast": _metrics(df.p10, df.p50, df.p90, df.actual),
        "amda": _metrics(df.p10_amda, df.p50_amda, df.p90_amda, df.actual),
        "v0": _metrics(df.p10_v0, df.p50_v0, df.p90_v0, df.actual),
        "brief20": _metrics(df.p10_brief20, df.p50_brief20, df.p90_brief20, df.actual),
    }


def _py(x):
    if isinstance(x, dict):
        return {k: _py(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_py(v) for v in x]
    if isinstance(x, (np.floating, float)):
        return float(x)
    if isinstance(x, (np.integer, int)):
        return int(x)
    if isinstance(x, (np.bool_, bool)):
        return bool(x)
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return None
    return x


def eval_month_renewvia(row: pd.Series) -> float:
    if row.target_flag == "window_12_24":
        return float(REF_MONTH)
    return 0.5 * (float(row.min_month) + float(row.max_month))


def score_rows(frame: pd.DataFrame, model, frozen: dict) -> pd.DataFrame:
    """Apply frozen P50 at month 18, then growth-align to eval_month. No refit."""
    pred = model.predict_frame(frame)
    month = pred.eval_month.to_numpy(float)
    slope = float(frozen["growth_slope"])
    mult = observed_multiplier(month, slope, ref=REF_MONTH)
    pred["p50"] = pred.p50.to_numpy(float) * mult
    pred["p10"] = pred.p10.to_numpy(float) * mult
    pred["p90"] = pred.p90.to_numpy(float) * mult
    rows = []
    for _, r in pred.iterrows():
        feats = r.to_dict()
        e = estimate_v0(feats, r.iso)
        k = to_month(1.0, float(r.eval_month)) / to_month(1.0, ANCHOR_MONTH)
        p10_v0, p50_v0, p90_v0 = e.p10 * k, e.p50 * k, e.p90 * k
        a10, a50, a90 = _range_from_sigma(r.amda, SIGMA)
        b10, b50, b90 = _range_from_sigma(20.0, SIGMA)
        actual = float(r.actual)
        survey = r.survey_kwh if "survey_kwh" in r.index and pd.notna(r.survey_kwh) else np.nan
        rows.append(
            {
                "site": r.site,
                "site_id": r.site_id,
                "eval_set": r.eval_set,
                "group": r.group,
                "country": r.iso,
                "geo_conf": r.geo_conf if "geo_conf" in r.index else "high",
                "target_flag": r.target_flag if "target_flag" in r.index else "",
                "eval_month": float(r.eval_month),
                "n_window": int(r.n_window) if "n_window" in r.index and pd.notna(r.n_window) else None,
                "actual": actual,
                "p10": float(r.p10),
                "p50": float(r.p50),
                "p90": float(r.p90),
                "inside": bool(actual >= r.p10 and actual <= r.p90),
                "ape_pawacast": float(ape(r.p50, actual)),
                "p10_amda": float(a10),
                "p50_amda": float(a50),
                "p90_amda": float(a90),
                "ape_amda": float(ape(a50, actual)),
                "p10_v0": float(p10_v0),
                "p50_v0": float(p50_v0),
                "p90_v0": float(p90_v0),
                "ape_v0": float(ape(p50_v0, actual)),
                "p10_brief20": float(b10),
                "p50_brief20": float(b50),
                "p90_brief20": float(b90),
                "ape_brief20": float(ape(b50, actual)),
                "survey_kwh": None if pd.isna(survey) else float(survey),
                "ape_survey": None if pd.isna(survey) else float(ape(survey, actual)),
                "bld_count": int(r.bld_count) if pd.notna(r.bld_count) else None,
                "amda": float(r.amda),
                "x_mapped_buildings": float(r.x_mapped_buildings),
            }
        )
    return pd.DataFrame(rows)


def load_r_test_frame() -> pd.DataFrame:
    sm = load_site_months(role="test")
    sm, _ = apply_imputation(sm)
    sites = attach_features(site_level_targets(sm, allow_test=True))
    found = set(sites.projectName)
    missing = sorted(TEST_SITES - found)
    if missing:
        print("R-test sites with no eligible site-months: " + ", ".join(missing), flush=True)
    extra = found - set(TEST_SITES)
    if extra:
        raise RuntimeError(f"non-test sites in test parquet: {extra}")
    sites = sites.copy()
    sites["site"] = sites.projectName
    sites["eval_set"] = "R-test"
    sites["actual"] = sites.kwh
    sites["eval_month"] = sites.apply(eval_month_renewvia, axis=1)
    sites["survey_kwh"] = np.nan
    sites["geo_conf"] = "high"
    return sites


def load_published_frame(eval_set: str, refresh: bool = False) -> pd.DataFrame:
    s = named_sites().query("eval_set == @eval_set").dropna(subset=["lat"]).reset_index(drop=True)
    cache = "named_sites" if eval_set == "A" else "eval_setB"
    feats = build_features(s, name=cache, refresh=refresh)
    keep = ["site_id", "bld_count", "bld_mean_area_m2", "bld_large_count",
            "poi_count", "ntl_2024_5km", "grid_dist_km"]
    out = s.merge(feats[keep], on="site_id", how="left")
    out["iso"] = out.country.map(iso_of)
    out["amda"] = out.iso.map(lambda c: country_baseline(c)[0])
    out["x_log_bld"] = np.log(out.bld_count.clip(lower=1) / REF_BLD)
    out["eval_month"] = out.months_since_connection.astype(float)
    out["actual"] = out.kwh_cust_month
    out["group"] = eval_set
    out["target_flag"] = "published"
    out["n_window"] = np.nan
    out["survey_kwh"] = out.survey_kwh_cust_month
    out["projectName"] = out.site
    return out


def country_check() -> dict:
    rows = []
    enko = named_sites().query("eval_set == 'unlocated'")
    extra = pd.DataFrame(
        {
            "site": enko.site,
            "country": enko.country,
            "customers": enko.customers,
            "kwh_cust_month": enko.kwh_cust_month,
            "source": enko.source,
        }
    )
    u = pd.concat([UNLOCATED, extra], ignore_index=True)
    for _, r in u.iterrows():
        iso = str(r.country)
        amda, src = country_baseline(iso)
        actual = float(r.kwh_cust_month)
        rows.append(
            {
                "site": r.site,
                "country": iso,
                "customers": None if pd.isna(r.customers) else int(r.customers) if float(r.customers) == int(r.customers) else float(r.customers),
                "actual": actual,
                "p50_pawacast_no_location": amda,
                "p50_amda": amda,
                "ape_amda": float(ape(amda, actual)),
                "amda_source": src,
                "source": r.source,
            }
        )
    df = pd.DataFrame(rows)
    return {
        "note": (
            "Unlocated published sites have no coordinates, so PawaCast equals the AMDA "
            "country (or regional) baseline. Not a site-level score."
        ),
        "median_ape_amda": float(df.ape_amda.median()),
        "n": int(len(df)),
        "sites": df.to_dict(orient="records"),
    }


def plot_ranges(df: pd.DataFrame, path: pathlib.Path) -> None:
    """P10–P90 bar vs actual dot. R-test highlighted. Deck-card size."""
    order = {"R-test": 0, "B": 1, "A": 2}
    d = df[df.eval_set.isin(order)].copy()
    d["_ord"] = d.eval_set.map(order)
    d = d.sort_values(["_ord", "country", "site"], ascending=[False, False, False]).reset_index(drop=True)
    n = len(d)
    fig, ax = plt.subplots(figsize=(10.0, 6.2), dpi=150)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    colours = {"R-test": PLASMA, "B": FLARE, "A": "#555555"}
    for i, r in d.iterrows():
        c = colours[r.eval_set]
        lw = 7.5 if r.eval_set == "R-test" else 5.5
        ax.plot([r.p10, r.p90], [i, i], color=c, lw=lw, solid_capstyle="round",
                alpha=0.92 if r.eval_set == "R-test" else 0.75, zorder=2)
        ax.plot(r.p50, i, marker="|", color=c, markersize=12, markeredgewidth=2.2, zorder=3)
        ax.scatter(r.actual, i, s=42, color=SUN, edgecolors=ASH, linewidths=0.8, zorder=4)
    ax.set_yticks(range(n))
    labels = [f"{r.site}  {r.country}  {r.eval_set}" for _, r in d.iterrows()]
    ax.set_yticklabels(labels, fontsize=8, fontfamily="sans-serif")
    for i, r in d.iterrows():
        if r.eval_set == "R-test":
            ax.get_yticklabels()[i].set_fontweight("bold")
            ax.get_yticklabels()[i].set_color(ASH)
    ax.set_xlabel("kWh per customer per month")
    ax.set_title("Held-out demand range  ·  P10–P90 vs actual")
    ax.axvline(20, color="#dddddd", lw=0.8, zorder=0)
    from matplotlib.lines import Line2D
    handles = [
        Line2D([0], [0], color=PLASMA, lw=7, solid_capstyle="round", label="R-test P10–P90"),
        Line2D([0], [0], color=FLARE, lw=6, solid_capstyle="round", label="Set B P10–P90"),
        Line2D([0], [0], color="#555555", lw=6, solid_capstyle="round", label="Set A P10–P90 (seen)"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor=SUN, markeredgecolor=ASH,
               markersize=7, label="actual"),
    ]
    ax.legend(handles=handles, frameon=False, loc="lower right", fontsize=8)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.set_xlim(0, max(40.0, float(d[["p90", "actual"]].max().max()) * 1.05))
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _print_set(name: str, metrics: dict) -> None:
    print(f"\n{name}")
    print(f"{'method':<12} {'medAPE':>8} {'cover':>8} {'width':>8} {'bias':>8} {'n':>4}")
    for m in ("pawacast", "amda", "v0", "brief20"):
        r = metrics[m]
        print(
            f"{m:<12} {100 * r['median_ape']:7.1f}% {100 * r['coverage_p10_p90']:7.0f}% "
            f"{r['range_width']:8.2f} {r['bias']:8.2f} {r['n']:4d}"
        )


def run_final(refresh: bool = False) -> dict:
    if not final_eval_enabled():
        raise HeldOutError("PAWACAST_FINAL_EVAL=1 is required for the one-time held-out score")
    model, frozen = load_frozen()
    if abs(float(frozen["beta_bld"]) - 0.3031258114090143) > 1e-12:
        raise RuntimeError("frozen beta_bld does not match model_freeze.txt")
    if frozen["interval_method"] != "oof_sigma":
        raise RuntimeError("frozen interval_method is not oof_sigma")

    r_test = score_rows(load_r_test_frame(), model, frozen)
    set_b = score_rows(load_published_frame("B", refresh=refresh), model, frozen)
    set_a = score_rows(load_published_frame("A", refresh=refresh), model, frozen)
    sites = pd.concat([r_test, set_b, set_a], ignore_index=True)
    sites = sites.sort_values(["eval_set", "country", "site"]).reset_index(drop=True)

    metrics = {
        "R-test": _method_metrics(r_test),
        "B": _method_metrics(set_b),
        "A": _method_metrics(set_a),
    }
    high_b = set_b[set_b.geo_conf != "low"]
    if len(high_b) and len(high_b) < len(set_b):
        metrics["B_geo_high"] = _method_metrics(high_b)

    country = country_check()
    plot_ranges(sites, OUT / "eval_ranges.png")

    payload = {
        "freeze_commit": FREEZE_COMMIT,
        "headline_set": "R-test",
        "headline": metrics["R-test"]["pawacast"],
        "frozen": {
            "formula": frozen["formula"],
            "beta_bld": frozen["beta_bld"],
            "sigma": frozen["sigma"],
            "interval_method": frozen["interval_method"],
            "growth_slope": frozen["growth_slope"],
            "ref_month": frozen["ref_month"],
            "target": frozen["target"],
        },
        "metrics": metrics,
        "country_check": country,
        "n_sites": {
            "R-test": int(len(r_test)),
            "B": int(len(set_b)),
            "A": int(len(set_a)),
        },
        "r_test_sites": sorted(r_test.site.tolist()),
        "set_b_sites": sorted(set_b.site.tolist()),
        "set_a_sites": sorted(set_a.site.tolist()),
        "note": (
            "Scored once with frozen coefficients. R-test is the headline. "
            "Set A was seen before the sprint (continuity). "
            "PawaCast P50 is grown from month 18 with the frozen log1p slope; "
            "v0 is grown from month 24 with the pre-sprint 18% rate; "
            "AMDA and 20 kWh are unscaled country/brief figures (same as TRAIN CV)."
        ),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    sites.to_csv(OUT / "eval_sites.csv", index=False, encoding="utf-8", lineterminator="\n")
    (OUT / "eval_final.json").write_text(json.dumps(_py(payload), indent=2), encoding="utf-8")

    print("sealed test sites scored: " + ", ".join(sorted(r_test.site)))
    print("\n=== HEADLINE  R-test (never seen) ===")
    _print_set("R-test", metrics["R-test"])
    _print_set("Set B (Olenarau KE, Tum ET, Omorate ET)", metrics["B"])
    if "B_geo_high" in metrics:
        _print_set("Set B excluding low geo_conf", metrics["B_geo_high"])
    _print_set("Set A (seen, continuity)", metrics["A"])
    print("\n=== PER SITE ===")
    cols = ["eval_set", "site", "country", "eval_month", "actual", "p50", "p10", "p90",
            "inside", "ape_pawacast", "ape_amda", "ape_v0", "ape_brief20"]
    print(sites[cols].round(3).to_string(index=False))
    print("\n=== COUNTRY CHECK (unlocated; PawaCast = AMDA) ===")
    cdf = pd.DataFrame(country["sites"])
    print(cdf[["site", "country", "actual", "p50_amda", "ape_amda"]].round(3).to_string(index=False))
    print(f"median APE vs AMDA: {100 * country['median_ape_amda']:.1f}%  n={country['n']}")
    print(f"\nwrote {OUT / 'eval_final.json'}")
    print(f"wrote {OUT / 'eval_sites.csv'}")
    print(f"wrote {OUT / 'eval_ranges.png'}")
    return payload


if __name__ == "__main__":
    pd.set_option("display.width", 220)
    pd.set_option("display.max_columns", 30)
    run_final()
