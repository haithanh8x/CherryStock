"""Restricted MCP server for CherryStock Git auto-sync.

This server intentionally exposes one mutation tool only: ``git_auto_sync``.
It does not expose an arbitrary shell. The tool executes the repository-owned
``scripts/git_auto_sync.ps1`` and returns bounded process output.

Run:
    python -m src.mcp_server.git_sync_mcp --transport http --port 8080
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _PROJECT_ROOT / "scripts" / "git_auto_sync.ps1"
_MAX_OUTPUT_CHARS = 40_000
_DEFAULT_TIMEOUT_SECONDS = 180

try:
    from mcp.server import MCPServer
    from mcp.server.transport_security import TransportSecuritySettings
    _MCP_SDK_V2 = True
except ImportError:  # pragma: no cover - MCP SDK 1.x compatibility
    from mcp.server.fastmcp import FastMCP as MCPServer
    TransportSecuritySettings = None  # type: ignore[assignment,misc]
    _MCP_SDK_V2 = False


def _create_mcp_server() -> Any:
    if _MCP_SDK_V2:
        return MCPServer("cherrystock-git-sync")
    return MCPServer(
        "cherrystock-git-sync",
        host="127.0.0.1",
        port=8080,
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True,
    )


mcp = _create_mcp_server()


def _bounded(value: str) -> str:
    if len(value) <= _MAX_OUTPUT_CHARS:
        return value
    return value[-_MAX_OUTPUT_CHARS:]


def _transport_security() -> Any:
    """Build an explicit Host allowlist for localhost and the configured tunnel."""
    if TransportSecuritySettings is None:
        return None

    allowed_hosts = ["127.0.0.1:*", "localhost:*", "[::1]:*"]
    public_host = os.getenv("CHERRYSTOCK_GIT_MCP_PUBLIC_HOST", "").strip()
    if public_host:
        # Accept either a hostname or an https:// URL from configuration.
        public_host = public_host.removeprefix("https://").removeprefix("http://").split("/", 1)[0]
        public_host = public_host.split(":", 1)[0]
        allowed_hosts.extend([public_host, f"{public_host}:*"])

    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=allowed_hosts,
        allowed_origins=[
            "http://127.0.0.1:*",
            "http://localhost:*",
            "http://[::1]:*",
        ],
    )


@mcp.tool()
def health_check() -> dict[str, Any]:
    """Check that the Git sync script exists and the MCP server is ready."""
    return {
        "status": "ok" if _SCRIPT.is_file() else "error",
        "repository": str(_PROJECT_ROOT),
        "script": str(_SCRIPT),
        "script_exists": _SCRIPT.is_file(),
    }


@mcp.tool()
def git_auto_sync(timeout_seconds: int = _DEFAULT_TIMEOUT_SECONDS) -> dict[str, Any]:
    """Run CherryStock's repository-owned scripts/git_auto_sync.ps1.

    This is intentionally a fixed command; callers cannot supply a shell
    command or alternate script path.
    """
    if not _SCRIPT.is_file():
        raise FileNotFoundError(f"Git auto-sync script not found: {_SCRIPT}")
    if not 10 <= timeout_seconds <= 600:
        raise ValueError("timeout_seconds must be between 10 and 600")

    started = time.monotonic()
    command = [
        "powershell.exe",
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(_SCRIPT),
    ]

    try:
        result = subprocess.run(
            command,
            cwd=str(_PROJECT_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "status": "timeout",
            "exit_code": None,
            "duration_ms": round((time.monotonic() - started) * 1000),
            "stdout": _bounded(exc.stdout or "") if isinstance(exc.stdout, str) else "",
            "stderr": _bounded(exc.stderr or "") if isinstance(exc.stderr, str) else "",
        }

    return {
        "status": "ok" if result.returncode == 0 else "error",
        "exit_code": result.returncode,
        "duration_ms": round((time.monotonic() - started) * 1000),
        "stdout": _bounded(result.stdout),
        "stderr": _bounded(result.stderr),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CherryStock Git Sync MCP server")
    parser.add_argument("--transport", choices=("stdio", "http"), default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)
    if args.transport == "stdio":
        mcp.run(transport="stdio")
        return
    if not 1 <= args.port <= 65535:
        raise ValueError("--port must be between 1 and 65535")
    if args.host not in {"127.0.0.1", "localhost"}:
        raise ValueError("Git Sync MCP must bind to localhost; expose it through a secured tunnel")

    if _MCP_SDK_V2:
        mcp.run(
            transport="streamable-http",
            host=args.host,
            port=args.port,
            streamable_http_path="/mcp",
            stateless_http=True,
            json_response=True,
            transport_security=_transport_security(),
        )
        return

    mcp.settings.host = args.host
    mcp.settings.port = args.port
    mcp.settings.streamable_http_path = "/mcp"
    mcp.settings.stateless_http = True
    mcp.settings.json_response = True
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
