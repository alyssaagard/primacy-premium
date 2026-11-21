"""
parse_cofer.py
Stage 1a. IMF COFER: quarterly currency composition of official foreign
exchange reserves, world aggregate.

Input (either file; the one with the later final quarter is used)
  data/raw/cofer.csv       portal export, one series per row, periods
                           in columns, claims in USD millions
  data/raw/cofer_api.csv   SDMX 2.1 CSV from api.imf.org, one
                           observation per row, claims in USD

Output
  data/processed/cofer_quarterly_long.csv   quarter, currency, measure
  data/processed/cofer_shares_wide.csv      one column per currency

Measures kept: SHRO_PT (share, percent) and NV_USD (claims, converted to
USD millions). The USD share is recomputed from claims and must match
the published share within 0.05 percentage points or the build fails.

Notes
* The renminbi is identified separately from 2016-Q4. Earlier quarters
  are missing, not zero.
* From the 2025-Q3 release, with revisions back to 2000-Q1, the IMF
  imputes the formerly unallocated portion, so shares refer to total
  foreign exchange reserves.
* Claims are valued at current exchange rates. Share changes therefore
  mix transactions and valuation effects.

Run: python src/parse_cofer.py
"""

import pandas as pd

from config import PROC, RAW

CURRENCIES = {
    "CI_USD": "USD", "CI_EUR": "EUR", "CI_CNY": "CNY", "CI_JPY": "JPY",
    "CI_GBP": "GBP", "CI_CAD": "CAD", "CI_AUD": "AUD", "CI_CHF": "CHF",
    "CI_OTHC": "OTHER", "CI_T": "TOTAL",
}
MEASURES = {"SHRO_PT": "share_pct", "NV_USD": "claims_usd_m"}


def read_portal(path) -> pd.DataFrame:
    df = pd.read_csv(path)
    w = df[df["SERIES_CODE"].str.startswith("G001.AFXRA")
           & df["SERIES_CODE"].str.endswith(".Q")].copy()
    parts = w["SERIES_CODE"].str.split(".", expand=True)
    w["ccy"] = parts[2].map(CURRENCIES)
    w["measure"] = parts[3].map(MEASURES)
    w = w.dropna(subset=["ccy", "measure"])
    qcols = [c for c in w.columns if "-Q" in c]
    return w.melt(id_vars=["ccy", "measure"], value_vars=qcols,
                  var_name="quarter", value_name="value").dropna(
                      subset=["value"])


def read_api(path) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)
    w = df[(df.COUNTRY == "G001") & (df.INDICATOR == "AFXRA")
           & (df.FREQUENCY == "Q")].copy()
    w["ccy"] = w.FXR_CURRENCY.map(CURRENCIES)
    w["measure"] = w.TYPE_OF_TRANSFORMATION.map(MEASURES)
    w = w.dropna(subset=["ccy", "measure", "OBS_VALUE"])
    w["value"] = w.OBS_VALUE.astype(float)
    # The API reports claims in USD; the portal export in USD millions.
    is_claims = w.measure == "claims_usd_m"
    w.loc[is_claims, "value"] = w.loc[is_claims, "value"] / 1e6
    return w.rename(columns={"TIME_PERIOD": "quarter"})[
        ["ccy", "measure", "quarter", "value"]]


def load() -> tuple[pd.DataFrame, str]:
    candidates = []
    if (RAW / "cofer.csv").exists():
        candidates.append((read_portal(RAW / "cofer.csv"), "portal export"))
    if (RAW / "cofer_api.csv").exists():
        candidates.append((read_api(RAW / "cofer_api.csv"), "SDMX API"))
    if not candidates:
        raise SystemExit("no COFER file found in data/raw/")
    return max(candidates, key=lambda c: c[0].quarter.max())


def main() -> None:
    PROC.mkdir(parents=True, exist_ok=True)
    long, origin = load()
    long["date"] = (pd.PeriodIndex(long["quarter"].str.replace("-", ""),
                                   freq="Q").to_timestamp(how="end")
                    .normalize())
    long = long.sort_values(["date", "ccy", "measure"]).reset_index(drop=True)
    long["source"] = f"IMF COFER, dataset IMF.STA:COFER 7.0.1 ({origin})"
    long = long[["ccy", "measure", "quarter", "value", "date", "source"]]

    shares = (long[long.measure == "share_pct"]
              .pivot_table(index=["quarter", "date"], columns="ccy",
                           values="value").reset_index())
    shares.columns.name = None
    shares = shares.drop(columns=[c for c in ["TOTAL"] if c in shares])

    claims = long[long.measure == "claims_usd_m"].pivot_table(
        index="quarter", columns="ccy", values="value")
    derived = 100 * claims["USD"] / claims["TOTAL"]
    gap = shares.set_index("quarter")["USD"].sub(derived).abs().max()
    if not gap < 0.05:
        raise ValueError(f"share reconciliation failed: max gap {gap:.3f} pp")

    long.to_csv(PROC / "cofer_quarterly_long.csv", index=False)
    shares.to_csv(PROC / "cofer_shares_wide.csv", index=False)

    last = shares.iloc[-1]
    print(f"cofer_quarterly_long.csv  {len(long):,} rows ({origin})")
    print(f"cofer_shares_wide.csv     {len(shares)} quarters "
          f"({shares.quarter.iloc[0]} to {shares.quarter.iloc[-1]})")
    print(f"reconciliation max gap    {gap:.4f} pp")
    print(f"{last.quarter}: USD {last.USD:.2f}  EUR {last.EUR:.2f}  "
          f"CNY {last.CNY:.2f}  OTHER {last.OTHER:.2f}")


if __name__ == "__main__":
    main()
