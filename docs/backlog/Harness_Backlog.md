# CherryStock Agent Harness Backlog

## Purpose

This backlog captures the work required to evolve CherryStock from an AI-assisted software-development setup into an explicit **Agent Harness architecture**.

The harness model used here separates the model from the runtime scaffolding around it:

```text
Agent = Model + Harness
```

For CherryStock, the harness is evaluated across six responsibilities:

1. Tool loop
2. Tools and MCP servers
3. Skill files
4. Memory
5. Hooks
6. Execution environment and observability

CherryStock already has a relatively mature **developer harness** for Copilot/local coding agents, but only an early foundation for a future **runtime stock-analysis agent harness**.

The target is not to replace CherryStock's layered architecture with a generic `agent/tools/models/utils` structure. Harness responsibilities must fit inside the canonical Domain / Application / Infrastructure / Interfaces architecture.

---

# Current-State Mapping

| Harness capability | Current CherryStock mapping | Status |
|---|---|---|
| Tool loop | `.github/copilot-instructions.md`, `.github/agents/TestEngineer.agent.md`, host agent execution | PARTIAL |
| Tools / MCP | `src/mcp_server/duckdb_mcp.py`, application ports, database/AmiBroker adapters | PARTIAL / GOOD FOUNDATION |
| Skill files | Procedures currently distributed across `.github/agents/**` and `.github/instructions/**` | PARTIAL |
| Memory | `docs/**`, ADRs, `docs/architecture/Second_Brain.md`, Git history | GOOD FOR DEVELOPMENT / MISSING RUNTIME EPISODIC MEMORY |
| Hooks | MCP mutation confirmation, transaction boundaries, validation guardrails | MISSING GENERIC HARNESS HOOKS |
| Execution environment | Git, VS Code, Python, DuckDB, AmiBroker, pytest, scripts, `run.py` | GOOD |
| Observability | Data-quality audit plus isolated logging | PARTIAL |

Important distinction:

```text
Developer Harness
  = AI/Copilot/local agents used to design, code, test and maintain CherryStock

Runtime Agent Harness
  = future Stock Analyst / Market Analyst agents operating as CherryStock product capabilities
```

Do not mix these two concerns into one implementation.

---

# Target Architecture

## Developer Harness

```text
.github/
├── copilot-instructions.md
├── agents/
│   ├── SolutionArchitect.agent.md
│   ├── TestEngineer.agent.md
│   └── Indicator_Management.agent.md
├── instructions/
├── skills/
│   ├── architecture-design/
│   │   └── SKILL.md
│   ├── indicator-onboarding/
│   │   └── SKILL.md
│   ├── regression-testing/
│   │   └── SKILL.md
│   ├── data-quality-validation/
│   │   └── SKILL.md
│   └── duckdb-migration/
│       └── SKILL.md
└── hooks/
    ├── security.json
    ├── validation.json
    └── observability.json
```

Ownership rule:

```text
Agent       = WHO performs a class of work
Instruction = repository/domain rules that MUST/MUST NOT be violated
Skill       = HOW to perform a specific repeatable procedure
Hook        = deterministic enforcement around execution/tool lifecycle
```

## Runtime Agent Harness

Runtime harness components should live inside the canonical `src/cherrystock` package:

```text
src/cherrystock/
├── application/
│   ├── agents/
│   │   ├── stock_analyst.py
│   │   └── market_analyst.py
│   ├── harness/
│   │   ├── runner.py
│   │   ├── tool_loop.py
│   │   ├── context.py
│   │   ├── skill_registry.py
│   │   ├── hooks.py
│   │   ├── completion.py
│   │   └── handoff.py
│   └── ports/
│       ├── llm.py
│       ├── tools.py
│       ├── memory.py
│       └── telemetry.py
├── infrastructure/
│   ├── llm/
│   ├── memory/
│   └── observability/
└── interfaces/
    ├── mcp/
    ├── web/
    └── cli/
```

Dependency direction:

```text
Interface
   ↓
Agent / Harness
   ↓
Application Port
   ↑
Infrastructure Adapter
```

The runtime agent MUST NOT depend directly on OpenRouter, DuckDB SQL, AmiBroker internals or a named LLM model.

---

# Backlog

## CS-HARNESS-001 — Formalize Developer Harness Architecture

**Priority:** P1  
**Status:** TODO

### Problem

CherryStock already has developer-agent governance, specialized agents and domain instructions, but there is no single architecture document defining how Agent, Instruction, Skill, Hook, Tool and Memory responsibilities differ.

Without an explicit contract, procedures can continue accumulating inside agent or instruction files and recreate large system-prompt-style configurations.

### Target

Document the CherryStock Developer Harness architecture and ownership boundaries.

### Acceptance Criteria

- Define Agent, Instruction, Skill, Hook, Tool and Memory responsibilities.
- Define precedence/routing between `.github/copilot-instructions.md`, agents, instructions and skills.
- Define how `docs/00_HOME.md` participates as knowledge-memory routing rather than executable procedure storage.
- Define when a new procedure becomes a Skill instead of an Agent or Instruction.
- Define developer harness separately from runtime product agents.
- Update `docs/00_HOME.md` with the harness architecture entry point.

### Dependencies

None.

---

## CS-HARNESS-002 — Introduce Native Skill Files

**Priority:** P1  
**Status:** TODO

### Problem

Repeatable execution procedures currently live inside `.github/agents/**` and `.github/instructions/**` together with roles and policy.

This increases context size and makes procedures harder to discover, reuse and evolve independently.

### Target

Introduce task-scoped skills under:

```text
.github/skills/<skill-name>/SKILL.md
```

Initial candidates:

```text
architecture-design
indicator-onboarding
regression-testing
data-quality-validation
duckdb-migration
ui-performance-diagnosis
```

### Acceptance Criteria

- `.github/skills/**` exists with a documented naming convention.
- At least one existing repeatable procedure is migrated as the reference implementation.
- Skill files contain procedure-specific execution guidance rather than broad repository policy.
- Skills link to authoritative architecture/domain documentation instead of duplicating it.
- Agent files become smaller and focus on role/routing/state-machine responsibilities.
- Instructions continue to own MUST/MUST NOT policy.
- Existing Copilot/local-agent workflows remain backward compatible during migration.

### Dependencies

- CS-HARNESS-001.

---

## CS-HARNESS-003 — Introduce Developer Harness Hooks

**Priority:** P1  
**Status:** TODO

### Problem

CherryStock has deterministic guardrails inside individual implementations, but no generic repository-level hook layer around AI tool execution.

Examples of existing guardrails include MCP write confirmation, database transaction boundaries and validation rules, but these are not unified as harness lifecycle controls.

### Target

Introduce repository hooks under:

```text
.github/hooks/
```

Initial hook categories:

```text
security
validation
observability
```

Hooks should be deterministic and narrowly scoped.

### Initial Use Cases

- Reject dangerous database mutations unless explicitly authorized.
- Reject unsafe Git operations such as unapproved destructive/force operations.
- Prevent credential/secrets exposure where feasible.
- Record relevant tool execution metadata.
- Trigger or recommend focused validation after material source changes.
- Detect architecture-document changes that may require an ADR check.

### Acceptance Criteria

- Hook lifecycle and ownership are documented.
- Security-critical decisions are deterministic rather than delegated solely to the LLM.
- Hooks have bounded execution time.
- Hook failures cannot silently corrupt repository/database state.
- Sensitive arguments and credentials are not logged.
- Hooks have focused tests or reproducible validation scenarios.
- Hook behavior does not create an execution/reasoning loop.

### Dependencies

- CS-HARNESS-001.

---

## CS-HARNESS-004 — Define Semantic Tool Contracts for Agents

**Priority:** P1  
**Status:** TODO

### Problem

The current MCP server exposes useful low-level database operations such as generic SQL `query()` and privileged `execute()`.

These are suitable for engineering/admin workflows but are too low-level as the primary interface for a production Stock Analyst agent. A runtime agent should not need to understand arbitrary DuckDB schemas or construct unrestricted SQL for normal analysis.

### Target

Define semantic, business-oriented tools backed by CherryStock application services and Single Sources of Truth.

Candidate tools:

```text
get_stock_price
get_stock_indicators
get_fundamentals
get_support_resistance
get_market_breadth
get_sector_strength
get_data_quality
```

Preferred flow:

```text
Agent
  ↓
Semantic Tool
  ↓
Application Query Service
  ↓
Port / Repository
  ↓
CherryMon SSOT
```

### Acceptance Criteria

- Normal stock-analysis tools expose stable domain contracts rather than arbitrary SQL.
- Each tool has explicit input/output schemas.
- Tools use existing CherryStock SSOT views/tables where defined.
- Tool errors are structured and distinguish invalid input, unavailable data and infrastructure failure.
- Read-oriented analysis tools are separated from privileged admin/write tools.
- Tool implementations contain no duplicated business rules already owned by Domain/Application layers.
- MCP becomes an Interface-layer adapter rather than the owner of business behavior.

### Dependencies

- Architecture Backlog CS-ARCH-002 and CS-ARCH-004.

---

## CS-HARNESS-005 — Separate Read Tools from Privileged Admin Tools

**Priority:** P1  
**Status:** TODO

### Problem

A single MCP surface currently contains both read/query and database mutation capabilities.

This increases the blast radius of an autonomous agent and makes authorization policy harder to reason about.

### Target

Separate normal analysis tooling from privileged write/admin operations.

Conceptual boundary:

```text
CherryStock Analysis MCP
    read-only semantic/query tools

CherryStock Admin MCP
    mutation / DDL / maintenance operations
    explicitly privileged
```

### Acceptance Criteria

- Runtime analysis agents cannot access arbitrary database mutation by default.
- Admin/write tools require explicit privileged configuration and confirmation.
- Read and write tool capabilities are independently testable.
- Authorization decisions are enforced in deterministic code/hooks.
- Existing engineering workflows have a documented migration path.

### Dependencies

- CS-HARNESS-003.
- CS-HARNESS-004.
- Architecture Backlog CS-ARCH-004.

---

## CS-HARNESS-006 — Define Runtime Agent Tool Loop

**Priority:** P2  
**Status:** TODO

### Problem

CherryStock has deterministic orchestration workflows and developer-agent execution rules, but no explicit runtime LLM agent loop for product agents.

`run.py` and data pipelines are deterministic workflow orchestration and MUST NOT be treated as an LLM agent loop.

### Target

Define a bounded runtime loop for future Stock Analyst / Market Analyst agents:

```text
REQUEST
  ↓
CONTEXT
  ↓
MODEL DECISION
  ↓
TOOL CALL
  ↓
OBSERVATION
  ↓
EVALUATE
  ├── NEED_MORE_DATA → MODEL DECISION
  ├── COMPLETE → RESPONSE
  └── BLOCKED/FAILED → TERMINATE
```

### Required Guardrails

- maximum tool-call budget;
- maximum iteration budget;
- maximum execution duration;
- no unchanged/repeated tool call without new evidence;
- explicit terminal states;
- structured failure propagation;
- cancellation support where appropriate;
- no autonomous database mutation through the normal analysis loop.

### Acceptance Criteria

- Tool loop has a finite state machine.
- Loop termination conditions are explicit and tested.
- Agent context is represented by an explicit structure rather than uncontrolled global state.
- Tool results are recorded as observations.
- Model/provider implementation is accessed through an LLM port.
- Tool access is through a tool registry/port.
- Unit tests can run the loop using fake LLM and fake tools.
- Deterministic CherryStock pipelines remain outside the LLM loop.

### Dependencies

- Architecture Backlog CS-ARCH-003.
- CS-HARNESS-004.

---

## CS-HARNESS-007 — Introduce Runtime Working-Memory Contract

**Priority:** P2  
**Status:** TODO

### Problem

A future multi-step runtime agent needs explicit current-run state. Relying only on model context makes state difficult to inspect, test, resume or constrain.

### Target

Introduce an explicit working-memory/context object for each agent run.

Candidate state:

```text
run_id
agent_code
objective
entity/ticker
current_step
tool_observations
assumptions
remaining_budget
terminal_status
```

### Acceptance Criteria

- Working memory is scoped to one agent run.
- No cross-run global mutable state is required.
- Tool observations can be inspected independently of the model conversation.
- Working memory has a bounded size/retention strategy.
- Sensitive tool/model data is not persisted accidentally.
- Working memory can be serialized sufficiently for diagnostics or controlled handoff if required.

### Dependencies

- CS-HARNESS-006.

---

## CS-HARNESS-008 — Introduce Runtime Episodic Memory

**Priority:** P2  
**Status:** TODO

### Problem

CherryStock has strong engineering knowledge memory through Git/docs/ADRs, but there is no standardized runtime memory for previous agent analyses or decisions.

A Stock Analyst should eventually be able to answer questions such as:

```text
What changed in MWG since the previous analysis?
Which previous thesis assumptions are no longer valid?
What data caused the previous decision?
```

### Target

Define durable episodic memory separately from knowledge/document memory.

Conceptual data entities:

```text
sys_agent_run
sys_agent_event
sys_agent_memory
```

Candidate memory content:

```text
previous thesis
previous decision
confidence
important observations
assumptions
reference market state
analysis timestamp
```

### Acceptance Criteria

- Runtime memory is clearly separated into working, episodic and knowledge memory.
- Durable memory has an explicit schema and ownership.
- Memory records reference the originating `run_id`.
- Memory retrieval is scoped by agent/entity/type rather than loading all historical state.
- Retention/expiration rules are defined.
- The agent does not treat previous model output as authoritative market truth without revalidation against current SSOT data.
- Memory persistence does not duplicate canonical price/fundamental/indicator datasets.

### Dependencies

- CS-HARNESS-007.
- Database architecture review required before persistence implementation.

---

## CS-HARNESS-009 — Introduce Agent Run Identity and Correlation

**Priority:** P1  
**Status:** TODO

### Problem

Current repository search shows no standardized `run_id`, `trace_id` or correlation identifier spanning multi-step agent/tool/model execution.

Without correlation, failures and latency across model calls, tool calls and application services are difficult to reconstruct.

### Target

Every runtime agent execution receives an immutable run identifier propagated across:

```text
Agent Run
LLM calls
Tool calls
Application service calls where appropriate
Memory events
Telemetry
```

### Acceptance Criteria

- Every runtime agent run has a unique `run_id`.
- Tool and model telemetry include the originating `run_id`.
- Correlation does not depend on thread-local/global mutable state where explicit propagation is practical.
- Run identifiers are safe to log.
- Existing non-agent pipelines can adopt compatible correlation IDs incrementally without being blocked by this work.

### Dependencies

- Architecture Backlog CS-ARCH-008.

---

## CS-HARNESS-010 — Centralize Agent Observability

**Priority:** P1  
**Status:** TODO

### Problem

CherryStock has data-quality audit persistence and isolated logging, but no unified observability contract for agent, model and tool execution.

### Target

Capture structured telemetry for:

### Agent Run

```text
run_id
agent_code
started_at
completed_at
status
iteration_count
```

### LLM Call

```text
run_id
provider
model
prompt_version
input_tokens
output_tokens
latency
cost/error
```

### Tool Call

```text
run_id
tool_name
started_at
latency
status
error_type
```

Raw sensitive arguments/results should not be logged by default.

### Acceptance Criteria

- Agent, LLM and tool telemetry share correlation through `run_id`.
- Structured logging conventions are documented.
- Model/provider usage and latency are measurable.
- Tool latency/failure is measurable.
- Retry/iteration counts are observable.
- Credentials, secrets and sensitive payloads are redacted or omitted.
- Runtime log files remain excluded from Git.
- Observability implementation aligns with Architecture Backlog CS-ARCH-008 rather than creating a competing logging framework.

### Dependencies

- CS-HARNESS-009.
- Architecture Backlog CS-ARCH-008.

---

## CS-HARNESS-011 — Add Runtime Harness Hooks

**Priority:** P2  
**Status:** TODO

### Problem

Runtime agent safety and validation should not depend entirely on the model following natural-language instructions.

### Target

Introduce deterministic runtime hook contracts around agent lifecycle and tool execution.

Candidate lifecycle:

```text
before_run
after_run
before_tool_call
after_tool_call
on_tool_failure
before_memory_write
```

Candidate policies:

- tool authorization;
- input schema validation;
- write-operation denial for analysis agents;
- sensitive-data redaction;
- budget enforcement;
- telemetry emission;
- memory-write validation.

### Acceptance Criteria

- Hook interface is deterministic and independent from LLM reasoning.
- Hooks can deny a tool call before execution.
- Hook ordering is explicit.
- A hook failure has defined fail-open/fail-closed behavior; security hooks default to fail-closed.
- Hooks cannot recursively trigger uncontrolled agent loops.
- Hook execution is observable.
- Unit tests cover allow, deny and failure behavior.

### Dependencies

- CS-HARNESS-006.
- CS-HARNESS-010.

---

## CS-HARNESS-012 — Define Execution Budgets and Recovery Policy

**Priority:** P2  
**Status:** TODO

### Problem

Long-running/autonomous agents need explicit operational budgets and recovery behavior. The existing developer TestEngineer anti-loop rules are useful precedent but are not a runtime contract.

### Target

Define runtime limits for:

```text
max_iterations
max_tool_calls
max_llm_calls
max_duration
max_retries
optional token/cost budget
```

Define terminal states such as:

```text
COMPLETE
FAILED
BLOCKED
BUDGET_EXCEEDED
CANCELLED
```

### Acceptance Criteria

- Budget values are configuration-driven.
- Exceeding a budget terminates cleanly.
- Retry policy requires new evidence/material change where applicable.
- Partial observations remain available for diagnostics.
- Recovery/resume semantics are explicitly defined before implementing resumable runs.
- Agent cannot silently continue after a terminal state.

### Dependencies

- CS-HARNESS-006.
- CS-HARNESS-007.
- CS-HARNESS-009.

---

## CS-HARNESS-013 — Define Context Handoff / Compaction Strategy

**Priority:** P3  
**Status:** TODO

### Problem

Long-running tasks should not depend on retaining an indefinitely growing LLM conversation context.

### Target

Support structured handoff/compaction through artifacts/state rather than uncontrolled conversation growth.

A handoff should preserve only the information required to continue:

```text
objective
completed steps
important observations
open questions
remaining budget
relevant memory references
next allowed action
```

### Acceptance Criteria

- Handoff schema is explicit and versioned if persisted.
- Tool outputs are summarized/referenced rather than blindly copied into new context.
- Canonical market data remains in CherryMon rather than being duplicated into handoff artifacts.
- Handoff preserves `run_id` or parent/child correlation as designed.
- Compaction cannot silently change terminal decisions or factual observations.

### Dependencies

- CS-HARNESS-007.
- CS-HARNESS-008.
- CS-HARNESS-009.

---

## CS-HARNESS-014 — Add Harness Evaluation Suite

**Priority:** P3  
**Status:** TODO

### Problem

Unit tests can verify deterministic harness code but do not measure whether the complete agent harness chooses the right tools, remains grounded or behaves consistently across model/prompt changes.

### Target

Introduce `evals/` for runtime-agent evaluation when production agents are implemented.

Evaluate at least:

```text
tool-selection accuracy
tool-call efficiency
data-grounding correctness
hallucination rate
completion correctness
loop termination
memory retrieval correctness
prompt regression
model/provider regression
```

### Acceptance Criteria

- Evaluation datasets are separate from unit tests.
- Same evaluation cases can compare multiple model/provider configurations.
- Harness failures can be distinguished from model-quality failures where possible.
- Loop/iteration/tool-call metrics are recorded per evaluation case.
- Unsafe write attempts fail evaluation.
- Evaluation aligns with Architecture Backlog CS-ARCH-009 rather than introducing duplicate ownership.

### Dependencies

- CS-HARNESS-006 through CS-HARNESS-012 as applicable.
- Architecture Backlog CS-ARCH-009.

---

# Memory Model

CherryStock should explicitly distinguish three memory classes:

```text
Working Memory
  current run only
  context + observations + budgets

Episodic Memory
  previous agent runs
  thesis / decision / observations / assumptions

Knowledge Memory
  repository documentation
  ADRs
  domain knowledge
  DB metadata
  canonical CherryMon datasets
```

Rules:

- Knowledge memory MUST NOT be duplicated into episodic memory unnecessarily.
- Previous agent conclusions are evidence/history, not a replacement for current CherryMon data.
- Runtime agents MUST revalidate time-sensitive claims against current SSOT data.
- Developer engineering memory remains Git/repository based.

---

# Tool Design Rules

Runtime agent tools should prefer semantic contracts:

```text
GOOD
get_stock_indicators(ticker, timeframe)
get_fundamentals(ticker)
get_support_resistance(ticker)

AVOID AS DEFAULT RUNTIME TOOL
query("SELECT ... arbitrary SQL ...")
execute("UPDATE ...")
```

Generic SQL tools may remain available for engineering/admin workflows but should not be the default runtime analysis surface.

---

# Harness Safety Rules

1. Deterministic security policy belongs in hooks/code, not only prompts.
2. Runtime analysis agents are read-only by default.
3. Agent loops must have finite budgets and explicit terminal states.
4. No repeated unchanged tool call after failure without new evidence.
5. Tools expose stable application/domain contracts.
6. Memory never becomes a competing Source of Truth for market data.
7. Every production agent run is traceable through a run identifier.
8. Sensitive tool/model payloads are not logged by default.
9. Developer harness and runtime harness remain separately owned.
10. Deterministic data pipelines such as `run.py` remain workflows, not LLM agent loops.

---

# Suggested Implementation Order

```text
P1 — Developer harness foundation
CS-HARNESS-001 Formalize Developer Harness Architecture
CS-HARNESS-002 Native Skill Files
CS-HARNESS-003 Developer Harness Hooks

P1 — Runtime contracts / safety foundation
CS-HARNESS-004 Semantic Tool Contracts
CS-HARNESS-005 Read vs Admin Tool Separation
CS-HARNESS-009 Agent Run Identity
CS-HARNESS-010 Agent Observability

P2 — Runtime agent harness
CS-HARNESS-006 Runtime Tool Loop
CS-HARNESS-007 Working Memory
CS-HARNESS-008 Episodic Memory
CS-HARNESS-011 Runtime Hooks
CS-HARNESS-012 Execution Budgets / Recovery

P3 — Advanced harness capabilities
CS-HARNESS-013 Context Handoff / Compaction
CS-HARNESS-014 Harness Evaluation Suite
```

---

# Relationship to Architecture Backlog

This backlog is specialized for Agent Harness work and should not duplicate generic architecture ownership already tracked in `docs/backlog/Architecture_Backlog.md`.

Important relationships:

| Harness backlog | Related architecture backlog |
|---|---|
| CS-HARNESS-004 / 005 | CS-ARCH-002, CS-ARCH-004 |
| CS-HARNESS-006 | CS-ARCH-003 |
| CS-HARNESS-009 / 010 | CS-ARCH-008 |
| CS-HARNESS-014 | CS-ARCH-009 |

If a generic architecture backlog item is completed first, update this document to reference the implemented contract rather than duplicating implementation work.

---

# ADR Guidance

The following decisions should be considered cross-module architecture decisions and normally require ADRs before production implementation:

- canonical runtime agent harness architecture;
- runtime memory persistence model;
- read/admin MCP security boundary;
- agent observability/correlation contract;
- runtime tool-loop execution and recovery semantics.

Developer-only skill/hook organization may not require a separate ADR if it does not alter runtime architecture, but the Developer Harness architecture should still be documented under `docs/architecture/**`.

---

# Definition of Done for Harness Adoption

CherryStock can be considered to have an explicit production Agent Harness when all of the following are true:

```text
Tool Loop
  bounded runtime loop exists

Tools / MCP
  semantic tools + read/admin boundary exist

Skills
  repeatable procedures are discoverable task-scoped skills

Memory
  working + episodic + knowledge memory ownership is explicit

Hooks
  deterministic pre/post execution guardrails exist

Execution Environment
  runtime is reproducible and configuration-driven

Observability
  every agent/model/tool execution is correlated and measurable
```

Until then, CherryStock should be described as having a strong AI-assisted development harness and a partial runtime-agent harness foundation.
