# Agent Harness — Official Responsibility Hierarchy

## Purpose

This document is the canonical explanation of how Agent, Instruction, Skill, Docs, Tool, Implementation and Verification relate inside CherryStock.

The decision is recorded in `docs/adr/ADR-011-agent-harness-responsibility-hierarchy.md`.

## 1. Official L0–L7 hierarchy

```text
L0  Governance
    .github/copilot-instructions.md

L1  Agent — WHO owns the outcome
    .github/agents/*.agent.md

L2  Instruction — mandatory RULES / CONSTRAINTS
    .github/instructions/*.instructions.md

L3  Skill — HOW to perform a repeatable procedure
    .github/skills/*/SKILL.md

L4  Docs — durable KNOWLEDGE / DESIGN
    docs/**

L5  Tool — execution CAPABILITY
    MCP · GitHub · DuckDB · Flint · Archify · Draw.io · scripts · CLI

L6  Implementation — runtime BEHAVIOR
    src/** + run.py / runMonthly.py / runtime entry points

L7  Verification — executable EVIDENCE
    tests/** + reproducible validation evidence
```

Core invariant:

```text
Agent        owns the OUTCOME.
Skill        owns the PROCEDURE.
Instruction  owns mandatory RULES / CONSTRAINTS.
Docs         own durable KNOWLEDGE / DESIGN.
Tool         provides EXECUTION CAPABILITY.
Implementation owns runtime behavior.
Verification owns evidence that behavior satisfies the contract.
```

This hierarchy expresses ownership and precedence. It does not mean every task must load every layer.

## 2. Operational workflow

```text
User Request
    ↓
L0 Governance / Router
    ↓
L1 Authoritative Agent
    ↓
L2 Mandatory Instructions
    ↓
L4 Smallest relevant Docs set
    ↓
Need repeatable specialist procedure?
    ├── No
    │    ↓
    │  L5 Tool / L6 Implementation as required
    │
    └── Yes
         ↓
       L3 Skill
         ↓
       L5 Tool / L6 Implementation
    ↓
L7 Verification when delivery requires independent evidence
    ↓
Agent evaluates owned gate / handoff / terminal outcome
```

Docs are normally read before a Skill is executed so the procedure operates against the current requirement/design/domain contract. L3 remains above L4 in the responsibility hierarchy because the Skill is an executable procedure layer, not because it must be read first.

## 3. Ownership boundaries

### L0 — Governance

`.github/copilot-instructions.md` owns repository-wide routing, precedence, handoff rules, bounded execution and cross-cutting engineering policy.

It answers:

- Which Agent owns this outcome?
- Which constraints have precedence?
- Which handoff/gate is required next?
- When must execution stop?

It should not duplicate detailed domain architecture or specialist procedures.

### L1 — Agent

An Agent is accountable for one class of engineering outcome.

Examples:

- Business Analyst → requirement readiness.
- Solution Architect → design readiness.
- Indicator Management → concrete indicator lifecycle readiness.
- Chart → visualization decision / Flint artifact readiness.
- General Coding → implementation readiness.
- Test Engineer → independent validation verdict.

Agent files should primarily contain:

```text
Role
Trigger
Owned outcome / readiness state
Required inputs
Context discovery boundaries
Escalation / handoff
Stop conditions
Material ownership
```

Detailed reusable procedures should be delegated to Skills.

### L2 — Instruction

Instructions define mandatory constraints for a domain or execution surface.

Examples:

- database transaction and SQL safety;
- indicator SSOT and lifecycle invariants;
- testing retry/validation constraints;
- chart integration constraints;
- crawler behavior;
- Archify synchronization constraints.

Instruction style should be normative: MUST, MUST NOT, SHOULD where appropriate. A procedural tutorial belongs in a Skill or runbook instead.

### L3 — Skill

A Skill packages a repeatable task procedure that may be reused by one or more compatible Agents.

Current catalog:

```text
.github/skills/
├── architecture-design/
├── indicator-onboarding/
├── regression-testing/
├── data-quality-validation/
├── duckdb-migration/
├── chart-authoring/
└── drawio-skill/
```

A Skill may:

- read authoritative Docs;
- obey Instructions;
- invoke Tools;
- define bounded step-by-step execution and evidence requirements.

A Skill may not:

- become the authoritative Agent;
- override a repository/domain Instruction;
- redefine architecture or business rules;
- claim a readiness gate owned by another Agent.

### L4 — Docs

`docs/**` is the durable engineering/domain knowledge layer.

Canonical responsibilities:

```text
docs/backlog/requirements/**   requirement contracts
docs/architecture/**          current/target system design
docs/adr/**                   durable architecture decisions and rationale
docs/domain/**                business/market/domain knowledge
docs/reference/**             generated/reference/historical context
docs/runbook/**               reproducible operational procedures
docs/development/**           developer workflow and implementation guidance
docs/ChangeRequest/**         release/change traceability
```

`docs/00_HOME.md` is the knowledge routing entry point, not a duplicate knowledge store.

### L5 — Tool

Tools provide capability. Examples:

- GitHub connector;
- CherryMon/DuckDB MCP;
- Flint MCP;
- Archify CLI/runtime;
- Draw.io Desktop CLI and upstream scripts;
- Python/pytest/PowerShell;
- repository scripts.

A Tool returns evidence/results. The owning Agent still decides whether that evidence satisfies its contract.

### L6 — Implementation

Runtime behavior belongs to source and executable entry points:

```text
src/**
run.py
runMonthly.py
```

CherryStock is incrementally migrating toward `src/cherrystock/**` as the canonical layered runtime package. Existing legacy modules remain supported until their dedicated migration backlog is implemented; this Harness reorganization does not perform a big-bang source move.

### L7 — Verification

`tests/**` contains executable validation. Durable manual/operational validation procedures may live under `docs/runbook/**`, but the final evidence-backed verdict belongs to the Test Engineer when independent validation is required.

## 4. Dependency rules

Preferred direction:

```text
Governance → Agent
Agent      → Instruction
Agent      → Docs
Agent      → Skill
Skill      → Instruction
Skill      → Docs
Skill      → Tool
Tool       → evidence/result
Agent      → Implementation owner / handoff
Test       → verdict
```

Avoid:

```text
Agent       embeds every specialist procedure
Instruction becomes a long tutorial
Skill       becomes Source of Truth
Docs        contains executable persona/routing
Tool        makes architecture/business decisions
Implementation silently changes approved contracts
Test        self-expands into unrelated refactoring
```

## 5. Current Agent-to-Skill mapping

| Agent | Default specialist Skills when applicable |
|---|---|
| Business Analyst | No mandatory procedure Skill yet; durable requirements use existing BA contract/templates |
| Solution Architect | `architecture-design`; optional `drawio-skill`; Archify tool remains mandatory where synchronization contract applies |
| Indicator Management | `indicator-onboarding` |
| Chart | `chart-authoring` |
| General Coding | `duckdb-migration`, `data-quality-validation` when the implementation scope requires them |
| Test Engineer | `regression-testing`, `data-quality-validation` |

Skills are selected by task, not loaded indiscriminately.

## 6. Example — technical indicator onboarding

```text
User: add RSI/ATR/etc.
 ↓
L0 copilot-instructions routes to Indicator Management
 ↓
L1 Indicator_Management.agent.md owns lifecycle outcome
 ↓
L2 indicators.instructions.md constrains SSOT/safety
 ↓
L4 Indicator_Engine.md + ADR-002 + DB metadata provide current knowledge
 ↓
L3 indicator-onboarding/SKILL.md defines Discover → Metadata → Backfill → Validate
 ↓
L5 CherryMon MCP / Python wrapper executes operations
 ↓
L6 calcEngine/runtime persists behavior/data
 ↓
L7 TestEngineer validates independently
```

## 7. Example — architecture change

```text
User request
 ↓
SolutionArchitect.agent.md
 ↓
mandatory domain Instructions
 ↓
architecture / ADR / current source evidence
 ↓
architecture-design Skill
 ↓
Archify for synchronized architecture artifact
Draw.io optionally for editable review artifact
 ↓
approved design handoff
 ↓
GeneralCoding/domain owner
 ↓
TestEngineer
```

Architecture meaning remains in Markdown/ADR. Generated diagrams are presentation/validation artifacts, not a second Source of Truth.

## 8. Legacy migration completed by this hierarchy

The legacy `.github/agents/Instructions/**` mixed responsibility is retired:

- stock terminology → `docs/domain/market/Stock_Terms.md`;
- stock strategy knowledge → `docs/domain/strategy/Stock_Strategies.md`;
- indicator procedure → `.github/skills/indicator-onboarding/SKILL.md`;
- long-form legacy indicator reference → `docs/reference/Indicator_Engine_Legacy_Reference.md`;
- stale generated project-structure reference → removed.

## 9. Related artifacts

- `docs/architecture/agent-harness/README.md`
- `docs/architecture/agent-harness/AGENT_EXECUTION_FLOW.md`
- `docs/adr/ADR-011-agent-harness-responsibility-hierarchy.md`
- `.github/skills/README.md`
- `docs/architecture/diagrams/agent-harness-five-components.drawio`
- `docs/architecture/diagrams/cherrystock-adlc-agent-harness.workflow.json`
