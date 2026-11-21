"""
calibrate.py
Stage 2a. Reserve-channel parameters.

Estimates
---------
1. US dollar share. The quarterly change in the dollar share of reserves
   (percentage points) is regressed on the year-on-year change in the
   log China/US military expenditure ratio and an indicator for 2022-Q1
   and 2022-Q2, the quarters of the freeze of Russian central bank
   assets. The annual ratio is interpolated linearly in logs between
   year-end values. Standard errors are Newey-West with four lags.

2. Renminbi share. The same specification from 2017-Q1, with the
   dependent variable in log-odds, log(s / (100 - s)). The renminbi
   share is close to zero, and a model in percentage points can produce
   negative simulated shares.

3. Residuals of both regressions, kept for resampling in stage 3a.

4. Reference episodes:
   peace_dividend     US real expenditure, 1988 to 1998
   sanctions_2022     observed share changes in 2022-Q1 and 2022-Q2
   accretion_decade   compound real growth of China and the United
                      States over the last ten years of data
   us_last_year       latest observed annual change in US real
                      expenditure
   drift_regimes      mean quarterly change before and from 2022-Q1

The expenditure regressor explains almost none of the variance in
reserve share changes. The coefficient is reported with its interval;
the interval is wide and includes zero.

Run: python src/calibrate.py
Writes: outputs/calibration.json, outputs/innovation_pools.csv
"""

import json

import numpy as np
import pandas as pd
import statsmodels.api as sm

from config import BUILD_DATE, HAC_LAGS_QUARTERLY, OUT, PROC

EVENT_QUARTERS = ["2022-Q1", "2022-Q2"]
REGIME_START = "2022-Q1"
CNY_START = "2017-Q1"


def logit(share_pct: pd.Series) -> pd.Series:
    return np.log(share_pct / (100 - share_pct))


def quarterly_ratio_regressor(feats: pd.DataFrame,
                              quarters: pd.Series) -> pd.Series:
    """Year-on-year change in log(China/US expenditure) at quarter ends."""
    annual = feats.set_index("year")["cn_us_ratio"].dropna()
    anchors = pd.Series(
        np.log(annual.values),
        index=pd.PeriodIndex([f"{y}Q4" for y in annual.index], freq="Q")
        .to_timestamp(how="end").normalize())
    grid = pd.to_datetime(quarters)
    filled = (anchors.reindex(anchors.index.union(grid))
              .interpolate(method="time").reindex(grid))
    # No extrapolation beyond the last annual observation.
    filled[filled.index > anchors.index.max()] = np.nan
    return filled.diff(4)


def hac_ols(y: pd.Series, X: pd.DataFrame) -> dict:
    fit = sm.OLS(y, sm.add_constant(X), missing="drop").fit(
        cov_type="HAC", cov_kwds={"maxlags": HAC_LAGS_QUARTERLY})
    names = list(fit.params.index)
    return {
        "params": {k: float(v) for k, v in fit.params.items()},
        "bse": {k: float(v) for k, v in fit.bse.items()},
        "conf_int_95": {k: [float(a), float(b)]
                        for k, (a, b) in fit.conf_int().iterrows()},
        "cov_names": names,
        "cov": [[float(v) for v in row] for row in fit.cov_params().values],
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

    shares = shares.sort_values("date").reset_index(drop=True)
    shares["d_usd"] = shares["USD"].diff()
    shares["d_cny"] = shares["CNY"].diff()
    shares["d_cny_logit"] = logit(shares["CNY"]).diff()
    shares["d_other"] = shares["OTHER"].diff()
    shares["x_ratio"] = quarterly_ratio_regressor(feats, shares["date"]).values
    shares["dum_2022"] = shares["quarter"].isin(EVENT_QUARTERS) * 1.0
    pre = shares["quarter"] < REGIME_START
    post = ~pre
    cny_span = shares["quarter"] >= CNY_START
    event = shares["dum_2022"] == 1

    usd_reg = hac_ols(shares["d_usd"], shares[["x_ratio", "dum_2022"]])
    cny = shares[cny_span]
    cny_reg = hac_ols(cny["d_cny_logit"], cny[["x_ratio", "dum_2022"]])
    cny_reg["dependent"] = "quarterly change in log-odds of the CNY share"
    usd_reg["dependent"] = "quarterly change in the USD share, pp"

    pools = pd.DataFrame({
        "usd_resid": pd.Series(usd_reg.pop("resid")),
        "cny_resid_logit": pd.Series(cny_reg.pop("resid")),
    })
    pools.to_csv(OUT / "innovation_pools.csv", index=False)

    us, cn = wide["USA"], wide["CHN"]
    y1 = int(wide["USA"].dropna().index.max())
    y0 = y1 - 10
    cases = {
        "peace_dividend": {
            "description": "US real military expenditure, 1988 to 1998",
            "total_real_change_pct": float(100 * (us[1998] / us[1988] - 1)),
            "annual_rate_pct": float(100 * ((us[1998] / us[1988]) ** 0.1 - 1)),
        },
        "sanctions_2022": {
            "description": "Observed quarterly share changes in 2022-Q1 and "
                           "2022-Q2 (pp; CNY also in log-odds)",
            "d_usd": shares.loc[event, "d_usd"].round(4).tolist(),
            "d_cny": shares.loc[event, "d_cny"].round(4).tolist(),
            "d_cny_logit": shares.loc[event, "d_cny_logit"].round(5).tolist(),
            "d_other": shares.loc[event, "d_other"].round(4).tolist(),
        },
        "accretion_decade": {
            "description": f"Compound real growth, {y0} to {y1}, "
                           "percent per year",
            "start_year": y0, "end_year": y1,
            "china": float(100 * ((cn[y1] / cn[y0]) ** 0.1 - 1)),
            "usa": float(100 * ((us[y1] / us[y0]) ** 0.1 - 1)),
        },
        "us_last_year": {
            "description": f"Change in US real expenditure, {y1}, percent",
            "year": y1,
            "value": float(100 * (us[y1] / us[y1 - 1] - 1)),
        },
        "drift_regimes": {
            "description": "Mean quarterly share change before and from "
                           f"{REGIME_START} (pp; CNY also in log-odds)",
            "usd_pre": float(shares.loc[pre, "d_usd"].mean()),
            "usd_post": float(shares.loc[post, "d_usd"].mean()),
            "cny_pre": float(shares.loc[cny_span & pre, "d_cny"].mean()),
            "cny_post": float(shares.loc[post, "d_cny"].mean()),
            "cny_pre_logit":
                float(shares.loc[cny_span & pre, "d_cny_logit"].mean()),
            "cny_post_logit": float(shares.loc[post, "d_cny_logit"].mean()),
        },
        "diversification_drift": {
            "description": "Mean quarterly change in the share of other "
                           f"currencies, pp, before and from {REGIME_START}",
            "pre_2022": float(shares.loc[pre, "d_other"].mean()),
            "post_2022": float(shares.loc[post, "d_other"].mean()),
        },
    }

    calib = {
        "meta": {
            "built": BUILD_DATE,
            "cofer_span": [shares["quarter"].iloc[0],
                           shares["quarter"].iloc[-1]],
            "milex_span": [int(wide.index.min()), int(wide.index.max())],
            "hac_lags": HAC_LAGS_QUARTERLY,
        },
        "latest_state": {
            "quarter": shares["quarter"].iloc[-1],
            "usd_share": float(shares["USD"].iloc[-1]),
            "cny_share": float(shares["CNY"].iloc[-1]),
            "eur_share": float(shares["EUR"].iloc[-1]),
            "other_share": float(shares["OTHER"].iloc[-1]),
            "cn_us_ratio": float(feats.set_index("year")
                                 .loc[y1, "cn_us_ratio"]),
            "cn_us_ratio_year": y1,
        },
        "usd_regression": usd_reg,
        "cny_regression": cny_reg,
        "cases": cases,
    }
    (OUT / "calibration.json").write_text(json.dumps(calib, indent=2))

    b = usd_reg["params"]["x_ratio"]
    lo, hi = usd_reg["conf_int_95"]["x_ratio"]
    print(f"USD share on d log(CN/US): {b:+.2f} pp "
          f"[95% CI {lo:+.2f}, {hi:+.2f}], n = {usd_reg['nobs']}, "
          f"R2 = {usd_reg['r2']:.3f}")
    bc = cny_reg["params"]["x_ratio"]
    lc, hc = cny_reg["conf_int_95"]["x_ratio"]
    print(f"CNY log-odds on d log(CN/US): {bc:+.2f} "
          f"[95% CI {lc:+.2f}, {hc:+.2f}], n = {cny_reg['nobs']}")
    print(f"peace dividend 1988-1998: "
          f"{cases['peace_dividend']['total_real_change_pct']:.1f}% total, "
          f"{cases['peace_dividend']['annual_rate_pct']:.2f}% per year")
    print(f"growth {y0}-{y1}: China "
          f"{cases['accretion_decade']['china']:+.2f}%, United States "
          f"{cases['accretion_decade']['usa']:+.2f}% per year; "
          f"US {y1}: {cases['us_last_year']['value']:+.1f}%")


if __name__ == "__main__":
    main()
