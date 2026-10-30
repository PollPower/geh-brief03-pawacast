"""PawaCast web app. Frozen day-one model; meter update v2.

Coordinates typed or clicked by users are shown on screen and not written to disk.
"""
from __future__ import annotations

import json
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

from pawacast.cost_card import maji_moto_cost
from pawacast.features import build_features
from pawacast.model.growth import observed_multiplier
from pawacast.model.loglinear import load_frozen
from pawacast.model.update_v2 import update_v2
from pawacast.sharing.ingest import maji_moto_sharing_demo
from pawacast.targets.demo import DEMO_SITES

SUN, FLARE, PLASMA, ASH = "#FFD93D", "#FF6B35", "#FF3366", "#0D0D0D"
FREEZE = "c3df2c8"
# Ash #0D0D0D on white ~19:1; white on Ash ~19:1; Sun #FFD93D on Ash ~13:1. WCAG AA.

st.set_page_config(page_title="PawaCast · PollPower", layout="wide", page_icon="⚡")

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@400;600&family=Space+Mono:wght@400;700&display=swap');
html, body, [class*="css"] {{ font-family: Inter, sans-serif; color: {ASH}; }}
h1, h2, h3, .bebas {{ font-family: 'Bebas Neue', sans-serif; letter-spacing: 0.04em; }}
.mono {{ font-family: 'Space Mono', monospace; color: {ASH}; }}
.pp-bar {{
  background: linear-gradient(90deg, {SUN} 0%, {FLARE} 55%, {PLASMA} 100%);
  padding: 0.85rem 1.2rem; margin: -1rem -1rem 1rem -1rem; color: {ASH};
}}
.pp-bar h1 {{ margin: 0; font-size: 2.1rem; color: {ASH}; }}
.pp-bar .sub {{ font-family: 'Space Mono', monospace; font-size: 0.78rem; color: {ASH}; }}
.answer {{
  background: {ASH}; color: #ffffff; border-left: 6px solid {SUN};
  padding: 0.95rem 1.05rem; margin: 0.4rem 0 1rem 0;
}}
.answer, .answer * {{ color: #ffffff !important; }}
.answer .kicker {{ font-family: 'Space Mono', monospace; font-size: 0.72rem;
  letter-spacing: 0.08em; color: {SUN} !important; margin-bottom: 0.35rem; }}
.answer .big {{ font-family: 'Bebas Neue', sans-serif; font-size: 2.8rem;
  line-height: 0.95; color: {SUN} !important; }}
.answer .unit {{ font-size: 1.02rem; margin: 0.15rem 0 0.45rem 0; color: #ffffff !important; }}
.answer .range {{ font-family: 'Space Mono', monospace; font-size: 0.98rem;
  color: #ffffff !important; margin-top: 0.2rem; }}
.sim {{ background: {SUN}; color: {ASH}; font-family: 'Space Mono', monospace;
       font-size: 0.72rem; padding: 0.1rem 0.4rem; }}
.how {{ background: #f4f4f4; padding: 0.75rem 0.9rem; font-size: 0.88rem; }}
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
def _meter_real(mtime: float):
    return _json("meter_update_real.json")


@st.cache_data
def _sharing_demo(mtime: float):
    return maji_moto_sharing_demo()


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


def growth_chart(frame: pd.DataFrame, band_color: str, line_color: str) -> alt.Chart:
    d = frame.copy()
    d["month"] = d["month"].astype(int)
    x = alt.X(
        "month:O",
        title="months since connection",
        axis=alt.Axis(
            labelExpr="datum.value % 3 == 0 ? datum.value : ''",
            labelAngle=0,
        ),
    )
    band = (
        alt.Chart(d)
        .mark_area(opacity=0.22, color=band_color)
        .encode(x=x, y=alt.Y("p10:Q", title="kWh / household / month"), y2="p90:Q")
    )
    line = (
        alt.Chart(d)
        .mark_line(color=line_color, strokeWidth=2)
        .encode(x=x, y="p50:Q")
    )
    return alt.layer(band, line).properties(height=200).configure_view(strokeWidth=0)


def waterfall_rows(est18, p50_24: float, k24: float) -> pd.DataFrame:
    rows = []
    level = float(est18.baseline)
    rows.append(
        {
            "step": "Country baseline",
            "kwh": round(level, 2),
            "delta": "",
            "mult": "×1.00",
            "note": "AMDA KE 2020 · 3.7 kWh",
        }
    )
    for name, mult, why in est18.drivers:
        if name == "Country baseline":
            continue
        before = level
        level = before * float(mult)
        rows.append(
            {
                "step": name,
                "kwh": round(level, 2),
                "delta": f"{level - before:+.1f} kWh",
                "mult": f"×{float(mult):.2f}",
                "note": why,
            }
        )
    rows.append(
        {
            "step": "At 24 months",
            "kwh": round(p50_24, 2),
            "delta": f"{p50_24 - est18.p50:+.1f} kWh",
            "mult": f"×{k24:.2f}",
            "note": "frozen growth from month 18",
        }
    )
    return pd.DataFrame(rows)


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
    real = _meter_real(_mtime("meter_update_real.json"))
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

        tr0 = 100 * real["summary"]["TRAIN-LOGO"]["0"]["median_ape"]
        tr6 = 100 * real["summary"]["TRAIN-LOGO"]["6"]["median_ape"]
        rt0 = 100 * real["summary"]["R-test"]["0"]["median_ape"]
        rt6 = 100 * real["summary"]["R-test"]["6"]["median_ape"]
        st.markdown("<div class='mono'>HOW TESTED</div>", unsafe_allow_html=True)
        with st.expander("How tested", expanded=True):
            st.markdown(
                f"TRAIN leave-one-group-out median error **{tr0:.0f}% → {int(tr6)}%** "
                f"with 6 months of real readings. Held-out R-test **{rt0:.0f}% → {int(rt6)}%**."
            )
            st.markdown(
                "Honest limits: the day-one model missed the Nigerian test sites; "
                "the updated range is **overconfident** (R-test coverage 20% after "
                "6 months). Frozen model is not a guarantee of revenue."
            )

    with right:
        st.markdown("<div class='mono'>SITE</div>", unsafe_allow_html=True)
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
            f"<div class='answer'>"
            f"<div class='kicker'>EXPECTED DEMAND AT 24 MONTHS</div>"
            f"<div class='big'>{p50_24:.1f}</div>"
            f"<div class='unit'>kWh per household per month at 24 months</div>"
            f"<div class='range'>most likely {p10_24:.1f} – {p90_24:.1f}</div>"
            f"<div class='range'>{n} households: {p10_24*n:,.0f} – {p90_24*n:,.0f} kWh/month"
            f" (most likely {p50_24*n:,.0f})</div></div>",
            unsafe_allow_html=True,
        )

        st.markdown("<div class='mono'>WHY THIS NUMBER</div>", unsafe_allow_html=True)
        wf = waterfall_rows(est18, p50_24, k24)
        st.table(wf)
        st.caption(
            "Biggest uncertainty: the starting level. Real Renewvia sites in Kenya ranged 1.7–16 kWh."
        )

        cost = maji_moto_cost()
        st.markdown("<div class='mono'>COST (KENYA MEDIAN, 100 HOUSEHOLDS)</div>", unsafe_allow_html=True)
        st.markdown(
            f"**USD {cost['b_cost_usd']:,.0f}** all-in "
            f"(USD {cost['b_usd_per_connection']:,.0f}/connection × {cost['households']})."
        )
        st.caption(
            f"Secondary — generation sized to forecast demand: {cost['a_kwp']:.1f} kWp × "
            f"USD {cost['a_usd_per_kwp']:,.0f}/kWp = USD {cost['a_cost_usd']:,.0f}. "
            f"Do not add (a) and (b); both views use the same capex."
        )

    st.markdown("<div class='mono'>GROWTH AFTER CONNECTION</div>", unsafe_allow_html=True)
    prior_c = curve_frame(est18.p10, est18.p50, est18.p90, slope)
    st.altair_chart(growth_chart(prior_c, "#cccccc", FLARE), use_container_width=True)
    st.caption("Most sites flat after year 1 (~7%/yr)")

    st.markdown("<div class='mono'>METERS CORRECT</div>", unsafe_allow_html=True)
    st.markdown("<span class='sim'>SIMULATED</span> readings for the demo — not signed PollPower meters.",
                unsafe_allow_html=True)
    a, b, c = st.columns([1, 1, 0.6])
    month = a.number_input("month", min_value=0, max_value=48, value=3, step=1)
    kwh = b.number_input("kWh / household", min_value=0.1, max_value=80.0, value=4.2, step=0.1)
    readings = st.session_state.readings
    if c.button("Add"):
        st.session_state.readings = list(readings) + [(float(month), float(kwh))]
        st.rerun()
    if st.session_state.readings:
        u = update_v2(est18.p50, st.session_state.readings, cal, sigma, slope)
        post_c = curve_frame(u["p10"], u["p50"], u["p90"], slope)
        before, after = st.columns(2)
        with before:
            st.markdown("**Forecast**")
            st.write(f"{p50_24:.1f} kWh  ·  most likely {p10_24:.1f} – {p90_24:.1f}")
            st.altair_chart(growth_chart(prior_c, "#bbbbbb", "#888888"), use_container_width=True)
        with after:
            st.markdown("**After SIMULATED readings**")
            st.write(f"{u['p50']:.1f} kWh  ·  most likely {u['p10']:.1f} – {u['p90']:.1f}")
            st.altair_chart(growth_chart(post_c, FLARE, FLARE), use_container_width=True)
        wr = (u["p90"] / u["p10"]) / (est18.p90 / est18.p10)
        st.write(
            f"After **{len(st.session_state.readings)}** SIMULATED month(s) the range is "
            f"{1-wr:.0%} narrower than the forecast."
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
            "- Customer count, rounded to 5 (only if ≥ 25)\n"
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
        share = _sharing_demo(_mtime("sharing_records.json"))
        b18 = share["blended_month18"]
        f18 = share["frozen_month18"]
        st.caption(
            f"DEMO ({share['month_label']}): Maji Moto with Olkiramatian-area records "
            f"({share['olkiramatian_distance_km']:.0f} km, {share['radius_km']:.0f} km radius, "
            f"{share['n_nearby_records']} Tier 2 records). P50 "
            f"{f18['p50']:.2f} → {b18['p50']:.2f} kWh/customer. Frozen β not refit. "
            f"Tier 2 demo built from Renewvia open data (CC BY-SA 4.0)."
        )


if __name__ == "__main__":
    main()
