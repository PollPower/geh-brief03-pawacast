"""Plain-language driver ranking from the frozen model. No refit."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from pawacast.model.growth import observed_multiplier
from pawacast.model.loglinear import REF_BLD, REF_MONTH, load_frozen
from pawacast.model.prior import country_baseline

OUT = Path(__file__).resolve().parents[1] / "results"


def main():
    model, frozen = load_frozen()
    beta = float(frozen["beta_bld"])
    slope = float(frozen["growth_slope"])
    ke, ke_src = country_baseline("KE")
    ng, ng_src = country_baseline("NG")
    cv = pd.read_csv(OUT / "cv_train_sites.csv", encoding="utf-8")
    bld_mult = cv.x_mapped_buildings
    # Kalobeyei vs OOF P50 (LOGO, never uses test)
    kal = cv[cv.site.str.startswith("Kalobeyei")]
    kal_rows = []
    for _, r in kal.iterrows():
        kal_rows.append(
            {
                "site": r.site,
                "actual": float(r.actual),
                "p50_logo": float(r.p50),
                "ratio": float(r.actual / r.p50),
            }
        )
    payload = {
        "model": "frozen day-one log-linear; commit in results/model_freeze.txt",
        "ranked": [
            {
                "rank": 1,
                "name": "Country / region baseline",
                "plain": (
                    f"Where the site is matters most. A typical Kenyan village starts at "
                    f"{ke:.1f} kWh per customer per month ({ke_src}); a typical Nigerian "
                    f"village starts at {ng:.1f} kWh ({ng_src}). That is a {ng / ke:.1f}× gap "
                    "before any buildings are counted."
                ),
                "ke_kwh": ke,
                "ng_kwh": ng,
                "ratio_ng_over_ke": ng / ke,
            },
            {
                "rank": 2,
                "name": "Settlement size (mapped buildings)",
                "plain": (
                    f"Each extra mapped building within 1 km raises demand slowly "
                    f"(elasticity {beta:.2f} on log buildings vs a village of {int(REF_BLD)}). "
                    f"Doubling the building count multiplies demand by {2 ** beta:.2f}×. "
                    f"On TRAIN, that multiplier ran from {bld_mult.min():.2f}× to {bld_mult.max():.2f}×."
                ),
                "beta_bld": beta,
                "ref_buildings": REF_BLD,
                "double_buildings_multiplier": 2 ** beta,
                "train_multiplier_min": float(bld_mult.min()),
                "train_multiplier_max": float(bld_mult.max()),
            },
            {
                "rank": 3,
                "name": "Months since connection",
                "plain": (
                    "Demand grows a little after power-on, then flattens. With the frozen "
                    f"slope, month 0 is {float(observed_multiplier(0, slope)):.2f}× the month-18 "
                    f"level, month 12 is {float(observed_multiplier(12, slope)):.2f}×, and month 24 "
                    f"is {float(observed_multiplier(24, slope)):.2f}×. That is about "
                    f"{100 * frozen['growth_annual_0_24']:.0f}% per year over the first two years "
                    f"and only {100 * frozen['growth_annual_12_24']:.0f}% per year after year 1."
                ),
                "slope": slope,
                "mult_month_0": float(observed_multiplier(0, slope)),
                "mult_month_12": float(observed_multiplier(12, slope)),
                "mult_month_24": float(observed_multiplier(24, slope)),
                "annual_0_24": frozen["growth_annual_0_24"],
                "annual_12_24": frozen["growth_annual_12_24"],
            },
        ],
        "exception": {
            "finding": (
                "Business-heavy settlements run about 3× above the model. "
                "Kalobeyei Town used 14.6 kWh vs a 4.5 kWh forecast (3.3×); "
                "Kalobeyei Settlement used 19.7 vs 4.8 (4.1×). "
                "The frozen model has no business-mix term — mapped buildings and country "
                "do not see shops, clinics and markets in a refugee settlement."
            ),
            "sites": kal_rows,
        },
    }
    path = OUT / "top_drivers.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
