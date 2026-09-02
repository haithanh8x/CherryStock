# CherryStock Agent Harness — Governance and Routing

## Purpose
This file is the mandatory repository-level entry point for CherryStock AI-assisted work.

It defines global governance, intent classification, specialist routing, ownership priority, handoff contracts, bounded execution and material ownership.

The default repository agent acts as task orchestrator. Specialist agents own their defined outcomes. Canonical Agent Harness architecture is documented at `docs/architecture/agent-harness/README.md`.

## Instruction priority
Trước khi sửa code hoặc thiết kế, đọc instructions theo thứ tự:

1. .github/copilot-instructions.md — global engineering governance.
2. .github/agents/CherryMon.agent.md — architecture constitution.
3. Intent-specific agent nếu có:
   - .github/agents/BusinessAnalyst.agent.md cho requirement analysis, clarification, acceptance criteria và backlog.
   - .github/agents/SolutionArchitect.agent.md cho architecture/design.
   - .github/agents/Indicator_Management.agent.md cho concrete indicator lifecycle.
   - .github/agents/GeneralCoding.agent.md cho clear general implementation.
   - .github/agents/TestEngineer.agent.md cho test design, validation runbook, reproduce bug, performance test hoặc execution verification.
4. Matching .github/instructions/*.instructions.md — domain-specific policy.
5. docs/00_HOME.md và related architecture/specification/ADR documents under docs/.
6. Existing implementation và tests.
7. User requirement, trừ khi user chủ động yêu cầu thay đổi architecture/policy.

Nếu có conflict giữa instructions, phải nêu conflict và ưu tiên rule có level cao hơn hoặc file owner của domain đó. Không duplicate một technical rule sang nhiều instruction files.

## Intent routing

### Mandatory Agent Selection

Before executing a task, classify its primary intent and select the authoritative agent below. Do not bypass a mandatory specialist agent when its scope matches.

| Primary intent | Authoritative agent |
| --- | --- |
| Requirement analysis, clarification, scope, business rules, acceptance criteria, backlog creation/refinement or requirement decomposition | `.github/agents/BusinessAnalyst.agent.md` |
| Onboard, add, activate, modify, repair, deactivate, or delete a technical indicator, its components, metadata, parameter/config family, or D/W/M configuration | `.github/agents/Indicator_Management.agent.md` |
| Architecture, system design, solution design, technical design, structural refactor, integration design, data architecture, MCP architecture, or AI/agent architecture | `.github/agents/SolutionArchitect.agent.md` |
| Clear implementation, focused bug fix, contract-preserving refactor, code/config/SQL/script/documentation change not owned end-to-end by a domain agent | `.github/agents/GeneralCoding.agent.md` |
| Test design, test execution, validation, regression, reproduction, cross-check, acceptance, performance, or execution verification | `.github/agents/TestEngineer.agent.md` |

Agent selection defines WHO owns the task. Matching `.github/instructions/*.instructions.md` files still define domain rules, and `docs/**` remains the engineering knowledge Source of Truth.

### Business Analysis / Requirement Management

For requirement analysis, clarification, scope definition, business rules, acceptance criteria, backlog creation/refinement, impact discovery or requirement decomposition, MUST follow `.github/agents/BusinessAnalyst.agent.md`.

Durable requirement output belongs under `docs/backlog/requirements/`.

Do not require Business Analyst for a small explicit change when behavior, scope and acceptance criteria are already clear. Business Analyst owns requirement readiness; it does not design architecture, implement code or claim test verdicts.

### Indicator Management

For onboarding a new indicator or modifying any existing indicator lifecycle artifact, MUST follow `.github/agents/Indicator_Management.agent.md` before making metadata, calculation, backfill, activation, deactivation, or deletion changes.

This includes:
- new indicator or new output component;
- changes to indicator definition, calculation parameters, warmup, metadata, or library mapping;
- new or modified parameter/config family;
- changes to D/W/M configuration coverage;
- activation, repair, targeted backfill, deactivation, or permanent deletion;
- validation of `dim_indicator`, `dim_indicator_component`, `dim_indicator_config`, `vw_Indicator_config`, or `vw_Ticker_indicators` as part of an indicator lifecycle change.

`Indicator_Management.agent.md` is the authoritative owner for indicator lifecycle operations. Do not implement these changes directly through the general implementation workflow.

A broad redesign of the Indicator Engine remains owned by `SolutionArchitect.agent.md`; the Solution Architect MUST consult the Indicator Management contract for indicator-domain constraints. A request to design or onboard one concrete indicator remains owned by `Indicator_Management.agent.md`.

### Design / Architecture
For architecture, system design, solution design, component design, technical design, data model, workflow design, integration design, architecture refactor, migration design or similar requests:

MUST follow .github/agents/SolutionArchitect.agent.md before proposing the design.

Design requests MUST use docs/00_HOME.md as the knowledge routing entry point and inspect relevant architecture documents, ADRs, domain references and existing source before finalizing a proposal.

Do not design from the user prompt alone when repository context is available.

### Testing / Validation
For test case design, regression test, test plan/runbook, pytest design, reproduce bug, local cross-check, UI/performance test, acceptance test or execution verification:

MUST follow .github/agents/TestEngineer.agent.md and .github/instructions/testing.instructions.md.

Testing tasks MUST be finite and bounded:
- one objective at a time;
- one active hypothesis at a time;
- explicit retry budget;
- explicit PASS / FAIL / BLOCKED / REGRESSION;
- explicit KEEP / REVERT / STOP action;
- no automatic transition to another hypothesis after a terminal verdict.

### Implementation
For a clear implementation request not owned end-to-end by a specialist domain agent, MUST follow `.github/agents/GeneralCoding.agent.md` and matching domain instructions.

If implementation follows an approved architecture design, preserve the approved contracts and update docs/ADR when the implementation changes them.

General Coding normally ends with `IMPLEMENTED_PENDING_VALIDATION` and hands off to Test Engineer. It must not self-declare final PASS.

## Agent ownership and handoff

When multiple agents appear relevant, use this ownership priority:

1. Domain-specific agent for a concrete domain lifecycle operation.
2. Business Analyst when requirement quality/readiness is the primary objective.
3. Solution Architect for broad architecture or cross-module design.
4. General Coding for clear implementation not owned end-to-end by a domain agent.
5. Test Engineer for independent validation and test-focused work.

Default handoff:
- Unclear/material new request: `BusinessAnalyst` → `READY_FOR_DESIGN` or `READY_FOR_IMPLEMENTATION`.
- Requirement needing design: `BusinessAnalyst` → `SolutionArchitect` → `GeneralCoding` or domain owner → `TestEngineer`.
- Clear implementation: `GeneralCoding` → `IMPLEMENTED_PENDING_VALIDATION` → `TestEngineer`.
- Indicator lifecycle change: `Indicator_Management` → implementation/backfill → `TestEngineer` validation.
- Test-only request: `TestEngineer` owns the task and returns a finite verdict.

Examples:
- "Phân tích requirement và tạo backlog cho cảnh báo cổ phiếu" → `BusinessAnalyst.agent.md`.
- "Sửa lỗi nhỏ đã có acceptance criteria" → `GeneralCoding.agent.md`.
- "Thêm / onboard indicator RSI" → `Indicator_Management.agent.md`.
- "Thiết kế indicator RSI mới" → `Indicator_Management.agent.md`; consult architecture rules only when needed.
- "Thiết kế lại Indicator Engine" → `SolutionArchitect.agent.md`; consult Indicator Management for lifecycle constraints.
- "Test Indicator Engine sau refactor" → `TestEngineer.agent.md`.

## Domain routing
- Requirement analysis / clarification / backlog / acceptance criteria → .github/agents/BusinessAnalyst.agent.md + docs/backlog/requirements/
- Clear general implementation / bug fix / contract-preserving refactor → .github/agents/GeneralCoding.agent.md + matching domain instruction(s)
- Database / DuckDB / SQL / transaction / data quality → .github/instructions/database.instructions.md
- Technical indicator lifecycle / metadata / components / config families / activation / backfill / deactivation / deletion → .github/agents/Indicator_Management.agent.md + .github/instructions/indicators.instructions.md
- Broad Indicator Engine architecture or cross-module redesign → .github/agents/SolutionArchitect.agent.md + .github/instructions/indicators.instructions.md
- Chart / visualization / UI chart contracts → .github/instructions/chart.instructions.md
- Crawlers / ingestion / external data sources → .github/instructions/crawler.instructions.md
- Tests / validation / execution verification → .github/instructions/testing.instructions.md + .github/agents/TestEngineer.agent.md

Knowledge routing starts at:
- docs/00_HOME.md

Related legacy/domain knowledge currently referenced by the knowledge map may still reside under .github/agents/** until migrated to docs/**.

## Required workflow
Before implementation:
1. Identify affected domain(s).
2. Read CherryMon.agent.md.
3. Select the mandatory specialist using the Intent routing and ownership priority above.
4. If requirement readiness is the objective or material ambiguity exists, route through BusinessAnalyst.agent.md first.
5. If the request is a concrete indicator lifecycle change, route through Indicator_Management.agent.md first.
6. If the request is broad design/architecture, route through SolutionArchitect.agent.md first.
7. If the request is a clear implementation, route through GeneralCoding.agent.md.
8. If the request is test design/execution, route through TestEngineer.agent.md first.
9. Read matching domain instruction(s).
10. Read docs/00_HOME.md and related requirement/architecture/specification/ADR documents.
11. Inspect existing implementation and similar patterns.
12. Determine input, output, dependencies, side effects, error handling, transaction and idempotency requirements.
13. Propose the smallest compatible change.

During implementation:
- Reuse existing utilities/services/repositories before creating abstractions.
- Keep data access, business logic, validation, orchestration and rendering responsibilities clear.
- Do not introduce silent failures.
- Do not hard-code credentials, environment-specific paths or configuration that already has a config source.
- Do not rename/remove public interfaces unless required.
- Avoid database/API calls in loops when batching is possible.
- Use explicit SQL columns; avoid SELECT *.
- Add type hints/docstrings where consistent with the codebase.
- Do not use broad exception swallowing such as except Exception: pass.

## Anti-loop execution governance
These rules apply to any AI/local-agent execution, not only tests:

1. Define one current objective before making changes.
2. Do not repeat the same analysis, file read, command or edit unless new evidence justifies it.
3. Never rerun the same failing command unchanged.
4. Default maximum two repair attempts for the same defect unless the user explicitly requests deeper investigation.
5. If two materially equivalent attempts fail, classify BLOCKED/FAIL and stop.
6. Do not broaden scope opportunistically.
7. A terminal verdict ends the current execution path.
8. A new hypothesis requires a new explicit task or a runbook that explicitly authorizes the next step.

## Change policy
- Prefer small, targeted, backward-compatible changes.
- Preserve existing naming conventions and module responsibilities.
- New architecture decisions that affect multiple modules should be recorded under docs/adr/.
- Instructions define how AI/developers must work; architecture docs define how the system works.
- GitHub repository Markdown is the Single Source of Truth. Obsidian and VS Code must read the same files from the local Git checkout; do not maintain duplicated documentation copies.
- Architecture/design changes must update the relevant docs/** document or ADR when the approved system contract changes.

## Validation and testing
Every code change must be validated using .github/instructions/testing.instructions.md.
For focused test-design or execution work, also use .github/agents/TestEngineer.agent.md.
At minimum, test relevant happy path, empty/invalid input, boundary/failure behavior and idempotency when applicable.
Run a relevant test or real execution before claiming success. If execution is impossible, state exactly what remains unverified.

## Execution
For new/changed callable workflows, provide a reproducible command. Prefer an existing entry point; otherwise use a simple python -c command or a focused scripts/run_<name>.py wrapper that imports real source code and does not duplicate business logic.

## Final response format
For implementation work use this concise structure:

### Analysis
- Existing flow
- Relevant files
- Implementation approach

### Changes
- File / function / change

### Validation
- Rules validated

### Tests
- Commands executed
- Result

### Execute
- Reproducible command

### Notes
- Assumptions / remaining risks

For requirement/backlog work, use the output contract defined by .github/agents/BusinessAnalyst.agent.md.
For design/architecture work, use the output contract defined by .github/agents/SolutionArchitect.agent.md.
For general implementation work, use the output contract defined by .github/agents/GeneralCoding.agent.md.
For test-design/execution work, use the output contract defined by .github/agents/TestEngineer.agent.md.

Do not only provide sample code when repository write access is available and the user asked for implementation.
