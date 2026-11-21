"""
build_preview.py
Stage 5c. Static summary page.

Fills docs/index_template.html from docs/payload.json and embeds the
four figures as base64, writing docs/static_preview.html. The file has
no external dependencies.

Run: python src/build_preview.py   (after build_dashboard_data.py)
"""

import base64
import json

from config import DOCS, FIG
from render import fill

FIGURES = {"FIG1": "plate1_reserves.png", "FIG2": "plate2_milex.png",
           "FIG3": "plate3_arms_trade.png", "FIG4": "plate4_forecast.png"}


def main() -> None:
    payload = json.loads((DOCS / "payload.json").read_text())
    extra = {k: base64.b64encode((FIG / f).read_bytes()).decode("ascii")
             for k, f in FIGURES.items()}
    html = fill((DOCS / "index_template.html").read_text(), payload, extra)
    (DOCS / "static_preview.html").write_text(html)
    print(f"docs/static_preview.html written "
          f"({len(html.encode()) / 1024:,.0f} KB)")


if __name__ == "__main__":
    main()
