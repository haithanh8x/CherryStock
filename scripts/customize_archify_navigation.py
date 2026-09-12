#!/usr/bin/env python3
"""Inject CherryStock drill-down navigation into Archify-delivered HTML.

Archify owns diagram validation/rendering. This post-processor adds presentation-only
navigation between generated architecture pages using stable Archify data-node-id
attributes. The mapping is externalized in JSON so regeneration remains deterministic.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

STYLE_ID = "cherrystock-archify-navigation-style"
SCRIPT_ID = "cherrystock-archify-navigation-script"
BACK_ID = "cherrystock-archify-back-link"

STYLE_RE = re.compile(
    rf'<style\s+id=["\']{re.escape(STYLE_ID)}["\']>.*?</style>\s*',
    flags=re.IGNORECASE | re.DOTALL,
)
SCRIPT_RE = re.compile(
    rf'<script\s+id=["\']{re.escape(SCRIPT_ID)}["\']>.*?</script>\s*',
    flags=re.IGNORECASE | re.DOTALL,
)
BACK_RE = re.compile(
    rf'<a\s+id=["\']{re.escape(BACK_ID)}["\'].*?</a>\s*',
    flags=re.IGNORECASE | re.DOTALL,
)


def build_style() -> str:
    return f"""<style id=\"{STYLE_ID}\">
/* CherryStock Archify drill-down navigation. */
svg .cherrystock-drilldown-node {{
  cursor: zoom-in;
}}

svg .cherrystock-drilldown-node [data-node-label] {{
  text-decoration: underline dotted;
  text-underline-offset: 3px;
}}

svg .cherrystock-drilldown-node:hover {{
  filter: drop-shadow(0 0 5px rgba(56, 189, 248, 0.45));
}}

#{BACK_ID} {{
  position: fixed;
  left: 16px;
  bottom: 16px;
  z-index: 9999;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  border: 1px solid rgba(148, 163, 184, 0.35);
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.90);
  color: #e2e8f0;
  text-decoration: none;
  backdrop-filter: blur(8px);
  font: 12px/1.2 \"JetBrains Mono\", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  box-shadow: 0 8px 24px rgba(0,0,0,0.22);
}}

#{BACK_ID}:hover {{
  border-color: rgba(56, 189, 248, 0.65);
}}

html[data-theme=\"light\"] #{BACK_ID} {{
  background: rgba(255,255,255,0.94);
  color: #0f172a;
  border-color: rgba(100,116,139,0.30);
}}
</style>
"""


def build_script(page_config: dict) -> str:
    payload = json.dumps(page_config.get("nodes", {}), ensure_ascii=False)
    return f"""<script id=\"{SCRIPT_ID}\">
(function () {{
  var nodes = {payload};

  function navigate(target) {{
    if (!target) return;
    window.location.href = target;
  }}

  Object.keys(nodes).forEach(function (nodeId) {{
    var cfg = nodes[nodeId] || {{}};
    var candidates = document.querySelectorAll('[data-node-id="' + nodeId + '"]');
    if (!candidates.length) return;

    candidates.forEach(function (node) {{
      node.classList.add('cherrystock-drilldown-node');
      node.setAttribute('tabindex', '0');
      node.setAttribute('role', 'link');
      node.setAttribute('aria-label', cfg.label || ('Open ' + nodeId + ' detail'));
      node.setAttribute('data-drilldown-target', cfg.target || '');

      var title = node.querySelector(':scope > title[data-cherrystock-drilldown-title]');
      if (!title) {{
        title = document.createElementNS('http://www.w3.org/2000/svg', 'title');
        title.setAttribute('data-cherrystock-drilldown-title', 'true');
        node.insertBefore(title, node.firstChild);
      }}
      title.textContent = (cfg.label || ('Open ' + nodeId + ' detail')) +
        ((cfg.interaction || 'double-click') === 'click' ? ' — click' : ' — double-click');

      var interaction = cfg.interaction || 'double-click';
      if (interaction === 'click') {{
        node.addEventListener('click', function (event) {{
          event.preventDefault();
          event.stopPropagation();
          navigate(cfg.target);
        }});
      }} else {{
        node.addEventListener('dblclick', function (event) {{
          event.preventDefault();
          event.stopPropagation();
          navigate(cfg.target);
        }});
      }}

      node.addEventListener('keydown', function (event) {{
        if (event.key === 'Enter') {{
          event.preventDefault();
          event.stopPropagation();
          navigate(cfg.target);
        }}
      }});
    }});
  }});
}})();
</script>
"""


def build_back(back_config: dict | None) -> str:
    if not back_config:
        return ""
    target = str(back_config.get("target", "")).replace('"', "&quot;")
    label = str(back_config.get("label", "← Back")).replace("<", "&lt;").replace(">", "&gt;")
    return f'<a id="{BACK_ID}" href="{target}" aria-label="{label}">{label}</a>\n'


def customize(html_path: Path, config_path: Path) -> None:
    if not html_path.is_file():
        raise FileNotFoundError(f"Archify HTML not found: {html_path}")
    if not config_path.is_file():
        raise FileNotFoundError(f"Archify navigation config not found: {config_path}")

    config = json.loads(config_path.read_text(encoding="utf-8"))
    pages = config.get("pages", {})
    page_config = pages.get(html_path.name)
    if not page_config:
        print(f"No CherryStock Archify navigation mapping for {html_path.name}; skipped.")
        return

    html = html_path.read_text(encoding="utf-8")
    html = STYLE_RE.sub("", html)
    html = SCRIPT_RE.sub("", html)
    html = BACK_RE.sub("", html)

    head_close = re.search(r"</head\s*>", html, flags=re.IGNORECASE)
    body_close = re.search(r"</body\s*>", html, flags=re.IGNORECASE)
    if not head_close or not body_close:
        raise RuntimeError("Cannot inject navigation: </head> or </body> was not found in the Archify HTML.")

    style = build_style()
    html = html[: head_close.start()] + style + html[head_close.start() :]

    body_close = re.search(r"</body\s*>", html, flags=re.IGNORECASE)
    navigation = build_back(page_config.get("back")) + build_script(page_config)
    html = html[: body_close.start()] + navigation + html[body_close.start() :]
    html_path.write_text(html, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Apply CherryStock drill-down navigation to an Archify HTML artifact."
    )
    parser.add_argument("html", type=Path, help="Path to delivered Archify HTML")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("docs/architecture/diagrams/cherrystock-archify-navigation.json"),
        help="Navigation mapping JSON",
    )
    args = parser.parse_args()

    customize(args.html, args.config)
    print(f"CherryStock Archify navigation applied: {args.html}")
