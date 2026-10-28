# Sprint prompts for Cursor (paste one per block; rules load automatically from .cursor/rules)

Do not run any of these before the `geh2026-sprint-start` tag exists (`git fetch --tags; git tag -l geh2026-sprint-start`).

---

## Block 1 (hours 00–05): data foundation

Confirm the tag `geh2026-sprint-start` exists on origin; stop if not. Then:
1. Inspect the schemas of 2–3 `data/raw/renewvia/sparkmeterreadings_clean_*.parquet` files and `customers.parquet` (columns, dtypes, time range, row counts). Show me before writing the pipeline.
2. Write `pawacast/targets/renewvia.py`: for every site, compute monthly kWh per active **customer meter** (meterRole "Customer Meter"), the number of active customer meters, the residential/commercial/institution mix, and months since `powerOnDate`. Use DuckDB with a memory limit; never load a whole readings file into pandas. Save `data/targets/renewvia_site_months.parquet`.
3. Seal the held-out data: the loader must refuse to return consumption for `role == "test"` sites unless `PAWACAST_FINAL_EVAL=1`. Add a test proving it raises.
4. Build site features for all 24 Renewvia sites and the 3 demo sites with `build_features` (cached).
5. Print a summary table for the TRAIN sites only (site, months of data, median kWh/customer/month, customers). Commit, push, update CHANGELOG (hours 00–05).

## Block 2 (hours 05–12): model

Using TRAIN sites only:
1. Fit a demand-range model: P10/P50/P90 kWh/customer/month at a given month since connection, from site features plus country/region and customer mix. Start with a hierarchical log-linear model with AMDA-informed priors; try LightGBM quantile only if it clearly helps under cross-validation.
2. Evaluate with leave-one-group-out CV over the 13 train groups (groups from `renewvia_split.py`). Report median absolute % error of P50, P10–P90 coverage, range width and bias, against the same baselines as EVAL_PLAN (20 kWh, AMDA country average, v0).
3. Keep it explainable: each prediction returns its drivers as multipliers with plain reasons.
4. Save `results/cv_train.json` and a per-site CSV. Commit, push, CHANGELOG.

## Block 3 (hours 12–16): the one-time held-out score

1. Freeze the model (record the commit hash in `results/model_freeze.txt`).
2. Run `PAWACAST_FINAL_EVAL=1 python -m pawacast.evaluate --final` scoring: R-test (5 Renewvia sites), set B (Olenarau, Tum, Omorate), set A (seen, for continuity), and the country-level check. Same metrics and baselines as EVAL_PLAN.
3. Save `results/eval_final.json`, `results/eval_sites.csv`, and a chart `results/eval_ranges.png` (predicted P10–P90 bar vs actual dot per site, PollPower colours).
4. Do NOT change the model after this. Commit, push, CHANGELOG. Print the headline numbers for the deck.

## Block 4 (hours 16–24): growth curve, drivers, cost, web app

1. Growth curve: fit kWh/customer vs months since power-on (0–24 and beyond) on TRAIN sites, with an uncertainty band; compare with published growth rates. Save `results/growth_curve.png` (sized for a deck card, transparent background) and JSON.
2. Top drivers: rank which inputs move the forecast most, in plain words. Save `results/top_drivers.json`.
3. Cost estimate from Renewvia capex: USD per kWp and per connection (median and range, by country), plus a simple sizing for Maji Moto at 100 households using the P50/P90. Save `results/cost_estimate.json`.
4. Build `app/streamlit_app.py` per UI_DESIGN.md: map (streamlit-folium), site panel, answer card, drivers bar chart, growth chart, meters-correct panel (simulated readings labelled SIMULATED), lender report download (REPORT_DESIGN.md, HTML to PDF), "How tested" panel reading `results/`. Pre-compute the demo sites. Run it locally and show me screenshots.

## Block 5 (hours 24–32): meter-data sharing flow

Per SHARING_DESIGN.md §6:
1. Record schema (JSON) and validator.
2. Aggregation script: per-customer monthly totals into a published record (k ≥ 10, rounding, differential-privacy noise). Demo on TRAIN Renewvia sites.
3. Compact circuit proving that the published sum and count match committed values and that count ≥ 10. Compile and test locally. Deploy to Midnight Preview only if time allows; ask first.
4. Ingest shared records into PawaCast (prior and growth). Commit, push, CHANGELOG. **Feature freeze at hour 32.**

## Block 6 (hours 32–40): ship

1. Deployment notes for OpenClaw: pm2 process `pawacast` on 127.0.0.1:8501 with `--max-memory-restart 700M`, then enable the nginx proxy block. Write `deploy/DEPLOY.md`.
2. README: what it does, how to run, results with links to `results/`, data credits and licences, prior work vs sprint work.
3. Final CHANGELOG pass. No new features.
