"""Building and place (POI) features from Overture Maps, read over HTTP with DuckDB.

Overture combines Google Open Buildings, Microsoft footprints and OpenStreetMap
(buildings) and Meta/Microsoft/OSM places (POIs). Licence: ODbL / CDLA-Permissive.

For each site we count what lies within a radius of the site centre:
  buildings: count, total and mean footprint area, count of large (>=100 m2) footprints
  places:    total count and counts by use group (commerce, education, health, ...)
"""
from __future__ import annotations
import json, math, urllib.request
import duckdb
import pandas as pd

S3 = "s3://overturemaps-us-west-2/release/{rel}/theme={theme}/type={typ}/*"

PLACE_GROUPS = {
    "commerce": ["shop", "store", "market", "retail", "supermarket", "convenience", "grocery", "wholesale", "hardware", "boutique", "kiosk", "mobile_phone", "electronics"],
    "food": ["restaurant", "cafe", "bar", "pub", "food", "bakery", "butcher", "hotel", "lodging", "guest_house"],
    "services": ["salon", "barber", "beauty", "tailor", "repair", "mechanic", "car_", "auto", "garage", "laundry", "printing", "bank", "atm", "money", "financial", "mpesa", "agent"],
    "productive": ["mill", "farm", "agricultur", "factory", "manufactur", "workshop", "welding", "carpenter", "construction", "industrial", "fuel", "gas_station"],
    "education": ["school", "college", "university", "education", "kindergarten"],
    "health": ["hospital", "clinic", "health", "pharmacy", "medical", "dispensary", "doctor"],
    "civic": ["church", "mosque", "religious", "place_of_worship", "government", "police", "post_office", "community"],
}

def latest_release() -> str:
    cat = json.load(urllib.request.urlopen("https://stac.overturemaps.org/catalog.json", timeout=30))
    return [l["title"].split()[0] for l in cat["links"] if l.get("latest")][0]

def connect() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    for ext in ("httpfs", "spatial"):
        con.install_extension(ext); con.load_extension(ext)
    con.execute("SET s3_region='us-west-2'")
    return con

def _deg(radius_m: float, lat: float) -> tuple[float, float]:
    dlat = radius_m / 111_320
    return dlat, dlat / max(math.cos(math.radians(lat)), 0.1)

def _clusters(sites: pd.DataFrame, cell_deg: float = 1.0):
    key = (sites.lat // cell_deg).astype(int).astype(str) + "_" + (sites.lon // cell_deg).astype(int).astype(str)
    for _, g in sites.groupby(key):
        yield g

def site_features(sites: pd.DataFrame, radius_m: float = 1000, poi_radius_m: float = 2000,
                  release: str | None = None, con=None) -> pd.DataFrame:
    """sites: columns site_id, lat, lon. Returns one row of features per site_id."""
    rel = release or latest_release()
    con = con or connect()
    out = []
    for g in _clusters(sites):
        r = max(radius_m, poi_radius_m)
        dlat, dlon = _deg(r, g.lat.mean())
        xmin, xmax = g.lon.min() - dlon, g.lon.max() + dlon
        ymin, ymax = g.lat.min() - dlat, g.lat.max() + dlat
        con.register("s", g[["site_id", "lat", "lon"]])
        b = con.execute(f"""
            WITH bld AS (
              SELECT (bbox.xmin + bbox.xmax) / 2 AS x, (bbox.ymin + bbox.ymax) / 2 AS y,
                     ST_Area_Spheroid(ST_FlipCoordinates(geometry)) AS area_m2
              FROM read_parquet('{S3.format(rel=rel, theme="buildings", typ="building")}', hive_partitioning=1)
              WHERE bbox.xmin BETWEEN {xmin} AND {xmax} AND bbox.ymin BETWEEN {ymin} AND {ymax})
            SELECT s.site_id,
                   count(bld.x) AS bld_count,
                   coalesce(sum(bld.area_m2), 0) AS bld_area_m2,
                   coalesce(avg(bld.area_m2), 0) AS bld_mean_area_m2,
                   count(*) FILTER (WHERE bld.area_m2 >= 100) AS bld_large_count
            FROM s LEFT JOIN bld
              ON 2 * 6371000 * asin(sqrt(pow(sin(radians(bld.y - s.lat) / 2), 2)
                 + cos(radians(s.lat)) * cos(radians(bld.y)) * pow(sin(radians(bld.x - s.lon) / 2), 2))) <= {radius_m}
            GROUP BY s.site_id""").df()
        p = con.execute(f"""
            WITH pl AS (
              SELECT (bbox.xmin + bbox.xmax) / 2 AS x, (bbox.ymin + bbox.ymax) / 2 AS y,
                     lower(concat_ws(' ', basic_category, taxonomy.primary,
                                     array_to_string(taxonomy.hierarchy, ' '))) AS cat
              FROM read_parquet('{S3.format(rel=rel, theme="places", typ="place")}', hive_partitioning=1)
              WHERE bbox.xmin BETWEEN {xmin} AND {xmax} AND bbox.ymin BETWEEN {ymin} AND {ymax})
            SELECT s.site_id, pl.cat
            FROM s JOIN pl
              ON 2 * 6371000 * asin(sqrt(pow(sin(radians(pl.y - s.lat) / 2), 2)
                 + cos(radians(s.lat)) * cos(radians(pl.y)) * pow(sin(radians(pl.x - s.lon) / 2), 2))) <= {poi_radius_m}
            """).df()
        con.unregister("s")
        cnt = pd.DataFrame({"site_id": g.site_id.values})
        cnt["poi_count"] = cnt.site_id.map(p.groupby("site_id").size()).fillna(0).astype(int)
        for grp, words in PLACE_GROUPS.items():
            m = p.cat.fillna("").str.contains("|".join(words), regex=True).astype(bool)
            cnt[f"poi_{grp}"] = cnt.site_id.map(p[m].groupby("site_id").size()).fillna(0).astype(int)
        out.append(b.merge(cnt, on="site_id", how="outer"))
    return pd.concat(out, ignore_index=True)
