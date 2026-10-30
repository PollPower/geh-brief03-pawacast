"""Deck-card growth figure. Frozen TRAIN slope. Transparent background."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from pawacast.model.growth import observed_curve
from pawacast.targets.renewvia import load_site_months

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results"
SUN, FLARE, PLASMA, ASH = "#FFD93D", "#FF6B35", "#FF3366", "#0D0D0D"


def main():
    g = json.loads((OUT / "cv_train.json").read_text(encoding="utf-8"))["growth"]
    curve = observed_curve(g, months=range(0, 25))
    sm = load_site_months(role="train")
    sm = sm[(sm.kwh_cust_month > 0) & (sm.months_since_power_on.between(0, 24))]

    fig, ax = plt.subplots(figsize=(10.0, 5.4), dpi=160)
    fig.patch.set_alpha(0.0)
    ax.set_facecolor("none")
    for _, gg in sm.groupby("projectName"):
        gg = gg.sort_values("months_since_power_on")
        ax.plot(gg.months_since_power_on, gg.kwh_cust_month, color="#bbbbbb", lw=0.9, alpha=0.55)
    ax.fill_between(curve.month, curve.p10, curve.p90, color=FLARE, alpha=0.32, linewidth=0, zorder=2)
    ax.plot(curve.month, curve.p50, color=PLASMA, lw=2.8, zorder=3, label="median (frozen slope)")
    ax.axvline(12, color="#dddddd", lw=0.8, zorder=1)
    ax.set_xlim(0, 24)
    ax.set_ylim(0, 22)
    ax.set_xlabel("months since connection", color=ASH)
    ax.set_ylabel("kWh per customer per month", color=ASH)
    ax.tick_params(colors=ASH)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    for sp in ("left", "bottom"):
        ax.spines[sp].set_color(ASH)
    ax.set_title("Demand after connection", color=ASH, loc="left", fontsize=14, pad=10)
    fig.text(0.04, 0.02, "most sites flat after year 1", color=ASH, fontsize=11, style="italic")
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    path = OUT / "growth_curve_deck.png"
    fig.savefig(path, dpi=160, transparent=True)
    plt.close(fig)
    print(f"wrote {path}  slope={g['slope']:.4f}  annual_12_24={100 * g['annual_12_24']:.1f}%")


if __name__ == "__main__":
    main()
