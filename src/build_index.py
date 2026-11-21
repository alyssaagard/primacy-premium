"""
build_index.py
Stage 5b. Results page.

Inserts docs/payload.json into docs/index_dashboard_template.html and
writes index.html at the repository root. The page loads Plotly from a
CDN; all data are embedded in the file.

Run: python src/build_index.py
"""

import json

from config import DOCS, ROOT


def main() -> None:
    payload_path = DOCS / "payload.json"
    template_path = DOCS / "index_dashboard_template.html"

    payload = payload_path.read_text()
    json.loads(payload)  # stop if the payload is not valid JSON

    html = template_path.read_text()
    generated = json.loads(payload)["generated"]
    html = html.replace("{{GENERATED}}", generated)
    html = html.replace("{{PAYLOAD}}", payload)

    if "{{" in html:
        raise ValueError("unfilled placeholders remain in index.html")

    out = ROOT / "index.html"
    out.write_text(html)
    kb = out.stat().st_size / 1024
    print(f"index.html written ({kb:,.0f} KB)")


if __name__ == "__main__":
    main()
