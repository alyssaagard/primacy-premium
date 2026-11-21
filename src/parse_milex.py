"""
parse_milex.py
Stage 1b. SIPRI Military Expenditure Database.

Input
  data/raw/sipri_milex.xlsx

Output
  data/processed/milex_panel.csv          United States, China, Russia
                                          and the world total, constant
                                          2024 USD millions
  data/processed/milex_features.csv       China/US ratio and real growth
  data/processed/milex_tier_panel.csv     five measures by analytic tier
  data/processed/milex_country_panel.csv  country-year panel of the three
                                          allied tiers, used by the H2 test

Notes
* All growth rates and ratios use constant 2024 prices and exchange
  rates.
* "..." and "xxx" in the workbook are read as missing.
* SIPRI reports China from 1989 and Russia from 1992. Chinese figures
  are SIPRI estimates.
* The world total comes from the "Regional totals" sheet (USD billions,
  converted to millions). Header and row positions are located by
  content.
* Tier totals are chain-linked over matched members; see tiers.py.

Run: python src/parse_milex.py
"""

import pandas as pd

from config import PROC
from tiers import WORKBOOK, build_country_panel, build_tier_panel

COUNTRIES = {"United States of America": "USA", "China": "CHN",
             "Russia": "RUS"}
SOURCE = "SIPRI Military Expenditure Database 1949-2025, v1.2 (April 2026)"


def load_country_sheet() -> pd.DataFrame:
    df = pd.read_excel(WORKBOOK, sheet_name="Constant (2024) US$", header=5)
    df = df.rename(columns={df.columns[0]: "country"})
    df["country"] = df["country"].astype(str).str.strip()
    keep = df[df["country"].isin(COUNTRIES)].copy()
    keep["iso3"] = keep["country"].map(COUNTRIES)
    years = [c for c in keep.columns if isinstance(c, (int, float))]
    long = keep.melt(id_vars=["iso3"], value_vars=years, var_name="year",
                     value_name="milex_constusd_m")
    long["year"] = long["year"].astype(int)
    long["milex_constusd_m"] = pd.to_numeric(long["milex_constusd_m"],
                                             errors="coerce")
    return long.dropna(subset=["milex_constusd_m"])


def load_world_total() -> pd.DataFrame:
    raw = pd.read_excel(WORKBOOK, sheet_name="Regional totals", header=None)
    hdr = None
    for i in range(len(raw)):
        vals = pd.to_numeric(raw.iloc[i, 1:], errors="coerce")
        if vals.notna().sum() > 20 and vals.dropna().between(1900, 2100).all():
            hdr = i
            break
    world = raw.index[raw[0].astype(str).str.strip().eq("World")][0]
    out = pd.DataFrame({
        "iso3": "WORLD",
        "year": pd.to_numeric(raw.iloc[hdr, 1:], errors="coerce").values,
        "milex_constusd_m":
            pd.to_numeric(raw.iloc[world, 1:], errors="coerce").values * 1e3,
    }).dropna()
    out["year"] = out["year"].astype(int)
    # The last column repeats the final year at current prices; keep the
    # constant-price observation, which appears first.
    return out.drop_duplicates(subset="year", keep="first")


def main() -> None:
    PROC.mkdir(parents=True, exist_ok=True)
    panel = pd.concat([load_country_sheet(), load_world_total()])
    panel = panel.sort_values(["iso3", "year"]).reset_index(drop=True)
    panel["source"] = SOURCE
    panel.to_csv(PROC / "milex_panel.csv", index=False)

    wide = panel.pivot_table(index="year", columns="iso3",
                             values="milex_constusd_m")
    feats = pd.DataFrame(index=wide.index)
    feats["cn_us_ratio"] = wide["CHN"] / wide["USA"]
    feats["us_real_growth"] = wide["USA"].pct_change(fill_method=None)
    feats["cn_real_growth"] = wide["CHN"].pct_change(fill_method=None)
    feats["world_real_growth"] = wide["WORLD"].pct_change(fill_method=None)
    feats.reset_index().to_csv(PROC / "milex_features.csv", index=False)

    tiers = build_tier_panel()
    tiers.to_csv(PROC / "milex_tier_panel.csv", index=False)
    countries = build_country_panel()
    countries.to_csv(PROC / "milex_country_panel.csv", index=False)

    y = wide.index.max()
    print(f"milex_panel.csv          {len(panel):,} rows")
    print(f"milex_tier_panel.csv     {len(tiers):,} rows")
    print(f"milex_country_panel.csv  {len(countries):,} rows, "
          f"{countries.country.nunique()} countries, "
          f"{countries.year.min()} to {countries.year.max()}")
    print(f"{y}: USA {wide.loc[y, 'USA'] / 1e3:,.0f}  "
          f"CHN {wide.loc[y, 'CHN'] / 1e3:,.0f}  "
          f"RUS {wide.loc[y, 'RUS'] / 1e3:,.0f}  "
          f"WORLD {wide.loc[y, 'WORLD'] / 1e3:,.0f} (USD bn, constant 2024); "
          f"China/US ratio {feats.loc[y, 'cn_us_ratio']:.3f}")


if __name__ == "__main__":
    main()
