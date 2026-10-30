"""Cache Overture/VIIRS/GridFinder features for EVAL_PLAN set B (Olenarau, Tum, Omorate)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pawacast.features import build_features
from pawacast.targets.public import named_sites

if __name__ == "__main__":
    s = named_sites().query("eval_set == 'B'").dropna(subset=["lat"]).reset_index(drop=True)
    print(s[["site", "site_id", "country", "lat", "lon", "geo_conf"]].to_string(index=False))
    f = build_features(s, name="eval_setB", refresh=False)
    print(f[["site_id", "bld_count", "bld_mean_area_m2", "grid_dist_km", "ntl_2024_5km"]].to_string(index=False))
    print(f"rows={len(f)}")
