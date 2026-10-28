"""Look for an openly downloadable annual VIIRS night-lights raster."""
import requests
def ckan(q):
    r = requests.get("https://energydata.info/api/3/action/package_search", params={"q": q, "rows": 8}, timeout=30).json()
    for p in r["result"]["results"]:
        res = [(x.get("format"), x.get("url")) for x in p.get("resources", [])][:3]
        print("-", p["title"][:80], "|", p.get("license_id"), "|", res)
print("energydata.info: night lights"); ckan("nighttime lights VIIRS")
print("\nZenodo:")
r = requests.get("https://zenodo.org/api/records", params={"q": "VIIRS annual nighttime light global", "size": 8, "sort": "mostrecent"}, timeout=30).json()
for h in r["hits"]["hits"]:
    files = [(f["key"], round(f["size"] / 1e6)) for f in h.get("files", [])][:4]
    print("-", h["id"], h["metadata"]["title"][:90], h["metadata"].get("license", {}).get("id"), files)
