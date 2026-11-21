"""
tiers.py
Tier aggregation of the SIPRI expenditure workbook.

Aggregation rules
-----------------
Dollar measures are tier totals. Membership coverage in SIPRI changes
over time (for example the United Arab Emirates series ends in 2014, and
several European states enter in 1992 and 1993). A plain sum over
available members therefore contains level breaks that are coverage
changes, not spending changes. Tier totals are instead chain-linked:
growth between t-1 and t is computed over members observed in both
years, and levels are obtained by applying those growth rates backward
from the latest year's observed total. The raw sum and the member count
are retained in the panel for audit.

Intensity measures (share of GDP, per capita, share of government
spending) are tier medians over available members.

SIPRI codes unavailable data as "..." and non-existence as "xxx". Both
are read as missing.
"""

import numpy as np
import pandas as pd

from config import (ALLIED_TIERS, MEASURES, PROC, RAW, TIERS)

WORKBOOK = RAW / "sipri_milex.xlsx"


def read_measure(sheet: str, header: int) -> pd.DataFrame:
    """Country-year long frame for one SIPRI sheet; missing codes dropped."""
    df = pd.read_excel(WORKBOOK, sheet_name=sheet, header=header)
    df = df.rename(columns={df.columns[0]: "country"})
    years = [c for c in df.columns if isinstance(c, (int, float))
             and 1949 <= int(c) <= 2100]
    df = df[["country"] + years].dropna(subset=["country"])
    df["country"] = df["country"].astype(str).str.strip()
    long = df.melt(id_vars="country", var_name="year", value_name="value")
    long["year"] = long["year"].astype(int)
    long["value"] = pd.to_numeric(long["value"], errors="coerce")
    return long.dropna(subset=["value"])


def chain_link(wide: pd.DataFrame) -> pd.DataFrame:
    """Chain-linked total for a year-by-member matrix.

    Returns value (chain-linked level), raw_sum and n_members by year.
    The level is anchored on the latest year's observed total and carried
    backward with matched-member growth. The chain stops at the first
    year pair with no member observed in both years.
    """
    wide = wide.sort_index()
    raw = wide.sum(axis=1, min_count=1)
    n = wide.notna().sum(axis=1)
    years = [y for y in wide.index if n[y] > 0]
    level = pd.Series(np.nan, index=wide.index, dtype=float)
    last = years[-1]
    level[last] = raw[last]
    for t in reversed(years[1:]):
        prev = t - 1
        if prev not in wide.index or np.isnan(level[t]):
            break
        both = wide.loc[t].notna() & wide.loc[prev].notna()
        den = wide.loc[t][both].sum()
        if not both.any() or den <= 0:
            break
        level[prev] = level[t] * wide.loc[prev][both].sum() / den
    out = pd.DataFrame({"value": level, "raw_sum": raw, "n_members": n})
    return out.dropna(subset=["value"])


def build_tier_panel() -> pd.DataFrame:
    """All measures aggregated to the six tiers, long format."""
    member_of = {c: t for t, members in TIERS.items() for c in members}
    parts = []
    for sheet, (key, _label, header, how) in MEASURES.items():
        long = read_measure(sheet, header)
        absent = sorted(set(member_of) - set(long["country"].unique()))
        if absent:
            print(f"  {sheet}: tier members absent from sheet: {absent}")
        wide = long.pivot_table("value", "year", "country")
        for tier, members in TIERS.items():
            w = wide.reindex(columns=[m for m in members if m in wide.columns])
            if how == "sum":
                agg = chain_link(w)
            else:
                agg = pd.DataFrame({"value": w.median(axis=1),
                                    "raw_sum": np.nan,
                                    "n_members": w.notna().sum(axis=1)}
                                   ).dropna(subset=["value"])
            agg = agg.reset_index().rename(columns={"index": "year"})
            agg.insert(0, "tier", tier)
            agg["measure"] = key
            agg["agg"] = "chain-linked sum" if how == "sum" else "median"
            parts.append(agg)
    panel = pd.concat(parts, ignore_index=True)
    panel["year"] = panel["year"].astype(int)
    return panel[["tier", "year", "value", "measure", "agg",
                  "n_members", "raw_sum"]]


def tier_panel() -> pd.DataFrame:
    """Tier panel written by parse_milex.py (stage 1b)."""
    return pd.read_csv(PROC / "milex_tier_panel.csv")


def level_table() -> pd.DataFrame:
    """Constant-dollar levels by year: six tiers, World, Rest of world.

    Rest of world is the SIPRI world total minus the United States,
    China and the three allied tiers. It therefore contains Russia and
    any tier member SIPRI does not report in the anchor year.
    """
    t = tier_panel()
    t = t[t.measure == "milex_usd_const2024"]
    wide = t.pivot_table("value", "year", "tier").sort_index()
    m = pd.read_csv(PROC / "milex_panel.csv")
    wide["World"] = m[m.iso3 == "WORLD"].set_index("year").milex_constusd_m
    simulated = ["United States", "China"] + ALLIED_TIERS
    wide["Rest of world"] = wide["World"] - wide[simulated].sum(
        axis=1, min_count=len(simulated))
    return wide


def growth_table() -> pd.DataFrame:
    """Real growth in percent per year for every column of level_table."""
    return (level_table().pct_change(fill_method=None) * 100).dropna(how="all")


def build_country_panel() -> pd.DataFrame:
    """Country-year panel for the three allied tiers.

    Columns: country, tier, year, g (real expenditure growth, percent),
    g_lag, gdp_g (real GDP growth implied by SIPRI constant-dollar
    expenditure divided by its GDP share, percent), us_lag, cn_lag
    (principal growth in the previous year) and w (the country's share
    of pooled allied expenditure in the previous year).
    """
    const = read_measure(*_sheet("milex_usd_const2024")).pivot_table(
        "value", "year", "country")
    share = read_measure(*_sheet("milex_pct_gdp")).pivot_table(
        "value", "year", "country")
    gdp = const / share.reindex_like(const)
    us = const["United States of America"].pct_change(fill_method=None) * 100
    cn = const["China"].pct_change(fill_method=None) * 100
    rows = []
    for tier in ALLIED_TIERS:
        for c in TIERS[tier]:
            if c not in const:
                continue
            x = const[c].where(const[c] > 0)
            g = x.pct_change(fill_method=None) * 100
            y = gdp[c].where(gdp[c] > 0).pct_change(fill_method=None) * 100
            df = pd.DataFrame({"country": c, "tier": tier, "g": g,
                               "g_lag": g.shift(1), "gdp_g": y,
                               "us_lag": us.shift(1), "cn_lag": cn.shift(1),
                               "level_lag": x.shift(1)})
            rows.append(df.reset_index().rename(columns={"index": "year"}))
    p = pd.concat(rows, ignore_index=True)
    p = p.dropna(subset=["g", "g_lag", "gdp_g", "us_lag", "cn_lag",
                         "level_lag"])
    p["w"] = p.level_lag / p.groupby("year").level_lag.transform("sum")
    return p.drop(columns="level_lag").sort_values(
        ["year", "country"]).reset_index(drop=True)


def _sheet(key: str) -> tuple[str, int]:
    for sheet, (k, _label, header, _how) in MEASURES.items():
        if k == key:
            return sheet, header
    raise KeyError(key)
