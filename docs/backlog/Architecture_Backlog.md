# CherryStock Architecture Backlog

## Purpose

This backlog captures architecture improvements identified while reviewing CherryStock against a responsibility-oriented AI/application project structure.

The target is **not** to copy a generic `agent/tools/models/utils` repository layout. CherryStock should continue evolving toward a layered architecture with explicit Domain, Application, Infrastructure and Interface responsibilities.

---

## CS-ARCH-001 — Canonical runtime package under `src/cherrystock`

**Priority:** P1  
**Status:** TODO

### Problem

CherryStock currently has a new layered package:

```text
src/cherrystock/
├── application/
├── infrastructure/
└── config/
```

but it still coexists with legacy top-level runtime modules such as:

```text
src/CrawlStock
src/calcEngine
src/Chart
src/Ults
src/Orchestrator
src/Telegram
src/AiModels
src/mcp_server
src/webapp
```

This creates a hybrid architecture and makes ownership/dependency direction less explicit.

### Target

Make `src/cherrystock/**` the canonical runtime package and migrate legacy modules incrementally into:

```text
domain/
application/
infrastructure/
interfaces/
config/
```

### Acceptance Criteria

- New runtime modules are created under `src/cherrystock/**`.
- New architecture does not introduce additional top-level legacy-style packages under `src/`.
- Migration can happen feature-by-feature without a big-bang rewrite.
- Existing public behavior remains backward compatible during migration.
- Architecture documentation defines the canonical target package layout.

### Dependencies

- Architecture decision describing package ownership and dependency direction.

---

## CS-ARCH-002 — Remove direct legacy imports from Application Services

**Priority:** P1  
**Status:** TODO

### Problem

`SyncWritePipelineService` currently imports implementations directly from legacy modules including `CrawlStock`, `Ults` and `calcEngine`.

This means the Application layer still depends directly on concrete implementation details.

### Target

Introduce/complete application ports and infrastructure/domain adapters so Application Services depend on contracts instead of concrete legacy modules.

Preferred direction:

```text
Interface
   ↓
Application Service
   ↓
Application Port
   ↑
Infrastructure / Domain Adapter
```

### Acceptance Criteria

- Application Services no longer require direct imports from migrated legacy implementation modules.
- External data ingestion is accessed through explicit ports.
- Persistence is accessed through repositories / Unit of Work.
- Domain calculations have explicit ownership and reusable contracts.
- Unit tests can substitute ports without requiring real external systems.

### Dependencies

- CS-ARCH-001.

---

## CS-ARCH-003 — Refactor `AiModels` into an LLM provider layer

**Priority:** P1  
**Status:** TODO

### Problem

`src/AiModels/Qwen80b.py` currently combines model provider configuration, model selection, prompt content, execution and output handling in one script.

### Target

Move runtime LLM integration toward:

```text
src/cherrystock/
├── application/
│   └── ports/
│       └── llm.py
├── infrastructure/
│   └── llm/
│       ├── openrouter_client.py
│       └── model_registry.py
└── prompts/
```

Runtime agents should depend on an LLM port, not directly on OpenRouter or a specific model.

### Acceptance Criteria

- No runtime agent is coupled directly to a named external model/provider.
- Model/provider selection is configuration-driven.
- Prompt content is not embedded inside provider/client implementation.
- Credentials remain environment/config based.
- LLM integration is testable through a fake/mock port.

### Dependencies

- CS-ARCH-001.

---

## CS-ARCH-004 — Move MCP into the Interface Layer

**Priority:** P1  
**Status:** TODO

### Problem

`src/mcp_server/duckdb_mcp.py` currently combines transport, SQL classification, database execution, mutation confirmation and serialization.

### Target

Treat MCP as an external interface:

```text
interfaces/mcp
      ↓
application services / query services
      ↓
repositories / ports
      ↓
DuckDB
```

Separate read-oriented market/query capabilities from privileged write/admin capabilities.

### Acceptance Criteria

- MCP transport code does not own business rules.
- Read/query MCP paths use stable CherryStock views/services where applicable.
- Arbitrary mutation capabilities are isolated from normal read tooling.
- Write/admin MCP operations require explicit privileged handling.
- MCP behavior has focused automated tests.

### Dependencies

- CS-ARCH-001.
- CS-ARCH-002.

---

## CS-ARCH-005 — Migrate domain knowledge out of `.github/agents/Instructions`

**Priority:** P1  
**Status:** TODO

### Problem

The governance model states:

```text
.github/** = AI/developer governance
docs/**    = engineering/domain knowledge
```

but domain/reference knowledge still exists under files such as:

- `.github/agents/Instructions/StockTerm.md`
- `.github/agents/StockStrategies.md`
- `.github/agents/Instructions/Indicator_Engine.md`
- `.github/agents/Instructions/project_structured.md`

This creates ownership ambiguity and duplicate/legacy knowledge paths.

### Target

Move knowledge to canonical locations such as:

```text
docs/domain/**
docs/architecture/**
docs/reference/**
```

Keep `.github/agents/**` focused on agent role, workflow and routing instructions.

### Acceptance Criteria

- Domain knowledge is no longer owned by `.github/agents/Instructions/**`.
- `docs/00_HOME.md` routes to canonical knowledge files.
- Indicator architecture content is consolidated into `docs/architecture/Indicator_Engine.md`.
- Developer/AI MUST/MUST NOT rules remain under `.github/instructions/**`.
- Legacy references are removed after migration.

### Dependencies

None.

---

## CS-ARCH-006 — Eliminate legacy project-structure documentation

**Priority:** P1  
**Status:** TODO

### Problem

`.github/agents/Instructions/project_structured.md` is a generated/legacy artifact and contains stale structural documentation plus generation-output text.

It does not reflect the current layered architecture and should not remain a knowledge Source of Truth.

### Target

Replace it with canonical architecture documentation under `docs/architecture/**`, then remove the legacy reference.

### Acceptance Criteria

- Current package/module architecture is documented under `docs/architecture/**`.
- `docs/00_HOME.md` no longer links to the legacy project structure file.
- Legacy generated artifact is removed.
- No architecture rule is lost during migration.

### Dependencies

- CS-ARCH-001.

---

## CS-ARCH-007 — Reduce and dissolve generic `Ults` ownership

**Priority:** P2  
**Status:** TODO

### Problem

Generic utility folders tend to accumulate database, validation, configuration, observability and business responsibilities, increasing coupling.

CherryStock currently has several responsibilities under `src/Ults`.

### Target

Move utilities to the owning layer/domain, for example:

```text
DuckLib                  → infrastructure/database
DataQualityOrchestration → application/services
DataValidation           → application/domain validation ownership
Timing                   → observability/shared technical helper
lstPara                  → config/settings
```

### Acceptance Criteria

- New business/domain behavior is not added to `src/Ults`.
- Each migrated utility has an explicit owner.
- Imports are updated incrementally with backward-compatible shims only when necessary.
- Generic `Ults` dependency surface decreases over time.

### Dependencies

- CS-ARCH-001.

---

## CS-ARCH-008 — Add centralized observability contracts

**Priority:** P2  
**Status:** TODO

### Problem

Operational logging currently exists in isolated implementation areas, but CherryStock does not yet have a consistent observability contract for pipelines, tools and future AI agents.

### Target

Define common structured observability for:

- pipeline/workflow execution;
- data-quality failures;
- tool calls;
- AI-agent execution;
- model/provider usage;
- latency/errors/retries.

### Acceptance Criteria

- Common logging/tracing conventions are documented.
- Execution correlation/run ID exists for multi-step workflows.
- Errors are structured enough to identify failing step/component.
- Runtime logs remain excluded from Git.
- Sensitive data and credentials are not logged.

### Dependencies

- Can proceed independently.

---

## CS-ARCH-009 — Add AI evaluation layer for production agents

**Priority:** P3  
**Status:** TODO

### Problem

Automated unit/integration tests verify deterministic code but do not measure AI-agent quality or regressions across prompts/models.

### Target

Introduce an `evals/` area when stock-analysis/market-analysis agents become production capabilities.

Evaluation should cover:

- tool-selection accuracy;
- data-grounding correctness;
- hallucination rate;
- decision consistency;
- prompt regression;
- model regression.

### Acceptance Criteria

- Stable evaluation cases exist outside normal unit tests.
- The same dataset can compare multiple model/provider configurations.
- Expected decision/grounding criteria are explicit.
- Evaluation results can block unsafe/low-quality agent changes when adopted in CI.

### Dependencies

- CS-ARCH-003.
- Runtime AI agent capability.

---

## CS-ARCH-010 — Repository hygiene: remove tracked local/sensitive artifacts

**Priority:** P0  
**Status:** TODO

### Problem

Repository root currently exposes entries such as `.env`, `state.json`, `CherryStock.code-workspace` and `__pycache__` even though matching patterns are present in `.gitignore`.

Files committed before ignore rules were added remain tracked.

### Target

Remove local/generated/sensitive artifacts from Git tracking while preserving safe templates such as `.env.example`.

### Acceptance Criteria

- `.env` is not tracked.
- `state.json` is not tracked unless explicitly reclassified as a required application artifact.
- IDE-local workspace files are not tracked unless intentionally standardized.
- Python cache artifacts are not tracked.
- Any credential previously committed in `.env` is reviewed and rotated if necessary.
- `.env.example` contains only safe placeholder configuration.

### Dependencies

None.

---

## Suggested Implementation Order

```text
P0
CS-ARCH-010 Repository hygiene

P1
CS-ARCH-005 Knowledge migration
CS-ARCH-006 Legacy documentation cleanup
CS-ARCH-001 Canonical runtime package
CS-ARCH-002 Application dependency inversion
CS-ARCH-003 LLM provider layer
CS-ARCH-004 MCP interface refactor

P2
CS-ARCH-007 Reduce Ults
CS-ARCH-008 Observability

P3
CS-ARCH-009 AI evals
```

## Notes

Backlog entries describe planned work only. When a design is approved, the resulting architecture contract must be written to `docs/architecture/**` and material cross-module decisions must be captured in `docs/adr/**` before or together with implementation.
