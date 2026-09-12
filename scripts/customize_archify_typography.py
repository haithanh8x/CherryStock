#!/usr/bin/env python3
"""Apply CherryStock typography overrides to an Archify-delivered HTML artifact.

Archify remains responsible for validation, geometry and rendering. This script only
injects presentation CSS after a successful deliver so CherryStock can use a
sans-serif font for architecture node/boundary titles while preserving Archify's
JetBrains Mono treatment for technical context and relationship text.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

STYLE_ID = "cherrystock-archify-typography"
STYLE_RE = re.compile(
    rf'<style\s+id=["\']{re.escape(STYLE_ID)}["\']>.*?</style>\s*',
    flags=re.IGNORECASE | re.DOTALL,
)


def _css_string(value: str) -> str:
    """Quote a CSS font-family token safely enough for local authored input."""
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def build_style(sans_font: str) -> str:
    sans = _css_string(sans_font)
    return f"""<style id=\"{STYLE_ID}\">
/* CherryStock presentation-only typography override.
   Archify geometry/validation remains authoritative for the rendered artifact. */
:root {{
  --cherrystock-arch-font-sans: {sans}, \"Segoe UI Variable\", \"Segoe UI\", Arial, sans-serif;
}}

/* Architecture names: human-readable sans-serif. */
svg [data-node-label],
svg [data-boundary-label] {{
  font-family: var(--cherrystock-arch-font-sans) !important;
  letter-spacing: -0.01em;
}}

/* Everything else intentionally inherits Archify's JetBrains Mono stack:
   context/sublabels, tags, relationship labels, source evidence and viewer details. */
</style>
"""


def customize(path: Path, sans_font: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"Archify HTML not found: {path}")

    html = path.read_text(encoding="utf-8")
    html = STYLE_RE.sub("", html)
    head_close = re.search(r"</head\s*>", html, flags=re.IGNORECASE)
    if not head_close:
        raise RuntimeError("Cannot inject typography: </head> was not found in the Archify HTML.")

    style = build_style(sans_font)
    html = html[: head_close.start()] + style + html[head_close.start() :]
    path.write_text(html, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Apply CherryStock typography to an Archify-delivered HTML artifact."
    )
    parser.add_argument("html", type=Path, help="Path to the delivered Archify HTML file")
    parser.add_argument(
        "--sans-font",
        default="Inter",
        help="Preferred sans-serif font for architecture node/boundary titles (default: Inter)",
    )
    args = parser.parse_args()

    customize(args.html, args.sans_font)
    print(f"CherryStock Archify typography applied: {args.html} (sans={args.sans_font})")
