# Daily Incremental Movement Pipeline

- **Requirement:** REQ-0034
- **Status:** IMPLEMENTED_PENDING_VALIDATION
- **Decision:** ADR-018
- **Daily entry:** run.py
- **Service:** src/cherrystock/application/services/movement_daily_pipeline.py
- **Universe:** vw_Ticker_Active
- **Lineage:** ZZ_D_5_MVP → PM_ZZ_D_V2 → MovementContext

## 1. Target Runtime

~~~text
run.py
  │
  ├─ Phase A — canonical daily shared transaction
  │    EOD / Intraday / DQ
  │    Index / Trend / Indicators
  │    SmartMoney
  │         ↓
  │       COMMIT
  │
  └─ Phase B — MovementDailyPipelineService
       │
       ├─ set-based plan
       │    LatestOHLCDate
       │    vs ZigZagAsOfDate
       │    + ZigZag/PriceMovement lineage parity
       │
       ├─ stale ZigZag ticker
       │      full-history deterministic ZigZag rebuild
       │      ticker transaction
       │
       ├─ stale Price Movement only
       │      skip ZigZag
       │
       └─ Price Movement
              refresh only if confirmed lineage changed
              ticker transaction
                    ↓
            MovementContext derived dynamically
~~~

## 2. Why Post-Commit

The existing daily UoW must commit first so Movement can read newly synchronized EOD through
independent reader/writer connections.

Movement intentionally uses a different failure domain:

- core daily transaction remains atomic;
- Movement is isolated per ticker;
- Movement failure causes the process to report failure, but does not undo successfully committed
  EOD/Indicator/SmartMoney data.

## 3. Incremental Selection Contract

Planner reads all active tickers set-wise and classifies:

~~~text
NO_OHLC
SOURCE_REWIND
FORCED
MISSING_ZIGZAG
STALE_ZIGZAG
STALE_PRICE_MOVEMENT
UP_TO_DATE
LIMITED_OUT
~~~

Primary date rule:

~~~text
LatestOHLCDate > ZigZagAsOfDate
    → STALE_ZIGZAG
~~~

Recovery rule:

~~~text
LatestOHLCDate = ZigZagAsOfDate
AND ZigZag confirmed lineage != Price Movement/profile lineage
    → STALE_PRICE_MOVEMENT
~~~

Aligned rerun:

~~~text
LatestOHLCDate = ZigZagAsOfDate
AND confirmed lineage aligned
    → UP_TO_DATE
    → no write
~~~

## 4. ZigZag Execution Strategy

REQ-0034 V1 does not introduce stateful bar-by-bar advancement.

For a selected ZigZag ticker:

~~~text
load full canonical OHLC
→ existing calculate_zigzag()
→ replace ticker-local ZigZag persistence
~~~

This deliberately favors exact equivalence with the validated REQ-0033 initial-load output.

A later optimization may introduce stateful incremental advancement only after proving exact
parity against full rebuild across historical replay.

## 5. Price Movement Incremental Rule

After ZigZag is current, compare:

~~~text
ZigZag:
  SwingCount
  LastSwingSeq
  LastConfirmedAtDate
  confirmed swing geometry

Price Movement:
  SwingCount
  LastSwingSeq
  LastConfirmedAtDate
  copied confirmed swing geometry

Movement Profile:
  ProfileRows
  LastSwingSeq
  AsOfConfirmedAtDate
~~~

Only refresh Price Movement when these confirmed contracts disagree.

If only the provisional current leg changes:

~~~text
Price Movement = UP_TO_DATE
MovementContext = changes dynamically via vw_Ticker_ZigZag_Current
~~~

## 6. Recovery Semantics

If a previous run committed ZigZag but Price Movement failed:

~~~text
ZigZagAsOfDate == LatestOHLCDate
Price Movement lineage stale
        ↓
STALE_PRICE_MOVEMENT
        ↓
repair Price Movement only
~~~

This makes same-day retry self-healing for downstream failures.

## 7. Source Rewind

If:

~~~text
LatestOHLCDate < ZigZagAsOfDate
~~~

the pipeline does not mutate that ticker and reports SOURCE_REWIND.

This prevents silently rebuilding a calculated state from an unexpectedly truncated source.

## 8. Same-Date Corrections

Current canonical OHLC does not expose a row mutation timestamp/version suitable for deterministic
same-date change detection.

Therefore:

~~~text
same Date + corrected values
→ not automatically detectable by date watermark
→ use --force for repair
~~~

Standalone maintenance:

~~~powershell
python scripts\run_daily_movement.py --ticker MWG --force
~~~

## 9. Transaction Model

~~~text
Phase A:
BEGIN
  core daily pipeline
COMMIT

Phase B:
Ticker A ZigZag       BEGIN → COMMIT/ROLLBACK
Ticker A PriceMove    BEGIN → COMMIT/ROLLBACK
Ticker B ZigZag       BEGIN → COMMIT/ROLLBACK
...
~~~

If Phase B has failures, run.py raises after the service finishes so scheduling/operations sees
a failed run while preserving already committed data.

## 10. Validation

Structural validator requires:

- all active tickers have OHLC;
- all active tickers have ZigZag current state;
- LatestOHLCDate <= ZigZagAsOfDate, with equality expected after current daily load;
- no source rewind;
- exact ZigZag ↔ Price Movement swing row-count and confirmed-geometry parity;
- one current Movement Profile for every ticker with confirmed swing;
- profile lineage equals latest confirmed ZigZag lineage;
- one MovementContext row for every Movement Profile.

## 11. Operational Interfaces

Normal:

~~~powershell
python run.py
~~~

Standalone plan:

~~~powershell
python scripts\run_daily_movement.py --dry-run
~~~

Forced repair:

~~~powershell
python scripts\run_daily_movement.py --ticker MWG --force
~~~

Validator:

~~~powershell
python scripts\validate_daily_movement.py
~~~

## 12. Compatibility

- REQ-0033 initial-load scripts remain valid.
- Existing ZigZag/Price Movement formulas are unchanged.
- No DuckDB schema migration is introduced.
- SmartMoney daily order/contract is unchanged.
- MovementContext remains derived.

## 13. Handoff

~~~text
DESIGN HANDOFF
Requirement: REQ-0034
Outcome: IMPLEMENTED_PENDING_VALIDATION
ADR: ADR-018
Daily transaction: core commit first
Movement transaction: ticker/stage isolated
Incremental unit: ticker selection + Price Movement lineage
ZigZag V1 execution: deterministic full-history per selected ticker
Next owner: TestEngineer
~~~
