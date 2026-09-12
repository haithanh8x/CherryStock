#!/usr/bin/env python3
"""Apply CherryStock typography overrides to an Archify-delivered HTML artifact.

Archify remains responsible for validation, geometry and rendering. This script only
injects presentation CSS and a small runtime font picker after a successful deliver.
Node/boundary titles can switch fonts in-browser while technical context and
relationship text keep Archify's JetBrains Mono treatment.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

STYLE_ID = "cherrystock-archify-typography"
CONTROL_ID = "cherrystock-archify-font-picker"
SCRIPT_ID = "cherrystock-archify-font-picker-script"

STYLE_RE = re.compile(
    rf'<style\s+id=["\']{re.escape(STYLE_ID)}["\']>.*?</style>\s*',
    flags=re.IGNORECASE | re.DOTALL,
)
CONTROL_RE = re.compile(
    rf'<div\s+id=["\']{re.escape(CONTROL_ID)}["\'].*?</div>\s*',
    flags=re.IGNORECASE | re.DOTALL,
)
SCRIPT_RE = re.compile(
    rf'<script\s+id=["\']{re.escape(SCRIPT_ID)}["\']>.*?</script>\s*',
    flags=re.IGNORECASE | re.DOTALL,
)


def _css_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def build_style(sans_font: str) -> str:
    sans = _css_string(sans_font)
    return f"""<style id=\"{STYLE_ID}\">
/* CherryStock presentation-only typography override. */
:root {{
  --cherrystock-arch-font-sans: {sans}, \"Segoe UI Variable\", \"Segoe UI\", Arial, sans-serif;
}}

svg [data-node-label],
svg [data-boundary-label] {{
  font-family: var(--cherrystock-arch-font-sans) !important;
  letter-spacing: -0.01em;
}}

#{CONTROL_ID} {{
  position: fixed;
  right: 16px;
  bottom: 16px;
  z-index: 9999;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border: 1px solid rgba(148, 163, 184, 0.35);
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.90);
  color: #e2e8f0;
  backdrop-filter: blur(8px);
  font: 12px/1.2 \"JetBrains Mono\", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  box-shadow: 0 8px 24px rgba(0,0,0,0.22);
}}

#{CONTROL_ID} label {{ opacity: 0.78; }}
#{CONTROL_ID} select {{
  min-width: 142px;
  padding: 5px 8px;
  border: 1px solid rgba(148, 163, 184, 0.40);
  border-radius: 6px;
  background: #111827;
  color: #f8fafc;
  font: inherit;
}}

html[data-theme=\"light\"] #{CONTROL_ID} {{
  background: rgba(255,255,255,0.94);
  color: #0f172a;
  border-color: rgba(100,116,139,0.30);
}}
html[data-theme=\"light\"] #{CONTROL_ID} select {{
  background: #ffffff;
  color: #0f172a;
}}
</style>
"""


def build_control(default_font: str) -> str:
    options = [
        "Inter",
        "Segoe UI",
        "IBM Plex Sans",
        "Arial",
        "system-ui",
        "JetBrains Mono",
    ]
    rendered = []
    for name in options:
        selected = " selected" if name == default_font else ""
        rendered.append(f'<option value="{name}"{selected}>{name}</option>')
    return (
        f'<div id="{CONTROL_ID}" aria-label="CherryStock architecture font picker">'
        '<label for="cherrystock-arch-font-select">Font</label>'
        '<select id="cherrystock-arch-font-select">'
        + "".join(rendered)
        + '</select></div>\n'
    )


def build_script(default_font: str) -> str:
    safe_default = default_font.replace("\\", "\\\\").replace("'", "\\'")
    return f"""<script id=\"{SCRIPT_ID}\">
(function () {{
  var key = 'cherrystock-arch-font';
  var select = document.getElementById('cherrystock-arch-font-select');
  if (!select) return;
  var stacks = {{
    'Inter': '\"Inter\", \"Segoe UI Variable\", \"Segoe UI\", Arial, sans-serif',
    'Segoe UI': '\"Segoe UI Variable\", \"Segoe UI\", Arial, sans-serif',
    'IBM Plex Sans': '\"IBM Plex Sans\", \"Segoe UI\", Arial, sans-serif',
    'Arial': 'Arial, sans-serif',
    'system-ui': 'system-ui, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif',
    'JetBrains Mono': '\"JetBrains Mono\", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace'
  }};
  function apply(name) {{
    var stack = stacks[name] || stacks['Inter'];
    document.documentElement.style.setProperty('--cherrystock-arch-font-sans', stack);
    select.value = stacks[name] ? name : '{safe_default}';
  }}
  var saved = null;
  try {{ saved = localStorage.getItem(key); }} catch (_) {{}}
  apply(saved || '{safe_default}');
  select.addEventListener('change', function () {{
    apply(select.value);
    try {{ localStorage.setItem(key, select.value); }} catch (_) {{}}
  }});
}})();
</script>
"""


def customize(path: Path, sans_font: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"Archify HTML not found: {path}")

    html = path.read_text(encoding="utf-8")
    html = STYLE_RE.sub("", html)
    html = CONTROL_RE.sub("", html)
    html = SCRIPT_RE.sub("", html)

    head_close = re.search(r"</head\s*>", html, flags=re.IGNORECASE)
    body_close = re.search(r"</body\s*>", html, flags=re.IGNORECASE)
    if not head_close or not body_close:
        raise RuntimeError("Cannot inject typography: </head> or </body> was not found in the Archify HTML.")

    style = build_style(sans_font)
    html = html[: head_close.start()] + style + html[head_close.start() :]

    body_close = re.search(r"</body\s*>", html, flags=re.IGNORECASE)
    control_and_script = build_control(sans_font) + build_script(sans_font)
    html = html[: body_close.start()] + control_and_script + html[body_close.start() :]
    path.write_text(html, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Apply CherryStock typography and runtime font picker to an Archify HTML artifact."
    )
    parser.add_argument("html", type=Path, help="Path to the delivered Archify HTML file")
    parser.add_argument(
        "--sans-font",
        default="Inter",
        help="Default font for architecture node/boundary titles (default: Inter)",
    )
    args = parser.parse_args()

    customize(args.html, args.sans_font)
    print(
        f"CherryStock Archify typography applied: {args.html} "
        f"(default={args.sans_font}, runtime font picker enabled)"
    )
