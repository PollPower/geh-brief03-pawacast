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
- Confirmed `geh2026-sprint-start` on origin (`e61ed0ac`). Inspected TRAIN-only clean-readings schemas (Akipelai, Lomekwi, Olkiramatian) plus customers/minigridprojects; did not open test-site consumption files (Balep, Bendeghe-Afi, Opu, Ozuzu, Kapelbok).
- Added `pawacast/targets/renewvia.py`: DuckDB site-month aggregator with build-time seal (test readings never opened unless `PAWACAST_FINAL_EVAL=1`), loader guard, partial-month kWh/day × 30.44, observed-slot active-meter rule, `kwh_cust_month_observed_only`. Train output `data/targets/renewvia_site_months_train.parquet`.
- Added `tests/test_renewvia_seal.py` proving the loader raises `HeldOutError` for test sites without the flag, and that the builder does not list test readings files. `duckdb` and `pytest` added to `requirements.txt`.
- Built TRAIN site-months (flag off): sealed Balep, Bendeghe-Afi, Opu, Kapelbok, Ozuzu (files not opened); skipped Emakalakala (no clean readings file). 18 train sites, 871 site-months → `data/targets/renewvia_site_months_train.parquet`. Summary in `results/renewvia_train_summary.csv`. Test parquet was not created.
- Cached site features for all 24 Renewvia sites (`data/features/renewvia.parquet`; coordinates only, including test) and reused the 3 demo-site cache (`data/features/demo_sites.parquet`). Preview in `results/renewvia_features_preview.csv`.

### Hours 05–12
- Imputation check (TRAIN): Emereoke median |observed_only/gapfilled − 1| = 44%, Kalobeyei Settlement 58% (both >15%). Those two sites use `kwh_cust_month_observed_only` for modelling. Logged in `results/cv_train.json`.
- Day-one target: median kWh/customer in months 12–24 after power-on. All 18 TRAIN sites had that window (none needed the earliest-12 fallback).
- Log-linear model with AMDA country offset (KE 3.7 / NG 11.0) and one fitted predictor, log(building count / 300), ridge λ=2. Footprint, grid distance, POIs and night lights dropped (weak or confounded on TRAIN). P10/P90 from residual log-sd (σ≈0.72), not v0 SIGMA.
- Leave-one-group-out CV over 13 TRAIN groups (`results/cv_train.json`, `results/cv_train_sites.csv`): PawaCast median APE 45%, coverage 83% (15/18), P90/P10 6.3, bias +0.08. AMDA 52% / 78% / 5.3 / +0.25; v0 55% / 56% / 5.3 / −0.01; brief 20 kWh 282%. Not frozen. Test sites not used.
- Growth: site intercept + common log1p(month) slope on TRAIN site-months. Common within-site growth ≈7%/year (near Blodgett 8%); 12→24 months only ≈3%. Published 8% / 21% / 47% all sit inside the wide per-site slope band. Figure `results/growth_curve.png`.
- Imputation decision (docs + TRAIN check on Emereoke / Kalobeyei Settlement): `profile`/`uniform` redistribute the cumulative `energy` register across comms gaps (conserved to 1e-5), they do not invent kWh. Reverted to gap-filled `kwh_cust_month` for **all** TRAIN sites. Emereoke 12–24 actual: 5.09 gap-filled vs 2.09 observed_only. Re-ran LOGO CV: PawaCast median APE 46.1%, coverage 72% (13/18), P90/P10 4.93, bias +0.03 (was 45.3% / 83% / 6.3 / +0.08 with observed_only on two sites). AMDA 52% / v0 55% / brief 20 kWh 266%. Logged under EVAL_PLAN Deviations. Not frozen. Test sites not opened.

- Range calibration (TRAIN LOGO only): P10/P90 from out-of-fold sigma of log(actual/P50), not in-sample residuals. Empirical P10/P90 of 18 residuals logged but not used (n=18 is jumpy). P50 unchanged. Re-ran CV: PawaCast median APE 46.1%, coverage 83% (15/18), P90/P10 6.01, bias +0.03 (was 46.1% / 72% / 4.93 / +0.03). AMDA 52% / v0 55% / brief 20 kWh 266%.

### Hours 12–16
- Model frozen at `c3df2c8` (`results/model_freeze.txt`, `results/model_frozen.json`). P50 formula, β_bld, OOF σ and growth slope must not change after this.

### Hours 16–24
### Hours 24–32 (feature freeze at 32)
### Hours 32–48
