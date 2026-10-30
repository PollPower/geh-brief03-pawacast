"""PawaCast web app. Frozen day-one model; meter update v2.

Coordinates typed or clicked by users are shown on screen and not written to disk.
"""
from __future__ import annotations

import json
import math
import pathlib
from datetime import date

import altair as alt
import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

ROOT = pathlib.Path(__file__).resolve().parents[1]
import sys

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pawacast.features import build_features
from pawacast.model.growth import observed_multiplier
from pawacast.model.loglinear import load_frozen
from pawacast.model.prior import Estimate
from pawacast.model.update_v2 import update_v2
from pawacast.sharing.ingest import blend_prior, nearby_records, load_records
from pawacast.targets.demo import DEMO_SITES

SUN, FLARE, PLASMA, ASH = "#FFD93D", "#FF6B35", "#FF3366", "#0D0D0D"
FREEZE = "c3df2c8"

st.set_page_config(page_title="PawaCast · PollPower", layout="wide", page_icon="⚡")

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@400;600&family=Space+Mono:wght@400;700&display=swap');
html, body, [class*="css"] {{ font-family: Inter, sans-serif; color: {ASH}; }}
h1, h2, h3, .bebas {{ font-family: 'Bebas Neue', sans-serif; letter-spacing: 0.04em; }}
.mono {{ font-family: 'Space Mono', monospace; }}
.pp-bar {{
  background: linear-gradient(90deg, {SUN} 0%, {FLARE} 55%, {PLASMA} 100%);
  padding: 0.85rem 1.2rem; margin: -1rem -1rem 1rem -1rem; color: {ASH};
}}
.pp-bar h1 {{ margin: 0; font-size: 2.1rem; }}
.pp-bar .sub {{ font-family: 'Space Mono', monospace; font-size: 0.78rem; }}
.answer {{
  background: #fff8e8; border-left: 6px solid {PLASMA}; padding: 0.9rem 1rem; margin: 0.4rem 0 1rem 0;
}}
.answer .big {{ font-family: 'Bebas Neue', sans-serif; font-size: 2.6rem; line-height: 1; color: {ASH}; }}
.answer .range {{ font-family: 'Space Mono', monospace; font-size: 0.95rem; }}
.sim {{ background: {SUN}; color: {ASH}; font-family: 'Space Mono', monospace;
       font-size: 0.72rem; padding: 0.1rem 0.4rem; }}
footer {{ font-size: 0.78rem; color: #555; }}
</style>
"""


@st.cache_resource
def _model():
    return load_frozen()


def _json(name: str):
    p = ROOT / "results" / name
    return json.loads(p.read_text(encoding="utf-8"))


@st.cache_data
def _cal(mtime: float):
    j = _json("meter_update_v2.json")
    return {
        "noise": j["v2"]["noise"],
        "projection": j["v2"]["projection"],
        "scale": j["v2"]["scale"],
    }


@st.cache_data
def _eval(mtime: float):
    return _json("eval_final.json")


@st.cache_data
def _cost(mtime: float):
    return _json("cost_estimate.json")


@st.cache_data
def _nearby_blend(lat: float, lon: float, p10: float, p50: float, p90: float, sigma: float, mtime: float):
    """Shift the on-screen prior with shared records. Frozen β is not refit."""
    recs = load_records()
    nearby = nearby_records(recs, lat, lon, radius_km=80.0)
    est = Estimate(p10=p10, p50=p50, p90=p90, baseline=0.0, drivers=[])
    blended = blend_prior(est, nearby, sigma)
    return {
        "n_nearby": len(nearby),
        "blended": blended,
        "dist_note": "80 km radius (Olkiramatian is ~77 km from Maji Moto)",
    }


def _mtime(name: str) -> float:
    p = ROOT / "results" / name
    return p.stat().st_mtime if p.exists() else 0.0


@st.cache_data
def _demo_features():
    demo = DEMO_SITES.copy()
    return build_features(demo, name="demo_sites"), demo


def curve_frame(p10, p50, p90, slope, months=range(0, 25)) -> pd.DataFrame:
    m = list(months)
    mult = observed_multiplier(m, slope)
    return pd.DataFrame({"month": m, "p10": p10 * mult, "p50": p50 * mult, "p90": p90 * mult})


def growth_chart(prior: pd.DataFrame, post: pd.DataFrame | None) -> alt.Chart:
    band = (
        alt.Chart(prior)
        .mark_area(opacity=0.28, color="#bbbbbb")
        .encode(x=alt.X("month:Q", title="months since connection"), y="p10:Q", y2="p90:Q")
    )
    line = (
        alt.Chart(prior)
        .mark_line(color="#888888", strokeDash=[4, 3])
        .encode(x="month:Q", y=alt.Y("p50:Q", title="kWh / customer / month"))
    )
    layers = [band, line]
    if post is not None:
        layers += [
            alt.Chart(post).mark_area(opacity=0.35, color=FLARE).encode(x="month:Q", y="p10:Q", y2="p90:Q"),
            alt.Chart(post).mark_line(color=PLASMA, strokeWidth=3).encode(x="month:Q", y="p50:Q"),
        ]
    return alt.layer(*layers).properties(height=220).configure_view(strokeWidth=0)


def html_report(name, country, lat, lon, n, est, site_p10, site_p50, site_p90, feats, ev) -> str:
    bld = int(feats.get("bld_count") or 0)
    h = ev["headline"]
    drivers = "".join(
        f"<tr><td>{n_}</td><td class='mono'>×{m:.2f}</td><td>{why}</td></tr>"
        for n_, m, why in est.drivers
    )
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>PawaCast · {name}</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@400;600&family=Space+Mono&display=swap');
body {{ font-family: Inter, sans-serif; color: {ASH}; margin: 24px; }}
.bar {{ background: linear-gradient(90deg, {SUN}, {FLARE}, {PLASMA}); height: 10px; }}
h1 {{ font-family: 'Bebas Neue', sans-serif; font-size: 2.4rem; margin: 0.4rem 0; }}
.mono {{ font-family: 'Space Mono', monospace; }}
table {{ width: 100%; border-collapse: collapse; }}
td {{ padding: 4px 8px; border-bottom: 1px solid #eee; }}
.foot {{ font-size: 0.8rem; color: #666; margin-top: 1.5rem; }}
</style></head><body>
<div class="bar"></div>
<p class="mono">POLL POWER · PAWACAST SITE REPORT · {date.today().isoformat()} · {FREEZE}</p>
<h1>{name}</h1>
<p>{country} · {lat:.4f}, {lon:.4f} · {bld} buildings within 1 km</p>
<h2>1. The answer</h2>
<p>Expected demand at 24 months: <b>{est.p50:.1f}</b> kWh / customer / month</p>
<p>80% range: {est.p10:.1f} – {est.p90:.1f}</p>
<p>For {n} customers: {site_p10:,.0f} – {site_p90:,.0f} kWh / month (most likely {site_p50:,.0f})</p>
<p>We expect this site to use about {est.p50:.1f} kWh per customer per month, most likely between {est.p10:.1f} and {est.p90:.1f}.</p>
<h2>2. Why this number</h2>
<table>{drivers}</table>
<h2>5. How sure we are</h2>
<p>Tested on {h['n']} held-out Renewvia sites (R-test): median error {100*h['median_ape']:.0f}%,
{100*h['coverage_p10_p90']:.0f}% of sites inside the day-one range. TRAIN leave-one-group-out median error 46%.</p>
<p class="foot">Sources: Overture Maps · VIIRS · GridFinder · AMDA. Not a guarantee of revenue. Model {FREEZE}.</p>
</body></html>"""


def apply_site(site_id: str, name: str, lat: float, lon: float, country: str, customers, feats: dict):
    st.session_state.site_id = site_id
    st.session_state.name = name
    st.session_state.lat = float(lat)
    st.session_state.lon = float(lon)
    st.session_state.country = country
    st.session_state.customers = int(customers or 100)
    st.session_state.feats = feats
    st.session_state.readings = []


def init_state():
    if "site_id" in st.session_state:
        return
    feats, demo = _demo_features()
    row = demo[demo.site_id == "demo_maji_moto"].iloc[0]
    f = feats[feats.site_id == "demo_maji_moto"].iloc[0].to_dict()
    apply_site(row.site_id, row["name"], row.lat, row.lon, row.country, row.customers, f)


def main():
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(
        '<div class="pp-bar"><h1>POLL POWER · PAWACAST</h1>'
        '<div class="sub">Demand before you build</div></div>',
        unsafe_allow_html=True,
    )
    init_state()
    model, frozen = _model()
    cal = _cal(_mtime("meter_update_v2.json"))
    ev = _eval(_mtime("eval_final.json"))
    feats_demo, demo = _demo_features()
    slope = float(frozen["growth_slope"])
    sigma = float(frozen["sigma"])

    left, right = st.columns([1.15, 1])
    with left:
        m = folium.Map(location=[-1.22, 35.78], zoom_start=9, tiles="OpenStreetMap")
        for _, r in demo.iterrows():
            folium.CircleMarker(
                [r.lat, r.lon], radius=8, color=PLASMA, fill=True, fill_color=SUN,
                fill_opacity=0.95, popup=r["name"], tooltip=r["name"],
            ).add_to(m)
        folium.CircleMarker(
            [st.session_state.lat, st.session_state.lon], radius=11,
            color=ASH, fill=False, weight=2,
        ).add_to(m)
        clicked = st_folium(m, height=420, width=None, returned_objects=["last_clicked", "last_object_clicked_tooltip"])
        tip = (clicked or {}).get("last_object_clicked_tooltip")
        if tip:
            hit = demo[demo["name"] == tip]
            if len(hit) and hit.iloc[0].site_id != st.session_state.site_id:
                r = hit.iloc[0]
                f = feats_demo[feats_demo.site_id == r.site_id].iloc[0].to_dict()
                apply_site(r.site_id, r["name"], r.lat, r.lon, r.country, r.customers, f)
                st.rerun()
        lc = (clicked or {}).get("last_clicked")
        if lc and abs(lc["lat"] - st.session_state.lat) > 1e-4:
            with st.spinner("fetching buildings… 30–80 s"):
                sites = pd.DataFrame(
                    {"site_id": ["click"], "lat": [lc["lat"]], "lon": [lc["lng"]]}
                )
                f = build_features(sites).iloc[0].to_dict()
            apply_site("click", "Dropped pin", lc["lat"], lc["lng"], st.session_state.country, st.session_state.customers, f)
            st.rerun()

    with right:
        st.markdown(f"<div class='mono'>SITE</div>", unsafe_allow_html=True)
        st.markdown(f"<h2 class='bebas' style='margin-top:0'>{st.session_state.name}</h2>", unsafe_allow_html=True)
        st.caption(f"{st.session_state.lat:.4f}, {st.session_state.lon:.4f} · "
                   f"{float(st.session_state.feats.get('grid_dist_km') or 0):.1f} km to grid")
        c1, c2 = st.columns(2)
        st.session_state.customers = c1.number_input("Customers", min_value=10, max_value=5000,
                                                     value=int(st.session_state.customers), step=10)
        st.session_state.country = c2.selectbox("Country", ["KE", "NG", "ET"],
                                                index=["KE", "NG", "ET"].index(st.session_state.country)
                                                if st.session_state.country in ("KE", "NG", "ET") else 0)
        est18 = model.estimate(st.session_state.feats, st.session_state.country)
        k24 = float(observed_multiplier(24, slope))
        p10_24, p50_24, p90_24 = est18.p10 * k24, est18.p50 * k24, est18.p90 * k24
        n = int(st.session_state.customers)
        st.markdown(
            f"<div class='answer'><div class='mono'>EXPECTED DEMAND AT 24 MONTHS</div>"
            f"<div class='big'>{p50_24:.1f}</div>"
            f"<div>kWh / household / month</div>"
            f"<div class='range'>most likely {p10_24:.1f} – {p90_24:.1f}</div>"
            f"<div class='range'>{n} households: {p10_24*n:,.0f} – {p90_24*n:,.0f} kWh/mo"
            f" (most likely {p50_24*n:,.0f})</div></div>",
            unsafe_allow_html=True,
        )
        st.markdown("<div class='mono'>WHY THIS NUMBER</div>", unsafe_allow_html=True)
        drv = pd.DataFrame(
            [{"driver": n_, "x": m, "why": why} for n_, m, why in est18.drivers]
        )
        st.altair_chart(
            alt.Chart(drv).mark_bar(color=FLARE).encode(
                y=alt.Y("driver:N", sort=None, title=None),
                x=alt.X("x:Q", title="multiplier", scale=alt.Scale(domain=[0, max(1.2, float(drv.x.max()) * 1.15)])),
                tooltip=["driver", "x", "why"],
            ).properties(height=140),
            use_container_width=True,
        )
        for n_, m, why in est18.drivers:
            st.caption(f"**{n_}** ×{m:.2f} — {why}")

    st.markdown("<div class='mono'>GROWTH AFTER CONNECTION</div>", unsafe_allow_html=True)
    prior_c = curve_frame(est18.p10, est18.p50, est18.p90, slope)
    post_c = None
    readings = st.session_state.readings
    if readings:
        u = update_v2(est18.p50, readings, cal, sigma, slope)
        post_c = curve_frame(u["p10"], u["p50"], u["p90"], slope)
    st.altair_chart(growth_chart(prior_c, post_c), use_container_width=True)

    st.markdown("<div class='mono'>METERS CORRECT</div>", unsafe_allow_html=True)
    st.markdown("<span class='sim'>SIMULATED</span> readings for the demo — not signed PollPower meters.",
                unsafe_allow_html=True)
    a, b, c = st.columns([1, 1, 0.6])
    month = a.number_input("month", min_value=0, max_value=48, value=3, step=1)
    kwh = b.number_input("kWh / household", min_value=0.1, max_value=80.0, value=4.2, step=0.1)
    if c.button("Add"):
        st.session_state.readings = list(readings) + [(float(month), float(kwh))]
        st.rerun()
    if st.session_state.readings:
        u = update_v2(est18.p50, st.session_state.readings, cal, sigma, slope)
        wr = (u["p90"] / u["p10"]) / (est18.p90 / est18.p10)
        st.write(
            f"After **{len(st.session_state.readings)}** SIMULATED month(s): "
            f"most likely **{u['p50']:.1f}** ({u['p10']:.1f} – {u['p90']:.1f}). "
            f"Range is {1-wr:.0%} narrower than the forecast."
        )
        st.dataframe(
            pd.DataFrame(st.session_state.readings, columns=["month", "kWh/customer"]),
            hide_index=True, use_container_width=True,
        )
        if st.button("Clear readings"):
            st.session_state.readings = []
            st.rerun()

    report = html_report(
        st.session_state.name, st.session_state.country,
        st.session_state.lat, st.session_state.lon, n,
        type(est18)(p10=p10_24, p50=p50_24, p90=p90_24,
                    baseline=est18.baseline, drivers=est18.drivers),
        p10_24 * n, p50_24 * n, p90_24 * n, st.session_state.feats, ev,
    )
    st.download_button("Download lender report (HTML)", data=report,
                       file_name="pawacast-report.html", mime="text/html")
    with st.expander("How tested"):
        h = ev["headline"]
        st.write(
            f"Headline **R-test** (5 never-seen Renewvia sites): median error "
            f"**{100*h['median_ape']:.0f}%**, {100*h['coverage_p10_p90']:.0f}% inside the day-one range, "
            f"width {h['range_width']:.1f}. TRAIN leave-one-group-out: 46% median error, 83% coverage. "
            f"Meter update v2 is calibrated to ~80% coverage on TRAIN-LOGO; R-test update coverage is "
            f"post-hoc and still weak. Frozen model `{FREEZE}`."
        )

    st.markdown("<div class='mono'>SHARE YOUR METER DATA</div>", unsafe_allow_html=True)
    st.markdown(
        "Operators share a **site-month record**, not a customer list. "
        "PawaCast uses nearby records to shift a new site’s prior; the site’s own "
        "meters still correct the range."
    )
    c_share, c_priv = st.columns(2)
    with c_share:
        st.markdown("**What is shared**")
        st.markdown(
            "- H3 cell (~36 km²), not the pin\n"
            "- Month, and months since power-on\n"
            "- Customer count, rounded to 5 (only if ≥ 10)\n"
            "- Mean / P10 / P50 / P90 kWh per customer\n"
            "- Business share, rounded to 10%\n"
            "- A proof that sum and count match the committed meters"
        )
    with c_priv:
        st.markdown("**What stays private**")
        st.markdown(
            "- Exact coordinates\n"
            "- Customer names, phones, meter IDs\n"
            "- Any one customer’s kWh\n"
            "- Tariffs, revenue, margins, payment history"
        )
    st.markdown(
        "**Tier 1 — PollPower-metered.** Readings are signed on the chip; the proof "
        "is against EBT settlement. Strongest weight.\n\n"
        "**Tier 2 — other operators.** Export from SteamaCo / SparkMeter / Odyssey, "
        "signed by the operator. The proof matches the commitment; it does not prove "
        "the meters were honest. Weighted at half of Tier 1."
    )
    if st.session_state.site_id == "demo_maji_moto":
        share = _nearby_blend(
            float(st.session_state.lat), float(st.session_state.lon),
            est18.p10, est18.p50, est18.p90, sigma,
            _mtime("sharing_records.json"),
        )
        b = share["blended"]
        st.caption(
            f"DEMO: Maji Moto with Olkiramatian-area records ({share['dist_note']}, "
            f"{share['n_nearby']} Tier 2 records). Month-18 P50 "
            f"{est18.p50:.2f} → {b['p50']:.2f} kWh/customer. Frozen β not refit. "
            f"Tier 2 demo built from Renewvia open data (CC BY-SA 4.0)."
        )

    cost = _cost(_mtime("cost_estimate.json"))["maji_moto"]
    a50 = cost["size_p50"]["a_generation_and_storage_sized_to_demand"]
    b50 = cost["size_p50"]["b_all_in_per_connection_from_actuals"]
    st.caption(
        f"Maji Moto 100 HH (frozen P50): (a) demand-sized {a50['kwp']:.1f} kWp × Kenya all-in "
        f"${a50['usd_per_kwp_all_in']:,.0f}/kWp = ${a50['cost_usd']:,.0f}; "
        f"(b) 100 × ${b50['usd_per_connection']:,.0f}/connection = ${b50['cost_usd']:,.0f}. "
        f"Do not add those. Sources: Overture Maps · VIIRS · GridFinder · AMDA · Renewvia. Model {FREEZE}."
    )


if __name__ == "__main__":
    main()
