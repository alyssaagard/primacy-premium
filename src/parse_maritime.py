"""
parse_maritime.py
Stage 1e: the shipping channel, from four UNCTAD maritime tables.

WHY THIS TABLE EXISTS
---------------------
Channel two of the design is shipping and war risk. The war risk side is
an event table (parse_security.py); this parser builds the structural
side: who owns the ships, who builds them, who is connected, and who
moves the boxes. Four UNCTAD exports carry that story. Merchant fleet by
flag of registration (dead weight tons, 1980 to 2026), ships built by
economy (gross tonnage, 2014 to 2025), the Liner Shipping Connectivity
Index (quarterly, 2006 to 2026), and container port throughput (TEU,
2010 to 2024). China's position in each is the exposure the model
carries: a demonstration pathway that disrupts East Asian shipping
disrupts the system's own builder and busiest ports.

PARSING NOTES
-------------
UNCTAD ships wide files with one column triplet per period
(Value, Footnote, MissingValue). Only the Value columns are read.
The fleet, shipbuilding and throughput exports in the evidence base are
group-level tables, so China's value is derived exactly the way UNCTAD
itself presents it: developing economies minus developing economies
excluding China. The LSCI export carries individual economies, so
China, the United States, Taiwan and the East Asian builders are read
directly. LSCI is quarterly and is annualized by mean over available
quarters. Output is one tidy long table, with derived rows labelled as
derived.
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "unctad"
OUT = ROOT / "data" / "processed"

# Group files carry aggregates only; LSCI carries individual economies.
GROUPS = {
    "World": ["World"],
    "Asia": ["Asia"],
    "Europe": ["Europe"],
    "Americas": ["Americas"],
    "Developing economies": ["Developing economies"],
    "Developing excl China": ["Developing economies excluding China"],
}
LSCI_ECONOMIES = {
    "World": ["World"],
    "China": ["China"],
    "United States": ["United States of America", "United States"],
    "Japan": ["Japan"],
    "South Korea": ["Korea, Republic of", "Republic of Korea"],
    "Taiwan": ["China, Taiwan Province of", "Taiwan Province of China"],
    "Singapore": ["Singapore"],
}

FILES = {
    "merchant_fleet_kdwt": ("US_MerchantFleet_20260729_211122.csv",
                            "_Dead_weight_tons_in_thousands_Value",
                            "thousand dwt, flag of registration"),
    "ships_built_gt": ("US_ShipBuilding_20260729_222541.csv",
                       "_Gross_Tonnage_Value", "gross tons"),
    "container_throughput_teu": ("US_ContPortThroughput_20260729_211612.csv",
                                 "_TEU_Twenty_foot_Equivalent_Unit_Value", "TEU"),
}


def tidy_wide(fname: str, suffix: str, unit: str, series: str) -> pd.DataFrame:
    df = pd.read_csv(RAW / fname)
    label_col = df.columns[0]
    rows = []
    labels = set(df[label_col].astype(str))
    for econ, cands in GROUPS.items():
        hit = next((c for c in cands if c in labels), None)
        if hit is None:
            print(f"  {series}: no label for {econ}")
            continue
        rec = df[df[label_col] == hit].iloc[0]
        for col in df.columns:
            if col.endswith(suffix):
                year = int(col.split("_")[0].split()[-1])
                val = pd.to_numeric(rec[col], errors="coerce")
                if pd.notna(val):
                    rows.append({"series": series, "economy": econ,
                                 "year": year, "value": float(val), "unit": unit})
    out = pd.DataFrame(rows)

    # China, derived as UNCTAD presents it: developing minus developing
    # excluding China. Validated to be positive and below the world total.
    dev = out[out.economy == "Developing economies"].set_index("year").value
    dxc = out[out.economy == "Developing excl China"].set_index("year").value
    wld = out[out.economy == "World"].set_index("year").value
    cn = (dev - dxc).dropna()
    bad = cn[(cn <= 0) | (cn >= wld.reindex(cn.index))]
    if len(bad):
        raise ValueError(f"{series}: derived China fails validation in {list(bad.index)}")
    out = pd.concat([out, pd.DataFrame({
        "series": series, "economy": "China (derived)", "year": cn.index,
        "value": cn.values, "unit": unit + ", derived"})], ignore_index=True)
    return out


def tidy_lsci() -> pd.DataFrame:
    df = pd.read_csv(RAW / "US_LSCI_20260729_211749.csv")
    label_col = df.columns[0]
    vcols = [c for c in df.columns if c.endswith("_Value")]
    rows = []
    labels = set(df[label_col].astype(str))
    for econ, cands in LSCI_ECONOMIES.items():
        hit = next((c for c in cands if c in labels), None)
        if hit is None:
            print(f"  lsci: no label for {econ}")
            continue
        rec = df[df[label_col] == hit].iloc[0]
        by_year: dict[int, list[float]] = {}
        for col in vcols:
            year = int(col.split()[1].split("_")[0])
            val = pd.to_numeric(rec[col], errors="coerce")
            if pd.notna(val):
                by_year.setdefault(year, []).append(float(val))
        for year, vals in by_year.items():
            rows.append({"series": "lsci", "economy": econ, "year": year,
                         "value": round(sum(vals) / len(vals), 2),
                         "unit": "index, Q1 2023 = 100, annual mean"})
    return pd.DataFrame(rows)


def main() -> None:
    parts = [tidy_wide(f, sfx, unit, series)
             for series, (f, sfx, unit) in FILES.items()]
    parts.append(tidy_lsci())
    out = pd.concat(parts, ignore_index=True).sort_values(
        ["series", "economy", "year"])
    out["source"] = "UNCTADstat maritime transport tables, retrieved 29 July 2026"
    out.to_csv(OUT / "maritime_panel.csv", index=False)

    cn = out[(out.series == "ships_built_gt") & (out.economy == "China (derived)")]
    wd = out[(out.series == "ships_built_gt") & (out.economy == "World")]
    if len(cn) and len(wd):
        y = int(cn.year.max())
        share = 100 * cn[cn.year == y].value.iloc[0] / wd[wd.year == y].value.iloc[0]
        print(f"maritime_panel.csv: {len(out)} rows; China built "
              f"{share:.0f}% of world gross tonnage in {y}")


if __name__ == "__main__":
    main()
