"""
parse_swift.py
Stage 1d: extract the renminbi settlement series from the SWIFT trackers.

WHY THIS TABLE EXISTS
---------------------
H3 turns on a gap: the renminbi is used to settle trade but not held as
a reserve asset. COFER gives the reserve side. The settlement side lives
in Swift's monthly RMB Tracker (renamed Global Currency Tracker in
February 2026), published only as PDF. This parser reads every monthly
issue in data/raw/swift/ and extracts three numbers per month: the
renminbi's share of global payments, the dollar's share of global
payments, and the renminbi's share of trade finance.

PARSING NOTES
-------------
The trackers are two-column layouts, so a single text line can carry
both the global panel (left) and the ex-Eurozone panel (right). The
first ranked match on a line always belongs to the left panel, which is
the global payments series we want. Trade finance sits on its own page,
found by heading. Each issue reports the previous month's data, so the
data month is read from the document text itself, never inferred from
the filename. Older issues label the currency RMB, newer ones CNY; both
are accepted. Values are validated against sane ranges so a layout
change fails loudly instead of shipping a wrong series.
"""

import re
import subprocess
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "swift"
OUT = ROOT / "data" / "processed"

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

    # The global payments page carries the ranked table and, just above
    # it, the data month. Find the first page with a ranked USD line.
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

    # Validation gates: a redesigned layout should fail, not mislead.
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
    df["source"] = "Swift RMB Tracker / Global Currency Tracker (monthly PDFs)"
    df.to_csv(OUT / "swift_settlement.csv", index=False)
    print(f"swift_settlement.csv: {len(df)} months, "
          f"{df['month'].iloc[0]} to {df['month'].iloc[-1]}; "
          f"latest CNY payments {df['cny_payments_pct'].iloc[-1]}%")


if __name__ == "__main__":
    main()
