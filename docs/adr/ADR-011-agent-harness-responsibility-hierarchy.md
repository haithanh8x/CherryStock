# ADR-011 — Agent Harness Responsibility Hierarchy

- **Status:** Accepted
- **Date:** 2026-09-15
- **Decision scope:** Repository-wide AI/developer harness structure

## Context

CherryStock already separates repository governance, specialist Agents, domain Instructions, engineering Docs, runtime source and tests. Reusable Skills were added incrementally, but the responsibility boundary between Agent, Instruction, Skill, Docs and Tool was not yet a single durable architecture decision. Historical material under `.github/agents/Instructions/**` also mixed domain knowledge, operational procedure and agent behavior.

Without a formal hierarchy, the same rule or procedure can be duplicated across Agent files, Instructions and Docs, increasing prompt/context size and creating ownership drift.

## Decision

CherryStock adopts the following official responsibility hierarchy:

```text
L0  Governance      .github/copilot-instructions.md
L1  Agent           .github/agents/*.agent.md
L2  Instruction     .github/instructions/*.instructions.md
L3  Skill           .github/skills/*/SKILL.md
L4  Docs            docs/**
L5  Tool            MCP / GitHub / DuckDB / Flint / Archify / Draw.io / scripts / CLI
L6  Implementation  src/** + runtime entry points
L7  Verification    tests/** + reproducible validation evidence
```

The invariant is:

```text
Agent        owns the OUTCOME.
Skill        owns the PROCEDURE.
Instruction  owns mandatory RULES / CONSTRAINTS.
Docs         own durable KNOWLEDGE / DESIGN.
Tool         provides EXECUTION CAPABILITY.
Implementation owns runtime behavior.
Verification owns evidence that behavior satisfies the contract.
```

The hierarchy is a responsibility and precedence model, not a requirement to load every layer for every task. The normal operational sequence is:

```text
Governance
  → authoritative Agent
  → mandatory Instructions
  → smallest relevant Docs set
  → Skill when a repeatable specialist procedure applies
  → Tool / Implementation
  → Verification
```

A Skill cannot change Agent ownership, override an Instruction, redefine an ADR, or become a knowledge Source of Truth. A Tool cannot make a business/architecture decision by itself.

## Material placement rules

- Role, trigger, owned outcome, gate, handoff and stop conditions belong in `.github/agents/*.agent.md`.
- MUST/MUST NOT safety, domain and execution constraints belong in `.github/instructions/*.instructions.md`.
- Repeatable multi-step specialist procedures belong in `.github/skills/*/SKILL.md`.
- Architecture, domain knowledge, requirements, decisions, reference material and runbooks belong in `docs/**`.
- Execution adapters/capabilities remain in MCP configuration, scripts, CLIs or infrastructure code.
- Runtime behavior belongs in `src/**`.
- Independent executable validation belongs in `tests/**` and durable reproducible evidence/runbooks where appropriate.

## Legacy migration

The old `.github/agents/Instructions/**` location is retired as a knowledge/procedure owner.

- Stock terminology moves to `docs/domain/market/Stock_Terms.md`.
- Stock strategy knowledge moves to `docs/domain/strategy/Stock_Strategies.md`.
- Indicator lifecycle procedure moves to `.github/skills/indicator-onboarding/SKILL.md`.
- The old long-form Indicator Engine material is preserved only as a historical reference under `docs/reference/Indicator_Engine_Legacy_Reference.md`; canonical architecture remains `docs/architecture/Indicator_Engine.md`.
- Generated/stale project-structure documentation is removed; current structure is documented by the high-level architecture and Agent Harness materials.

## Consequences

### Positive

- Agent files can stay focused on ownership and handoff.
- Procedures become reusable across compatible Agents.
- Mandatory rules have one clear policy layer.
- Durable knowledge is discoverable through `docs/00_HOME.md`.
- Tools remain replaceable capabilities rather than hidden architecture owners.
- The Agent Harness becomes easier to extend without growing monolithic system prompts.

### Trade-offs

- Agents may need to load a Skill in addition to Instructions and Docs for specialist work.
- Existing references to legacy `.github/agents/Instructions/**` must be migrated.
- Architecture diagrams and routing documents must stay synchronized with the hierarchy.

## Alternatives considered

### Put all behavior in Agent files

Rejected because role, policy, procedure and knowledge would grow together and become difficult to reuse or govern.

### Put all procedures in Instructions

Rejected because Instructions should remain concise mandatory constraints. Procedures evolve independently and may be shared across Agents.

### Treat Skills or Tools as task owners

Rejected because procedure/capability does not imply accountability for requirement, design, implementation or validation outcomes.

## Related material

- `docs/architecture/agent-harness/README.md`
- `docs/architecture/agent-harness/AGENT_SKILL_INSTRUCTION_DOC_TOOL.md`
- `.github/copilot-instructions.md`
- `.github/skills/README.md`
- `docs/backlog/Harness_Backlog.md`
- `docs/backlog/Architecture_Backlog.md`
