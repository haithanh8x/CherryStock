---
applyTo: "src/CrawlStock/**/*.py,src/Orchestrator/**/*.py,scripts/*crawl*.py"
---

# Crawler / Ingestion Instructions

This file defines mandatory rules for external-data ingestion pipelines.

Canonical knowledge:
- `docs/architecture/Data_Architecture.md`
- relevant source/integration architecture under `docs/architecture/`
- operational guidance under `docs/runbook/`

## Agent routing
- Unclear source behavior, data requirement, freshness rule, scope or acceptance criteria → `.github/agents/BusinessAnalyst.agent.md`.
- New ingestion architecture, integration contract or cross-pipeline design → `.github/agents/SolutionArchitect.agent.md`.
- Clear crawler/ingestion implementation following approved contracts → `.github/agents/GeneralCoding.agent.md`.
- Test design/execution or independent data-pipeline validation → `.github/agents/TestEngineer.agent.md`.

General Coding MUST preserve documented source and persistence contracts, update canonical materials when an approved contract changes, and end with `IMPLEMENTED_PENDING_VALIDATION`.

## Pipeline contract
Preferred flow:

```text
source adapter
    ↓
fetch
    ↓
normalize
    ↓
validate
    ↓
upsert/persist
    ↓
data-quality audit
    ↓
orchestration result
```

## Rules
- Keep source-specific parsing inside source adapters/modules.
- Normalize external schemas before downstream persistence when practical.
- Do not silently swallow network, parsing, schema or persistence failures.
- Retry only errors that are reasonably transient; avoid retrying deterministic schema/validation failures without change.
- Reuse project DuckDB transaction/access conventions from `database.instructions.md`.
- Upserts should be idempotent and keyed explicitly.
- Log source, target dataset, requested period, records fetched/written and final status without secrets.
- Validation and audit persistence must remain separate concerns.
- WARNING may continue according to pipeline policy; FAIL must be surfaced clearly.
- Scheduling/orchestration belongs in orchestration modules, not inside source parsers.

## Validation
Verify where applicable:
- source response is not unexpectedly empty;
- required fields exist;
- dates/tickers/keys normalize correctly;
- duplicates are handled intentionally;
- expected trading date/freshness is correct;
- rerun does not duplicate rows;
- partial failure does not leave inconsistent multi-step writes.

If a source contract changes, update the relevant architecture/data documentation rather than hiding the change inside parser code.