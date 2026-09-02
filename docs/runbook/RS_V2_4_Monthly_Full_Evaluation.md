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
