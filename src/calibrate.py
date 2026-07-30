"""
calibrate.py
Stage 2 of the pipeline: historical parameter estimation.

DESIGN PRINCIPLE
----------------
Nothing in the simulation is assumed. Every parameter the Monte Carlo
engine consumes is estimated here from the real series built in stage 1
and written to outputs/calibration.json with its uncertainty. The
scenario pathways are imposed exogenously later; the response of the
system to those pathways is measured, not invented.

WHAT IS ESTIMATED
-----------------
1. Reserve channel response (the channel implemented in this preview).
   Quarterly change in the US dollar share of allocated reserves is
   regressed on the year over year change in the log China/US military
   expenditure ratio (annual SIPRI data linearly interpolated to
   quarters), with indicator terms for 2022-Q1 and 2022-Q2, the
   quarters in which the freezing of Russian central bank assets
   repriced reserve demand. Standard errors are Newey-West (HAC, four
   lags) because quarterly share changes are autocorrelated. The same
   specification is run for the renminbi share from 2017-Q1.

   The expectation from theory (hypothesis H3) is a coefficient near
   zero: reserve composition should be the slowest channel, so the
   confidence interval matters more than the point estimate. Estimating
   a null precisely is the point, not a failure.

2. Empirical innovation pools. Regression residuals are saved for
   bootstrap resampling in the simulation, so simulated quarters
   inherit the true fat tails of reserve share changes instead of a
   convenient Gaussian.

3. Calibration cases, each a named historical episode:
   * peace_dividend    US real expenditure contraction 1988-1998, the
                       reverse experiment for the retrenchment pathway.
   * sanctions_2022    observed share changes in 2022-Q1/Q2, the only
                       modern observation of a demonstration-class
                       reserve shock. Reused as the shock draw.
   * accretion_decade  real growth rates 2015-2025 for China and the
                       USA, anchoring the accretion pathway.
   * us_2025_decline   the observed 2025 fall in US real spending,
                       anchoring the retrenchment pathway.

Run:  python src/calibrate.py   (after the three stage 1 parsers)
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
OUT = ROOT / "outputs"


def quarterly_ratio_regressor(feats: pd.DataFrame,
                              quarters: pd.Series) -> pd.Series:
    """Interpolate the annual CN/US expenditure ratio to quarter ends and
    return the year over year change in its log.

    Interpolation is linear in log space between year-end anchors. The
    resulting regressor is smooth by construction, which biases against
    finding spurious quarterly correlation, a conservative choice."""
    annual = feats.set_index("year")["cn_us_ratio"]
    anchors = pd.Series(
        np.log(annual.values),
        index=pd.PeriodIndex([f"{y}Q4" for y in annual.index], freq="Q")
        .to_timestamp(how="end")
        .normalize(),
    )
    grid = pd.to_datetime(quarters)
    filled = (
        anchors.reindex(anchors.index.union(grid))
        .interpolate(method="time")
        .reindex(grid)
    )
    return filled.diff(4)  # year over year, at quarterly frequency


def hac_ols(y: pd.Series, X: pd.DataFrame) -> dict:
    """OLS with Newey-West standard errors; returns a JSON-safe summary."""
    model = sm.OLS(y, sm.add_constant(X), missing="drop")
    fit = model.fit(cov_type="HAC", cov_kwds={"maxlags": 4})
    return {
        "params": {k: float(v) for k, v in fit.params.items()},
        "bse": {k: float(v) for k, v in fit.bse.items()},
        "conf_int_95": {
            k: [float(a), float(b)]
            for k, (a, b) in fit.conf_int().iterrows()
        },
        "r2": float(fit.rsquared),
        "nobs": int(fit.nobs),
        "resid": [float(r) for r in fit.resid],
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    shares = pd.read_csv(PROC / "cofer_shares_wide.csv", parse_dates=["date"])
    feats = pd.read_csv(PROC / "milex_features.csv")
    panel = pd.read_csv(PROC / "milex_panel.csv")
    wide = panel.pivot_table(index="year", columns="iso3",
                             values="milex_constusd_m")

    # ---- 1. Reserve channel regressions --------------------------------
    shares = shares.sort_values("date").reset_index(drop=True)
    shares["d_usd"] = shares["USD"].diff()
    shares["d_cny"] = shares["CNY"].diff()
    shares["d_other"] = shares["OTHER"].diff()
    shares["x_ratio"] = quarterly_ratio_regressor(feats, shares["date"]).values
    shares["dum_2022"] = shares["quarter"].isin(["2022-Q1", "2022-Q2"]) * 1.0

    usd_reg = hac_ols(shares["d_usd"],
                      shares[["x_ratio", "dum_2022"]])
    cny = shares[shares["quarter"] >= "2017-Q1"]
    cny_reg = hac_ols(cny["d_cny"], cny[["x_ratio", "dum_2022"]])

    # ---- 2. Innovation pools -------------------------------------------
    pools = pd.DataFrame({
        "usd_resid": pd.Series(usd_reg.pop("resid")),
        "cny_resid": pd.Series(cny_reg.pop("resid")),
    })
    pools.to_csv(OUT / "innovation_pools.csv", index=False)

    # ---- 3. Named calibration cases ------------------------------------
    us = wide["USA"]
    cn = wide["CHN"]
    cases = {
        "peace_dividend": {
            "description": "US real military expenditure, 1988 to 1998",
            "total_real_change_pct": float(100 * (us[1998] / us[1988] - 1)),
            "annual_rate_pct": float(100 * ((us[1998] / us[1988]) ** 0.1 - 1)),
        },
        "sanctions_2022": {
            "description": ("Observed quarterly share changes around the "
                            "2022 freezing of Russian reserves, pp"),
            "d_usd": shares.loc[shares["dum_2022"] == 1, "d_usd"]
                     .round(3).tolist(),
            "d_cny": shares.loc[shares["dum_2022"] == 1, "d_cny"]
                     .round(3).tolist(),
            "d_other": shares.loc[shares["dum_2022"] == 1, "d_other"]
                       .round(3).tolist(),
        },
        "accretion_decade": {
            "description": "Real growth anchors, 2015 to 2025, pct per year",
            "china": float(100 * ((cn[2025] / cn[2015]) ** 0.1 - 1)),
            "usa": float(100 * ((us[2025] / us[2015]) ** 0.1 - 1)),
        },
        "us_2025_decline": {
            "description": "Observed 2025 change in US real expenditure, pct",
            "value": float(100 * (us[2025] / us[2024] - 1)),
        },
        "drift_regimes": {
            "description": ("Mean quarterly share change, pp, before and "
                            "after 2022-Q1; the difference is the regime "
                            "shift replayed after a demonstration event"),
            "usd_pre": float(shares.loc[shares["quarter"] < "2022-Q1",
                                        "d_usd"].mean()),
            "usd_post": float(shares.loc[shares["quarter"] >= "2022-Q1",
                                         "d_usd"].mean()),
            "cny_pre": float(shares.loc[(shares["quarter"] >= "2017-Q1")
                                        & (shares["quarter"] < "2022-Q1"),
                                        "d_cny"].mean()),
            "cny_post": float(shares.loc[shares["quarter"] >= "2022-Q1",
                                         "d_cny"].mean()),
        },
        "diversification_drift": {
            "description": ("Mean quarterly change in the 'other currencies' "
                            "share, pp, before and after 2022-Q1"),
            "pre_2022": float(shares.loc[shares["quarter"] < "2022-Q1",
                                         "d_other"].mean()),
            "post_2022": float(shares.loc[shares["quarter"] >= "2022-Q1",
                                          "d_other"].mean()),
        },
    }

    calib = {
        "meta": {
            "built": "2026-07-24",
            "cofer_span": [shares["quarter"].iloc[0],
                           shares["quarter"].iloc[-1]],
            "milex_span": [int(wide.index.min()), int(wide.index.max())],
            "note": ("All parameters estimated from IMF COFER and SIPRI "
                     "data prepared by the stage 1 parsers."),
        },
        "latest_state": {
            "quarter": shares["quarter"].iloc[-1],
            "usd_share": float(shares["USD"].iloc[-1]),
            "cny_share": float(shares["CNY"].iloc[-1]),
            "eur_share": float(shares["EUR"].iloc[-1]),
            "other_share": float(shares["OTHER"].iloc[-1]),
            "cn_us_ratio_2025": float(feats.set_index("year")
                                      .loc[2025, "cn_us_ratio"]),
        },
        "usd_regression": usd_reg,
        "cny_regression": cny_reg,
        "cases": cases,
    }
    (OUT / "calibration.json").write_text(json.dumps(calib, indent=2))

    b = usd_reg["params"]["x_ratio"]
    lo, hi = usd_reg["conf_int_95"]["x_ratio"]
    print(f"USD share response to YoY d(log CN/US milex ratio):")
    print(f"  beta = {b:+.2f} pp  [95 pct CI {lo:+.2f}, {hi:+.2f}]  "
          f"n = {usd_reg['nobs']}, R2 = {usd_reg['r2']:.3f}")
    print(f"2022 sanctions quarters, observed dUSD: "
          f"{cases['sanctions_2022']['d_usd']}")
    print(f"Peace dividend 1988-98: "
          f"{cases['peace_dividend']['total_real_change_pct']:.1f} pct total, "
          f"{cases['peace_dividend']['annual_rate_pct']:.1f} pct per year")
    print(f"Accretion anchors 2015-25: China "
          f"{cases['accretion_decade']['china']:+.1f}, USA "
          f"{cases['accretion_decade']['usa']:+.1f} pct per year")
    print(f"US 2025 real change: {cases['us_2025_decline']['value']:+.1f} pct")
    print("calibration.json and innovation_pools.csv written")


if __name__ == "__main__":
    main()
