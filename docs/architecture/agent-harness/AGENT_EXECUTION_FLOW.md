# CherryStock ADLC — Agent Execution Flow and Repository Material Map

## Purpose

This document is the detailed execution companion to `docs/architecture/agent-harness/README.md`.

The README defines the canonical ADLC control model, ownership and gates. This file explains **how each CherryStock agent actually runs**, which `.md` files it must read, which repository folders it may update, what each material is for, and where the handoff goes next.

The synchronized visualization is:

```text
docs/architecture/diagrams/cherrystock-adlc-agent-harness.workflow.json
        ↓ Archify validate + deliver
docs/architecture/generated/CherryStock_ADLC_Agent_Harness.html
```

---

## 1. Shared bootstrap order

Every routed CherryStock task starts from the same control stack. The intent-specific agent changes, but the governance order does not.

```text
User request
  ↓
.github/copilot-instructions.md
  ↓
.github/agents/CherryMon.agent.md
  ↓
intent-specific .github/agents/*.agent.md
  ↓
matching .github/instructions/*.instructions.md
  ↓
docs/00_HOME.md
  ↓
smallest relevant docs/** set
  ↓
existing source / SQL / tests / runbooks
```

### File purposes

| File / folder | Purpose |
|---|---|
| `.github/copilot-instructions.md` | Executable ADLC router and repository-level governance. Classifies intent, selects one authoritative owner, defines handoff/gate rules and anti-loop policy. |
| `.github/agents/CherryMon.agent.md` | Stable architecture constitution. Defines module responsibilities, dependency principles, Source-of-Truth rules and the high-level agent/domain routing map. |
| `.github/agents/*.agent.md` | Defines **WHO owns an outcome**, what context that agent must inspect, its workflow, boundaries, terminal states and handoff contract. |
| `.github/instructions/*.instructions.md` | Defines **HOW a domain must execute safely**. These are mandatory execution constraints, not outcome owners. |
| `.github/skills/**` | Reusable specialized authoring/tool procedure. Example: `chart-authoring/SKILL.md`. |
| `docs/00_HOME.md` | Durable knowledge router. Agents use it to locate the smallest relevant architecture, ADR, requirement, development and runbook materials. |
| `docs/**` | Engineering knowledge Source of Truth for how CherryStock works and why durable decisions exist. |
| `src/**` | Runtime implementation. |
| `scripts/**` | Focused initialization, migration, backfill, rendering and standalone execution helpers. |
| `tests/**` | Executable automated validation. |

---

## 2. Agent roster and execution contract

### 2.1 Default Repository Agent / ADLC Router

**Control file:** `.github/copilot-instructions.md`

This is the orchestration layer. It does not replace a specialist agent.

Flow:

```text
interpret user intent
  → identify affected domain
  → classify primary intent
  → select authoritative agent
  → load mandatory shared governance
  → load the smallest domain context
  → preserve upstream gate + acceptance criteria
  → hand off
  → consolidate terminal result for the user
```

Primary routing:

- requirement ambiguity/readiness → `BusinessAnalyst.agent.md`;
- architecture/design → `SolutionArchitect.agent.md`;
- concrete indicator lifecycle → `Indicator_Management.agent.md`;
- chart recommendation / Flint authoring → `Chart.agent.md`;
- clear implementation → `GeneralCoding.agent.md`;
- test/validation → `TestEngineer.agent.md`.

The router normally writes no duplicate domain document. Its job is coordination and context preservation.

---

### 2.2 CherryMon Architecture Constitution

**File:** `.github/agents/CherryMon.agent.md`

This file participates in every serious route as a **shared constitution**, not as a normal task owner.

It defines:

- module responsibilities such as `src/calcEngine`, `src/Chart`, `src/CrawlStock`, `src/DuckDB`, `src/Orchestrator`, `src/Ults`;
- dependency direction principles;
- database naming conventions (`raw_*`, `cal_*`, `dim_*`, `vw_*`, `sys_*`);
- key CherryMon public/data contracts;
- agent-harness routing and domain instruction routing;
- repository knowledge architecture.

If actual repository structure intentionally diverges from this constitution, architecture documentation must be updated rather than silently ignoring the mismatch.

---

### 2.3 BusinessAnalyst.agent.md

**Owner:** requirement quality and backlog readiness.

Mandatory reads:

```text
.github/copilot-instructions.md
.github/agents/CherryMon.agent.md
docs/00_HOME.md
docs/backlog/requirements/**
relevant docs/architecture/** and docs/adr/**
matching .github/instructions/*.instructions.md when domain constraints matter
existing implementation only as evidence of current behavior
```

Execution:

```text
FRAME
  objective · problem · target outcome · stakeholders
    ↓
DEFINE
  functional requirements · business rules · scope · constraints · risks
    ↓
MAKE TESTABLE
  deterministic acceptance criteria
    ↓
DECOMPOSE / ROUTE
  stable REQ id · next owner · architecture-needed? · validation owner
```

Durable output:

```text
docs/backlog/requirements/REQ-<number>-<short-name>.md
```

Template:

```text
docs/backlog/requirements/REQUIREMENT_TEMPLATE.md
```

Folder purpose: `docs/backlog/requirements/**` is the canonical location for durable business/functional requirements. It is not the runtime Source of Truth after implementation.

Exit states:

- `READY_FOR_DESIGN` → `SolutionArchitect.agent.md`;
- `READY_FOR_IMPLEMENTATION` → `GeneralCoding.agent.md` or authoritative domain agent;
- `NEEDS_CLARIFICATION` / `DRAFT` → remains with BA;
- `BLOCKED` → router/user decision.

BA does not create architecture, edit production code or claim a test verdict.

---

### 2.4 SolutionArchitect.agent.md

**Owner:** design readiness, architecture contracts and durable architecture decisions.

Mandatory reads:

```text
.github/copilot-instructions.md
.github/agents/CherryMon.agent.md
ready docs/backlog/requirements/REQ-*.md when available
docs/00_HOME.md
relevant docs/architecture/**
relevant docs/adr/**
matching .github/instructions/*.instructions.md
existing source / SQL / tests / similar implementation patterns
```

Execution:

```text
CONTEXT
  identify requirement, domains, current Source of Truth
    ↓
CURRENT STATE
  components · data flow · dependencies · persistence · constraints
    ↓
PROPOSED DESIGN
  responsibilities · contracts · data model · failure handling · observability
    ↓
DECISION CHECK
  ownership · duplication · compatibility · migration · ADR need
    ↓
ARCHIFY SYNCHRONIZATION
  typed source + generated HTML + validation
```

Durable outputs:

```text
docs/architecture/**
docs/adr/**                                  # when a durable cross-module decision is required
docs/architecture/diagrams/**               # Archify typed source
docs/architecture/generated/**              # generated presentation only
```

Important distinction:

- `docs/architecture/**` and `docs/adr/**` contain architecture meaning and decisions;
- `docs/architecture/generated/**` is presentation output and is never edited as the Source of Truth;
- Archify is the Solution Architect's visualization/validation tool, not an architecture authority.

Exit:

```text
APPROVED_FOR_IMPLEMENTATION
```

Only after the design document, ADR when needed, Archify typed source and generated artifact are synchronized and validated.

Next owner: `GeneralCoding.agent.md` or the authoritative domain agent.

---

### 2.5 Indicator_Management.agent.md

**Owner:** concrete technical-indicator lifecycle.

Mandatory context:

```text
docs/architecture/Indicator_Engine.md
.github/instructions/indicators.instructions.md
.github/agents/Instructions/Indicator_Engine.md   # remaining legacy detailed reference
src/calcEngine/indicatorRegistry.py
src/calcEngine/calcIndicators.py
current CherryMon indicator metadata/data via cherrymon-duckdb MCP
```

Purpose of the main materials:

- `docs/architecture/Indicator_Engine.md` — canonical indicator architecture contract;
- `indicators.instructions.md` — mandatory indicator execution/safety rules;
- legacy `Instructions/Indicator_Engine.md` — detailed operational reference not yet fully migrated;
- `src/calcEngine/**` — actual calculation engine evidence;
- CherryMon DuckDB metadata/views — current indicator configuration/data evidence.

Execution:

```text
DISCOVER
  scenario + current definition/components/configs + D/W/M coverage
    ↓
PHASE 1 — CONFIG METADATA
  transactional definition/component/config upsert via MCP
    ↓
PHASE 2 — HISTORICAL BACKFILL
  targeted refresh_technical_indicators() wrapper; MWG smoke first
    ↓
PHASE 3 — VALIDATION
  coverage · dates · nulls · duplicates · zero outputs · sample values
```

Primary data contracts include:

```text
dim_indicator
dim_indicator_component
dim_indicator_config
cal_indicator_values
vw_Indicator_config
vw_Ticker_indicators
```

Exit:

```text
IMPLEMENTED_PENDING_VALIDATION
  → TestEngineer.agent.md
```

If supporting engine code outside the lifecycle needs an approved implementation, route that code scope to `GeneralCoding.agent.md`.

---

### 2.6 Chart.agent.md

**Owner:** chart recommendation, visualization decision and Flint chart authoring/rendering.

Mandatory context:

```text
.github/copilot-instructions.md
.github/agents/CherryMon.agent.md
.github/instructions/chart.instructions.md
.github/skills/chart-authoring/SKILL.md
docs/architecture/Chart_Architecture.md
relevant requirement/domain docs from docs/00_HOME.md
actual dataset/query/schema or chart-ready contract
```

Purpose:

- `Chart.agent.md` — owns the analytical visualization outcome;
- `chart.instructions.md` — production/domain chart execution rules;
- `chart-authoring/SKILL.md` — detailed Flint authoring procedure;
- `Chart_Architecture.md` — reusable chart/application architecture contract;
- actual data contract — prevents invented chart semantics.

Execution:

```text
UNDERSTAND analytical question + grain + fields
  ↓
RECOMMEND best chart + bounded alternatives
  ↓
MAP TO FLINT chart type / backend / channels
  ↓
TRANSFORM input when required
  ↓
VALIDATE with flint/validate_chart
  ↓
RENDER / COMPILE
  ↓
SANITY CHECK
```

Outcomes:

- `CHART_RECOMMENDATION_READY`;
- `CHART_SPEC_READY`;
- `CHART_RENDERED`;
- `NEEDS_DATA_TRANSFORM`;
- `NEEDS_REQUIREMENT_CLARIFICATION`;
- `NEEDS_ARCHITECTURE_DECISION`;
- `UNSUPPORTED_BY_FLINT`;
- `BLOCKED`.

Advisory/spec/render may be terminal. Production application integration hands the approved chart/data-transform contract to `GeneralCoding.agent.md`, then independent validation can follow.

---

### 2.7 GeneralCoding.agent.md

**Owner:** clear implementation not owned end-to-end by a specialist domain agent.

Mandatory reads:

```text
.github/copilot-instructions.md
.github/agents/CherryMon.agent.md
ready requirement when present
approved architecture / ADR when applicable
matching .github/instructions/*.instructions.md
relevant canonical docs routed from docs/00_HOME.md
existing implementation + nearest similar patterns
nearest tests and execution entry points
```

Execution:

```text
CONFIRM
  objective · accepted material · AC · affected files
    ↓
INSPECT
  flow · contracts · dependencies · side effects · idempotency
    ↓
IMPLEMENT
  smallest backward-compatible change
    ↓
UPDATE MATERIALS
  canonical docs / runbooks / requirement linkage / ChangeRequest
    ↓
DEVELOPER VERIFICATION
  narrowest meaningful check
    ↓
HANDOFF
  exact changed scope + commands + evidence + risks
```

Primary outputs:

```text
src/**
scripts/**
tests/** when implementation-side test change is in scope
existing canonical docs
docs/development/implementation-notes/** only when non-obvious detail needs a durable note
docs/ChangeRequest/** for release/change traceability when applicable
```

Exit:

```text
IMPLEMENTED_PENDING_VALIDATION
  → TestEngineer.agent.md
```

General Coding cannot self-declare `PASS`.

Escalation:

- unclear expected behavior → BA;
- new Source of Truth/public contract/cross-module boundary → SA;
- concrete indicator lifecycle → Indicator Management.

---

### 2.8 TestEngineer.agent.md

**Owner:** independent evidence-backed validation verdict.

Mandatory reads:

```text
.github/copilot-instructions.md
.github/agents/CherryMon.agent.md
.github/instructions/testing.instructions.md
related requirement + acceptance criteria
GeneralCoding/domain implementation handoff
docs/00_HOME.md
matching domain instructions
relevant architecture / ADR / specification
production code under test
nearest tests / runbooks
```

Execution state machine:

```text
DEFINE
  ↓
PREPARE
  ↓
EXECUTE
  ↓
EVALUATE
  ├── PASS → COMPLETE
  ├── FAIL → bounded focused repair/retest → COMPLETE
  └── BLOCKED → REPORT → COMPLETE
```

Validation depth is selected using `.github/instructions/testing.instructions.md`:

- `BUG FAST VALIDATION`;
- `INTEGRATION VALIDATION`;
- `FULL RELEASE / MONTHLY VALIDATION`.

Primary evidence locations:

```text
tests/**
docs/runbook/** when a reproducible manual/operational procedure is durable
execution logs / command evidence referenced by the handoff
```

Terminal verdict owner:

```text
PASS | FAIL | BLOCKED | REGRESSION
```

Feedback routing:

- missing/ambiguous acceptance criteria → BA;
- architecture decision gap → SA;
- current implementation defect/regression → GeneralCoding or authoritative domain owner;
- external dependency/environment block → router/user.

---

## 3. Domain instruction map

| Domain | Mandatory instruction | Purpose |
|---|---|---|
| DuckDB / SQL / transaction / data quality | `.github/instructions/database.instructions.md` | Database safety, connection/transaction patterns, data-quality rules and SQL conventions. |
| Technical indicators | `.github/instructions/indicators.instructions.md` | Indicator metadata/config/backfill/public-view execution contract. |
| Chart / visualization | `.github/instructions/chart.instructions.md` | Chart/data-contract/integration rules. |
| Crawler / ingestion | `.github/instructions/crawler.instructions.md` | External-source ingestion constraints and operational rules. |
| Python | `.github/instructions/python.instructions.md` | Python execution/convention constraints. |
| Testing | `.github/instructions/testing.instructions.md` | Minimum sufficient evidence, finite validation and retry policy. |
| Archify | `.github/instructions/archify.instructions.md` | Typed-source, validation, generated-artifact and architecture synchronization rules. |

A domain instruction does not own the task. It constrains whichever agent currently owns the outcome.

---

## 4. Folder purpose in the ADLC trace

```text
.github/
  copilot-instructions.md       router/governance
  agents/                       WHO owns outcomes
  instructions/                 HOW domain execution must behave
  skills/                       reusable specialist procedure/tool contract

docs/
  00_HOME.md                    knowledge navigation entry point
  backlog/requirements/         BA durable requirement contract
  architecture/                 SA durable system/design Source of Truth
  architecture/diagrams/        Archify typed sources
  architecture/generated/       generated presentation only
  adr/                          durable architecture decisions
  development/                  development workflow + non-obvious implementation guidance
  runbook/                      reproducible operational/test procedures
  ChangeRequest/                change/release traceability
src/                            runtime implementation
scripts/                        focused execution / migration / backfill / render utilities
tests/                          executable validation
```

Canonical evidence chain:

```text
User intent
  → REQ-* / accepted explicit request
  → architecture / ADR / approved contracts when required
  → implementation diff
  → test/runbook evidence
  → PASS | FAIL | BLOCKED | REGRESSION
```

---

## 5. Canonical flows

### Material or initially unclear change

```text
User
  → Default Repository Agent
  → BusinessAnalyst.agent.md
  → READY_FOR_DESIGN
  → SolutionArchitect.agent.md
  → APPROVED_FOR_IMPLEMENTATION
  → GeneralCoding.agent.md or authoritative domain agent
  → IMPLEMENTED_PENDING_VALIDATION
  → TestEngineer.agent.md
  → PASS | FAIL | BLOCKED | REGRESSION
  → Router → User / failed-outcome owner
```

### Clear bounded implementation

```text
User → Router → GeneralCoding.agent.md → TestEngineer.agent.md → verdict
```

### Concrete indicator lifecycle

```text
User
  → Router
  → Indicator_Engine.md + indicators.instructions.md
  → Indicator_Management.agent.md
  → IMPLEMENTED_PENDING_VALIDATION
  → TestEngineer.agent.md
  → verdict
```

BA or SA is inserted only when requirement ambiguity or architecture change justifies it.

### Chart advisory

```text
User
  → Router
  → Chart_Architecture.md + chart.instructions.md + chart-authoring/SKILL.md
  → Chart.agent.md
  → CHART_RECOMMENDATION_READY / CHART_SPEC_READY / CHART_RENDERED
  → User
```

### Chart production integration

```text
Chart.agent.md
  → approved chart/data-transform contract
  → GeneralCoding.agent.md
  → IMPLEMENTED_PENDING_VALIDATION
  → TestEngineer.agent.md
  → verdict
```

---

## 6. Archify generation and maintenance

Typed source:

```text
docs/architecture/diagrams/cherrystock-adlc-agent-harness.workflow.json
```

Generated presentation:

```text
docs/architecture/generated/CherryStock_ADLC_Agent_Harness.html
```

Local render wrapper:

```powershell
.\scripts\render_archify_agent_harness.ps1
```

GitHub render workflow:

```text
.github/workflows/render-archify-agent-harness.yml
```

Maintenance rule: whenever routing, an agent contract, gate, mandatory context, file ownership or folder purpose changes, update this execution map and the Archify typed source in the same change set, then regenerate the HTML. Do not manually patch generated HTML.