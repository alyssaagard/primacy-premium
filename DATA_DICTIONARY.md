# Data dictionary

Every artifact the model produces or consumes, grouped as in the
page's input register, with row counts and columns read from the
files at generation time. This file is written by
`src/build_data_dictionary.py` from the same register the dashboard
publishes, and generation fails if any artifact is missing, so the
codebook cannot describe a build that does not exist. Sources are
cited in full in `REFERENCES.md`; reuse terms are stated there and
in the license.

## Reserve composition

### `data/processed/cofer_quarterly_long.csv`

IMF COFER 7.0.1, shares and nominal claims, tidied and reconciled. Rows or keys: 1,818.

Columns: `ccy` (str), `measure` (str), `quarter` (str), `value` (float64), `date` (str), `source` (str).

### `data/processed/cofer_shares_wide.csv`

Quarterly share matrix, 1999-Q1 to 2026-Q1. Feeds the reserve channel. Rows or keys: 109.

Columns: `quarter` (str), `date` (str), `AUD` (float64), `CAD` (float64), `CHF` (float64), `CNY` (float64), `EUR` (float64), `GBP` (float64), `JPY` (float64), `OTHER` (float64), `TOTAL` (float64), `USD` (float64).

### `data/processed/cofer_flow_attribution.csv`

Valuation robustness by flow attribution: each currency's share of the quarterly change in allocated claims. Exact FX adjustment needs price indices outside the evidence base; the limitation is documented. Rows or keys: 377.

Columns: `quarter` (str), `ccy` (str), `flow_share_pct` (float64), `source` (str).

### `data/processed/swift_settlement.csv`

Monthly renminbi payments and trade finance shares from 27 Swift tracker issues. The settlement leg of the H3 settlement-reserve gap. Rows or keys: 27.

Columns: `month` (str), `cny_payments_pct` (float64), `usd_payments_pct` (float64), `cny_trade_finance_pct` (float64), `source_file` (str), `source` (str).

## Defense expenditure

### `data/processed/milex_panel.csv`

SIPRI v1.2 constant 2024 US$, four headline actors plus world. Rows or keys: 185.

Columns: `iso3` (str), `year` (int64), `milex_constusd_m` (float64), `source` (str).

### `data/processed/milex_features.csv`

China to US ratio and real growth rates, the model's regressor. Rows or keys: 77.

Columns: `year` (int64), `cn_us_ratio` (float64), `us_real_growth` (float64), `cn_real_growth` (float64), `world_real_growth` (float64).

### `data/processed/milex_tier_panel.csv`

Five measures aggregated to the six analytic tiers, 1949 to 2025. Rows or keys: 1,553.

Columns: `tier` (str), `year` (int64), `value` (float64), `measure` (str), `agg` (str).

### `data/processed/nato_burden.csv`

Defence spending as share of real GDP per ally, 2014 to 2026e, from NATO's own 2026 release. Rows or keys: 403.

Columns: `ally` (str), `year` (int64), `pct_gdp` (float64), `estimate` (bool), `source` (str).

## Arms transfers

### `data/processed/arms_transfers_global.csv`

World deliveries in SIPRI trend indicator values, 1950 to 2025. Rows or keys: 76.

Columns: `year` (int64), `tiv_m` (float64), `source` (str).

### `data/processed/supplier_concentration.csv`

Supplier shares and Herfindahl index over five-year order windows. Rows or keys: 88.

Columns: `window` (int64), `supplier` (str), `tiv_delivered` (float64), `share` (float64), `hhi` (float64).

### `data/processed/arms_recipient_imports.csv`

Recipient-level import volumes, 2011 to 2025, tiered to the design. Rows or keys: 1,893.

Columns: `recipient` (str), `year` (int64), `tiv_m` (float64), `tier` (str), `source` (str).

### `data/processed/allied_import_dependence.csv`

US share and supplier Herfindahl of each allied tier's imports by five-year order window. The pathway II diversification tripwire's baseline. Rows or keys: 34.

Columns: `tier` (str), `window` (int64), `us_share` (float64), `supplier_hhi` (float64), `n_suppliers` (int64), `tiv_total` (float64), `source` (str).

## Commercial channels

### `data/processed/semiconductor_channel.csv`

Channel one. TSMC quarterly revenue from the company's own statements. Foundry concentration carried qualitatively: the ranking table in the evidence base is paywalled, so no Herfindahl is computed from it. Rows or keys: 10.

Columns: `quarter` (str), `tsmc_revenue_usd_m` (float64), `source_file` (str), `rev_yoy_pct` (float64), `capacity_note` (str), `source` (str).

### `data/processed/maritime_panel.csv`

Channel two structure: fleet, shipbuilding, connectivity, throughput. China derived as developing minus developing excluding China. Rows or keys: 644.

Columns: `series` (str), `economy` (str), `year` (int64), `value` (float64), `unit` (str), `source` (str).

### `data/processed/war_risk_events.csv`

Channel two pricing: the 2026 Mideast Gulf AWRP episode, 0.175 to 1.0 percent of hull value, the demonstration repricing calibration. Rows or keys: 1.

Columns: `episode` (str), `area` (str), `awrp_pre_pct_hull` (float64), `awrp_during_pct_hull` (float64), `multiple` (float64), `date` (str), `source` (str).

### `data/processed/energy_chokepoints.csv`

Channel three. Oil transit by chokepoint, million barrels per day. Rows or keys: 40.

Columns: `chokepoint` (str), `year` (int64), `flow_mbd` (float64), `source` (str).

### `data/processed/steo_brent.csv`

Brent monthly, observed and EIA forecast to 2027, the price baseline. Rows or keys: 72.

Columns: `month` (str), `brent_usd_bbl` (float64), `source` (str).

## Event study

### `data/processed/taiwan_strait_events.csv`

Exercise and repricing dates with documentary sources. Layer four's event list. Rows or keys: 7.

Columns: `date` (str), `event` (str), `kind` (str), `source` (str).

## System dynamics

### `data/processed/alliance_matrix.csv`

Treaty commitment structure by tier. A documented design input, not an estimate. Rows or keys: 28.

Columns: `tier` (str), `member` (str), `commitment` (float64), `basis` (str), `source` (str).

### `data/processed/nuclear_panel.csv`

Warhead counts and DOD projections defining the parity threshold. Rows or keys: 6.

Columns: `country` (str), `year` (int64), `stockpile` (int64), `kind` (str), `deployed_strategic` (float64), `source` (str).

### `outputs/calibration_layer2.json`

Allied feedback on lagged US and China growth, HAC(3), 1951 to 2025. Rows or keys: 6.

Top-level keys: `description`, `feedback`, `principal_blocks`, `demonstration_mobilization_2022`, `event_windows`, `h2_historical`.

### `outputs/layer2_residual_pools.csv`

Block residuals, resampled as the system simulation's innovations. Rows or keys: 252.

Columns: `block` (str), `resid` (float64).

### `outputs/layer2_fan.csv`

Percentile fans for five blocks by pathway and year to 2035. Rows or keys: 180.

Columns: `pathway` (str), `block` (str), `year` (int64), `p05` (float64), `p10` (float64), `p25` (float64), `p50` (float64), `p75` (float64), `p90` (float64), `p95` (float64).

### `outputs/layer2_summary.json`

Endpoint distributions, the H1 test, and the arms demand projection. Rows or keys: 10.

Top-level keys: `draws`, `seed`, `horizon`, `endpoints_2035_musd`, `allied_share_2035`, `h1`, `h2_simulation`, `arms_demand_2035`, `war_risk_event_multiplier`, `caveats`.

## Estimation

### `outputs/calibration.json`

Every estimated parameter with confidence intervals. Nothing assumed. Rows or keys: 5.

Top-level keys: `meta`, `latest_state`, `usd_regression`, `cny_regression`, `cases`.

### `outputs/innovation_pools.csv`

Regression residuals, resampled as bootstrap innovations. Rows or keys: 105.

Columns: `usd_resid` (float64), `cny_resid` (float64).

## Forecast

### `outputs/simulation_fan.csv`

Percentile fans by pathway, currency and quarter, to 2035-Q4. Rows or keys: 234.

Columns: `currency` (str), `pathway` (str), `quarter` (str), `p05` (float64), `p10` (float64), `p25` (float64), `p50` (float64), `p75` (float64), `p90` (float64), `p95` (float64).

### `outputs/simulation_summary.json`

Endpoint distributions and the reserve-channel separation statistic. Rows or keys: 5.

Top-level keys: `draws`, `seed`, `horizon`, `usd`, `cny`.

## Hypothesis tests

### `data/processed/hypothesis_panel.csv`

One tidy table holding every measurement behind H1, H2 and H3: tests, evidence, robustness and context, filterable by hypothesis. Rows or keys: 977.

Columns: `hypothesis` (str), `role` (str), `series` (str), `scope` (str), `freq` (str), `period` (str), `value` (float64), `unit` (str), `source` (str).

### `outputs/hypothesis_tests.json`

The three verdicts with statistics, machine readable, feeding the ledger. Rows or keys: 3.

Top-level keys: `H1`, `H2`, `H3`.

## The unified hypothesis dataset, in detail

`data/processed/hypothesis_panel.csv` is the single table that measures
every hypothesis. One row is one measurement, and the grammar is constant:

| column | meaning |
|---|---|
| `hypothesis` | `H1`, `H2`, `H3`, or `context` |
| `role` | `test` (a computed statistic), `evidence` (an observed series the test reads), `input` (a simulated quantity), or `robustness` (an alternative measurement guarding a caveat) |
| `series` | what is measured, e.g. `settlement_reserve_gap`, `feedback_b_us`, `pathway_separation` |
| `scope` | the actor, tier, currency, pathway, chokepoint, or window the row belongs to; pipe-separated when two dimensions apply |
| `freq` | the row's native frequency: `quarterly`, `monthly`, `annual`, `annual mean`, `window`, `endpoint`, or `event` |
| `period` | year, quarter (`2026-Q1`), month (`2026-06`), or a year range (`1969-1975`) |
| `value` | the number |
| `unit` | its unit, stated in full |
| `source` | the upstream source or pipeline script that produced it |

Filter on `hypothesis` to read one claim's complete case, test and
evidence together. Filter `role == "test"` for the statistics behind the
verdicts in `outputs/hypothesis_tests.json`. The `context` rows carry
the structural exposures the channels reference (warheads, chokepoint
flows, fabrication revenue, shipbuilding, connectivity, the Brent path,
and the war-risk multiple) so the dataset stands alone in a BI tool
without the rest of the repository.

Worth knowing when reusing:

The settlement-reserve gap is monthly Swift renminbi payments share
minus the COFER renminbi share of that month's quarter, with the latest
reported quarter carried forward for months COFER has not yet covered.
The flow-attribution robustness series is each currency's share of the
quarterly change in total allocated claims; it bounds, rather than
removes, the valuation caveat on stock shares. H1 separations are in
standard-deviation units of endpoint spread, scored on allied responses
only, with the imposed drivers reported as context. All simulated rows
descend from seed 20260724 and reproduce exactly.


Thirty artifacts, 9,225 rows and keys in all, every one
read off disk at build time.
