---
name: indicator-onboarding
description: "Execute the CherryStock technical-indicator lifecycle: discover current metadata/library support, change definition/components/D-W-M configs safely, run targeted historical backfill, validate public indicator contracts, and hand off for independent verification."
---

# CherryStock Indicator Onboarding Skill

## Owner and scope

Default owner: `.github/agents/Indicator_Management.agent.md`.

Use for:
- `NEW`;
- `ACTIVATE`;
- `NEW_PARAMETER_FAMILY`;
- `MODIFY`;
- `REPAIR`;
- `DEACTIVATE`;
- explicit permanent `DELETE`.

Canonical contracts:
- `docs/architecture/Indicator_Engine.md`;
- `docs/adr/ADR-002-indicator-source-of-truth.md`;
- `.github/instructions/indicators.instructions.md`.

Historical detail, when needed for migration archaeology only: `docs/reference/Indicator_Engine_Legacy_Reference.md`.

## Mandatory state machine

```text
DISCOVER
  ↓
PHASE 1 — METADATA / CONFIG
  ↓ PASS only
PHASE 2 — TARGETED HISTORICAL BACKFILL
  ↓ PASS only
PHASE 3 — VALIDATION
  ↓
IMPLEMENTED_PENDING_VALIDATION
  ↓
TestEngineer
```

A failed phase stops the procedure. Do not skip forward.

## Phase 0 — Discover

Before mutation:

1. Identify scenario and requested indicator/config family.
2. Read canonical architecture + indicator Instructions.
3. Inspect `src/calcEngine/indicatorRegistry.py`, `src/calcEngine/calcIndicators.py` and nearest tests when relevant.
4. Inspect current CherryMon metadata through the approved CherryMon/DuckDB MCP:
   - `dim_indicator`;
   - `dim_indicator_component`;
   - `dim_indicator_config`;
   - current fact-row coverage for affected configs;
   - `vw_Indicator_config` and `vw_Ticker_indicators` where relevant.
5. Confirm library engine/function, required inputs, parameters, warmup requirement and output mapping.
6. Confirm write/transaction tools are available before a multi-step metadata mutation.

If library resolution or output mapping is unclear, stop before changing metadata.

## Phase 1 — Metadata / configuration

For add/activate/repair/parameter-family changes:

1. Upsert `dim_indicator` idempotently.
2. Upsert all required `dim_indicator_component` rows.
3. Upsert the complete config family in `dim_indicator_config`.
4. Default production family is D/W/M unless the approved requirement explicitly scopes otherwise.
5. Use one transaction for related metadata writes.
6. Read back generated `ConfigId` values; never assume IDs are stable across environments.
7. Validate:
   - one coherent master definition;
   - function resolves;
   - RequiredInputs and ParameterSchema are compatible;
   - active component mapping is complete;
   - each parameter family has expected timeframe coverage;
   - WarmupBars is sufficient;
   - enabled configs are visible through configuration SSOT.

For `MODIFY`, do not silently change the historical meaning of an existing `ConfigCode`. Prefer a new parameter/config family when semantics change.

### Deactivate / delete

Default removal mode is `DEACTIVATE`:
- disable affected configs;
- preserve definition/components and historical facts unless explicitly approved otherwise.

Permanent delete requires explicit user/request approval after impact discovery. Delete only the affected scope, inside a transaction, in dependency order. Never truncate `cal_indicator_values` or touch unrelated ConfigIds.

## Phase 2 — Historical backfill

1. Run a targeted smoke calculation first, normally on a long-history ticker such as MWG when appropriate.
2. Resolve target ConfigIds dynamically from stable config codes/indicator metadata.
3. Call `refresh_technical_indicators()` through the approved focused script/wrapper for the affected ConfigIds.
4. Prefer targeted family backfill; do not recompute unrelated enabled configs without an explicit reason.
5. Preserve idempotent replacement/upsert semantics for the logical key:

```text
Ticker + Date + ConfigId + ComponentCode
```

6. For full-history/cumulative indicators, follow the canonical registry/architecture execution trait rather than applying an ordinary finite-window checkpoint incorrectly.

If smoke/backfill fails, stop and return the evidence; do not mark production-ready.

## Phase 3 — Validation

Validate the affected scope at minimum:

- metadata definition/component/config completeness;
- expected D/W/M coverage;
- source ticker/date coverage;
- non-empty output after valid warmup;
- numeric/value validity;
- NULL behavior;
- duplicate logical keys;
- zero-output configs;
- unexpected/missing components;
- sample values where meaningful;
- rerun/idempotency behavior;
- no unintended row changes to unrelated ConfigIds;
- public read contract through `vw_Ticker_indicators`.

Do not infer success from script exit code alone.

## MCP / write safety

- Follow `.github/instructions/database.instructions.md` for SQL/transaction safety.
- Use explicit columns; no `SELECT *`.
- Related metadata writes require an explicit transaction.
- On a mid-transaction failure, rollback before retrying.
- If the MCP exposes only read tools, stop before PHASE 1 instead of bypassing the approved write boundary.

## Evidence / handoff

Return:

```text
INDICATOR LIFECYCLE HANDOFF
Scenario:
IndicatorCode:
Affected ConfigCodes / ConfigIds:
Metadata transaction:
Backfill scope/result:
Validation summary:
Unrelated scope verified:
Outcome: IMPLEMENTED_PENDING_VALIDATION | BLOCKED | IMPLEMENTATION_FAILED
Next owner: TestEngineer | SolutionArchitect | GeneralCoding | User
```

Permanent removal additionally reports affected historical fact rows and preserved unaffected configs.

## Stop conditions

- architecture redesign needed → Solution Architect;
- supporting non-lifecycle code implementation needed → General Coding;
- any lifecycle phase fails → stop and report;
- lifecycle implementation complete → Test Engineer for independent verdict.
