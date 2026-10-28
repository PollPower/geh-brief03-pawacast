# Brief 03 sprint design: forecast first, meters correct

Pre-sprint design for Team PollPower, Global Energy Hackathon 2026.
**Status: design only. No features are built before 30 Oct 2026, 12:00 PM ET** (Innovator Handbook, §7 "Preparing before the sprint").

## What the judges will check (Brief 03)

| Brief deliverable | Our sprint output | Disclosure (c) row |
|---|---|---|
| Model or app that returns a demand estimate with a range for any location | Demand-range model: lat/lon → P10 / P50 / P90 kWh per customer per month | Demand-range model |
| Demand growth curve for the first years after connection | Growth curve, months 0–24 | 2-year growth curve |
| Validation against held-out metered sites | Public-benchmark validation (no partner data); headline = median absolute % error | Validation against public benchmarks |
| Plain-language explanation of main drivers a lender can review | Top-3 driver ranking + one-paragraph site report | Drivers for lenders |
| Proposal for how operators could share meter data safely | ZK flow: operators prove aggregates from EBT-attested meter readings without revealing customers | Meter-data sharing flow |

Impact metric (25%): **error versus actual metered demand on held-out sites**. Everything else is secondary to having a real number here.

## Architecture (built during the sprint)

1. **Site features (public data only)** for a point + radius (default 1 km):
   - Building count and total footprint area: Google Open Buildings / OpenStreetMap
   - Night-time light intensity: NOAA VIIRS monthly composite
   - Distance to grid: GridFinder
   - Schools, clinics, markets: Energy Access Explorer / OSM POIs
   - Optional, prior work disclosed: PollPower solar-scouting tiles (Sentinel-2) for rooftop-solar presence
2. **Prior (day-one) model**: gradient-boosted quantile regression (P10/P50/P90) on site features → kWh/customer/month. Small, CPU-only, runs on a laptop (brief constraint).
3. **Growth model**: log-growth curve fitted to month-since-connection on metered sites; reported as a band, not a line.
4. **Bayesian update ("meters correct")**: once a site has N months of metered kWh, shrink the prior range toward observed demand. This is the reframe made concrete: the pitch's "a meter can't be off by 7×".
5. **Driver explanation**: SHAP or permutation importance → top-3 drivers in plain words.
6. **Sharing flow (proposal + demo)**: operator publishes per-site monthly totals as a commitment; a ZK proof on Midnight attests the total equals the sum of EBT-settled, gateway-signed readings. No customer-level data leaves the operator.

## Evaluation protocol

- Unit: **site** (not customer), so the hold-out is honest.
- Leave-one-site-out (or k-fold by site if > 30 sites).
- Report: median absolute % error of P50; share of sites whose actual falls inside P10–P90 (target ≈ 80%).
- Compare against a naive baseline (brief's survey range midpoint, 20 kWh) so judges see the improvement.

## Validation without partner meter data (decided 28 Oct)

PollPower has no metered data from real sites, and no third-party validation partner. The sprint therefore validates against **public data only** and says so on screen and in the disclosure.

1. **Primary: AMDA site benchmarks.** Use site-level consumption and ARPU figures from AMDA benchmarking reports as held-out targets where a site's location or district can be matched. Report median absolute % error of P50 against them.
2. **Range check: ESMAP survey range.** Show that predicted P10–P90 ranges fall inside the brief's observed 5–35 kWh/customer/month and are narrower than it.
3. **Baseline comparison.** Same targets, naive 20 kWh midpoint, to show the model beats a guess.
4. **Meter-correction demo on labelled synthetic sites.** Demonstrate step 4 (meters narrow the range) with clearly labelled simulated readings, the same way Milestone 3 used labelled test values. Never presented as real results.

Pitch line: "Validated against public benchmarks; field validation starts with our 100-household pilot." Ask the coach whether a partner dataset can be added during the sprint.

## Allowed prep before the sprint (do now)

- [x] Validation source decided: public benchmarks (above)
- [ ] Download AMDA benchmarking reports and extract site-level figures (data collection, not feature work)
- [ ] Request a coach in #innovators-digital-solutions-apps-ai-ml
- [x] Python env (installed 28 Oct): `pandas geopandas shapely lightgbm scikit-learn shap rasterio requests matplotlib`
- [x] Access checked 28 Oct: Open Buildings, VIIRS, Zenodo, Energy Access Explorer reachable; Overpass API timed out (retry)
- [ ] Tag all prior-work repos on 29 Oct (see disclosure statement)
- [ ] Create the sprint repo (empty, README only); every feature commit lands after 30 Oct 12:00 PM ET

## Sprint plan (hours from 30 Oct 12:00 PM ET)

| Hours | Work |
|---|---|
| 00–05 | Pull features for training sites; lock evaluation split |
| 05–16 | Prior model + baseline; first back-test number |
| 16–24 | Growth curve; Bayesian meter update; coach checkpoint at hour 24 |
| 24–32 | Driver explanation; sharing-flow demo; **feature freeze at 32** |
| 32–40 | Fill deck slide 3, one-pager, disclosure (c) |
| 40–48 | Demo video (3–5 min), pitch video, upload |
