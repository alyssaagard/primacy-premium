"""
make_figures.py
Stage 5. Four static figures.

  Figure 1   reserve shares by currency (IMF COFER)
  Figure 2   military expenditure of the United States, China and
             Russia from 1988 (SIPRI, constant 2024 USD)
  Figure 3   world arms deliveries (SIPRI TIV) and supplier
             concentration (Herfindahl index, five-year order windows)
  Figure 4   simulated reserve shares to 2035 by pathway

All values are read from the processed tables and simulation outputs.
Fonts fall back to Liberation Serif where Times New Roman is absent.

Run: python src/make_figures.py
Writes: outputs/figures/plate1_reserves.png ... plate4_forecast.png
"""

import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from config import FIG, OUT, PROC

INK = "#141414"
BLUSH = "#ffebfe"
PETAL = "#facde9"
THISTLE = "#ebe1e7"
IVORY = "#fffdf6"

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Liberation Serif", "DejaVu Serif"],
    "font.size": 11,
    "axes.edgecolor": INK,
    "axes.linewidth": 0.8,
    "axes.labelcolor": INK,
    "text.color": INK,
    "xtick.color": INK,
    "ytick.color": INK,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.grid": True,
    "grid.color": THISTLE,
    "grid.linewidth": 0.7,
    "axes.axisbelow": True,
    "savefig.dpi": 200,
    "savefig.bbox": "tight",
})


def tidy(ax, ylab=""):
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="x", visible=False)
    if ylab:
        ax.set_ylabel(ylab, fontsize=10)


def vline(ax, x, label, y_frac=0.94):
    ax.axvline(x, color=INK, lw=0.7, ls=(0, (2, 3)))
    ax.text(x, ax.get_ylim()[0] + y_frac * (ax.get_ylim()[1]
            - ax.get_ylim()[0]), " " + label, fontsize=8.5,
            style="italic", va="top")


def plate_1():
    s = pd.read_csv(PROC / "cofer_shares_wide.csv", parse_dates=["date"])
    fig, (a, b) = plt.subplots(
        2, 1, figsize=(8.6, 5.4), sharex=True,
        gridspec_kw={"height_ratios": [2.1, 1.2], "hspace": 0.12},
    )
    a.fill_between(s["date"], s["USD"], 40, color=PETAL, alpha=0.55, lw=0)
    a.plot(s["date"], s["USD"], color=INK, lw=1.8, label="US dollar")
    a.plot(s["date"], s["EUR"], color=INK, lw=1.0, ls="--", label="Euro")
    a.set_ylim(15, 74)
    tidy(a, "share of foreign exchange reserves, %")
    vline(a, pd.Timestamp("2022-02-28"), "Russian reserves frozen")
    a.legend(frameon=False, loc="center right", fontsize=9)

    b.fill_between(s["date"], s["OTHER"], 0, color=PETAL, lw=0,
                   label="Other currencies")
    b.plot(s["date"], s["OTHER"], color=INK, lw=1.0)
    b.plot(s["date"], s["CNY"], color=INK, lw=1.4, ls=":",
           label="Renminbi")
    b.set_ylim(0, max(7.2, 1.08 * s["OTHER"].max()))
    tidy(b, "%")
    vline(b, pd.Timestamp("2016-11-30"), "RMB identified in COFER", 0.90)
    b.legend(frameon=False, loc="upper left", fontsize=9)
    fig.savefig(FIG / "plate1_reserves.png")
    plt.close(fig)


def plate_2():
    p = pd.read_csv(PROC / "milex_panel.csv")
    w = p.pivot_table(index="year", columns="iso3",
                      values="milex_constusd_m") / 1e3
    w = w.loc[1988:]
    cases = json.loads((OUT / "calibration.json").read_text())["cases"]
    drop = cases["peace_dividend"]["total_real_change_pct"]
    last = cases["us_last_year"]
    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    ax.axvspan(1988, 1998, color=BLUSH, zorder=0)
    ax.text(1993, 1020, f"1988 to 1998\nUnited States {drop:.0f}%",
            ha="center", fontsize=8.5, style="italic")
    ax.fill_between(w.index, w["CHN"], 0, color=PETAL, lw=0)
    ax.plot(w.index, w["USA"], color=INK, lw=1.8,
            label="United States")
    ax.plot(w.index, w["CHN"], color=INK, lw=1.2, ls="--",
            label="China (SIPRI estimate)")
    ax.plot(w.index, w["RUS"], color=INK, lw=1.0, ls=":", label="Russia")
    ax.set_ylim(0, 1150)
    tidy(ax, "US$ billion, constant 2024")
    ax.legend(frameon=False, loc="center left", bbox_to_anchor=(0.02, 0.42),
              fontsize=9)
    ax.annotate(f"{last['year']}: United States {last['value']:+.1f}% real",
                xy=(last["year"], w.loc[last["year"], "USA"]),
                xytext=(2012.5, 780), fontsize=8.5, style="italic",
                arrowprops=dict(arrowstyle="-", lw=0.7, color=INK))
    fig.savefig(FIG / "plate2_milex.png")
    plt.close(fig)


def plate_3():
    v = pd.read_csv(PROC / "arms_transfers_global.csv")
    h = (pd.read_csv(PROC / "supplier_concentration.csv")
         [["window", "hhi"]].drop_duplicates())
    h = h[(h["window"] >= 1950) & (h["window"] <= 2020)]
    fig, ax = plt.subplots(figsize=(8.6, 4.2))
    ax.fill_between(v["year"], v["tiv_m"] / 1e3, 0, color=PETAL, lw=0)
    ax.plot(v["year"], v["tiv_m"] / 1e3, color=INK, lw=1.3,
            label="Deliveries of major arms (left)")
    tidy(ax, "SIPRI trend indicator value, bn")
    ax.set_ylim(0, 50)

    ax2 = ax.twinx()
    ax2.plot(h["window"] + 2.5, h["hhi"], color=INK, lw=1.0, ls="--",
             marker="o", ms=3.5, markerfacecolor=IVORY,
             label="Supplier concentration, HHI (right)")
    ax2.set_ylim(0, 0.42)
    ax2.set_ylabel("Herfindahl index of suppliers", fontsize=10)
    ax2.spines[["top"]].set_visible(False)
    ax2.grid(visible=False)

    lines = ax.get_legend_handles_labels()[0] + \
        ax2.get_legend_handles_labels()[0]
    labels = ax.get_legend_handles_labels()[1] + \
        ax2.get_legend_handles_labels()[1]
    ax.legend(lines, labels, frameon=False, loc="upper right", fontsize=9)
    fig.savefig(FIG / "plate3_arms_trade.png")
    plt.close(fig)


def plate_4():
    s = pd.read_csv(PROC / "cofer_shares_wide.csv", parse_dates=["date"])
    fan = pd.read_csv(OUT / "simulation_fan.csv")
    fan["date"] = (pd.PeriodIndex(fan["quarter"], freq="Q")
                   .to_timestamp(how="end"))
    hist = s[s["date"] >= "2015-01-01"]

    fig, (a, b) = plt.subplots(
        2, 1, figsize=(8.6, 6.0), sharex=True,
        gridspec_kw={"height_ratios": [2.2, 1.1], "hspace": 0.13},
    )
    styles = {"accretion": ("-", 1.8, "accretion"),
              "retrenchment": ("--", 1.3, "retrenchment"),
              "demonstration": ((0, (3, 1, 1, 1)), 1.3, "demonstration")}

    u = fan[fan["currency"] == "USD"]
    acc = u[u["pathway"] == "accretion"]
    a.fill_between(acc["date"], acc["p10"], acc["p90"], color=PETAL,
                   alpha=0.8, lw=0,
                   label="10th to 90th percentile, accretion")
    a.plot(hist["date"], hist["USD"], color=INK, lw=1.8)
    for p, (ls, lw, lab) in styles.items():
        d = u[u["pathway"] == p]
        a.plot(d["date"], d["p50"], color=INK, lw=lw, ls=ls, label=lab)
    a.axhline(50, color=INK, lw=0.6, ls=(0, (1, 3)))
    a.text(pd.Timestamp("2015-06-30"), 50.4, "50% line", fontsize=8,
           style="italic")
    a.set_ylim(38, 62)
    tidy(a, "USD share of reserves, %")
    vline(a, s["date"].iloc[-1], f"last observed, {s['quarter'].iloc[-1]}",
          0.16)
    a.legend(frameon=False, loc="lower left", fontsize=8.5, ncols=2)

    c = fan[fan["currency"] == "CNY"]
    b.plot(hist["date"], hist["CNY"], color=INK, lw=1.6)
    accc = c[c["pathway"] == "accretion"]
    b.fill_between(accc["date"], accc["p10"], accc["p90"], color=PETAL,
                   alpha=0.8, lw=0)
    for p, (ls, lw, lab) in styles.items():
        d = c[c["pathway"] == p]
        b.plot(d["date"], d["p50"], color=INK, lw=lw, ls=ls)
    b.set_ylim(0, 1.05 * accc["p90"].max())
    tidy(b, "CNY share of reserves, %")
    fig.savefig(FIG / "plate4_forecast.png")
    plt.close(fig)


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    plate_1()
    plate_2()
    plate_3()
    plate_4()
    print("four figures written to outputs/figures/")


if __name__ == "__main__":
    main()
