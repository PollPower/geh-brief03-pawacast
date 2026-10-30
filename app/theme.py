"""PollPower visual theme for the PawaCast Streamlit app.

Tokens match pollpower.energy/media. No numbers or copy live here.
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
INK = "#FFFFFF"
BODY = "#CCCCCC"
NAV_H = "65px"
MONO = "'Space Mono', ui-monospace, monospace"

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Instrument+Serif:ital@0;1&family=Space+Mono:wght@400;700&display=swap');

:root {{
  --sun: {SUN}; --flare: {FLARE}; --plasma: {PLASMA}; --ash: {ASH};
  --steel: {STEEL}; --ghost: {GHOST}; --page: {PAGE}; --ink: {INK}; --body: {BODY};
}}

header[data-testid="stHeader"],
header[data-testid="stHeader"] *,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
[data-testid="stHeaderActionElements"],
[data-testid="stAppToolbar"],
.stAppToolbar,
.stDecoration,
.stStatusWidget,
.stDeployButton,
.stAppDeployButton,
[data-testid="stAppDeployButton"],
#MainMenu,
#stHeader,
footer {{
  display: none !important;
  visibility: hidden !important;
  height: 0 !important;
  min-height: 0 !important;
  background: none !important;
  background-image: none !important;
  border: 0 !important;
  opacity: 0 !important;
  pointer-events: none !important;
}}
.stApp > header {{
  display: none !important;
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

.block-container {{
  padding-top: calc({NAV_H} + 24px) !important;
  padding-bottom: 3rem !important;
  max-width: 1400px;
}}
.stMain {{
  scroll-padding-top: calc({NAV_H} + 24px);
}}

h1, h2, h3, .bebas {{
  font-family: 'Bebas Neue', sans-serif !important;
  color: {INK} !important;
  letter-spacing: 0.02em;
  font-weight: 400;
  -webkit-text-fill-color: {INK};
  background: none;
}}
h1 {{
  font-size: 60px !important;
  line-height: 0.9 !important;
  margin: 0 0 0.55rem 0;
}}
@media (max-width: 640px) {{
  h1 {{ font-size: 36px !important; }}
}}
.grad {{
  background: linear-gradient(135deg, {SUN} 0%, {FLARE} 50%, {PLASMA} 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  color: transparent;
}}

p, li, .stMarkdown, [data-testid="stMarkdownContainer"],
[data-testid="stCaptionContainer"], .stCaption {{
  color: {BODY} !important;
  font-family: ui-sans-serif, system-ui, sans-serif;
}}
[data-testid="stCaptionContainer"], .stCaption, .stCaption p {{
  color: {GHOST} !important;
  font-family: {MONO} !important;
  font-size: 11px !important;
  letter-spacing: 0.04em;
}}

.eyebrow {{
  font-family: {MONO} !important;
  font-size: 11px !important;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: {GHOST} !important;
  -webkit-text-fill-color: {GHOST};
  margin: 0 0 12px 0;
}}
.lede {{
  font-family: 'Instrument Serif', serif !important;
  font-size: 20px !important;
  color: {GHOST} !important;
  -webkit-text-fill-color: {GHOST};
  line-height: 1.6;
  margin: 0.35rem 0 1.8rem 0;
  max-width: 42rem;
}}
.title-block {{ margin: 0 0 0.4rem 0; }}

.section {{
  font-family: {MONO} !important;
  color: {SUN} !important;
  -webkit-text-fill-color: {SUN};
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
  font-family: {MONO} !important;
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
  font-family: {MONO} !important;
  font-size: 0.95rem; color: {BODY} !important; margin-top: 0.2rem;
}}

.sim {{
  background: {SUN}; color: {ASH};
  font-family: {MONO};
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
  font-family: {MONO} !important;
  font-size: 11px !important;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: {GHOST} !important;
}}

.stButton > button, [data-testid="stBaseButton-secondary"],
[data-testid="stBaseButton-primary"],
[data-testid="stDownloadButton"] > button {{
  font-family: {MONO} !important;
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
  font-family: {MONO} !important;
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

code, kbd, samp {{
  font-family: {MONO} !important;
  background: #141414 !important;
  color: {BODY} !important;
  padding: 0.1em 0.35em;
  font-size: 0.9em;
}}
pre, pre code {{
  font-family: {MONO} !important;
  background: #141414 !important;
  color: {BODY} !important;
  border: 1px solid {STEEL};
}}

[data-testid="stTable"] table, .stTable table, [data-testid="stDataFrame"] {{
  background: rgba(255,255,255,.03) !important;
  color: {BODY} !important;
  border: 1px solid {STEEL};
}}
[data-testid="stTable"] th, .stTable th {{
  font-family: {MONO} !important;
  font-size: 11px; letter-spacing: 0.1em; text-transform: uppercase;
  color: {GHOST} !important;
  background: transparent !important;
}}
[data-testid="stTable"] td, .stTable td {{
  color: {BODY} !important;
  border-bottom: 1px solid {STEEL} !important;
}}

.pp-nav {{
  position: fixed; top: 0; left: 0; right: 0; z-index: 2147483647;
  height: {NAV_H};
  box-sizing: border-box;
  display: flex; align-items: center; justify-content: space-between;
  gap: 1rem; padding: 16px 40px;
  background: rgba(0,0,0,.6);
  backdrop-filter: blur(24px) saturate(160%);
  -webkit-backdrop-filter: blur(24px) saturate(160%);
  border-bottom: 1px solid rgba(255,255,255,.1);
}}
@media (max-width: 640px) {{
  .pp-nav {{ padding: 16px 20px; }}
}}
.pp-brand {{
  display: flex; align-items: center; gap: 12px; text-decoration: none !important;
  min-width: 0; flex-shrink: 0; color: {INK} !important;
}}
.pp-brand:hover {{ opacity: 0.8; color: {INK} !important; }}
.pp-orb {{
  width: 32px; height: 32px; border-radius: 50%; flex-shrink: 0;
  background: radial-gradient(circle at 30% 30%, {SUN}, {FLARE} 50%, {PLASMA} 100%);
  box-shadow: 0 0 24px rgba(255,217,61,.5);
}}
.pp-brand-text {{ display: flex; flex-direction: column; line-height: 1; }}
.pp-brand-name {{
  font-family: 'Bebas Neue', sans-serif;
  font-size: 19px; letter-spacing: 0.08em; line-height: 1;
  color: {INK} !important;
  -webkit-text-fill-color: {INK};
  background: none;
}}
.pp-brand-sub {{
  font-family: {MONO};
  font-size: 9px; letter-spacing: 0.14em; color: {GHOST};
  -webkit-text-fill-color: {GHOST};
  margin-top: 2px;
}}
.pp-nav-links {{
  display: flex; align-items: center; gap: 16px;
  overflow-x: auto; flex-wrap: nowrap; white-space: nowrap;
  -webkit-overflow-scrolling: touch; scrollbar-width: none;
}}
.pp-nav-links::-webkit-scrollbar {{ display: none; }}
.pp-nav-links a, .pp-nav-links a:visited, .pp-nav-links button {{
  font-family: {MONO} !important;
  font-size: 11px !important; letter-spacing: 0.1em;
  color: {GHOST} !important; text-decoration: none !important; flex-shrink: 0;
  text-transform: none;
  background: none; border: 0; padding: 0; cursor: pointer;
}}
.pp-nav-links a:hover, .pp-nav-links button:hover {{ color: {SUN} !important; }}
.pp-nav-links form {{ display: inline; margin: 0; }}

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

.back-link, .back-link:visited, button.back-link {{
  display: inline-block;
  font-family: {MONO} !important;
  font-size: 11px !important;
  letter-spacing: 0.1em;
  color: {GHOST} !important;
  text-decoration: none !important;
  margin: 0.35rem 0 1.1rem 0;
  background: none; border: 0; padding: 0; cursor: pointer;
}}
.back-link:hover, button.back-link:hover {{ color: {SUN} !important; }}
form.back-form {{ margin: 0; }}

.readme-page {{
  max-width: 820px;
  color: {BODY};
  font-family: ui-sans-serif, system-ui, sans-serif;
  font-size: 16px;
  line-height: 1.6;
}}
.readme-page, .readme-page p, .readme-page li {{
  color: {BODY} !important;
  font-size: 16px;
  line-height: 1.6;
}}
.readme-page h2, .readme-page h3 {{
  font-family: 'Bebas Neue', sans-serif !important;
  color: {INK} !important;
  -webkit-text-fill-color: {INK};
  letter-spacing: 0.04em;
  margin: 1.4rem 0 0.5rem 0;
}}
.readme-page table, .readme-page th, .readme-page td {{
  border: 1px solid {STEEL};
  border-collapse: collapse;
  padding: 0.4rem 0.65rem;
}}
.readme-page a, .readme-page a:visited {{ color: {SUN} !important; }}

.pp-foot {{
  margin-top: 2.4rem; padding-top: 1.1rem;
  border-top: 1px solid {STEEL};
}}
.pp-foot .name {{
  font-family: 'Bebas Neue', sans-serif; font-size: 1.35rem;
  letter-spacing: 0.1em; color: {INK}; margin: 0 0 0.35rem 0;
}}
.pp-foot .credits, .pp-foot .built {{
  font-family: {MONO};
  font-size: 10px; letter-spacing: 0.06em; color: {GHOST};
  margin: 0.15rem 0;
}}

iframe {{ border: 1px solid {STEEL} !important; }}
[data-testid="stHtml"] {{
  height: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
  overflow: visible !important;
}}
</style>
"""

ROUTER_JS = """
<script>
document.documentElement.setAttribute('data-pp-router', '1');
document.addEventListener('click', function (ev) {
  var a = ev.target && ev.target.closest && ev.target.closest('a');
  if (!a) return;
  var href = a.getAttribute('href') || '';
  if (href === '?' || href === './' || href === '/') {
    ev.preventDefault();
    ev.stopPropagation();
    window.location.replace(window.location.pathname);
    return;
  }
  if (href === '?view=readme' || href.indexOf('?view=readme') === 0) {
    ev.preventDefault();
    ev.stopPropagation();
    window.location.replace(window.location.pathname + '?view=readme');
  }
}, true);
</script>
"""

NAV_HTML = """
<nav class="pp-nav">
  <a class="pp-brand" href="https://pollpower.energy">
    <span class="pp-orb" aria-hidden="true"></span>
    <span class="pp-brand-text">
      <span class="pp-brand-name">POLL POWER</span>
      <span class="pp-brand-sub">PAWACAST · DEMAND FORECAST</span>
    </span>
  </a>
  <div class="pp-nav-links">
    <a href="?view=readme">README</a>
    <a href="https://pollpower.energy">← HOME</a>
  </div>
</nav>
"""

TITLE_HTML = """
<div class="title-block">
  <p class="eyebrow">BRIEF 03 · MINI-GRID DEMAND</p>
  <h1>FORECAST FIRST. <span class="grad">METERS CORRECT.</span></h1>
  <p class="lede">A demand range for any mini-grid site before you build, from public data, narrowed by real meter readings as they arrive.</p>
</div>
"""

README_HEAD_HTML = """
<div class="title-block">
  <p class="eyebrow">README</p>
  <h1>HOW PAWACAST <span class="grad">WORKS</span></h1>
</div>
"""

BACK_LINK_HTML = '<a class="back-link" href="?">← BACK TO FORECAST</a>'

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
                "labelFont": "Space Mono",
                "titleFont": "Space Mono",
                "labelFontSize": 11,
                "titleFontSize": 11,
            },
            "legend": {
                "labelColor": GHOST,
                "titleColor": GHOST,
                "labelFont": "Space Mono",
                "titleFont": "Space Mono",
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
            "font.family": "Space Mono",
        }
    )


def inject() -> None:
    alt.theme.enable("pawacast")
    apply_matplotlib()
    st.html(CSS)
    st.html(NAV_HTML + ROUTER_JS, unsafe_allow_javascript=True)


def title_block() -> None:
    st.markdown(TITLE_HTML, unsafe_allow_html=True)


def footer() -> None:
    st.markdown(FOOTER_HTML, unsafe_allow_html=True)
