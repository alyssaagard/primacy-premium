"""
parse_cofer.py
Stage 1a of the pipeline: IMF COFER, quarterly currency composition of
global foreign exchange reserves.

WHAT THIS SCRIPT DOES AND WHY
-----------------------------
The IMF publishes COFER as a wide "series per row, period per column"
export with 197 columns of mixed metadata and observations. That layout
is unusable for modeling. This script:

  1. Filters to the World aggregate (SERIES_CODE prefix G001), leaving
     the Advanced and Emerging aggregates for a later robustness check.
  2. Keeps two measures per currency:
        SHRO_PT  share of allocated reserves, in percent
        NV_USD   claims in US dollars, nominal
     Shares are the modeling target. Nominal claims are retained so the
     shares can be independently re-derived (claims / allocated total)
     as a validation step. The two must agree to within rounding.
  3. Melts quarterly columns (1999-Q1 through 2026-Q1) into a tidy long
     table: one row per (quarter, currency, measure).
  4. Writes two outputs:
        data/processed/cofer_quarterly_long.csv   tidy, BI ready
        data/processed/cofer_shares_wide.csv      one column per currency

MEASUREMENT NOTES THAT MATTER DOWNSTREAM
----------------------------------------
* Renminbi (CNY) is only separately identified from 2016-Q4, when the
  IMF began reporting it in COFER. Any RMB series must begin there, and
  models must not treat the pre-2016 zero as an observation.
* Shares are of ALLOCATED reserves. The allocated fraction of total
  reserves has itself risen over time as more reporters allocate, which
  is a composition effect the write-up must acknowledge.
* Valuation: COFER claims are reported at current exchange rates, so a
  weaker dollar mechanically lowers the USD share. A planned robustness series handles
  this with an exchange rate adjusted robustness series; the preview
  reports the headline unadjusted share, clearly labeled.

Run:  python src/parse_cofer.py
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "cofer.csv"
OUT = ROOT / "data" / "processed"

# COFER currency codes -> readable labels used across the project.
CURRENCIES = {
    "CI_USD": "USD",
    "CI_EUR": "EUR",
    "CI_CNY": "CNY",
    "CI_JPY": "JPY",
    "CI_GBP": "GBP",
    "CI_CAD": "CAD",
    "CI_AUD": "AUD",
    "CI_CHF": "CHF",
    "CI_OTHC": "OTHER",
    "CI_T": "TOTAL",
}

MEASURES = {"SHRO_PT": "share_pct", "NV_USD": "claims_usd_m"}


def quarter_cols(df: pd.DataFrame) -> list[str]:
    """Return the quarterly period columns, e.g. '1999-Q1', in order."""
    return [c for c in df.columns if "-Q" in c]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(RAW)

    # World aggregate, allocated reserves only. The series code encodes
    # everything we need: G001.AFXRA.<currency>.<measure>.<frequency>.
    world = df[df["SERIES_CODE"].str.startswith("G001.AFXRA")].copy()
    world = world[world["SERIES_CODE"].str.endswith(".Q")]

    parts = world["SERIES_CODE"].str.split(".", expand=True)
    world["ccy"] = parts[2].map(CURRENCIES)
    world["measure"] = parts[3].map(MEASURES)
    world = world.dropna(subset=["ccy", "measure"])

    qcols = quarter_cols(world)
    long = world.melt(
        id_vars=["ccy", "measure"],
        value_vars=qcols,
        var_name="quarter",
        value_name="value",
    ).dropna(subset=["value"])

    # Proper quarter-end timestamps for joins and plotting.
    long["date"] = (
        pd.PeriodIndex(long["quarter"].str.replace("-", ""), freq="Q")
        .to_timestamp(how="end")
        .normalize()
    )
    long = long.sort_values(["date", "ccy", "measure"]).reset_index(drop=True)
    long["source"] = "IMF COFER (IMF.STA COFER 7.0.1, retrieved 2026-07-24)"
    long.to_csv(OUT / "cofer_quarterly_long.csv", index=False)

    # Wide share table: the direct modeling input.
    shares = (
        long[long["measure"] == "share_pct"]
        .pivot_table(index=["quarter", "date"], columns="ccy", values="value")
        .reset_index()
    )
    shares.columns.name = None

    # VALIDATION: re-derive the USD share from nominal claims and confirm
    # it matches the published share to within 0.05 percentage points.
    claims = (
        long[long["measure"] == "claims_usd_m"]
        .pivot_table(index="quarter", columns="ccy", values="value")
    )
    derived = 100 * claims["USD"] / claims["TOTAL"]
    check = shares.set_index("quarter")["USD"].sub(derived).abs().max()
    assert check < 0.05, f"share reconciliation failed: max gap {check:.3f} pp"

    shares.to_csv(OUT / "cofer_shares_wide.csv", index=False)

    last = shares.iloc[-1]
    print(f"cofer_quarterly_long.csv  {len(long):,} rows")
    print(f"cofer_shares_wide.csv     {len(shares)} quarters "
          f"({shares['quarter'].iloc[0]} to {shares['quarter'].iloc[-1]})")
    print(f"reconciliation max gap    {check:.4f} pp (pass)")
    print(f"latest quarter {last['quarter']}: "
          f"USD {last['USD']:.2f}  EUR {last['EUR']:.2f}  "
          f"CNY {last['CNY']:.2f}  OTHER {last['OTHER']:.2f}")


if __name__ == "__main__":
    main()
