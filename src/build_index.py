"""
build_index.py
Stage 5b: inject the payload into the template and write index.html.

The split between 5a and 5b is deliberate. Stage 5a decides what is
true; stage 5b decides how it looks. Keeping them apart means the page
can be restyled without touching a single number, and the numbers can be
refreshed without touching a single style rule. It also means payload.json
is inspectable on its own, which is what a reviewer asks for first.

Plotly loads from a CDN, so the page needs a network connection on first
paint. Everything else, including all data, ships inside the file.

Run:  python src/build_index.py   (after build_dashboard_data.py)
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def main() -> None:
    payload_path = DOCS / "payload.json"
    template_path = DOCS / "index_dashboard_template.html"

    payload = payload_path.read_text()
    json.loads(payload)  # fail loudly rather than shipping a broken page

    html = template_path.read_text()
    generated = json.loads(payload)["generated"]
    html = html.replace("{{GENERATED}}", generated)
    html = html.replace("{{PAYLOAD}}", payload)

    if "{{" in html:
        raise ValueError("unfilled placeholders remain in index.html")

    out = ROOT / "index.html"
    out.write_text(html)
    kb = out.stat().st_size / 1024
    print(f"index.html written ({kb:,.0f} KB, data embedded, Plotly from CDN)")


if __name__ == "__main__":
    main()
