"""Geocode the Blodgett et al. (2017) Kenyan mini-grid villages with Nominatim (OSM)."""
import time, requests
import sys
NAMES = sys.argv[1:] or ["Barsaloi", "Enkoireroi", "Entesopia", "Marti", "Merile", "Namba Koloo", "Olenarau", "Opiroi"]
H = {"User-Agent": "PawaCast/0.1 (dev@pollpower.energy)"}
for n in NAMES:
    try:
        r = requests.get("https://nominatim.openstreetmap.org/search",
                         params={"q": n, "countrycodes": "ke", "format": "jsonv2", "limit": 4, "addressdetails": 1},
                         headers=H, timeout=30).json()
        print(n, "->", [(x["lat"][:7], x["lon"][:7], x.get("addresstype"), x["address"].get("county") or x["address"].get("state")) for x in r] or "none")
    except Exception as e:
        print(n, "ERR", str(e)[:120])
    time.sleep(1.2)
