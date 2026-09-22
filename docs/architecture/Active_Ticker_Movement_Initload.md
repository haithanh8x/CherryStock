# Active Ticker Movement Initial Load

- **Requirement:** REQ-0033
- **Status:** DONE — TESTENGINEER_PASS_KEEP
- **Owner:** .github/agents/SolutionArchitect.agent.md
- **Universe:** "CherryMon"."main"."vw_Ticker_Active"
- **ZigZag config:** ZZ_D_5_MVP
- **Price Movement config:** PM_ZZ_D_V2
- **Operational mode:** manual initial load / rerun; not in run.py

## 1. Purpose

Promote the already validated per-ticker ZigZag → Price Movement path from MWG-only execution
to the complete active ticker universe without changing analytical semantics.

This is an orchestration rollout, not a new indicator or segmentation model.

## 2. End-to-End Flow

~~~text
vw_Ticker_Active
      ↓ normalize / distinct / sort
Active ticker universe
      ↓
STAGE 1 — ZigZag
      │
      ├─ vw_Ticker_OHLC_D
      │       ↓
      ├─ refresh_zigzag_ticker()
      │       ↓
      ├─ cal_zigzag_pivot
      └─ cal_zigzag_current_leg
              ↓ commit ticker

STAGE 2 — Price Movement
      │
      ├─ vw_Ticker_ZigZag_Swings
      │
      ├─ swing_count > 0
      │       ↓
      │  refresh_price_movement_ticker()
      │       ↓
      │  cal_price_movement_swing
      │  cal_price_movement_profile
      │
      └─ swing_count = 0
              ↓
         clear stale Price Movement
         SKIPPED_NO_CONFIRMED_SWING

Public contracts
      ↓
vw_Ticker_ZigZag_*
vw_Ticker_Price_Movement_Swings
vw_Ticker_Movement_Profile
      ↓
vw_Ticker_Movement_Context
(derived automatically; no backfill)
~~~

## 3. Universe Contract

Canonical source:

~~~sql
SELECT DISTINCT
    UPPER(TRIM(CAST(Ticker AS VARCHAR))) AS Ticker
FROM "CherryMon"."main"."vw_Ticker_Active"
WHERE Ticker IS NOT NULL
  AND TRIM(CAST(Ticker AS VARCHAR)) <> ''
ORDER BY Ticker;
~~~

REQ-0033 intentionally does not substitute vw_Ticker, raw EOD symbol lists or hard-coded ticker arrays.

The runtime fails with a clear contract error if the view or Ticker column is unavailable.

## 4. ZigZag Reuse

src/calcEngine/zigzag.py now exposes:

~~~python
refresh_zigzag_ticker(connection=..., ticker=...)
~~~

The existing refresh_zigzag_mwg(...) remains a backward-compatible wrapper.

No ZigZag algorithm changes are made. The active configuration is still:

~~~text
ZZ_D_5_MVP
DeviationPct = 5%
Pivot source = HIGH_LOW
Confirmation source = CLOSE
~~~

REQ-0033 does not consume V1.1 calibration or V2 regime-aware research outputs.

## 5. Price Movement Reuse

Existing generic function refresh_price_movement_ticker(...) is reused.

A new maintenance helper clear_price_movement_ticker(...) removes stale PM_ZZ_D_V2 rows when
current ZigZag has no confirmed swings.

This is required for idempotent whole-universe rebuilds.

## 6. Transaction Model

A full-universe transaction would make one bad ticker roll back all prior work and is therefore rejected.

Transaction grain:

~~~text
Ticker A ZigZag       BEGIN → calculate/write → COMMIT/ROLLBACK
Ticker B ZigZag       BEGIN → calculate/write → COMMIT/ROLLBACK
...
Ticker A PriceMove    BEGIN → calculate/write → COMMIT/ROLLBACK
Ticker B PriceMove    BEGIN → calculate/write → COMMIT/ROLLBACK
...
~~~

Consequences:

- one ticker failure does not lose completed tickers;
- Price Movement failure does not erase the ticker's committed ZigZag;
- rerun replaces ticker-local persistence deterministically.

## 7. Failure Semantics

Hard failures:

~~~text
FAILED_NO_OHLC
FAILED
~~~

Hard failures contribute to non-zero process exit status.

Valid skip:

~~~text
SKIPPED_NO_CONFIRMED_SWING
~~~

This means ZigZag completed but the ticker has not yet produced a confirmed swing under the
5% config. Price Movement stale rows are cleared and this status does not fail the whole run.

Dependent skip:

~~~text
SKIPPED_ZIGZAG_FAILED
~~~

Price Movement is not attempted when ZigZag failed.

## 8. Canary Modes

Full active universe is the default:

~~~powershell
python scripts\initload\init_reload_zigzag_price_movement_active.py
~~~

One or more active tickers:

~~~powershell
python scripts\initload\init_reload_zigzag_price_movement_active.py --ticker MWG --ticker FPT
~~~

Deterministic first N:

~~~powershell
python scripts\initload\init_reload_zigzag_price_movement_active.py --limit 20
~~~

Optional fail-fast is intended for diagnosis only.

## 9. Evidence Contract

Optional output directory contains:

~~~text
Active_Ticker_Movement_Initload_Detail.csv
Active_Ticker_Movement_Initload_Summary.json
Active_Ticker_Movement_Validation_Coverage.csv
Active_Ticker_Movement_Validation_Summary.json
~~~

Canonical validation evidence path:

~~~text
docs/reference/data/price_movement/active/
~~~

Evidence should only be committed after TestEngineer PASS.

## 10. Validation Gates

Full-universe PASS requires:

1. active universe non-empty;
2. every active ticker has daily OHLC;
3. every active ticker with OHLC has exactly one ZigZag current row;
4. every ticker with ZigZag swings has exact Price Movement swing-count parity;
5. every ticker with ZigZag swings has exactly one Movement Profile;
6. zero-swing tickers retain zero Price Movement swing/profile rows;
7. focused tests PASS;
8. unchanged rerun remains structurally idempotent;
9. daily pipeline regression PASS;
10. run.py remains unchanged.

The gate is structural/data-contract validation, not investment-performance validation.

## 11. Operational Boundary

REQ-0033 does not authorize:

- adding ZigZag or Price Movement to run.py;
- daily automatic refresh;
- promoting calibrated or regime-aware deviation;
- Strategy integration.

A later daily rollout must define incremental/warmup behavior and separate DQ/transaction policy.

## 12. Main Artifacts

~~~text
src/calcEngine/zigzag.py
src/calcEngine/priceMovement.py
src/Orchestrator/active_ticker_movement_initload.py
scripts/initload/init_reload_zigzag_price_movement_active.py
scripts/validate_movement_active.py
tests/test_active_ticker_movement_initload.py
docs/runbook/Active_Ticker_Movement_Initload.md
~~~

## 13. Validation Closure

Full-universe validation completed on 2026-09-22:

- 349 active tickers;
- 349/349 ZigZag;
- 349/349 Price Movement;
- 349/349 MovementContext downstream;
- zero OHLC gaps;
- zero structural validation failures;
- idempotent business row counts;
- daily pipeline regression 3/3 PASS;
- run.py unchanged.

Evidence commit: `7e872c1b5b51834e8cec8f847bf6658fa03e9167`.

## 14. Handoff

~~~text
DESIGN HANDOFF
Requirement: REQ-0033
Outcome: DONE — TESTENGINEER_PASS_KEEP
Universe: vw_Ticker_Active
ZigZag: ZZ_D_5_MVP
Price Movement: PM_ZZ_D_V2
Transaction boundary: one ticker per stage
Daily pipeline: unchanged
Next owner: None
~~~
