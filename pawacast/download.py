"""Download the public rasters/vectors PawaCast uses into data/raw/.

Sources (all open licence):
- VIIRS annual night lights, 500 m, 2000-2024 (OpenGeoHub, Zenodo 17294744, CC-BY-4.0)
- GridFinder grid lines + LV-infrastructure raster (Arderne et al. 2020, Zenodo 3628142, CC-BY-4.0)
Buildings and places come from Overture Maps over HTTP (see features/overture.py).
"""
import pathlib, sys, requests

RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"

def zenodo_files(record):
    return {f["key"]: f["links"]["self"] for f in requests.get(f"https://zenodo.org/api/records/{record}", timeout=60).json()["files"]}

def fetch(url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        print("have", dest.name); return dest
    print("get ", dest.name)
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        tmp = dest.with_suffix(dest.suffix + ".part")
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
        tmp.replace(dest)
    return dest

def main(years=("2024", "2020", "2016")):
    ntl = zenodo_files(17294744)
    for y in years:
        key = next(k for k in ntl if k.startswith("nightlights.average_viirs") and f"_{y}0101_{y}1231_" in k)
        fetch(ntl[key], RAW / "viirs" / f"viirs_avg_{y}.tif")
    gf = zenodo_files(3628142)
    fetch(gf["grid.gpkg"], RAW / "gridfinder" / "grid.gpkg")
    fetch(gf["lv.tif"], RAW / "gridfinder" / "lv.tif")

if __name__ == "__main__":
    main(*sys.argv[1:])
