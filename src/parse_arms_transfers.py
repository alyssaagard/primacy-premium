"""
parse_arms_transfers.py
Stage 1c of the pipeline: SIPRI Arms Transfers Database.

TWO RAW FILES, TWO DIFFERENT JOBS
---------------------------------
1. sipri_tiv_imports.csv
   The recipient-by-year matrix of delivered major conventional arms in
   SIPRI trend indicator values (TIV, millions). Ten preamble lines,
   then 'Recipient,1950,...,2025', closing with a 'Total world import'
   row. That closing row is the global transfer volume series, the
   project's system-level activity indicator, 1950-2025.

2. sipri_traderegister.csv
   The deal-level register: roughly 30,000 transfer records with
   supplier, recipient, order year, weapon, and delivered TIV. From it
   this script builds supplier market shares and a Herfindahl-Hirschman
   concentration index in five-year windows. Supplier concentration is
   one of the project's falsification tripwires: a world hedging
   against a US retrenchment pathway shows up first as supplier
   diversification.

WHY TIV AND NOT DOLLARS
-----------------------
TIV measures the volume of military capability transferred, using a
common unit cost per weapon type, precisely so that it is comparable
across suppliers and decades. It is not a financial value and is never
mixed with the SIPRI expenditure series in one unit. The two enter the
model as separate indicators.

PARSING HAZARDS HANDLED HERE
----------------------------
* cp1252 encoding in the register (SIPRI exports from Windows).
* Thousands separators and stray spaces in the totals row.
* '0' meaning 'between 0 and 0.5 TIV' is kept as numeric zero, while
  empty cells (no identified delivery) become NaN and are dropped from
  sums rather than counted as zeros.
* Multi-year delivery strings in the register ('2010-2013') are not
  needed for the shares built here, which aggregate delivered TIV by
  supplier over order-year windows.

Run:  python src/parse_arms_transfers.py
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"

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
    out["source"] = "SIPRI Arms Transfers Database (TIV, retrieved 2026-07-24)"
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
    # HHI near 1 means a near monopoly of supply; competitive markets
    # sit well below 0.15 on this scale.
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
    w = conc["window"].max()
    lead = conc[conc["window"] == w].iloc[0]
    print(f"arms_transfers_global.csv    {len(vol)} years "
          f"({vol.year.min()}-{vol.year.max()})")
    print(f"latest year {latest.year:.0f}: {latest.tiv_m:,.0f} TIV m")
    print(f"supplier_concentration.csv   windows "
          f"{conc.window.min()}-{conc.window.max()}")
    print(f"{w}s window: top supplier {lead.supplier} "
          f"({100*lead.share:.1f} pct), HHI {lead.hhi:.3f}")


if __name__ == "__main__":
    main()
