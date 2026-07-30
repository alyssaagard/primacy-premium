"""
parse_security.py
Stage 1g: the security-side tables that layers 2 and 4 consume.

Five tables come out of this script.

1. nato_burden.csv. NATO's own defence expenditure release, Table 3,
   gives core defence spending as a share of real GDP per ally per year,
   2014 to 2026 (2026 estimated). This is the H2 outcome variable on the
   European side, measured by the alliance itself rather than
   reconstructed.

2. nuclear_panel.csv. Warhead counts from the Federation of American
   Scientists' Nuclear Notebook 2026 issues for China, the United
   States, and Russia, plus the 2025 China issue and the DOD-projected
   Chinese trajectory. This defines the parity threshold the scenarios
   reference. Numbers are extracted by anchored regex with validation,
   never typed in unverified.

3. arms_recipient_imports.csv and allied_import_dependence.csv. The
   recipient-level TIV matrix gives each ally's import volume 2011 to
   2025; the full trade register gives the United States' share of each
   allied tier's imports over five-year order windows. Supplier
   diversification among allies is a falsification tripwire for
   pathway II, so it needs a measured baseline.

4. taiwan_strait_events.csv. The event register for the event-study
   layer: major PLA exercise episodes and the 2026 Gulf war-risk
   episode, each with a documentary source held in the repository's
   evidence base.

5. alliance_matrix.csv and war_risk_events.csv. The commitment matrix
   encodes treaty structure (who is obligated to whom, and how hard);
   it is a design input, documented and cited, not an estimate. The war
   risk table records the one fully-quoted premium episode: Mideast Gulf
   additional war risk premia moving from 0.15 to 0.2 percent of hull
   value to around 1 percent in June 2026, with the March 2026 Joint War
   Committee listing expansion as the institutional marker.
"""

import re
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"

IP_ALLIES = ["Japan", "South Korea", "Korea, South", "Taiwan", "Australia",
             "Philippines", "New Zealand", "Thailand"]
NATO_EUROPE = ["Albania", "Belgium", "Bulgaria", "Croatia", "Czechia",
               "Czech Republic", "Denmark", "Estonia", "Finland", "France",
               "Germany", "Greece", "Hungary", "Iceland", "Italy", "Latvia",
               "Lithuania", "Luxembourg", "Montenegro", "Netherlands",
               "North Macedonia", "Norway", "Poland", "Portugal", "Romania",
               "Slovakia", "Slovenia", "Spain", "Sweden", "Turkiye", "Türkiye",
               "Turkey", "United Kingdom"]


def text_of(pdf: Path) -> str:
    return subprocess.run(["pdftotext", str(pdf), "-"],
                          capture_output=True, text=True).stdout


def parse_nato() -> None:
    raw = pd.read_excel(RAW / "nato" / "defexp2026en.xlsx", "Table 3", header=None)
    hdr = next(i for i in range(10)
               if pd.to_numeric(raw.iloc[i, 1:], errors="coerce").eq(2014).any())
    years = raw.iloc[hdr].tolist()
    rows = []
    for i in range(hdr + 1, len(raw)):
        name = raw.iloc[i, 0]
        if not isinstance(name, str) or not name.strip():
            continue
        name = name.strip().replace("*", "")
        if name.lower().startswith(("nato", "note", "source", "table")):
            continue
        for j, y in enumerate(years):
            yn = pd.to_numeric(str(y).replace("e", "").strip(), errors="coerce")
            if pd.isna(yn) or not (2000 <= int(yn) <= 2030):
                continue
            val = pd.to_numeric(raw.iloc[i, j], errors="coerce")
            if pd.notna(val) and 0 < val < 10:
                rows.append({"ally": name, "year": int(yn),
                             "pct_gdp": float(val),
                             "estimate": "e" in str(y)})
    df = pd.DataFrame(rows).drop_duplicates(["ally", "year"])
    if df.empty or df.year.max() < 2026:
        raise ValueError("NATO Table 3 parse failed validation")
    df["source"] = "NATO, Defence Expenditure of NATO Countries, 2026 edition, Table 3"
    df.to_csv(OUT / "nato_burden.csv", index=False)
    m26 = df[df.year == 2026].pct_gdp.median()
    print(f"nato_burden.csv: {df.ally.nunique()} allies, {df.year.min()} to "
          f"{df.year.max()}; median 2026e burden {m26:.2f}% of GDP")


def grab(txt: str, pattern: str, name: str) -> int:
    m = re.search(pattern, txt, re.I)
    if not m:
        raise ValueError(f"nuclear panel: could not find {name}")
    return int(m.group(1).replace(",", ""))


def parse_nuclear() -> None:
    cn26 = text_of(RAW / "nuclear" / "Chinese_nuclear_weapons__2026.pdf")
    us26 = text_of(RAW / "nuclear" / "United_States_nuclear_weapons__2026.pdf")
    ru26 = text_of(RAW / "nuclear" / "Russian_nuclear_weapons__2026.pdf")
    cn25 = text_of(RAW / "nuclear" / "FAS_Nuclear_Notebook_Chinese_nuclear_weapons_2025_PDF.pdf")

    rows = [
        {"country": "China", "year": 2025,
         "stockpile": grab(cn25, r"approximately (6\d\d) (?:nuclear )?warheads", "CN 2025"),
         "kind": "estimate"},
        {"country": "China", "year": 2026,
         "stockpile": grab(cn26, r"stockpile of approximately (\d{3})", "CN 2026"),
         "kind": "estimate"},
        {"country": "China", "year": 2030,
         "stockpile": grab(cn26, r"approximately (1,?000) (?:operational )?(?:nuclear )?warheads",
                           "CN 2030 projection"),
         "kind": "DOD projection"},
        {"country": "China", "year": 2035,
         "stockpile": grab(cn26, r"(1,?500) (?:nuclear )?warheads", "CN 2035 projection"),
         "kind": "DOD projection"},
        {"country": "United States", "year": 2026,
         "stockpile": grab(us26, r"stockpile of approximately (3,?7\d\d)", "US 2026"),
         "deployed_strategic": grab(us26, r"approximately (1,?7\d\d) warheads", "US deployed"),
         "kind": "estimate"},
        {"country": "Russia", "year": 2026,
         "stockpile": grab(ru26, r"stockpile of approximately (4,?\d{3})", "RU 2026"),
         "kind": "estimate"},
    ]
    df = pd.DataFrame(rows)
    df["source"] = ("FAS Nuclear Notebook, Bulletin of the Atomic Scientists, "
                    "2025 and 2026 issues; DOD China Military Power Report projections")
    df.to_csv(OUT / "nuclear_panel.csv", index=False)
    print(f"nuclear_panel.csv: {len(df)} rows; China {df[df.country=='China'].stockpile.tolist()}")


def parse_recipients() -> None:
    df = pd.read_csv(RAW / "sipri_arms" / "arms_transfers_dyad.csv", skiprows=9)
    df = df.rename(columns={df.columns[0]: "recipient"})
    ycols = [c for c in df.columns if str(c).strip()[:4].isdigit()
             and len(str(c).strip()) == 4]
    long = df.melt("recipient", ycols, "year", "tiv_m")
    long["year"] = long.year.astype(int)
    long["tiv_m"] = pd.to_numeric(long.tiv_m, errors="coerce")
    long = long.dropna(subset=["tiv_m"])
    long["tier"] = np.select(
        [long.recipient.isin(IP_ALLIES), long.recipient.isin(NATO_EUROPE),
         long.recipient.eq("Total world import")],
        ["Indo-Pacific allies", "NATO Europe", "World"], default="Other")
    long["source"] = "SIPRI Arms Transfers Database, TIV of imports, retrieved 29 July 2026"
    long.to_csv(OUT / "arms_recipient_imports.csv", index=False)
    print(f"arms_recipient_imports.csv: {len(long)} rows, "
          f"{long.recipient.nunique()} recipients")


def parse_dependence() -> None:
    reg = pd.read_csv(RAW / "sipri_arms" / "sipri_traderegister.csv",
                      skiprows=11, encoding="cp1252")
    reg = reg.rename(columns={reg.columns[0]: "recipient", reg.columns[1]: "supplier",
                              reg.columns[2]: "order_year",
                              reg.columns[-2]: "tiv_delivered"})
    reg["order_year"] = pd.to_numeric(reg.order_year, errors="coerce")
    reg["tiv_delivered"] = pd.to_numeric(reg.tiv_delivered, errors="coerce")
    reg = reg.dropna(subset=["order_year", "tiv_delivered"])
    reg["tier"] = np.select(
        [reg.recipient.isin(IP_ALLIES), reg.recipient.isin(NATO_EUROPE)],
        ["Indo-Pacific allies", "NATO Europe"], default=None)
    reg = reg[reg.tier.notna()]
    reg["window"] = (reg.order_year // 5 * 5).astype(int)
    rows = []
    for (tier, win), g in reg.groupby(["tier", "window"]):
        tot = g.tiv_delivered.sum()
        if tot <= 0:
            continue
        by_sup = g.groupby("supplier").tiv_delivered.sum() / tot
        rows.append({"tier": tier, "window": win,
                     "us_share": round(float(by_sup.get("United States", 0.0)), 4),
                     "supplier_hhi": round(float((by_sup ** 2).sum()), 4),
                     "n_suppliers": int((by_sup > 0.01).sum()),
                     "tiv_total": round(float(tot), 1)})
    dep = pd.DataFrame(rows).sort_values(["tier", "window"])
    dep["source"] = "SIPRI Arms Transfers Database trade register, order-year windows"
    dep.to_csv(OUT / "allied_import_dependence.csv", index=False)
    last = dep[dep.window == 2020]
    print("allied_import_dependence.csv:",
          {r.tier: f"US {100*r.us_share:.0f}%" for r in last.itertuples()})


def curated_tables() -> None:
    events = pd.DataFrame([
        {"date": "2022-08-04", "event": "Large-scale joint exercises encircling Taiwan after the Pelosi visit",
         "kind": "PLA exercise", "source": "DOD China Military Power Report 2025"},
        {"date": "2023-04-08", "event": "Joint Sword exercises following the Tsai-McCarthy meeting",
         "kind": "PLA exercise", "source": "DOD China Military Power Report 2025"},
        {"date": "2024-05-23", "event": "Joint Sword-2024A exercises after the Lai inauguration",
         "kind": "PLA exercise", "source": "DOD China Military Power Report 2025"},
        {"date": "2024-10-14", "event": "Joint Sword-2024B exercises",
         "kind": "PLA exercise", "source": "DOD China Military Power Report 2025"},
        {"date": "2025-04-01", "event": "Strait Thunder-2025A exercises",
         "kind": "PLA exercise", "source": "The Diplomat, January 2026"},
        {"date": "2026-03-03", "event": "JWC expands Listed Areas: Gulf littoral states added",
         "kind": "war risk listing", "source": "Joint War Committee circular JWLA-033"},
        {"date": "2026-06-15", "event": "Mideast Gulf AWRP rises from 0.15 to 0.2 percent of hull value to around 1 percent",
         "kind": "war risk repricing", "source": "Argus Media, June 2026"},
    ])
    events.to_csv(OUT / "taiwan_strait_events.csv", index=False)

    war = pd.DataFrame([
        {"episode": "Mideast Gulf 2026", "area": "Persian/Arabian Gulf and Gulf of Oman",
         "awrp_pre_pct_hull": 0.175, "awrp_during_pct_hull": 1.0,
         "multiple": round(1.0 / 0.175, 1), "date": "2026-06",
         "source": "Argus Media explainer on war risk insurance and AWRP, June 2026"},
    ])
    war.to_csv(OUT / "war_risk_events.csv", index=False)

    m = []
    m += [{"tier": "NATO Europe", "member": a, "commitment": 1.0,
           "basis": "North Atlantic Treaty, Article 5"} for a in
          ["France", "Germany", "United Kingdom", "Poland", "Italy", "Spain",
           "Netherlands", "Norway", "Denmark", "Sweden", "Finland", "Turkiye"]]
    m += [{"tier": "Indo-Pacific allies", "member": a, "commitment": 1.0,
           "basis": "Bilateral mutual defense treaty with the United States"} for a in
          ["Japan", "South Korea", "Australia", "Philippines", "Thailand"]]
    m += [{"tier": "Indo-Pacific allies", "member": "Taiwan", "commitment": 0.5,
           "basis": "Taiwan Relations Act, deliberate ambiguity"},
          {"tier": "Indo-Pacific allies", "member": "New Zealand", "commitment": 0.6,
           "basis": "ANZUS, partially suspended"}]
    m += [{"tier": "Hedging middle powers", "member": a, "commitment": 0.2,
           "basis": "No treaty obligation; active courtship by both blocs"} for a in
          ["India", "Indonesia", "Viet Nam", "Singapore", "Malaysia",
           "Saudi Arabia", "United Arab Emirates", "Brazil", "South Africa"]]
    am = pd.DataFrame(m)
    am["source"] = ("Treaty texts; NATO Hague Summit Declaration 2025; "
                    "CRS reports in the evidence base")
    am.to_csv(OUT / "alliance_matrix.csv", index=False)
    print(f"events {len(events)}, war risk {len(war)}, alliance matrix {len(am)} rows")


def main() -> None:
    parse_nato()
    parse_nuclear()
    parse_recipients()
    parse_dependence()
    curated_tables()


if __name__ == "__main__":
    main()
