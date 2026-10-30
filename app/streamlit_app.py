"""PawaCast web app. Frozen day-one model; meter update v2.

Coordinates typed or clicked by users are shown on screen and not written to disk.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from datetime import date

import altair as alt
import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP_DIR = pathlib.Path(__file__).resolve().parent
import sys

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from pawacast.cost_card import maji_moto_cost
from pawacast.features import build_features
from pawacast.model.growth import observed_multiplier
from pawacast.model.loglinear import load_frozen
from pawacast.model.update_v2 import update_v2
from pawacast.sharing.ingest import maji_moto_sharing_demo
from pawacast.targets.demo import DEMO_SITES
from theme import (
    ASH,
    BACK_LINK_HTML,
    FLARE,
    PLASMA,
    README_HEAD_HTML,
    SUN,
    footer,
    inject,
    title_block,
)

FREEZE = "c3df2c8"
PIN_TIMEOUT_S = 60
PIN_OFF_MSG = (
    "LIVE FORECASTS FOR NEW LOCATIONS ARE OFF IN THIS DEMO — fetching building data for a "
    "new site takes several minutes. Try one of the three demo sites, or run PawaCast "
    'locally (<a href="?view=readme" target="_top">README</a>).'
)
PIN_TIMEOUT_MSG = (
    "Timed out after 60 seconds fetching building data for this location. "
    'Try one of the three demo sites, or run PawaCast locally (<a href="?view=readme" target="_top">README</a>).'
)
# Page #0A0A0A; body #CCCCCC ≥4.5:1; ghost #888 on page ~5.6:1 (small labels);
# Sun #FFD93D on page ~12:1; white on answer card ~19:1.


def _live_pin_enabled() -> bool:
    return os.environ.get("PAWACAST_LIVE_PIN", "0") == "1"


def _query_view() -> str:
    try:
        value = st.query_params.get("view", "")
    except Exception:
        value = ""
    if isinstance(value, (list, tuple)):
        value = value[0] if value else ""
    return str(value or "").strip().lower()


_MD_IMG = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
_MD_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def _is_external_url(url: str) -> bool:
    u = url.strip()
    return u.startswith("http://") or u.startswith("https://") or u.startswith("mailto:")


def _prepare_readme(text: str) -> str:
    """Keep external links; turn repo-relative links into monospace filenames."""

    def _img(match: re.Match) -> str:
        alt, url = match.group(1), match.group(2)
        if _is_external_url(url):
            return match.group(0)
        return alt or ""

    def _link(match: re.Match) -> str:
        url = match.group(2).strip()
        if _is_external_url(url):
            return match.group(0)
        name = url.split("#", 1)[0].rstrip("/").split("/")[-1] or match.group(1)
        return f"`{name}`"

    text = _MD_IMG.sub(_img, text)
    return _MD_LINK.sub(_link, text)


def _render_readme() -> None:
    raw = (ROOT / "README.md").read_text(encoding="utf-8")
    body = _prepare_readme(raw)
    st.markdown(README_HEAD_HTML, unsafe_allow_html=True)
    st.markdown(BACK_LINK_HTML, unsafe_allow_html=True)
    st.markdown(f'<div class="readme-page">\n\n{body}\n\n</div>', unsafe_allow_html=True)
    st.markdown(BACK_LINK_HTML, unsafe_allow_html=True)


def _pin_card(text: str) -> None:
    st.markdown(f"<div class='pin-note'>{text}</div>", unsafe_allow_html=True)


def _fetch_click_features(lat: float, lon: float) -> dict:
    sites = pd.DataFrame({"site_id": ["click"], "lat": [lat], "lon": [lon]})
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(build_features, sites)
        try:
            return future.result(timeout=PIN_TIMEOUT_S).iloc[0].to_dict()
        except FuturesTimeout as exc:
            raise TimeoutError("Overture fetch timed out") from exc


def _safe_int(value, default: int) -> int:
    """int() that treats None/NaN as default. NaN is truthy, so `x or default` is not safe."""
    if value is None or pd.isna(value):
        return int(default)
    return int(value)


def _map_label(name: str) -> str:
    if str(name).startswith("Maji Moto"):
        return "Maji Moto"
    if str(name).startswith("Ewaso Ngiro"):
        return "Ewaso Ngiro"
    if str(name).startswith("Narok"):
        return "Narok town"
    return str(name)


def _safe_float(value, default: float) -> float:
    """float() that treats None/NaN as default."""
    if value is None or pd.isna(value):
        return float(default)
    return float(value)


st.set_page_config(page_title="PawaCast · Poll Power", layout="wide", page_icon="⚡")


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


def growth_chart(
    frame: pd.DataFrame, band_color: str | None = None, line_color: str | None = None
) -> alt.Chart:
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
    band_c = band_color or FLARE
    line_c = line_color or SUN
    band = (
        alt.Chart(d)
        .mark_area(opacity=0.25, color=band_c)
        .encode(x=x, y=alt.Y("p10:Q", title="kWh / household / month"), y2="p90:Q")
    )
    line = (
        alt.Chart(d)
        .mark_line(color=line_c, strokeWidth=2)
        .encode(x=x, y="p50:Q")
    )
    return alt.layer(band, line).properties(height=200).configure_view(strokeWidth=0, fill="transparent")


def waterfall_rows(est18, p50_24: float, k24: float) -> pd.DataFrame:
    rows = []
    level = float(est18.baseline)
    rows.append(
        {
            "step": "Country baseline",
            "kwh": f"{level:.1f}",
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
                "kwh": f"{level:.1f}",
                "delta": f"{level - before:+.1f}",
                "mult": f"×{float(mult):.2f}",
                "note": why,
            }
        )
    rows.append(
        {
            "step": "At 24 months",
            "kwh": f"{p50_24:.1f}",
            "delta": f"{p50_24 - est18.p50:+.1f}",
            "mult": f"×{k24:.2f}",
            "note": "growth to month 24",
        }
    )
    return pd.DataFrame(rows)


def html_report(name, country, lat, lon, n, est, site_p10, site_p50, site_p90, feats, ev) -> str:
    bld = _safe_int(feats.get("bld_count"), 0)
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
    st.session_state.lat = _safe_float(lat, 0.0)
    st.session_state.lon = _safe_float(lon, 0.0)
    st.session_state.country = country if isinstance(country, str) and country else "KE"
    st.session_state.customers = _safe_int(customers, 100)
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
    inject()
    if _query_view() == "readme":
        _render_readme()
        footer()
        return
    title_block()
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
        # CartoDB dark_matter now watermarks without an API key (folium 0.20+).
        # Esri World Dark Gray is the free dark basemap used instead.
        m = folium.Map(
            location=[-1.22, 35.78],
            zoom_start=9,
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}",
            attr="Tiles © Esri",
        )
        m.get_root().html.add_child(
            folium.Element(
                "<style>.pp-map-label{background:transparent!important;border:none!important;}</style>"
            )
        )
        for _, r in demo.iterrows():
            folium.CircleMarker(
                [r.lat, r.lon], radius=8, color=SUN, fill=True, fill_color=SUN,
                fill_opacity=0.95, popup=r["name"], tooltip=r["name"],
            ).add_to(m)
            selected = r.site_id == st.session_state.site_id
            label_color = SUN if selected else "#FFFFFF"
            folium.Marker(
                [r.lat, r.lon],
                icon=folium.DivIcon(
                    class_name="pp-map-label",
                    icon_size=(110, 18),
                    icon_anchor=(-12, 10),
                    html=(
                        f"<div style=\"font-family:'Space Mono',ui-monospace,monospace;"
                        f"font-size:10px;letter-spacing:.04em;color:{label_color};"
                        f"background:rgba(0,0,0,.6);padding:2px 6px;white-space:nowrap;"
                        f"display:inline-block;\">{_map_label(r['name'])}</div>"
                    ),
                ),
            ).add_to(m)
        pin_color = PLASMA if st.session_state.site_id == "click" else SUN
        if st.session_state.site_id == "click":
            folium.CircleMarker(
                [st.session_state.lat, st.session_state.lon], radius=8,
                color=PLASMA, fill=True, fill_color=PLASMA, fill_opacity=0.95,
                popup="Dropped pin", tooltip="Dropped pin",
            ).add_to(m)
        folium.CircleMarker(
            [st.session_state.lat, st.session_state.lon], radius=12,
            color=pin_color, fill=False, weight=2,
        ).add_to(m)
        clicked = st_folium(m, height=420, width=None, returned_objects=["last_clicked", "last_object_clicked_tooltip"])
        tip = (clicked or {}).get("last_object_clicked_tooltip")
        if tip:
            hit = demo[demo["name"] == tip]
            if not len(hit):
                hit = demo[demo["name"].map(_map_label) == tip]
            if len(hit) and hit.iloc[0].site_id != st.session_state.site_id:
                r = hit.iloc[0]
                f = feats_demo[feats_demo.site_id == r.site_id].iloc[0].to_dict()
                apply_site(r.site_id, r["name"], r.lat, r.lon, r.country, r.customers, f)
                st.rerun()
        lc = (clicked or {}).get("last_clicked")
        if lc and abs(lc["lat"] - st.session_state.lat) > 1e-4:
            click_key = (round(float(lc["lat"]), 5), round(float(lc["lng"]), 5))
            if not _live_pin_enabled():
                _pin_card(PIN_OFF_MSG)
            elif st.session_state.get("pin_timed_out") == click_key:
                _pin_card(PIN_TIMEOUT_MSG)
            else:
                with st.spinner("fetching buildings… up to 60 s"):
                    try:
                        f = _fetch_click_features(lc["lat"], lc["lng"])
                    except TimeoutError:
                        st.session_state.pin_timed_out = click_key
                        _pin_card(PIN_TIMEOUT_MSG)
                    else:
                        apply_site(
                            "click", "Dropped pin", lc["lat"], lc["lng"],
                            st.session_state.country, st.session_state.customers, f,
                        )
                        st.rerun()

        tr0 = 100 * real["summary"]["TRAIN-LOGO"]["0"]["median_ape"]
        tr6 = 100 * real["summary"]["TRAIN-LOGO"]["6"]["median_ape"]
        rt0 = 100 * real["summary"]["R-test"]["0"]["median_ape"]
        rt6 = 100 * real["summary"]["R-test"]["6"]["median_ape"]
        with st.expander("How tested", expanded=True):
            st.markdown(
                f"Tested on 18 real Renewvia mini-grids, each left out in turn: median error "
                f"{tr0:.0f}%, falling to {int(tr6)}% after 6 months of real meter readings. "
                f"On 5 sites the model never saw: {rt0:.0f}%, falling to {int(rt6)}%."
            )
            st.markdown(
                "Honest limits: from public data alone, forecasts for the unseen sites ran "
                "about 2.4× too high, and the Nigerian sites were missed. After updating "
                "with readings, the range is too narrow on unseen sites (it contained the "
                "real value 20% of the time). A forecast is not a guarantee of revenue."
            )

    with right:
        st.markdown("<div class='section'>SITE</div>", unsafe_allow_html=True)
        st.markdown(f"<h2 class='bebas' style='margin-top:0'>{st.session_state.name}</h2>", unsafe_allow_html=True)
        st.caption(f"{st.session_state.lat:.4f}, {st.session_state.lon:.4f} · "
                   f"{_safe_float(st.session_state.feats.get('grid_dist_km'), 0):.1f} km to grid")
        c1, c2 = st.columns(2)
        st.session_state.customers = c1.number_input(
            "Customers", min_value=10, max_value=5000,
            value=_safe_int(st.session_state.customers, 100), step=10,
        )
        st.session_state.country = c2.selectbox("Country", ["KE", "NG", "ET"],
                                                index=["KE", "NG", "ET"].index(st.session_state.country)
                                                if st.session_state.country in ("KE", "NG", "ET") else 0)
        est18 = model.estimate(st.session_state.feats, st.session_state.country)
        k24 = float(observed_multiplier(24, slope))
        p10_24, p50_24, p90_24 = est18.p10 * k24, est18.p50 * k24, est18.p90 * k24
        n = _safe_int(st.session_state.customers, 100)
        st.markdown(
            f"<div class='answer'>"
            f"<div class='kicker'>EXPECTED DEMAND AT 24 MONTHS</div>"
            f"<div class='big'>{p50_24:.1f}</div>"
            f"<div class='unit'>kWh per household per month at 24 months</div>"
            f"<div class='range'>80% range {p10_24:.1f} – {p90_24:.1f}</div>"
            f"<div class='range'>{n} households: {p10_24*n:,.0f} – {p90_24*n:,.0f} kWh/month"
            f" (most likely {p50_24*n:,.0f})</div></div>",
            unsafe_allow_html=True,
        )

        st.markdown("<div class='section'>WHY THIS NUMBER</div>", unsafe_allow_html=True)
        wf = waterfall_rows(est18, p50_24, k24)
        st.table(wf)
        st.caption(
            "Biggest uncertainty: the starting level. Real Renewvia sites in Kenya ranged 1.7–16 kWh."
        )

        cost = maji_moto_cost()
        st.markdown("<div class='section'>COST (KENYA MEDIAN, 100 HOUSEHOLDS)</div>", unsafe_allow_html=True)
        st.markdown(
            f"**USD {cost['b_cost_usd']:,.0f}** all-in "
            f"(USD {cost['b_usd_per_connection']:,.0f}/connection × {cost['households']})."
        )
        st.markdown(
            f"Solar alone, sized to forecast demand: {cost['a_kwp']:.1f} kWp × "
            f"USD {cost['a_usd_per_kwp']:,.0f}/kWp ≈ USD {cost['a_cost_usd']:,.0f}. "
            f"This is part of the all-in figure above, not an extra cost."
        )

    st.markdown("<div class='section'>GROWTH AFTER CONNECTION</div>", unsafe_allow_html=True)
    prior_c = curve_frame(est18.p10, est18.p50, est18.p90, slope)
    st.altair_chart(growth_chart(prior_c), use_container_width=True)
    st.caption("Most sites flat after year 1 (~7%/yr)")

    st.markdown("<div class='section'>METERS CORRECT</div>", unsafe_allow_html=True)
    st.markdown("<span class='sim'>SIMULATED</span> readings for the demo — not signed PollPower meters.",
                unsafe_allow_html=True)
    a, b, c = st.columns([1, 1, 0.6])
    month = a.number_input("month", min_value=0, max_value=48, value=3, step=1)
    kwh = b.number_input("kWh / household", min_value=0.1, max_value=80.0, value=4.2, step=0.1)
    readings = st.session_state.readings
    if c.button("Add", type="primary"):
        st.session_state.readings = list(readings) + [(float(month), float(kwh))]
        st.rerun()
    if st.session_state.readings:
        u = update_v2(est18.p50, st.session_state.readings, cal, sigma, slope)
        post_c = curve_frame(u["p10"], u["p50"], u["p90"], slope)
        before, after = st.columns(2)
        with before:
            st.markdown("**Forecast**")
            st.write(f"{p50_24:.1f} kWh  ·  most likely {p10_24:.1f} – {p90_24:.1f}")
            st.altair_chart(growth_chart(prior_c), use_container_width=True)
        with after:
            st.markdown("**After SIMULATED readings**")
            st.write(f"{u['p50']:.1f} kWh  ·  most likely {u['p10']:.1f} – {u['p90']:.1f}")
            st.altair_chart(growth_chart(post_c, FLARE, PLASMA), use_container_width=True)
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

    st.markdown("<div class='section'>SHARE YOUR METER DATA</div>", unsafe_allow_html=True)
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
            "- Mean / P10 / P50 / P90 kWh per customer (after privacy noise)\n"
            "- Business share, rounded to 10%\n"
            "- A 32-byte commitment to the exact per-customer totals\n"
            "- A Compact proof against that prior commitment"
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
        "The proof shows the operator's exact site-month total and customer count "
        "match readings it committed to earlier, without revealing any customer's "
        "values. Privacy noise is added after the proof, to the public release only."
    )
    st.markdown(
        "Circuit compiles with compactc 0.30.0 (N_MAX 128, "
        "proving key 306 MB). Circuit logic tested on 4 fixtures (valid; too few "
        "customers; wrong commitment; non-zero padding). Not deployed; no on-chain "
        "proofs generated during the sprint."
    )
    st.markdown(
        "**Tier 1 — PollPower-metered.** Readings are signed on the chip, "
        "and the commitment is designed to be published with the EBT settlement "
        "record. Strongest weight.\n\n"
        "**Tier 2 — other operators.** Export from SteamaCo / SparkMeter / Odyssey, "
        "signed by the operator. The proof matches the commitment; it does not prove "
        "the meters were honest. Weighted at half of Tier 1."
    )
    if st.session_state.site_id == "demo_maji_moto":
        share = _sharing_demo(_mtime("sharing_records.json"))
        b18 = share["blended_month18"]
        f18 = share["frozen_month18"]
        st.caption(
            f"DEMO: Maji Moto at month 18, using {share['n_nearby_records']} Tier 2 records "
            f"from the Olkiramatian area ({share['olkiramatian_distance_km']:.0f} km away, "
            f"within an {share['radius_km']:.0f} km radius). Most likely demand moves "
            f"{f18['p50']:.2f} → {b18['p50']:.2f} kWh per customer. The day-one model itself "
            f"is not changed. Tier 2 demo records built from Renewvia open data (CC BY-SA 4.0)."
        )

    footer()


if __name__ == "__main__":
    main()
