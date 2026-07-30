"""
build_data_dictionary.py
Stage 5d: the codebook, generated from the build rather than typed.

WHY GENERATED
-------------
A data dictionary that is written by hand drifts from the data the first
time the pipeline changes. This one is assembled from the same register
specification the dashboard publishes (so every artifact, note, and row
count is the build's own), plus the columns and dtypes read off each
file at generation time. If the register's hard gate fails, so does the
dictionary: an incomplete build cannot document itself as complete.

The one section written by hand is the grammar of hypothesis_panel.csv,
because a codebook's job is to explain intent, and intent does not live
in dtypes.

Run:  python src/build_data_dictionary.py
Writes: DATA_DICTIONARY.md at the repository root.
"""

import json
from pathlib import Path

import pandas as pd

from build_dashboard_data import register

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
OUT = ROOT / "outputs"


def resolve(name: str) -> Path:
    for cand in (PROC / f"{name}.csv", OUT / f"{name}.csv", OUT / f"{name}.json"):
        if cand.exists():
            return cand
    raise FileNotFoundError(name)


def describe(path: Path) -> str:
    if path.suffix == ".json":
        keys = list(json.loads(path.read_text()).keys())
        return "Top-level keys: `" + "`, `".join(str(k) for k in keys) + "`."
    df = pd.read_csv(path, nrows=500)
    cols = [f"`{c}` ({df[c].dtype})" for c in df.columns]
    return "Columns: " + ", ".join(cols) + "."


GRAMMAR = """\
## The unified hypothesis dataset, in detail

`data/processed/hypothesis_panel.csv` is the single table that measures
every hypothesis. One row is one measurement, and the grammar is constant:

| column | meaning |
|---|---|
| `hypothesis` | `H1`, `H2`, `H3`, or `context` |
| `role` | `test` (a computed statistic), `evidence` (an observed series the test reads), `input` (a simulated quantity), or `robustness` (an alternative measurement guarding a caveat) |
| `series` | what is measured, e.g. `settlement_reserve_gap`, `feedback_b_us`, `pathway_separation` |
| `scope` | the actor, tier, currency, pathway, chokepoint, or window the row belongs to; pipe-separated when two dimensions apply |
| `freq` | the row's native frequency: `quarterly`, `monthly`, `annual`, `annual mean`, `window`, `endpoint`, or `event` |
| `period` | year, quarter (`2026-Q1`), month (`2026-06`), or a year range (`1969-1975`) |
| `value` | the number |
| `unit` | its unit, stated in full |
| `source` | the upstream source or pipeline script that produced it |

Filter on `hypothesis` to read one claim's complete case, test and
evidence together. Filter `role == "test"` for the statistics behind the
verdicts in `outputs/hypothesis_tests.json`. The `context` rows carry
the structural exposures the channels reference (warheads, chokepoint
flows, fabrication revenue, shipbuilding, connectivity, the Brent path,
and the war-risk multiple) so the dataset stands alone in a BI tool
without the rest of the repository.

Worth knowing when reusing:

The settlement-reserve gap is monthly Swift renminbi payments share
minus the COFER renminbi share of that month's quarter, with the latest
reported quarter carried forward for months COFER has not yet covered.
The flow-attribution robustness series is each currency's share of the
quarterly change in total allocated claims; it bounds, rather than
removes, the valuation caveat on stock shares. H1 separations are in
standard-deviation units of endpoint spread, scored on allied responses
only, with the imposed drivers reported as context. All simulated rows
descend from seed 20260724 and reproduce exactly.
"""


def main() -> None:
    reg = register()
    by_group: dict[str, list] = {}
    for r in reg:
        by_group.setdefault(r["group"], []).append(r)

    lines = [
        "# Data dictionary",
        "",
        "Every artifact the model produces or consumes, grouped as in the",
        "page's input register, with row counts and columns read from the",
        "files at generation time. This file is written by",
        "`src/build_data_dictionary.py` from the same register the dashboard",
        "publishes, and generation fails if any artifact is missing, so the",
        "codebook cannot describe a build that does not exist. Sources are",
        "cited in full in `REFERENCES.md`; reuse terms are stated there and",
        "in the license.",
        "",
    ]
    total = 0
    for group, items in by_group.items():
        lines += [f"## {group}", ""]
        for r in items:
            path = resolve(r["table"])
            rel = path.relative_to(ROOT)
            total += r["rows"]
            lines += [f"### `{rel}`", "",
                      f"{r['note']} Rows or keys: {r['rows']:,}.", "",
                      describe(path), ""]
    lines += [GRAMMAR, "",
              f"Thirty artifacts, {total:,} rows and keys in all, every one",
              "read off disk at build time.", ""]
    (ROOT / "DATA_DICTIONARY.md").write_text("\n".join(lines))
    print(f"DATA_DICTIONARY.md: {len(reg)} artifacts documented, "
          f"{total:,} rows and keys")


if __name__ == "__main__":
    main()
