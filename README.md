# The Primacy Premium

Conditional forecasts of defense and commercial markets under Chinese military primacy, 2026 to 2035.

A Python modeling pipeline that asks one question of the historical record: if China attains nuclear parity and Indo-Pacific conventional primacy by 2035, how do global defense expenditure, arms transfer flows, and commercial risk pricing reallocate, and does the pathway to primacy condition those outcomes more strongly than the endpoint itself?

The interactive build is `index.html`, generated entirely from the pipeline's own artifacts. A typeset static preview is `docs/static_preview.html`.

## Argument, thesis, and hypotheses

Markets do not price whether the balance shifts. They price how. The model runs three pathways to one 2035 endpoint, gradual accretion, American retrenchment, and violent demonstration, and reports full distributions across ten thousand seeded draws each. Three hypotheses discipline the exercise, and each is tested in this build with its verdict written by the pipeline: H1, that identical endpoints reached by different pathways produce statistically distinguishable defense outcomes (supported on the median criterion, 2.3 times the reserve channel's separation, with the Indo-Pacific tier the mapped exception); H2, that American retrenchment moves allied budgets harder than Chinese growth alone (directionally supported in all three allied tiers, unresolved at annual frequency, one-sided p 0.22 to 0.35); and H3, that reserve composition is the slowest and least pathway-sensitive commercial channel (supported: a precisely estimated near-null defense coefficient, 0.36 sd pathway separation, and a live settlement-reserve gap of 1.11 percentage points as of June 2026).

## Why this is called conditional forecasting, not prediction

There is no training data for an event that has never occurred. The model therefore estimates response parameters from seven decades of history, imposes each scenario exogenously, and propagates parameter, innovation, and event-timing uncertainty jointly. Conditional forecasting with uncertainty propagation is the stronger epistemic position, and the project states it plainly.

## Methodology in five stages

1. **Data engineering.** Seven parsers turn fourteen source families into thirty validated artifacts: IMF COFER (with an independent share reconciliation that must pass to 0.05 pp or the build fails), the SIPRI expenditure workbook and both arms transfer files, twenty-seven monthly Swift trackers (the data month read from each document, never the filename), four UNCTAD maritime tables, the EIA chokepoint report and STEO workbook, nine TSMC quarterly statements, the NATO burden table, the FAS nuclear notebooks, and the curated event, war-risk, and alliance tables. Every extraction passes range gates so a source redesign fails loudly.
2. **Historical calibration.** Every parameter is estimated, none assumed. The reserve channel response is a Newey-West regression of quarterly dollar-share changes on the logged China to US expenditure ratio (`calibrate.py`); the alliance feedback system regresses each allied tier's real growth on both principals' lagged growth, HAC(3) over 1951 to 2025, alongside the 2022 mobilization differential and the named retrenchment windows (`calibrate_layer2.py`).
3. **Conditional simulation.** Two seeded engines: the reserve channel quarterly to 2035-Q4 (`simulate.py`), and a five-block system with endogenous allied budgets annually to 2035 (`simulate_layer2.py`), which scores the H1 test, projects arms demand through the measured delivery elasticity, and attaches the 2026 Gulf war-risk multiple (5.7x hull value) to demonstration events. Innovations are bootstrapped from measured residuals, keeping the true fat tails.
4. **Hypothesis assembly.** One tidy table, `data/processed/hypothesis_panel.csv`, holds every measurement behind H1, H2, and H3: tests, evidence, robustness, and context, filterable by hypothesis (`build_hypothesis_panel.py`). The verdicts live in `outputs/hypothesis_tests.json` and feed the page's ledger directly.
5. **Delivery.** Four static plates, the interactive page (every number injected by `build_dashboard_data.py` and `build_index.py`), and BI-ready exports for Power BI or Tableau. The repository remains the model of record.

## What the current build finds

The defense coefficient on the reserve channel is a precisely estimated near-null whose 95 percent interval spans zero, which is what H3 asserts. Median 2035 dollar shares sit within 2.1 points of each other across pathways inside an 80 percent band roughly 44 to 58 percent. The renminbi is where the roads diverge: 3.15 percent under accretion against 0.00 under a 2022-style demonstration, on the one measured precedent. The settlement side sharpens the point: the renminbi settles 3.1 percent of global payments and 8 percent of trade finance but holds 1.99 percent of reserves. With allied budgets endogenous, scored defense outcomes separate by a median 2.3 times the reserve channel, led by NATO Europe at 1.45 sd; the US coefficient exceeds the China coefficient in every allied tier while the live 2025 episode, US spending down 7.5 percent against NATO Europe up 15.6, shows substitution running ahead of the historical bandwagon pattern.

## Repository structure

```
primacy-premium/
├── index.html                     the interactive build (payload embedded)
├── favicon.ico, *.png             site icons (16, 32, apple-touch, android-chrome)
├── site.webmanifest               icon manifest for mobile home-screen installs
├── README.md
├── LICENSE.md                     CC BY-NC 4.0 (data excluded)
├── CITATION.cff                   cite-this-repository metadata
├── REFERENCES.md                  full source, software, and reuse citations
├── DATA_DICTIONARY.md             generated codebook for every artifact
├── .gitignore                     keeps raw publisher files out of the repo
├── requirements.txt
├── src/
│   ├── parse_cofer.py             stage 1a  reserves
│   ├── parse_milex.py             stage 1b  expenditure
│   ├── parse_arms_transfers.py    stage 1c  transfers and the deal register
│   ├── parse_swift.py             stage 1d  settlement, 27 tracker PDFs
│   ├── parse_maritime.py          stage 1e  fleet, shipbuilding, connectivity
│   ├── parse_energy_semis.py      stage 1f  chokepoints, Brent, TSMC
│   ├── parse_security.py          stage 1g  NATO, nuclear, dependence, events
│   ├── calibrate.py               stage 2a  reserve channel parameters
│   ├── calibrate_layer2.py        stage 2b  alliance feedback system
│   ├── simulate.py                stage 3a  reserve channel engine
│   ├── simulate_layer2.py         stage 3b  system and event engine, H1
│   ├── build_hypothesis_panel.py  stage 4   the unified hypothesis dataset
│   ├── make_figures.py            stage 5   four plates
│   ├── build_dashboard_data.py    stage 5a  payload and register
│   ├── build_index.py             stage 5b  index.html
│   ├── build_preview.py           stage 5c  static preview
│   └── build_data_dictionary.py   stage 5d  generated codebook
├── data/
│   ├── raw/                       place obtained sources here (see raw README)
│   └── processed/                 19 tidy tables, hypothesis_panel.csv the flagship
├── outputs/                       calibrations, fans, summaries, hypothesis_tests.json
└── docs/                          templates, payload.json, static_preview.html
```

## Reproduction

```
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python src/parse_cofer.py
python src/parse_milex.py
python src/parse_arms_transfers.py
python src/parse_swift.py
python src/parse_maritime.py
python src/parse_energy_semis.py
python src/parse_security.py
python src/calibrate.py
python src/calibrate_layer2.py
python src/simulate.py
python src/simulate_layer2.py
python src/build_hypothesis_panel.py
python src/make_figures.py
python src/build_dashboard_data.py
python src/build_index.py
python src/build_preview.py
python src/build_data_dictionary.py
```

The simulation is seeded (20260724), so a re-run on the same data vintages reproduces every number exactly. The register inside the page reads all thirty artifacts off disk with their row counts, and `build_dashboard_data.py` refuses to publish if any is missing.

## Publishing the preview with GitHub Pages

Upload the repository contents so `index.html` sits at the root, then Settings, Pages, deploy from branch, main, root. The page is self-contained except for the Plotly CDN.

## Sources and citation

GitHub renders a citation button from `CITATION.cff`. Full scholarly citations for every parsed source, the documentary evidence base, the software stack, and data reuse terms are in `REFERENCES.md`, and every artifact's columns, units, and construction are documented in `DATA_DICTIONARY.md`, which is generated from the build itself.

IMF, Currency Composition of Official Foreign Exchange Reserves, quarterly through 2026-Q1. SIPRI Military Expenditure Database 1949 to 2025 (v1.2, April 2026) and Arms Transfers Database, including the trade register; Chinese figures are SIPRI estimates. Swift, RMB Tracker and Global Currency Tracker, monthly, April 2024 data through June 2026 data. NATO, Defence Expenditure of NATO Countries, 2026. UNCTADstat maritime tables. US EIA, World Oil Transit Chokepoints and Short-Term Energy Outlook, July 2026. FAS Nuclear Notebook 2025 and 2026, with DOD China Military Power Report projections. TSMC consolidated condensed financial statements. TrendForce 1Q26 foundry ranking, public highlight only. Joint War Committee circular JWLA-033 and Argus Media war-risk reporting. Kiel Institute Ukraine Support Tracker as context for the 2022 mobilization case. Raw files are not redistributed, in keeping with the providers' terms; `data/raw/README.md` lists what to obtain and where to place it.

## Status and license

A complete build: five layers, thirty registered artifacts, three hypotheses tested with the caveats carried in the page itself. Estimates move with data vintages. Text, figures, and code are © 2026 Alyssa Agard, licensed CC BY-NC 4.0; the underlying publisher data are excluded from the license and used with citation under their own terms.
