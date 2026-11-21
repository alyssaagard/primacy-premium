# 1. Summary

The Primacy Premium is a quantitative study of how defense expenditure, arms transfers, and reserve currency composition would change if China reached nuclear parity with the United States and conventional military primacy in the Indo-Pacific by 2035. It asks whether those changes depend on the pathway by which primacy is reached.

Three pathways are specified: gradual accretion, US retrenchment, and a military demonstration. Each is simulated from parameters estimated on historical data, with {{meta.draws|int}} seeded draws per pathway. Results are distributions conditional on the pathway. The pathways are assumptions; the study does not estimate how likely any of them is.

The pipeline consists of {{meta.n_scripts}} Python scripts and produces {{meta.n_artifacts}} registered artifacts. Three hypotheses are tested, with the following verdicts in this build ({{generated}}).

- H1, allied defense expenditure in 2035 differs by pathway: {{hyp.tests.H1.verdict}}. The median pathway separation of the scored outcomes is {{hyp.h1.median_sd}} standard deviations, {{hyp.h1.median_ratio}} times that of the dollar reserve share. The statistic describes the simulation and is not a significance test.
- H2, allied expenditure responds more strongly to US than to Chinese expenditure: {{hyp.tests.H2.verdict}}. In a pooled panel of {{hyp.h2.primary.n_countries}} countries the one-sided p value is {{hyp.h2.primary.p_one_sided|f2}}.
- H3, reserve composition is the least pathway-sensitive outcome and the dollar's decline accrues mainly to currencies other than the renminbi: {{hyp.tests.H3.verdict}}.

Section 8 lists the corrections made since the first release of July 2026.

# 2. Research Question and Design

## 2.1 Background

The study began as a scenario: the state of defense and commercial markets if China became the leading military and nuclear power. A scenario of that kind has no measurable dependent variable and no claim that could be shown to be false. Three changes turned it into a research design. The antecedent was defined by two separable thresholds, nuclear parity and regional conventional primacy. The dependent variables were specified as measurable series: expenditure by actor tier, arms transfer volumes and supplier concentration, and reserve currency shares. The single scenario was replaced by three pathways, so that the effect of the pathway can be examined.

One observation shaped the reserve channel. In the IMF COFER data the renminbi's share of reserves peaked at {{cofer.cny_peak_value}} percent in {{cofer.cny_peak_quarter}} and was {{cofer.cny_latest_value}} percent in {{cofer.latest_quarter}}. Over the full sample the dollar share fell from {{cofer.usd_first}} percent in {{cofer.first_quarter}} to {{cofer.usd_latest}} percent. Between 2016-Q4, when the renminbi was first reported separately, and {{cofer.latest_quarter}}, the dollar share changed by {{hyp.h3.share_change.USD|+f2}} percentage points, the renminbi share by {{hyp.h3.share_change.CNY|+f2}}, and the combined share of currencies other than the dollar, euro, yen, pound, and renminbi by {{rep.other_change|+f2}}. Most of the dollar's decline did not accrue to the renminbi. This is the basis of H3.

## 2.2 Question

If China reaches nuclear parity with the United States and conventional military primacy in the Indo-Pacific by 2035, how do defense expenditure, arms transfers, and reserve currency composition change, and do the changes depend on the pathway by which primacy is reached?

## 2.3 Thesis

Allied defense expenditure and reserve composition in 2035 depend on how Chinese primacy is reached, not only on whether it is reached. The institutional responses involved (alliance budgets, procurement, supplier choice, reserve management) are responses to the character of the transition.

## 2.4 Conditional forecasting

No state has reached the combination of nuclear parity and regional conventional primacy against the United States that the study assumes. No model can therefore be fitted to the outcome. The study instead estimates response parameters from observed history, imposes each pathway as an assumption, and reports the distribution of outcomes given that pathway. Three sources of uncertainty are propagated: sampling uncertainty in the estimated coefficients, period-to-period innovations resampled from estimated residuals, and the timing of the demonstration event. The outputs are conditional forecasts. They do not state that any pathway will occur.

## 2.5 Pathways

- Accretion. Chinese and US real military expenditure continue at their compound growth rates from {{kpis.cagr_start}} to {{kpis.year}}: {{kpis.cn_cagr|f1}} percent per year for China and {{kpis.us_cagr|f1}} percent for the United States.
- Retrenchment. Chinese expenditure as in accretion. US real expenditure contracts at {{peace_dividend.annual_rate_pct|f1}} percent per year, the rate observed from 1988 to 1998, when it fell {{rep.peace_total|f1}} percent in total.
- Demonstration. Accretion, plus one event in a year drawn uniformly from 2028 to 2031. In the reserve channel the event repeats the share changes observed in 2022-Q1 and 2022-Q2, the quarters in which Russian central bank assets were frozen, followed by the change in drift observed after 2022-Q1. In the expenditure simulation each allied tier receives its measured change in mean growth after February 2022, declining linearly to zero over four years.

The pathways share the premise of Chinese primacy by 2035. They do not impose an identical 2035 force balance. US expenditure in 2035 is lower under retrenchment than under the other pathways, so differences between retrenchment and the others reflect both the route and the resulting level of US expenditure.

## 2.6 Actor tiers

Expenditure is aggregated into six tiers: China, the United States, Indo-Pacific allies, NATO Europe, hedging middle powers, and Russia. Membership is fixed at current composition for the whole sample. NATO Europe therefore includes states that acceded after 1991.

Dollar measures are tier totals. SIPRI coverage of members changes over time; for example, the United Arab Emirates is not reported after 2014. A plain sum over reported members would contain level breaks that reflect coverage, not spending. Tier totals are therefore chain-linked: growth between two years is computed over members reported in both, and levels are obtained by applying those growth rates backward from the latest total. Intensity measures (share of GDP, per capita, share of government spending) are tier medians.

## 2.7 Commercial channels

Reserve currency composition is simulated. Three further channels are documented with measured exposure series and are not simulated.

- Semiconductors: TSMC quarterly net revenue, {{vintage.tsmc.0}} to {{vintage.tsmc.1}}; latest {{vintage.tsmc_latest_usd_m|int}} million US dollars ({{rep.tsmc_latest_basis}}).
- Shipping and war risk: merchant fleet, shipbuilding, liner connectivity, and container throughput from UNCTAD, and the change in the additional war risk premium during the 2026 Mideast Gulf episode.
- Energy: oil transit by chokepoint from the US Energy Information Administration (Strait of Hormuz {{rep.hormuz}} million barrels per day, Strait of Malacca {{rep.malacca}}, {{rep.chokepoint_year}}) and the Brent price path.

# 3. Hypotheses and Tests

Each hypothesis has a stated statistic and decision rule. Verdicts are computed by the pipeline and written to `outputs/hypothesis_tests.json`.

## 3.1 H1: allied defense expenditure in 2035 differs by pathway

Statistic. For each outcome, pathway separation is the range of the three pathway medians in 2035 divided by the mean within-pathway standard deviation. The scored outcomes are the three allied tiers and the allied share of world expenditure. US and Chinese expenditure are reported but not scored, because their paths differ across pathways by assumption.

Rule. H1 is recorded as supported if the median scored separation exceeds twice the separation of the dollar reserve share. The threshold is a convention. The statistic describes the simulated distributions; it is not a significance test and has no p value.

{{REP_H1_TABLE}}

Result. The median scored separation is {{hyp.h1.median_sd}} standard deviations, {{hyp.h1.median_ratio}} times the dollar reserve share ({{hyp.h1.reserve}}). H1 is {{hyp.tests.H1.verdict}}. Separation is largest for {{hyp.h1.max.name}} and smallest for {{hyp.h1.min.name}}. Separation in NATO Europe and the hedging tier arises from two model features: the positive estimated coefficient on lagged US growth, which lowers allied expenditure under retrenchment, and the post-2022 change in growth applied under demonstration.

## 3.2 H2: allied expenditure responds more strongly to US than to Chinese expenditure

Specification. The test uses a country-year panel of the three allied tiers, {{hyp.h2.primary.sample.0}} to {{hyp.h2.primary.sample.1}} ({{hyp.h2.primary.n_countries}} countries, {{hyp.h2.primary.n_obs|int}} observations). The sample starts in 1991 because SIPRI reports China from 1989. Real expenditure growth is regressed on the previous year's real growth of US and Chinese expenditure, the lagged dependent variable, the country's own real GDP growth, and country fixed effects. Observations are weighted by the country's share of pooled allied expenditure in the previous year, so that the estimate refers to aggregate allied expenditure. Standard errors are Driscoll-Kraay with three lags. The statistic is the difference between the absolute values of the two coefficients, with a delta-method standard error and a one-sided p value from the t distribution with T - 1 degrees of freedom.

Rule. H2 is supported if the one-sided p value is below {{hyp.h2.alpha}}.

{{REP_H2_TABLE}}

Result. The coefficient on lagged US growth is {{hyp.h2.primary.b_us}} (standard error {{hyp.h2.primary.se_us}}; two-sided p {{hyp.h2.primary.p_us_two_sided|f2}}). The coefficient on lagged Chinese growth is {{hyp.h2.primary.b_cn}} (standard error {{hyp.h2.primary.se_cn}}; two-sided p {{hyp.h2.primary.p_cn_two_sided|f2}}). The difference in magnitudes is {{hyp.h2.primary.abs_gap}} with one-sided p {{hyp.h2.primary.p_one_sided|f2}}. H2 is {{hyp.tests.H2.verdict}}.

Three points qualify the result. First, the two regressors vary only over time, so the effective sample is {{hyp.h2.primary.n_years}} years regardless of the number of countries. Second, the result depends on weighting: without expenditure weights the difference is {{hyp.h2.sensitivity.unweighted.abs_gap}} (p {{hyp.h2.sensitivity.unweighted.p_one_sided|f2}}). Third, a specification that separates US reductions from US increases gives p {{hyp.h2.sensitivity.us_reductions_only.p_one_sided|f2}} in the full sample but p {{hyp.h2.sensitivity.us_reductions_only_from_1997.p_one_sided|f2}} when the sample starts in 1997. That result depends on the years immediately after the Cold War, when US and European expenditure fell together, and is not treated as evidence for H2.

The estimated US coefficient is positive: allied expenditure has tended to move in the same direction as US expenditure one year earlier. In {{kpis.year}} the opposite occurred. US real expenditure changed by {{kpis.us_yoy_pct|+f1}} percent and NATO Europe's by {{rep.nato_last|+f1}} percent.

## 3.3 H3: reserve composition is the least pathway-sensitive outcome, and the dollar's decline accrues mainly to currencies other than the renminbi

Rule. H3 is recorded as supported on the available measures if three conditions hold: the 95 percent interval of the expenditure coefficient in the dollar share regression contains zero; the pathway separation of the dollar share is below the median scored expenditure separation; and the renminbi's share of payments exceeds its share of reserves in every month observed. The shipping, energy, and semiconductor channels are not simulated, so the comparison across commercial channels is not tested.

Result. A unit change in the year-on-year log China/US expenditure ratio is associated with a change of {{kpis.beta|+f2}} percentage points in the quarterly dollar share (95 percent interval {{kpis.beta_lo}} to {{kpis.beta_hi}}; {{kpis.nobs}} quarters; R-squared {{kpis.r2}}). The interval is wide and contains zero. The regression does not detect an effect of relative military expenditure on the dollar share; it also cannot exclude effects of either sign within the interval.

Median dollar shares in 2035-Q4 are {{endpoints.usd.accretion.median|f1}} percent under accretion, {{endpoints.usd.retrenchment.median|f1}} under retrenchment, and {{endpoints.usd.demonstration.median|f1}} under demonstration, a range of {{kpis.usd_median_range}} percentage points. The 80 percent interval under accretion is {{endpoints.usd.accretion.p10|f0}} to {{endpoints.usd.accretion.p90|f0}} percent. Pathway separation is {{kpis.separation}} standard deviations, below the median for expenditure outcomes ({{hyp.h1.median_sd}}).

In {{rep.gap_month}} the renminbi accounted for {{rep.swift_cny}} percent of global payments by value and {{rep.trade_finance}} percent of trade finance in Swift data, against {{rep.cofer_cny}} percent of reserves in {{cofer.latest_quarter}}, the latest COFER quarter, a difference of {{kpis.gap_pp}} percentage points between payments and reserve shares. The payments share exceeded the reserve share in all {{vintage.swift_issues}} months observed. H3 is {{hyp.tests.H3.verdict}}.

The renminbi share is simulated in log-odds. Its median in 2035-Q4 is {{endpoints.cny.accretion.median|f1}} percent under accretion (80 percent interval {{endpoints.cny.accretion.p10|f1}} to {{endpoints.cny.accretion.p90|f1}}) and {{endpoints.cny.demonstration.median|f1}} percent under demonstration ({{endpoints.cny.demonstration.p10|f1}} to {{endpoints.cny.demonstration.p90|f1}}). The demonstration result repeats the change in the renminbi share after 2022. It rests on one episode and should be read as an illustration of that precedent.

# 4. Data Sources

Raw source files are not redistributed. `data/raw/README.md` lists each file and where to obtain it; `REFERENCES.md` gives full citations.

## 4.1 Quantitative sources

- IMF, Currency Composition of Official Foreign Exchange Reserves (COFER), {{vintage.cofer.0}} to {{vintage.cofer.1}}. Shares and claims by currency. From the 2025-Q3 release the IMF imputes the previously unallocated portion, with revisions back to 2000-Q1, so shares refer to total foreign exchange reserves.
- SIPRI Military Expenditure Database, {{vintage.milex.0}} to {{vintage.milex.1}}, version 1.2. Chinese figures are SIPRI estimates.
- SIPRI Arms Transfers Database: trend-indicator value tables and the trade register. Supplier concentration is computed over five-year windows by year of order.
- Swift RMB Tracker and Global Currency Tracker, {{vintage.swift_issues}} monthly issues covering {{vintage.swift.0}} to {{vintage.swift.1}}.
- NATO, Defence Expenditure of NATO Countries, 2026 edition, Table 3: expenditure as a share of real GDP for {{rep.nato_allies}} allies, {{vintage.nato.0}} to {{vintage.nato.1}} (latest year estimated).
- UNCTADstat maritime transport tables: merchant fleet, ships built, Liner Shipping Connectivity Index, container port throughput.
- US Energy Information Administration: World Oil Transit Chokepoints and the Short-Term Energy Outlook ({{vintage.steo}}).
- TSMC consolidated condensed financial statements, quarterly. A quarter without statements is taken from the earnings release, which states revenue in US dollar billions to two decimals.
- Federation of American Scientists, Nuclear Notebook, 2025 and 2026 issues for China, the United States, and Russia, with US Department of Defense projections for China.

## 4.2 Event and pricing sources

Joint War Committee circular JWLA-033 (3 March 2026) and Argus Media reporting on war risk insurance. During the 2026 Mideast Gulf episode the additional war risk premium rose from 0.15 to 0.2 percent of hull value to about 1 percent. Using the midpoint of the earlier range, the multiple is {{hyp.war_multiple}}. The US Department of Defense annual report on China (2025) is the source for the exercise record and the projected Chinese warhead trajectory.

## 4.3 Context sources

Congressional Research Service reports on naval force structure, Chinese naval modernization, New START limits, and the 2025 Hague summit; analyses of the expiration of New START by RUSI, the Council on Foreign Relations, the Federation of American Scientists, and the Vienna Center for Disarmament and Non-Proliferation; and official statements on the expiration. These inform design choices and supply no model inputs. The Kiel Institute Ukraine Support Tracker provides context for the post-2022 change in allied expenditure growth.

## 4.4 A source not used quantitatively

The TrendForce foundry revenue ranking for the first quarter of 2026 was obtained to compute a Herfindahl index of foundry concentration. The version available to the project is the public summary, which omits the market share table. No concentration index is computed. The summary's statement that Taiwan foundries are raising prices amid tight capacity into 2027 is recorded as text, and TSMC's reported revenue is the quantitative series for the channel.

# 5. Data Construction

Seven parsers convert the sources to long-format tables. Extracted values are range-checked, and the build stops on a failed check.

## 5.1 Reserve composition

The COFER parser writes a long quarterly table and a wide share table. It accepts the IMF portal export or the SDMX API file. The dollar share is recomputed from claims and must match the published share within 0.05 percentage points.

## 5.2 Defense expenditure

The SIPRI parser reads five measures: constant 2024 US dollars, current dollars, share of GDP, per capita, and share of government spending. It writes a panel for the United States, China, Russia, and the world total; the six-tier panel described in section 2.6; and a country-year panel of the three allied tiers for the H2 test. Missing-value codes in the workbook are read as missing.

## 5.3 Arms transfers

The trend-indicator tables give world deliveries from 1950 and recipient-level imports. The trade register is aggregated to supplier shares and a Herfindahl index by five-year order window. In the {{rep.dep_window}} window the United States accounts for {{rep.dep_ip_us|f0}} percent of Indo-Pacific allied imports and {{rep.dep_nato_us|f0}} percent of NATO Europe's. Deliveries against orders in recent windows are incomplete.

## 5.4 Payments shares

The Swift parser extracts three values per issue: the renminbi and dollar shares of global payments by value, and the renminbi share of trade finance. Each issue reports the previous month, so the data month is read from the document text. The payments page carries two panels on one text line; the first ranked match is the global panel.

## 5.5 Maritime structure

Four UNCTAD exports are combined into one panel of {{rep.maritime_rows}} rows. The fleet, shipbuilding, and throughput exports contain group aggregates only, so China is derived as developing economies minus developing economies excluding China and is labelled as derived. On this measure China built {{rep.china_ship_share|f0}} percent of world gross tonnage in {{rep.ship_year}}.

## 5.6 Energy and semiconductors

The chokepoint table is read from layout-preserved text. The Short-Term Energy Outlook parser extracts monthly Brent prices, observed and forecast. The TSMC parser reads the quarter and net revenue from each statement and removes duplicate quarters; a statement replaces an earnings release for the same quarter.

## 5.7 Security tables

NATO expenditure shares; warhead stockpile estimates (China {{rep.cn_2025}} in 2025 and {{rep.cn_2026}} in 2026, with Department of Defense projections of {{rep.cn_2030|int}} by 2030 and {{rep.cn_2035|int}} by 2035; United States {{rep.us_stock|int}}; Russia {{rep.ru_stock|int}}); recipient-level arms imports; allied import dependence by order window; and three tables coded by hand from the cited documents: an event register of {{rep.n_events}} episodes, the war risk premium table, and an alliance commitment table of {{rep.n_alliance}} entries. The commitment values are a design input and are not estimated.

## 5.8 Hypothesis dataset

`data/processed/hypothesis_panel.csv` holds every test statistic, evidence series, and context value in one long table of {{rep.panel_rows|int}} rows with the columns hypothesis, role, series, scope, freq, period, value, unit, and source. Roles are test, evidence, input, robustness, and sensitivity.

{{REP_PANEL_TABLE}}

# 6. Estimation and Simulation

## 6.1 Reserve channel

The quarterly change in the dollar share is regressed on the year-on-year change in the log China/US expenditure ratio and an indicator for 2022-Q1 and 2022-Q2. The annual ratio is interpolated linearly in logs between year-end values. Standard errors are Newey-West with four lags. The renminbi share is modeled in the same way from 2017-Q1 in log-odds, because the share is close to zero and a model in percentage points can produce negative simulated shares. Reference episodes are computed for use in the pathways: the 1988 to 1998 US contraction, the 2022 share changes, compound growth over the last ten years, and mean quarterly share changes before and from 2022-Q1.

## 6.2 Allied response

For each allied tier, real growth is regressed on the previous year's US and Chinese real growth, {{vintage.feedback_sample.0}} to {{vintage.feedback_sample.1}}, with Newey-West standard errors (three lags). These equations are inputs to the simulation.

{{REP_TIER_TABLE}}

The equations are static, and their residuals are serially correlated; the Breusch-Godfrey test rejects no autocorrelation for NATO Europe. Most coefficient intervals contain zero. The change in mean growth from 2015-2021 to 2022 onward is {{rep.mob_nato|+f2}} percentage points for NATO Europe, {{rep.mob_hedge|+f2}} for hedging middle powers, and {{rep.mob_ip|+f2}} for Indo-Pacific allies.

Mean growth in three earlier windows of US contraction is reported for description. From 1969 to 1975 US real expenditure fell while all three allied tiers grew. From 1989 to 1998 and from 2011 to 2015 NATO Europe contracted with the United States ({{rep.win_pd_nato|+f1}} and {{rep.win_seq_nato|+f1}} percent per year) while the other two tiers grew. The record does not show a uniform allied response to US contraction.

## 6.3 Simulation

Reserve shares are simulated quarterly to 2035-Q4. Expenditure is simulated annually from {{meta.horizon.0}} to {{meta.horizon.1}} for six blocks: the United States, China, the three allied tiers, and the rest of the world, which includes Russia. The first simulated year uses the last observed growth of the United States and China as lagged values. Rest-of-world growth is set to its mean over the last ten years of data.

In both simulations, coefficients are drawn jointly from a normal distribution with the estimated covariance. Reserve channel innovations are resampled with replacement from the regression residuals. Expenditure innovations are resampled by stationary bootstrap with a mean run length of five years, applied to all six blocks together over their common sample ({{vintage.residual_sample.0}} to {{vintage.residual_sample.1}}); this preserves correlation across blocks and short-run serial correlation.

{{REP_ENDPOINT_TABLE}}

World arms deliveries are projected from simulated world expenditure with an estimated elasticity of delivery growth to expenditure growth of {{hyp.arms.elasticity.beta}} (standard error {{hyp.arms.elasticity.se}}). The war risk premium multiple of {{hyp.war_multiple}} is attached to demonstration events as a reference value.

## 6.4 Reproducibility

Both simulations are seeded ({{meta.seed}}). Each pathway in the expenditure simulation uses a fixed integer offset from the seed. An earlier version derived the offset from Python's string hash, which differs between processes; this was corrected before the first release. Rerunning the pipeline on the same input files and library versions reproduces the published figures. Small floating-point differences can occur across platforms.

# 7. Results Page

The interactive page (`index.html`) contains eight panels: expenditure by tier; annual real change; US expenditure from 1985 to 2000; reserve shares by currency; simulated reserve shares; arms deliveries and supplier concentration; the hypothesis ledger; and the hypothesis evidence panel, with one view per hypothesis. It also lists every registered artifact with its row count. All values are read from `docs/payload.json`, which is written by the pipeline; the template contains no data.

# 8. Changes Since the First Release

The first release (July 2026) contained the following errors and limitations, which this build corrects.

- Tier totals were sums over the members reported in each year. Changes in SIPRI coverage appeared as changes in spending; the largest was a fall of about 12 percent in the hedging tier in 2015, when the United Arab Emirates series ends. Tier totals are now chain-linked. The post-2022 change in growth for the hedging tier, which was affected, is now {{rep.mob_hedge|+f2}} percentage points.
- The H2 test was run separately on three tier aggregates with one-sided p values of 0.22 to 0.35, and the sample was described as 1951 to 2025 when it began in 1991. The test is now a single pooled country panel with a dynamic specification and standard errors that allow for cross-sectional and serial dependence. The one-sided p value is {{hyp.h2.primary.p_one_sided|f2}}.
- Simulated coefficients were drawn independently and the intercept was fixed. They are now drawn jointly with the estimated covariance.
- Growth rates were estimated as log differences and applied as percentage changes. Percentage changes are now used throughout.
- The first simulated year used ten-year mean growth of the United States and China as lagged values. It now uses the last observed growth.
- The simulated world total omitted Russia. Russia is now part of the rest-of-world block.
- Expenditure innovations were resampled independently by block and year from samples of different length. They are now resampled jointly in runs of consecutive years from the common sample.
- The renminbi share was simulated in percentage points and truncated at zero, which produced a median of exactly zero under demonstration. It is now simulated in log-odds.
- In the demonstration pathway the 2022 share changes were added to baseline drift. They now replace it in the event quarters.
- The H2 and H3 verdicts and several figures in the page text were fixed strings. All are now computed.
- Data were updated: COFER to {{vintage.cofer.1}} and the Short-Term Energy Outlook to the {{vintage.steo}} edition.

# 9. Limitations

- Both event responses repeat a single episode (2022). They illustrate that precedent and do not estimate a general response.
- The H1 statistic is descriptive. US expenditure differs across pathways by assumption, and the threshold of twice the reserve separation is a convention. The margin above the threshold in this build is small.
- In the H2 test the regressors of interest vary only over time, giving {{hyp.h2.primary.n_years}} effective observations. The result depends on expenditure weighting.
- The tier equations used in simulation are static with serially correlated residuals. The bootstrap carries persistence only within runs averaging five years.
- COFER shares are valued at current exchange rates and mix transactions with valuation changes. The flow attribution series is a partial check only. The 1999 quarters precede the IMF's imputation of unallocated reserves.
- The renminbi model is estimated on {{kpis.cny_nobs}} quarters, and its simulated intervals are wide.
- Chinese expenditure figures are SIPRI estimates. SIPRI does not report the United Arab Emirates after 2014, so the hedging tier excludes it in levels.
- Rest-of-world growth is set to its ten-year mean, a period that includes wartime expenditure growth in Russia and Ukraine.
- The semiconductor, shipping, and energy channels are not simulated. Foundry concentration is not computed.

# 10. Observable Checks

The following observations would contradict the model's assumptions or the interpretation of its results.

- Sustained allied expenditure growth during a US contraction. The tier equations imply lower allied growth after lower US growth; {{kpis.year}} is one contrary year.
- A falling US share of allied arms imports during a US contraction, which would indicate substitution away from US supply. The model does not represent this.
- Convergence of the renminbi's payments and reserve shares without capital account liberalization.
- A further decline in the dollar share absorbed mainly by the renminbi.
- War risk premium changes during Taiwan Strait exercises that differ materially from the 2026 Mideast Gulf multiple.

# 11. Implications

## 11.1 Planning

In the simulation, allied expenditure in 2035 differs across pathways by more than reserve composition does. If that holds, planning that conditions only on the date at which China reaches a given capability omits information relevant to allied budgets. The finding is conditional on the tier equations and on the single-episode event response, and it should be weighted accordingly.

## 11.2 Alliances

The pooled coefficient on lagged US expenditure growth is positive ({{hyp.h2.primary.b_us}}, two-sided p {{hyp.h2.primary.p_us_two_sided|f2}}), and the coefficient on lagged Chinese growth is not distinguishable from zero. The difference in magnitudes is not statistically significant at the 5 percent level, so the data do not establish that US expenditure is the stronger influence. The positive US coefficient implies that allies reduced expenditure after US reductions over 1991 to 2025. The {{kpis.year}} observations run the other way. If allied expenditure continues to rise while US expenditure falls, the historical relationship used in the retrenchment pathway will understate allied expenditure.

US suppliers account for {{rep.dep_ip_us|f0}} percent of Indo-Pacific allied arms imports and {{rep.dep_nato_us|f0}} percent of NATO Europe's in the {{rep.dep_window}} order window. Higher allied expenditure under US retrenchment therefore raises the question of which suppliers receive the additional orders. The study does not model this.

## 11.3 Financial statecraft

The reserve data do not support the view that the dollar's declining reserve share has accrued mainly to the renminbi. The renminbi's share of payments is higher than its share of reserves, which is consistent with invoicing and reserve holding having different determinants. The simulated decline of the renminbi share under demonstration rests on one episode and is not a general estimate of the effect of coercion on reserve demand.

## 11.4 Method

The study reports interval estimates, states its decision rules, and reports results that do not support its hypotheses. The reserve channel regression is an example: it does not detect an effect, and the interval is wide enough that moderate effects of either sign cannot be excluded.

# 12. Reproduction

The pipeline requires Python 3.10 or later with pandas, NumPy, SciPy, statsmodels, Matplotlib, and openpyxl, and the pdftotext utility. The run order is given in `README.md`: seven parsers, two estimation scripts, two simulation scripts, the hypothesis panel builder, the figure script, and the output scripts. The register lists {{meta.n_artifacts}} artifacts with {{meta.n_rows|int}} rows and keys. Text, figures, and code are licensed CC BY-NC 4.0. The underlying source data are excluded from the license and are used with citation under their publishers' terms.

# 13. Further Work

- Data pending: Swift tracker issues after {{vintage.swift.1}}. {{rep.tsmc_pending}}
- Historical cases. The Soviet attainment of strategic parity and the Anglo-German naval race are the closest precedents for H1. Until they are examined, H1 rests on the simulation.
- H2. Annual data give few effective observations. Budget data at higher frequency, or a design that uses cross-country variation in exposure to US commitments with year effects, would give a sharper test.
- A dynamic specification for the tier equations, to address the serial correlation in their residuals.
- Simulation of the shipping, energy, and semiconductor channels.
