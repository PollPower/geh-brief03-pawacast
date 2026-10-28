"""Probe reachability of raster/vector sources (HEAD-ish requests only)."""
import requests
URLS = {
    "gridfinder zenodo record": "https://zenodo.org/api/records/3628142",
    "EOG VNL annual v2.2 index": "https://eogdata.mines.edu/nighttime_light/annual/v22/2023/",
    "Black Marble LAADS VNP46A4": "https://ladsweb.modaps.eosdis.nasa.gov/archive/allData/5200/VNP46A4/",
    "WorldPop covariates VIIRS": "https://data.worldpop.org/GIS/Covariates/Global_2015_2030/",
    "Light Every Night S3": "https://globalnightlight.s3.amazonaws.com/?list-type=2&max-keys=5",
    "Planetary Computer STAC": "https://planetarycomputer.microsoft.com/api/stac/v1/collections",
    "Energy Access Explorer": "https://energyaccessexplorer.org/",
    "GEP explorer": "https://electrifynow.energydata.info/",
    "energydata.info API": "https://energydata.info/api/3/action/package_search?q=mini-grid&rows=5",
}
for k, u in URLS.items():
    try:
        r = requests.get(u, timeout=25, allow_redirects=True, stream=True)
        snippet = r.raw.read(400, decode_content=True).decode("utf-8", "ignore").replace("\n", " ")
        print(f"{k}: {r.status_code} {r.url[:90]} | {snippet[:220]}")
    except Exception as e:
        print(f"{k}: ERR {str(e)[:150]}")
