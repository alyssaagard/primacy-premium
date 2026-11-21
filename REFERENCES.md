# References

Sources read by the pipeline, documentary sources, methods, and software. Retrieval dates are given for databases that are revised over time.

## Data sources read by the pipeline

International Monetary Fund. *Currency Composition of Official Foreign Exchange Reserves (COFER)*, dataset IMF.STA:COFER 7.0.1, quarterly, 1999-Q1 to 2026-Q2. Retrieved 21 November 2026 from the IMF SDMX API. From the 2025-Q3 release the unallocated portion is imputed, with revisions back to 2000-Q1.

Kwende, Glen, and Erin Nephew. "Improving the Analytical Usefulness of the IMF's COFER Data." IMF Technical Notes and Manuals 2025/14. Washington, DC: International Monetary Fund, November 2025. https://doi.org/10.5089/9798229004855.005

Stockholm International Peace Research Institute. *SIPRI Military Expenditure Database, 1949 to 2025*, version 1.2, April 2026. Retrieved 24 July 2026. Chinese expenditure figures are SIPRI estimates.

Stockholm International Peace Research Institute. *SIPRI Arms Transfers Database*: trend-indicator value tables of imports and the trade register of transfers of major conventional arms. Retrieved 24 and 29 July 2026.

Swift. *RMB Tracker* (issues to January 2026) and *Global Currency Tracker* (issues from February 2026). Monthly; thirty issues covering data months April 2024 to September 2026.

NATO. *Defence Expenditure of NATO Countries (2014 to 2026)*, 2026 edition, Table 3 (defence expenditure as a share of real GDP; 2026 figures are estimates). Brussels: NATO Public Diplomacy Division, 2026.

UNCTAD. *UNCTADstat* maritime transport tables: merchant fleet by flag of registration; ships built by country of building; Liner Shipping Connectivity Index; container port throughput. Retrieved 29 July 2026.

U.S. Energy Information Administration. *World Oil Transit Chokepoints*. Washington, DC: EIA, 2025.

U.S. Energy Information Administration. *Short-Term Energy Outlook*, November 2026 edition, series BREPUUS (Brent spot price, monthly, observed and forecast).

Kristensen, Hans M., Matt Korda, Eliana Johns, and Mackenzie Knight. "Chinese Nuclear Weapons, 2025." *Bulletin of the Atomic Scientists* 81 (2025).

Kristensen, Hans M., Matt Korda, Eliana Johns, and Mackenzie Knight-Boyle. "Chinese Nuclear Weapons, 2026." *Bulletin of the Atomic Scientists* 82 (2026).

Kristensen, Hans M., Matt Korda, Eliana Johns, and Mackenzie Knight-Boyle. "United States Nuclear Weapons, 2026." *Bulletin of the Atomic Scientists* 82 (2026).

Kristensen, Hans M., Matt Korda, Eliana Johns, and Mackenzie Knight-Boyle. "Russian Nuclear Weapons, 2026." *Bulletin of the Atomic Scientists* 82 (2026).

Taiwan Semiconductor Manufacturing Company. *Consolidated Condensed Financial Statements*, quarterly, first quarter 2024 to third quarter 2026. Hsinchu: TSMC.

TrendForce. *1Q26 Revenue Ranking among Top 10 Global Foundries*, 8 June 2026. Public summary only. The market share table is not available to this project and is not used.

Joint War Committee. *Circular JWLA-033, JWC Listed Areas: Hull War, Piracy, Terrorism and Related Perils*, 3 March 2026. London: Lloyd's Market Association.

Argus Media. Explainer on war risk insurance and additional war risk premiums in the Mideast Gulf, June 2026. Source of the premium before the episode (0.15 to 0.2 percent of hull value) and during it (about 1 percent).

## Documentary sources

U.S. Department of Defense. *Military and Security Developments Involving the People's Republic of China 2025: Annual Report to Congress*. Washington, DC, 2025. Source of the projected Chinese warhead trajectory and the exercise record.

*The Diplomat*. "The Growth of China's Navy." January 2026.

Seatrade Maritime News. Reporting on the March 2026 Joint War Committee listing extension. March 2026.

Kiel Institute for the World Economy. *The Ukraine Support Tracker*, 29th release, covering 24 January 2022 to 30 April 2026, Kiel Working Paper No. 2218. Kiel, 2026.

Congressional Research Service reports on naval force structure (RL32665), Chinese naval modernization (RL33153), New START central limits (IN12640), and the 2025 Hague summit (IN12566). Analyses of the expiration of New START by the Federation of American Scientists, RUSI, the Council on Foreign Relations, and the Vienna Center for Disarmament and Non-Proliferation. Statements on the expiration of 5 February 2026 by the UN Secretary-General and the French Foreign Ministry.

## Methods

Driscoll, John C., and Aart C. Kraay. "Consistent Covariance Matrix Estimation with Spatially Dependent Panel Data." *Review of Economics and Statistics* 80, no. 4 (1998): 549-560. https://doi.org/10.1162/003465398557825

Newey, Whitney K., and Kenneth D. West. "A Simple, Positive Semi-Definite, Heteroskedasticity and Autocorrelation Consistent Covariance Matrix." *Econometrica* 55, no. 3 (1987): 703-708. https://www.jstor.org/stable/1913610

Politis, Dimitris N., and Joseph P. Romano. "The Stationary Bootstrap." *Journal of the American Statistical Association* 89, no. 428 (1994): 1303-1313. https://doi.org/10.1080/01621459.1994.10476870

## Software

Python 3 with pandas, NumPy, SciPy, statsmodels, Matplotlib, and openpyxl (minimum versions in `requirements.txt`). PDF text extraction uses pdftotext (poppler). The interactive page uses Plotly.js loaded from a CDN. Simulation seed: 20260724.

## Data reuse

The tables in `data/processed/` are derived from the sources above and are published for verification and reuse with citation. Raw source files are not redistributed; `data/raw/README.md` lists what to obtain and where to place it. Reuse of the derived tables should cite this repository and the relevant upstream source. The settlement-reserve gap, the flow attribution series, the tier aggregates, and the simulation outputs are constructions of this project and are covered by its license.

## Citing this repository

GitHub renders a citation from `CITATION.cff`. In text:

Agard, Alyssa. *The Primacy Premium: Conditional Forecasts of Defense and Commercial Markets under Chinese Military Primacy, 2026 to 2035*, version 1.1.0. 2026. Code and derived data, CC BY-NC 4.0.

```bibtex
@misc{agard2026primacypremium,
  author  = {Agard, Alyssa},
  title   = {The Primacy Premium: Conditional Forecasts of Defense and
             Commercial Markets under Chinese Military Primacy, 2026 to 2035},
  year    = {2026},
  version = {1.1.0},
  note    = {Code and derived data, CC BY-NC 4.0. Underlying source
             data excluded and cited under their own terms.}
}
```
