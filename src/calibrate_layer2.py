"""
calibrate_layer2.py
Stage 2b: the system-dynamics layer's parameters, estimated from history.

WHAT THIS LAYER IS
------------------
Layer 2 makes allied budgets endogenous. Each allied tier's real growth
is modelled as a response to what the two principals did the year
before:

    g_tier(t) = b0 + b_us * g_us(t-1) + b_cn * g_cn(t-1) + e(t)

estimated by OLS with Newey-West standard errors over 1951 to 2025 from
the tier panel. The coefficient pair is the whole argument of H2 in two
numbers: if the hegemon's motion moves allied budgets harder than the
challenger's motion, then |b_us| > |b_cn|, and retrenchment, which is a
large negative US impulse, is the stronger signal. The test is a delta
method comparison of |b_us| against |b_cn| with a one-sided p value.

Two further quantities are measured here because the simulation needs
them. First, the rest-of-world block (world total minus the six tiers)
gets its own drift and residual pool so world totals close in the
simulation. Second, the demonstration mobilization case: the measured
step-up in allied growth after February 2022, the one modern
observation of alliance-wide mobilization following a violent shock.
Its post-2022 minus pre-2022 growth differential per tier is what the
demonstration pathway replays after the event quarter, with the n = 1
caveat carried explicitly into the outputs.

An event-window table is also computed: allied growth during named US
retrenchment windows (post-Vietnam, the peace dividend, the sequester
era, 2025) against the China-accretion-only window of 2015 to 2021,
so the H2 regression can be read against plain historical episodes.

Run:  python src/calibrate_layer2.py
Writes: outputs/calibration_layer2.json, outputs/layer2_residual_pools.csv
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
OUT = ROOT / "outputs"

ALLIED_TIERS = ["Indo-Pacific allies", "NATO Europe", "Hedging middle powers"]
RETRENCH_WINDOWS = {"post_vietnam_1969_1975": (1969, 1975),
                    "peace_dividend_1989_1998": (1989, 1998),
                    "sequester_2011_2015": (2011, 2015),
                    "observed_2025": (2025, 2025)}
ACCRETION_WINDOW = (2015, 2021)


def tier_panel() -> pd.DataFrame:
    """The tier panel, from disk if stage 5a has run, else built in memory.

    The panel csv is written by build_dashboard_data.py for inspectability,
    but this layer must also run on a clean checkout before stage 5a, so
    the same builder is imported and called when the file is absent.
    """
    path = PROC / "milex_tier_panel.csv"
    if path.exists():
        return pd.read_csv(path)
    from build_dashboard_data import build_tiers
    return build_tiers()[1]


def growth_table() -> pd.DataFrame:
    t = tier_panel()
    t = t[t.measure == "milex_usd_const2024"]
    wide = t.pivot_table("value", "year", "tier").sort_index()
    m = pd.read_csv(PROC / "milex_panel.csv")
    world = m[m.iso3 == "WORLD"].set_index("year").milex_constusd_m
    wide["World"] = world
    wide["Rest of world"] = wide["World"] - wide[
        [c for c in wide.columns if c not in ("World", "Rest of world")]
    ].sum(axis=1, min_count=1)
    return np.log(wide).diff().dropna(how="all") * 100


def estimate_feedback(g: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    out, pools = {}, []
    X = pd.DataFrame({"us_lag": g["United States"].shift(1),
                      "cn_lag": g["China"].shift(1)})
    for tier in ALLIED_TIERS:
        df = pd.concat([g[tier].rename("y"), X], axis=1).dropna()
        model = sm.OLS(df.y, sm.add_constant(df[["us_lag", "cn_lag"]])).fit(
            cov_type="HAC", cov_kwds={"maxlags": 3})
        b, se = model.params, model.bse
        # H2 per tier: one-sided test of |b_us| > |b_cn| by delta method.
        diff = abs(b.us_lag) - abs(b.cn_lag)
        var = (se.us_lag ** 2 + se.cn_lag ** 2
               - 2 * model.cov_params().loc["us_lag", "cn_lag"]
               * np.sign(b.us_lag) * np.sign(b.cn_lag))
        z = diff / np.sqrt(max(var, 1e-12))
        from scipy.stats import norm
        p_one_sided = float(1 - norm.cdf(z))
        out[tier] = {
            "b0": round(float(b["const"]), 3),
            "b_us": round(float(b.us_lag), 3),
            "b_cn": round(float(b.cn_lag), 3),
            "se_us": round(float(se.us_lag), 3),
            "se_cn": round(float(se.cn_lag), 3),
            "ci95_us": [round(float(v), 3) for v in model.conf_int().loc["us_lag"]],
            "ci95_cn": [round(float(v), 3) for v in model.conf_int().loc["cn_lag"]],
            "abs_gap": round(float(diff), 3),
            "p_us_stronger_one_sided": round(p_one_sided, 4),
            "nobs": int(model.nobs), "r2": round(float(model.rsquared), 3),
        }
        pools.append(pd.DataFrame({"block": tier, "resid": model.resid}))
    return out, pd.concat(pools)


def main() -> None:
    g = growth_table()
    feedback, pools = estimate_feedback(g)

    # Principals and rest of world: drift and residuals for the engine.
    blocks = {}
    for name in ["United States", "China", "Rest of world"]:
        s = g[name].dropna()
        s10 = s[s.index >= s.index.max() - 9]
        blocks[name] = {"mean_full": round(float(s.mean()), 3),
                        "mean_2016_2025": round(float(s10.mean()), 3),
                        "sd_full": round(float(s.std()), 3), "n": int(len(s))}
        pools = pd.concat([pools, pd.DataFrame(
            {"block": name, "resid": s - s.mean()})])

    # Demonstration mobilization: the 2022 alliance-wide step-up, n = 1.
    mob = {}
    for tier in ALLIED_TIERS:
        pre = g.loc[2015:2021, tier].mean()
        post = g.loc[2022:2025, tier].mean()
        mob[tier] = {"pre_2022_mean": round(float(pre), 2),
                     "post_2022_mean": round(float(post), 2),
                     "delta_pp": round(float(post - pre), 2)}

    # Event windows: allied growth under named US retrenchment episodes.
    windows = {}
    for name, (a, b) in RETRENCH_WINDOWS.items():
        seg = g.loc[a:b]
        windows[name] = {
            "us_mean": round(float(seg["United States"].mean()), 2),
            **{t: round(float(seg[t].mean()), 2) for t in ALLIED_TIERS}}
    a, b = ACCRETION_WINDOW
    seg = g.loc[a:b]
    windows["accretion_only_2015_2021"] = {
        "us_mean": round(float(seg["United States"].mean()), 2),
        "cn_mean": round(float(seg["China"].mean()), 2),
        **{t: round(float(seg[t].mean()), 2) for t in ALLIED_TIERS}}

    result = {
        "description": "Layer 2 parameters: allied feedback on lagged US and "
                       "China real growth, HAC(3), annual 1951 to 2025",
        "feedback": feedback, "principal_blocks": blocks,
        "demonstration_mobilization_2022": mob,
        "event_windows": windows,
        "h2_historical": {
            t: {"verdict": "us_stronger" if feedback[t]["abs_gap"] > 0 else "cn_stronger",
                "abs_gap": feedback[t]["abs_gap"],
                "p_one_sided": feedback[t]["p_us_stronger_one_sided"]}
            for t in ALLIED_TIERS},
    }
    (OUT / "calibration_layer2.json").write_text(json.dumps(result, indent=1))
    pools.to_csv(OUT / "layer2_residual_pools.csv", index=False)
    for t in ALLIED_TIERS:
        f = feedback[t]
        print(f"{t}: b_us {f['b_us']} (se {f['se_us']}), b_cn {f['b_cn']} "
              f"(se {f['se_cn']}), |gap| {f['abs_gap']}, p {f['p_us_stronger_one_sided']}")


if __name__ == "__main__":
    main()
