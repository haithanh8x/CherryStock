# CherryStock — agent entry point

This file is the cross-client bootstrap, not a second governance or knowledge source.
Repository paths below are relative to the CherryStock root.

## Before working

1. Read `.github/copilot-instructions.md` (governance and routing) and
   `.github/agents/CherryMon.agent.md` (shared architecture constitution), unless
   their current contents are already loaded as configured instructions.
2. Classify the requested outcome and read the corresponding contract under
   `.github/agents/`. Select the smallest sufficient route; do not load every agent.
3. Read matching `.github/instructions/*.instructions.md` before domain execution.
4. Start knowledge discovery at `docs/00_HOME.md`; follow only relevant
   requirement, architecture, ADR, domain and runbook links.
5. Load a matching procedure from `.github/skills/` only when needed, then inspect
   the affected implementation and nearest tests as evidence.

Governance owns routing; agents own outcomes; instructions own constraints;
skills own procedures; docs own knowledge; tools provide execution capability.
Higher-priority platform instructions still apply. Report conflicts rather than
silently changing contracts or treating planned backlog work as implemented.

## Working boundaries

- Check the working tree before edits and preserve unrelated user changes.
- Follow the governance write-location policy; obtain an explicit exception before
  local writes when required. Never infer permission to commit/push from a task.
- For code changes, use `docs/development/Development_Workflow.md`; for Python
  tests, runnable scripts or root commands also read
  `docs/development/Python_Execution_Conventions.md`.
- Do not run production pipelines, migrations, backfills or paid model calls just
  to discover the project. Establish scope and side effects first.
- Distinguish implementation checks from independent validation. Do not claim a
  specialist gate or a PASS without the required ownership and evidence.

## OpenCode

`opencode.jsonc` is a thin runtime adapter over the canonical `.github/` files.
Use the repository root as the OpenCode workspace. Setup, agent IDs, skill
discovery and validation are documented in
`docs/development/OpenCode_Setup.md`.
