"""Probe: can we read Overture buildings + places for a small bbox over HTTP?"""
import time, duckdb
con = duckdb.connect()
for ext in ("httpfs", "spatial"):
    con.install_extension(ext); con.load_extension(ext)
con.execute("SET s3_region='us-west-2'")
import json, urllib.request
cat = json.load(urllib.request.urlopen("https://stac.overturemaps.org/catalog.json"))
REL = [l["title"].split()[0] for l in cat["links"] if l.get("latest")][0]
print("release", REL)
# ~2 km box around Maji Moto-ish test point (Narok County)
lon, lat, d = 35.85, -1.30, 0.01
bb = dict(xmin=lon - d, xmax=lon + d, ymin=lat - d, ymax=lat + d)
for theme, typ in (("buildings", "building"), ("places", "place")):
    t = time.time()
    try:
        n = con.execute(f"""
          SELECT count(*) FROM read_parquet('s3://overturemaps-us-west-2/release/{REL}/theme={theme}/type={typ}/*', hive_partitioning=1)
          WHERE bbox.xmin BETWEEN {bb['xmin']} AND {bb['xmax']} AND bbox.ymin BETWEEN {bb['ymin']} AND {bb['ymax']}
        """).fetchone()[0]
        print(theme, n, f"{time.time()-t:.1f}s")
    except Exception as e:
        print(theme, "ERR", str(e)[:300])
