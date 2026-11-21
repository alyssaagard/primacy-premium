"""
parse_swift.py
Stage 1d. Swift RMB Tracker and Global Currency Tracker.

Input
  data/raw/swift/*.pdf   monthly issues (the RMB Tracker was renamed the
                         Global Currency Tracker in February 2026)

Output
  data/processed/swift_settlement.csv   one row per data month:
      cny_payments_pct        renminbi share of global payments value
      usd_payments_pct        US dollar share of global payments value
      cny_trade_finance_pct   renminbi share of trade finance value

Notes
* Requires the pdftotext utility (poppler).
* Each issue reports the previous month. The data month is read from
  the payments page of the document, not from the filename.
* The payments page has two panels on one text line: global payments
  (left) and payments excluding the eurozone (right). The first ranked
  match on a line is the global panel.
* Issues label the currency RMB or CNY; both are accepted.
* Extracted values are range-checked. A value outside the expected
  range stops the build.

Run: python src/parse_swift.py
"""

import re
import subprocess
from pathlib import Path

import pandas as pd

from config import PROC as OUT, RAW as RAW_ROOT

RAW = RAW_ROOT / "swift"

MONTHS = {m: i + 1 for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"])}

RANK_RE = re.compile(r"^\s*\d{1,2}\s+(CNY|RMB)\s+([\d.]+)%", re.M)
USD_RE = re.compile(r"^\s*1\s+USD\s+([\d.]+)%", re.M)
DATE_RE = re.compile(r"\b(January|February|March|April|May|June|July|August|"
                     r"September|October|November|December)\s+(20\d\d)\b")


def text_of(pdf: Path) -> str:
    return subprocess.run(["pdftotext", "-layout", str(pdf), "-"],
                          capture_output=True, text=True).stdout


def parse_issue(pdf: Path) -> dict | None:
    txt = text_of(pdf)
    pages = txt.split("\f")

    # The global payments page carries the ranked table and the data
    # month. It is the first page with a ranked USD line.
    gp = next((p for p in pages if USD_RE.search(p) and RANK_RE.search(p)), None)
    if gp is None:
        print(f"  skip {pdf.name}: no ranked payments table found")
        return None

    dm = DATE_RE.search(gp)
    if not dm:
        print(f"  skip {pdf.name}: no data month on the payments page")
        return None
    month = f"{int(dm.group(2))}-{MONTHS[dm.group(1)]:02d}"

    cny = float(RANK_RE.search(gp).group(2))
    usd = float(USD_RE.search(gp).group(1))

    tf_page = next((p for p in pages if "trade finance" in p.lower()
                    and RANK_RE.search(p)), None)
    tf = float(RANK_RE.search(tf_page).group(2)) if tf_page else None

    # Range checks.
    if not (0.5 <= cny <= 8.0):
        raise ValueError(f"{pdf.name}: CNY payments share {cny} out of range")
    if not (35.0 <= usd <= 70.0):
        raise ValueError(f"{pdf.name}: USD payments share {usd} out of range")
    if tf is not None and not (2.0 <= tf <= 15.0):
        raise ValueError(f"{pdf.name}: CNY trade finance share {tf} out of range")

    return {"month": month, "cny_payments_pct": cny, "usd_payments_pct": usd,
            "cny_trade_finance_pct": tf, "source_file": pdf.name}


def main() -> None:
    pdfs = sorted(RAW.glob("*.pdf"))
    if not pdfs:
        raise SystemExit("no tracker PDFs found in data/raw/swift/")
    rows = [r for p in pdfs if (r := parse_issue(p))]
    df = (pd.DataFrame(rows)
            .sort_values("month")
            .drop_duplicates("month", keep="last")
            .reset_index(drop=True))
    df["source"] = "Swift RMB Tracker / Global Currency Tracker, monthly issues"
    df.to_csv(OUT / "swift_settlement.csv", index=False)
    print(f"swift_settlement.csv: {len(df)} months, "
          f"{df['month'].iloc[0]} to {df['month'].iloc[-1]}; "
          f"latest CNY payments {df['cny_payments_pct'].iloc[-1]}%")


if __name__ == "__main__":
    main()
