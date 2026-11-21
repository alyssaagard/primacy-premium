"""
parse_energy_semis.py
Stage 1f. Energy and semiconductor exposure series.

Input
  data/raw/eia/EIA_world_oil_transit_chokepoints.pdf
  data/raw/eia/STEO_m.xlsx      Short-Term Energy Outlook workbook
  data/raw/tsmc/FS*.pdf         TSMC quarterly financial statements
  data/raw/tsmc/*.pdf           TSMC quarterly earnings releases (used
                                only for quarters without statements)

Output
  data/processed/energy_chokepoints.csv      oil transit by chokepoint,
                                             million barrels per day
  data/processed/steo_brent.csv              Brent spot, monthly,
                                             observed and EIA forecast
  data/processed/semiconductor_channel.csv   TSMC net revenue, USD m,
                                             by quarter

Notes
* Requires the pdftotext utility (poppler).
* The chokepoint table is read from layout-preserved text. The year
  header is located by pattern.
* The STEO edition is read from the workbook.
* TSMC statements are deduplicated by quarter because audited and
  unaudited issues overlap. A statement replaces an earnings release
  for the same quarter; the basis column records which was used.
* Foundry market shares are not used. The TrendForce ranking available
  to this project is the public summary, which omits the share table,
  so no concentration index is computed. The public summary's note on
  capacity is recorded as text.
* Extracted values are range-checked.

Run: python src/parse_energy_semis.py
"""

import re
import subprocess
from pathlib import Path

import pandas as pd

from config import PROC as OUT, RAW

CHOKEPOINTS = ["Strait of Hormuz", "Strait of Malacca", "Suez Canal and SUMED Pipeline",
               "Bab el-Mandeb", "Danish Straits", "Turkish Straits", "Panama Canal",
               "Cape of Good Hope"]


def text_of(pdf: Path) -> str:
    return subprocess.run(["pdftotext", "-layout", str(pdf), "-"],
                          capture_output=True, text=True).stdout


def parse_chokepoints() -> pd.DataFrame:
    txt = text_of(RAW / "eia" / "EIA_world_oil_transit_chokepoints.pdf")
    lines = txt.splitlines()
    years, rows = None, []
    for i, ln in enumerate(lines):
        ys = re.findall(r"\b(20\d\d)\b", ln)
        if len(ys) >= 4 and years is None and any(
                cp in "\n".join(lines[i:i + 25]) for cp in CHOKEPOINTS):
            years = [int(y) for y in ys]
        if years:
            for cp in CHOKEPOINTS:
                if ln.strip().startswith(cp):
                    vals = re.findall(r"(\d+\.\d)", ln)
                    for y, v in zip(years, vals):
                        rows.append({"chokepoint": cp, "year": y,
                                     "flow_mbd": float(v)})
    df = pd.DataFrame(rows).drop_duplicates(["chokepoint", "year"])
    if df.empty or df.flow_mbd.max() > 40:
        raise ValueError("chokepoint table parse failed validation")
    df["source"] = "EIA, World Oil Transit Chokepoints, 2025"
    df.to_csv(OUT / "energy_chokepoints.csv", index=False)
    h = df[(df.chokepoint == "Strait of Hormuz")].sort_values("year").iloc[-1]
    print(f"energy_chokepoints.csv: {len(df)} rows; Hormuz {h.flow_mbd} mb/d in {int(h.year)}")
    return df


def parse_brent() -> pd.DataFrame:
    raw = pd.read_excel(RAW / "eia" / "STEO_m.xlsx", "2tab", header=None)
    hdr_y = raw.iloc[2, 2:].tolist()
    hdr_m = raw.iloc[3, 2:].tolist()
    months, year = [], None
    for y, m in zip(hdr_y, hdr_m):
        if pd.notna(y) and str(y).strip().isdigit():
            year = int(y)
        months.append(f"{year}-{pd.to_datetime(str(m), format='%b').month:02d}"
                      if year and isinstance(m, str) and m.strip() else None)
    row = raw[raw[0] == "BREPUUS"].iloc[0, 2:].tolist()
    rows = [{"month": mo, "brent_usd_bbl": float(v)}
            for mo, v in zip(months, row) if mo and pd.notna(v)]
    df = pd.DataFrame(rows)
    if not (30 < df.brent_usd_bbl.median() < 150):
        raise ValueError("Brent parse failed validation")
    title = " ".join(str(v) for v in raw.iloc[1].dropna())
    ed = re.search(r"Short-Term Energy Outlook\s*-\s*([A-Z][a-z]+ \d{4})", title)
    edition = ed.group(1) if ed else "edition not stated"
    df["source"] = f"EIA Short-Term Energy Outlook, {edition}, series BREPUUS"
    df.to_csv(OUT / "steo_brent.csv", index=False)
    print(f"steo_brent.csv: {len(df)} months, {df.month.iloc[0]} to "
          f"{df.month.iloc[-1]} ({edition} edition)")
    return df


RELEASE_QUARTER = re.compile(
    r"quarter\s+ended\s+([A-Z][a-z]+\s+\d{1,2},\s+\d{4})")
RELEASE_REVENUE = re.compile(
    r"In US dollars,\s+\w+\s+quarter\s+revenue\s+was\s+\$([\d.]+)\s+billion")


def parse_tsmc() -> pd.DataFrame:
    """Quarterly net revenue in USD millions.

    Financial statements (FS*.pdf) are the primary source. A quarterly
    earnings release is used for a quarter whose statements are absent;
    it states revenue in USD billions to two decimals. A statement
    replaces a release for the same quarter.
    """
    rows = []
    for pdf in sorted((RAW / "tsmc").glob("*.pdf")):
        txt = text_of(pdf)
        flat = " ".join(txt.split())
        if pdf.name.startswith("FS"):
            q = re.search(r"For the Three Months Ended\s+"
                          r"([A-Z][a-z]+ \d{1,2}, \d{4})", txt)
            rev = re.search(r"Net Revenue\s+\$\s*([\d,]+)", txt)
            if not (q and rev):
                print(f"  skip {pdf.name}: no quarterly revenue line")
                continue
            value = float(rev.group(1).replace(",", ""))
            basis, rank = "financial statements", 1
        elif "TSMC Reports" in flat:
            q, rev = RELEASE_QUARTER.search(flat), RELEASE_REVENUE.search(flat)
            if not (q and rev):
                print(f"  skip {pdf.name}: no quarterly revenue sentence")
                continue
            value = float(rev.group(1)) * 1000
            basis, rank = "earnings release", 0
        else:
            continue
        end = pd.to_datetime(" ".join(q.group(1).split()))
        rows.append({"quarter": f"{end.year}-Q{(end.month - 1) // 3 + 1}",
                     "tsmc_revenue_usd_m": value, "basis": basis,
                     "rank": rank, "source_file": pdf.name})
    df = (pd.DataFrame(rows).sort_values(["quarter", "rank", "source_file"])
          .drop_duplicates("quarter", keep="last").drop(columns="rank")
          .reset_index(drop=True))
    if df.empty or not (5_000 < df.tsmc_revenue_usd_m.median() < 60_000):
        raise ValueError("TSMC revenue parse failed validation")
    return df


def main() -> None:
    parse_chokepoints()
    parse_brent()
    tsmc = parse_tsmc()
    tsmc["rev_yoy_pct"] = round(
        100 * (tsmc.tsmc_revenue_usd_m / tsmc.tsmc_revenue_usd_m.shift(4) - 1), 1)
    tsmc["capacity_note"] = ("Taiwan foundries including TSMC, UMC, Vanguard and "
                             "PSMC raising prices amid tight capacity into 2027 "
                             "(TrendForce public summary, June 2026)")
    tsmc["source"] = ("TSMC consolidated condensed statements of comprehensive "
                      "income and quarterly earnings releases; TrendForce 1Q26 "
                      "public summary")
    tsmc.to_csv(OUT / "semiconductor_channel.csv", index=False)
    print(f"semiconductor_channel.csv: {len(tsmc)} quarters "
          f"({tsmc.quarter.iloc[0]} to {tsmc.quarter.iloc[-1]}); latest revenue "
          f"USD {tsmc.tsmc_revenue_usd_m.iloc[-1]:,.0f}m")


if __name__ == "__main__":
    main()
