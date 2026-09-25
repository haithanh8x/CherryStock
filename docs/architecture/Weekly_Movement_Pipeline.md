# Weekly Movement Pipeline

- **Requirement:** REQ-0036
- **Status:** IMPLEMENTED_PENDING_VALIDATION
- **Decision:** ADR-020
- **Weekly entry:** `runWeekly.py`
- **Daily entry:** `run.py` (core only)
- **Manual entry:** `scripts/run_daily_movement.py`
- **Universe:** `vw_Ticker_Active`
- **Lineage:** `ZZ_D_5_MVP → PM_ZZ_D_V2 → MovementContext`

## 1. Target Operating Model

~~~text
DAILY
run.py
  ↓
EOD / Intraday
DQ
Index / Trend / Indicators
SmartMoney
  ↓
COMMIT
  ↓
metadata export
  ↓
STOP
~~~

~~~text
WEEKLY
runWeekly.py
  ↓
MovementWeeklyPipelineService
  ↓
vw_Ticker_Active
  ↓
full-history ZigZag per ticker
  ↓
Price Movement per ticker
  ↓
Movement Profile
  ↓
MovementContext
  ↓
weekly validator
~~~

~~~text
ON DEMAND
scripts/run_daily_movement.py
  --ticker <TICKER> --force
~~~

## 2. Reuse Decision

The weekly service delegates to:

~~~text
Orchestrator.active_ticker_movement_initload.initial_load_active_ticker_movement()
~~~

This is intentional because REQ-0033 already validated the full-universe behavior.

REQ-0036 changes scheduling/orchestration, not analytical calculation.

## 3. Why Weekly

REQ-0034 selected stale tickers daily, but on a new trading day nearly every active ticker becomes
stale. ZigZag then reloads and recalculates full history for each selected ticker.

Observed daily Movement wall-clock is approximately 60 minutes.

Weekly scheduling therefore reduces normal full-universe frequency while preserving exact output
semantics.

## 4. Daily Boundary

`run.py` owns only the canonical core daily transaction.

It must not import or invoke:

~~~text
MovementDailyPipelineService
MovementWeeklyPipelineService
_run_movement_steps
~~~

The existing manual daily/on-demand script remains supported but is no longer part of normal
`run.py`.

## 5. Weekly Boundary

`runWeekly.py` owns normal Movement refresh.

For every active ticker:

~~~text
Ticker ZigZag
  BEGIN → calculate full history → COMMIT/ROLLBACK

Ticker Price Movement
  BEGIN → rebuild confirmed movement/profile → COMMIT/ROLLBACK
~~~

One ticker failure does not roll back prior successful tickers.

A weekly run with any hard failures returns a failed process state.

## 6. Movement Freshness Contract

MovementContext remains daily analytical semantics but may be operationally refreshed weekly.

Additive public fields:

~~~text
LatestOHLCDate
MovementAgeTradingDays
MovementFreshnessStatus
~~~

Anchor:

~~~text
ContextAsOfDate =
COALESCE(CurrentLegAsOfDate, ProfileAsOfConfirmedAtDate)
~~~

Age:

~~~text
MovementAgeTradingDays =
count(vw_Ticker_OHLC_D.Date > ContextAsOfDate
      AND Date <= LatestOHLCDate)
~~~

Classification:

~~~text
age = 0     → FRESH
age 1..5    → AGING
age > 5     → STALE
missing     → UNKNOWN
~~~

This is a consumer safety contract, not a trading signal.

## 7. Consumer Rule

Consumers may use FRESH or AGING according to their own tolerance, but must not assume AGING is daily-current.

Consumers requiring daily-current movement should require:

~~~text
MovementFreshnessStatus = 'FRESH'
~~~

A future StrategyContext must explicitly gate on freshness.

## 8. Weekly SLA

Expected SLA:

~~~text
MovementAgeTradingDays <= 5
~~~

If a weekly job is missed, the public context becomes STALE without mutating historical movement facts.

## 9. Manual Repair

The existing service/script remains for exceptional repair:

~~~powershell
python scripts\run_daily_movement.py --ticker MWG --force
~~~

This may refresh an individual ticker to FRESH before the next weekly universe run.

## 10. Validation

Weekly PASS requires:

- REQ-0033 structural validator PASS;
- weekly runner completes with zero failures;
- MovementContext coverage equals active eligible universe;
- no UNKNOWN freshness;
- no STALE freshness after weekly completion;
- max Movement age <=5 sessions;
- daily runner contains no Movement invocation;
- daily core regression PASS;
- on-demand refresh regression PASS;
- Archify reflects weekly scheduling.

## 11. Compatibility

No ZigZag schema change.

No Price Movement schema change.

MovementContext public view receives additive fields only.

No change to `runMonthly.py`.

## 12. Historical Design Status

REQ-0034 remains DONE as historical evidence that daily integration worked.

ADR-018 is superseded only for normal scheduling by ADR-020. Its ticker-level recovery and
transaction observations remain useful for the on-demand path.

## 13. Handoff

~~~text
DESIGN HANDOFF
Requirement: REQ-0036
Outcome: IMPLEMENTED_PENDING_VALIDATION
ADR: ADR-020
Normal Movement schedule: weekly
Daily runner: core only
Manual repair: retained
Freshness SLA: <=5 ticker trading sessions
Next owner: TestEngineer
~~~
