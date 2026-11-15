import json
from datetime import date

from scripts import memory_audit as audit_mod

TODAY = date(2026, 11, 15)


def _header(src="user", sha=None, day="2026-11-15", agent="dev", status="active", text="fact"):
    sha_part = f"[sha={sha}]" if sha else ""
    return f"[src={src}]{sha_part}[date={day}][agent={agent}][status={status}] {text}"


def _entity(name, entity_type, *observations):
    return {"type": "entity", "name": name, "entityType": entity_type, "observations": list(observations)}


def _codes(findings):
    return {finding.code for finding in findings}


def _run(entities, relations=(), tmp_path=None, sha="abc1234"):
    return audit_mod.audit(list(entities), list(relations), tmp_path, TODAY, git_sha=lambda root, path: sha)


def test_valid_graph_has_no_findings(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "a.md").write_text("x", encoding="utf-8")
    entities = [
        _entity("task:req-0040", "task", _header(text="objective X; owner dev; gate none")),
        _entity("pointer:a-topic", "pointer", _header(src="docs/a.md#intro", sha="abc1234", agent="router")),
    ]
    relations = [{"type": "relation", "from": "task:req-0040", "to": "pointer:a-topic", "relationType": "references"}]
    assert _run(entities, relations, tmp_path) == []


def test_naming_header_and_relation_errors(tmp_path):
    entities = [
        _entity("Task REQ", "task", _header()),
        _entity("lesson:x", "task", "no header here"),
        _entity("task:y", "task", _header(agent="ghost", status="maybe")),
    ]
    relations = [{"type": "relation", "from": "task:y", "to": "task:missing", "relationType": "likes"}]
    codes = _codes(_run(entities, relations, tmp_path))
    assert {"bad_name", "bad_header", "bad_relation"} <= codes


def test_secret_and_permission_are_errors(tmp_path):
    entities = [
        _entity("task:a", "task", _header(text="token=ghp_abcdefghijklmnopqrstuvwxyz0123456789")),
        _entity("preference:git", "preference", _header(agent="user", text="user allowed push to main")),
    ]
    findings = _run(entities, tmp_path=tmp_path)
    assert {"secret", "forbidden_permission"} <= _codes(findings)
    assert all(f.severity == "error" for f in findings if f.code in {"secret", "forbidden_permission"})


def test_repository_pointer_staleness_and_missing_path(tmp_path):
    (tmp_path / "docs.md").write_text("x", encoding="utf-8")
    entities = [
        _entity("pointer:stale", "pointer", _header(src="docs.md", sha="1111111")),
        _entity("pointer:gone", "pointer", _header(src="nope.md", sha="1111111")),
        _entity("pointer:nosha", "pointer", _header(src="docs.md")),
    ]
    codes = [f.code for f in _run(entities, tmp_path=tmp_path, sha="2222222")]
    assert codes.count("stale_pointer") == 1
    assert "missing_path" in codes
    assert "bad_header" in codes


def test_retention(tmp_path):
    entities = [
        _entity("task:old", "task", _header(day="2026-10-01"), _header(day="2026-10-02", status="closed")),
        _entity("task:open", "task", _header(day="2026-10-01")),
        _entity("attempt:old-1", "attempt", _header(day="2026-09-01", status="failed")),
        _entity("lesson:old", "lesson", _header(day="2026-10-01")),
        _entity("lesson:done", "lesson", _header(day="2026-10-01", status="promoted")),
    ]
    expired = {f.entity for f in _run(entities, tmp_path=tmp_path) if f.code == "expired"}
    assert expired == {"task:old", "attempt:old-1", "lesson:old"}


def test_cli_exit_codes_and_json(tmp_path, capsys):
    memory = tmp_path / "memory.jsonl"
    memory.write_text("", encoding="utf-8")
    assert audit_mod.main(["--memory-file", str(memory), "--repo-root", str(tmp_path), "--today", "2026-11-15"]) == 0

    memory.write_text(json.dumps(_entity("bad", "task", "x")) + "\nnot json\n", encoding="utf-8")
    capsys.readouterr()
    rc = audit_mod.main(["--memory-file", str(memory), "--repo-root", str(tmp_path), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert payload["summary"]["errors"] >= 2
    assert "unreadable" in {f["code"] for f in payload["findings"]}


def test_missing_memory_file_is_empty_graph(tmp_path):
    assert audit_mod.main(["--memory-file", str(tmp_path / "absent.jsonl"), "--repo-root", str(tmp_path)]) == 0
