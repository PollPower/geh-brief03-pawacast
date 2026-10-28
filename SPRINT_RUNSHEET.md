# Sprint run-sheet — Team PollPower, Brief 03

Start: **Fri 30 Oct 12:00 PM ET** = Sat 31 Oct 01:00 JST (Garrett) = Fri 30 Oct 19:00 EAT (Timothy, Jonathan).
End: **Sun 1 Nov 12:00 PM ET** = Mon 2 Nov 02:00 JST = Sun 1 Nov 20:00 EAT.
US daylight saving ends at 2:00 AM ET on 1 Nov, so the sprint is **49 real hours**. Our own deadline is **hour 46** (Sun 23:00 JST / 17:00 EAT) to leave upload margin.

Roles: **Garrett** — model, code, demo. **Timothy** — legal, data-sharing terms, outreach. **Jonathan** — community engagement, field sites, field footage.

## Before the start (done or due)

- [x] Repo, features, v0 model, EVAL_PLAN.md, SHARING_DESIGN.md, REPORT_DESIGN.md (pre-sprint, disclosed)
- [ ] Prior-work tag runs 29 Oct 00:05 JST (scheduled on throne) — check `prior-work-tags.txt`
- [ ] Garrett sends the DATA_REQUESTS.md emails (29 Oct)
- [ ] Garrett picks 3 demo locations with coordinates: a quiet pastoral village, a market town, a PollPower candidate site
- [ ] Kick-off 29 Oct 8 PM ET (30 Oct 09:00 JST): note the portal, file rules, judge repo access
- [ ] Coach requested in #innovators-digital-solutions-apps-ai-ml
- [ ] OpenClaw: pawacast.pollpower.energy DNS, TLS, placeholder page, Python env on relay (environment only)
- [ ] Sprint-start tag runs 31 Oct 01:00 JST (scheduled on throne)

## Hour by hour

| Hours | JST / EAT | Garrett | Timothy | Jonathan |
|---|---|---|---|---|
| 00–05 | Sat 01:00–06:00 / Fri 19:00–Sat 00:00 | Confirm brief choice in portal; build monthly kWh per customer for the 24 Renewvia sites (first read of consumption); pull features for Renewvia + set B sites | Log any data-request replies; start DPA note | Write up the 3 demo sites: what people use power for now, likely first purchases (Starter Q2/Q3) |
| 05–12 | Sat 06:00–13:00 / 00:00–07:00 | Improved model: business-demand signal, country/segment calibration (parameters from literature only) | Rest | Rest |
| 12–16 | Sat 13:00–17:00 / 07:00–11:00 | **Run EVAL_PLAN on set B** — first unseen-site number | Data-sharing agreement draft (SHARING_DESIGN §5) | Field footage for pitch: a site, a meter, a customer (consent first) |
| 16–24 | Sat 17:00–Sun 01:00 / 11:00–19:00 | **Web app** (UI_DESIGN.md): map, answer card, drivers, growth, meters-correct; lender report download | One-page summary draft | Community section of the pitch: what operators/communities need to share data |
| **24** | Sun 01:00 / Sat 19:00 | **Coach checkpoint**: show set-B result and plan | Join | Join |
| 24–32 | Sun 01:00–09:00 / Sat 19:00–Sun 03:00 | Sharing flow: record schema, aggregation, Compact proof (sum, count ≥ 10) | Legal review of sharing flow | Rest |
| **32** | Sun 09:00 / 03:00 | **Feature freeze** — no new features after this | | |
| 32–40 | Sun 09:00–17:00 / 03:00–11:00 | OpenClaw deploys the app to pawacast.pollpower.energy; fill deck slide 3; record demo video (3–5 min) in the web app | Finalise one-pager; fill disclosure (c) and (d) | Review deck from a community view |
| 40–46 | Sun 17:00–23:00 / 11:00–17:00 | Record pitch video (≤5 min); export deck PDF (≤5 slides) | Sign disclosure; check every link opens without sign-in | Sign disclosure |
| **46** | Sun 23:00 / 17:00 | **Upload all six deliverables** | Confirm receipt | |
| 46–49 | buffer | Fix anything the upload check finds | | |

## The six deliverables

| # | Deliverable | Owner | Source |
|---|---|---|---|
| 1 | Demo video, 3–5 min | Garrett | Web app walkthrough (UI_DESIGN.md §3) on Ewaso Ngiro, Narok town, Maji Moto |
| 2 | Pitch video, ≤5 min | Garrett + Jonathan | Deck + field footage |
| 3 | Deck PDF, ≤5 slides | Garrett | Revised 5-slide deck; slide 3 filled with set-B result |
| 4 | One-page summary PDF | Timothy | Brief metrics: error on held-out sites, growth, sustainability |
| 5 | Build files link | Garrett | PollPower/geh-brief03-pawacast (judge access arranged at Kick-off) + live app at pawacast.pollpower.energy |
| 6 | Disclosure statement | Timothy | PollPower_GEH_Disclosure_Statement.pdf — sections (c), (d) filled |

## Rules we hold ourselves to

- Every sprint feature is committed after the sprint-start tag; CHANGELOG.md updated at each block.
- EVAL_PLAN.md is followed as written; any deviation is logged at its bottom.
- Anything simulated is labelled SIMULATED on screen and in the deck.
