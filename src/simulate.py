"""
simulate.py
Stage 3 of the pipeline: conditional forecasting with Monte Carlo
uncertainty propagation, reserve currency channel.

WHAT THIS IS, AND WHAT IT IS NOT
--------------------------------
This is not prediction. There is no training data for a Chinese
attainment of military primacy; n equals one and the one has not
happened. The engine below therefore does conditional forecasting:
response parameters are estimated from history (stage 2), a pathway is
imposed exogenously, and uncertainty is propagated honestly through
10,000 draws. Outputs are distributions, never point estimates.

THE THREE PATHWAYS (the scenario axis of the whole project)
-----------------------------------------------------------
P1 ACCRETION      China's real military spending keeps its measured
                  2015-2025 rate; US spending keeps its own measured
                  decade rate. The ratio closes gradually.
P2 RETRENCHMENT   China as in P1; US contracts at the measured
                  1988-1998 peace dividend rate, the only clean decade
                  of sustained US real contraction on record.
P3 DEMONSTRATION  P1, plus a demonstration-class shock at a random
                  quarter in 2028-2031. The shock is not invented: the
                  event quarters replay the observed 2022-Q1/Q2 share
                  changes (the freezing of Russian reserves being the
                  only modern observation of this class), and the
                  quarters after the event inherit the measured
                  post-2022 shift in drift for each currency.

THREE SOURCES OF UNCERTAINTY, PROPAGATED JOINTLY
------------------------------------------------
1. Parameter uncertainty. Each draw resamples the regression
   coefficients from their estimated (HAC) sampling distribution.
2. Innovation uncertainty. Quarterly disturbances are bootstrapped from
   the stage 2 residual pools, preserving the true fat tails of
   reserve share changes.
3. Scenario timing uncertainty. In P3 the shock quarter is uniform over
   2028-2031, so the fan integrates over when as well as whether.

HYPOTHESIS UNDER TEST HERE
--------------------------
H3 says reserve composition is the slowest and least pathway sensitive
channel: the three fans should overlap heavily, and the standardized
separation between pathway medians should be small relative to the
spread of any single pathway. The engine computes that separation
directly, so the preview reports a measured result, not an assertion.

Run:  python src/simulate.py   (after calibrate.py)
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"

N_DRAWS = 10_000
SEED = 20260724
HORIZON_END = "2035Q4"
PCTS = [5, 10, 25, 50, 75, 90, 95]


def pathway_regressor(calib: dict, quarters: pd.PeriodIndex) -> dict:
    """Year over year change in log(CN/US milex ratio), per pathway.

    Constant within a pathway because the pathway growth rates are
    constant; expressed exactly as the calibration regressor was built,
    so the estimated coefficient applies without unit gymnastics."""
    g = calib["cases"]["accretion_decade"]
    cn = 1 + g["china"] / 100
    us_accr = 1 + g["usa"] / 100
    us_retr = 1 + calib["cases"]["peace_dividend"]["annual_rate_pct"] / 100
    x = {
        "accretion": float(np.log(cn / us_accr)),
        "retrenchment": float(np.log(cn / us_retr)),
    }
    x["demonstration"] = x["accretion"]
    return {k: np.full(len(quarters), v) for k, v in x.items()}


def simulate_currency(ccy: str, calib: dict, pools: pd.DataFrame,
                      quarters: pd.PeriodIndex, rng: np.random.Generator
                      ) -> tuple[pd.DataFrame, dict]:
    reg = calib[f"{ccy}_regression"]
    start = calib["latest_state"]["usd_share" if ccy == "usd"
                                  else "cny_share"]
    resid = pools[f"{ccy}_resid"].dropna().values
    H = len(quarters)

    # Demonstration event material, straight from the 2022 observation:
    # the event quarters replay the observed jumps, and quarters after
    # the event inherit the measured post-2022 minus pre-2022 drift.
    ev = calib["cases"]["sanctions_2022"][f"d_{ccy}"]
    regimes = calib["cases"]["drift_regimes"]
    post_shift = regimes[f"{ccy}_post"] - regimes[f"{ccy}_pre"]

    x = pathway_regressor(calib, quarters)
    event_window = [i for i, q in enumerate(quarters)
                    if "2028" <= str(q)[:4] <= "2031"]

    fans, endpoints = [], {}
    for path in ["accretion", "retrenchment", "demonstration"]:
        # 1. parameter uncertainty
        b0 = rng.normal(reg["params"]["const"], reg["bse"]["const"], N_DRAWS)
        b1 = rng.normal(reg["params"]["x_ratio"], reg["bse"]["x_ratio"],
                        N_DRAWS)
        # 2. innovation uncertainty (bootstrap)
        eps = rng.choice(resid, size=(N_DRAWS, H), replace=True)

        drift = b0[:, None] + b1[:, None] * x[path][None, :]

        if path == "demonstration":
            # 3. timing uncertainty + measured event replay
            t0 = rng.choice(event_window, N_DRAWS)
            for k, jump in enumerate(ev):
                idx = np.clip(t0 + k, 0, H - 1)
                extra = np.zeros((N_DRAWS, H))
                extra[np.arange(N_DRAWS), idx] = jump
                drift = drift + extra
            after = (np.arange(H)[None, :] > (t0[:, None] + len(ev) - 1))
            drift = drift + post_shift * after

        paths_arr = start + np.cumsum(drift + eps, axis=1)
        paths_arr = np.clip(paths_arr, 0.0, 100.0)

        q = np.percentile(paths_arr, PCTS, axis=0)
        fan = pd.DataFrame(q.T, columns=[f"p{p:02d}" for p in PCTS])
        fan.insert(0, "quarter", quarters.astype(str))
        fan.insert(0, "pathway", path)
        fan.insert(0, "currency", ccy.upper())
        fans.append(fan)

        end = paths_arr[:, -1]
        endpoints[path] = {
            "median": float(np.median(end)),
            "p10": float(np.percentile(end, 10)),
            "p90": float(np.percentile(end, 90)),
            "prob_below_50": float((end < 50).mean()) if ccy == "usd"
            else None,
            "endpoint_sd": float(end.std()),
        }

    # H3 metric: pathway separation in units of within-pathway spread.
    med = [endpoints[p]["median"] for p in endpoints]
    sd = np.mean([endpoints[p]["endpoint_sd"] for p in endpoints])
    endpoints["pathway_separation_sd_units"] = float(
        (max(med) - min(med)) / sd
    )
    return pd.concat(fans, ignore_index=True), endpoints


def main() -> None:
    calib = json.loads((OUT / "calibration.json").read_text())
    pools = pd.read_csv(OUT / "innovation_pools.csv")
    rng = np.random.default_rng(SEED)

    last = calib["latest_state"]["quarter"].replace("-", "")
    quarters = pd.period_range(
        pd.Period(last, freq="Q") + 1, HORIZON_END, freq="Q"
    )

    all_fans, summary = [], {"draws": N_DRAWS, "seed": SEED,
                             "horizon": [str(quarters[0]), str(quarters[-1])]}
    for ccy in ["usd", "cny"]:
        fan, ends = simulate_currency(ccy, calib, pools, quarters, rng)
        all_fans.append(fan)
        summary[ccy] = ends

    pd.concat(all_fans, ignore_index=True).to_csv(
        OUT / "simulation_fan.csv", index=False
    )
    (OUT / "simulation_summary.json").write_text(json.dumps(summary, indent=2))

    u = summary["usd"]
    print(f"{N_DRAWS:,} draws per pathway per currency, seed {SEED}")
    print(f"USD share, median at {quarters[-1]}:")
    for p in ["accretion", "retrenchment", "demonstration"]:
        e = u[p]
        print(f"  {p:<14} {e['median']:5.1f}  "
              f"[p10 {e['p10']:.1f}, p90 {e['p90']:.1f}]  "
              f"P(<50 pct) = {e['prob_below_50']:.2f}")
    print(f"  pathway separation: "
          f"{u['pathway_separation_sd_units']:.2f} sd units  "
          f"(H3 expects a small number)")
    c = summary["cny"]
    print(f"CNY share, median at {quarters[-1]}: "
          f"accretion {c['accretion']['median']:.2f}, "
          f"demonstration {c['demonstration']['median']:.2f}")


if __name__ == "__main__":
    main()
