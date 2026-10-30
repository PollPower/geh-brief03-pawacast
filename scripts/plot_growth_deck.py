"""Deck-card growth figure. Frozen TRAIN slope. Transparent background."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from pawacast.model.growth import observed_curve

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results"
SUN, FLARE, MUTED = "#FFD93D", "#FF6B35", "#888888"
W, H, DPI = 1600, 900, 100
PX_TO_PT = 72.0 / DPI


def main():
    g = json.loads((OUT / "cv_train.json").read_text(encoding="utf-8"))["growth"]
    curve = observed_curve(g, months=range(0, 25))
    p50_0 = float(curve.loc[curve.month == 0, "p50"].iloc[0])
    p50_12 = float(curve.loc[curve.month == 12, "p50"].iloc[0])
    p50_24 = float(curve.loc[curve.month == 24, "p50"].iloc[0])
    p90_24 = float(curve.loc[curve.month == 24, "p90"].iloc[0])

    plt.rcParams.update({"font.family": "sans-serif", "font.size": 13})
    fig, ax = plt.subplots(figsize=(W / DPI, H / DPI), dpi=DPI)
    fig.patch.set_alpha(0.0)
    ax.set_facecolor("none")

    ax.fill_between(
        curve.month, curve.p10, curve.p90,
        color=FLARE, alpha=0.25, linewidth=0, edgecolor="none", zorder=2,
    )
    ax.plot(curve.month, curve.p50, color=SUN, lw=4 * PX_TO_PT, solid_capstyle="butt", zorder=3)

    ax.annotate(
        f" {p50_0:.1f}", xy=(0, p50_0), xytext=(0, 6),
        textcoords="offset points", color="#FFFFFF", fontsize=14,
        ha="left", va="bottom", fontfamily="sans-serif", zorder=4,
    )
    ax.annotate(
        f"{p50_24:.1f}", xy=(24, p50_24), xytext=(0, 6),
        textcoords="offset points", color="#FFFFFF", fontsize=14,
        ha="right", va="bottom", fontfamily="sans-serif", zorder=4,
    )
    ax.annotate(
        "80% range", xy=(24, p90_24), xytext=(0, 6),
        textcoords="offset points", color=MUTED, fontsize=12,
        ha="right", va="bottom", fontfamily="sans-serif", zorder=4,
    )

    ax.set_xlim(0, 24)
    ax.set_ylim(0, 10)
    ax.set_xticks([0, 6, 12, 18, 24])
    ax.set_yticks([0, 5, 10])
    ax.set_xlabel("Months after connection", color=MUTED, fontsize=13, fontfamily="sans-serif")
    ax.set_ylabel("kWh per customer per month", color=MUTED, fontsize=13, fontfamily="sans-serif")
    ax.tick_params(colors=MUTED, labelsize=13, width=1)
    for lab in ax.get_xticklabels() + ax.get_yticklabels():
        lab.set_fontfamily("sans-serif")
        lab.set_fontsize(13)
        lab.set_color(MUTED)
    ax.grid(False)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    for sp in ("left", "bottom"):
        ax.spines[sp].set_color(MUTED)

    fig.subplots_adjust(left=0.08, right=0.97, bottom=0.12, top=0.96)
    path = OUT / "growth_curve_deck_dark.png"
    fig.savefig(path, dpi=DPI, transparent=True, facecolor="none")
    plt.close(fig)
    print(f"wrote {path}")
    print(f"P50 month 0={p50_0:.6f}  12={p50_12:.6f}  24={p50_24:.6f}")
    print(f"slope={g['slope']:.6f}")


if __name__ == "__main__":
    main()
