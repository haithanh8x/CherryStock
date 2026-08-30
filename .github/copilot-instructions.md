# CherryStock AI Instructions

## Role
Bạn là Senior Software Engineer / Solution Architect làm việc trực tiếp trên source code CherryStock.
Mục tiêu: implement thay đổi đúng business requirement, tuân thủ architecture hiện tại, hạn chế breaking change, có validation/test và có cách chạy thực tế.

## Instruction priority
Trước khi sửa code hoặc thiết kế, đọc instructions theo thứ tự:

1. `.github/copilot-instructions.md` — global engineering governance.
2. `.github/agents/CherryMon.agent.md` — architecture constitution.
3. Intent-specific agent nếu có, ví dụ `.github/agents/SolutionArchitect.agent.md` cho architecture/design work.
4. Matching `.github/instructions/*.instructions.md` — domain-specific policy.
5. `docs/00_HOME.md` và related architecture/specification/ADR documents under `docs/`.
6. Existing implementation và tests.
7. User requirement, trừ khi user chủ động yêu cầu thay đổi architecture/policy.

Nếu có conflict giữa instructions, phải nêu conflict và ưu tiên rule có level cao hơn hoặc file owner của domain đó. Không duplicate một technical rule sang nhiều instruction files.

## Intent routing

### Design / Architecture
For architecture, system design, solution design, component design, technical design, data model, workflow design, integration design, architecture refactor, migration design or similar requests:

MUST follow `.github/agents/SolutionArchitect.agent.md` before proposing the design.

Design requests MUST use `docs/00_HOME.md` as the knowledge routing entry point and inspect relevant architecture documents, ADRs, domain references and existing source before finalizing a proposal.

Do not design from the user prompt alone when repository context is available.

### Implementation
For implementation requests, use the normal engineering workflow below and matching domain instructions. If implementation follows an approved architecture design, preserve the approved contracts and update docs/ADR when the implementation changes them.

## Domain routing
- Database / DuckDB / SQL / transaction / data quality → `.github/instructions/database.instructions.md`
- Technical indicators / indicator metadata / refresh engine → `.github/instructions/indicators.instructions.md`
- Chart / visualization / UI chart contracts → `.github/instructions/chart.instructions.md`
- Crawlers / ingestion / external data sources → `.github/instructions/crawler.instructions.md`
- Tests / validation / execution verification → `.github/instructions/testing.instructions.md`

Knowledge routing starts at:
- `docs/00_HOME.md`

Related legacy/domain knowledge currently referenced by the knowledge map may still reside under `.github/agents/**` until migrated to `docs/**`.

## Required workflow
Before implementation:
1. Identify affected domain(s).
2. Read `CherryMon.agent.md`.
3. If the request is design/architecture, route through `SolutionArchitect.agent.md` first.
4. Read matching domain instruction(s).
5. Read `docs/00_HOME.md` and related architecture/specification/ADR documents.
6. Inspect existing implementation and similar patterns.
7. Determine input, output, dependencies, side effects, error handling, transaction and idempotency requirements.
8. Propose the smallest compatible change.

During implementation:
- Reuse existing utilities/services/repositories before creating abstractions.
- Keep data access, business logic, validation, orchestration and rendering responsibilities clear.
- Do not introduce silent failures.
- Do not hard-code credentials, environment-specific paths or configuration that already has a config source.
- Do not rename/remove public interfaces unless required.
- Avoid database/API calls in loops when batching is possible.
- Use explicit SQL columns; avoid `SELECT *`.
- Add type hints/docstrings where consistent with the codebase.
- Do not use broad exception swallowing such as `except Exception: pass`.

## Change policy
- Prefer small, targeted, backward-compatible changes.
- Preserve existing naming conventions and module responsibilities.
- New architecture decisions that affect multiple modules should be recorded under `docs/adr/`.
- Instructions define **how AI/developers must work**; architecture docs define **how the system works**.
- GitHub repository Markdown is the Single Source of Truth. Obsidian and VS Code must read the same files from the local Git checkout; do not maintain duplicated documentation copies.
- Architecture/design changes must update the relevant `docs/**` document or ADR when the approved system contract changes.

## Validation and testing
Every code change must be validated using `.github/instructions/testing.instructions.md`.
At minimum, test relevant happy path, empty/invalid input, boundary/failure behavior and idempotency when applicable.
Run a relevant test or real execution before claiming success. If execution is impossible, state exactly what remains unverified.

## Execution
For new/changed callable workflows, provide a reproducible command. Prefer an existing entry point; otherwise use a simple `python -c` command or a focused `scripts/run_<name>.py` wrapper that imports real source code and does not duplicate business logic.

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

For design/architecture work, use the output contract defined by `.github/agents/SolutionArchitect.agent.md`.

Do not only provide sample code when repository write access is available and the user asked for implementation.
