"""Site features from public data: `build_features(sites)` -> one row per site_id."""
from __future__ import annotations
import pathlib
import pandas as pd

CACHE = pathlib.Path(__file__).resolve().parents[2] / "data" / "features"

def build_features(sites: pd.DataFrame, name: str | None = None, refresh: bool = False) -> pd.DataFrame:
    """sites: DataFrame with site_id, lat, lon. Cached to data/features/<name>.parquet."""
    from .overture import site_features
    from .rasters import raster_features
    path = CACHE / f"{name}.parquet" if name else None
    if path and path.exists() and not refresh:
        return pd.read_parquet(path)
    f = site_features(sites).merge(raster_features(sites), on="site_id", how="outer")
    f = sites[["site_id", "lat", "lon"]].merge(f, on="site_id", how="left")
    if path:
        CACHE.mkdir(parents=True, exist_ok=True)
        f.to_parquet(path, index=False)
    return f
