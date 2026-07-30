"""
parse_energy_semis.py
Stage 1f: the energy and semiconductor channels.

WHY THIS TABLE EXISTS
---------------------
Channels one and three of the design. Energy exposure is carried as
chokepoint throughput: the EIA's World Oil Transit Chokepoints report
gives crude and products flow through each strait in million barrels per
day, and the STEO workbook gives the Brent path the scenarios reprice
against. Semiconductor exposure is carried as concentration: TSMC's own
quarterly statements give the revenue level, and TrendForce's foundry
ranking gives the market shares from which a foundry Herfindahl index is
computed where sources allow. The demonstration pathway's commercial
bite runs through exactly these numbers: the share of world oil passing
Hormuz and Malacca, and the fabrication revenue sitting on Taiwan.

One descope is recorded here rather than papered over: the TrendForce
foundry ranking in the evidence base is the report's public preview, and
its market share table is withheld behind the paywall. A Herfindahl
index cannot be computed from a redacted table, so foundry
concentration is carried qualitatively (the report's own public
highlight that Taiwan foundries are raising prices amid tight capacity
into 2027) while the quantitative exposure variable is TSMC's audited
and unaudited quarterly revenue, which the company itself publishes.

PARSING NOTES
-------------
The EIA table is a layout-preserved text grid; the year header is
located by pattern, not position. TSMC statements are parsed per file
for the quarter label and the USD net revenue figure, then deduplicated
by quarter since audited and unaudited issues overlap. All extracted
values pass range gates so a source redesign fails loudly.
"""

import re
import subprocess
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"

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
    df["source"] = "EIA Short-Term Energy Outlook, July 2026, series BREPUUS"
    df.to_csv(OUT / "steo_brent.csv", index=False)
    print(f"steo_brent.csv: {len(df)} months, {df.month.iloc[0]} to {df.month.iloc[-1]}")
    return df


def parse_tsmc() -> pd.DataFrame:
    rows = []
    for pdf in sorted((RAW / "tsmc").glob("*.pdf")):
        txt = text_of(pdf)
        q = re.search(r"For the Three Months Ended\s+([A-Z][a-z]+ \d{1,2}, \d{4})", txt)
        rev = re.search(r"Net Revenue\s+\$\s*([\d,]+)", txt)
        if not (q and rev):
            print(f"  skip {pdf.name}: no quarterly revenue line")
            continue
        end = pd.to_datetime(q.group(1))
        rows.append({"quarter": f"{end.year}-Q{(end.month - 1) // 3 + 1}",
                     "tsmc_revenue_usd_m": float(rev.group(1).replace(",", "")),
                     "source_file": pdf.name})
    df = (pd.DataFrame(rows).sort_values(["quarter", "source_file"])
          .drop_duplicates("quarter", keep="last").reset_index(drop=True))
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
                             "(TrendForce public highlight, June 2026)")
    tsmc["source"] = ("TSMC consolidated condensed statements of comprehensive "
                      "income, quarterly; TrendForce 1Q26 report public highlight")
    tsmc.to_csv(OUT / "semiconductor_channel.csv", index=False)
    print(f"semiconductor_channel.csv: {len(tsmc)} quarters "
          f"({tsmc.quarter.iloc[0]} to {tsmc.quarter.iloc[-1]}); latest revenue "
          f"USD {tsmc.tsmc_revenue_usd_m.iloc[-1]:,.0f}m")


if __name__ == "__main__":
    main()
