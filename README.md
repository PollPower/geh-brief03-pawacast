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

Live dropped-pin forecasts (Overture fetch) are off unless `PAWACAST_LIVE_PIN=1`; default `0` for the hosted demo, with a 60-second timeout when on.

## Data credits

- **Renewvia operational dataset** (24 mini-grids, Kenya and Nigeria): Selby, N. *High-Frequency, Multi-Domain Operational Dataset for Community Solar Mini-Grids in Kenya and Nigeria.* Zenodo, 2026. https://doi.org/10.5281/zenodo.22149101 — CC BY-SA 4.0.
  A data descriptor with the same title has been submitted to *Scientific Data* (Oct 2026). **Cite the published descriptor once it is out; until then cite the Zenodo dataset** (Renewvia's stated preference). Anything we publish that is derived from this data is released under CC BY-SA 4.0 with attribution.
  Documentation and data dictionary: https://github.com/Renewvia-Energy/minigrid-dataset
  See [DATA_LICENSE.md](DATA_LICENSE.md).
- Overture Maps Foundation (ODbL / CDLA-Permissive); VIIRS annual night lights, OpenGeoHub (Zenodo 17294744, CC BY 4.0); GridFinder, Arderne et al. 2020 (Zenodo 3628142, CC BY 4.0); AMDA *Benchmarking Africa's Minigrids*; Blodgett et al. 2017; Wassie & Ahlgren 2024.

## Sharing meter data (sprint)

Operators share a site-month **record**, not a customer list. The proof shows
the operator's exact site-month total and customer count match readings it
committed to earlier, without revealing any customer's values. Privacy noise
is added after the proof, to the public release only. The published (noised)
figure is not itself proven.

Circuit compiles with compactc 0.30.0 (N_MAX 128, proving key 306 MB).
Circuit logic tested on 4 fixtures (valid; too few customers; wrong
commitment; non-zero padding). Not deployed; no on-chain proofs generated
during the sprint. See `zk/COMPILE.md` and `SHARING_DESIGN.md`.

Licence: [Apache-2.0](LICENSE). Renewvia-derived files in `results/` are CC BY-SA 4.0 — see [DATA_LICENSE.md](DATA_LICENSE.md).
