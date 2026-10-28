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

## Deviations

None yet.
