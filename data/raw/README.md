# Raw data

Raw source files are not redistributed. Obtain the files below and place them at the stated paths. Stages 2 to 5 of the pipeline run from `data/processed/` without them.

| Path | Contents | Source |
|---|---|---|
| `data/raw/cofer.csv` or `data/raw/cofer_api.csv` | IMF COFER. Either the data portal export (`cofer.csv`) or the SDMX 2.1 CSV from `https://api.imf.org/external/sdmx/2.1/data/IMF.STA,COFER/all` requested with `Accept: text/csv` (`cofer_api.csv`). If both are present, the file with the later final quarter is used. | IMF Data |
| `data/raw/sipri_milex.xlsx` | SIPRI Military Expenditure Database workbook, all sheets | SIPRI |
| `data/raw/sipri_tiv_imports.csv` | Importer TIV table, all recipients, 1950 onward | SIPRI Arms Transfers Database |
| `data/raw/sipri_traderegister.csv` | Trade register export | SIPRI Arms Transfers Database |
| `data/raw/sipri_arms/arms_transfers_dyad.csv` | Recipient-by-year TIV table | SIPRI Arms Transfers Database |
| `data/raw/sipri_arms/sipri_traderegister.csv` | Copy of the trade register | SIPRI Arms Transfers Database |
| `data/raw/swift/*.pdf` | RMB Tracker and Global Currency Tracker, monthly issues | Swift |
| `data/raw/unctad/US_MerchantFleet_*.csv`, `US_ShipBuilding_*.csv`, `US_LSCI_*.csv`, `US_ContPortThroughput_*.csv` | Maritime transport tables. File names are set in `src/parse_maritime.py`. | UNCTADstat |
| `data/raw/eia/EIA_world_oil_transit_chokepoints.pdf` | World Oil Transit Chokepoints | US EIA |
| `data/raw/eia/STEO_m.xlsx` | Short-Term Energy Outlook monthly workbook | US EIA |
| `data/raw/tsmc/FS*.pdf` | Consolidated condensed financial statements, quarterly | TSMC investor relations |
| `data/raw/nuclear/*.pdf` | FAS Nuclear Notebook: China 2025; China, United States, and Russia 2026. File names are set in `src/parse_security.py`. | Bulletin of the Atomic Scientists |
| `data/raw/nato/defexp2026en.xlsx` | Defence Expenditure of NATO Countries, 2026 edition | NATO |

The parsers range-check extracted values and stop on a failed check. PDF parsing requires the `pdftotext` utility (poppler).
