# Changelog

Times are ET. The line between pre-sprint and sprint work is the git tag `geh2026-sprint-start`.

## Pre-sprint (before 30 Oct 2026, 12:00 PM ET) — disclosed as prior work

### 28 Oct 2026
- Repository created; design document (DESIGN.md), README, project layout.
- Open-source dependency inventory of PollPower platform repos (oss-inventory/).
- Site-feature pipeline from public data: Overture buildings and places, VIIRS night lights (2016/2020/2024), GridFinder distance to grid.
- Ground truth: no open site-level metered dataset found; loaded 8 named Kenyan sites (Blodgett et al. 2017, 6 geocoded) for held-out validation, AMDA country/segment benchmarks for priors, three published growth observations.
- Day-one range model (AMDA baseline x business mix x building size x night lights), 24-month growth curve, Bayesian meter update, CLI with lender-readable driver report.
- First held-out validation (6 Kenyan sites, not used for fitting): median error 60% for PawaCast vs 46% for the AMDA country average alone, 638% for the brief's 20 kWh midpoint, 375% for household surveys; 5 of 6 sites inside P10-P90.
- Sprint preparation (design only, no features): EVAL_PLAN.md (frozen evaluation protocol, set A seen / set B unseen), SHARING_DESIGN.md (meter-data sharing flow), REPORT_DESIGN.md (lender report layout), DATA_REQUESTS.md (data requests to AMDA, CrossBoundary, paper authors), SPRINT_RUNSHEET.md.
- UI_DESIGN.md: web app design (Streamlit, map-first) and hosting plan for pawacast.pollpower.energy. Design only; the app is built in the sprint.
- Demo locations chosen: Ewaso Ngiro, Narok town, Maji Moto (pawacast/targets/demo.py).
- Test set B frozen (data only, not scored by any model): Olenarau (KE, low-confidence location), Tum and Omorate (ET, Wassie & Ahlgren 2024). Five more published sites that cannot be located kept for the country-level check only. Evaluation code restricted to set A until the sprint.
- Meter-update demo on SIMULATED monthly readings around measured annual averages: median error 60% -> 4% after 3 months, range 77% narrower.

## Sprint (30 Oct 12:00 PM ET – 1 Nov 12:00 PM ET)

### Hours 00–05
### Hours 05–16
### Hours 16–24
### Hours 24–32 (feature freeze at 32)
### Hours 32–48
