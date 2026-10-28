# Meter-data sharing flow — design (pre-sprint)

Brief 03 deliverable: *"Proposal for how operators could share meter data safely."*
Root cause it answers: *"Operators do not share data. Metered consumption sits in private company systems, so each developer starts from scratch."*

This is a design only. Nothing here is built before the sprint.

## 1. What an operator shares, and what never leaves them

| Shared (public record) | Never shared |
|---|---|
| Site location, coarsened to an H3 cell (resolution 6, ~36 km²) | Exact coordinates |
| Month, and months since the site was commissioned | Customer names, phone numbers, meter IDs |
| Number of active customers, rounded to the nearest 5 | Any single customer's consumption |
| Mean kWh per customer, and P10 / P50 / P90 across customers | Tariffs, revenue, margins |
| Share of customers that are businesses (rounded to 10%) | Payment history |
| A proof that the numbers come from genuine meter readings | The readings themselves |

A record is only published if the site has **at least 10 active customers** that month (k-anonymity). Small noise (differential privacy, ε set per record) is added to the published statistics so no customer can be reverse-engineered from repeated releases.

## 2. Why anyone should believe the numbers

Two trust tiers, so operators without PollPower hardware can still join:

**Tier 1 — PollPower-metered sites (strongest).**
1. Each meter reading is signed on the chip by the gateway's secure element (Ed25519). Milestone II showed this on real hardware.
2. The Meter Authority has registered that gateway key. The EBT v8 contract only mints from readings that pass the three-check gate (secure element, Meter Authority, Producer Registry).
3. The operator builds the monthly record from those settled readings and submits a zero-knowledge proof on Midnight that:
   - the published total and count equal the sum and count of readings already committed in EBT settlement for that site and month;
   - the count is ≥ 10;
   - the published P10/P50/P90 are consistent with the committed per-customer totals.
   The proof reveals the statistics and nothing else.

**Tier 2 — other operators' meters (lighter).**
1. The operator exports monthly per-customer totals from their own metering platform (SteamaCo, SparkMeter, Odyssey export, etc.).
2. They sign the export with an operator key registered with the data cooperative, and commit a hash of it on-chain.
3. They submit the same zero-knowledge proof against that commitment. This proves the published statistics match what they committed; it does not prove the meters were honest. Records are labelled Tier 2 and weighted lower by the model.

## 3. How PawaCast uses shared records

- Records with a commissioning month feed the **growth curve** directly.
- Records become **training and test sites** for the day-one model, which is the data the brief marks "partner needed".
- For a new candidate site, records from nearby H3 cells shift its prior (spatial pooling), and the site's own records, once it has meters, narrow its range (the existing meter update).
- Every forecast states how many shared sites informed it, and their tiers, so a lender can see the evidence base.

## 4. Why an operator would share

- **Better forecasts for their own next site**, from everyone's data, not just their own.
- **Cheaper capital**: a lender can verify a site's performance record without a data room or site visit.
- **No competitive leak**: no customer data, tariffs, revenue or exact locations.
- A record shared is attributable to the operator, if they choose, as a track record for lenders.

## 5. Legal frame (Timothy)

- Kenya Data Protection Act 2019: published records are aggregated and anonymised; confirm they fall outside "personal data" with k ≥ 10, rounding and noise.
- A short data-sharing agreement: what is shared, licence (CC BY 4.0 for published records), right to withdraw future records, no re-identification.
- Customer notice: operators tell customers that anonymised site statistics may be shared.

## 6. Sprint build scope (hours 24–32)

1. Record schema (JSON) and validator.
2. Aggregation script: per-customer monthly totals → published record (k-threshold, rounding, noise).
3. Compact circuit: prove published sum and count match committed values, and count ≥ 10. Compile and test locally; deploy to Midnight Preview only if time allows.
4. PawaCast ingest: load shared records and use them in the prior and growth curve.
5. One-page explainer for operators and lenders.

Demo data for the sprint is **simulated and labelled as such**, unless a partner shares real records first.

## Open questions

- Is ε-noise acceptable to lenders, or do they need exact figures under NDA instead? Ask the coach.
- Can percentile proofs be done cheaply in Compact, or should the sprint prove sum and count only?
- Who runs the Tier 2 key registry? A PollPower-run registry at first, governed by the DAO lane later.
