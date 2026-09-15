# REQ-0027 — Price Movement Character V1 Implementation Note

## Handoff state

```text
Owner: GeneralCoding.agent.md
Outcome: IMPLEMENTED_PENDING_VALIDATION
Next owner: TestEngineer.agent.md
```

Requirement:
`docs/backlog/requirements/REQ-0027-price-movement-characterization.md`

Approved architecture:
`docs/architecture/Price_Movement_Character.md`

ADR:
`docs/adr/ADR-012-price-movement-character-as-separate-analytics-domain.md`

Local validation runbook:
`docs/runbook/Price_Movement_Character_V1.md`

## Implemented scope

V1 now includes:

- domain swing/state calculation under `src/cherrystock/domain/analytics/price_movement/**`;
- adaptive ATR + percentage-floor reversal confirmation;
- separate pivot date and confirmation date;
- provisional daily state;
- magnitude, velocity and persistence features/scores;
- same-ticker/same-direction historical percentile scoring;
- explainable movement-character labels;
- additive/idempotent DuckDB schema + metadata seed;
- confirmed swing and daily point-in-time persistence;
- three public read contracts;
- `PriceMovementRepository` inside caller-owned `DuckDBUnitOfWork`;
- full historical rebuild and incremental checkpoint refresh;
- canonical daily orchestration between Indicators and SmartMoneyScore;
- DataValidation hook for daily persistence;
- read-only historical contract validator;
- targeted local runner, full initload runner and read-only inspect tool;
- focused unit and pipeline-order tests;
- detailed local runbook.

## Incremental safety

Incremental refresh resumes only from a usable persisted `PROVISIONAL` state.

If an active ticker has no usable checkpoint, the implementation rebuilds that ticker from full source history instead of inferring a swing state from a truncated window.

Historical source corrections before the latest checkpoint are intentionally repaired with targeted full rebuild:

```powershell
python scripts\run_price_movement.py --mode full --ticker MWG
```

## Point-in-time semantics

Confirmed swing knowledge follows:

```text
PivotEndDate <= ConfirmedAtDate
```

Historical scoring for daily date `D` only uses same-direction events with:

```text
ConfirmedAtDate < D
```

The current unconfirmed leg is persisted as:

```text
SwingStatus = PROVISIONAL
```

## Indicator contract

ATR is consumed through:

```text
vw_Indicator_config
vw_Ticker_indicators
```

No numeric `ConfigId` is treated as portable. `ATR14_D` is preferred when enabled; otherwise the enabled daily ATR VALUE contract is resolved from metadata.

When ATR is unavailable:

```text
ThresholdSource = PCT_FALLBACK
QualityStatus = PARTIAL
ATRNormMagnitude = NULL
```

## Transaction contract

Price Movement does not call COMMIT/ROLLBACK internally.

Daily runtime path:

```text
run.py
→ DuckDBUnitOfWork
→ SyncWritePipelineService
→ Indicators
→ Price Movement Character
→ SmartMoneyScore
→ Data Quality
→ UoW COMMIT / ROLLBACK
```

Full initload also uses a single UoW and validates the historical contract before commit.

## Developer verification

Pure domain synthetic verification was executed during implementation for:

- pivot date vs confirmation date;
- smooth vs noisy persistence evidence;
- same-direction score generation;
- insufficient-history state.

Result observed during developer implementation:

```text
4 passed
```

This is developer evidence only and is not the independent TestEngineer verdict.

DuckDB physical migration/backfill/runtime validation must be executed on the user's local CherryMon database using:

`docs/runbook/Price_Movement_Character_V1.md`.

## Known operational constraints

- V1 is daily only.
- Current feature calculation recomputes the active leg path to preserve transparent point-in-time metrics; full initload should be smoke-tested on selected tickers before all-universe execution.
- Incremental mode does not automatically detect historical OHLC/ATR corrections before its persisted checkpoint; use targeted full repair when upstream history changes.
- Price Movement labels describe price-path character only and must not be treated as Smart Money intent.

## TestEngineer acceptance focus

Independent validation should cover at least:

1. focused pytest suite;
2. schema rerun idempotency;
3. full MWG rebuild;
4. full active-universe initload;
5. duplicate-key invariants;
6. pivot/confirmation ordering;
7. same-direction alternation;
8. historical-count no-look-ahead invariant;
9. public-view row contract;
10. incremental rerun equivalence/no duplicate;
11. `run.py` ordering and rollback behavior;
12. Data Quality audit persistence.
