"""
config.py
Shared constants: paths, simulation settings, tier membership.

Tier membership is fixed at current composition for the whole sample.
NATO Europe is the set of current European members, including states
that acceded after 1991; Turkiye is assigned to NATO Europe by treaty
status. Hedging middle powers have no treaty commitment to either
principal.
"""

import os
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
OUT = ROOT / "outputs"
DOCS = ROOT / "docs"
FIG = OUT / "figures"

SEED = 20260724
DRAWS = 10_000
HORIZON_YEAR = 2035
EVENT_YEARS = (2028, 2031)        # demonstration event window, inclusive
BLOCK_LENGTH = 5                  # mean run length in years, stationary bootstrap
HAC_LAGS_QUARTERLY = 4
HAC_LAGS_ANNUAL = 3
PCTS = [5, 10, 25, 50, 75, 90, 95]
PATHWAYS = ["accretion", "retrenchment", "demonstration"]

# Build date. Set PRIMACY_BUILD_DATE to pin it for a reproducible rebuild.
BUILD_DATE = os.environ.get("PRIMACY_BUILD_DATE", date.today().isoformat())

TIERS = {
    "China": ["China"],
    "United States": ["United States of America"],
    "Indo-Pacific allies": [
        "Japan", "Korea, South", "Taiwan", "Australia",
        "Philippines", "New Zealand", "Thailand",
    ],
    "NATO Europe": [
        "Albania", "Belgium", "Bulgaria", "Croatia", "Czechia", "Denmark",
        "Estonia", "Finland", "France", "Germany", "Greece", "Hungary",
        "Iceland", "Italy", "Latvia", "Lithuania", "Luxembourg",
        "Montenegro", "Netherlands", "North Macedonia", "Norway", "Poland",
        "Portugal", "Romania", "Slovakia", "Slovenia", "Spain", "Sweden",
        "Türkiye", "United Kingdom",
    ],
    "Hedging middle powers": [
        "India", "Indonesia", "Viet Nam", "Singapore", "Malaysia",
        "Saudi Arabia", "United Arab Emirates", "Brazil", "South Africa",
    ],
    "Russia": ["Russia"],
}
TIER_ORDER = ["China", "United States", "Indo-Pacific allies",
              "NATO Europe", "Hedging middle powers", "Russia"]
ALLIED_TIERS = ["Indo-Pacific allies", "NATO Europe", "Hedging middle powers"]
PRINCIPALS = ["United States", "China"]
# Simulated blocks. Russia is not simulated separately and is part of
# "Rest of world" (world total minus the five other blocks).
BLOCKS = PRINCIPALS + ALLIED_TIERS + ["Rest of world"]

# SIPRI sheet -> (key, label, header row, aggregation rule)
MEASURES = {
    "Constant (2024) US$": ("milex_usd_const2024", "Constant 2024 US$", 5, "sum"),
    "Current US$": ("milex_usd_current", "Current US$", 5, "sum"),
    "Share of GDP": ("milex_pct_gdp", "Share of GDP", 5, "median"),
    "Per capita": ("milex_per_capita_usd", "Per capita US$", 6, "median"),
    "Share of Govt. spending": ("milex_govt_share_pct",
                                "Share of government spending", 7, "median"),
}
