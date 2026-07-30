"""
parse_milex.py
Stage 1b of the pipeline: SIPRI Military Expenditure Database, 1949-2025.

WHAT THIS SCRIPT DOES AND WHY
-----------------------------
SIPRI ships a formatted Excel workbook meant for human reading: title
rows, footnote markers, "..." for unavailable data and "xxx" for years
in which a state did not exist. This script turns the sheet
"Constant (2024) US$" into a tidy country-year panel and appends the
world total from "Regional totals", because a consistent world series
only exists from 1988 in SIPRI's own estimation.

Constant dollar figures (2024 prices and exchange rates) are the right
basis for every comparison in this project: growth rates, ratios, and
elasticities must be real, not nominal.

DERIVED SERIES BUILT HERE
-------------------------
* milex_panel.csv        tidy country-year panel (USA, China, Russia,
                         plus the World total), constant 2024 USD m.
* milex_features.csv     the model's defense-side feature set:
      cn_us_ratio        China / USA expenditure ratio, the project's
                         headline accretion indicator
      us_real_growth     year over year real growth, USA
      cn_real_growth     year over year real growth, China
      world_real_growth  year over year real growth, world total

DATA HYGIENE
------------
* Soviet-era Russia values before 1992 are not comparable and are left
  out of the panel by construction (SIPRI reports Russia from 1992).
* "..." and "xxx" are coerced to NaN, never to zero. Treating missing
  as zero is the single most common error in secondary uses of SIPRI.
* Chinese figures are SIPRI estimates, not official budgets. The
  budget-opacity layer will carry official, SIPRI and PPP bands as a
  distribution;
  the preview uses the SIPRI estimate and says so.

Run:  python src/parse_milex.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "sipri_milex.xlsx"
OUT = ROOT / "data" / "processed"

COUNTRIES = {
    "United States of America": "USA",
    "China": "CHN",
    "Russia": "RUS",
}


def load_country_sheet() -> pd.DataFrame:
    """Country rows from 'Constant (2024) US$', header on spreadsheet row 6."""
    df = pd.read_excel(RAW, sheet_name="Constant (2024) US$", header=5)
    df = df.rename(columns={df.columns[0]: "country"})
    df["country"] = df["country"].astype(str).str.strip()
    keep = df[df["country"].isin(COUNTRIES)].copy()
    keep["iso3"] = keep["country"].map(COUNTRIES)

    year_cols = [c for c in keep.columns if isinstance(c, (int, float))]
    long = keep.melt(
        id_vars=["iso3"], value_vars=year_cols,
        var_name="year", value_name="milex_constusd_m",
    )
    long["year"] = long["year"].astype(int)
    # "..." and "xxx" arrive as strings; coerce to NaN, never zero.
    long["milex_constusd_m"] = pd.to_numeric(
        long["milex_constusd_m"], errors="coerce"
    )
    return long.dropna(subset=["milex_constusd_m"])


def load_world_total() -> pd.DataFrame:
    """World row from 'Regional totals'. Figures there are US$ billions;
    convert to millions so the panel has one unit."""
    raw = pd.read_excel(RAW, sheet_name="Regional totals", header=None)

    # Locate the header row (the one whose cells are years) and the row
    # labeled 'World'. Positions are found, not hard coded, so the
    # parser survives SIPRI's yearly re-layout.
    hdr_idx = None
    for i in range(len(raw)):
        vals = pd.to_numeric(raw.iloc[i, 1:], errors="coerce")
        if vals.notna().sum() > 20 and vals.dropna().between(1900, 2100).all():
            hdr_idx = i
            break
    world_idx = raw.index[
        raw[0].astype(str).str.strip().eq("World")
    ][0]

    years = pd.to_numeric(raw.iloc[hdr_idx, 1:], errors="coerce")
    values = pd.to_numeric(raw.iloc[world_idx, 1:], errors="coerce")
    out = pd.DataFrame({
        "iso3": "WORLD",
        "year": years.values,
        "milex_constusd_m": values.values * 1_000.0,
    }).dropna()
    out["year"] = out["year"].astype(int)
    # The final column of the SIPRI regional sheet repeats the last year
    # at current prices; drop any duplicate year, keeping the constant
    # price observation that appears first.
    return out.drop_duplicates(subset="year", keep="first")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    panel = pd.concat([load_country_sheet(), load_world_total()])
    panel = panel.sort_values(["iso3", "year"]).reset_index(drop=True)
    panel["source"] = "SIPRI Milex Database 1949-2025 (v1.2, April 2026)"
    panel.to_csv(OUT / "milex_panel.csv", index=False)

    wide = panel.pivot_table(
        index="year", columns="iso3", values="milex_constusd_m"
    )
    feats = pd.DataFrame(index=wide.index)
    feats["cn_us_ratio"] = wide["CHN"] / wide["USA"]
    feats["us_real_growth"] = wide["USA"].pct_change()
    feats["cn_real_growth"] = wide["CHN"].pct_change()
    feats["world_real_growth"] = wide["WORLD"].pct_change()
    feats = feats.reset_index()
    feats.to_csv(OUT / "milex_features.csv", index=False)

    y = wide.index.max()
    print(f"milex_panel.csv     {len(panel):,} rows, {panel.iso3.nunique()} series")
    print(f"latest year {y}:  USA {wide.loc[y,'USA']/1e3:,.0f}  "
          f"CHN {wide.loc[y,'CHN']/1e3:,.0f}  "
          f"RUS {wide.loc[y,'RUS']/1e3:,.0f}  "
          f"WORLD {wide.loc[y,'WORLD']/1e3:,.0f}  (US$ bn, constant 2024)")
    print(f"CN/US ratio {y}:   {feats.set_index('year').loc[y,'cn_us_ratio']:.3f}")
    r15 = wide.loc[y, "CHN"] / wide.loc[2015, "CHN"]
    print(f"China real growth 2015-{y}: {100*(r15**(1/(y-2015))-1):.1f} pct per year")


if __name__ == "__main__":
    main()
