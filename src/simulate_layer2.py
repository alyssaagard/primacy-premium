"""
simulate_layer2.py
Stage 3b: the system-dynamics and event simulation, and the H1 test.

WHAT RUNS HERE
--------------
Ten thousand seeded draws per pathway, annual, 2026 to 2035, over a
five-block system: the United States, China, three allied tiers, and a
rest-of-world block so world totals close. The principals follow their
pathway definitions from stage 2 (accretion at measured decade rates,
retrenchment substituting the peace dividend contraction for the United
States, demonstration adding an event at a uniform random year 2028 to
2031). Allied tiers respond through the estimated feedback equations,
with three uncertainties propagated jointly: parameter uncertainty
(coefficients redrawn each path from their estimated sampling
distributions, so the sign ambiguity in the feedback survives into the
fan), innovation uncertainty (residuals bootstrapped from the measured
pools, keeping the true fat tails), and event timing. After a
demonstration event, allied tiers additionally receive the measured
2022 mobilization differential, the one modern observation of
alliance-wide response to a violent shock, decayed linearly over four
years and carried with its n = 1 caveat.

THE H1 TEST
-----------
H1 claims pathway identity conditions outcomes more than the endpoint.
The statistic is the same one layer 1 used for reserves: the maximum
separation between pathway medians divided by the mean within-pathway
endpoint standard deviation. Two definitional choices matter and are
stated here rather than left implicit. First, outcomes are responses,
not drivers: the United States and China paths differ across pathways
by construction, so the scored outcome set is the three allied tiers
and the allied share of world spending, with the principals reported as
context only. Second, the primary criterion is the median scored
outcome against twice the reserve-channel separation, with the minimum
reported alongside as the strict robustness reading, so a single weakly
coupled tier is named rather than either hidden or allowed to veto the
gradient the other outcomes show.

A layer 4 hook is also written: world arms-transfer demand is projected
from allied and principal budgets through the measured elasticity of
delivery volumes to world expenditure growth, and the war-risk
multiplier from the 2026 Gulf episode is attached to the demonstration
event year as the insurance-market repricing factor.

Run:  python src/simulate_layer2.py
Writes: outputs/layer2_fan.csv, outputs/layer2_summary.json
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
OUT = ROOT / "outputs"

SEED = 20260724
DRAWS = 10_000
YEARS = list(range(2026, 2036))
TIERS = ["Indo-Pacific allies", "NATO Europe", "Hedging middle powers"]
PATHWAYS = ["accretion", "retrenchment", "demonstration"]


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


def load_inputs():
    cal1 = json.loads((OUT / "calibration.json").read_text())
    cal2 = json.loads((OUT / "calibration_layer2.json").read_text())
    pools = pd.read_csv(OUT / "layer2_residual_pools.csv")
    tier = tier_panel()
    tier = tier[tier.measure == "milex_usd_const2024"]
    levels = tier.pivot_table("value", "year", "tier").sort_index()
    m = pd.read_csv(PROC / "milex_panel.csv")
    world = m[m.iso3 == "WORLD"].set_index("year").milex_constusd_m
    base = levels.loc[levels.index.max()].to_dict()
    base["World"] = float(world.loc[world.index.max()])
    base["Rest of world"] = base["World"] - sum(
        v for k, v in base.items() if k not in ("World", "Rest of world"))
    arms = pd.read_csv(PROC / "arms_transfers_global.csv")
    war = pd.read_csv(PROC / "war_risk_events.csv")
    return cal1, cal2, pools, base, world, arms, war


def arms_elasticity(arms: pd.DataFrame, world: pd.Series) -> dict:
    """Elasticity of world delivery growth to world expenditure growth."""
    a = arms.set_index("year").tiv_m
    g = pd.concat([np.log(a).diff().rename("arms"),
                   np.log(world).diff().rename("milex")], axis=1).dropna()
    import statsmodels.api as sm
    fit = sm.OLS(g.arms, sm.add_constant(g.milex)).fit(
        cov_type="HAC", cov_kwds={"maxlags": 3})
    return {"beta": round(float(fit.params.milex), 3),
            "se": round(float(fit.bse.milex), 3),
            "const": round(float(fit.params.const), 4),
            "nobs": int(fit.nobs)}


def main() -> None:
    rng = np.random.default_rng(SEED)
    cal1, cal2, pools, base, world_hist, arms, war = load_inputs()
    fb = cal2["feedback"]
    blocks = cal2["principal_blocks"]
    mob = cal2["demonstration_mobilization_2022"]
    pd_rate = cal1["cases"]["peace_dividend"]["annual_rate_pct"]
    acc = cal1["cases"]["accretion_decade"]
    pool = {b: g.resid.to_numpy() for b, g in pools.groupby("block")}
    war_mult = float(war.multiple.iloc[0])

    n_y = len(YEARS)
    results = {}
    for pi, path in enumerate(PATHWAYS):
        # Sub-seed by fixed pathway index: Python's salted str hash would
        # vary across processes and quietly break exact reproducibility.
        rng_p = np.random.default_rng(SEED + pi + 1)
        us_g = np.full((DRAWS, n_y), acc["usa"])
        cn_g = np.full((DRAWS, n_y), acc["china"])
        if path == "retrenchment":
            us_g[:] = pd_rate
        us_g += rng_p.choice(pool["United States"], (DRAWS, n_y))
        cn_g += rng_p.choice(pool["China"], (DRAWS, n_y))

        event_year = (rng_p.integers(2028, 2032, DRAWS)
                      if path == "demonstration" else np.full(DRAWS, 9999))

        lvl = {t: np.full(DRAWS, base[t]) for t in TIERS}
        lvl["United States"] = np.full(DRAWS, base["United States"])
        lvl["China"] = np.full(DRAWS, base["China"])
        lvl["Rest of world"] = np.full(DRAWS, base["Rest of world"])

        # Parameter uncertainty: one coefficient draw per path per tier.
        coef = {t: {
            "b0": rng_p.normal(fb[t]["b0"], 0.0, DRAWS),
            "b_us": rng_p.normal(fb[t]["b_us"], fb[t]["se_us"], DRAWS),
            "b_cn": rng_p.normal(fb[t]["b_cn"], fb[t]["se_cn"], DRAWS)}
            for t in TIERS}

        fan_rows, us_prev, cn_prev = [], np.zeros(DRAWS), np.zeros(DRAWS)
        # Lag initialization: the observed 2025 growth for both principals.
        us_prev[:] = blocks["United States"]["mean_2016_2025"]
        cn_prev[:] = blocks["China"]["mean_2016_2025"]

        world_paths = np.zeros((DRAWS, n_y))
        allied_share = np.zeros((DRAWS, n_y))
        for j, year in enumerate(YEARS):
            for t in TIERS:
                g = (coef[t]["b0"] + coef[t]["b_us"] * us_prev
                     + coef[t]["b_cn"] * cn_prev
                     + rng_p.choice(pool[t], DRAWS))
                since = year - event_year
                bump = np.where((since >= 0) & (since < 4),
                                mob[t]["delta_pp"] * (1 - since / 4), 0.0)
                lvl[t] = lvl[t] * (1 + (g + bump) / 100)
            rest_g = (blocks["Rest of world"]["mean_2016_2025"]
                      + rng_p.choice(pool["Rest of world"], DRAWS))
            lvl["Rest of world"] *= (1 + rest_g / 100)
            lvl["United States"] *= (1 + us_g[:, j] / 100)
            lvl["China"] *= (1 + cn_g[:, j] / 100)
            us_prev, cn_prev = us_g[:, j], cn_g[:, j]

            world = sum(lvl.values())
            world_paths[:, j] = world
            allied_share[:, j] = 100 * (lvl["Indo-Pacific allies"]
                                        + lvl["NATO Europe"]) / world
            for name, arr in lvl.items():
                q = np.percentile(arr, [5, 10, 25, 50, 75, 90, 95])
                fan_rows.append({"pathway": path, "block": name, "year": year,
                                 **{f"p{p:02d}": round(float(v), 1)
                                    for p, v in zip([5, 10, 25, 50, 75, 90, 95], q)}})
        results[path] = {"lvl": {k: v.copy() for k, v in lvl.items()},
                         "allied_share_2035": allied_share[:, -1],
                         "world_2035": world_paths[:, -1],
                         "fan": fan_rows}

    # ---- H1: pathway separation per defense outcome, vs the reserve channel.
    def separation(values_by_path: dict) -> float:
        meds = [np.median(v) for v in values_by_path.values()]
        sds = [np.std(v) for v in values_by_path.values()]
        return float((max(meds) - min(meds)) / np.mean(sds))

    scored = {t: separation({p: results[p]["lvl"][t] for p in PATHWAYS})
              for t in TIERS}
    scored["Allied share of world"] = separation(
        {p: results[p]["allied_share_2035"] for p in PATHWAYS})
    drivers = {t: separation({p: results[p]["lvl"][t] for p in PATHWAYS})
               for t in ["United States", "China"]}
    reserve_sep = json.loads((OUT / "simulation_summary.json").read_text())[
        "usd"]["pathway_separation_sd_units"]

    med = float(np.median(list(scored.values())))
    mn_name, mn = min(scored.items(), key=lambda kv: kv[1])
    h1 = {
        "scored_outcome_separation_sd": {k: round(v, 2) for k, v in scored.items()},
        "driver_separation_sd_context": {k: round(v, 2) for k, v in drivers.items()},
        "reserve_separation_sd": round(float(reserve_sep), 2),
        "median_outcome_sd": round(med, 2),
        "median_over_reserve_ratio": round(med / reserve_sep, 1),
        "min_outcome": {"name": mn_name, "sd": round(mn, 2),
                        "over_reserve_ratio": round(mn / reserve_sep, 1)},
        "verdict": ("supported" if med > 2 * reserve_sep else "not supported"),
        "definition": "max median gap over mean within-pathway sd, 2035 endpoints; "
                      "scored outcomes are the three allied tiers and the allied "
                      "share of world spending (responses, not drivers); primary "
                      "criterion is the median scored outcome exceeding twice the "
                      "reserve-channel separation, with the minimum outcome "
                      "reported as the strict robustness reading",
    }

    # ---- H2 in simulation: retrenchment vs accretion effect on allied budgets.
    h2_sim = {}
    for t in TIERS:
        d_ret = np.median(results["retrenchment"]["lvl"][t]) \
            - np.median(results["accretion"]["lvl"][t])
        h2_sim[t] = {"retrench_minus_accretion_2035_musd": round(float(d_ret), 0),
                     "pct_of_accretion_median": round(
                         100 * d_ret / np.median(results["accretion"]["lvl"][t]), 1)}

    # ---- layer 4 hooks: arms demand projection and war-risk attachment.
    el = arms_elasticity(arms, world_hist := pd.read_csv(
        PROC / "milex_panel.csv").query("iso3=='WORLD'").set_index("year").milex_constusd_m)
    arms_2035 = {}
    base_arms = float(arms.tiv_m.iloc[-1])
    base_world = float(world_hist.iloc[-1])
    for p in PATHWAYS:
        wg = (results[p]["world_2035"] / base_world) ** (1 / 10) - 1
        growth = np.exp((el["const"] + el["beta"] * np.log(1 + wg)) * 10)
        arms_2035[p] = {"median_tiv_m": round(float(np.median(base_arms * growth)), 0),
                        "p10": round(float(np.percentile(base_arms * growth, 10)), 0),
                        "p90": round(float(np.percentile(base_arms * growth, 90)), 0)}

    fan = pd.DataFrame([r for p in PATHWAYS for r in results[p]["fan"]])
    fan.to_csv(OUT / "layer2_fan.csv", index=False)

    summary = {
        "draws": DRAWS, "seed": SEED, "horizon": [YEARS[0], YEARS[-1]],
        "endpoints_2035_musd": {
            p: {t: {"median": round(float(np.median(results[p]["lvl"][t])), 0),
                    "p10": round(float(np.percentile(results[p]["lvl"][t], 10)), 0),
                    "p90": round(float(np.percentile(results[p]["lvl"][t], 90)), 0)}
                for t in TIERS + ["United States", "China"]}
            for p in PATHWAYS},
        "allied_share_2035": {
            p: {"median": round(float(np.median(results[p]["allied_share_2035"])), 2),
                "p10": round(float(np.percentile(results[p]["allied_share_2035"], 10)), 2),
                "p90": round(float(np.percentile(results[p]["allied_share_2035"], 90)), 2)}
            for p in PATHWAYS},
        "h1": h1, "h2_simulation": h2_sim,
        "arms_demand_2035": {"elasticity": el, **arms_2035},
        "war_risk_event_multiplier": war_mult,
        "caveats": [
            "Demonstration mobilization replays the 2022 differential, n = 1.",
            "Feedback coefficients carry sign uncertainty; parameter draws keep it.",
            "Annual frequency; quarterly event dynamics live in the reserve layer.",
        ],
    }
    (OUT / "layer2_summary.json").write_text(json.dumps(summary, indent=1))
    print("H1 scored:", h1["scored_outcome_separation_sd"],
          "drivers:", h1["driver_separation_sd_context"])
    print("vs reserve", h1["reserve_separation_sd"], "->", h1["verdict"],
          f"(median/reserve = {h1['median_over_reserve_ratio']}x; "
          f"min = {h1['min_outcome']['name']} at {h1['min_outcome']['sd']})")
    print("Allied share 2035 medians:",
          {p: summary["allied_share_2035"][p]["median"] for p in PATHWAYS})


if __name__ == "__main__":
    main()
