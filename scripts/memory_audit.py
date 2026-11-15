#!/usr/bin/env python3
"""Read-only auditor for the cherrystock-memory MCP knowledge graph (ADR-019).

Checks naming, observation headers, forbidden content, stale/missing repository
pointers, relation integrity and retention. It never modifies the memory file;
fixes are applied through the memory MCP tools.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

DEFAULT_MEMORY_FILE = "~/.config/opencode/cherrystock-memory.jsonl"
ENTITY_TYPES = ("pointer", "task", "attempt", "lesson", "preference")
RELATION_TYPES = ("references", "attempt_of", "derived_from")
AGENTS = ("router", "ba", "sa", "dev", "test", "indicators", "chart", "user")
STATUSES = ("active", "stale", "promoted", "closed", "failed")
NON_REPO_SOURCES = ("user", "session")
MAX_OBSERVATION_LENGTH = 400
RETENTION_DAYS = {"task": 7, "attempt": 30, "lesson": 14}

NAME_RE = re.compile(r"^(?P<type>[a-z]+):[a-z0-9][a-z0-9._-]*$")
HEADER_RE = re.compile(
    r"^\[src=(?P<src>[^\]]+)\]"
    r"(?:\[sha=(?P<sha>[0-9a-f]{4,40})\])?"
    r"\[date=(?P<date>\d{4}-\d{2}-\d{2})\]"
    r"\[agent=(?P<agent>[a-z]+)\]"
    r"\[status=(?P<status>[a-z]+)\]\s+(?P<text>\S.*)$",
    flags=re.DOTALL,
)
SECRET_PATTERNS = (
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{30,}"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)\b(password|passwd|secret|api[_-]?key|token)\s*[=:]\s*\S{6,}"),
)
PERMISSION_RE = re.compile(
    r"(?i)\b(allow(?:ed)?|authori[sz]ed?|permission|approved?)\b.{0,40}\b(push|commit|merge|local[- ]?write|write[- ]?location)\b"
    r"|\b(push|commit|merge)\b.{0,20}\b(allowed|authori[sz]ed|approved)\b"
)


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    entity: str
    detail: str


def load_graph(path: Path) -> tuple[list[dict], list[dict], list[str]]:
    entities: list[dict] = []
    relations: list[dict] = []
    unreadable: list[str] = []
    if not path.exists():
        return entities, relations, unreadable
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            unreadable.append(line[:80])
            continue
        kind = record.get("type") if isinstance(record, dict) else None
        if kind == "entity":
            entities.append(record)
        elif kind == "relation":
            relations.append(record)
        else:
            unreadable.append(line[:80])
    return entities, relations, unreadable


def git_last_sha(repo_root: Path, rel_path: str) -> str | None:
    result = subprocess.run(
        ["git", "log", "-1", "--format=%h", "--", rel_path],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    sha = result.stdout.strip()
    return sha or None


def _parse_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _repo_path(src: str) -> str | None:
    if src in NON_REPO_SOURCES:
        return None
    return src.split("#", 1)[0].strip()


def audit(
    entities: list[dict],
    relations: list[dict],
    repo_root: Path,
    today: date,
    git_sha: Callable[[Path, str], str | None] = git_last_sha,
) -> list[Finding]:
    findings: list[Finding] = []
    sha_cache: dict[str, str | None] = {}
    names = {entity.get("name") for entity in entities}

    def add(severity: str, code: str, entity: str, detail: str) -> None:
        findings.append(Finding(severity, code, entity, detail))

    for entity in entities:
        name = str(entity.get("name", ""))
        entity_type = entity.get("entityType")
        match = NAME_RE.match(name)
        if not match or match["type"] not in ENTITY_TYPES:
            add("error", "bad_name", name, f"name must be <{'|'.join(ENTITY_TYPES)}>:<kebab-key>")
        elif entity_type != match["type"]:
            add("error", "bad_name", name, f"entityType {entity_type!r} must equal {match['type']!r}")

        statuses: list[str] = []
        dates: list[date] = []
        for index, observation in enumerate(entity.get("observations", [])):
            where = f"{name}[{index}]"
            for pattern in SECRET_PATTERNS:
                if pattern.search(observation):
                    add("error", "secret", where, "possible credential/secret; delete this observation")
                    break
            if PERMISSION_RE.search(observation):
                add("error", "forbidden_permission", where, "permissions are never remembered (ADR-019)")
            if len(observation) > MAX_OBSERVATION_LENGTH:
                add("warning", "too_long", where, f"{len(observation)} > {MAX_OBSERVATION_LENGTH} characters")

            header = HEADER_RE.match(observation)
            if not header:
                add("error", "bad_header", where, "missing [src][sha?][date][agent][status] header")
                continue
            if header["agent"] not in AGENTS:
                add("error", "bad_header", where, f"unknown agent {header['agent']!r}")
            if header["status"] not in STATUSES:
                add("error", "bad_header", where, f"unknown status {header['status']!r}")
            observed = _parse_date(header["date"])
            if observed is None:
                add("error", "bad_header", where, f"invalid date {header['date']!r}")
            else:
                dates.append(observed)
            statuses.append(header["status"])

            rel_path = _repo_path(header["src"])
            if rel_path is None:
                continue
            if not (repo_root / rel_path).exists():
                add("warning", "missing_path", where, f"{rel_path} does not exist")
                continue
            if not header["sha"]:
                add("error", "bad_header", where, "sha is required for a repository src")
                continue
            if header["status"] != "active":
                continue
            if rel_path not in sha_cache:
                sha_cache[rel_path] = git_sha(repo_root, rel_path)
            current = sha_cache[rel_path]
            recorded = header["sha"]
            if current and not (current.startswith(recorded) or recorded.startswith(current)):
                add("warning", "stale_pointer", where, f"{rel_path} changed: recorded {recorded}, current {current}")

        limit = RETENTION_DAYS.get(str(entity_type))
        if limit and dates:
            age = (today - max(dates)).days if entity_type != "lesson" else (today - min(dates)).days
            latest_status = statuses[-1] if statuses else "active"
            expired = (
                (entity_type == "task" and latest_status == "closed" and age > limit)
                or (entity_type == "attempt" and age > limit)
                or (entity_type == "lesson" and latest_status == "active" and age > limit)
            )
            if expired:
                add("warning", "expired", name, f"{entity_type} older than {limit} days ({age}); promote or delete")

    for relation in relations:
        label = f"{relation.get('from')} -{relation.get('relationType')}-> {relation.get('to')}"
        if relation.get("relationType") not in RELATION_TYPES:
            add("error", "bad_relation", label, f"relationType must be one of {RELATION_TYPES}")
        for end in ("from", "to"):
            if relation.get(end) not in names:
                add("error", "bad_relation", label, f"{end} endpoint does not exist")
    return findings


def _default_memory_file() -> Path:
    return Path(os.environ.get("MEMORY_FILE_PATH") or DEFAULT_MEMORY_FILE).expanduser()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--memory-file", type=Path, default=None)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--today", type=date.fromisoformat, default=None, help="YYYY-MM-DD (testing)")
    parser.add_argument("--json", action="store_true", help="emit machine-readable findings")
    args = parser.parse_args(argv)

    memory_file = (args.memory_file or _default_memory_file()).expanduser()
    repo_root = args.repo_root.resolve()
    entities, relations, unreadable = load_graph(memory_file)
    findings = audit(entities, relations, repo_root, args.today or date.today())
    findings.extend(Finding("error", "unreadable", "-", line) for line in unreadable)
    errors = sum(1 for finding in findings if finding.severity == "error")

    summary = {
        "memory_file": str(memory_file),
        "entities": len(entities),
        "relations": len(relations),
        "errors": errors,
        "warnings": len(findings) - errors,
    }
    if args.json:
        print(json.dumps({"summary": summary, "findings": [asdict(f) for f in findings]}, indent=2))
    else:
        for finding in findings:
            print(f"{finding.severity.upper():7} {finding.code:20} {finding.entity}: {finding.detail}")
        print(
            f"memory audit: {summary['entities']} entities, {summary['relations']} relations, "
            f"{errors} errors, {summary['warnings']} warnings ({memory_file})"
        )
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
