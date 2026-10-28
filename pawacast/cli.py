"""PawaCast for any location.

  python -m pawacast.cli --lat -1.784 --lon 36.053 --country KE [--customers 60] [--name Entasopia]

Prints the day-one range, the 24-month growth curve and a plain-language driver report
a lender can read. Optional --readings "6:4.2,7:4.8" applies meter readings (month:kWh/customer).
"""
from __future__ import annotations
import argparse
import pandas as pd
from .features import build_features
from .model.prior import estimate, SIGMA
from .model.growth import growth_curve, to_month, ANCHOR_MONTH
from .model.update import update

def report(lat, lon, country="KE", name="site", customers=None, readings=None) -> str:
    sites = pd.DataFrame({"site_id": [name], "lat": [lat], "lon": [lon]})
    f = build_features(sites).iloc[0].to_dict()
    e = estimate(f, country)
    k0 = to_month(1.0, 0) / to_month(1.0, ANCHOR_MONTH)
    curve = growth_curve(e.p50, SIGMA)
    L = [f"PawaCast demand estimate — {name} ({lat:.4f}, {lon:.4f}, {country})", ""]
    L.append(f"Mature demand (about 24 months after connection), kWh per customer per month:")
    L.append(f"  P10 {e.p10:5.1f}   P50 {e.p50:5.1f}   P90 {e.p90:5.1f}")
    L.append(f"Day one: P50 {e.p50 * k0:.1f} kWh/customer/month")
    if customers:
        L.append(f"Site total at 24 months for {customers} customers: "
                 f"{e.p10 * customers:,.0f} – {e.p90 * customers:,.0f} kWh/month (P50 {e.p50 * customers:,.0f})")
    L += ["", "Why this number (each factor multiplies the baseline):"]
    for n, m, why in e.drivers:
        L.append(f"  {n:<18} x{m:4.2f}  {why}" if n != "Country baseline" else f"  {n:<18}        {why}")
    L += ["", "Growth curve, kWh/customer/month:", "  month   P10   P50   P90"]
    for _, r in curve[curve.month.isin([0, 3, 6, 12, 18, 24])].iterrows():
        L.append(f"  {int(r.month):>5} {r.p10:5.1f} {r.p50:5.1f} {r.p90:5.1f}")
    if readings:
        u = update(e.p50, readings)
        L += ["", f"After {len(readings)} metered month(s): P10 {u['p10']:.1f}  P50 {u['p50']:.1f}  P90 {u['p90']:.1f} "
                  f"(range {1 - u['width_ratio']:.0%} narrower than the forecast)"]
    L += ["", "Range = 80% interval. Inputs: Overture Maps buildings/places, VIIRS night lights, GridFinder, AMDA benchmarks."]
    return "\n".join(L)

def main():
    a = argparse.ArgumentParser()
    a.add_argument("--lat", type=float, required=True); a.add_argument("--lon", type=float, required=True)
    a.add_argument("--country", default="KE"); a.add_argument("--name", default="site")
    a.add_argument("--customers", type=int); a.add_argument("--readings", default="")
    x = a.parse_args()
    reads = [(float(m), float(k)) for m, k in (p.split(":") for p in x.readings.split(",") if p)]
    print(report(x.lat, x.lon, x.country, x.name, x.customers, reads))

if __name__ == "__main__":
    main()
