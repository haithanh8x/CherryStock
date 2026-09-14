#!/usr/bin/env python3
"""Enrich the CherryStock ADLC Archify Semantic Passport with agent execution detail.

Archify remains authoritative for typed workflow validation, geometry, relationships
and the base standalone viewer. This deterministic post-processing layer reads a
CherryStock-owned sidecar and adds details-on-demand inside the existing Semantic
Passport popup. Generated HTML remains presentation output and must not be edited by
hand.
"""

from __future__ import annotations

import argparse
import html as html_lib
import json
import re
from pathlib import Path

STYLE_ID = "cherrystock-agent-passport-style"
SCRIPT_ID = "cherrystock-agent-passport-script"
PANEL_ID = "cherrystock-agent-passport-detail"

STYLE_RE = re.compile(
    rf'<style\s+id=["\']{re.escape(STYLE_ID)}["\']>.*?</style>\s*',
    flags=re.IGNORECASE | re.DOTALL,
)
SCRIPT_RE = re.compile(
    rf'<script\s+id=["\']{re.escape(SCRIPT_ID)}["\']>.*?</script>\s*',
    flags=re.IGNORECASE | re.DOTALL,
)


def load_details(path: Path) -> dict[str, dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError("Agent passport sidecar must use schema_version=1")
    nodes = data.get("nodes")
    if not isinstance(nodes, dict) or not nodes:
        raise ValueError("Agent passport sidecar must contain a non-empty nodes object")

    for node_id, detail in nodes.items():
        if not isinstance(node_id, str) or not node_id.strip():
            raise ValueError("Agent passport node ids must be non-empty strings")
        if not isinstance(detail, dict):
            raise ValueError(f"Passport detail for {node_id!r} must be an object")
        title = detail.get("title")
        items = detail.get("items")
        if not isinstance(title, str) or not title.strip():
            raise ValueError(f"Passport detail for {node_id!r} requires a title")
        if not isinstance(items, list) or not items:
            raise ValueError(f"Passport detail for {node_id!r} requires non-empty items")
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                raise ValueError(f"Passport item {node_id}[{index}] must be an object")
            if not isinstance(item.get("label"), str) or not item["label"].strip():
                raise ValueError(f"Passport item {node_id}[{index}] requires label")
            if not isinstance(item.get("text"), str) or not item["text"].strip():
                raise ValueError(f"Passport item {node_id}[{index}] requires text")
    return nodes


def build_style() -> str:
    return f"""<style id=\"{STYLE_ID}\">
/* CherryStock agent execution detail inside Archify Semantic Passport. */
#{PANEL_ID} {{
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid color-mix(in srgb, var(--toolbar-border) 72%, transparent);
}}
#{PANEL_ID}[hidden] {{ display: none !important; }}
#{PANEL_ID} .cherrystock-passport-kicker {{
  display: block;
  margin-bottom: 5px;
  color: var(--frontend-stroke);
  font: 700 9px/1.2 \"JetBrains Mono\", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}}
#{PANEL_ID} .cherrystock-passport-title {{
  margin: 0 0 9px;
  color: var(--text-primary, var(--toolbar-text));
  font: 700 12px/1.35 var(--cherrystock-arch-font-sans, \"Inter\", \"Segoe UI\", Arial, sans-serif);
}}
#{PANEL_ID} ul {{
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 7px;
}}
#{PANEL_ID} li {{
  position: relative;
  padding-left: 13px;
  color: var(--toolbar-text);
  font: 10px/1.48 \"JetBrains Mono\", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}}
#{PANEL_ID} li::before {{
  content: \"•\";
  position: absolute;
  left: 0;
  color: var(--frontend-stroke);
}}
#{PANEL_ID} .cherrystock-passport-label {{
  color: var(--text-primary, var(--toolbar-text));
  font-weight: 700;
}}
</style>
"""


def build_script(nodes: dict[str, dict]) -> str:
    payload = json.dumps(nodes, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return f"""<script id=\"{SCRIPT_ID}\">
(function () {{
  var details = {payload};
  var chip = document.getElementById('focus-chip');
  var focusId = document.getElementById('focus-id');
  if (!chip || !focusId) return;

  var panel = document.getElementById('{PANEL_ID}');
  if (!panel) {{
    panel = document.createElement('section');
    panel.id = '{PANEL_ID}';
    panel.hidden = true;
    panel.setAttribute('aria-label', 'CherryStock agent execution detail');
    var anchor = document.getElementById('focus-reach') || document.getElementById('relationship-lens-list');
    if (anchor && anchor.parentNode) anchor.parentNode.insertBefore(panel, anchor);
    else chip.appendChild(panel);
  }}

  function appendText(tag, className, text) {{
    var el = document.createElement(tag);
    if (className) el.className = className;
    el.textContent = text;
    return el;
  }}

  function renderAgentDetail() {{
    var id = (focusId.textContent || '').trim();
    var detail = details[id];
    panel.replaceChildren();
    if (!detail || chip.hidden) {{
      panel.hidden = true;
      return;
    }}

    panel.appendChild(appendText('span', 'cherrystock-passport-kicker', 'Agent execution'));
    panel.appendChild(appendText('div', 'cherrystock-passport-title', detail.title));

    var list = document.createElement('ul');
    detail.items.forEach(function (item) {{
      var row = document.createElement('li');
      var label = appendText('span', 'cherrystock-passport-label', item.label + ': ');
      row.appendChild(label);
      row.appendChild(document.createTextNode(item.text));
      list.appendChild(row);
    }});
    panel.appendChild(list);
    panel.hidden = false;
  }}

  new MutationObserver(renderAgentDetail).observe(focusId, {{
    childList: true,
    subtree: true,
    characterData: true
  }});
  new MutationObserver(renderAgentDetail).observe(chip, {{
    attributes: true,
    attributeFilter: ['hidden']
  }});
  document.addEventListener('click', function () {{ window.setTimeout(renderAgentDetail, 0); }}, true);
  document.addEventListener('keyup', function () {{ window.setTimeout(renderAgentDetail, 0); }}, true);
  renderAgentDetail();
}})();
</script>
"""


def enrich(html_path: Path, details_path: Path) -> None:
    if not html_path.is_file():
        raise FileNotFoundError(f"Archify HTML not found: {html_path}")
    if not details_path.is_file():
        raise FileNotFoundError(f"Agent passport sidecar not found: {details_path}")

    nodes = load_details(details_path)
    html = html_path.read_text(encoding="utf-8")

    missing = [
        node_id
        for node_id in nodes
        if f'data-node-id="{html_lib.escape(node_id, quote=True)}"' not in html
    ]
    if missing:
        raise RuntimeError(
            "Agent passport sidecar references node ids not present in delivered HTML: "
            + ", ".join(sorted(missing))
        )

    html = STYLE_RE.sub("", html)
    html = SCRIPT_RE.sub("", html)

    head_close = re.search(r"</head\s*>", html, flags=re.IGNORECASE)
    body_close = re.search(r"</body\s*>", html, flags=re.IGNORECASE)
    if not head_close or not body_close:
        raise RuntimeError("Cannot enrich agent passport: </head> or </body> was not found")

    style = build_style()
    html = html[: head_close.start()] + style + html[head_close.start() :]

    body_close = re.search(r"</body\s*>", html, flags=re.IGNORECASE)
    script = build_script(nodes)
    html = html[: body_close.start()] + script + html[body_close.start() :]
    html_path.write_text(html, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Add CherryStock agent execution detail to the Archify Semantic Passport popup."
    )
    parser.add_argument("html", type=Path, help="Delivered Archify HTML file")
    parser.add_argument("details", type=Path, help="CherryStock agent passport sidecar JSON")
    args = parser.parse_args()

    enrich(args.html, args.details)
    count = len(load_details(args.details))
    print(f"CherryStock agent passport enriched: {args.html} ({count} detailed nodes)")
