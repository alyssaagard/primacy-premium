"""
simulate_layer2.py
Stage 3b. Conditional simulation of expenditure by block, and H1.

Blocks: United States, China, Indo-Pacific allies, NATO Europe, hedging
middle powers, and rest of world (which includes Russia). Annual, from
the year after the last observation to 2035.

Pathways
--------
accretion       US and Chinese real growth at their compound rates over
                the last ten years of data.
retrenchment    China as above; the United States at the 1988 to 1998
                rate of contraction.
demonstration   Accretion, plus one event at a year drawn uniformly from
                2028 to 2031. From the event year, each allied tier
                receives its measured change in mean growth after
                February 2022, declining linearly to zero over four
                years. One episode.

Allied tiers follow the stage 2b feedback equations. The first simulated
year uses the last observed growth of the United States and China as
lagged values. Rest of world grows at its mean rate over the last ten
years of data.

Uncertainty
-----------
1. Parameters: each tier's intercept and two slopes are drawn jointly
   from a normal distribution with the estimated covariance.
2. Innovations: residual growth is resampled by stationary bootstrap
   with a mean block length of five years. Runs of consecutive years are
   drawn from the common residual sample and applied to all six blocks
   together, which preserves correlation across blocks and short-run
   serial correlation.
3. Timing: the event year is random within its window.

H1 statistic
------------
For each outcome, pathway separation is the range of the three pathway
medians at the horizon divided by the mean within-pathway standard
deviation. Scored outcomes are the three allied tiers and the allied
share of world expenditure. The United States and China are reported
but not scored because their paths differ across pathways by
assumption. H1 is recorded as supported if the median scored separation
exceeds twice the separation of the US dollar reserve share from stage
3a. The statistic describes the simulated distributions. It is not a
significance test and has no p value.

Also written: a projection of world arms deliveries from the elasticity
of delivery growth to world expenditure growth, and the war risk
premium multiple attached to demonstration events.

Run: python src/simulate_layer2.py
Writes: outputs/layer2_fan.csv, outputs/layer2_summary.json
"""

import json

import numpy as np
import pandas as pd
import statsmodels.api as sm

from config import (ALLIED_TIERS, BLOCK_LENGTH, BLOCKS, DRAWS, EVENT_YEARS,
                    HAC_LAGS_ANNUAL, HORIZON_YEAR, OUT, PATHWAYS, PCTS, PROC,
                    SEED)
from tiers import level_table

DECAY_YEARS = 4
H1_RATIO = 2.0


def arms_elasticity(arms: pd.DataFrame, world: pd.Series) -> dict:
    """Elasticity of world delivery growth to world expenditure growth."""
    a = arms.set_index("year").tiv_m
    g = pd.concat([np.log(a).diff().rename("arms"),
                   np.log(world).diff().rename("milex")], axis=1).dropna()
    fit = sm.OLS(g.arms, sm.add_constant(g.milex)).fit(
        cov_type="HAC", cov_kwds={"maxlags": HAC_LAGS_ANNUAL})
    return {"beta": round(float(fit.params.milex), 3),
            "se": round(float(fit.bse.milex), 3),
            "const": round(float(fit.params.const), 4),
            "nobs": int(fit.nobs)}


def block_bootstrap(resid: np.ndarray, n_years: int,
                    rng: np.random.Generator) -> np.ndarray:
    """Stationary bootstrap (Politis and Romano 1994).

    Returns residuals with shape (DRAWS, n_years, n_blocks). Each year
    either continues the current run of consecutive sample years or,
    with probability 1 / BLOCK_LENGTH, starts a new run at a random
    year. Runs wrap from the last sample year to the first.
    """
    n = resid.shape[0]
    restart = rng.random((DRAWS, n_years)) < 1 / BLOCK_LENGTH
    restart[:, 0] = True
    start = rng.integers(0, n, (DRAWS, n_years))
    idx = np.empty((DRAWS, n_years), dtype=int)
    idx[:, 0] = start[:, 0]
    for j in range(1, n_years):
        idx[:, j] = np.where(restart[:, j], start[:, j],
                             (idx[:, j - 1] + 1) % n)
    return resid[idx]


def separation(values_by_path: dict) -> float:
    meds = [np.median(v) for v in values_by_path.values()]
    sds = [np.std(v) for v in values_by_path.values()]
    return float((max(meds) - min(meds)) / np.mean(sds))


def main() -> None:
    cal1 = json.loads((OUT / "calibration.json").read_text())
    cal2 = json.loads((OUT / "calibration_layer2.json").read_text())
    fb = cal2["feedback"]
    blocks = cal2["principal_blocks"]
    mob = cal2["demonstration_mobilization_2022"]
    acc = cal1["cases"]["accretion_decade"]
    pd_rate = cal1["cases"]["peace_dividend"]["annual_rate_pct"]

    levels = level_table()
    base_year = int(levels[BLOCKS].dropna().index.max())
    base = levels.loc[base_year, BLOCKS].to_dict()
    years = list(range(base_year + 1, HORIZON_YEAR + 1))
    n_y = len(years)

    pools = pd.read_csv(OUT / "layer2_residual_pools.csv")
    resid = (pools.pivot_table("resid", "year", "block")[BLOCKS]
             .sort_index().to_numpy())
    col = {b: i for i, b in enumerate(BLOCKS)}

    arms = pd.read_csv(PROC / "arms_transfers_global.csv")
    war_mult = float(pd.read_csv(PROC / "war_risk_events.csv").multiple.iloc[0])

    results = {}
    for pi, path in enumerate(PATHWAYS):
        # A fixed integer offset per pathway keeps runs reproducible.
        rng = np.random.default_rng(SEED + pi + 1)
        eps = block_bootstrap(resid, n_y, rng)
        us_rate = pd_rate if path == "retrenchment" else acc["usa"]
        us_g = us_rate + eps[:, :, col["United States"]]
        cn_g = acc["china"] + eps[:, :, col["China"]]
        row_g = (blocks["Rest of world"]["mean_last10"]
                 + eps[:, :, col["Rest of world"]])
        event_year = (rng.integers(EVENT_YEARS[0], EVENT_YEARS[1] + 1, DRAWS)
                      if path == "demonstration" else np.full(DRAWS, 9999))

        coef = {}
        for t in ALLIED_TIERS:
            names = fb[t]["cov_names"]
            mean = [fb[t]["b0"], fb[t]["b_us"], fb[t]["b_cn"]]
            order = [names.index(k) for k in ["const", "us_lag", "cn_lag"]]
            cov = np.array(fb[t]["cov"])[np.ix_(order, order)]
            coef[t] = rng.multivariate_normal(mean, cov, DRAWS)

        lvl = {b: np.full(DRAWS, base[b], dtype=float) for b in BLOCKS}
        us_prev = np.full(DRAWS, blocks["United States"]["last_year_growth"])
        cn_prev = np.full(DRAWS, blocks["China"]["last_year_growth"])
        fan_rows = []
        for j, year in enumerate(years):
            for t in ALLIED_TIERS:
                c = coef[t]
                g = (c[:, 0] + c[:, 1] * us_prev + c[:, 2] * cn_prev
                     + eps[:, j, col[t]])
                since = year - event_year
                bump = np.where((since >= 0) & (since < DECAY_YEARS),
                                mob[t]["delta_pp"] * (1 - since / DECAY_YEARS),
                                0.0)
                lvl[t] = lvl[t] * (1 + (g + bump) / 100)
            lvl["Rest of world"] *= 1 + row_g[:, j] / 100
            lvl["United States"] *= 1 + us_g[:, j] / 100
            lvl["China"] *= 1 + cn_g[:, j] / 100
            us_prev, cn_prev = us_g[:, j], cn_g[:, j]
            for name, arr in lvl.items():
                q = np.percentile(arr, PCTS)
                fan_rows.append({"pathway": path, "block": name, "year": year,
                                 **{f"p{p:02d}": round(float(v), 1)
                                    for p, v in zip(PCTS, q)}})
        world = sum(lvl.values())
        results[path] = {
            "lvl": {k: v.copy() for k, v in lvl.items()},
            "allied_share": 100 * (lvl["Indo-Pacific allies"]
                                   + lvl["NATO Europe"]) / world,
            "world": world, "fan": fan_rows}

    scored = {t: separation({p: results[p]["lvl"][t] for p in PATHWAYS})
              for t in ALLIED_TIERS}
    scored["Allied share of world"] = separation(
        {p: results[p]["allied_share"] for p in PATHWAYS})
    drivers = {t: separation({p: results[p]["lvl"][t] for p in PATHWAYS})
               for t in ["United States", "China"]}
    reserve_sep = json.loads((OUT / "simulation_summary.json").read_text())[
        "usd"]["pathway_separation_sd_units"]
    med = float(np.median(list(scored.values())))
    mn_name, mn = min(scored.items(), key=lambda kv: kv[1])
    mx_name, mx = max(scored.items(), key=lambda kv: kv[1])
    h1 = {
        "scored_outcome_separation_sd": {k: round(v, 2)
                                         for k, v in scored.items()},
        "driver_separation_sd_context": {k: round(v, 2)
                                         for k, v in drivers.items()},
        "reserve_separation_sd": round(float(reserve_sep), 2),
        "median_outcome_sd": round(med, 2),
        "median_over_reserve_ratio": round(med / reserve_sep, 1),
        "min_outcome": {"name": mn_name, "sd": round(mn, 2),
                        "over_reserve_ratio": round(mn / reserve_sep, 1)},
        "max_outcome": {"name": mx_name, "sd": round(mx, 2)},
        "criterion_ratio": H1_RATIO,
        "verdict": ("supported" if med > H1_RATIO * reserve_sep
                    else "not supported"),
        "definition": "Range of pathway medians divided by mean "
                      "within-pathway standard deviation, at the horizon. "
                      "Scored outcomes: three allied tiers and the allied "
                      "share of world expenditure. Criterion: median scored "
                      "separation greater than twice the US dollar reserve "
                      "share separation. Descriptive statistic of the "
                      "simulation; not a significance test.",
    }

    h2_sim = {}
    for t in ALLIED_TIERS:
        a = np.median(results["accretion"]["lvl"][t])
        r = np.median(results["retrenchment"]["lvl"][t])
        h2_sim[t] = {"retrench_minus_accretion_musd": round(float(r - a), 0),
                     "pct_of_accretion_median": round(100 * (r - a) / a, 1)}

    world_hist = levels["World"].dropna()
    el = arms_elasticity(arms, world_hist)
    base_arms = float(arms.tiv_m.iloc[-1])
    arms_end = {}
    for p in PATHWAYS:
        wg = (results[p]["world"] / world_hist.iloc[-1]) ** (1 / n_y) - 1
        proj = base_arms * np.exp(
            (el["const"] + el["beta"] * np.log(1 + wg)) * n_y)
        arms_end[p] = {"median_tiv_m": round(float(np.median(proj)), 0),
                       "p10": round(float(np.percentile(proj, 10)), 0),
                       "p90": round(float(np.percentile(proj, 90)), 0)}

    pd.DataFrame([r for p in PATHWAYS for r in results[p]["fan"]]).to_csv(
        OUT / "layer2_fan.csv", index=False)

    def dist(v):
        return {"median": round(float(np.median(v)), 2),
                "p10": round(float(np.percentile(v, 10)), 2),
                "p90": round(float(np.percentile(v, 90)), 2)}

    summary = {
        "draws": DRAWS, "seed": SEED, "base_year": base_year,
        "horizon": [years[0], years[-1]],
        "mean_block_length_years": BLOCK_LENGTH,
        "endpoints_musd": {
            p: {t: {k: round(v, 0) for k, v in dist(results[p]["lvl"][t]).items()}
                for t in BLOCKS} for p in PATHWAYS},
        "allied_share": {p: dist(results[p]["allied_share"])
                         for p in PATHWAYS},
        "h1": h1, "h2_simulation": h2_sim,
        "arms_demand": {"elasticity": el, **arms_end},
        "war_risk_event_multiplier": war_mult,
        "caveats": [
            "The post-event allied response repeats one episode (2022).",
            "The tier feedback equations are static and their residuals "
            "are serially correlated; the bootstrap carries persistence "
            f"only within runs averaging {BLOCK_LENGTH} years.",
            "Coefficient signs are uncertain; parameter draws retain this.",
        ],
    }
    (OUT / "layer2_summary.json").write_text(json.dumps(summary, indent=1))
    print("H1 scored:", h1["scored_outcome_separation_sd"])
    print("drivers:", h1["driver_separation_sd_context"],
          "reserve:", h1["reserve_separation_sd"])
    print(f"median/reserve {h1['median_over_reserve_ratio']} -> "
          f"{h1['verdict']}")
    print("allied share:", {p: summary["allied_share"][p]["median"]
                            for p in PATHWAYS})


if __name__ == "__main__":
    main()
