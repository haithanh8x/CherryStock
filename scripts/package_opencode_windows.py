"""Build an allowlisted, credential-free Windows setup ZIP from this checkout."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = PROJECT_ROOT / "tools/opencode_windows"


def build(output: Path, config: Path) -> None:
    original = json.loads(config.read_text(encoding="utf-8"))
    provider = original.get("providers", original.get("provider", {}))["bedrock-local"]
    models = {}
    for key, model in provider["models"].items():
        models[key] = {
            "name": model.get("name", key),
            "capabilities": {"tools": model.get("capabilities", {}).get("tools", model.get("tool_call", True))},
            "limit": model["limit"],
        }
    # Reconstruct permitted fields; never copy passwords, headers, tokens or service state.
    portable = {
        "$schema": "https://opencode.ai/config.json",
        "providers": {"bedrock-local": {
            "name": "AWS Bedrock (local proxy)",
            "package": "@opencode/ai/providers/openai-compatible",
            "settings": {"baseURL": "http://127.0.0.1:8765/v1", "apiKey": "not-needed-for-local"},
            "models": models,
        }},
        "model": original["model"],
        "agents": {"title": {"model": original.get("small_model", "bedrock-local/global.anthropic.claude-haiku-5-5")}},
        "shell": "powershell.exe",
        "mcp": {"servers": {}},
    }
    for name in ("atlassian", "cloudflare", "figma", "drawio"):
        server = original["mcp"]["servers"][name]
        portable["mcp"]["servers"][name] = {"type": "remote", "url": server["url"]}
    portable["mcp"]["servers"]["github"] = {
        "type": "local",
        "command": ["__GITHUB_MCP_EXE__", "stdio", "--toolsets", "context,repos,issues,pull_requests,users", "--oauth-scopes", "repo,read:org"],
        "environment": {"GITHUB_PERSONAL_ACCESS_TOKEN": ""},
    }
    files: dict[str, bytes] = {}

    def add(path: Path, name: str) -> None:
        if path.is_symlink():
            raise ValueError(f"Refusing symlink: {path}")
        files[name] = path.read_bytes()

    for path in TEMPLATE.rglob("*"):
        if path.is_file() and path.suffix in (".ps1", ".md", ".txt"):
            add(path, path.relative_to(TEMPLATE).as_posix())
    for root in (".github/agents", ".github/instructions", ".github/skills", ".opencode/commands", "scripts/lib"):
        for path in (PROJECT_ROOT / root).rglob("*"):
            if path.is_file() and path.suffix in (".md", ".py", ".ps1", ".psm1", ".txt"):
                add(path, "snapshot/" + path.relative_to(PROJECT_ROOT).as_posix())
    for path in (PROJECT_ROOT / "docs").rglob("*.md"):
        add(path, "snapshot/" + path.relative_to(PROJECT_ROOT).as_posix())
    for name in ("AGENTS.md", "opencode.jsonc", ".github/copilot-instructions.md", "scripts/install_drawio_skill.ps1",
                 "src/llm/bedrock_http_proxy.py", "src/llm/llm_client.py"):
        add(PROJECT_ROOT / name, "snapshot/" + name)
    files["opencode.windows.template.json"] = (json.dumps(portable, indent=2, ensure_ascii=False) + "\n").encode()
    manifest = {
        "format": 1,
        "description": "Setup/harness snapshot, not a full CherryStock clone or offline installer",
        "files": {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())},
        "excluded": ["AWS config/credentials/cache", "OAuth tokens", "OpenCode database/service.json/password", ".env", "private keys/certificates", "Mac binaries/venvs", "DuckDB/data", "Draw.io backup files"],
    }
    files["manifest.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    # Never overwrite a previous handoff archive.
    with zipfile.ZipFile(output, "x", zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            archive.writestr("CherryStock-OpenCode-Windows/" + name, data)
    print(f"Created {output} ({output.stat().st_size:,} bytes; {len(files)} files)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--config", type=Path, default=Path.home() / ".config/opencode/opencode.json")
    args = parser.parse_args()
    build(args.output.resolve(), args.config.expanduser().resolve())
