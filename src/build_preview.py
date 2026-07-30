"""
build_preview.py
Stage 5 of the pipeline: assemble the HTML preview.

WHY A BUILDER INSTEAD OF A HAND-WRITTEN PAGE
--------------------------------------------
Every quantitative claim on the page is injected here from the pipeline
artifacts (calibration.json, simulation_summary.json, the processed
tables). The text physically cannot disagree with the model that
produced it, and re-running the pipeline after a data update re-writes
the page. The four plates are embedded as base64 so index.html is a
single self-contained file: it renders anywhere, including GitHub
Pages, with no asset paths to break.

Run:  python src/build_preview.py   (writes the static typeset preview)
"""

import base64
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
OUT = ROOT / "outputs"
FIG = OUT / "figures"


def b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def main() -> None:
    calib = json.loads((OUT / "calibration.json").read_text())
    summ = json.loads((OUT / "simulation_summary.json").read_text())
    shares = pd.read_csv(PROC / "cofer_shares_wide.csv").iloc[-1]
    conc = pd.read_csv(PROC / "supplier_concentration.csv")

    # Supplier concentration: use the last COMPLETE five-year window.
    last_complete = conc.loc[conc["window"] <= 2020, "window"].max()
    win = conc[conc["window"] == last_complete]
    lead = win.sort_values("share", ascending=False).iloc[0]

    u, c = summ["usd"], summ["cny"]
    reg = calib["usd_regression"]
    cases = calib["cases"]

    fill = {
        "Q_LATEST": calib["latest_state"]["quarter"],
        "USD": f"{shares['USD']:.1f}",
        "EUR": f"{shares['EUR']:.1f}",
        "JPY": f"{shares['JPY']:.1f}",
        "GBP": f"{shares['GBP']:.1f}",
        "CNY": f"{shares['CNY']:.1f}",
        "OTHER": f"{shares['OTHER']:.1f}",
        "RATIO": f"{calib['latest_state']['cn_us_ratio_2025']:.2f}",
        "BETA": f"{reg['params']['x_ratio']:+.2f}",
        "BETA_LO": f"{reg['conf_int_95']['x_ratio'][0]:+.2f}",
        "BETA_HI": f"{reg['conf_int_95']['x_ratio'][1]:+.2f}",
        "NOBS": str(reg["nobs"]),
        "CN_CAGR": f"{cases['accretion_decade']['china']:+.1f}",
        "US_CAGR": f"{cases['accretion_decade']['usa']:+.1f}",
        "PEACE_RATE": f"{cases['peace_dividend']['annual_rate_pct']:.1f}",
        "PEACE_TOTAL": f"{cases['peace_dividend']['total_real_change_pct']:.0f}",
        "US2025": f"{cases['us_2025_decline']['value']:.1f}",
        "OTHER_PRE": f"{cases['diversification_drift']['pre_2022']:.3f}",
        "OTHER_POST": f"{cases['diversification_drift']['post_2022']:.2f}",
        "ACC_MED": f"{u['accretion']['median']:.1f}",
        "RET_MED": f"{u['retrenchment']['median']:.1f}",
        "DEM_MED": f"{u['demonstration']['median']:.1f}",
        "ACC_P10": f"{u['accretion']['p10']:.0f}",
        "ACC_P90": f"{u['accretion']['p90']:.0f}",
        "ACC_PLT50": f"{u['accretion']['prob_below_50']:.2f}",
        "RET_PLT50": f"{u['retrenchment']['prob_below_50']:.2f}",
        "SEP": f"{u['pathway_separation_sd_units']:.2f}",
        "CNY_ACC_MED": f"{c['accretion']['median']:.1f}",
        "CNY_DEM_MED": f"{c['demonstration']['median']:.1f}",
        "HHI_WINDOW": f"{int(last_complete)} to {int(last_complete) + 4}",
        "HHI_2020": f"{lead['hhi']:.2f}",
        "TOPSUP_2020": str(lead["supplier"]),
        "TOPSHARE_2020": f"{100 * lead['share']:.0f}",
        "FIG1": b64(FIG / "plate1_reserves.png"),
        "FIG2": b64(FIG / "plate2_milex.png"),
        "FIG3": b64(FIG / "plate3_arms_trade.png"),
        "FIG4": b64(FIG / "plate4_forecast.png"),
    }

    html = (ROOT / "docs" / "index_template.html").read_text()
    for key, val in fill.items():
        html = html.replace("{{" + key + "}}", val)

    leftovers = [t for t in ("{{",) if t in html]
    if leftovers:
        raise ValueError("unfilled placeholders remain in index.html")

    (ROOT / "docs" / "static_preview.html").write_text(html)
    kb = len(html.encode()) / 1024
    print(f"docs/static_preview.html written ({kb:,.0f} KB, self-contained)")


if __name__ == "__main__":
    main()
