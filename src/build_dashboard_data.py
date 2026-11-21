"""
build_dashboard_data.py
Stage 5a. Payload for the results page.

Reads the processed tables and model outputs and writes
docs/payload.json. The page template contains no data; every figure it
displays is taken from this payload.

The payload includes a register of all artifacts with row counts read
from disk. The build stops if a registered artifact is missing.

Run: python src/build_dashboard_data.py
"""

import json

import pandas as pd

from config import (ALLIED_TIERS, BUILD_DATE, DOCS, MEASURES, OUT, PATHWAYS,
                    PROC, ROOT, TIER_ORDER)
from tiers import growth_table

REGISTER = [
    # (artifact, group, directory, description)
    ("cofer_quarterly_long", "Reserve composition", PROC,
     "IMF COFER shares and claims by currency and quarter."),
    ("cofer_shares_wide", "Reserve composition", PROC,
     "Quarterly reserve shares, one column per currency."),
    ("cofer_flow_attribution", "Reserve composition", PROC,
     "Currency share of the quarterly change in total claims. Partial "
     "check on valuation effects; flows and valuation remain mixed."),
    ("swift_settlement", "Reserve composition", PROC,
     "Monthly renminbi and dollar payments shares and renminbi trade "
     "finance share from Swift tracker issues."),
    ("milex_panel", "Defense expenditure", PROC,
     "SIPRI constant 2024 USD: United States, China, Russia, world."),
    ("milex_features", "Defense expenditure", PROC,
     "China/US expenditure ratio and real growth rates."),
    ("milex_tier_panel", "Defense expenditure", PROC,
     "Five measures by analytic tier. Dollar totals are chain-linked "
     "over matched members; intensity measures are tier medians."),
    ("milex_country_panel", "Defense expenditure", PROC,
     "Country-year growth panel of the three allied tiers, used by the "
     "H2 test."),
    ("nato_burden", "Defense expenditure", PROC,
     "Defence expenditure as a share of real GDP by ally, NATO Table 3."),
    ("arms_transfers_global", "Arms transfers", PROC,
     "World deliveries of major arms in SIPRI trend-indicator values."),
    ("supplier_concentration", "Arms transfers", PROC,
     "Supplier shares and Herfindahl index by five-year order window."),
    ("arms_recipient_imports", "Arms transfers", PROC,
     "Recipient-level import volumes with tier labels."),
    ("allied_import_dependence", "Arms transfers", PROC,
     "US share and supplier Herfindahl index of allied-tier imports by "
     "five-year order window."),
    ("semiconductor_channel", "Commercial channels", PROC,
     "TSMC quarterly net revenue. Foundry market shares are not "
     "available to this project and no concentration index is computed."),
    ("maritime_panel", "Commercial channels", PROC,
     "Merchant fleet, shipbuilding, liner connectivity and container "
     "throughput. China derived from UNCTAD group aggregates."),
    ("war_risk_events", "Commercial channels", PROC,
     "Additional war risk premium before and during the 2026 Mideast "
     "Gulf episode."),
    ("energy_chokepoints", "Commercial channels", PROC,
     "Oil transit by chokepoint, million barrels per day."),
    ("steo_brent", "Commercial channels", PROC,
     "Brent spot price, monthly, observed and EIA forecast."),
    ("taiwan_strait_events", "Events", PROC,
     "Dated exercise and war-risk events with documentary sources."),
    ("alliance_matrix", "System", PROC,
     "Treaty commitment coding by tier member. Design input."),
    ("nuclear_panel", "System", PROC,
     "Warhead stockpile estimates and US Department of Defense "
     "projections for China."),
    ("calibration_layer2", "System", OUT,
     "Tier feedback equations, H2 panel tests, block growth statistics."),
    ("layer2_residual_pools", "System", OUT,
     "Residual growth by block and year, resampled in simulation."),
    ("layer2_fan", "System", OUT,
     "Simulated expenditure percentiles by block, pathway and year."),
    ("layer2_summary", "System", OUT,
     "Endpoint distributions, the H1 statistic, arms delivery projection."),
    ("calibration", "Estimation", OUT,
     "Reserve-channel regressions and reference episodes."),
    ("innovation_pools", "Estimation", OUT,
     "Reserve-channel regression residuals, resampled in simulation."),
    ("simulation_fan", "Forecast", OUT,
     "Simulated reserve share percentiles by pathway, currency, quarter."),
    ("simulation_summary", "Forecast", OUT,
     "Endpoint distributions and reserve share separation."),
    ("hypothesis_panel", "Hypothesis tests", PROC,
     "All test statistics, evidence series and context rows for H1, H2 "
     "and H3 in one long table."),
    ("hypothesis_tests", "Hypothesis tests", OUT,
     "Verdicts and statistics for the three hypotheses."),
]


def resolve(name: str, folder):
    for suffix in (".csv", ".json"):
        if (folder / f"{name}{suffix}").exists():
            return folder / f"{name}{suffix}"
    return None


def register() -> list:
    """Artifact list with row counts (CSV rows or top-level JSON keys)."""
    reg, missing = [], []
    for name, group, folder, note in REGISTER:
        path = resolve(name, folder)
        if path is None:
            missing.append(name)
            continue
        rows = (len(pd.read_csv(path)) if path.suffix == ".csv"
                else len(json.loads(path.read_text())))
        reg.append({"table": name, "group": group, "state": "built",
                    "rows": int(rows), "note": note,
                    "path": str(path.relative_to(ROOT))})
    if missing:
        raise ValueError(f"missing artifacts: {missing}")
    return reg


def nn(v, digits=3):
    return None if pd.isna(v) else round(float(v), digits)


def main() -> None:
    calib = json.loads((OUT / "calibration.json").read_text())
    summ = json.loads((OUT / "simulation_summary.json").read_text())
    cal2 = json.loads((OUT / "calibration_layer2.json").read_text())
    l2 = json.loads((OUT / "layer2_summary.json").read_text())
    tests = json.loads((OUT / "hypothesis_tests.json").read_text())
    cases = calib["cases"]
    reg_usd = calib["usd_regression"]

    # --- expenditure by tier ---------------------------------------------
    tp = pd.read_csv(PROC / "milex_tier_panel.csv")
    tier_series = {}
    for key, g in tp.groupby("measure"):
        tier_series[key] = {
            t: {"x": d.year.tolist(), "y": [round(float(v), 4) for v in d.value]}
            for t, d in g.sort_values("year").groupby("tier")}
    growth = growth_table()
    last_year = int(growth.index.max())
    yoy = []
    for t in TIER_ORDER:
        s = growth[t].dropna().loc[last_year - 9:]
        yoy.append({"tier": t, "x": [int(i) for i in s.index],
                    "y": [round(float(v), 2) for v in s]})

    # --- reserve composition ----------------------------------------------
    cofer = pd.read_csv(PROC / "cofer_shares_wide.csv")
    ccys = [c for c in ["USD", "EUR", "JPY", "GBP", "CNY", "CAD", "AUD",
                        "CHF", "OTHER"] if c in cofer.columns]
    cof = {"quarters": cofer["quarter"].tolist()}
    for c in ccys:
        cof[c] = [nn(v) for v in cofer[c]]
    cny = cofer.dropna(subset=["CNY"])
    peak, latest = cny.loc[cny["CNY"].idxmax()], cny.iloc[-1]
    cof.update({
        "cny_peak_quarter": peak["quarter"],
        "cny_peak_value": round(float(peak["CNY"]), 2),
        "cny_latest_value": round(float(latest["CNY"]), 2),
        "latest_quarter": cofer["quarter"].iloc[-1],
        "usd_first": round(float(cofer["USD"].iloc[0]), 2),
        "usd_latest": round(float(cofer["USD"].iloc[-1]), 2),
        "first_quarter": cofer["quarter"].iloc[0],
        "other_drift_pre": round(cases["diversification_drift"]["pre_2022"], 3),
        "other_drift_post": round(cases["diversification_drift"]["post_2022"], 3),
    })

    # --- arms transfers -----------------------------------------------------
    arms = pd.read_csv(PROC / "arms_transfers_global.csv")
    conc = pd.read_csv(PROC / "supplier_concentration.csv")
    conc = conc[conc.window >= 1950]
    windows = sorted(conc["window"].unique())
    hhi = conc.groupby("window")["hhi"].first().reindex(windows)
    lead = (conc.sort_values("share", ascending=False)
            .groupby("window").first().reindex(windows))
    # Last window whose five order years have all elapsed. Deliveries
    # against orders in recent windows are still incomplete.
    last_complete = int(max(w for w in windows
                            if w + 4 < int(arms.year.max())))
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
        "tiv_latest": round(float(arms["tiv_m"].iloc[-1]), 0),
        "latest_year": int(arms["year"].iloc[-1]),
    }

    # --- simulated reserve shares -------------------------------------------
    fan = pd.read_csv(OUT / "simulation_fan.csv")
    fan["quarter"] = fan["quarter"].str.replace(r"(\d{4})Q(\d)", r"\1-Q\2",
                                                regex=True)
    forecast = {"quarters": sorted(fan["quarter"].unique()), "series": {},
                "last_observed": cofer["quarter"].iloc[-1]}
    for (ccy, path), g in fan.groupby(["currency", "pathway"]):
        g = g.sort_values("quarter")
        forecast["series"][f"{ccy}|{path}"] = {
            k: [round(float(v), 3) for v in g[k]]
            for k in ["p05", "p10", "p25", "p50", "p75", "p90", "p95"]}
    forecast["history"] = {"quarters": cofer["quarter"].tolist(),
                           "USD": [nn(v) for v in cofer["USD"]],
                           "CNY": [nn(v) for v in cofer["CNY"]]}

    # --- US contraction of 1988 to 1998 ------------------------------------
    us = (tp[(tp.measure == "milex_usd_const2024")
             & (tp.tier == "United States")].set_index("year")["value"])
    win = us.loc[1985:2000]
    peace = {"x": [int(i) for i in win.index],
             "y": [round(float(v), 1) for v in win],
             "peak_year": 1988, "trough_year": 1998,
             "contraction_pct":
                 round(cases["peace_dividend"]["total_real_change_pct"], 1),
             "annual_rate_pct":
                 round(cases["peace_dividend"]["annual_rate_pct"], 1)}

    # --- headline figures -----------------------------------------------------
    milex = pd.read_csv(PROC / "milex_panel.csv")

    def val(iso):
        return float(milex[(milex.iso3 == iso)
                           & (milex.year == last_year)].milex_constusd_m.iloc[0])

    feats = pd.read_csv(PROC / "milex_features.csv").set_index("year")
    kpis = {
        "year": last_year,
        "world_bn": round(val("WORLD") / 1000, 0),
        "us_bn": round(val("USA") / 1000, 1),
        "cn_bn": round(val("CHN") / 1000, 1),
        "cn_us_ratio": round(float(feats.loc[last_year, "cn_us_ratio"]), 3),
        "us_yoy_pct": round(float(feats.loc[last_year, "us_real_growth"]) * 100, 1),
        "cn_yoy_pct": round(float(feats.loc[last_year, "cn_real_growth"]) * 100, 1),
        "cn_cagr": round(cases["accretion_decade"]["china"], 1),
        "us_cagr": round(cases["accretion_decade"]["usa"], 1),
        "cagr_start": cases["accretion_decade"]["start_year"],
        "beta": round(reg_usd["params"]["x_ratio"], 2),
        "beta_lo": round(reg_usd["conf_int_95"]["x_ratio"][0], 2),
        "beta_hi": round(reg_usd["conf_int_95"]["x_ratio"][1], 2),
        "r2": round(reg_usd["r2"], 3),
        "nobs": int(reg_usd["nobs"]),
        "separation": round(summ["usd"]["pathway_separation_sd_units"], 2),
        "usd_median_range": round(summ["usd"]["median_range_pp"], 1),
        "cny_separation": round(summ["cny"]["pathway_separation_sd_units"], 2),
        "cny_nobs": int(calib["cny_regression"]["nobs"]),
    }
    endpoints = {
        c: {p: {k: (None if summ[c][p].get(k) is None
                    else round(float(summ[c][p][k]), 2))
                for k in ["median", "p10", "p90", "prob_below_50"]}
            for p in PATHWAYS} for c in ["usd", "cny"]}

    # --- hypothesis evidence ---------------------------------------------------
    hp = pd.read_csv(PROC / "hypothesis_panel.csv")
    gap = hp[hp.series == "settlement_reserve_gap"].set_index("period").value
    sw = pd.read_csv(PROC / "swift_settlement.csv").set_index("month")
    cofer_cny = (sw.cny_payments_pct - gap).round(2)
    dep = pd.read_csv(PROC / "allied_import_dependence.csv")
    dep = dep[dep.window >= 1950]
    h1s, fb, h2 = l2["h1"], cal2["feedback"], cal2["h2"]
    hyp = {
        "tests": {k: {kk: v[kk] for kk in ["claim", "verdict", "headline"]}
                  for k, v in tests.items()},
        "h1": {"outcomes": list(h1s["scored_outcome_separation_sd"].keys()),
               "sd": list(h1s["scored_outcome_separation_sd"].values()),
               "drivers": h1s["driver_separation_sd_context"],
               "reserve": h1s["reserve_separation_sd"],
               "median_sd": h1s["median_outcome_sd"],
               "median_ratio": h1s["median_over_reserve_ratio"],
               "criterion_ratio": h1s["criterion_ratio"],
               "min": h1s["min_outcome"], "max": h1s["max_outcome"]},
        "h2": {"tiers": ALLIED_TIERS,
               "b_us": [fb[t]["b_us"] for t in ALLIED_TIERS],
               "ci_us": [fb[t]["ci95_us"] for t in ALLIED_TIERS],
               "b_cn": [fb[t]["b_cn"] for t in ALLIED_TIERS],
               "ci_cn": [fb[t]["ci95_cn"] for t in ALLIED_TIERS],
               "bg_p": [fb[t]["breusch_godfrey_p"] for t in ALLIED_TIERS],
               "sample": fb[ALLIED_TIERS[0]]["sample"],
               "primary": h2["primary"], "by_tier": h2["by_tier"],
               "sensitivity": h2["sensitivity"], "alpha": h2["alpha"],
               "static_p": [fb[t]["static_test"]["p_one_sided"]
                            for t in ALLIED_TIERS],
               "dep": {t: {"x": g.window.astype(int).tolist(),
                           "us": [round(100 * v, 1) for v in g.us_share],
                           "hhi": [round(float(v), 3) for v in g.supplier_hhi]}
                       for t, g in dep.groupby("tier")},
               "windows": cal2["event_windows"],
               "mobilization": cal2["demonstration_mobilization_2022"],
               "sim": l2["h2_simulation"]},
        "h3": {"months": sw.index.tolist(),
               "swift_cny": [round(float(v), 2) for v in sw.cny_payments_pct],
               "trade_finance": [nn(v, 2) for v in sw.cny_trade_finance_pct],
               "cofer_cny": [nn(v, 2) for v in cofer_cny],
               "gap": [nn(v, 2) for v in gap.reindex(sw.index)],
               "usd_payments_latest":
                   round(float(sw.usd_payments_pct.iloc[-1]), 1),
               "criteria": tests["H3"]["statistics"]["criteria"],
               "share_change":
                   tests["H3"]["statistics"]["share_change_since_2016Q4_pp"]},
        "allied_share": l2["allied_share"],
        "endpoints_musd": l2["endpoints_musd"],
        "arms": l2["arms_demand"],
        "war_multiple": l2["war_risk_event_multiplier"],
    }
    kpis["gap_pp"] = round(float(gap.dropna().iloc[-1]), 2)

    reg = register()
    semi = pd.read_csv(PROC / "semiconductor_channel.csv")
    brent = pd.read_csv(PROC / "steo_brent.csv")
    nato = pd.read_csv(PROC / "nato_burden.csv")
    vintage = {
        "cofer": [cofer["quarter"].iloc[0], cofer["quarter"].iloc[-1]],
        "milex": [int(milex.year.min()), last_year],
        "swift": [sw.index[0], sw.index[-1]], "swift_issues": int(len(sw)),
        "tsmc": [semi.quarter.iloc[0], semi.quarter.iloc[-1]],
        "tsmc_quarters": int(len(semi)),
        "tsmc_latest_usd_m": round(float(semi.tsmc_revenue_usd_m.iloc[-1]), 0),
        "steo": brent.source.iloc[0].split(",")[1].strip(),
        "nato": [int(nato.year.min()), int(nato.year.max())],
        "feedback_sample": fb[ALLIED_TIERS[0]]["sample"],
        "residual_sample": cal2["residual_sample"],
    }
    meta = {
        "generated": BUILD_DATE, "seed": l2["seed"], "draws": l2["draws"],
        "horizon": l2["horizon"], "base_year": l2["base_year"],
        "n_artifacts": len(reg),
        "n_rows": int(sum(r["rows"] for r in reg)),
        "n_scripts": sum("__main__" in f.read_text()
                         for f in (ROOT / "src").glob("*.py")),
    }

    payload = {
        "generated": BUILD_DATE, "meta": meta, "vintage": vintage,
        "measures": {k: lbl for _, (k, lbl, _h, _a) in MEASURES.items()},
        "agg_rule": {k: a for _, (k, _lbl, _h, a) in MEASURES.items()},
        "tiers": TIER_ORDER, "tier_series": tier_series, "yoy": yoy,
        "peace_dividend": peace, "cofer": cof, "arms": arms_payload,
        "forecast": forecast, "endpoints": endpoints, "kpis": kpis,
        "hyp": hyp, "register": reg,
    }
    DOCS.mkdir(exist_ok=True)
    (DOCS / "payload.json").write_text(json.dumps(payload, separators=(",", ":")))
    kb = (DOCS / "payload.json").stat().st_size / 1024
    print(f"payload.json: {kb:,.0f} KB; register {len(reg)} artifacts, "
          f"{meta['n_rows']:,} rows and keys")


if __name__ == "__main__":
    main()
