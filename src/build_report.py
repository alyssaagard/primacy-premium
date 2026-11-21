"""
build_report.py
Stage 5e. Report.

Fills docs/report_template.md from docs/payload.json and the processed
tables, converts it to HTML, and writes report.html at the repository
root. The template is plain text with a small subset of Markdown:
"# " and "## " headings, "- " lists, pipe tables, and `code` spans.

Run: python src/build_report.py   (after build_dashboard_data.py)
"""

import html
import json
import re

import pandas as pd

from config import ALLIED_TIERS, DOCS, OUT, PATHWAYS, PROC, ROOT
from render import fill
from tiers import growth_table

HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>The Primacy Premium: Report</title>
<meta name="description" content="Report on The Primacy Premium: conditional forecasts of defense and commercial markets under Chinese military primacy, 2026 to 2035.">
<meta name="author" content="Alyssa I. Agard">
<link rel="icon" type="image/png" sizes="32x32" href="favicon-32x32.png">
<link rel="icon" type="image/png" sizes="16x16" href="favicon-16x16.png">
<link rel="shortcut icon" href="favicon.ico">
<link rel="apple-touch-icon" sizes="180x180" href="apple-touch-icon.png">
<link rel="manifest" href="site.webmanifest">
<meta name="theme-color" content="#FFEFFE">
<style>
{css}
</style>
</head>
<body>
<div class="wrap">
<header class="doc-head">
  <h1 class="doc-title">THE PRIMACY PREMIUM</h1>
  <p class="doc-sub">Conditional forecasts of defense and commercial markets under Chinese military primacy, 2026 to 2035</p>
  <div class="doc-meta">
    <span>Alyssa I. Agard</span><span>Build of {built}</span><span>simulation seed {seed}</span>
  </div>
</header>
<nav class="toc" aria-label="Table of contents">
<h2 class="toc-h">Contents</h2>
<ol class="toc-list">
{toc}
</ol>
</nav>
<main>
{body}
</main>
</div>
</body>
</html>
"""


def md_table(header: list, rows: list) -> str:
    lines = ["| " + " | ".join(header) + " |"]
    lines += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(lines)


def inline(text: str) -> str:
    text = html.escape(text, quote=False)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", text)


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def to_html(md: str) -> tuple[str, str]:
    """Convert the template subset of Markdown; return (body, toc)."""
    out, toc = [], []
    for block in re.split(r"\n\s*\n", md.strip()):
        lines = block.strip().split("\n")
        first = lines[0]
        if first.startswith("# ") or first.startswith("## "):
            level = 1 if first.startswith("# ") else 2
            title = first[level + 1:].strip()
            out.append(f'<h{level} id="{slug(title)}">{inline(title)}</h{level}>')
            toc.append(f'<li class="lvl{level}"><a href="#{slug(title)}">'
                       f'{inline(title)}</a></li>')
        elif all(ln.startswith("- ") for ln in lines):
            items = "\n".join(f"<li>{inline(ln[2:])}</li>" for ln in lines)
            out.append(f"<ul>\n{items}\n</ul>")
        elif all(ln.startswith("|") for ln in lines):
            cells = [[c.strip() for c in ln.strip("|").split("|")]
                     for ln in lines]
            head = "".join(f"<th>{inline(c)}</th>" for c in cells[0])
            body = "\n".join(
                "<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>"
                for r in cells[1:])
            out.append(f"<table>\n<thead><tr>{head}</tr></thead>\n"
                       f"<tbody>\n{body}\n</tbody>\n</table>")
        else:
            out.append(f"<p>{inline(' '.join(lines))}</p>")
    return "\n".join(out), "\n".join(toc)


def report_values(payload: dict) -> tuple[dict, dict]:
    cal1 = json.loads((OUT / "calibration.json").read_text())
    cal2 = json.loads((OUT / "calibration_layer2.json").read_text())
    hyp = payload["hyp"]
    g = growth_table()
    last = int(g.index.max())
    dep = pd.read_csv(PROC / "allied_import_dependence.csv")
    win = payload["arms"]["last_complete_window"]
    d = dep[dep.window == win].set_index("tier").us_share * 100
    ch = pd.read_csv(PROC / "energy_chokepoints.csv")
    ch = ch[ch.year == ch.year.max()].set_index("chokepoint").flow_mbd
    mar = pd.read_csv(PROC / "maritime_panel.csv")
    built = mar[mar.series == "ships_built_gt"]
    sy = int(built.year.max())
    b = built[built.year == sy].set_index("economy").value
    nuc = pd.read_csv(PROC / "nuclear_panel.csv")
    stock = {(r.country, int(r.year)): int(r.stockpile)
             for r in nuc.itertuples()}
    mob = cal2["demonstration_mobilization_2022"]
    w = cal2["event_windows"]
    hp = pd.read_csv(PROC / "hypothesis_panel.csv")
    semi = pd.read_csv(PROC / "semiconductor_channel.csv")
    released = semi[semi.basis == "earnings release"].quarter.tolist()
    tsmc_pending = (
        f"TSMC revenue for {', '.join(released)} is taken from the earnings "
        "release and should be replaced when the financial statements are "
        "added." if released else
        f"TSMC statements after {semi.quarter.iloc[-1]}.")
    rep = {
        "tsmc_pending": tsmc_pending,
        "tsmc_latest_basis": semi.basis.iloc[-1],
        "peace_total": cal1["cases"]["peace_dividend"]["total_real_change_pct"],
        "other_change":
            hyp["h3"]["share_change"]["Other than USD, EUR, JPY, GBP, CNY"],
        "nato_last": float(g.loc[last, "NATO Europe"]),
        "gap_month": hyp["h3"]["months"][-1],
        "swift_cny": hyp["h3"]["swift_cny"][-1],
        "trade_finance": hyp["h3"]["trade_finance"][-1],
        "cofer_cny": hyp["h3"]["cofer_cny"][-1],
        "dep_window": f"{win} to {win + 4}",
        "dep_ip_us": float(d["Indo-Pacific allies"]),
        "dep_nato_us": float(d["NATO Europe"]),
        "hormuz": float(ch["Strait of Hormuz"]),
        "malacca": float(ch["Strait of Malacca"]),
        "chokepoint_year": int(pd.read_csv(
            PROC / "energy_chokepoints.csv").year.max()),
        "china_ship_share": 100 * b["China (derived)"] / b["World"],
        "ship_year": sy,
        "maritime_rows": len(mar),
        "nato_allies": int(pd.read_csv(PROC / "nato_burden.csv").ally.nunique()),
        "cn_2025": stock[("China", 2025)], "cn_2026": stock[("China", 2026)],
        "cn_2030": stock[("China", 2030)], "cn_2035": stock[("China", 2035)],
        "us_stock": stock[("United States", 2026)],
        "ru_stock": stock[("Russia", 2026)],
        "n_events": len(pd.read_csv(PROC / "taiwan_strait_events.csv")),
        "n_alliance": len(pd.read_csv(PROC / "alliance_matrix.csv")),
        "panel_rows": len(hp),
        "mob_nato": mob["NATO Europe"]["delta_pp"],
        "mob_hedge": mob["Hedging middle powers"]["delta_pp"],
        "mob_ip": mob["Indo-Pacific allies"]["delta_pp"],
        "win_pd_nato": w["peace_dividend_1989_1998"]["NATO Europe"],
        "win_seq_nato": w["sequester_2011_2015"]["NATO Europe"],
    }

    h1 = hyp["h1"]
    h1_rows = [[o, f"{s:.2f}", "scored"]
               for o, s in zip(h1["outcomes"], h1["sd"])]
    h1_rows += [[k, f"{v:.2f}", "not scored (assumed)"]
                for k, v in h1["drivers"].items()]
    h1_rows.append(["US dollar reserve share", f"{h1['reserve']:.2f}",
                    "reference"])

    def h2_row(label, r):
        return [label, r["n_obs"], f"{r['b_us']} ({r['se_us']})",
                f"{r['b_cn']} ({r['se_cn']})", r["abs_gap"],
                f"{r['p_one_sided']:.2f}"]

    h2 = hyp["h2"]
    h2_rows = [h2_row("Pooled, expenditure-weighted (test)", h2["primary"])]
    h2_rows += [h2_row(f"{t}, weighted", h2["by_tier"][t])
                for t in ALLIED_TIERS]
    sv = h2["sensitivity"]
    h2_rows += [
        h2_row("Pooled, unweighted", sv["unweighted"]),
        h2_row("Pooled, US reductions only", sv["us_reductions_only"]),
        h2_row("Pooled, US reductions only, from 1997",
               sv["us_reductions_only_from_1997"]),
        h2_row("Pooled, US reductions only, lagged tier growth added",
               sv["us_reductions_only_tier_lag_control"]),
    ]

    fb = cal2["feedback"]
    tier_rows = [[t, f"{fb[t]['b_us']} ({fb[t]['se_us']})",
                  f"{fb[t]['b_cn']} ({fb[t]['se_cn']})", fb[t]["nobs"],
                  fb[t]["r2"], f"{fb[t]['breusch_godfrey_p']:.3f}",
                  f"{fb[t]['static_test']['p_one_sided']:.2f}"]
                 for t in ALLIED_TIERS]

    ep = hyp["endpoints_musd"]
    blocks = list(ep[PATHWAYS[0]].keys())
    end_rows = [[b] + [f"{ep[p][b]['median'] / 1000:,.0f} "
                       f"({ep[p][b]['p10'] / 1000:,.0f} to "
                       f"{ep[p][b]['p90'] / 1000:,.0f})" for p in PATHWAYS]
                for b in blocks]
    end_rows.append(["Allied share of world, %"] + [
        f"{hyp['allied_share'][p]['median']:.1f} "
        f"({hyp['allied_share'][p]['p10']:.1f} to "
        f"{hyp['allied_share'][p]['p90']:.1f})" for p in PATHWAYS])

    counts = hp.groupby(["hypothesis", "role"]).size().reset_index(name="n")
    tables = {
        "REP_H1_TABLE": md_table(
            ["Outcome", "Separation, sd", "Status"], h1_rows),
        "REP_H2_TABLE": md_table(
            ["Specification", "N", "b_us (se)", "b_cn (se)",
             "Difference in magnitudes", "One-sided p"], h2_rows),
        "REP_TIER_TABLE": md_table(
            ["Tier", "b_us (se)", "b_cn (se)", "N", "R-squared",
             "Breusch-Godfrey p", "Static test p"], tier_rows),
        "REP_ENDPOINT_TABLE": md_table(
            [f"{payload['meta']['horizon'][1]} median (10th to 90th "
             "percentile), USD bn constant 2024", "Accretion",
             "Retrenchment", "Demonstration"], end_rows),
        "REP_PANEL_TABLE": md_table(
            ["Hypothesis", "Role", "Rows"],
            [[r.hypothesis, r.role, r.n] for r in counts.itertuples()]),
    }
    return rep, tables


def main() -> None:
    payload = json.loads((DOCS / "payload.json").read_text())
    rep, tables = report_values(payload)
    md = fill((DOCS / "report_template.md").read_text(),
              {**payload, "rep": rep}, tables)
    body, toc = to_html(md)
    css = (DOCS / "report.css").read_text().strip()
    page = HEAD.format(css=css, built=payload["generated"],
                       seed=payload["meta"]["seed"], toc=toc, body=body)
    (ROOT / "report.html").write_text(page)
    words = len(re.sub(r"<[^>]+>", " ", body).split())
    print(f"report.html written ({words:,} words)")


if __name__ == "__main__":
    main()
