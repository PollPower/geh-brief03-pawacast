"""Meter-update v2 vs frozen update. TRAIN calibration; R-test post-hoc.

Does not change the frozen day-one model or headline score.
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

from .meter_update_real import (
    KS,
    OUT,
    ROOT,
    ape,
    first_k_readings,
    load_all_site_months,
    load_priors,
    posterior_at_18,
    _py,
)
from .model.loglinear import REF_MONTH
from .model.prior import Z90
from .model.update import OBS_SIGMA
from .model.update_v2 import (
    choose_scale,
    estimate_noise,
    estimate_projection,
    update_v2,
)
from .targets.renewvia import HeldOutError, final_eval_enabled, load_site_months

SUN, FLARE, PLASMA, ASH = "#FFD93D", "#FF6B35", "#FF3366", "#0D0D0D"
NOTE_RTEST = "post-hoc, test already seen"


def summarise(df: pd.DataFrame, p10="p10", p50="p50", p90="p90") -> dict:
    out = {}
    for grp, g in df.groupby("group"):
        out[grp] = {}
        for k, gg in g.groupby("k"):
            inside = (gg.actual >= gg[p10]) & (gg.actual <= gg[p90])
            out[grp][str(int(k))] = {
                "median_ape": float(np.median(ape(gg[p50], gg.actual))),
                "coverage_p10_p90": float(inside.mean()),
                "n_inside": int(inside.sum()),
                "range_width": float(np.median(gg[p90] / gg[p10])),
                "bias": float(np.median(np.log(gg[p50] / gg.actual))),
                "n": int(len(gg)),
            }
    return out


def plot_both(frozen: dict, v2: dict, path: pathlib.Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10.0, 5.4), dpi=150)
    fig.patch.set_facecolor("white")
    ks = list(KS)
    series = [
        ("TRAIN-LOGO", "frozen", FLARE, "--", 0.7),
        ("TRAIN-LOGO", "v2", FLARE, "-", 1.0),
        ("R-test", "frozen", PLASMA, "--", 0.7),
        ("R-test", "v2", PLASMA, "-", 1.0),
    ]
    src = {"frozen": frozen, "v2": v2}
    ax = axes[0]
    ax.set_facecolor("white")
    for grp, kind, color, ls, alpha in series:
        y = [100 * src[kind][grp][str(k)]["median_ape"] for k in ks]
        lbl = f"{grp} {kind}"
        ax.plot(ks, y, color=color, ls=ls, lw=2.4, marker="o", markersize=6, alpha=alpha, label=lbl)
    ax.set_xticks(ks)
    ax.set_xlabel("months of REAL readings")
    ax.set_ylabel("median APE of P50 (%)")
    ax.set_ylim(0, None)
    ax.set_title("error")
    ax.legend(frameon=False, fontsize=7.5, loc="upper right")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax = axes[1]
    ax.set_facecolor("white")
    ax.axhline(80, color="#cccccc", lw=1.2, zorder=0)
    ax.text(0.15, 82, "80% target", color="#888888", fontsize=8)
    for grp, kind, color, ls, alpha in series:
        y = [100 * src[kind][grp][str(k)]["coverage_p10_p90"] for k in ks]
        ax.plot(ks, y, color=color, ls=ls, lw=2.4, marker="o", markersize=6, alpha=alpha, label=f"{grp} {kind}")
    ax.set_xticks(ks)
    ax.set_xlabel("months of REAL readings")
    ax.set_ylabel("P10–P90 coverage (%)")
    ax.set_ylim(0, 105)
    ax.set_title("coverage")
    ax.legend(frameon=False, fontsize=7.5, loc="lower right")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.suptitle("Meters correct  ·  REAL meter data (Renewvia)  ·  frozen vs update v2", fontsize=12)
    fig.text(
        0.5, 0.01,
        "R-test is post-hoc, test already seen.  Day-one model unchanged.  "
        "v2 sigma = AR(1) monthly noise + first-k→12–24 projection error.",
        ha="center", fontsize=8, color="#555555",
    )
    fig.tight_layout(rect=(0, 0.06, 1, 0.94))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    fig.savefig(OUT / "meter_update_real.png", dpi=150)
    plt.close(fig)


def run() -> dict:
    if not final_eval_enabled():
        raise HeldOutError("PAWACAST_FINAL_EVAL=1 is required (R-test scored post-hoc only)")
    priors, frozen = load_priors()
    sigma_prior = float(frozen["sigma"])
    slope = float(frozen["growth_slope"])
    train_sm = load_site_months(role="train")
    targets = pd.read_csv(OUT / "cv_train_sites.csv", encoding="utf-8")
    noise = estimate_noise(train_sm, slope)
    projection = estimate_projection(train_sm, targets, slope, noise)
    cal = {"noise": noise, "projection": projection, "scale": 1.0}

    sm = load_all_site_months()
    rows_f, rows_v = [], []
    for _, p in priors.iterrows():
        site_sm = sm[sm.projectName == p.site]
        for k in KS:
            readings = first_k_readings(site_sm, k)
            fr = posterior_at_18(p.p50_prior, sigma_prior, readings, slope)
            rows_f.append(
                {
                    "site": p.site, "group": p.group, "k": int(k),
                    "actual": float(p.actual),
                    "p10": float(fr["p10"]), "p50": float(fr["p50"]), "p90": float(fr["p90"]),
                }
            )
            v2 = update_v2(p.p50_prior, readings, cal, sigma_prior, slope)
            sd0 = float(v2.get("posterior_sd_unscaled") or v2["sigma"])
            z0 = math.log(v2["p50"] / p.actual) / sd0 if sd0 > 0 else 0.0
            rows_v.append(
                {
                    "site": p.site, "group": p.group, "k": int(k),
                    "actual": float(p.actual),
                    "p50": float(v2["p50"]),
                    "sd_unscaled": sd0,
                    "z_unscaled": z0,
                    "n_readings": int(v2["n_readings"]),
                    "sigma_like": v2["sigma_like"],
                }
            )
    df_f = pd.DataFrame(rows_f)
    df_v = pd.DataFrame(rows_v)
    scale = choose_scale(df_v, target=0.80)
    cal["scale"] = scale
    cal["scale_note"] = (
        f"single TRAIN-LOGO scale on k=1,3,6 so |z| 80th percentile / Z90 ≈ 1; scale={scale:.3f}"
    )
    # apply scale to k>=1; k=0 stays the frozen day-one interval
    p10, p90, sig = [], [], []
    for _, r in df_v.iterrows():
        s = float(r.sd_unscaled) if int(r.k) == 0 else float(r.sd_unscaled) * scale
        p10.append(float(r.p50) * math.exp(-Z90 * s))
        p90.append(float(r.p50) * math.exp(Z90 * s))
        sig.append(s)
    df_v["p10"] = p10
    df_v["p90"] = p90
    df_v["sigma"] = sig

    sum_f = summarise(df_f)
    sum_v = summarise(df_v)
    plot_both(sum_f, sum_v, OUT / "meter_update_v2.png")

    payload = {
        "label": "REAL meter data (Renewvia) — update v2",
        "r_test_note": NOTE_RTEST,
        "day_one_model": "frozen; unchanged",
        "frozen_update": {
            "obs_sigma": OBS_SIGMA,
            "note": "independent monthly noise; overconfident",
            "summary": sum_f,
        },
        "v2": {
            "noise": noise,
            "projection": projection,
            "scale": scale,
            "scale_note": cal["scale_note"],
            "sigma_prior": sigma_prior,
            "ref_month": REF_MONTH,
            "summary": sum_v,
        },
        "sites_v2": df_v.to_dict(orient="records"),
        "note": (
            "v2 predictive sigma = scale * posterior sd, with likelihood sd "
            "sqrt(AR1 var of k-month mean + extra first-k→12–24 projection var). "
            "Noise, projection, and scale from TRAIN only. "
            f"R-test is {NOTE_RTEST}."
        ),
    }
    (OUT / "meter_update_v2.json").write_text(json.dumps(_py(payload), indent=2), encoding="utf-8")
    print("update v2  TRAIN-only calibration  R-test: " + NOTE_RTEST)
    print(f"sigma_month={noise['sigma_month']:.3f}  rho={noise['rho']:.3f}  scale={scale:.3f}")
    print(f"{'method':<8} {'group':<12} {'k':>3} {'medAPE':>8} {'cover':>8} {'width':>8} {'bias':>8}")
    for name, smry in (("frozen", sum_f), ("v2", sum_v)):
        for grp in ("TRAIN-LOGO", "R-test"):
            for k in KS:
                s = smry[grp][str(k)]
                tag = grp if name == "v2" and grp == "R-test" else grp
                print(
                    f"{name:<8} {tag:<12} {k:3d} {100 * s['median_ape']:7.1f}% "
                    f"{100 * s['coverage_p10_p90']:6.0f}% {s['range_width']:8.2f} {s['bias']:8.2f}"
                )
    print(f"\nwrote {OUT / 'meter_update_v2.json'}")
    print(f"wrote {OUT / 'meter_update_v2.png'} and updated {OUT / 'meter_update_real.png'}")
    return payload


if __name__ == "__main__":
    pd.set_option("display.width", 220)
    run()
