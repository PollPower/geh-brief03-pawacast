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
- One-time held-out score (`PAWACAST_FINAL_EVAL=1`): built `renewvia_site_months_test.parquet` (5 sites, 198 months) with the frozen aggregator. Scored frozen coefficients only — no refit.
- **Headline R-test** (Balep, Bendeghe-Afi, Opu, Ozuzu, Kapelbok): PawaCast median APE 136%, coverage 60% (3/5), P90/P10 6.01, bias +0.86. AMDA 117% / 60% / 5.29 / +0.78; v0 195% / 40%; brief 20 kWh 295% / 20%. Ozuzu 14.6 vs P50 14.8; Kapelbok 1.00 vs 4.41 (outside); Bendeghe-Afi 4.07 vs P10 5.18 (just outside). Nigerian test sites sit well below the AMDA NG 11 kWh prior.
- Set B (Olenarau KE month 20; Tum and Omorate ET month 10, growth-aligned): PawaCast median APE 66.5%, coverage 33% (1/3), bias −1.09. AMDA 77% / 33%. Olenarau inside (3.74 vs 2.01); Tum 43.3 and Omorate 73.2 sit far above the EAST_SOUTH 10 kWh prior even after the building multiplier.
- Set A (seen, continuity): PawaCast median APE 37.4%, coverage 83% (5/6), bias +0.25. AMDA 47% / 83%; v0 60% / 83%.
- Country check (6 unlocated published sites): PawaCast without coordinates equals AMDA; median APE vs those published figures 61%.
- Artifacts: `results/eval_final.json`, `results/eval_sites.csv`, `results/eval_ranges.png`. Model not changed after the score.
- Declared the real-meter update protocol in EVAL_PLAN Deviations (OBS_SIGMA = 0.30, frozen P50/σ/growth, k = 0/1/3/6, R-test + TRAIN-LOGO). Not yet run.
- REAL meter update (`results/meter_update_real.json`, `results/meter_update_real.png`), OBS_SIGMA = 0.30 unchanged. Median APE / width — R-test n=5: k=0 136%/6.01, k=1 96.2%/2.03, k=3 63.8%/1.54, k=6 56.4%/1.36. TRAIN-LOGO n=18: k=0 46.1%/6.01, k=1 31.7%/2.03, k=3 28.1%/1.54, k=6 28.8%/1.36. Frozen model not changed; headline R-test table not rescored.
- Meter-update coverage and bias (no tuning): updated P10–P90 is overconfident. R-test coverage k=1/3/6 = 0%/20%/20%, bias +0.67/+0.49/+0.45. TRAIN-LOGO 56%/33%/28%, bias −0.12/−0.23/−0.17. Caption: “range after update is overconfident: 0% coverage (R-test) … 28% coverage (TRAIN-LOGO)”.
- Optional v2 (country intercepts shrunk toward AMDA, λ=2): TRAIN LOGO median APE 50.2% (worse than frozen 46.1%), coverage 83%, width 6.23. R-test **post-hoc, test already seen**: 79.6% APE, 80% coverage. Does not replace the headline. `results/v2_posthoc.json`. Logged under EVAL_PLAN Deviations.

### Hours 16–24
- Meter-update v2 (TRAIN-LOGO only): month-to-month log-sd 0.428, lag-1 ρ = 0.74, plus first-k→12–24 projection error. TRAIN-LOGO coverage at k=1/3/6 = 78%/78%/83% (was 56%/33%/28%), width 3.37/3.13/2.77, APE 34%/28%/26%. R-test **post-hoc, test already seen**: coverage 20%/40%/20%, APE 119%/115%/81%. Day-one model unchanged. `results/meter_update_v2.json`, chart shows frozen vs v2. Logged under EVAL_PLAN Deviations.
- Deck growth card `results/growth_curve_deck.png`: frozen TRAIN slope, months 0–24, median + band, caption “most sites flat after year 1”, transparent background.

### Hours 24–32 (feature freeze at 32)
### Hours 32–48
