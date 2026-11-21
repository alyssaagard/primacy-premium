"""
render.py
Template filling for the static pages.

A token has the form {{path.to.value|format}}. The path is resolved in
the payload; integer components index lists (negative values count from
the end). Formats: int (thousands separator), f0 to f3 (fixed decimals),
+f0 to +f3 (signed), or none. Tokens in upper case (for example
{{FIG1}}) are taken from the extra mapping. An unresolved token stops
the build.
"""

import re

TOKEN = re.compile(r"\{\{([A-Za-z0-9_.\- ,]+?)(?:\|(\+?[a-z0-9]+))?\}\}")


def resolve(data, path: str):
    cur = data
    for part in path.split("."):
        if isinstance(cur, list):
            cur = cur[int(part)]
        else:
            cur = cur[part]
    return cur


def fmt(value, spec: str | None) -> str:
    if spec is None:
        return str(value)
    if spec == "int":
        return f"{float(value):,.0f}"
    signed = spec.startswith("+")
    digits = int(spec.lstrip("+")[1:])
    return f"{float(value):{'+' if signed else ''}.{digits}f}"


def fill(template: str, payload: dict, extra: dict | None = None) -> str:
    extra = extra or {}

    def repl(m: re.Match) -> str:
        key, spec = m.group(1), m.group(2)
        if key in extra:
            return str(extra[key])
        try:
            return fmt(resolve(payload, key), spec)
        except (KeyError, IndexError, ValueError, TypeError) as exc:
            raise ValueError(f"unresolved template token: {key}") from exc

    out = TOKEN.sub(repl, template)
    if "{{" in out:
        raise ValueError("unfilled placeholders remain")
    return out
