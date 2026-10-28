# PawaCast — mini-grid demand before building

Team PollPower's entry to the Global Energy Hackathon 2026, **Brief 03: Predict mini-grid demand before building** (Digital Solutions & AI track).

PawaCast gives a demand **range** (P10 / P50 / P90 kWh per customer per month) for any location from public data, a growth curve for the first 24 months after connection, and plain-language drivers a lender can review. Once a site has meters, readings narrow the range: *forecast first, meters correct.*

## Prior work vs sprint work

- Everything committed **before** the tag `geh2026-sprint-start` (30 Oct 2026, 12:00 PM ET) is pre-sprint work and is listed in section (b) of our disclosure statement.
- Everything **after** that tag was built during the 48-hour sprint and is listed in section (c).
- The PollPower platform repositories this builds on are tagged `geh2026-prior-work`.
- `CHANGELOG.md` records what was built and when.

## Layout

```
pawacast/        Python package
  features/      site features from public data (buildings, night lights, grid, POIs)
  targets/       ground-truth demand data loaders
  model/         range model, growth curve, meter update, drivers
tools/           one-off scripts (licence inventory, etc.)
oss-inventory/   open-source dependency inventory for the disclosure
data/            local cache, not committed
```

## Setup

```
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

Licence: to be decided before submission.
