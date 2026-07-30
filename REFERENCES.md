# References

Every source the pipeline parses, in citation form, followed by the documentary evidence base, the software stack, data reuse terms, and how to cite this repository. Retrieval dates are given because several sources are living databases whose vintages matter for exact reproduction.

## Parsed data sources

International Monetary Fund. *Currency Composition of Official Foreign Exchange Reserves (COFER)*, dataset IMF.STA COFER 7.0.1, quarterly series through 2026-Q1. Retrieved 24 July 2026.

Stockholm International Peace Research Institute. *SIPRI Military Expenditure Database, 1949 to 2025*, version 1.2, April 2026 release. Retrieved 24 July 2026. Chinese expenditure figures are SIPRI estimates.

Stockholm International Peace Research Institute. *SIPRI Arms Transfers Database*: trend-indicator-value import and export tables and the trade register of transfers of major conventional arms. Retrieved 24 and 29 July 2026.

Swift. *RMB Tracker* (issues through January 2026) and *Global Currency Tracker* (issues from February 2026), monthly, twenty-seven issues covering April 2024 through June 2026 data months.

NATO. *Defence Expenditure of NATO Countries (2014 to 2026)*, 2026 edition, Table 3 (defence expenditure as a share of real GDP); 2026 figures are estimates. Brussels: NATO Public Diplomacy Division, 2026.

UNCTAD. *UNCTADstat* maritime transport tables: merchant fleet by flag of registration (dead-weight tons, 1980 to 2026); ships built by country of building (gross tonnage, 2014 to 2025); Liner Shipping Connectivity Index (quarterly, 2006 to 2026); container port throughput (TEU, 2010 to 2024). Retrieved 29 July 2026.

U.S. Energy Information Administration. *World Oil Transit Chokepoints*. Washington, DC: EIA, 2025.

U.S. Energy Information Administration. *Short-Term Energy Outlook*, July 2026 edition, series BREPUUS (Brent spot average, monthly, observed and forecast through 2027).

Kristensen, Hans M., Matt Korda, Eliana Johns, and Mackenzie Knight. "Chinese Nuclear Weapons, 2025." *Bulletin of the Atomic Scientists* 81 (2025).

Kristensen, Hans M., Matt Korda, Eliana Johns, and Mackenzie Knight-Boyle. "Chinese Nuclear Weapons, 2026." *Bulletin of the Atomic Scientists* 82 (2026).

Kristensen, Hans M., Matt Korda, Eliana Johns, and Mackenzie Knight-Boyle. "United States Nuclear Weapons, 2026." *Bulletin of the Atomic Scientists* 82 (2026).

Kristensen, Hans M., Matt Korda, Eliana Johns, and Mackenzie Knight-Boyle. "Russian Nuclear Weapons, 2026." *Bulletin of the Atomic Scientists* 82 (2026).

Taiwan Semiconductor Manufacturing Company. *Consolidated Condensed Financial Statements*, quarterly issues, first quarter 2024 through second quarter 2026. Hsinchu: TSMC investor relations.

TrendForce. *1Q26 Revenue Ranking among Top 10 Global Foundries*, 8 June 2026. Public highlight only: the ranking table itself is paywalled and is not used; foundry concentration is therefore carried qualitatively in the model, as documented in the parser and the input register.

Joint War Committee. *Circular JWLA-033, JWC Listed Areas: Hull War, Piracy, Terrorism and Related Perils*, 3 March 2026. London: Lloyd's Market Association.

Argus Media. Explainer on war risk insurance and additional war risk premia in the Mideast Gulf, June 2026. Source of the 0.15 to 0.2 percent of hull value baseline and the roughly 1 percent wartime quote used as the demonstration repricing multiple.

## Documentary evidence base

These sources anchor the curated event, projection, and calibration tables and the design's qualitative claims; they are cited in the artifacts that draw on them.

U.S. Department of Defense. *Military and Security Developments Involving the People's Republic of China 2025: Annual Report to Congress*. Washington, DC, 2025. Source of the projected Chinese warhead trajectory and the exercise record.

*The Diplomat*. "The Growth of China's Navy." January 2026.

Seatrade Maritime News. Reporting on the March 2026 Joint War Committee listing extension. March 2026.

Kiel Institute for the World Economy. *The Ukraine Support Tracker*, 29th release, covering 24 January 2022 to 30 April 2026, Kiel Working Paper No. 2218. Kiel, 2026. Context for the 2022 mobilization calibration case.

Congressional Research Service reports consulted on force structure, naval modernization, New START central limits, and the 2025 Hague summit; Federation of American Scientists, RUSI, CFR, and VCDNP analyses of the New START expiration; and official statements on the treaty's 5 February 2026 expiration by the UN Secretary-General and the French Foreign Ministry.

## Software

Python 3 with pandas, NumPy, SciPy, statsmodels, Matplotlib, and openpyxl (versions pinned in `requirements.txt`). The interactive page renders with Plotly.js loaded from CDN. The simulation is seeded (20260724); two runs on the same data vintages are byte-identical.

## Data reuse and terms

The processed tables in `data/processed/` are derived, reshaped, and in several cases computed series, published here for verification and reuse with citation. Raw publisher files are deliberately not redistributed: IMF, SIPRI, Swift, TSMC, TrendForce, and the Bulletin retain their own terms, and `data/raw/README.md` explains exactly what to obtain and where to place it to re-run the pipeline. Anyone reusing the derived tables should cite both this repository and the relevant upstream sources above; the settlement-reserve gap, the flow-attribution series, the tier aggregates, and all simulation outputs are this project's own constructions and carry its license.

## Citing this repository

GitHub renders a citation button from `CITATION.cff`. In text:

Agard, Alyssa. *The Primacy Premium: Conditional Forecasts of Defense and Commercial Markets under Chinese Military Primacy, 2026 to 2035*, version 1.0.0. 2026. Code and derived data, CC BY-NC 4.0.

```bibtex
@misc{agard2026primacypremium,
  author  = {Agard, Alyssa},
  title   = {The Primacy Premium: Conditional Forecasts of Defense and
             Commercial Markets under Chinese Military Primacy, 2026 to 2035},
  year    = {2026},
  version = {1.0.0},
  note    = {Code and derived data, CC BY-NC 4.0. Underlying publisher
             data excluded and cited under their own terms.}
}
```
