# ADR-019 — Developer Memory MCP Is an L5 Working/Episodic Memory Tool

- **Status:** Accepted
- **Date:** 2026-11-15
- **Decision scope:** Repository-wide AI/developer harness (developer sessions, not runtime agents)
- **Related:** ADR-011, `docs/backlog/Harness_Backlog.md` (Memory Model, CS-HARNESS-007/008)

## Context

CherryStock knowledge memory is Git-based: `AGENTS.md`/`.github/**` define ownership and rules,
`docs/**` holds durable design and domain knowledge. Each AI session nevertheless starts without
recollection of in-flight tasks, previous failed commands, or where relevant knowledge lives, so
agents re-read the same files and may rerun unchanged failed commands, contrary to the anti-loop
governance.

A knowledge-graph memory MCP server (`@modelcontextprotocol/server-memory`, `cherrystock-memory`)
is now available to developer clients. Without a contract it would become a hidden, unreviewed,
second knowledge store that silently conflicts with docs/ADRs and can leak sensitive data.

## Decision

1. The memory MCP server is an **L5 Tool**. It provides recall capability only; it is never a
   Source of Truth and has the lowest precedence of any material (below Tool/runtime evidence of
   the current session).
2. It stores only **developer working/episodic memory**:
   - `pointer` — where knowledge lives (repository path + section), never the knowledge itself;
   - `task` — in-flight objective, owner, gate, branch, next owner;
   - `attempt` — a failed command/hypothesis with its failure signature and the commit it ran on;
   - `lesson` — a candidate durable finding awaiting promotion into `docs/**`;
   - `preference` — user interaction preferences.
3. **Knowledge memory stays in Git.** A `lesson` that remains useful must be promoted into the
   owning `docs/**` / Instruction / Skill through a normal reviewed change, then marked
   `promoted`. Memory is disposable: deleting the graph must lose no canonical knowledge.
4. **Repository wins.** Any memory item conflicting with repository content is stale; agents
   re-read the repository and correct or delete the item. Pointers carry the git commit of the
   referenced path so staleness is mechanically detectable.
5. Memory MUST NOT hold business rules, formulas, architecture decisions, schema copies, market
   data as fact, validation verdicts as evidence, permissions (write-location, commit, push
   exceptions) or any credential/secret/personal data.
6. **Independence:** Test Engineer does not use implementation-side memory claims as evidence and
   does not read another owner's `task`/`lesson` items to form a verdict.
7. The graph file lives **outside the repository** (per user/machine, e.g.
   `~/.config/opencode/cherrystock-memory.jsonl`) and is never committed. The repository owns the
   contract (`.github/instructions/memory.instructions.md`), the procedure
   (`.github/skills/memory-hygiene/SKILL.md`) and a read-only auditor (`scripts/memory_audit.py`).
8. Runtime-agent memory (CS-HARNESS-007/008, `sys_agent_*` in DuckDB) is a separate future
   decision and is **not** implemented by this server.

## Consequences

### Positive

- Sessions resume in-flight work and avoid rerunning known-failed commands.
- Recall is pointer-based, so context stays small and docs remain the single knowledge store.
- Staleness, secrets and convention drift are detectable by a deterministic audit.

### Trade-offs

- Agents must follow write conventions; the server itself does not enforce them.
- Memory is per machine; it is not shared between Mac/Windows checkouts.
- Promotion requires a reviewed docs change, which is deliberate friction.

## Alternatives considered

- **Store knowledge in memory, docs as export** — rejected: creates an unreviewed second Source of
  Truth and violates ADR-011.
- **Commit the memory file into the repository** — rejected: noisy, machine-specific, risk of
  leaking sensitive content, and duplicates Git history.
- **No memory** — rejected: loses anti-loop and resume benefits that docs cannot provide.

## Related material

- `.github/instructions/memory.instructions.md`
- `.github/skills/memory-hygiene/SKILL.md`
- `scripts/memory_audit.py`, `tests/test_memory_audit.py`
- `docs/architecture/agent-harness/AGENT_SKILL_INSTRUCTION_DOC_TOOL.md` §10
- `docs/development/OpenCode_Setup.md` (Memory MCP)
