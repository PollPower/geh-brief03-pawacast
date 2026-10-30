"""REAL meter update on Renewvia site-months. Frozen prior; OBS_SIGMA = 0.30.

Protocol declared in EVAL_PLAN.md Deviations before this was run.
Does not refit the day-one model or rewrite the headline score.
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

from .model.growth import observed_multiplier
from .model.loglinear import REF_MONTH, load_frozen
from .model.update import OBS_SIGMA, update
from .targets.renewvia import HeldOutError, TEST_SITES, final_eval_enabled, load_site_months

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "results"
SUN, FLARE, PLASMA, ASH = "#FFD93D", "#FF6B35", "#FF3366", "#0D0D0D"
KS = (0, 1, 3, 6)


def ape(pred, actual):
    return abs(pred - actual) / actual


def _py(x):
    if isinstance(x, dict):
        return {k: _py(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_py(v) for v in x]
    if isinstance(x, (np.bool_, bool)):
        return bool(x)
    if isinstance(x, (np.floating, float)):
        return None if not math.isfinite(x) else float(x)
    if isinstance(x, (np.integer, int)):
        return int(x)
    return x


def first_k_readings(sm: pd.DataFrame, k: int) -> list[tuple[float, float]]:
    g = sm.sort_values("month").head(int(k))
    out = []
    for _, r in g.iterrows():
        kwh = float(r.kwh_cust_month)
        if not math.isfinite(kwh) or kwh <= 0:
            continue
        m = max(float(r.months_since_power_on), 0.0)
        out.append((m, kwh))
    return out


def posterior_at_18(p50_prior: float, sigma_prior: float, readings, slope: float) -> dict:
    """Map readings to month 18 with the frozen log1p slope, then conjugate update."""
    adj = []
    for m, kwh in readings:
        mult = float(observed_multiplier(m, slope, ref=REF_MONTH))
        k18 = kwh / mult if mult > 0 else kwh
        adj.append((float(REF_MONTH), k18))
    return update(p50_prior, adj, sigma_prior=sigma_prior, g=0.0)


def load_priors() -> tuple[pd.DataFrame, dict]:
    _, frozen = load_frozen()
    train = pd.read_csv(OUT / "cv_train_sites.csv", encoding="utf-8")
    evals = pd.read_csv(OUT / "eval_sites.csv", encoding="utf-8")
    rtest = evals[evals.eval_set == "R-test"].copy()
    rows = []
    for _, r in train.iterrows():
        rows.append(
            {
                "site": r.site,
                "site_id": r.site_id,
                "group": "TRAIN-LOGO",
                "p50_prior": float(r.p50),
                "actual": float(r.actual),
            }
        )
    for _, r in rtest.iterrows():
        rows.append(
            {
                "site": r.site,
                "site_id": r.site_id,
                "group": "R-test",
                "p50_prior": float(r.p50),
                "actual": float(r.actual),
            }
        )
    return pd.DataFrame(rows), frozen


def load_all_site_months() -> pd.DataFrame:
    train = load_site_months(role="train")
    test = load_site_months(role="test")
    if set(test.projectName) != set(TEST_SITES):
        raise RuntimeError(f"test parquet sites {sorted(test.projectName)} != {sorted(TEST_SITES)}")
    return pd.concat([train, test], ignore_index=True)


def summarise(rows: pd.DataFrame) -> dict:
    out = {}
    for grp, g in rows.groupby("group"):
        out[grp] = {}
        for k, gg in g.groupby("k"):
            n = int(len(gg))
            n_inside = int(gg.inside.sum())
            coverage = float(gg.inside.mean())
            out[grp][str(int(k))] = {
                "median_ape": float(gg.ape.median()),
                "range_width": float(gg.width.median()),
                "coverage_p10_p90": coverage,
                "n_inside": n_inside,
                "bias": float(gg.bias.median()),
                "n": n,
            }
    return out


def overconfidence_notes(summary: dict, threshold: float = 0.80) -> dict:
    """Plain-language flags. No parameter is changed."""
    notes = []
    by_group = {}
    for grp in ("R-test", "TRAIN-LOGO"):
        parts = []
        low = False
        for k in (1, 3, 6):
            cov = summary[grp][str(k)]["coverage_p10_p90"]
            n_in = summary[grp][str(k)]["n_inside"]
            n = summary[grp][str(k)]["n"]
            parts.append(f"k={k} {100 * cov:.0f}% ({n_in}/{n})")
            if cov < threshold:
                low = True
        line = f"{grp}: " + ", ".join(parts)
        if low:
            # Worst of k=1,3,6 for the caption's X%.
            worst = min(summary[grp][str(k)]["coverage_p10_p90"] for k in (1, 3, 6))
            line = (
                f"range after update is overconfident: {100 * worst:.0f}% coverage "
                f"({grp}; " + ", ".join(parts) + ")"
            )
        by_group[grp] = {"overconfident": low, "text": line}
        notes.append(line)
    return {"threshold": threshold, "groups": by_group, "lines": notes}


def plot_update(summary: dict, notes: dict, path: pathlib.Path) -> None:
    fig, ax = plt.subplots(figsize=(10.0, 5.6), dpi=150)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax2 = ax.twinx()
    styles = {
        "R-test": (PLASMA, "R-test (n=5)"),
        "TRAIN-LOGO": (FLARE, "TRAIN-LOGO (n=18)"),
    }
    ks = list(KS)
    for grp, (color, label) in styles.items():
        ape = [100 * summary[grp][str(k)]["median_ape"] for k in ks]
        ax.plot(ks, ape, color=color, lw=2.6, marker="o", markersize=7, label=label)
    # Same n and OBS_SIGMA → same posterior width in both groups.
    width = [summary["R-test"][str(k)]["range_width"] for k in ks]
    ax2.plot(ks, width, color=ASH, lw=1.6, ls="--", marker="s", markersize=5, label="range width")
    ax.set_xticks(list(KS))
    ax.set_xlabel("months of REAL meter readings")
    ax.set_ylabel("median APE of P50 (%)")
    ax2.set_ylabel("median P90 / P10")
    ax.set_title("Meters correct  ·  REAL meter data (Renewvia)")
    ax.set_ylim(0, None)
    ax2.set_ylim(0, None)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, frameon=False, loc="upper right")
    ax.text(
        0.02, 0.06,
        "prior σ = 0.699  ·  OBS_SIGMA = 0.30 (pre-sprint)  ·  frozen growth  ·  no tuning",
        transform=ax.transAxes, fontsize=8, color="#666666",
    )
    for sp in ("top",):
        ax.spines[sp].set_visible(False)
        ax2.spines[sp].set_visible(False)
    caption_lines = []
    for grp in ("R-test", "TRAIN-LOGO"):
        if not notes["groups"][grp]["overconfident"]:
            continue
        covs = [summary[grp][str(k)]["coverage_p10_p90"] for k in (1, 3, 6)]
        caption_lines.append(
            f"range after update is overconfident: {100 * min(covs):.0f}% coverage "
            f"({grp}; k=1/3/6 = " + "/".join(f"{100 * c:.0f}%" for c in covs) + ")"
        )
    caption = "\n".join(caption_lines)
    fig.tight_layout(rect=(0, 0.14 if caption else 0.02, 1, 1))
    if caption:
        fig.text(0.5, 0.015, caption, ha="center", va="bottom", fontsize=8.5, color=ASH)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)


def run() -> dict:
    if not final_eval_enabled():
        raise HeldOutError("PAWACAST_FINAL_EVAL=1 is required (R-test site-months)")
    priors, frozen = load_priors()
    sigma = float(frozen["sigma"])
    slope = float(frozen["growth_slope"])
    if abs(OBS_SIGMA - 0.30) > 1e-12:
        raise RuntimeError("OBS_SIGMA must stay 0.30")
    sm = load_all_site_months()
    rows = []
    for _, p in priors.iterrows():
        site_sm = sm[sm.projectName == p.site]
        if site_sm.empty:
            raise RuntimeError(f"no site-months for {p.site}")
        for k in KS:
            readings = first_k_readings(site_sm, k)
            post = posterior_at_18(p.p50_prior, sigma, readings, slope)
            rows.append(
                {
                    "site": p.site,
                    "site_id": p.site_id,
                    "group": p.group,
                    "k": int(k),
                    "n_readings": int(post["n_readings"]),
                    "actual": float(p.actual),
                    "p50_prior": float(p.p50_prior),
                    "p10": float(post["p10"]),
                    "p50": float(post["p50"]),
                    "p90": float(post["p90"]),
                    "sigma": float(post["sigma"]),
                    "width": float(post["p90"] / post["p10"]),
                    "ape": float(ape(post["p50"], p.actual)),
                    "inside": bool(p.actual >= post["p10"] and p.actual <= post["p90"]),
                    "bias": float(math.log(post["p50"] / p.actual)),
                    "reading_months": [m for m, _ in readings],
                }
            )
    df = pd.DataFrame(rows)
    summary = summarise(df)
    notes = overconfidence_notes(summary)
    plot_update(summary, notes, OUT / "meter_update_real.png")
    payload = {
        "label": "REAL meter data (Renewvia)",
        "obs_sigma": OBS_SIGMA,
        "sigma_prior": sigma,
        "growth_slope": slope,
        "ref_month": REF_MONTH,
        "ks": list(KS),
        "note": (
            "Day-one P50/σ frozen. TRAIN priors are leave-one-group-out. "
            "Readings are the first k site-months in the aggregate, mapped to month 18 "
            "with the frozen log1p growth slope, then updated with OBS_SIGMA=0.30. "
            "Headline R-test table is unchanged. No tuning."
        ),
        "overconfidence": notes,
        "caption": (
            "  ".join(
                f"range after update is overconfident: "
                f"{100 * min(summary[g][str(k)]['coverage_p10_p90'] for k in (1, 3, 6)):.0f}% coverage ({g})"
                for g in ("R-test", "TRAIN-LOGO")
                if notes["groups"][g]["overconfident"]
            )
            or None
        ),
        "summary": summary,
        "sites": df.drop(columns=["reading_months"]).to_dict(orient="records"),
        "reading_months": {
            f"{r.group}|{r.site}|k{int(r.k)}": r.reading_months for _, r in df.iterrows()
        },
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "meter_update_real.json").write_text(
        json.dumps(_py(payload), indent=2), encoding="utf-8"
    )
    print("REAL meter data (Renewvia)  OBS_SIGMA=0.30  sigma_prior=%.3f  no tuning" % sigma)
    print(f"{'group':<12} {'k':>3} {'medAPE':>8} {'cover':>8} {'width':>8} {'bias':>8} {'n':>4}")
    for grp in ("R-test", "TRAIN-LOGO"):
        for k in KS:
            s = summary[grp][str(k)]
            print(
                f"{grp:<12} {k:3d} {100 * s['median_ape']:7.1f}% "
                f"{100 * s['coverage_p10_p90']:6.0f}% "
                f"{s['range_width']:8.2f} {s['bias']:8.2f} {s['n']:4d}"
            )
    for line in notes["lines"]:
        print(line)
    print(f"\nwrote {OUT / 'meter_update_real.json'}")
    print(f"wrote {OUT / 'meter_update_real.png'}")
    return payload


if __name__ == "__main__":
    pd.set_option("display.width", 200)
    run()
