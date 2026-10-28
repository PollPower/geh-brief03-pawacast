"""Night-light and grid features from local rasters/vectors in data/raw/.

  ntl_{y}_1km / ntl_{y}_5km : mean VIIRS radiance in a ~1 km / ~5 km window
  ntl_growth                : ntl_2024_5km - ntl_2016_5km (activity trend)
  lv_infra_1km              : GridFinder LV-infrastructure likelihood (mean in ~1 km)
  grid_dist_km              : distance to the nearest GridFinder MV/HV line
"""
from __future__ import annotations
import math, pathlib
import numpy as np
import pandas as pd
import rasterio
from rasterio.windows import from_bounds

RAW = pathlib.Path(__file__).resolve().parents[2] / "data" / "raw"

def _window_mean(src, lon, lat, half_m):
    dlat = half_m / 111_320
    dlon = dlat / max(math.cos(math.radians(lat)), 0.1)
    w = from_bounds(lon - dlon, lat - dlat, lon + dlon, lat + dlat, src.transform)
    a = src.read(1, window=w, boundless=True, fill_value=src.nodata if src.nodata is not None else 0, masked=True)
    a = a.astype("float64")
    return float(a.mean()) if a.count() else np.nan

def raster_features(sites: pd.DataFrame, years=("2016", "2024")) -> pd.DataFrame:
    out = pd.DataFrame({"site_id": sites.site_id.values})
    for y in years:
        p = RAW / "viirs" / f"viirs_avg_{y}.tif"
        if not p.exists():
            continue
        with rasterio.open(p) as src:
            out[f"ntl_{y}_1km"] = [_window_mean(src, x, y_, 500) for x, y_ in zip(sites.lon, sites.lat)]
            out[f"ntl_{y}_5km"] = [_window_mean(src, x, y_, 2500) for x, y_ in zip(sites.lon, sites.lat)]
    if {"ntl_2016_5km", "ntl_2024_5km"} <= set(out.columns):
        out["ntl_growth"] = out.ntl_2024_5km - out.ntl_2016_5km
    lv = RAW / "gridfinder" / "lv.tif"
    if lv.exists():
        with rasterio.open(lv) as src:
            out["lv_infra_1km"] = [_window_mean(src, x, y_, 500) for x, y_ in zip(sites.lon, sites.lat)]
    out["grid_dist_km"] = grid_distance_km(sites)
    return out

_GRID = None
def grid_distance_km(sites: pd.DataFrame) -> np.ndarray:
    """Distance from each site to the nearest GridFinder line, in km (UTM per site zone)."""
    global _GRID
    import geopandas as gpd
    p = RAW / "gridfinder" / "grid.gpkg"
    if not p.exists():
        return np.full(len(sites), np.nan)
    res = []
    for lon, lat in zip(sites.lon, sites.lat):
        d = 2.0  # search box in degrees (~220 km)
        g = gpd.read_file(p, bbox=(lon - d, lat - d, lon + d, lat + d))
        if g.empty:
            res.append(np.nan); continue
        zone = int((lon + 180) // 6) + 1
        crs = f"EPSG:{32600 + zone if lat >= 0 else 32700 + zone}"
        pt = gpd.GeoSeries(gpd.points_from_xy([lon], [lat]), crs=4326).to_crs(crs).iloc[0]
        res.append(g.to_crs(crs).distance(pt).min() / 1000)
    return np.array(res)
