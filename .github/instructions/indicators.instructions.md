---
applyTo: "src/calcEngine/**/*.py,scripts/*indicator*.py,src/DuckDB/**/*indicator*.sql"
---

# Indicator Engine Instructions

This file defines mandatory constraints for technical-indicator lifecycle, calculation and validation. The repeatable procedure lives in `.github/skills/indicator-onboarding/SKILL.md`.

Canonical knowledge:
- `docs/architecture/Indicator_Engine.md`;
- `docs/adr/ADR-002-indicator-source-of-truth.md`;
- current generated database metadata under `docs/reference/`.

## Routing

- Concrete indicator lifecycle → `.github/agents/Indicator_Management.agent.md` + `indicator-onboarding` Skill.
- Broad Indicator Engine redesign → `.github/agents/SolutionArchitect.agent.md` + `architecture-design` Skill.
- Supporting contract-preserving implementation → `.github/agents/GeneralCoding.agent.md`.
- Independent validation → `.github/agents/TestEngineer.agent.md`.

Indicator lifecycle ownership has priority over General Coding.

## Source-of-Truth contracts

- `dim_indicator`: master definition/runtime-library contract.
- `dim_indicator_component`: output component contract.
- `dim_indicator_config`: executable parameters/timeframe config.
- `vw_Indicator_config`: configuration SSOT.
- `cal_indicator_values`: internal long-format calculated persistence.
- `vw_Ticker_indicators`: public/calculated indicator SSOT.

Downstream code MUST use `vw_Ticker_indicators` instead of direct `cal_indicator_values` access when the public view satisfies the use case.

## Mandatory lifecycle invariants

- New indicators MUST be metadata/config driven when the existing engine supports that model.
- Adding an indicator MUST NOT require a new fact table or ALTER of a wide indicator fact schema.
- Do not create one table per indicator.
- Do not hard-code one new branch per indicator into `run.py`; library/function resolution belongs in the registry/config architecture.
- `RequiredInputs`, `ParameterSchema`, config `Parameters`, component mapping and library function MUST be mutually compatible.
- Active multi-output indicators MUST have complete component mapping.
- Default production config family MUST include D/W/M unless an approved requirement explicitly scopes otherwise.
- `WarmupBars` MUST be sufficient for the calculation contract.
- Config IDs MUST be resolved from stable metadata; do not assume numeric IDs are portable across environments.
- Prefer targeted ConfigId backfill; unrelated indicators MUST NOT be recomputed without reason.
- Logical-key reruns MUST remain idempotent:

```text
Ticker + Date + ConfigId + ComponentCode
```

## Mutation safety

- Related definition/component/config changes MUST use one explicit transaction.
- If the approved MCP exposes only read capability, lifecycle mutation MUST stop rather than bypass the write boundary.
- Never truncate `cal_indicator_values` as part of onboarding/repair/removal.
- Removal defaults to deactivation. Permanent delete requires explicit authorization and MUST be scoped to affected configs/dependencies only.
- A failed lifecycle phase MUST stop later phases.

Database SQL/transaction rules additionally follow `.github/instructions/database.instructions.md`.

## Generated/current context

Before metadata changes, use:
- `docs/reference/DB_Metadata.md` for current physical schema evidence;
- current generated indicator metadata snapshots for actual master/component/config rows;
- CherryMon MCP for live current-state evidence when available.

Generated reference material is evidence, not target-design ownership.

## Minimum validation constraints

Before lifecycle implementation is handed off as ready, verify the affected scope:

- definition/component/config completeness;
- expected D/W/M coverage;
- function/input/parameter compatibility;
- output exists after valid warmup when source history is sufficient;
- value/NULL behavior is valid;
- logical keys have no unintended duplicates;
- expected components are present and no unexpected components appear;
- source-to-output ticker/date coverage is reasonable for the contract;
- unrelated ConfigIds are not modified unexpectedly;
- rerun/idempotency behavior is preserved;
- `vw_Ticker_indicators` exposes the expected public result.

Final independent verdict belongs to Test Engineer.

## Procedure

For the exact Discover → Metadata → Backfill → Validate procedure, use:

```text
.github/skills/indicator-onboarding/SKILL.md
```

Historical long-form material has been moved out of Agent governance to:

```text
docs/reference/Indicator_Engine_Legacy_Reference.md
```

That file is historical/reference context only. New architecture belongs in `docs/architecture/Indicator_Engine.md`; new mandatory rules belong here; new repeatable lifecycle steps belong in the Skill.
