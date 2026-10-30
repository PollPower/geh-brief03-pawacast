"""PollPower visual theme for the PawaCast Streamlit app.

Tokens match pollpower.energy. No numbers or copy live here.
"""
from __future__ import annotations

import altair as alt
import streamlit as st

SUN = "#FFD93D"
FLARE = "#FF6B35"
PLASMA = "#FF3366"
ASH = "#0D0D0D"
STEEL = "#2A2A2A"
GHOST = "#888888"
PAGE = "#0A0A0A"
INK = "#F5F5F5"
BODY = "#CCCCCC"
NAV_H = "64px"

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Instrument+Serif:ital@0;1&family=JetBrains+Mono:wght@400;500;700&display=swap');

:root {{
  --sun: {SUN}; --flare: {FLARE}; --plasma: {PLASMA}; --ash: {ASH};
  --steel: {STEEL}; --ghost: {GHOST}; --page: {PAGE}; --ink: {INK}; --body: {BODY};
}}

header[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stDecoration"],
#MainMenu,
footer,
.stAppDeployButton,
[data-testid="stAppDeployButton"] {{
  display: none !important;
  visibility: hidden !important;
  height: 0 !important;
}}

.stApp, [data-testid="stAppViewContainer"], .stAppViewContainer {{
  background-color: {PAGE} !important;
  background-image:
    linear-gradient(rgba(255,217,61,.07) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,217,61,.07) 1px, transparent 1px) !important;
  background-size: 80px 80px !important;
  background-attachment: fixed !important;
  color: {BODY};
  font-family: ui-sans-serif, system-ui, sans-serif;
}}

[data-testid="stHeader"] {{ background: transparent !important; }}

.block-container {{
  padding-top: 5.6rem !important;
  padding-bottom: 3rem !important;
  max-width: 1400px;
}}
.stMain {{
  scroll-padding-top: 72px;
}}

h1, h2, h3, .bebas {{
  font-family: 'Bebas Neue', sans-serif !important;
  color: {INK} !important;
  letter-spacing: 0.04em;
  font-weight: 400;
}}
h1 {{
  background: linear-gradient(90deg, {SUN} 0%, {FLARE} 55%, {PLASMA} 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent !important;
  -webkit-text-fill-color: transparent;
}}

p, li, .stMarkdown, [data-testid="stMarkdownContainer"],
[data-testid="stCaptionContainer"], .stCaption {{
  color: {BODY} !important;
  font-family: ui-sans-serif, system-ui, sans-serif;
}}
[data-testid="stCaptionContainer"], .stCaption, .stCaption p {{
  color: {GHOST} !important;
  font-family: 'JetBrains Mono', ui-monospace, monospace !important;
  font-size: 11px !important;
  letter-spacing: 0.04em;
}}

.lede {{
  font-family: 'Instrument Serif', serif;
  font-size: 1.25rem;
  color: {BODY};
}}

.section {{
  font-family: 'JetBrains Mono', ui-monospace, monospace !important;
  color: {GHOST} !important;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  font-size: 11px;
  background: transparent;
  display: block;
  padding: 0;
  margin: 1.1rem 0 0.45rem 0;
}}

.answer {{
  background: rgba(255,255,255,.03);
  color: {INK};
  border: 1px solid {SUN};
  border-radius: 0;
  padding: 1rem 1.1rem;
  margin: 0.5rem 0 1rem 0;
}}
.answer, .answer * {{ color: {INK} !important; }}
.answer .kicker {{
  font-family: 'JetBrains Mono', ui-monospace, monospace !important;
  font-size: 11px; letter-spacing: 0.1em; text-transform: uppercase;
  color: {GHOST} !important; margin-bottom: 0.4rem;
}}
.answer .big {{
  font-family: 'Bebas Neue', sans-serif !important;
  font-size: 3rem; line-height: 0.92;
  color: {INK} !important;
  -webkit-text-fill-color: {INK};
  background: none;
}}
.answer .unit {{
  font-size: 1.02rem; margin: 0.2rem 0 0.45rem 0; color: {BODY} !important;
}}
.answer .range {{
  font-family: 'JetBrains Mono', ui-monospace, monospace !important;
  font-size: 0.95rem; color: {BODY} !important; margin-top: 0.2rem;
}}

.sim {{
  background: {SUN}; color: {ASH};
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-size: 11px; letter-spacing: 0.1em; padding: 0.12rem 0.4rem;
}}

div[data-testid="stExpander"],
div[data-testid="stVerticalBlockBorderWrapper"] {{
  background: rgba(255,255,255,.03) !important;
  border: 1px solid {STEEL} !important;
  border-radius: 0 !important;
}}
div[data-testid="stExpander"] p,
div[data-testid="stExpander"] li,
div[data-testid="stExpander"] [data-testid="stMarkdownContainer"] {{
  color: {BODY} !important;
}}
summary, [data-testid="stExpander"] summary, .streamlit-expanderHeader {{
  font-family: 'JetBrains Mono', ui-monospace, monospace !important;
  font-size: 11px !important;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: {GHOST} !important;
}}

.stButton > button, [data-testid="stBaseButton-secondary"],
[data-testid="stBaseButton-primary"],
[data-testid="stDownloadButton"] > button {{
  font-family: 'JetBrains Mono', ui-monospace, monospace !important;
  font-size: 11px !important;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  border-radius: 0 !important;
}}
.stButton > button {{
  background: transparent !important;
  color: {INK} !important;
  border: 1px solid rgba(255,255,255,.25) !important;
}}
.stButton > button:hover {{
  background: {SUN} !important;
  color: {ASH} !important;
  border-color: {SUN} !important;
}}
[data-testid="stBaseButton-primary"],
.stButton > button[kind="primary"] {{
  background: linear-gradient(135deg, {SUN}, {FLARE}) !important;
  color: {ASH} !important;
  border: 0 !important;
}}
[data-testid="stDownloadButton"] > button {{
  background: transparent !important;
  color: {INK} !important;
  border: 1px solid rgba(255,255,255,.25) !important;
}}
[data-testid="stDownloadButton"] > button:hover {{
  background: {SUN} !important;
  color: {ASH} !important;
}}

div[data-testid="stNumberInput"] input,
div[data-baseweb="select"] > div,
.stSelectbox [data-baseweb="select"] > div,
.stTextInput input {{
  background: {ASH} !important;
  color: {INK} !important;
  border: 1px solid {STEEL} !important;
  border-radius: 0 !important;
}}
[data-testid="stWidgetLabel"] p, label, .stNumberInput label, .stSelectbox label {{
  font-family: 'JetBrains Mono', ui-monospace, monospace !important;
  font-size: 11px !important;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: {GHOST} !important;
}}
input[type="range"], .stSlider [data-baseweb="slider"] div[role="slider"] {{
  accent-color: {SUN};
}}

a, a:visited {{ color: {SUN} !important; }}
a:hover {{ color: {FLARE} !important; }}

[data-testid="stTable"] table, .stTable table, [data-testid="stDataFrame"] {{
  background: rgba(255,255,255,.03) !important;
  color: {BODY} !important;
  border: 1px solid {STEEL};
}}
[data-testid="stTable"] th, .stTable th {{
  font-family: 'JetBrains Mono', ui-monospace, monospace !important;
  font-size: 11px; letter-spacing: 0.1em; text-transform: uppercase;
  color: {GHOST} !important;
  background: transparent !important;
}}
[data-testid="stTable"] td, .stTable td {{
  color: {BODY} !important;
  border-bottom: 1px solid {STEEL} !important;
}}

.pp-nav {{
  position: fixed; top: 0; left: 0; right: 0; z-index: 100000;
  height: {NAV_H};
  display: flex; align-items: center; justify-content: space-between;
  gap: 1rem; padding: 0 1.2rem;
  background: rgba(255,255,255,.05);
  backdrop-filter: blur(40px) saturate(180%);
  -webkit-backdrop-filter: blur(40px) saturate(180%);
  border-bottom: 1px solid rgba(255,255,255,.1);
}}
.pp-brand {{
  display: flex; align-items: center; gap: 0.7rem; text-decoration: none !important;
  min-width: 0; flex-shrink: 0;
}}
.pp-orb {{
  width: 40px; height: 40px; border-radius: 50%; flex-shrink: 0;
  background: radial-gradient(circle at 30% 30%, {SUN}, {FLARE} 50%, {PLASMA} 100%);
  box-shadow: 0 0 18px rgba(255,107,53,.55), 0 0 36px rgba(255,51,102,.28);
}}
.pp-brand-text {{ display: flex; flex-direction: column; line-height: 1.05; }}
.pp-brand-name {{
  font-family: 'Bebas Neue', sans-serif;
  font-size: 20px; letter-spacing: 0.1em; color: {INK};
  background: linear-gradient(90deg, {SUN}, {FLARE}, {PLASMA});
  -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent; color: transparent;
}}
.pp-brand-sub {{
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-size: 9px; letter-spacing: 0.12em; color: {GHOST}; text-transform: uppercase;
}}
.pp-nav-links {{
  display: flex; align-items: center; gap: 1.35rem;
  overflow-x: auto; flex-wrap: nowrap; white-space: nowrap;
  -webkit-overflow-scrolling: touch; scrollbar-width: none;
}}
.pp-nav-links::-webkit-scrollbar {{ display: none; }}
.pp-nav-links a {{
  font-family: 'JetBrains Mono', ui-monospace, monospace !important;
  font-size: 11px !important; letter-spacing: 0.12em; text-transform: uppercase;
  color: {INK} !important; text-decoration: none !important; flex-shrink: 0;
}}
.pp-nav-links a:hover {{ color: {SUN} !important; }}

.pin-note {{
  background: rgba(255,255,255,.03);
  color: {BODY};
  border: 1px solid {STEEL};
  border-radius: 0;
  padding: 0.75rem 0.9rem;
  margin: 0.5rem 0 1rem 0;
  font-family: ui-sans-serif, system-ui, sans-serif;
  font-size: 0.95rem;
  line-height: 1.45;
}}

.pp-foot {{
  margin-top: 2.4rem; padding-top: 1.1rem;
  border-top: 1px solid {STEEL};
}}
.pp-foot .name {{
  font-family: 'Bebas Neue', sans-serif; font-size: 1.35rem;
  letter-spacing: 0.1em; color: {INK}; margin: 0 0 0.35rem 0;
}}
.pp-foot .credits, .pp-foot .built {{
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-size: 10px; letter-spacing: 0.06em; color: {GHOST};
  margin: 0.15rem 0;
}}

iframe {{ border: 1px solid {STEEL} !important; }}
</style>
"""

NAV_HTML = """
<div class="pp-nav">
  <a class="pp-brand" href="https://pollpower.energy" target="_blank" rel="noopener">
    <span class="pp-orb" aria-hidden="true"></span>
    <span class="pp-brand-text">
      <span class="pp-brand-name">POLL POWER</span>
      <span class="pp-brand-sub">PAWACAST · DEMAND FORECAST</span>
    </span>
  </a>
  <nav class="pp-nav-links">
    <a href="https://pollpower.energy">HOME</a>
    <a href="https://pollpower.energy/milestone2">MILESTONE 2</a>
    <a href="https://github.com/PollPower">GITHUB</a>
    <a href="https://pollpower.energy/support">SUPPORT</a>
  </nav>
</div>
"""

FOOTER_HTML = """
<div class="pp-foot">
  <div class="name">POLL POWER</div>
  <p class="credits">Renewvia CC BY-SA 4.0 · AMDA · Overture · VIIRS · GridFinder</p>
  <p class="built">Built for the Global Energy Hackathon 2026 · Brief 03</p>
</div>
"""


@alt.theme.register("pawacast", enable=True)
def _altair_theme():
    return alt.theme.ThemeConfig(
        {
            "background": "transparent",
            "view": {"stroke": "transparent", "fill": "transparent"},
            "axis": {
                "labelColor": GHOST,
                "titleColor": GHOST,
                "gridColor": STEEL,
                "domainColor": STEEL,
                "tickColor": GHOST,
                "labelFont": "JetBrains Mono",
                "titleFont": "JetBrains Mono",
                "labelFontSize": 11,
                "titleFontSize": 11,
            },
            "legend": {
                "labelColor": GHOST,
                "titleColor": GHOST,
                "labelFont": "JetBrains Mono",
                "titleFont": "JetBrains Mono",
            },
            "title": {"color": INK, "font": "Bebas Neue"},
        }
    )


def apply_matplotlib() -> None:
    try:
        import matplotlib as mpl
    except ImportError:
        return
    mpl.rcParams.update(
        {
            "figure.facecolor": PAGE,
            "axes.facecolor": PAGE,
            "axes.edgecolor": STEEL,
            "axes.labelcolor": GHOST,
            "xtick.color": GHOST,
            "ytick.color": GHOST,
            "text.color": BODY,
            "grid.color": STEEL,
            "font.family": "JetBrains Mono",
        }
    )


def inject() -> None:
    alt.theme.enable("pawacast")
    apply_matplotlib()
    st.markdown(CSS + NAV_HTML, unsafe_allow_html=True)


def footer() -> None:
    st.markdown(FOOTER_HTML, unsafe_allow_html=True)
