---
applyTo: "**"
---

# Memory MCP Instructions

Mandatory constraints for the `cherrystock-memory` knowledge-graph MCP server.
Decision: `docs/adr/ADR-019-developer-memory-mcp-as-l5-working-memory.md`.
Procedure: `.github/skills/memory-hygiene/SKILL.md`.

## 1. Precedence

- Memory is an L5 Tool with the lowest precedence. Repository content always wins.
- A memory item MUST NOT be cited as the authority for a rule, design, contract or verdict.
  Verify every recalled pointer against the repository before relying on it.
- Memory MUST NOT influence agent routing; route first, then recall within the routed scope.

## 2. Allowed content

Entity name format is `<type>:<kebab-key>`; `entityType` equals `<type>`.

| type | Holds | Lifetime |
|---|---|---|
| `pointer` | repository path + section for a topic | until path changes (stale) |
| `task` | objective, owner agent, gate, branch, next owner | delete 7 days after `closed` |
| `attempt` | failed command/hypothesis, failure signature, commit | delete 30 days after creation or task close |
| `lesson` | candidate durable finding | promote or delete within 14 days |
| `preference` | user interaction preference | until user changes it |

Allowed relation types: `references` (to a `pointer`), `attempt_of` (`attempt` → `task`),
`derived_from` (`lesson` → `task`/`attempt`).

## 3. Observation header (MUST)

```text
[src=<repo-path|user|session>][sha=<git short sha>][date=YYYY-MM-DD][agent=<id>][status=<s>] <text>
```

- `agent` ∈ `router|ba|sa|dev|test|indicators|chart|user`.
- `status` ∈ `active|stale|promoted|closed|failed`.
- `sha` is REQUIRED when `src` is a repository path: the last commit touching that path.
- Text is one short fact (≤ 400 characters). No pasted files, logs, query results or diffs.

## 4. Forbidden content (MUST NOT)

- credentials, tokens, keys, passwords, connection strings, personal data;
- business rules, formulas, parameters, architecture decisions, schema copies — store a `pointer`;
- market data/prices/scores presented as fact;
- `PASS`/verdict claims as evidence — evidence lives in `tests/**` / `docs/reference/data/**`;
- permissions: write-location exceptions, commit/push authorization, approvals. These are
  granted per request and are never remembered.

## 5. Behavior

- Recall: `search_nodes` with a scoped query and `limit`; never `read_graph` without
  `entityTypes` or `observationLimit` in normal work.
- Before rerunning a command, check for an `attempt` with the same signature on the same commit.
  An unchanged failure MUST NOT be retried (governance anti-loop rule).
- When recalled content conflicts with the repository, mark it `stale` or delete it; do not edit
  docs to match memory.
- Test Engineer MUST NOT use implementation-side `task`/`lesson` claims as validation evidence.
- Durable findings MUST be promoted to `docs/**`/Instruction/Skill by the owning agent through a
  normal reviewed change before claiming the knowledge is captured.
- Memory writes are not deliverables and never substitute for the governance handoff payload.
