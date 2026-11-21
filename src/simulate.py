"""
simulate.py
Stage 3a. Conditional simulation of the reserve channel.

The simulation is conditional. Response parameters are estimated in
stage 2a; each pathway is imposed as an assumption; the output is the
distribution of the US dollar and renminbi reserve shares to 2035-Q4
given that pathway.

Pathways
--------
accretion       China and the United States grow at their compound real
                rates over the last ten years of data.
retrenchment    China as above; US real expenditure contracts at the
                1988 to 1998 rate.
demonstration   Accretion, plus one event at a quarter drawn uniformly
                from 2028 to 2031. In the two event quarters the share
                change equals the change observed in 2022-Q1 and
                2022-Q2. After the event, drift shifts by the difference
                between mean quarterly change from 2022-Q1 and before
                it. This rests on a single episode.

Uncertainty
-----------
1. Parameters: the intercept and expenditure coefficient are drawn
   jointly from a normal distribution with the estimated Newey-West
   covariance.
2. Innovations: quarterly residuals are resampled with replacement from
   the stage 2a residuals.
3. Timing: the event quarter is random within its window.

The dollar share is simulated in percentage points and the renminbi
share in log-odds, as estimated. Pathway separation is the range of
pathway medians at the horizon divided by the mean within-pathway
standard deviation.

Run: python src/simulate.py
Writes: outputs/simulation_fan.csv, outputs/simulation_summary.json
"""

import json

import numpy as np
import pandas as pd

from config import (DRAWS, EVENT_YEARS, HORIZON_YEAR, OUT, PATHWAYS, PCTS,
                    SEED)

SPEC = {
    # currency: (regression key, residual column, start key, scale)
    "usd": ("usd_regression", "usd_resid", "usd_share", "level"),
    "cny": ("cny_regression", "cny_resid_logit", "cny_share", "logit"),
}


def pathway_regressor(calib: dict) -> dict:
    """Year-on-year change in log(China/US expenditure) by pathway."""
    g = calib["cases"]["accretion_decade"]
    cn = 1 + g["china"] / 100
    us_acc = 1 + g["usa"] / 100
    us_ret = 1 + calib["cases"]["peace_dividend"]["annual_rate_pct"] / 100
    x = {"accretion": float(np.log(cn / us_acc)),
         "retrenchment": float(np.log(cn / us_ret))}
    x["demonstration"] = x["accretion"]
    return x


def draw_coefficients(reg: dict, rng: np.random.Generator) -> tuple:
    names = reg["cov_names"]
    idx = [names.index("const"), names.index("x_ratio")]
    mean = np.array([reg["params"]["const"], reg["params"]["x_ratio"]])
    cov = np.array(reg["cov"])[np.ix_(idx, idx)]
    b = rng.multivariate_normal(mean, cov, DRAWS)
    return b[:, 0], b[:, 1]


def simulate_currency(ccy: str, calib: dict, pools: pd.DataFrame,
                      quarters: pd.PeriodIndex, rng: np.random.Generator
                      ) -> tuple[pd.DataFrame, dict]:
    reg_key, resid_col, start_key, scale = SPEC[ccy]
    reg = calib[reg_key]
    start = calib["latest_state"][start_key]
    resid = pools[resid_col].dropna().values
    H = len(quarters)
    suffix = "_logit" if scale == "logit" else ""
    jumps = calib["cases"]["sanctions_2022"][f"d_{ccy}{suffix}"]
    regimes = calib["cases"]["drift_regimes"]
    shift = regimes[f"{ccy}_post{suffix}"] - regimes[f"{ccy}_pre{suffix}"]
    x = pathway_regressor(calib)
    window = [i for i, q in enumerate(quarters)
              if EVENT_YEARS[0] <= q.year <= EVENT_YEARS[1]]
    z0 = np.log(start / (100 - start)) if scale == "logit" else start

    fans, endpoints = [], {}
    for path in PATHWAYS:
        b0, b1 = draw_coefficients(reg, rng)
        eps = rng.choice(resid, size=(DRAWS, H), replace=True)
        step = np.repeat((b0 + b1 * x[path])[:, None], H, axis=1)

        if path == "demonstration":
            t0 = rng.choice(window, DRAWS)
            cols = np.arange(H)[None, :]
            for k, jump in enumerate(jumps):
                step = np.where(cols == (t0[:, None] + k), jump, step)
            step = step + shift * (cols > (t0[:, None] + len(jumps) - 1))

        z = z0 + np.cumsum(step + eps, axis=1)
        if scale == "logit":
            share = 100 / (1 + np.exp(-z))
        else:
            share = np.clip(z, 0.0, 100.0)

        q = np.percentile(share, PCTS, axis=0)
        fan = pd.DataFrame(q.T, columns=[f"p{p:02d}" for p in PCTS])
        fan.insert(0, "quarter", quarters.astype(str))
        fan.insert(0, "pathway", path)
        fan.insert(0, "currency", ccy.upper())
        fans.append(fan)

        end = share[:, -1]
        endpoints[path] = {
            "median": float(np.median(end)),
            "p10": float(np.percentile(end, 10)),
            "p90": float(np.percentile(end, 90)),
            "prob_below_50": float((end < 50).mean()) if ccy == "usd"
            else None,
            "endpoint_sd": float(end.std()),
        }

    med = [endpoints[p]["median"] for p in PATHWAYS]
    sd = np.mean([endpoints[p]["endpoint_sd"] for p in PATHWAYS])
    endpoints["median_range_pp"] = float(max(med) - min(med))
    endpoints["pathway_separation_sd_units"] = float(
        (max(med) - min(med)) / sd)
    return pd.concat(fans, ignore_index=True), endpoints


def main() -> None:
    calib = json.loads((OUT / "calibration.json").read_text())
    pools = pd.read_csv(OUT / "innovation_pools.csv")
    rng = np.random.default_rng(SEED)

    last = pd.Period(calib["latest_state"]["quarter"].replace("-", ""),
                     freq="Q")
    quarters = pd.period_range(last + 1, f"{HORIZON_YEAR}Q4", freq="Q")

    fans, summary = [], {"draws": DRAWS, "seed": SEED,
                         "last_observed": str(last),
                         "horizon": [str(quarters[0]), str(quarters[-1])]}
    for ccy in ["usd", "cny"]:
        fan, ends = simulate_currency(ccy, calib, pools, quarters, rng)
        fans.append(fan)
        summary[ccy] = ends

    pd.concat(fans, ignore_index=True).to_csv(
        OUT / "simulation_fan.csv", index=False)
    (OUT / "simulation_summary.json").write_text(json.dumps(summary, indent=2))

    for ccy in ["usd", "cny"]:
        s = summary[ccy]
        line = ", ".join(f"{p} {s[p]['median']:.2f} "
                         f"[{s[p]['p10']:.2f}, {s[p]['p90']:.2f}]"
                         for p in PATHWAYS)
        print(f"{ccy.upper()} share {quarters[-1]}, median [p10, p90]: {line}")
        print(f"  separation {s['pathway_separation_sd_units']:.2f} sd")


if __name__ == "__main__":
    main()
