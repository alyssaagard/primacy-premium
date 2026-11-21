"""
build_hypothesis_panel.py
Stage 4. Hypothesis dataset and verdicts.

Output
  data/processed/hypothesis_panel.csv        one row per measurement
  data/processed/cofer_flow_attribution.csv  flow shares by currency
  outputs/hypothesis_tests.json              verdicts and statistics

hypothesis_panel.csv columns
  hypothesis  H1, H2, H3 or context
  role        test, evidence, input, robustness or sensitivity
  series      quantity measured
  scope       actor, tier, currency, pathway or window
  freq        native frequency of the row
  period      year, quarter, month or window
  value, unit, source

Flow attribution
  COFER shares are stock shares at current exchange rates, so they move
  with valuation as well as transactions. An exact valuation adjustment
  requires currency price indices that this project does not hold. As a
  partial check, each currency's share of the quarterly change in total
  claims is computed for quarters in which total claims rose. The series
  still mixes flows and valuation.

Verdict rules
  H1  supported if the median scored separation exceeds twice the US
      dollar reserve share separation (stage 3b). Descriptive.
  H2  supported if the pooled panel test of |b_us| > |b_cn| has a
      one-sided p value below 0.05 (stage 2b).
  H3  supported on the available measures if (a) the 95 percent interval
      of the expenditure coefficient in the dollar share regression
      contains zero, (b) the dollar share separation is below the median
      scored expenditure separation, and (c) the renminbi's payments
      share exceeds its reserve share in every month observed. The
      shipping, energy and semiconductor channels are not simulated, so
      the comparison across commercial channels is not tested.

Run: python src/build_hypothesis_panel.py
"""

import json

import pandas as pd

from config import OUT, PROC
from tiers import growth_table

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


def row(hypothesis, role, series, scope, freq, period, value, unit, source):
    return pd.DataFrame([dict(zip(COLS, [hypothesis, role, series, scope,
                                         freq, str(period), value, unit,
                                         source]))])


def flow_attribution() -> pd.DataFrame:
    c = pd.read_csv(PROC / "cofer_quarterly_long.csv")
    claims = c[c.measure == "claims_usd_m"].pivot_table(
        "value", "quarter", "ccy").sort_index()
    total = claims["TOTAL"]
    d_claims, d_total = claims.diff(), total.diff()
    flow = (d_claims.div(d_total, axis=0) * 100)[d_total > 0]
    out = (flow[["USD", "EUR", "CNY", "JPY", "GBP"]].reset_index()
           .melt("quarter", var_name="ccy", value_name="flow_share_pct")
           .dropna())
    out["source"] = ("Derived from IMF COFER claims: currency share of the "
                     "quarterly change in total claims, quarters with "
                     "rising totals")
    out.to_csv(PROC / "cofer_flow_attribution.csv", index=False)
    return out


def settlement_gap() -> pd.DataFrame:
    """Monthly Swift CNY payments share minus the COFER CNY share of the
    same quarter. The latest COFER quarter is carried forward."""
    c = pd.read_csv(PROC / "cofer_quarterly_long.csv")
    cny_q = (c[(c.measure == "share_pct") & (c.ccy == "CNY")]
             .set_index("quarter").value)
    sw = pd.read_csv(PROC / "swift_settlement.csv")
    sw["quarter"] = sw.month.str[:4] + "-Q" + (
        (sw.month.str[5:7].astype(int) - 1) // 3 + 1).astype(str)
    sw["cofer_cny"] = sw.quarter.map(cny_q).ffill()
    sw["gap_pp"] = (sw.cny_payments_pct - sw.cofer_cny).round(2)
    return sw


def main() -> None:
    cal1 = json.loads((OUT / "calibration.json").read_text())
    cal2 = json.loads((OUT / "calibration_layer2.json").read_text())
    sim1 = json.loads((OUT / "simulation_summary.json").read_text())
    sim2 = json.loads((OUT / "layer2_summary.json").read_text())
    horizon = str(sim2["horizon"][1])
    draws = f"{sim2['draws']} draws per pathway, seed {sim2['seed']}"
    parts: list[pd.DataFrame] = []

    # ------------------------------------------------------------- H1
    h1 = sim2["h1"]
    for k, v in h1["scored_outcome_separation_sd"].items():
        parts.append(row("H1", "test", "pathway_separation", k, "endpoint",
                         horizon, v, "sd units",
                         f"simulate_layer2.py, {draws}"))
    for k, v in h1["driver_separation_sd_context"].items():
        parts.append(row("H1", "test", "pathway_separation_driver", k,
                         "endpoint", horizon, v, "sd units",
                         "simulate_layer2.py; imposed, not scored"))
    parts.append(row("H1", "test", "reserve_channel_separation", "USD share",
                     "endpoint", horizon, h1["reserve_separation_sd"],
                     "sd units", "simulate.py"))
    parts.append(row("H1", "test", "median_over_reserve_ratio",
                     "scored outcomes", "endpoint", horizon,
                     h1["median_over_reserve_ratio"], "ratio",
                     "simulate_layer2.py"))
    for p, tiers in sim2["endpoints_musd"].items():
        for t, d in tiers.items():
            parts.append(row("H1", "input", "simulated_endpoint", f"{t} | {p}",
                             "endpoint", horizon, d["median"],
                             "USD m, constant 2024", "layer2_summary.json"))
    for p, d in sim2["allied_share"].items():
        parts.append(row("H1", "input", "allied_share", p, "endpoint",
                         horizon, d["median"], "% of world",
                         "layer2_summary.json"))

    # ------------------------------------------------------------- H2
    h2 = cal2["h2"]
    pr = h2["primary"]
    span = f"{pr['sample'][0]}-{pr['sample'][1]}"
    panel_src = ("calibrate_layer2.py: country panel, fixed effects, "
                 "expenditure-weighted, Driscoll-Kraay(3)")
    for name, key, unit in [("panel_b_us", "b_us", "pp per pp, lag 1"),
                            ("panel_b_cn", "b_cn", "pp per pp, lag 1"),
                            ("panel_abs_gap", "abs_gap", "pp per pp"),
                            ("panel_p_one_sided", "p_one_sided",
                             "one-sided p")]:
        parts.append(row("H2", "test", name, "All allied tiers", "annual",
                         span, pr[key], unit, panel_src))
        for tier, r in h2["by_tier"].items():
            parts.append(row("H2", "sensitivity", name, tier, "annual", span,
                             r[key], unit, panel_src))
    for label, r in h2["sensitivity"].items():
        s = f"{r['sample'][0]}-{r['sample'][1]}"
        for name, key, unit in [("panel_b_us", "b_us", "pp per pp, lag 1"),
                                ("panel_b_cn", "b_cn", "pp per pp, lag 1"),
                                ("panel_p_one_sided", "p_one_sided",
                                 "one-sided p")]:
            parts.append(row("H2", "sensitivity", name,
                             f"All allied tiers | {label}", "annual", s,
                             r[key], unit, "calibrate_layer2.py"))
    for tier, f in cal2["feedback"].items():
        s = f"{f['sample'][0]}-{f['sample'][1]}"
        src = "calibrate_layer2.py: tier equation, OLS, HAC(3)"
        parts.append(row("H2", "input", "feedback_b_us", tier, "annual", s,
                         f["b_us"], "pp per pp, lag 1", src))
        parts.append(row("H2", "input", "feedback_b_cn", tier, "annual", s,
                         f["b_cn"], "pp per pp, lag 1", src))
        parts.append(row("H2", "sensitivity", "static_tier_p_one_sided", tier,
                         "annual", s, f["static_test"]["p_one_sided"],
                         "one-sided p", src + "; first-release test"))
    actor = {"us_mean": "United States", "cn_mean": "China"}
    for w, d in cal2["event_windows"].items():
        yrs = [seg for seg in w.split("_") if seg.isdigit()]
        label = w.rsplit("_" + yrs[0], 1)[0].replace("_", " ")
        for scope, v in d.items():
            parts.append(row("H2", "evidence", "event_window_growth",
                             f"{actor.get(scope, scope)} | {label}",
                             "annual mean", "-".join(yrs), v,
                             "% real, mean over window",
                             "SIPRI via calibrate_layer2.py"))
    dep = pd.read_csv(PROC / "allied_import_dependence.csv")
    dep["us_share_pct"] = dep.us_share * 100
    dep["scope"] = dep.tier + " | " + dep.window.astype(str)
    parts.append(rows_from(dep, "H2", "evidence", "us_supplier_share",
                           "scope", "window", "us_share_pct",
                           "% of tier imports, 5-year order window",
                           "SIPRI trade register", "window"))
    parts.append(rows_from(dep, "H2", "evidence", "supplier_hhi", "scope",
                           "window", "supplier_hhi",
                           "Herfindahl, 5-year order window",
                           "SIPRI trade register", "window"))
    nato = pd.read_csv(PROC / "nato_burden.csv")
    med = nato.groupby("year", as_index=False).pct_gdp.median()
    parts.append(rows_from(med, "H2", "evidence", "nato_median_burden", None,
                           "year", "pct_gdp", "% of GDP, median ally",
                           "NATO defence expenditure, Table 3", "annual"))
    for t, d in cal2["demonstration_mobilization_2022"].items():
        parts.append(row("H2", "evidence", "mobilization_2022_delta", t,
                         "annual mean", "2022 onward vs 2015-2021",
                         d["delta_pp"], "pp change in mean real growth",
                         "calibrate_layer2.py; one episode"))

    # ------------------------------------------------------------- H3
    c = pd.read_csv(PROC / "cofer_quarterly_long.csv")
    shares = c[c.measure == "share_pct"]
    for ccy in ["USD", "CNY", "EUR"]:
        parts.append(rows_from(shares[shares.ccy == ccy], "H3", "evidence",
                               "cofer_share", "ccy", "quarter", "value",
                               "% of foreign exchange reserves", "IMF COFER",
                               "quarterly"))
    sw = settlement_gap().assign(ccy="CNY")
    swift_src = "Swift RMB Tracker / Global Currency Tracker"
    parts.append(rows_from(sw, "H3", "evidence", "swift_payments_share",
                           "ccy", "month", "cny_payments_pct",
                           "% of global payments value", swift_src, "monthly"))
    parts.append(rows_from(sw, "H3", "evidence", "swift_trade_finance_share",
                           "ccy", "month", "cny_trade_finance_pct",
                           "% of trade finance value", swift_src, "monthly"))
    parts.append(rows_from(sw, "H3", "test", "settlement_reserve_gap", "ccy",
                           "month", "gap_pp",
                           "pp, Swift payments share minus COFER share",
                           "derived: Swift minus IMF COFER", "monthly"))
    parts.append(rows_from(flow_attribution(), "H3", "robustness",
                           "cofer_flow_share", "ccy", "quarter",
                           "flow_share_pct",
                           "% of quarterly change in total claims",
                           "derived from IMF COFER claims", "quarterly"))
    dr = cal1["cases"]["drift_regimes"]
    for ccy in ["USD", "CNY"]:
        for reg in ["pre", "post"]:
            parts.append(row("H3", "evidence", "drift_regime",
                             f"{ccy} | {reg}", "quarterly mean",
                             "before / from 2022-Q1",
                             dr[f"{ccy.lower()}_{reg}"], "pp per quarter",
                             "calibrate.py"))
    reg = cal1["usd_regression"]
    lo, hi = reg["conf_int_95"]["x_ratio"]
    for name, v in [("usd_coefficient", reg["params"]["x_ratio"]),
                    ("usd_coefficient_ci_low", lo),
                    ("usd_coefficient_ci_high", hi)]:
        parts.append(row("H3", "test", name, "USD share", "quarterly",
                         "-".join(cal1["meta"]["cofer_span"]), round(v, 3),
                         "pp per unit change in log expenditure ratio",
                         "calibrate.py, HAC(4)"))
    usd_sep = sim1["usd"]["pathway_separation_sd_units"]
    parts.append(row("H3", "test", "reserve_pathway_separation", "USD share",
                     "endpoint", horizon, round(usd_sep, 3), "sd units",
                     "simulate.py"))
    wide = pd.read_csv(PROC / "cofer_shares_wide.csv").set_index("quarter")
    since = wide.loc["2016-Q4":]
    minor = [k for k in ["AUD", "CAD", "CHF", "OTHER"] if k in wide.columns]
    change = {"USD": since.USD.iloc[-1] - since.USD.iloc[0],
              "CNY": since.CNY.iloc[-1] - since.CNY.iloc[0],
              "Other than USD, EUR, JPY, GBP, CNY":
                  since[minor].sum(axis=1).iloc[-1]
                  - since[minor].sum(axis=1).iloc[0]}
    for k, v in change.items():
        parts.append(row("H3", "evidence", "share_change_since_2016Q4", k,
                         "window", f"2016-Q4 to {since.index[-1]}",
                         round(float(v), 2), "pp", "IMF COFER"))

    # --------------------------------------------------------- context
    nuc = pd.read_csv(PROC / "nuclear_panel.csv")
    parts.append(rows_from(nuc, "context", "input", "nuclear_stockpile",
                           "country", "year", "stockpile", "warheads",
                           "FAS Nuclear Notebook; DOD projections", "annual"))
    ch = pd.read_csv(PROC / "energy_chokepoints.csv")
    parts.append(rows_from(ch[ch.year == ch.year.max()], "context", "input",
                           "chokepoint_flow", "chokepoint", "year", "flow_mbd",
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
                           "year", "value", "index, annual mean",
                           "UNCTADstat", "annual"))
    br = pd.read_csv(PROC / "steo_brent.csv")
    br["year"] = br.month.str[:4]
    bry = br.groupby("year", as_index=False).brent_usd_bbl.mean().round(1)
    parts.append(rows_from(bry, "context", "input", "brent_annual_mean", None,
                           "year", "brent_usd_bbl", "USD per barrel",
                           br.source.iloc[0], "annual"))
    war = pd.read_csv(PROC / "war_risk_events.csv")
    parts.append(rows_from(war, "context", "input", "war_risk_multiple",
                           "episode", "date", "multiple",
                           "ratio of premium during to before the episode",
                           war.source.iloc[0], "event"))

    panel = pd.concat(parts, ignore_index=True)[COLS]
    panel.to_csv(PROC / "hypothesis_panel.csv", index=False)

    # ---------------------------------------------------- verdict file
    g = growth_table()
    last = int(g.index.max())
    gap_ok = bool((sw.gap_pp.dropna() > 0).all())
    ci_spans_zero = bool(lo < 0 < hi)
    sep_below = bool(usd_sep < h1["median_outcome_sd"])
    h3_ok = gap_ok and ci_spans_zero and sep_below
    latest = sw.dropna(subset=["gap_pp"]).iloc[-1]
    tests = {
        "H1": {
            "claim": "Allied expenditure outcomes differ across pathways by "
                     "more than the reserve channel does",
            "verdict": h1["verdict"],
            "headline": (
                f"median scored separation {h1['median_outcome_sd']} sd, "
                f"{h1['median_over_reserve_ratio']} times the reserve channel "
                f"({h1['reserve_separation_sd']} sd); largest "
                f"{h1['max_outcome']['name']} at {h1['max_outcome']['sd']} sd, "
                f"smallest {h1['min_outcome']['name']} at "
                f"{h1['min_outcome']['sd']} sd; descriptive, not a "
                "significance test"),
            "statistics": h1,
        },
        "H2": {
            "claim": "Allied expenditure responds more strongly to US "
                     "expenditure than to Chinese expenditure",
            "verdict": h2["verdict"],
            "headline": (
                f"pooled panel of {pr['n_countries']} countries, "
                f"{pr['sample'][0]} to {pr['sample'][1]}: b_us {pr['b_us']} "
                f"(se {pr['se_us']}), b_cn {pr['b_cn']} (se {pr['se_cn']}), "
                f"difference in magnitudes {pr['abs_gap']}, one-sided p "
                f"{pr['p_one_sided']:.2f}; {last}: United States "
                f"{g.loc[last, 'United States']:+.1f} percent, NATO Europe "
                f"{g.loc[last, 'NATO Europe']:+.1f} percent"),
            "statistics": h2,
        },
        "H3": {
            "claim": "Reserve composition responds least to the pathway, and "
                     "the dollar's decline does not accrue to the renminbi",
            "verdict": ("supported on the available measures" if h3_ok
                        else "not supported"),
            "headline": (
                f"expenditure coefficient {reg['params']['x_ratio']:+.2f} pp, "
                f"95 percent interval {lo:.2f} to {hi:.2f}; dollar share "
                f"separation {usd_sep:.2f} sd; renminbi {latest.cny_payments_pct} "
                f"percent of payments against "
                f"{float(latest.cofer_cny):.2f} percent of reserves "
                f"({latest.month}, gap {latest.gap_pp} pp); other commercial "
                "channels not simulated"),
            "statistics": {
                "criteria": {"interval_contains_zero": ci_spans_zero,
                             "separation_below_expenditure_median": sep_below,
                             "payments_share_exceeds_reserve_share": gap_ok},
                "latest_gap_pp": float(latest.gap_pp),
                "latest_gap_month": latest.month,
                "share_change_since_2016Q4_pp":
                    {k: round(float(v), 2) for k, v in change.items()},
                "drift_regimes": dr,
                "reserve_separation_sd": usd_sep},
        },
    }
    (OUT / "hypothesis_tests.json").write_text(json.dumps(tests, indent=1))

    print(f"hypothesis_panel.csv: {len(panel)} rows")
    print(panel.groupby(["hypothesis", "role"]).size().to_string())
    for k, v in tests.items():
        print(f"{k}: {v['verdict']} | {v['headline']}")


if __name__ == "__main__":
    main()
