"""
build_hypothesis_panel.py
Stage 4: one dataset that measures every hypothesis.

WHAT THIS IS
------------
Every number the three hypotheses rest on, in a single tidy table:
data/processed/hypothesis_panel.csv. One row is one measurement. The
grammar is constant across the file:

    hypothesis  H1 | H2 | H3 | context
    role        test | evidence | input | robustness
    series      what is being measured
    scope       which actor, tier, currency, pathway or window
    freq        the native frequency of the row
    period      year, quarter, month or window label
    value       the number
    unit        its unit
    source      where it came from

Test rows carry the computed statistics (separations, coefficients,
p values). Evidence rows carry the observed series each test reads
(reserve shares, settlement shares, burden shares, dependence windows,
event-window growth). Input rows carry simulated endpoints. Context
rows carry the structural exposures the channels reference (warheads,
chokepoint flows, fabrication revenue, shipbuilding shares). The point
of one file is auditability: a reader can filter on H2 and see the
whole case, test and evidence together, without opening the pipeline.

Also built here, because it belongs to the same audit trail:

cofer_flow_attribution.csv. The reserve shares in COFER are stock
shares at market value, so exchange-rate swings move them without a
single asset being traded. The exact valuation adjustment needs
currency-by-currency price indices that are not in the evidence base,
so the robustness series used instead is flow attribution: each
currency's share of the change in total allocated claims per quarter.
It is a bounded, honest proxy: flows and valuation are mixed in the
quarterly delta, but a currency persistently absorbing a larger share
of new claims than its stock share implies accumulation regardless of
valuation. The limitation is documented here and in the register.

hypothesis_tests.json. The three verdicts with their statistics, one
place, machine readable, consumed by the dashboard ledger.

Run:  python src/build_hypothesis_panel.py
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
OUT = ROOT / "outputs"

COLS = ["hypothesis", "role", "series", "scope", "freq", "period",
        "value", "unit", "source"]


def rows_from(df, hypothesis, role, series, scope_col, period_col,
              value_col, unit, source, freq):
    out = pd.DataFrame({
        "hypothesis": hypothesis, "role": role, "series": series,
        "scope": df[scope_col].astype(str) if scope_col else "",
        "freq": freq, "period": df[period_col].astype(str),
        "value": pd.to_numeric(df[value_col], errors="coerce"),
        "unit": unit, "source": source})
    return out.dropna(subset=["value"])


def flow_attribution() -> pd.DataFrame:
    c = pd.read_csv(PROC / "cofer_quarterly_long.csv")
    claims = c[c.measure == "claims_usd_m"].pivot_table(
        "value", "quarter", "ccy").sort_index()
    total = claims.sum(axis=1)
    d_claims, d_total = claims.diff(), total.diff()
    flow = (d_claims.div(d_total, axis=0) * 100)[d_total > 0]
    out = (flow[["USD", "EUR", "CNY", "JPY", "GBP"]]
           .reset_index().melt("quarter", var_name="ccy",
                               value_name="flow_share_pct").dropna())
    out["source"] = ("Derived from IMF COFER allocated claims; each currency's "
                     "share of the quarterly change in total allocated claims")
    out.to_csv(PROC / "cofer_flow_attribution.csv", index=False)
    return out


def main() -> None:
    cal1 = json.loads((OUT / "calibration.json").read_text())
    cal2 = json.loads((OUT / "calibration_layer2.json").read_text())
    sim1 = json.loads((OUT / "simulation_summary.json").read_text())
    sim2 = json.loads((OUT / "layer2_summary.json").read_text())
    parts: list[pd.DataFrame] = []

    # ------------------------------------------------------------- H1
    h1 = sim2["h1"]
    parts.append(pd.DataFrame([
        {"hypothesis": "H1", "role": "test", "series": "pathway_separation",
         "scope": k, "freq": "endpoint", "period": "2035", "value": v,
         "unit": "sd units",
         "source": "simulate_layer2.py, 10000 draws per pathway, seed 20260724"}
        for k, v in h1["scored_outcome_separation_sd"].items()]))
    parts.append(pd.DataFrame([
        {"hypothesis": "H1", "role": "test", "series": "pathway_separation_driver",
         "scope": k, "freq": "endpoint", "period": "2035", "value": v,
         "unit": "sd units", "source": "simulate_layer2.py (context, not scored)"}
        for k, v in h1["driver_separation_sd_context"].items()]))
    parts.append(pd.DataFrame([
        {"hypothesis": "H1", "role": "test", "series": "reserve_channel_separation",
         "scope": "USD share", "freq": "endpoint", "period": "2035",
         "value": h1["reserve_separation_sd"], "unit": "sd units",
         "source": "simulate.py layer 1"},
        {"hypothesis": "H1", "role": "test", "series": "median_over_reserve_ratio",
         "scope": "scored outcomes", "freq": "endpoint", "period": "2035",
         "value": h1["median_over_reserve_ratio"], "unit": "ratio",
         "source": "simulate_layer2.py"}]))
    for p, tiers in sim2["endpoints_2035_musd"].items():
        parts.append(pd.DataFrame([
            {"hypothesis": "H1", "role": "input", "series": "simulated_endpoint",
             "scope": f"{t} | {p}", "freq": "endpoint", "period": "2035",
             "value": d["median"], "unit": "USD m, constant 2024",
             "source": "layer2_summary.json"} for t, d in tiers.items()]))
    parts.append(pd.DataFrame([
        {"hypothesis": "H1", "role": "input", "series": "allied_share_2035",
         "scope": p, "freq": "endpoint", "period": "2035", "value": d["median"],
         "unit": "% of world", "source": "layer2_summary.json"}
        for p, d in sim2["allied_share_2035"].items()]))

    # ------------------------------------------------------------- H2
    for tier, f in cal2["feedback"].items():
        parts.append(pd.DataFrame([
            {"hypothesis": "H2", "role": "test", "series": "feedback_b_us",
             "scope": tier, "freq": "annual", "period": "1951-2025",
             "value": f["b_us"], "unit": "pp per pp, lag 1",
             "source": "calibrate_layer2.py, HAC(3)"},
            {"hypothesis": "H2", "role": "test", "series": "feedback_b_cn",
             "scope": tier, "freq": "annual", "period": "1951-2025",
             "value": f["b_cn"], "unit": "pp per pp, lag 1",
             "source": "calibrate_layer2.py, HAC(3)"},
            {"hypothesis": "H2", "role": "test", "series": "p_us_stronger",
             "scope": tier, "freq": "annual", "period": "1951-2025",
             "value": f["p_us_stronger_one_sided"], "unit": "one-sided p",
             "source": "delta method on |b_us| - |b_cn|"}]))
    actor = {"us_mean": "United States", "cn_mean": "China"}
    for w, d in cal2["event_windows"].items():
        yrs = [seg for seg in w.split("_") if seg.isdigit()]
        period = "-".join(yrs)
        label = w.rsplit("_" + yrs[0], 1)[0].replace("_", " ")
        for scope, v in d.items():
            parts.append(pd.DataFrame([{
                "hypothesis": "H2", "role": "evidence",
                "series": "event_window_growth",
                "scope": f"{actor.get(scope, scope)} | {label}",
                "freq": "annual mean", "period": period,
                "value": v, "unit": "% real, mean over window",
                "source": "SIPRI milex via calibrate_layer2.py"}]))
    dep = pd.read_csv(PROC / "allied_import_dependence.csv")
    dep["us_share_pct"] = dep.us_share * 100
    parts.append(rows_from(dep.assign(scope=dep.tier + " | " + dep.window.astype(str)),
                           "H2", "evidence", "us_supplier_share", "scope", "window",
                           "us_share_pct", "% of tier imports, 5-year order window",
                           "SIPRI trade register", "window"))
    parts.append(rows_from(dep.assign(scope=dep.tier + " | " + dep.window.astype(str)),
                           "H2", "evidence", "supplier_hhi", "scope", "window",
                           "supplier_hhi", "Herfindahl, 5-year order window",
                           "SIPRI trade register", "window"))
    nato = pd.read_csv(PROC / "nato_burden.csv")
    med = nato.groupby("year", as_index=False).pct_gdp.median()
    parts.append(rows_from(med, "H2", "evidence", "nato_median_burden", None,
                           "year", "pct_gdp", "% of GDP, median ally",
                           "NATO defence expenditure 2026, Table 3", "annual"))
    for t, d in cal2["demonstration_mobilization_2022"].items():
        parts.append(pd.DataFrame([{
            "hypothesis": "H2", "role": "evidence", "series": "mobilization_2022_delta",
            "scope": t, "freq": "annual mean", "period": "2022-2025 vs 2015-2021",
            "value": d["delta_pp"], "unit": "pp step-up in real growth",
            "source": "calibrate_layer2.py; n = 1 episode"}]))

    # ------------------------------------------------------------- H3
    c = pd.read_csv(PROC / "cofer_quarterly_long.csv")
    shares = c[c.measure == "share_pct"]
    for ccy in ["USD", "CNY", "EUR"]:
        s = shares[shares.ccy == ccy]
        parts.append(rows_from(s, "H3", "evidence", "cofer_share", "ccy",
                               "quarter", "value", "% of allocated reserves",
                               "IMF COFER", "quarterly"))
    sw = pd.read_csv(PROC / "swift_settlement.csv")
    parts.append(rows_from(sw.assign(ccy="CNY"), "H3", "evidence",
                           "swift_payments_share", "ccy", "month",
                           "cny_payments_pct", "% of global payments value",
                           "Swift RMB / Global Currency Tracker", "monthly"))
    parts.append(rows_from(sw.assign(ccy="CNY"), "H3", "evidence",
                           "swift_trade_finance_share", "ccy", "month",
                           "cny_trade_finance_pct", "% of trade finance value",
                           "Swift RMB / Global Currency Tracker", "monthly"))
    # The settlement-reserve gap: monthly Swift CNY minus the COFER CNY
    # share of that month's quarter (latest available quarter carried
    # forward for months COFER has not yet reported).
    cny_q = (shares[shares.ccy == "CNY"].set_index("quarter").value)
    sw["quarter"] = sw.month.str[:4] + "-Q" + (
        (sw.month.str[5:7].astype(int) - 1) // 3 + 1).astype(str)
    sw["cofer_cny"] = sw.quarter.map(cny_q).ffill()
    sw["gap_pp"] = (sw.cny_payments_pct - sw.cofer_cny).round(2)
    parts.append(rows_from(sw.assign(ccy="CNY"), "H3", "test",
                           "settlement_reserve_gap", "ccy", "month", "gap_pp",
                           "pp, Swift payments share minus COFER share",
                           "derived: Swift minus IMF COFER", "monthly"))
    flow = flow_attribution()
    parts.append(rows_from(flow, "H3", "robustness", "cofer_flow_share",
                           "ccy", "quarter", "flow_share_pct",
                           "% of quarterly change in allocated claims",
                           "derived from IMF COFER claims", "quarterly"))
    dr = cal1["cases"]["drift_regimes"]
    parts.append(pd.DataFrame([
        {"hypothesis": "H3", "role": "test", "series": "drift_regime",
         "scope": f"{ccy} | {reg}", "freq": "quarterly mean",
         "period": "pre/post 2022-Q1", "value": dr[f"{ccy.lower()}_{reg}"],
         "unit": "pp per quarter", "source": "calibrate.py"}
        for ccy in ["USD", "CNY"] for reg in ["pre", "post"]]))
    parts.append(pd.DataFrame([
        {"hypothesis": "H3", "role": "test", "series": "reserve_pathway_separation",
         "scope": "USD share", "freq": "endpoint", "period": "2035",
         "value": sim1["usd"]["pathway_separation_sd_units"], "unit": "sd units",
         "source": "simulate.py layer 1"}]))

    # --------------------------------------------------------- context
    nuc = pd.read_csv(PROC / "nuclear_panel.csv")
    parts.append(rows_from(nuc, "context", "input", "nuclear_stockpile",
                           "country", "year", "stockpile", "warheads",
                           "FAS Nuclear Notebook 2025/2026; DOD projections",
                           "annual"))
    ch = pd.read_csv(PROC / "energy_chokepoints.csv")
    latest = ch[ch.year == ch.year.max()]
    parts.append(rows_from(latest, "context", "input", "chokepoint_flow",
                           "chokepoint", "year", "flow_mbd",
                           "million barrels per day",
                           "EIA World Oil Transit Chokepoints", "annual"))
    semi = pd.read_csv(PROC / "semiconductor_channel.csv")
    parts.append(rows_from(semi, "context", "input", "tsmc_revenue", None,
                           "quarter", "tsmc_revenue_usd_m", "USD m",
                           "TSMC consolidated statements", "quarterly"))
    mar = pd.read_csv(PROC / "maritime_panel.csv")
    built = mar[(mar.series == "ships_built_gt")
                & mar.economy.isin(["World", "China (derived)"])]
    parts.append(rows_from(built, "context", "input", "ships_built_gt",
                           "economy", "year", "value", "gross tons",
                           "UNCTADstat", "annual"))
    lsci = mar[(mar.series == "lsci")
               & mar.economy.isin(["China", "United States", "Taiwan"])]
    parts.append(rows_from(lsci, "context", "input", "lsci", "economy",
                           "year", "value", "index, annual mean", "UNCTADstat",
                           "annual"))
    br = pd.read_csv(PROC / "steo_brent.csv")
    br["year"] = br.month.str[:4]
    bry = br.groupby("year", as_index=False).brent_usd_bbl.mean().round(1)
    parts.append(rows_from(bry, "context", "input", "brent_annual_mean", None,
                           "year", "brent_usd_bbl", "USD per barrel",
                           "EIA STEO July 2026", "annual"))
    war = pd.read_csv(PROC / "war_risk_events.csv")
    parts.append(rows_from(war, "context", "input", "war_risk_multiple",
                           "episode", "date", "multiple",
                           "x, AWRP during over before",
                           "Argus Media, June 2026", "event"))

    panel = pd.concat(parts, ignore_index=True)[COLS]
    panel.to_csv(PROC / "hypothesis_panel.csv", index=False)

    # ---------------------------------------------------- verdict file
    latest_gap = sw.dropna(subset=["gap_pp"]).iloc[-1]
    tests = {
        "H1": {
            "claim": "The pathway to primacy conditions outcomes more than the "
                     "endpoint itself",
            "verdict": sim2["h1"]["verdict"],
            "headline": f"median scored outcome separates by "
                        f"{sim2['h1']['median_outcome_sd']} sd, "
                        f"{sim2['h1']['median_over_reserve_ratio']}x the reserve "
                        f"channel; exception: "
                        f"{sim2['h1']['min_outcome']['name']} at "
                        f"{sim2['h1']['min_outcome']['sd']} sd",
            "statistics": sim2["h1"],
        },
        "H2": {
            "claim": "American retrenchment moves allied budgets harder than "
                     "Chinese growth alone",
            "verdict": "directionally supported, not resolved",
            "headline": "the US coefficient exceeds the China coefficient in "
                        "absolute size in all three tiers (one-sided p 0.22 to "
                        "0.35); the 2025 episode shows substitution, US -7.5 "
                        "percent against NATO Europe +15.6 percent",
            "statistics": cal2["h2_historical"],
        },
        "H3": {
            "claim": "Reserve composition moves late and least among the "
                     "commercial channels",
            "verdict": "supported",
            "headline": f"renminbi settles {sw.cny_payments_pct.iloc[-1]}% of "
                        f"payments but holds {round(float(sw.cofer_cny.iloc[-1]), 2)}% "
                        f"of reserves (gap {latest_gap.gap_pp} pp, "
                        f"{latest_gap.month}); USD pathway separation 0.36 sd",
            "statistics": {
                "latest_gap_pp": float(latest_gap.gap_pp),
                "drift_regimes": dr,
                "reserve_separation_sd":
                    sim1["usd"]["pathway_separation_sd_units"]},
        },
    }
    (OUT / "hypothesis_tests.json").write_text(json.dumps(tests, indent=1))

    print(f"hypothesis_panel.csv: {len(panel)} rows across "
          f"{panel.hypothesis.nunique()} hypotheses + context")
    print(panel.groupby(['hypothesis', 'role']).size().to_string())
    print(f"settlement-reserve gap, latest: {latest_gap.gap_pp} pp ({latest_gap.month})")


if __name__ == "__main__":
    main()
