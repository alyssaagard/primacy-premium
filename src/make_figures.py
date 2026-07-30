"""
make_figures.py
Stage 4 of the pipeline: the four plates embedded in the HTML preview.

Every mark on these figures is drawn from the processed data or the
simulation output; nothing is illustrative. The palette is fixed to the
preview's design tokens (blush ffebfe, petal facde9, thistle ebe1e7,
ink 141414, ivory fffdf6) and the type is serif to match the page,
which is set in Times New Roman. Liberation Serif is metrically
compatible with Times New Roman and is used when rendering on systems
where Times itself is not installed.

  Plate I    the reserve ledger, 1999 to 2026 (IMF COFER)
  Plate II   the defense ledger, 1988 to 2025 (SIPRI, constant 2024 USD)
  Plate III  the arms trade, 1950 to 2025 (SIPRI TIV) with supplier
             concentration (HHI on order-year windows)
  Plate IV   the conditional forecast fan to 2035, three pathways

Run:  python src/make_figures.py   (after simulate.py)
"""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
OUT = ROOT / "outputs"
FIG = OUT / "figures"

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
    tidy(a, "share of allocated reserves, %")
    vline(a, pd.Timestamp("2022-02-28"), "Russian reserves frozen")
    a.legend(frameon=False, loc="center right", fontsize=9)

    b.fill_between(s["date"], s["OTHER"], 0, color=PETAL, lw=0,
                   label="Nontraditional currencies")
    b.plot(s["date"], s["OTHER"], color=INK, lw=1.0)
    b.plot(s["date"], s["CNY"], color=INK, lw=1.4, ls=":",
           label="Renminbi")
    b.set_ylim(0, 7.2)
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
    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    ax.axvspan(1988, 1998, color=BLUSH, zorder=0)
    ax.text(1993, 1020, "the peace dividend\n1988 to 1998, US -32%",
            ha="center", fontsize=8.5, style="italic")
    ax.fill_between(w.index, w["CHN"], 0, color=PETAL, lw=0)
    ax.plot(w.index, w["USA"], color=INK, lw=1.8,
            label="United States")
    ax.plot(w.index, w["CHN"], color=INK, lw=1.2, ls="--",
            label="China (SIPRI estimate)")
    ax.plot(w.index, w["RUS"], color=INK, lw=1.0, ls=":", label="Russia")
    ax.set_ylim(0, 1150)
    tidy(ax, "US$ billion, constant 2024")
    ax.legend(frameon=False, loc="upper left", fontsize=9)
    ax.annotate("2025: US -7.5% real", xy=(2025, w.loc[2025, "USA"]),
                xytext=(2015.2, 780), fontsize=8.5, style="italic",
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
    styles = {"accretion": ("-", 1.8, "P1 accretion"),
              "retrenchment": ("--", 1.3, "P2 retrenchment"),
              "demonstration": ((0, (3, 1, 1, 1)), 1.3,
                                "P3 demonstration")}

    u = fan[fan["currency"] == "USD"]
    acc = u[u["pathway"] == "accretion"]
    a.fill_between(acc["date"], acc["p10"], acc["p90"], color=PETAL,
                   alpha=0.8, lw=0,
                   label="10th to 90th percentile, P1")
    a.plot(hist["date"], hist["USD"], color=INK, lw=1.8)
    for p, (ls, lw, lab) in styles.items():
        d = u[u["pathway"] == p]
        a.plot(d["date"], d["p50"], color=INK, lw=lw, ls=ls, label=lab)
    a.axhline(50, color=INK, lw=0.6, ls=(0, (1, 3)))
    a.text(pd.Timestamp("2015-06-30"), 50.4, "50% line", fontsize=8,
           style="italic")
    a.set_ylim(38, 62)
    tidy(a, "USD share of reserves, %")
    vline(a, pd.Timestamp("2026-03-31"), "last observed, 2026-Q1", 0.16)
    a.legend(frameon=False, loc="lower left", fontsize=8.5, ncols=2)

    c = fan[fan["currency"] == "CNY"]
    b.plot(hist["date"], hist["CNY"], color=INK, lw=1.6)
    accc = c[c["pathway"] == "accretion"]
    b.fill_between(accc["date"], accc["p10"], accc["p90"], color=PETAL,
                   alpha=0.8, lw=0)
    for p, (ls, lw, lab) in styles.items():
        d = c[c["pathway"] == p]
        b.plot(d["date"], d["p50"], color=INK, lw=lw, ls=ls)
    b.set_ylim(0, 6.5)
    tidy(b, "CNY share, %")
    fig.savefig(FIG / "plate4_forecast.png")
    plt.close(fig)


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    plate_1()
    plate_2()
    plate_3()
    plate_4()
    print("four plates written to outputs/figures/")


if __name__ == "__main__":
    main()
