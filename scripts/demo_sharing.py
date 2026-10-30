"""Build TRAIN-only shared records and show one example plus Laplace noise vs n.

Never opens held-out test-site consumption. Label is Tier 2 Renewvia CC BY-SA 4.0,
not SIMULATED: these are real TRAIN aggregates with k-anonymity, rounding, and noise.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pawacast.sharing.aggregate import (
    DEFAULT_EPSILON,
    KWH_CLIP,
    TIER2_RENEWVIA_LABEL,
    build_train_records,
    noise_table,
    write_records,
)
from pawacast.sharing.validate import validate_records

OUT_RECORDS = ROOT / "results" / "sharing_records.json"
OUT_DEMO = ROOT / "results" / "sharing_demo.json"


def _example(records: list[dict]) -> dict:
    """Prefer an Olkiramatian-area cell; else the median-n record."""
    olki = [
        r
        for r in records
        if "renewvia_olkiramatian" in r.get("proof_ref", "")
        and 12 <= r["months_since_power_on"] <= 24
    ]
    if olki:
        olki.sort(key=lambda r: abs(r["months_since_power_on"] - 18))
        return olki[0]
    mid = sorted(records, key=lambda r: r["n_customers"])[len(records) // 2]
    return mid


def main() -> None:
    print("building TRAIN shared records (test sites sealed)", flush=True)
    records = build_train_records(refresh=False)
    validate_records(records)
    write_records(records, OUT_RECORDS)
    ns = sorted(r["n_customers"] for r in records)
    example = _example(records)
    table = noise_table()
    demo = {
        "label": TIER2_RENEWVIA_LABEL,
        "n_records": len(records),
        "n_h3_cells": len({r["h3_res6"] for r in records}),
        "n_customers_min": ns[0] if ns else None,
        "n_customers_median": ns[len(ns) // 2] if ns else None,
        "n_customers_max": ns[-1] if ns else None,
        "epsilon": DEFAULT_EPSILON,
        "kwh_clip": KWH_CLIP,
        "example_record": example,
        "noise_vs_n": table,
        "publish_threshold": 25,
        "epsilon_period": "month",
        "yearly_epsilon_budget": 12.0,
        "note": (
            "Clip 20 kWh/customer/month. Laplace scale for the mean is (clip/n)/ε. "
            "Per-release ε = 1.0 (one month). Basic composition: 12 monthly releases "
            "spend yearly_epsilon_budget = 12. At n=10 typical |noise| is 2.0 kWh "
            "(40% of a 5 kWh mean) so we do not publish below n=25, where typical "
            "|noise| is 0.8 kWh (16%). Compact proves exact sum and count; the "
            "published mean is that ratio after this noise."
        ),
    }
    OUT_DEMO.parent.mkdir(parents=True, exist_ok=True)
    OUT_DEMO.write_text(
        json.dumps(demo, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"wrote {OUT_RECORDS}  records={len(records)}", flush=True)
    print(f"wrote {OUT_DEMO}", flush=True)
    print("example record:", flush=True)
    print(json.dumps(example, indent=2), flush=True)
    print("noise vs n (typical |noise| on the mean, clip=20, ε=1):", flush=True)
    for row in table:
        print(
            f"  n={row['n_customers']:4d}  scale={row['laplace_scale']:7.3f} kWh  "
            f"|noise|/mean={row['typical_abs_noise_over_mean']:.2f}",
            flush=True,
        )


if __name__ == "__main__":
    main()
