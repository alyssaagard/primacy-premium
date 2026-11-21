# The Primacy Premium

Conditional forecasts of defense and commercial markets under Chinese military primacy, 2026 to 2035.

This repository contains a Python pipeline that estimates response parameters from historical data and simulates three pathways to Chinese military primacy by 2035. It tests whether allied defense expenditure and reserve currency composition depend on the pathway.

* Interactive results: `index.html`
* Report: `report.html`
* Static summary: `docs/static_preview.html`

## Research question

If China reaches nuclear parity with the United States and conventional military primacy in the Indo-Pacific by 2035, how do defense expenditure, arms transfers, and reserve currency composition change, and do the changes depend on the pathway by which primacy is reached?

## Design

Three pathways are imposed as assumptions. The study does not estimate their likelihood.

| Pathway | Definition |
|---|---|
| Accretion | Chinese and US real military expenditure continue at their compound growth rates of the last ten years of data. |
| Retrenchment | China as in accretion. US real expenditure contracts at the rate observed from 1988 to 1998. |
| Demonstration | Accretion, plus one event in a year drawn from 2028 to 2031. Reserve shares and allied expenditure growth repeat the changes observed in 2022. |

Two outcomes are simulated with 10,000 seeded draws per pathway: military expenditure by block (annual), and the US dollar and renminbi shares of official foreign exchange reserves (quarterly). Semiconductor, shipping, and energy exposure series are reported and not simulated.

The term conditional forecast is used because the outputs are distributions given an assumed pathway. No instance of the outcome exists in the historical record, so no model is fitted to it.

## Hypotheses and results

Verdicts are computed by the pipeline and written to `outputs/hypothesis_tests.json`. Values below are from the build of 2026-11-21.

| | Hypothesis | Statistic | Verdict |
|---|---|---|---|
| H1 | Allied defense expenditure in 2035 differs by pathway. | Median pathway separation of four scored outcomes, 0.74 sd, 2.2 times the dollar reserve share (0.34 sd). Descriptive; not a significance test. | Supported |
| H2 | Allied expenditure responds more strongly to US than to Chinese expenditure. | Pooled panel of 45 countries, 1991 to 2025: b_us 0.160 (se 0.091), b_cn -0.056 (se 0.075); one-sided p 0.12 for the difference in magnitudes. | Not supported at the 5 percent level |
| H3 | Reserve composition is the least pathway-sensitive outcome, and the dollar's decline accrues mainly to currencies other than the renminbi. | Expenditure coefficient +0.93 pp, 95 percent interval -0.94 to 2.80; dollar share separation 0.34 sd; renminbi 3.33 percent of payments (September 2026) against 2.11 percent of reserves (2026-Q2). | Supported on the available measures |

Notes on interpretation:

* H1 separation in NATO Europe and the hedging tier follows from the positive estimated coefficient on lagged US growth and from the post-2022 change in growth applied under demonstration. US expenditure differs across pathways by assumption.
* H2 depends on expenditure weighting. Unweighted, the difference in magnitudes is -0.014 (p 0.54). A specification restricted to US reductions gives p 0.03 in the full sample and p 0.73 from 1997; it is not treated as evidence.
* H3 does not compare reserves with the other commercial channels, which are not simulated.
* In 2025, US real expenditure fell 7.5 percent and NATO Europe's rose 15.6 percent, opposite to the co-movement the positive US coefficient implies.

## Method

1. **Data.** Seven parsers convert published sources to long-format tables, with range checks that stop the build on failure. Tier expenditure totals are chain-linked over members reported in consecutive years, so changes in SIPRI coverage do not appear as changes in spending.
2. **Estimation.** `calibrate.py`: the quarterly change in the dollar reserve share is regressed on the year-on-year change in the log China/US expenditure ratio and an indicator for 2022-Q1 and 2022-Q2, with Newey-West standard errors; the renminbi share is modeled in log-odds. `calibrate_layer2.py`: allied tier growth is regressed on lagged US and Chinese growth (simulation input), and H2 is tested on a country panel with fixed effects, a lagged dependent variable, own GDP growth, expenditure weights, and Driscoll-Kraay standard errors.
3. **Simulation.** `simulate.py` (reserve shares) and `simulate_layer2.py` (expenditure by block). Coefficients are drawn jointly from their estimated sampling distributions. Reserve innovations are resampled from regression residuals. Expenditure innovations are resampled by stationary bootstrap, jointly across blocks. The demonstration event date is random.
4. **Hypothesis assembly.** `build_hypothesis_panel.py` writes all statistics and evidence series to `data/processed/hypothesis_panel.csv` and the verdicts to `outputs/hypothesis_tests.json`.
5. **Output.** Four figures, the interactive page, the static summary, the report, and the data dictionary. The processed tables load directly into Power BI or Tableau.

## Repository structure

```
primacy-premium/
├── index.html                     interactive results page (data embedded)
├── report.html                    report
├── README.md
├── LICENSE.md                     CC BY-NC 4.0 (source data excluded)
├── CITATION.cff
├── REFERENCES.md                  source and software citations
├── DATA_DICTIONARY.md             generated from the build
├── requirements.txt
├── src/
│   ├── config.py                  paths, seed, tier membership
│   ├── tiers.py                   tier aggregation and country panel
│   ├── render.py                  template filling
│   ├── parse_cofer.py             1a  reserve composition
│   ├── parse_milex.py             1b  expenditure, tier and country panels
│   ├── parse_arms_transfers.py    1c  arms transfers
│   ├── parse_swift.py             1d  payments shares
│   ├── parse_maritime.py          1e  fleet, shipbuilding, connectivity
│   ├── parse_energy_semis.py      1f  chokepoints, Brent, TSMC
│   ├── parse_security.py          1g  NATO, nuclear, imports, events
│   ├── calibrate.py               2a  reserve channel
│   ├── calibrate_layer2.py        2b  allied response and H2 test
│   ├── simulate.py                3a  reserve shares
│   ├── simulate_layer2.py         3b  expenditure by block, H1
│   ├── build_hypothesis_panel.py  4   hypothesis dataset and verdicts
│   ├── make_figures.py            5   figures
│   ├── build_dashboard_data.py    5a  payload and register
│   ├── build_index.py             5b  index.html
│   ├── build_preview.py           5c  static summary
│   ├── build_data_dictionary.py   5d  DATA_DICTIONARY.md
│   └── build_report.py            5e  report.html
├── data/
│   ├── raw/                       source files (not redistributed)
│   └── processed/                 processed tables
├── outputs/                       estimates, simulation output, figures
└── docs/                          templates, payload.json, static summary
```

## Reproduction

Requirements: Python 3.10 or later, the packages in `requirements.txt`, and the `pdftotext` utility (poppler). Place the source files as listed in `data/raw/README.md`, then run:

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
python src/build_report.py
```

The simulations are seeded (20260724). Rerunning on the same input files and library versions reproduces the published figures; small floating-point differences can occur across platforms. Set the environment variable `PRIMACY_BUILD_DATE` to fix the build date written to the outputs.

Stages 2 to 5 run from the processed tables in this repository without the raw files.

## Limitations

* Both event responses in the demonstration pathway repeat a single episode (2022).
* The tier equations used in the expenditure simulation are static and their residuals are serially correlated, most strongly for NATO Europe. Most coefficient intervals include zero.
* The H2 regressors vary only over time, so the effective sample is 35 years.
* COFER shares are valued at current exchange rates and mix transactions with valuation changes.
* Chinese expenditure figures are SIPRI estimates. SIPRI does not report the United Arab Emirates after 2014.
* The renminbi model is estimated on 36 quarters and its simulated intervals are wide.

The report lists the corrections made since the first release (July 2026).

## Data

IMF COFER, 1999-Q1 to 2026-Q2. SIPRI Military Expenditure Database 1949 to 2025 (v1.2, April 2026) and Arms Transfers Database. Swift RMB Tracker and Global Currency Tracker, data months April 2024 to September 2026. NATO, Defence Expenditure of NATO Countries, 2026 edition. UNCTADstat maritime transport tables. US EIA, World Oil Transit Chokepoints and Short-Term Energy Outlook (November 2026). FAS Nuclear Notebook, 2025 and 2026. TSMC financial statements, 2024-Q1 to 2026-Q3. Joint War Committee circular JWLA-033 and Argus Media reporting on war risk premiums.

Full citations are in `REFERENCES.md`. Columns and units of every artifact are in `DATA_DICTIONARY.md`. Raw source files are not redistributed.

## License

Text, figures, and code are © 2026 Alyssa I. Agard and licensed CC BY-NC 4.0. The underlying source data are excluded from the license and are used with citation under their publishers' terms. See `LICENSE.md`.
