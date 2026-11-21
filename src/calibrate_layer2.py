"""
calibrate_layer2.py
Stage 2b. Allied response parameters and the H2 test.

Tier feedback equations (simulation input)
------------------------------------------
For each allied tier, real expenditure growth is regressed on the
previous year's real growth of US and Chinese expenditure:

    g_tier(t) = b0 + b_us * g_us(t-1) + b_cn * g_cn(t-1) + e(t)

by OLS with Newey-West standard errors (three lags). The sample starts
in 1991 because SIPRI reports China from 1989. Growth is percent per
year on chain-linked tier totals. The full coefficient covariance is
stored so that stage 3b can draw the coefficients jointly. A
Breusch-Godfrey test and the Durbin-Watson statistic are reported
because the residuals of the aggregate equations are serially
correlated, most strongly for NATO Europe.

H2 test
-------
H2 states that allied expenditure responds more strongly to US
expenditure than to Chinese expenditure, |b_us| > |b_cn|. The
confirmatory test uses the country-year panel of all three allied tiers:

    g_i(t) = a_i + rho * g_i(t-1) + b_us * g_us(t-1) + b_cn * g_cn(t-1)
             + c * dy_i(t) + e_i(t)

with country fixed effects, the lagged dependent variable, and the
country's own real GDP growth. Observations are weighted by the
country's share of pooled allied expenditure in the previous year, so
the estimand is the response of aggregate allied expenditure. Standard
errors are Driscoll-Kraay (three lags), which allow for cross-sectional
dependence and serial correlation; this is required because the two
regressors of interest vary only over time. The statistic is
|b_us| - |b_cn| with a delta-method standard error and a one-sided p
value from the t distribution with T - 1 degrees of freedom, T being
the number of years.

The following are reported alongside the confirmatory test and do not
enter the verdict: the same test by tier; the unweighted pooled test;
the static tier-level test used in the first release; and a
specification that separates US reductions from US increases, with two
checks of its stability.

Other quantities for stage 3b
-----------------------------
* Mean and residual growth of the United States, China and the rest of
  the world. Residuals of all blocks are aligned by year on their
  common sample for joint resampling.
* The change in mean allied growth from 2015-2021 to 2022 onward, used
  as the post-event response in the demonstration pathway. One episode.
* Mean growth in named windows of US contraction, for description.

Run: python src/calibrate_layer2.py
Writes: outputs/calibration_layer2.json, outputs/layer2_residual_pools.csv
"""

import json
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats
from statsmodels.stats.diagnostic import acorr_breusch_godfrey

from config import ALLIED_TIERS, BLOCKS, HAC_LAGS_ANNUAL, OUT, PROC
from tiers import growth_table

US_CONTRACTION_WINDOWS = {"post_vietnam_1969_1975": (1969, 1975),
                          "peace_dividend_1989_1998": (1989, 1998),
                          "sequester_2011_2015": (2011, 2015)}
PRE_2022 = (2015, 2021)
ALPHA = 0.05


def abs_gap_test(b: pd.Series, V: pd.DataFrame, us: str, cn: str,
                 dof: int | None) -> dict:
    """One-sided test of |b[us]| > |b[cn]| by the delta method."""
    gap = abs(b[us]) - abs(b[cn])
    var = (V.loc[us, us] + V.loc[cn, cn]
           - 2 * V.loc[us, cn] * np.sign(b[us]) * np.sign(b[cn]))
    se = float(np.sqrt(max(var, 1e-12)))
    stat = gap / se
    p = (1 - stats.norm.cdf(stat)) if dof is None else (
        1 - stats.t.cdf(stat, dof))
    return {"abs_gap": round(float(gap), 3), "se": round(se, 3),
            "stat": round(float(stat), 2), "p_one_sided": round(float(p), 4)}


def tier_feedback(g: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    """Static tier equations for the simulation, with diagnostics."""
    X = pd.DataFrame({"us_lag": g["United States"].shift(1),
                      "cn_lag": g["China"].shift(1)})
    out, resid = {}, {}
    for tier in ALLIED_TIERS:
        df = pd.concat([g[tier].rename("y"), X], axis=1).dropna()
        ols = sm.OLS(df.y, sm.add_constant(df[["us_lag", "cn_lag"]])).fit()
        fit = ols.get_robustcov_results(cov_type="HAC",
                                        maxlags=HAC_LAGS_ANNUAL)
        names = list(ols.params.index)
        b = pd.Series(fit.params, index=names)
        se = pd.Series(fit.bse, index=names)
        V = pd.DataFrame(fit.cov_params(), index=names, columns=names)
        ci = pd.DataFrame(fit.conf_int(), index=names)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", FutureWarning)
            bg_p = float(acorr_breusch_godfrey(ols, nlags=2)[1])
        out[tier] = {
            "b0": round(float(b["const"]), 3),
            "b_us": round(float(b.us_lag), 3),
            "b_cn": round(float(b.cn_lag), 3),
            "se_us": round(float(se.us_lag), 3),
            "se_cn": round(float(se.cn_lag), 3),
            "ci95_us": [round(float(v), 3) for v in ci.loc["us_lag"]],
            "ci95_cn": [round(float(v), 3) for v in ci.loc["cn_lag"]],
            "cov_names": names,
            "cov": [[float(v) for v in row] for row in V.values],
            "nobs": int(ols.nobs),
            "sample": [int(df.index.min()), int(df.index.max())],
            "r2": round(float(ols.rsquared), 3),
            "breusch_godfrey_p": round(bg_p, 4),
            "durbin_watson": round(float(sm.stats.durbin_watson(ols.resid)), 2),
            "static_test": abs_gap_test(b, V, "us_lag", "cn_lag", None),
        }
        resid[tier] = ols.resid
    return out, pd.DataFrame(resid)


def panel_fit(df: pd.DataFrame, formula: str, weighted: bool):
    """Fixed-effects regression with Driscoll-Kraay standard errors."""
    df = df.sort_values(["year", "country"]).reset_index(drop=True)
    time = (df.year - df.year.min()).to_numpy()
    kw = {"cov_type": "nw-groupsum",
          "cov_kwds": {"time": time, "maxlags": HAC_LAGS_ANNUAL,
                       "use_correction": "hac"}}
    if weighted:
        w = df.w / df.groupby("year").w.transform("sum")
        return smf.wls(formula, df, weights=w).fit(**kw), df
    return smf.ols(formula, df).fit(**kw), df


def panel_result(df: pd.DataFrame, weighted: bool, asymmetric: bool = False,
                 extra: str = "") -> dict:
    us_terms = "us_neg + us_pos" if asymmetric else "us_lag"
    formula = f"g ~ {us_terms} + cn_lag + g_lag + gdp_g{extra} + C(country)"
    fit, used = panel_fit(df, formula, weighted)
    b, V = fit.params, fit.cov_params()
    T = used.year.nunique()
    us = "us_neg" if asymmetric else "us_lag"
    res = {"n_obs": int(fit.nobs), "n_countries": int(used.country.nunique()),
           "n_years": int(T),
           "sample": [int(used.year.min()), int(used.year.max())],
           "weighted": weighted,
           "b_us": round(float(b[us]), 3), "se_us": round(float(fit.bse[us]), 3),
           "b_cn": round(float(b.cn_lag), 3),
           "se_cn": round(float(fit.bse.cn_lag), 3),
           "rho": round(float(b.g_lag), 3),
           "b_gdp": round(float(b.gdp_g), 3),
           "p_us_two_sided": round(float(
               2 * (1 - stats.t.cdf(abs(b[us] / fit.bse[us]), T - 1))), 4),
           "p_cn_two_sided": round(float(
               2 * (1 - stats.t.cdf(abs(b.cn_lag / fit.bse.cn_lag), T - 1))), 4),
           **abs_gap_test(b, V, us, "cn_lag", T - 1)}
    if asymmetric:
        res["b_us_increase"] = round(float(b.us_pos), 3)
        res["se_us_increase"] = round(float(fit.bse.us_pos), 3)
    return res


def h2_tests(g: pd.DataFrame) -> dict:
    panel = pd.read_csv(PROC / "milex_country_panel.csv")
    panel["us_neg"] = panel.us_lag.clip(upper=0)
    panel["us_pos"] = panel.us_lag.clip(lower=0)
    tier_lag = (g[ALLIED_TIERS].shift(1).stack().rename("tier_lag")
                .rename_axis(["year", "tier"]).reset_index())
    panel = panel.merge(tier_lag, on=["year", "tier"], how="left")

    primary = panel_result(panel, weighted=True)
    gap, p = primary["abs_gap"], primary["p_one_sided"]
    if gap > 0 and p < ALPHA:
        verdict = "supported"
    elif gap > 0:
        verdict = "not supported at the 5 percent level"
    else:
        verdict = "not supported"

    return {
        "statistic": "|b_us| - |b_cn|, one-sided, delta method, "
                     "Driscoll-Kraay covariance, t(T - 1)",
        "alpha": ALPHA,
        "verdict": verdict,
        "primary": primary,
        "by_tier": {t: panel_result(panel[panel.tier == t], weighted=True)
                    for t in ALLIED_TIERS},
        "sensitivity": {
            "unweighted": panel_result(panel, weighted=False),
            "us_reductions_only": panel_result(panel, True, asymmetric=True),
            "us_reductions_only_from_1997": panel_result(
                panel[panel.year >= 1997], True, asymmetric=True),
            "us_reductions_only_tier_lag_control": panel_result(
                panel.dropna(subset=["tier_lag"]), True, asymmetric=True,
                extra=" + tier_lag"),
        },
    }


def main() -> None:
    g = growth_table()
    last = int(g.index.max())
    feedback, tier_resid = tier_feedback(g)

    # Residual growth of the non-allied blocks, then the common sample.
    resid = tier_resid.copy()
    for name in ["United States", "China", "Rest of world"]:
        resid[name] = g[name]
    resid = resid.dropna()
    sample = [int(resid.index.min()), int(resid.index.max())]
    blocks = {}
    for name in ["United States", "China", "Rest of world"]:
        s = g.loc[sample[0]:sample[1], name]
        blocks[name] = {"mean_sample": round(float(s.mean()), 3),
                        "mean_last10": round(float(s.loc[last - 9:].mean()), 3),
                        "sd_sample": round(float(s.std()), 3),
                        "last_year": last,
                        "last_year_growth": round(float(g.loc[last, name]), 3),
                        "n": int(len(s))}
    resid = resid - resid.mean()
    pools = (resid[BLOCKS].stack().rename("resid")
             .rename_axis(["year", "block"]).reset_index())
    pools.to_csv(OUT / "layer2_residual_pools.csv", index=False)

    mob = {}
    for tier in ALLIED_TIERS:
        pre = g.loc[PRE_2022[0]:PRE_2022[1], tier].mean()
        post = g.loc[2022:last, tier].mean()
        mob[tier] = {"pre_2022_mean": round(float(pre), 2),
                     "post_2022_mean": round(float(post), 2),
                     "delta_pp": round(float(post - pre), 2)}

    windows = {}
    spans = {**US_CONTRACTION_WINDOWS, f"observed_{last}": (last, last)}
    for name, (a, b) in spans.items():
        seg = g.loc[a:b]
        windows[name] = {
            "us_mean": round(float(seg["United States"].mean()), 2),
            **{t: round(float(seg[t].mean()), 2) for t in ALLIED_TIERS}}
    seg = g.loc[PRE_2022[0]:PRE_2022[1]]
    windows[f"accretion_only_{PRE_2022[0]}_{PRE_2022[1]}"] = {
        "us_mean": round(float(seg["United States"].mean()), 2),
        "cn_mean": round(float(seg["China"].mean()), 2),
        **{t: round(float(seg[t].mean()), 2) for t in ALLIED_TIERS}}

    h2 = h2_tests(g)
    result = {
        "description": "Allied response to lagged US and Chinese real "
                       "expenditure growth; percent per year, chain-linked "
                       "tier totals",
        "feedback": feedback,
        "principal_blocks": blocks,
        "residual_sample": sample,
        "demonstration_mobilization_2022": mob,
        "event_windows": windows,
        "h2": h2,
    }
    (OUT / "calibration_layer2.json").write_text(json.dumps(result, indent=1))

    for t in ALLIED_TIERS:
        f = feedback[t]
        print(f"{t}: b_us {f['b_us']} ({f['se_us']}), b_cn {f['b_cn']} "
              f"({f['se_cn']}), n {f['nobs']}, BG p {f['breusch_godfrey_p']}")
    pr = h2["primary"]
    print(f"H2 pooled panel: b_us {pr['b_us']} ({pr['se_us']}), "
          f"b_cn {pr['b_cn']} ({pr['se_cn']}), gap {pr['abs_gap']}, "
          f"p {pr['p_one_sided']}; n {pr['n_obs']}, "
          f"{pr['n_countries']} countries, {pr['n_years']} years -> "
          f"{h2['verdict']}")
    for k, v in {**h2["by_tier"], **h2["sensitivity"]}.items():
        print(f"  {k}: b_us {v['b_us']} ({v['se_us']}), b_cn {v['b_cn']} "
              f"({v['se_cn']}), gap {v['abs_gap']}, p {v['p_one_sided']}")


if __name__ == "__main__":
    main()
