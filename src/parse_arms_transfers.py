"""
parse_arms_transfers.py
Stage 1c. SIPRI Arms Transfers Database.

Input
  data/raw/sipri_tiv_imports.csv     recipient-by-year matrix of
                                     deliveries in trend-indicator values
                                     (TIV, millions), ending in a
                                     "Total world import" row
  data/raw/sipri_traderegister.csv   deal-level trade register

Output
  data/processed/arms_transfers_global.csv    world deliveries by year
  data/processed/supplier_concentration.csv   top five supplier shares
                                              and the Herfindahl index
                                              by five-year order window

Notes
* TIV measures the volume of transferred capability at a common unit
  cost per weapon type. It is not a financial value and is not combined
  with the expenditure series.
* The register is cp1252-encoded. Totals carry thousands separators.
* A recorded "0" (between 0 and 0.5 TIV) is kept as zero. Empty cells
  are missing and excluded from sums.
* Concentration is computed on delivered TIV grouped by year of order.
  Recent windows are incomplete because orders placed in them are still
  being delivered.

Run: python src/parse_arms_transfers.py
"""

import pandas as pd

from config import PROC as OUT, RAW

PREAMBLE_IMPORTS = 9   # metadata lines before the header row
PREAMBLE_REGISTER = 11


def global_volume() -> pd.DataFrame:
    df = pd.read_csv(RAW / "sipri_tiv_imports.csv", skiprows=PREAMBLE_IMPORTS)
    df = df.rename(columns={df.columns[0]: "recipient"})
    total = df[df["recipient"].astype(str).str.startswith("Total world")]
    if len(total) != 1:
        raise ValueError("expected exactly one 'Total world import' row")

    years = [c for c in df.columns if str(c).strip().isdigit()]
    out = total.melt(value_vars=years, var_name="year", value_name="tiv_m")
    out["year"] = out["year"].astype(int)
    out["tiv_m"] = pd.to_numeric(
        out["tiv_m"].astype(str).str.replace(",", "").str.strip(),
        errors="coerce",
    )
    out = out.dropna().sort_values("year").reset_index(drop=True)
    out["source"] = "SIPRI Arms Transfers Database, TIV of imports"
    return out


def supplier_concentration() -> pd.DataFrame:
    reg = pd.read_csv(
        RAW / "sipri_traderegister.csv",
        skiprows=PREAMBLE_REGISTER,
        encoding="cp1252",
    )
    reg.columns = [c.strip() for c in reg.columns]
    reg = reg.rename(columns={
        "Supplier": "supplier",
        "Year of order": "order_year",
        "SIPRI TIV of delivered weapons": "tiv_delivered",
    })
    reg["order_year"] = pd.to_numeric(reg["order_year"], errors="coerce")
    reg["tiv_delivered"] = pd.to_numeric(reg["tiv_delivered"], errors="coerce")
    reg = reg.dropna(subset=["supplier", "order_year", "tiv_delivered"])

    reg["window"] = (reg["order_year"] // 5 * 5).astype(int)
    grp = (
        reg.groupby(["window", "supplier"])["tiv_delivered"]
        .sum()
        .reset_index()
    )
    grp["share"] = grp.groupby("window")["tiv_delivered"].transform(
        lambda s: s / s.sum()
    )

    # Herfindahl-Hirschman index per window, on shares in [0, 1].
    hhi = (
        grp.assign(sq=lambda d: d["share"] ** 2)
        .groupby("window")["sq"].sum()
        .rename("hhi")
        .reset_index()
    )
    top = (
        grp.sort_values(["window", "share"], ascending=[True, False])
        .groupby("window")
        .head(5)
    )
    top = top.merge(hhi, on="window")
    return top


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    vol = global_volume()
    vol.to_csv(OUT / "arms_transfers_global.csv", index=False)

    conc = supplier_concentration()
    conc.to_csv(OUT / "supplier_concentration.csv", index=False)

    latest = vol.iloc[-1]
    print(f"arms_transfers_global.csv    {len(vol)} years "
          f"({vol.year.min()} to {vol.year.max()}); "
          f"{latest.year:.0f}: {latest.tiv_m:,.0f} TIV m")
    print(f"supplier_concentration.csv   windows "
          f"{conc.window.min()} to {conc.window.max()}")


if __name__ == "__main__":
    main()
