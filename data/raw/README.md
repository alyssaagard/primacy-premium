# Raw data acquisition

Raw source files are not redistributed in this repository, in keeping with each publisher's terms. Obtain the files below and place them at the stated paths; filenames may carry retrieval stamps, and the parsers locate content by structure, not by name, wherever the publisher allows it.

| Path | Contents | Where to obtain |
|---|---|---|
| `data/raw/cofer.csv` | IMF COFER bulk export, quarterly | IMF Data, COFER dataset |
| `data/raw/sipri_milex.xlsx` | SIPRI Military Expenditure workbook, all sheets | SIPRI databases |
| `data/raw/sipri_tiv_imports.csv` | SIPRI importer TIV table | SIPRI Arms Transfers Database |
| `data/raw/sipri_traderegister.csv` | SIPRI trade register export | SIPRI Arms Transfers Database |
| `data/raw/sipri_arms/arms_transfers_dyad.csv` | Recipient-by-year TIV matrix | SIPRI Arms Transfers Database |
| `data/raw/sipri_arms/sipri_traderegister.csv` | Copy of the trade register for the dependence table | SIPRI Arms Transfers Database |
| `data/raw/swift/*.pdf` | RMB Tracker and Global Currency Tracker monthly issues | Swift, on registration |
| `data/raw/unctad/*.csv` | Merchant fleet, ships built, LSCI, container throughput | UNCTADstat data centre |
| `data/raw/eia/EIA_world_oil_transit_chokepoints.pdf` | Chokepoint report | US EIA |
| `data/raw/eia/STEO_m.xlsx` | Short-Term Energy Outlook workbook | US EIA |
| `data/raw/tsmc/FS*.pdf` | Consolidated condensed financial statements, quarterly | TSMC investor relations |
| `data/raw/tsmc/1Q26_...TrendForce.pdf` | Foundry ranking public page (highlight only is used) | TrendForce |
| `data/raw/nuclear/*.pdf` | FAS Nuclear Notebook issues, 2025 China and 2026 China, US, Russia | Bulletin of the Atomic Scientists / FAS |
| `data/raw/nato/defexp2026en.xlsx` | Defence Expenditure of NATO Countries, 2026 | NATO |

The parsers validate what they extract and fail loudly on a redesign rather than shipping a wrong number.
