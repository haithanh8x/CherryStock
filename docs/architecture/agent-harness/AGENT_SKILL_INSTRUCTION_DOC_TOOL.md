# Agent Harness — Agent, Skill, Instruction, Docs and Tool

## Purpose

This document defines the relationship between five core CherryStock Agent Harness components:

```text
Agent        = owns the OUTCOME
Skill        = owns the PROCEDURE
Instruction  = owns mandatory RULES / CONSTRAINTS
Docs         = own durable KNOWLEDGE / DESIGN
Tool         = provides EXECUTION CAPABILITY
```

Editable Draw.io source:

```text
docs/architecture/diagrams/agent-harness-five-components.drawio
```

Local validation/export runbook:

```text
docs/runbook/Drawio_Skill.md
```

---

## 1. Ownership model

### Agent — WHO owns the result

An Agent is accountable for a specific engineering outcome and readiness gate.

Examples:

- `BusinessAnalyst.agent.md` owns requirement readiness.
- `SolutionArchitect.agent.md` owns design readiness.
- `GeneralCoding.agent.md` owns implementation readiness.
- `TestEngineer.agent.md` owns the independent validation verdict.
- `Chart.agent.md` owns chart recommendation and Flint authoring outcomes.

An Agent may call Skills and Tools, but the Agent remains accountable for the final outcome it owns.

### Skill — HOW to perform a repeatable specialist task

A Skill packages a reusable procedure that can be invoked by one or more Agents.

Examples:

```text
.github/skills/chart-authoring/SKILL.md
.github/skills/drawio-skill/SKILL.md
```

A Skill does not own business or architecture decisions. It translates an already-routed task into a repeatable execution procedure.

### Instruction — mandatory RULES

Instructions constrain how work may be executed in a domain.

Examples:

```text
.github/instructions/database.instructions.md
.github/instructions/indicators.instructions.md
.github/instructions/testing.instructions.md
.github/instructions/chart.instructions.md
```

Instructions are not tutorials and should not duplicate architecture knowledge. They define mandatory repository/domain constraints.

### Docs — durable KNOWLEDGE

`docs/**` is the engineering knowledge layer.

It owns:

- current architecture;
- ADR decisions and rationale;
- domain rules;
- reference contracts;
- runbooks;
- requirements and backlog traceability.

Docs are read by Agents and Skills as evidence/context, but Docs do not execute work.

### Tool — execution CAPABILITY

Tools perform concrete operations.

Examples:

- GitHub connector;
- DuckDB MCP;
- Flint MCP;
- Archify CLI/skill runtime;
- Draw.io Desktop CLI;
- upstream `drawio-skill` Python scripts;
- Python/pytest/PowerShell scripts.

A Tool provides capability but does not decide whether the requested architecture or behavior is correct.

---

## 2. Canonical relationship

```text
                         mandatory constraints
                    ┌──────────────────────────┐
                    │                          ▼
              +-------------+             +---------+
              | Instruction | ----------> |  Agent  |
              +-------------+             +---------+
                                                │
                         knowledge/context      │ selects / invokes
                    ┌───────────────────────────┤
                    │                           ▼
                +------+                    +-------+
                | Docs | -----------------> | Skill |
                +------+                    +-------+
                                               │
                                               │ executes through
                                               ▼
                                            +------+
                                            | Tool |
                                            +------+
                                               │
                                               └── evidence/result → Agent
```

Important secondary relationships:

- Instructions also constrain Skills.
- Skills may read Docs to understand the task-specific contract.
- Tools return execution evidence to the Skill/Agent.
- Tools MUST NOT become architecture or business Sources of Truth.

---

## 3. Execution workflow

```text
User Request
    ↓
.github/copilot-instructions.md
    ↓ route
Authoritative Agent
    ↓
Load mandatory Instructions
    ↓
Read smallest relevant Docs set
    ↓
Need repeatable specialist procedure?
    ├── No  → Agent executes within its contract
    └── Yes → Load Skill
                ↓
             Skill calls Tool(s)
                ↓
             Tool evidence/result
                ↓
             Agent evaluates outcome
                ↓
             Handoff / readiness gate / terminal verdict
```

The Agent remains responsible for deciding whether evidence is sufficient for its owned outcome.

---

## 4. Example — Draw.io architecture artifact

Request:

```text
Draw the relationship between Agent, Skill, Instruction, Docs and Tool.
```

Flow:

```text
SolutionArchitect Agent
    │
    ├── reads repository governance / architecture docs
    ├── obeys architecture instructions and Source-of-Truth rules
    │
    └── invokes drawio-skill
            │
            ├── authors editable .drawio XML
            ├── calls upstream validate.py
            └── optionally calls Draw.io Desktop CLI for PNG/SVG/PDF
```

Ownership remains:

```text
SolutionArchitect → architecture meaning / correctness
Drawio Skill      → diagram authoring procedure
Draw.io Tool      → rendering/export capability
Docs              → durable architecture evidence
Instructions      → mandatory constraints
```

---

## 5. Draw.io versus Archify

CherryStock now supports both, with different responsibilities.

### Archify

Use for the existing mandatory Solution Architect synchronization/validation contract for approved architecture changes where `SolutionArchitect.agent.md` requires it.

Archify typed sources and generated outputs participate in the current design readiness gate.

### Draw.io

Use when:

- the user explicitly requests Draw.io/diagrams.net;
- an editable workshop/review artifact is useful;
- an ERD/UML/workflow/data-flow diagram should remain directly editable in Draw.io;
- a portable `.drawio` source is desired.

Draw.io is supplementary and does not replace canonical architecture Markdown, ADRs, or the mandatory Archify artifact synchronization rule.

---

## 6. Dependency rules

Preferred dependency direction:

```text
Agent       → Skill
Agent       → Instruction
Agent       → Docs
Skill       → Instruction
Skill       → Docs
Skill       → Tool
Tool        → result/evidence
```

Avoid:

```text
Tool        → architecture decision
Skill       → becomes Source of Truth
Instruction → duplicates full docs
Docs        → contains executable agent persona
Agent       → embeds every specialist procedure inline
```

This separation keeps the harness modular and reduces prompt/context bloat.

---

## 7. Reference artifact

The first CherryStock Draw.io skill artifact demonstrates this exact relationship:

```text
docs/architecture/diagrams/agent-harness-five-components.drawio
```

Its intended semantics are:

- `Instruction → Agent`: governs/constrains.
- `Docs → Agent`: provides context/knowledge.
- `Agent → Skill`: selects/invokes a procedure.
- `Instruction → Skill`: constrains the procedure.
- `Docs → Skill`: supplies authoritative references.
- `Skill → Tool`: executes through capability.
- `Tool → Agent`: returns evidence/results for evaluation.

The diagram is presentation/reference material. This Markdown remains the durable explanation of the relationship model.
