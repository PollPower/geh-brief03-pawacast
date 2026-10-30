# PawaCast evaluation plan (frozen before the sprint)

Committed before the `geh2026-sprint-start` tag so the sprint result can't be tuned to the test sites after the fact.
Any change to this file after the tag is listed under "Deviations" at the bottom, with the reason.

## 1. What is being tested

The headline question from Brief 03: **how far is the forecast from actual metered demand at sites the model has never seen?**

Unit of evaluation: the **site** (not the customer). Target: measured kWh per customer per month, at the months the source measured it.

## 2. Test sets

| Set | Sites | Status before the sprint |
|---|---|---|
| **A — seen** | 6 Kenyan sites, Blodgett et al. 2017 (Barsaloi, Entesopia, Marti, Merile, Namba Koloo, Opiroi) | Pre-sprint model v0 (commit `258fbcb`) has been scored on these. Results are known, so they can no longer prove anything on their own. |
| **B — unseen** | Every other site with published measured consumption and a defensible location, listed in `pawacast/targets/public.py` before the tag (see section 7) | **No model has been run on these.** No evaluation code may touch set B before the sprint starts. |
| **C — aggregate** | AMDA country averages (KE, TZ, NG, SL, ...) | Check that the model's average over a country's candidate sites lands near AMDA's figure. |

The headline number reported to judges is from **set B**. Set A is reported alongside it, labelled "seen".

Sites with `geo_conf = low` are scored but also reported with them excluded, so a bad geocode can't drive the result.

## 3. Metrics (all reported, none dropped)

1. **Median absolute % error of P50** — the primary metric.
2. **P10–P90 coverage**: share of sites whose actual value falls inside the range. Target ~80%; much lower means overconfident, much higher means uselessly wide.
3. **Range width**: median P90 / P10 ratio. Reported so a wide range can't hide behind good coverage.
4. **Bias**: median of log(P50 / actual). Positive = over-forecasting, the error that leads to oversized systems.
5. **Per-site table**: every site, every number, including the bad ones.

## 4. Baselines (same sites, same metrics)

| Baseline | What it is |
|---|---|
| Brief midpoint | 20 kWh/customer/month for every site |
| AMDA country average | latest AMDA figure for the site's country, no site features |
| Household survey | the pre-connection survey prediction, where the source published one |
| PawaCast v0 | the pre-sprint model at commit `258fbcb` |

The sprint model only "improves" if it beats **both** the AMDA country average and v0 on set B.

## 5. Rules

- Test-set values are never used to set any parameter. Parameters come from AMDA, the brief, or published literature, and each one is cited in code.
- If a parameter is changed after seeing any set-B result, both the before and after numbers are reported, with the reason.
- Every site in set B is reported. Sites are only dropped for a reason written down before scoring (e.g. no location at all).
- Growth: the 24-month growth range is checked against every published growth observation (share inside the range).
- Meter update: any demo on simulated readings is labelled SIMULATED wherever it appears. If a real monthly series is obtained, the update is tested by hiding later months.

## 6. Outputs

`results/eval_setB.json`, `results/eval_setA.json`, `results/eval_sites.csv`, plus one chart: predicted range vs actual per site.

## 7. Set B freeze

Set B is whatever is in `pawacast/targets/public.py` at the `geh2026-sprint-start` tag. The git history shows when each site was added.

## Amendment 1 — Renewvia operational data (28 Oct 2026, before the sprint)

On 28 Oct 2026 Renewvia published an anonymised operational dataset for 24 of its community solar mini-grids in Kenya and Nigeria
(Selby, Zenodo 10.5281/zenodo.22149101, CC BY-SA 4.0): site coordinates, power-on dates, system size and capex, 11,942 customer
records with tariff class (residential / commercial / institution), and 15-minute smart-meter consumption.

This is the "metered consumption from live sites" the brief marks "partner needed", so it becomes the main evaluation data.
The split below was fixed **before any consumption value was read** — only names and coordinates were used — and is committed in
`pawacast/targets/renewvia_split.py` / `renewvia_split.csv`.

| Set | Sites | Use |
|---|---|---|
| **R-test** | Balep, Bendeghe-Afi, Opu, Ozuzu (Nigeria); Kapelbok (Kenya) — 5 sites, 3 groups | Scored once, at the end of the sprint. Never used for fitting or tuning. **Headline number.** |
| **R-train** | the other 19 sites, 13 groups | May be used to fit the model during the sprint. Also scored by leave-one-group-out cross-validation (secondary number). |
| **B** | Olenarau, Tum, Omorate (published) | Unchanged: unseen, scored at the end of the sprint. |
| **A** | 6 Blodgett sites | Unchanged: seen, reported for continuity. |

Grouping keeps near-neighbour sites (same settlement, same island cluster, within a few km) on the same side of the split.
Groups were assigned by hash, not by hand; the result happens to put only one Kenyan site in R-test, and it is kept as drawn.

Target on Renewvia sites: mean kWh per **customer meter** per month (meterRole = "Customer Meter"), computed from the gap-filled
15-minute product, by months since power-on. Totalizer, repeater and generator meters are excluded. Months with fewer than 10
active customer meters are dropped (same k ≥ 10 rule as SHARING_DESIGN.md).

Licence: CC BY-SA 4.0 — any derived dataset we publish (site-month aggregates) is released under CC BY-SA 4.0 with attribution.

## Deviations

### 31 Oct 2026 — TRAIN target uses gap-filled kWh for every site

Block 2 first treated `profile`/`uniform` slots as possibly invented and switched Emereoke and Kalobeyei Settlement to `kwh_cust_month_observed_only` (median |rel. diff.| 44% and 58%).

The clean product does **not** invent energy. It diffs the meter’s cumulative `energy` register and redistributes a known gap total onto missed 15-minute slots (`Data Dictionary.md`, sparkmeterreadings_clean: “redistributing gap energy”; “sum of `energy_kwh` … equals the sum of valid raw energy diffs to within 1 × 10⁻⁵”). Null/invalid diffs produce no rows. `observed_only` therefore undercounts real consumption.

**Change:** all TRAIN sites use gap-filled `kwh_cust_month`. R-test readings files were not opened.

**CV before the change** (observed_only on those two sites): PawaCast median APE 45.3%, coverage 83% (15/18), P90/P10 6.3, bias +0.08. Emereoke 12–24 month actual 2.09 kWh.

**CV after** (gap-filled for all 18): PawaCast median APE 46.1%, coverage 72% (13/18), P90/P10 4.93, bias +0.03. Emereoke 12–24 month actual 5.09 kWh. AMDA 52.0% / v0 55.5% / brief 20 kWh 266%. Model not frozen.

### 31 Oct 2026 — meter update on real Renewvia readings (declared before running)

The frozen day-one model and the one-time held-out score are not revisited. This block tests “forecast first, meters correct” on **real** site-month kWh (Renewvia, gap-filled), not simulated readings.

**Protocol (fixed before looking at update results):**

- Prior: frozen day-one P50 at month 18, σ = 0.6994248481546623 (OOF log residual sd). R-test uses the frozen full-TRAIN P50. Each TRAIN site uses its leave-one-group-out P50 from `results/cv_train_sites.csv` (the out-of-fold fit), not the full-TRAIN fit.
- Readings: the first k chronological site-months in the existing aggregate (`month` ascending), for k ∈ {1, 3, 6}. These are already restricted to ≥10 active customer meters and ≥20 observed days. k = 0 is the day-one forecast with no meters.
- Update: `pawacast/model/update.py` conjugate Normal update. **OBS_SIGMA stays 0.30** (pre-sprint; not tuned). Each reading is mapped to month 18 with the frozen growth slope `log1p(m) − log1p(18)`, slope = 0.08463413938171409, then passed to `update(..., g=0)` so the old 18% compound-annual growth is not applied on top.
- Target: the same months 12–24 median kWh/customer already used for day-one (R-test from the frozen score; TRAIN from LOGO). Posterior P50 is at month 18.
- Metrics: median APE of P50 and median P90/P10 width, for k = 0, 1, 3, 6, separately on R-test (n=5) and TRAIN-LOGO (n=18).
- Outputs: `results/meter_update_real.json`, `results/meter_update_real.png`. Chart labelled REAL meter data (Renewvia).
- No change to frozen β, σ, growth slope, or the headline R-test table.

### 31 Oct 2026 — optional v2 country intercepts (post-hoc, does not replace headline)

After the frozen score, a separate model added country intercepts α_KE, α_NG on top of log(AMDA), ridge-shrunk toward 0 (λ=2, same as v1 β). TRAIN LOGO and a labelled R-test score only. R-test had already been seen.

**TRAIN LOGO:** v2 median APE 50.2%, coverage 83% (15/18), P90/P10 6.23, bias −0.04. Frozen v1 was 46.1% / 83% / 6.01 / +0.03. v2 is worse on the pre-declared TRAIN criterion, so it would not have been chosen before seeing R-test.

**R-test (post-hoc, test already seen):** v2 median APE 79.6%, coverage 80% (4/5), width 6.23, bias +0.59. Frozen headline remains 136% / 60% / 6.01 / +0.86. The NG intercept (×0.76) fits low TRAIN Nigerian sites and then helps the low Nigerian test sites; that comparison is not a valid selection result.

Saved `results/v2_posthoc.json`. Frozen model and `results/eval_final.json` unchanged.
