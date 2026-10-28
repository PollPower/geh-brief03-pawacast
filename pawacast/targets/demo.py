"""Demo locations for the sprint video (chosen 28 Oct 2026). Not test sites: no measured demand.

Coordinates are village/town centres from OpenStreetMap (Nominatim). Maji Moto is the village
centre; replace with the exact PollPower pilot coordinates when confirmed.
"""
import pandas as pd

DEMO_SITES = pd.DataFrame([
    # site_id,             name,                         lat,       lon,      country, customers, role
    ("demo_ewaso_ngiro",  "Ewaso Ngiro, Narok",         -1.15391, 35.76177, "KE", None, "busy trading village"),
    ("demo_narok_town",   "Narok town",                 -1.08869, 35.87149, "KE", None, "county hub (on the national grid)"),
    ("demo_maji_moto",    "Maji Moto, Narok (PollPower pilot)", -1.33866, 35.71253, "KE", 100, "PollPower 100-household pilot"),
], columns=["site_id", "name", "lat", "lon", "country", "customers", "role"])
