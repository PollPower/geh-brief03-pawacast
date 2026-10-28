# PawaCast web app — design (pre-sprint)

Design only. The app is a new feature and is **built during the sprint** (hours 16–24), after the `geh2026-sprint-start` tag.
Hosting setup (subdomain, TLS, placeholder page) is environment preparation and may be done before the sprint.

## 1. Who it's for and what it must show in 60 seconds

A developer or lender opens a page, clicks a village on a map, and within a minute sees:
1. the expected demand and its range,
2. why the number came out that way,
3. how it grows after connection,
4. how meter readings shrink the range (the PollPower point),
5. a lender report they can download.

## 2. Screen layout (single page, desktop first, usable on a phone)

```
┌──────────────────────────────────────────────────────────────────────┐
│ ▬▬▬ gradient bar                                                     │
│ (orb) POLL POWER · PAWACAST          Demand before you build   [ⓘ]  │
├───────────────────────────────┬──────────────────────────────────────┤
│                               │ SITE  Maji Moto, Narok (PollPower)   │
│        MAP (Leaflet / OSM)    │ -1.3387, 35.7125 · 8.7 km to grid    │
│                               │ Customers [ 100 ]  Country [KE ▾]    │
│  ● Ewaso Ngiro                ├──────────────────────────────────────┤
│  ● Narok town                 │ EXPECTED DEMAND AT 24 MONTHS          │
│  ● Maji Moto                  │   3.6 kWh / household / month        │
│                               │   most likely 1.5 – 8.2              │
│  click anywhere to forecast   │   100 households: 150 – 820 kWh/mo   │
│                               ├──────────────────────────────────────┤
│                               │ WHY THIS NUMBER   (horizontal bars)   │
│                               │  Country baseline   3.7 kWh  AMDA KE  │
│                               │  Business activity  ×1.01            │
│                               │  Building size      ×0.95            │
│                               │  Night lights       ×1.00            │
├───────────────────────────────┴──────────────────────────────────────┤
│ GROWTH AFTER CONNECTION  (line + shaded band, months 0–24)            │
├──────────────────────────────────────────────────────────────────────┤
│ METERS CORRECT                                                        │
│  Add readings: month [ 3 ] kWh/household [ 4.2 ]  [+]   or  [Upload CSV]│
│  Forecast band (grey) vs after-readings band (flare) — narrows live   │
│  "After 3 months of readings the range is 77% narrower."             │
├──────────────────────────────────────────────────────────────────────┤
│ [Download lender report (PDF)]   How tested: 6 + 3 held-out sites ⓘ  │
│ Sources: Overture Maps · VIIRS · GridFinder · AMDA · model v[commit] │
└──────────────────────────────────────────────────────────────────────┘
```

Design system: PollPower (Sun #FFD93D, Flare #FF6B35, Plasma #FF3366, Ash #0D0D0D); Bebas Neue headings, Space Mono labels, Inter body. Light page with the gradient bar, matching the disclosure statement.

Plain-language rules (same as REPORT_DESIGN.md): "most likely" range, never "P10/P90" in the main view; every multiplier with its observed reason; simulated readings labelled SIMULATED.

## 3. Interaction flow (also the demo-video script)

1. Page opens on Narok County with the three demo sites marked.
2. Click **Maji Moto** → answer card fills instantly (pre-computed).
3. Point at "Why this number": low business activity, small buildings, no night lights.
4. Click **Narok town** → number and drivers jump; same tool, different village.
5. Back to Maji Moto → **Meters correct**: add three months of readings → band narrows on screen.
6. **Download lender report** → PDF opens.
7. Click an arbitrary new point → progress bar ("fetching buildings… 30–80 s") → result.

## 4. Speed

| Case | Approach | Time |
|---|---|---|
| Demo sites, test sites | Features pre-computed and cached (data/features/*.parquet) | instant |
| New point | Live Overture + raster lookup, cached after first run | 30–80 s, with progress bar |
| Later | Pre-computed feature grid for Narok and Kajiado counties (H3 res 8) | instant |

## 5. Tech

- **Streamlit** (Python) — reuses `pawacast` directly; one file, `app/streamlit_app.py`.
- Map: `streamlit-folium` (Leaflet, OpenStreetMap tiles, attribution shown).
- Charts: Altair (ships with Streamlit), styled to the design system.
- Report PDF: HTML template → PDF (Playwright or WeasyPrint), per REPORT_DESIGN.md.
- No login, no stored user data. Coordinates typed by users are not logged.

Runs on a laptop (`streamlit run app/streamlit_app.py`) and on a free cloud tier, which meets the brief's constraint.

## 6. Hosting on pollpower.energy (via OpenClaw)

Target: **https://pawacast.pollpower.energy**

| Step | When | Who |
|---|---|---|
| DNS record for `pawacast.pollpower.energy` → relay server | Pre-sprint (environment) | OpenClaw |
| nginx server block, TLS certificate, static "PawaCast — coming 1 Nov" placeholder | Pre-sprint (environment) | OpenClaw |
| Python 3.12 venv on relay (system Python) with `requirements.txt` | Pre-sprint (environment) | OpenClaw |
| Deploy the app: `git pull`, pm2 process `pawacast` on 127.0.0.1:8501, nginx proxy with websocket upgrade (Streamlit needs it) | Sprint, after the app works locally | OpenClaw |
| Copy cached demo-site features to the server | Sprint | OpenClaw |

Constraints for the server:
- Separate pm2 process; must not touch pollpower-v2-api, settlement services or their nginx blocks.
- Outbound HTTPS to `overturemaps-us-west-2.s3.amazonaws.com` and `stac.overturemaps.org` (live lookups).
- ~1.1 GB for rasters (VIIRS ×3, GridFinder) under the app's data folder.
- Memory: Overture lookups via DuckDB can peak at ~1–2 GB; set `memory_limit` in DuckDB.

Fallback if relay hosting isn't ready: Streamlit Community Cloud (free) from the same repo, linked from pollpower.energy.

## 7. Sprint build checklist (hours 16–24)

- [ ] `app/streamlit_app.py`: map, site panel, answer card, drivers chart, growth chart
- [ ] Meters-correct panel using `pawacast.model.update`
- [ ] Pre-compute demo-site features into the repo's cache
- [ ] Lender report download (REPORT_DESIGN.md)
- [ ] "How tested" panel reading `results/` (EVAL_PLAN.md numbers)
- [ ] Deploy to pawacast.pollpower.energy (OpenClaw), smoke-test from a phone
