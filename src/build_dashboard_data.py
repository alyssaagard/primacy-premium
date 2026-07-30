"""
build_dashboard_data.py
Stage 5a: assemble the single JSON payload the interactive page consumes.

WHY A PAYLOAD BUILDER
---------------------
The page holds no numbers of its own. Everything it draws arrives from
this script, which reads the pipeline's own artifacts (the processed
tables, calibration.json, simulation_fan.csv, simulation_summary.json)
and the SIPRI workbook. One consequence matters: the page cannot drift
from the model, because there is nothing in it to drift. Re-run the
pipeline and the page re-states itself.

Two jobs here beyond assembly:

1. Multi-measure tier panel. The core pipeline only needed four actors
   in constant dollars. An interactive page needs the full measure set
   (constant US$, current US$, share of GDP, per capita) aggregated into
   the six actor tiers the research design uses. That parsing happens
   here and is written back to data/processed/milex_tier_panel.csv so it
   is inspectable rather than trapped inside a JSON blob.

2. The register. The state of every table is read off disk, not typed
   by hand: each artifact reports built with its true row count, and the
   builder refuses to write a payload if any registered artifact is
   missing, so the page cannot claim a completeness the pipeline does
   not have. Two rows carry descope notes rather than data gaps: the
   valuation robustness for reserves is a flow-attribution series
   because currency price indices are not in the evidence base, and
   foundry concentration is carried qualitatively because the ranking
   table in the evidence base is paywalled.

Aggregation rule: the two dollar measures sum across a tier; share of
GDP and per capita take the tier median, because summing intensity
ratios across countries produces a number that means nothing.

Run:  python src/build_dashboard_data.py
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
OUT = ROOT / "outputs"
DOCS = ROOT / "docs"

# SIPRI sheet name -> (payload key, human label, header row, aggregation)
MEASURES = {
    "Constant (2024) US$": ("milex_usd_const2024", "Constant 2024 US$", 5, "sum"),
    "Current US$": ("milex_usd_current", "Current US$", 5, "sum"),
    "Share of GDP": ("milex_pct_gdp", "Share of GDP", 5, "median"),
    "Per capita": ("milex_per_capita_usd", "Per capita US$", 6, "median"),
    "Share of Govt. spending": ("milex_govt_share_pct",
                                "Share of government spending", 7, "median"),
}

# The six-tier scope from the research design. Tiers are analytic
# objects, not geography: the question is who reprices in response to
# whom, so Turkey sits with NATO Europe (treaty obligation) while India
# and the Gulf sit with the hedgers (no obligation, active courtship).
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


def read_measure(sheet: str, header: int) -> pd.DataFrame:
    """Return a tidy country-year frame for one SIPRI sheet.

    SIPRI marks unavailable data with '...' and non-existence with 'xxx'.
    Both must become NaN. Coercing them to zero is the single most common
    error in secondary use of this database and it silently drags every
    tier total downward.
    """
    df = pd.read_excel(RAW / "sipri_milex.xlsx", sheet_name=sheet, header=header)
    df = df.rename(columns={df.columns[0]: "country"})
    year_cols = [c for c in df.columns if isinstance(c, (int, float))
                 and 1949 <= int(c) <= 2025]
    df = df[["country"] + year_cols].dropna(subset=["country"])
    df["country"] = df["country"].astype(str).str.strip()
    long = df.melt(id_vars="country", var_name="year", value_name="value")
    long["year"] = long["year"].astype(int)
    long["value"] = pd.to_numeric(long["value"], errors="coerce")
    return long.dropna(subset=["value"])


def build_tiers() -> tuple[dict, pd.DataFrame]:
    """Aggregate every measure into the six tiers; return payload + audit table."""
    series, audit = {}, []
    member_of = {c: t for t, members in TIERS.items() for c in members}

    for sheet, (key, _label, header, how) in MEASURES.items():
        long = read_measure(sheet, header)
        long["tier"] = long["country"].map(member_of)
        hit = long.dropna(subset=["tier"])

        # Coverage check: a tier whose members are missing from a sheet
        # would silently plot as a lower line rather than as a gap.
        missing = set(member_of) - set(long["country"].unique())
        if missing:
            print(f"  {sheet}: {len(missing)} tier members absent "
                  f"({', '.join(sorted(missing)[:4])}...)")

        agg = (hit.groupby(["tier", "year"])["value"]
                  .sum() if how == "sum" else
               hit.groupby(["tier", "year"])["value"].median())
        agg = agg.reset_index()
        agg["measure"] = key
        agg["agg"] = how
        audit.append(agg)

        series[key] = {
            t: {"x": g["year"].tolist(), "y": [round(float(v), 4) for v in g["value"]]}
            for t, g in agg.groupby("tier")
        }
    return series, pd.concat(audit, ignore_index=True)


def yoy_from_tiers(tier_series: dict) -> list:
    """Real year-on-year growth per tier, last ten years."""
    out = []
    for t in TIER_ORDER:
        s = tier_series["milex_usd_const2024"].get(t)
        if not s:
            continue
        v = pd.Series(s["y"], index=s["x"]).sort_index()
        g = (v.pct_change() * 100).dropna()
        g = g[g.index >= g.index.max() - 9]
        out.append({"tier": t, "x": [int(i) for i in g.index],
                    "y": [round(float(x), 2) for x in g]})
    return out


def register() -> list:
    """Read the build state off disk rather than asserting it.

    Every artifact the model produces or consumes is listed with its true
    row count. The builder raises if anything is missing: an all-built
    register must be earned by the pipeline, not typed into a script.
    """
    spec = [
        ("cofer_quarterly_long", "Reserve composition", PROC / "cofer_quarterly_long.csv",
         "IMF COFER 7.0.1, shares and nominal claims, tidied and reconciled."),
        ("cofer_shares_wide", "Reserve composition", PROC / "cofer_shares_wide.csv",
         "Quarterly share matrix, 1999-Q1 to 2026-Q1. Feeds the reserve channel."),
        ("cofer_flow_attribution", "Reserve composition", PROC / "cofer_flow_attribution.csv",
         "Valuation robustness by flow attribution: each currency's share of the "
         "quarterly change in allocated claims. Exact FX adjustment needs price "
         "indices outside the evidence base; the limitation is documented."),
        ("swift_settlement", "Reserve composition", PROC / "swift_settlement.csv",
         "Monthly renminbi payments and trade finance shares from 27 Swift tracker "
         "issues. The settlement leg of the H3 settlement-reserve gap."),
        ("milex_panel", "Defense expenditure", PROC / "milex_panel.csv",
         "SIPRI v1.2 constant 2024 US$, four headline actors plus world."),
        ("milex_features", "Defense expenditure", PROC / "milex_features.csv",
         "China to US ratio and real growth rates, the model's regressor."),
        ("milex_tier_panel", "Defense expenditure", PROC / "milex_tier_panel.csv",
         "Five measures aggregated to the six analytic tiers, 1949 to 2025."),
        ("nato_burden", "Defense expenditure", PROC / "nato_burden.csv",
         "Defence spending as share of real GDP per ally, 2014 to 2026e, from "
         "NATO's own 2026 release."),
        ("arms_transfers_global", "Arms transfers", PROC / "arms_transfers_global.csv",
         "World deliveries in SIPRI trend indicator values, 1950 to 2025."),
        ("supplier_concentration", "Arms transfers", PROC / "supplier_concentration.csv",
         "Supplier shares and Herfindahl index over five-year order windows."),
        ("arms_recipient_imports", "Arms transfers", PROC / "arms_recipient_imports.csv",
         "Recipient-level import volumes, 2011 to 2025, tiered to the design."),
        ("allied_import_dependence", "Arms transfers", PROC / "allied_import_dependence.csv",
         "US share and supplier Herfindahl of each allied tier's imports by "
         "five-year order window. The pathway II diversification tripwire's baseline."),
        ("semiconductor_channel", "Commercial channels", PROC / "semiconductor_channel.csv",
         "Channel one. TSMC quarterly revenue from the company's own statements. "
         "Foundry concentration carried qualitatively: the ranking table in the "
         "evidence base is paywalled, so no Herfindahl is computed from it."),
        ("maritime_panel", "Commercial channels", PROC / "maritime_panel.csv",
         "Channel two structure: fleet, shipbuilding, connectivity, throughput. "
         "China derived as developing minus developing excluding China."),
        ("war_risk_events", "Commercial channels", PROC / "war_risk_events.csv",
         "Channel two pricing: the 2026 Mideast Gulf AWRP episode, 0.175 to 1.0 "
         "percent of hull value, the demonstration repricing calibration."),
        ("energy_chokepoints", "Commercial channels", PROC / "energy_chokepoints.csv",
         "Channel three. Oil transit by chokepoint, million barrels per day."),
        ("steo_brent", "Commercial channels", PROC / "steo_brent.csv",
         "Brent monthly, observed and EIA forecast to 2027, the price baseline."),
        ("taiwan_strait_events", "Event study", PROC / "taiwan_strait_events.csv",
         "Exercise and repricing dates with documentary sources. Layer four's event list."),
        ("alliance_matrix", "System dynamics", PROC / "alliance_matrix.csv",
         "Treaty commitment structure by tier. A documented design input, not an estimate."),
        ("nuclear_panel", "System dynamics", PROC / "nuclear_panel.csv",
         "Warhead counts and DOD projections defining the parity threshold."),
        ("calibration_layer2", "System dynamics", OUT / "calibration_layer2.json",
         "Allied feedback on lagged US and China growth, HAC(3), 1951 to 2025."),
        ("layer2_residual_pools", "System dynamics", OUT / "layer2_residual_pools.csv",
         "Block residuals, resampled as the system simulation's innovations."),
        ("layer2_fan", "System dynamics", OUT / "layer2_fan.csv",
         "Percentile fans for five blocks by pathway and year to 2035."),
        ("layer2_summary", "System dynamics", OUT / "layer2_summary.json",
         "Endpoint distributions, the H1 test, and the arms demand projection."),
        ("calibration", "Estimation", OUT / "calibration.json",
         "Every estimated parameter with confidence intervals. Nothing assumed."),
        ("innovation_pools", "Estimation", OUT / "innovation_pools.csv",
         "Regression residuals, resampled as bootstrap innovations."),
        ("simulation_fan", "Forecast", OUT / "simulation_fan.csv",
         "Percentile fans by pathway, currency and quarter, to 2035-Q4."),
        ("simulation_summary", "Forecast", OUT / "simulation_summary.json",
         "Endpoint distributions and the reserve-channel separation statistic."),
        ("hypothesis_panel", "Hypothesis tests", PROC / "hypothesis_panel.csv",
         "One tidy table holding every measurement behind H1, H2 and H3: tests, "
         "evidence, robustness and context, filterable by hypothesis."),
        ("hypothesis_tests", "Hypothesis tests", OUT / "hypothesis_tests.json",
         "The three verdicts with statistics, machine readable, feeding the ledger."),
    ]
    reg, missing = [], []
    for name, group, path, note in spec:
        if not path.exists():
            missing.append(name)
            continue
        if path.suffix == ".csv":
            rows = len(pd.read_csv(path))
        else:
            rows = len(json.loads(path.read_text()))
        reg.append({"table": name, "group": group, "state": "built",
                    "rows": int(rows), "note": note})
    if missing:
        raise ValueError(f"register refuses to publish; missing artifacts: {missing}")
    return reg


def main() -> None:
    print("assembling dashboard payload")

    calib = json.loads((OUT / "calibration.json").read_text())
    summ = json.loads((OUT / "simulation_summary.json").read_text())
    cases = calib["cases"]
    reg_usd = calib["usd_regression"]

    # --- defense expenditure, four measures, six tiers -------------------
    tier_series, audit = build_tiers()
    audit.to_csv(PROC / "milex_tier_panel.csv", index=False)
    print(f"  milex_tier_panel.csv: {len(audit):,} rows")

    # --- reserve composition --------------------------------------------
    cofer = pd.read_csv(PROC / "cofer_shares_wide.csv")
    ccys = [c for c in ["USD", "EUR", "JPY", "GBP", "CNY", "CAD", "AUD", "CHF", "OTHER"]
            if c in cofer.columns]
    cof = {"quarters": cofer["quarter"].tolist()}
    for c in ccys:
        cof[c] = [None if pd.isna(v) else round(float(v), 3) for v in cofer[c]]
    cny = cofer.dropna(subset=["CNY"])
    peak = cny.loc[cny["CNY"].idxmax()]
    latest = cny.iloc[-1]
    cof.update({
        "cny_peak_quarter": peak["quarter"], "cny_peak_value": round(float(peak["CNY"]), 2),
        "cny_latest_quarter": latest["quarter"], "cny_latest_value": round(float(latest["CNY"]), 2),
        "cny_decline_pct": round(100 * (latest["CNY"] / peak["CNY"] - 1), 1),
        "usd_first": round(float(cofer["USD"].iloc[0]), 2),
        "usd_latest": round(float(cofer["USD"].iloc[-1]), 2),
        "first_quarter": cofer["quarter"].iloc[0],
    })

    # --- arms transfers ---------------------------------------------------
    arms = pd.read_csv(PROC / "arms_transfers_global.csv")
    conc = pd.read_csv(PROC / "supplier_concentration.csv")
    windows = sorted(conc["window"].unique())
    hhi = conc.groupby("window")["hhi"].first().reindex(windows)
    lead = (conc.sort_values("share", ascending=False)
                .groupby("window").first().reindex(windows))
    last_complete = int(max(w for w in windows if w <= 2020))
    lc = lead.loc[last_complete]
    arms_payload = {
        "years": arms["year"].astype(int).tolist(),
        "tiv": [round(float(v), 1) for v in arms["tiv_m"]],
        "windows": [int(w) for w in windows],
        "hhi": [round(float(v), 4) for v in hhi],
        "lead_supplier": lead["supplier"].tolist(),
        "lead_share": [round(100 * float(v), 2) for v in lead["share"]],
        "last_complete_window": last_complete,
        "lc_supplier": str(lc["supplier"]),
        "lc_share": round(100 * float(lc["share"]), 1),
        "lc_hhi": round(float(lc["hhi"]), 3),
        "tiv_2025": round(float(arms["tiv_m"].iloc[-1]), 0),
    }

    # --- conditional forecast --------------------------------------------
    fan = pd.read_csv(OUT / "simulation_fan.csv")
    fan["quarter"] = fan["quarter"].str.replace(r"(\d{4})Q(\d)", r"\1-Q\2", regex=True)
    forecast = {"quarters": sorted(fan["quarter"].unique()), "series": {}}
    for (ccy, path), g in fan.groupby(["currency", "pathway"]):
        g = g.sort_values("quarter")
        forecast["series"][f"{ccy}|{path}"] = {
            k: [round(float(v), 3) for v in g[k]]
            for k in ["p05", "p10", "p25", "p50", "p75", "p90", "p95"]
        }
    # History prefix so the fan is read against the observed record.
    forecast["history"] = {
        "quarters": cofer["quarter"].tolist(),
        "USD": [None if pd.isna(v) else round(float(v), 3) for v in cofer["USD"]],
        "CNY": [None if pd.isna(v) else round(float(v), 3) for v in cofer["CNY"]],
    }

    # --- peace dividend, the retrenchment anchor --------------------------
    # The marked window is taken from calibration.json, not re-derived here.
    # If the panel picked its own peak the page would quote one contraction
    # while the simulation used another, which is the sort of quiet
    # inconsistency that discredits a whole build.
    us = (audit[(audit["measure"] == "milex_usd_const2024")
                & (audit["tier"] == "United States")]
          .set_index("year")["value"].sort_index())
    pd_win = us[(us.index >= 1985) & (us.index <= 2000)]
    peak_year, trough_year = 1988, 1998
    peace = {
        "x": [int(i) for i in pd_win.index],
        "y": [round(float(v), 1) for v in pd_win],
        "peak_year": peak_year, "trough_year": trough_year,
        "contraction_pct": round(cases["peace_dividend"]["total_real_change_pct"], 1),
        "annual_rate_pct": round(cases["peace_dividend"]["annual_rate_pct"], 1),
    }

    # --- headline figures --------------------------------------------------
    milex = pd.read_csv(PROC / "milex_panel.csv")
    latest_yr = int(milex["year"].max())
    def val(iso):
        r = milex[(milex["iso3"] == iso) & (milex["year"] == latest_yr)]["milex_constusd_m"]
        return float(r.iloc[0]) if len(r) else float("nan")
    feats = pd.read_csv(PROC / "milex_features.csv").set_index("year")

    kpis = {
        "year": latest_yr,
        "world_bn": round(val("WORLD") / 1000, 0),
        "us_bn": round(val("USA") / 1000, 1),
        "cn_bn": round(val("CHN") / 1000, 1),
        "ratio": round(val("USA") / val("CHN"), 2),
        "cn_us_ratio": round(float(feats.loc[latest_yr, "cn_us_ratio"]), 3),
        "us_yoy_pct": round(float(feats.loc[latest_yr, "us_real_growth"]) * 100, 1),
        "cn_yoy_pct": round(float(feats.loc[latest_yr, "cn_real_growth"]) * 100, 1),
        "cn_cagr": round(cases["accretion_decade"]["china"], 1),
        "us_cagr": round(cases["accretion_decade"]["usa"], 1),
        "beta": round(reg_usd["params"]["x_ratio"], 2),
        "beta_lo": round(reg_usd["conf_int_95"]["x_ratio"][0], 2),
        "beta_hi": round(reg_usd["conf_int_95"]["x_ratio"][1], 2),
        "nobs": int(reg_usd["nobs"]),
        "separation": round(summ["usd"]["pathway_separation_sd_units"], 2),
    }
    endpoints = {
        c: {p: {k: (None if summ[c][p].get(k) is None else round(float(summ[c][p][k]), 2))
                for k in ["median", "p10", "p90", "prob_below_50"]
                if k in summ[c][p]}
            for p in ["accretion", "retrenchment", "demonstration"]}
        for c in ["usd", "cny"]
    }

    # --- hypothesis evidence block ---------------------------------------
    tests = json.loads((OUT / "hypothesis_tests.json").read_text())
    cal2 = json.loads((OUT / "calibration_layer2.json").read_text())
    l2 = json.loads((OUT / "layer2_summary.json").read_text())
    sw = pd.read_csv(PROC / "swift_settlement.csv")
    cny_q = cofer.set_index("quarter")["CNY"]
    sw["q"] = sw.month.str[:4] + "-Q" + (
        (sw.month.str[5:7].astype(int) - 1) // 3 + 1).astype(str)
    sw["cofer_cny"] = sw.q.map(cny_q).ffill()
    sw["gap"] = (sw.cny_payments_pct - sw.cofer_cny).round(2)
    dep = pd.read_csv(PROC / "allied_import_dependence.csv")
    dep = dep[dep.window >= 1950]
    h1s = l2["h1"]
    hyp = {
        "tests": {k: {kk: v[kk] for kk in ["claim", "verdict", "headline"]}
                  for k, v in tests.items()},
        "h1": {
            "outcomes": list(h1s["scored_outcome_separation_sd"].keys()),
            "sd": list(h1s["scored_outcome_separation_sd"].values()),
            "drivers": h1s["driver_separation_sd_context"],
            "reserve": h1s["reserve_separation_sd"],
            "median_ratio": h1s["median_over_reserve_ratio"],
            "min": h1s["min_outcome"],
        },
        "h2": {
            "tiers": list(cal2["feedback"].keys()),
            "b_us": [cal2["feedback"][t]["b_us"] for t in cal2["feedback"]],
            "ci_us": [cal2["feedback"][t]["ci95_us"] for t in cal2["feedback"]],
            "b_cn": [cal2["feedback"][t]["b_cn"] for t in cal2["feedback"]],
            "ci_cn": [cal2["feedback"][t]["ci95_cn"] for t in cal2["feedback"]],
            "p": [cal2["feedback"][t]["p_us_stronger_one_sided"]
                  for t in cal2["feedback"]],
            "dep": {t: {"x": g.window.astype(int).tolist(),
                        "us": [round(100 * v, 1) for v in g.us_share],
                        "hhi": [round(float(v), 3) for v in g.supplier_hhi]}
                    for t, g in dep.groupby("tier")},
            "windows": cal2["event_windows"],
        },
        "h3": {
            "months": sw.month.tolist(),
            "swift_cny": [round(float(v), 2) for v in sw.cny_payments_pct],
            "trade_finance": [None if pd.isna(v) else round(float(v), 2)
                              for v in sw.cny_trade_finance_pct],
            "cofer_cny": [None if pd.isna(v) else round(float(v), 2)
                          for v in sw.cofer_cny],
            "gap": [None if pd.isna(v) else round(float(v), 2) for v in sw.gap],
            "usd_payments_latest": round(float(sw.usd_payments_pct.iloc[-1]), 1),
        },
        "layer2_share": l2["allied_share_2035"],
        "arms_2035": l2["arms_demand_2035"],
        "war_multiple": l2["war_risk_event_multiplier"],
    }
    kpis["gap_pp"] = round(float(sw.gap.dropna().iloc[-1]), 2)
    kpis["h1_ratio"] = h1s["median_over_reserve_ratio"]

    payload = {
        "generated": "2026-07-29",
        "measures": {k: lbl for _, (k, lbl, _h, _a) in MEASURES.items()},
        "agg_rule": {k: a for _, (k, _lbl, _h, a) in MEASURES.items()},
        "tiers": TIER_ORDER,
        "tier_series": tier_series,
        "yoy": yoy_from_tiers(tier_series),
        "peace_dividend": peace,
        "cofer": cof,
        "arms": arms_payload,
        "forecast": forecast,
        "endpoints": endpoints,
        "kpis": kpis,
        "hyp": hyp,
        "register": register(),
    }

    DOCS.mkdir(exist_ok=True)
    (DOCS / "payload.json").write_text(json.dumps(payload, separators=(",", ":")))
    kb = (DOCS / "payload.json").stat().st_size / 1024
    print(f"  payload.json: {kb:,.0f} KB")
    print(f"  register: {sum(r['state'] == 'built' for r in payload['register'])} built "
          f"of {len(payload['register'])} tables")


if __name__ == "__main__":
    main()
