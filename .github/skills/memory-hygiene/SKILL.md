---
name: memory-hygiene
description: "Recall, record, audit, promote and prune CherryStock developer memory in the cherrystock-memory MCP knowledge graph under ADR-019. Use at session start/resume of a multi-step task, after a failed attempt, at a handoff/gate, or when asked to clean up or audit memory."
---

# CherryStock Memory Hygiene Skill

## Applicable owners

Any routed Agent for its own `task`/`attempt`/`lesson` items. The router may maintain
`pointer` and `preference` items. Promotion of a `lesson` is performed by the owner of the
target material (e.g. SA for architecture, Dev for runbooks).

Mandatory constraints: `.github/instructions/memory.instructions.md`.
Decision: `docs/adr/ADR-019-developer-memory-mcp-as-l5-working-memory.md`.

## Inputs

- routed owner and current objective;
- task key (REQ id, branch or short slug);
- tool: `cherrystock-memory` MCP (`search_nodes`, `open_nodes`, `create_entities`,
  `add_observations`, `create_relations`, `delete_observations`, `delete_entities`).

## Procedure

### 1. Recall (start / resume)

1. `search_nodes(query=<task key or topic>, limit=10)`.
2. For each `pointer` used, compare its `sha` with `git log -1 --format=%h -- <path>`.
   Different → read the file again and update or mark the pointer `stale`.
3. Read open `attempt` items for the task; do not rerun an identical failed command on the same
   commit without new evidence.
4. Continue from repository material; memory only narrows what to read.

### 2. Record (during work)

- New task: `create_entities([{name:"task:<key>", entityType:"task", observations:[<header> objective/owner/gate/branch]}])`.
- Failed command/hypothesis: `attempt:<key>-<n>` with the command, the first error line and the
  commit, plus relation `attempt_of → task:<key>`.
- Useful location: `pointer:<topic>` with `src=<path>` and `sha`.
- Candidate finding: `lesson:<slug>` with `status=active`, relation `derived_from`.

Write only header-formatted, single-fact observations (see Instruction §3).

### 3. Handoff / gate

- Add an observation to `task:<key>` with the new gate and next owner.
- The governance handoff payload remains the deliverable; memory only mirrors state.

### 4. Promote

For each active `lesson`:
1. identify the owning canonical material (`docs/**`, Instruction, Skill, runbook);
2. update it through a normal repository change within the owner's scope;
3. replace the lesson status with `promoted` and `src=<new path>`, or delete it.

### 5. Audit and prune

Run the read-only auditor from the repository root:

```sh
python scripts/memory_audit.py --repo-root .
python scripts/memory_audit.py --repo-root . --json
```

The default memory file is `$MEMORY_FILE_PATH` or `~/.config/opencode/cherrystock-memory.jsonl`;
override with `--memory-file`. Exit code `1` means at least one `error` finding.

Fix findings through the MCP tools (never by hand-editing the JSONL while the server runs):
- `secret` / `forbidden_permission` → delete the observation immediately;
- `bad_name` / `bad_header` → rewrite the observation in the required format;
- `stale_pointer` / `missing_path` → re-verify and update, or delete;
- `expired` → delete the closed task/attempt or the overdue lesson after promotion review.

## Evidence / output

Report the auditor summary and which items were promoted/deleted. Memory content is never
evidence for a readiness gate.

## Stop conditions

- Auditor reports no errors and the objective's items are current → stop.
- Unable to determine the owning material for a lesson → leave it `active`, report to router.

## Anti-patterns

- copying doc sections, schemas or formulas into observations;
- `read_graph` of the whole graph on every task;
- remembering "user allowed push/commit/local writes";
- Test Engineer reading Dev's lesson "tests pass" as evidence;
- editing docs to match stale memory.
