# R/S V2.4 Monthly Full Source Effectiveness

## Purpose

Operational runbook for the monthly full-universe R/S V2.4 Source Effectiveness refresh.

Primary CLI entry point:

~~~text
scripts/run_rs_v2_4_full_evaluation.py
~~~

Orchestration implementation:

~~~text
src/Orchestrator/rs_v2_4_full_evaluation.py
~~~

The script is a thin wrapper. The Orchestrator service reuses:

~~~text
scripts/run_rs_v2_3_evaluation.py
scripts/run_rs_v2_4_source_effectiveness.py
scripts/promote_rs_v2_4_source.py
~~~

It does not duplicate R/S calculation logic and does not automatically change runtime weights or provider registration.

## Monthly Default

Run from repository root:

~~~powershell
python scripts/run_rs_v2_4_full_evaluation.py
~~~

Default behavior:

~~~text
Universe              raw_lstTicker.status='Y' ∩ eligible raw_stock_eod tickers
Minimum history       500 bars
Freshness tolerance   5 market trading bars
Lookback              3 years
Snapshot step         5 trading bars
Horizons              5,10,20,40
Scopes                SOURCE_CONFIG,SOURCE_FAMILY
Promotion             dry-run
Resume                enabled
~~~

The script automatically resolves a safe evaluation_end.

For the largest default horizon H40, the evaluation end is the trading date that leaves at least 40 later market trading dates available as future outcome evidence.

Therefore the latest raw market date is not automatically used as the evaluation snapshot end.

## Understanding Snapshots and Horizons

The monthly evaluator does not test every trading date by default.

With:

```text
Snapshot step = 5
```

it samples approximately every fifth trading bar:

```text
snapshot #1
+5 trading bars
snapshot #2
+5 trading bars
snapshot #3
...
```

For each sampled historical date, the system:

```text
1. calculates the R/S ladder point-in-time;
2. freezes that signal;
3. looks forward over a selected horizon;
4. labels what actually happened to the level.
```

Default horizons:

| Horizon | Meaning |
|---|---|
| H5 | next 5 trading bars |
| H10 | next 10 trading bars |
| H20 | next 20 trading bars |
| H40 | next 40 trading bars |

The horizons are future observation windows, not different model versions.

### What is evaluated

For each historical S/R level, the evaluator records behavior such as:

```text
Touch
Hold
Break
Retest
Directional Edge
```

Example:

```text
Snapshot
Ticker = MWG
Date   = 2026-05-04
S1     = 55
R1     = 62
```

Under H20, the evaluator checks the next 20 market trading bars to determine whether S1/R1 were touched, held, broken or retested.

### What the percentages mean

After many historical events are collected, the framework calculates empirical historical rates.

Example:

```text
Touch Rate             = 42%
Hold Rate given touch  = 68%
Break Rate given touch = 32%
Retest Rate given break= 47%
```

These percentages summarize historical evidence.

They do not automatically mean:

```text
Current MWG R1 has exactly 32% probability of breaking.
```

Current V2.4 does not provide a calibrated per-current-level probability model.

The correct distinction is:

```text
Historical Rate
    = observed frequency in historical evaluation events

Predictive Probability
    = calibrated forecast for a specific current ticker/level/horizon
```

Only the first is currently part of the V2.4 evaluation contract.

A future probability-calibration layer may use these historical events to estimate outputs such as:

```text
P(Break R1 within H20)
P(Hold S1 within H10)
P(Retest after break within H20)
```

but such probabilities must not be inferred directly from aggregate historical rates without calibration.

### Why H40 changes evaluation_end

If H40 is requested, each snapshot requires 40 future market bars to label its outcome.

Therefore the evaluator intentionally reserves 40 later trading bars and moves evaluation_end backward from latest_data_date.

This is required to avoid:

```text
immature outcomes
censored labels
look-ahead leakage
```


## Monthly Flow

~~~text
Resolve latest market date
        ↓
Reserve future outcome bars
        ↓
Resolve active ticker universe
raw_lstTicker.status='Y'
        ↓
Apply history + freshness eligibility
        ↓
Baseline H5 / H10 / H20 / H40
        ↓
Resolve current R/S source catalog
        ↓
SOURCE_CONFIG ablation
        ↓
Source Effectiveness
        ↓
Promotion Gate dry-run
        ↓
SOURCE_FAMILY ablation
        ↓
Family Effectiveness
        ↓
Promotion Gate dry-run
        ↓
vw_RS_Source_Effectiveness
~~~

One baseline is reused by every ablation for the same horizon.

## Source Catalog

Indicator-backed current sources are resolved from:

~~~text
"CherryMon"."main"."vw_Indicator_config"
~~~

using active/enabled metadata.

Current R/S mapping:

~~~text
MA price-level configs with runtime lengths 20/50/100/200
    → TREND_AVERAGE / LEVEL

BB active price-level components
    → VOLATILITY_BAND / LEVEL

ATR active D configs
    → VOLATILITY_CONTEXT / CONTEXT

RSI active D/W/M configs
    → MOMENTUM_CONFIRMATION / CONFIRMATION
~~~

Current structural/volume source contracts are also included:

~~~text
SWING_HIGH
SWING_LOW
PREV_WEEK_HIGH
PREV_WEEK_LOW
PREV_MONTH_HIGH
PREV_MONTH_LOW
HIGH_52W
LOW_52W

VP_POC
VP_HVN
VP_LVN
~~~

LEVEL source-config evaluation requires that the canonical source appears in baseline historical lineage.

CONTEXT and CONFIRMATION sources remain eligible without direct LEVEL lineage because they are evaluated marginally.

For SOURCE_FAMILY ablation, the full discovered family membership is excluded, not only one selected config.

`--skip-source-keys` suppresses config-level evaluation for those keys; it does not weaken a SOURCE_FAMILY ablation by removing family members from the exclusion set.

### Active ticker universe

The monthly default universe is:

~~~text
raw_lstTicker.status = 'Y'
        ∩
ticker has raw_stock_eod history
        ∩
minimum history bars satisfied
        ∩
freshness gate satisfied
~~~

Inactive tickers remain in historical EOD storage but are excluded from new monthly full-evaluation runs.

Explicit `--tickers` overrides are also validated against the same active/history/freshness eligibility set.

### Historical provider warm-up

Ticker eligibility and snapshot eligibility are separate contracts.

A ticker can have >=500 bars over the complete evaluation dataset while its earliest snapshot inside the requested window still has insufficient point-in-time history for a provider.

Current hard warm-up contract:

~~~text
VOLUME_PROFILE
min_records = 30 valid positive-volume OHLCV bars
lookback    = max(540 calendar days, window_bars * 3)
~~~

Historical evaluation therefore:

~~~text
sample every N bars from requested window
        ↓
check enabled-provider warm-up at each sampled date
        ↓
skip immature sampled dates
        ↓
evaluate only mature point-in-time snapshots
~~~

The sampling cadence remains anchored to the original requested window; warm-up filtering does not re-base or shift the cadence.

The monthly `expected_snapshot_count` uses the same shared warm-up selector as the historical evaluator so plan, persistence and resume metadata remain consistent.

This does not change live R/S runtime behavior. Direct Volume Profile calculation with insufficient history still fails its normal validation contract.

## Plan Before Running

To resolve the current evaluation window and universe without launching historical child jobs:

~~~powershell
python scripts/run_rs_v2_4_full_evaluation.py --plan-only
~~~

Review:

~~~text
run_prefix
start
evaluation_end
latest_data_date
future_outcome_bars_reserved
universe_filter = raw_lstTicker.status='Y'
ticker_count
horizons
scopes
promotion_mode
~~~

## Focused Smoke

Before the first monthly full run, use a bounded single-source smoke:

~~~powershell
python scripts/run_rs_v2_4_full_evaluation.py --tickers MWG,FPT,HPG --horizons 20 --only-source-keys MA50_D --scopes SOURCE_CONFIG --promotion-mode dry-run --run-prefix RSV24FULL_SMOKE_20260902
~~~

Expected terminal output includes:

~~~text
"monthly_full_evaluation_status": "COMPLETED"
"ticker_count": 3
"source_count": 1
"horizons": [20]
"promotion_mode": "dry-run"
"public_view": "\"CherryMon\".\"main\".\"vw_RS_Source_Effectiveness\""
~~~

A valid evidence-driven result may still be RESEARCH or REJECTED. That is not an orchestration failure.

## Resume After Interruption

Default:

~~~text
--resume = true
~~~

Run the same command again.

The orchestrator checks deterministic child run IDs.

A child evaluation run is reused only when:

~~~text
Status = COMPLETED
+
DatasetStart matches
+
DatasetEnd matches
+
HorizonBars matches
+
TickerCount matches
+
SnapshotCount matches
+
completed event ticker universe matches
+
include/exclude source contract matches
~~~

Effectiveness runs additionally require matching baseline/ablation/source/scope metadata.

If a deterministic run ID exists with incompatible metadata, the script stops with a resume-collision error.

It does not silently reuse incompatible evidence.

## Monthly Run IDs

Default prefix:

~~~text
RSV24FULL_<YYYYMM>_E<evaluation_end>_S<snapshot_step>_U<universe_hash>
~~~

Example:

~~~text
RSV24FULL_202609_E20260708_S5_U1A2B3C4D
~~~

Examples of child runs:

~~~text
..._BASE_H20
..._ABL_SRC_MA50_D_H20
..._EFF_SRC_MA50_D_H20

..._ABL_FAM_TREND_AVERAGE_H20
..._EFF_FAM_TREND_AVERAGE_H20
~~~

Ablation model versions include a deterministic hash of excluded source membership. This prevents a source-family membership change from being silently treated as the same ablation specification.

## Promotion Mode

### Default

~~~powershell
python scripts/run_rs_v2_4_full_evaluation.py --promotion-mode dry-run
~~~

The Source Promotion Gate is evaluated but no audit decision is persisted.

### Audit

To persist governance decisions:

~~~powershell
python scripts/run_rs_v2_4_full_evaluation.py --promotion-mode audit
~~~

Audit mode calls the existing promotion runner with deterministic decision IDs and --apply.

Even audit mode must not mutate:

~~~text
Indicator Engine metadata
R/S provider registry
runtime weights
production model deployment
~~~

### Skip

~~~powershell
python scripts/run_rs_v2_4_full_evaluation.py --promotion-mode skip
~~~

Use only when the objective is effectiveness refresh without promotion evaluation.

## Useful Overrides

Explicit date window:

~~~powershell
python scripts/run_rs_v2_4_full_evaluation.py --start 2023-01-01 --end 2026-06-30
~~~

An explicit end date is rejected if it does not leave enough future trading bars for the largest requested horizon.

Smaller smoke universe:

~~~powershell
python scripts/run_rs_v2_4_full_evaluation.py --max-tickers 10
~~~

One horizon:

~~~powershell
python scripts/run_rs_v2_4_full_evaluation.py --horizons 20
~~~

Selected sources:

~~~powershell
python scripts/run_rs_v2_4_full_evaluation.py --only-source-keys MA50_D,RSI14_D
~~~

Skip selected sources:

~~~powershell
python scripts/run_rs_v2_4_full_evaluation.py --skip-source-keys VP_HVN,VP_LVN
~~~

## Public Result

After completed effectiveness runs, query:

~~~sql
SELECT *
FROM "CherryMon"."main"."vw_RS_Source_Effectiveness"
ORDER BY
    "SourceKey",
    "HorizonBars",
    "EffectivenessScore" DESC;
~~~

The view exposes the latest completed row by:

~~~text
Ticker / ScopeType / SourceKey / HorizonBars
~~~

It remains the public Source Effectiveness SSOT.

## Monthly Operating Recommendation

~~~text
Daily
    runtime data/indicator/R-S refresh only

Weekly
    optional focused/incremental research

Monthly
    run_rs_v2_4_full_evaluation.py

Event-driven
    rerun when indicator/source/model semantics materially change
~~~

Do not schedule a daily full-universe multi-horizon ablation.

## Failure Handling

If a baseline fails:

~~~text
STOP
fix the direct failure
rerun the same monthly command
resume completed work
~~~

If one child run has incompatible metadata under the same deterministic ID:

~~~text
STOP
inspect requested window/config
use a new --run-prefix if the new evidence set is intentional
~~~

Do not delete historical effectiveness evidence merely to make a rerun succeed.
