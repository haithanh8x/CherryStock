# SmartMoneyScore V1 Deployment & Validation Runbook

- Status: IMPLEMENTED_PENDING_VALIDATION
- Requirement: REQ-0025
- Architecture: docs/architecture/SmartMoneyScore.md
- ADR: docs/adr/ADR-009-smart-money-score-state-aware-scoring.md
- Validation owner: TestEngineer

## Purpose

Bootstrap, backfill, validate and prepare SmartMoneyScore V1 for daily incremental operation.

Public contract:

~~~text
"CherryMon"."main"."vw_Ticker_SmartMoney"
~~~

V1 outputs:

~~~text
SmartMoneyScore
ConfidenceScore
MarketState
FactorCoverage
DataQualityStatus

FreshFlowScore
RelativeLiquidityScore
LiquidityAccelerationScore
RelativeStrengthScore
AccumulationScore
AccumulationMemoryScore
SupplyLockScore
LimitUpScore
TrendScore
DistributionScore
~~~

Historical LimitUpScore remains NULL / UNAVAILABLE until the point-in-time
As-Traded market-limit contract passes its own migration validation.

## Implementation artifacts

Storage / metadata / public view:

~~~text
src/DuckDB/sql/smart_money_v1_schema.sql
~~~

Runtime:

~~~text
src/calcEngine/smartMoneyScore.py
src/cherrystock/infrastructure/database/repositories/smart_money_repository.py
~~~

Execution:

~~~text
scripts/initload/init_reload_smart_money_score.py
scripts/run_smart_money.py
scripts/validate_smart_money_incremental.py
~~~

Validation:

~~~text
tests/test_smart_money_score.py
tests/test_smart_money_evaluation.py
src/DuckDB/sql/smart_money_v1_preflight.sql
tests/test_smart_money_score.md
~~~

Research / calibration:

~~~text
src/calcEngine/smartMoneyEvaluation.py
scripts/evaluate_smart_money_v1.py
~~~

## V1 input contract

| Input | Source | Required |
|---|---|---|
| OHLCV | vw_Ticker_OHLC_D | Yes |
| TradingValue + quality | vw_Ticker_OHLC_D | Yes |
| VNINDEX | raw_index_eod | Yes for RS |
| MA20 / MA50 | vw_Ticker_indicators | Optional but expected |
| OBV_D / AD_D | vw_Ticker_indicators | Optional but expected |
| Point-in-time LimitUp | vw_stock_market_limit_eod | Optional; currently unavailable |

BuyUp/SellDown/ATO/ATC are not V1 core scoring dependencies.

## Algorithm contract

Rolling features:

~~~text
Return1/5/20/60
ALV5/20/60
RVAL20
LiquidityAcceleration
LiquidityCompression
CLV / CLV20
RS5/20/60 vs VNINDEX
MA20/MA50 trend
OBV 20-session slope
AD 20-session slope
~~~

Normalization is same-date cross-sectional percentile. No future date participates.

Accumulation memory:

~~~text
Memory_t =
    lambda * Memory_(t-1)
  + (1-lambda) * AccumulationScore_t

default lambda = 0.90
~~~

Daily incremental does not recompute full history. It uses:

~~~text
target checkpoint
        ↓
~70 prior market sessions warmup
        +
latest persisted AccumulationMemory before warmup
        ↓
recalculate rolling factors + memory
        ↓
replace target checkpoint only
~~~

Cross-sectional normalization still uses the complete active universe for each
calculated date, even when --tickers limits persisted ticker rows.

# Phase 0 — Sync code

~~~powershell
git pull
git status
~~~

# Phase 1 — Focused unit tests

~~~powershell
python -m pytest tests/test_smart_money_score.py tests/test_smart_money_evaluation.py -v
~~~

Required cases:

- same-date percentile;
- minimum-universe handling;
- accumulation-memory recursion;
- persisted memory seed;
- missing LimitUp remains NULL;
- state precedence;
- SupplyLock weight renormalization when LimitUp is missing.

If unit tests fail:

~~~text
Verdict: FAIL
Action: FIX ONCE
~~~

Do not start historical backfill.

# Phase 2 — Full historical initload

~~~powershell
python scripts\initload\init_reload_smart_money_score.py
~~~

The script performs atomically:

~~~text
schema + metadata seed
        ↓
full active-universe source load
        ↓
feature calculation
        ↓
same-date normalization
        ↓
memory/state/score/confidence
        ↓
factor + score persistence
        ↓
COMMIT
        ↓
export DB metadata
~~~

Expected summary:

~~~text
status = OK
score_rows_upserted > 0
factor_rows_upserted > 0
state_distribution non-empty
~~~

# Phase 3 — Read-only SQL preflight

Execute:

~~~text
src/DuckDB/sql/smart_money_v1_preflight.sql
~~~

Validate:

1. six required base tables + public view exist;
2. SMART_MONEY_V1 is enabled;
3. exactly ten V1 factors are enabled;
4. every state weight profile totals approximately 1.0;
5. score/confidence ranges are 0..100;
6. FactorCoverage is 0..1;
7. duplicate score keys = 0;
8. duplicate factor keys = 0;
9. missing LimitUp remains NULL / UNAVAILABLE;
10. state distribution contains only supported states;
11. MWG is readable from public view;
12. every score row has factor evidence.

# Phase 4 — Full vs incremental convergence

After full initload:

~~~powershell
python scripts\validate_smart_money_incremental.py --days 30 --tickers MWG FPT HPG
~~~

The validator captures the current full-history baseline, runs incremental refresh
inside the same transaction, compares score/factor rows, and always ROLLBACKs.

Expected:

~~~text
SmartMoney full/incremental convergence: PASS
~~~

Any difference is a regression.

# Phase 5 — Public contract spot-check

~~~sql
SELECT
    Ticker,
    Date,
    ModelCode,
    ModelVersion,
    SmartMoneyScore,
    ConfidenceScore,
    MarketState,
    FactorCoverage,
    DataQualityStatus,
    FreshFlowScore,
    RelativeLiquidityScore,
    LiquidityAccelerationScore,
    RelativeStrengthScore,
    AccumulationScore,
    AccumulationMemoryScore,
    SupplyLockScore,
    LimitUpScore,
    TrendScore,
    DistributionScore
FROM "CherryMon"."main"."vw_Ticker_SmartMoney"
WHERE Ticker IN ('MWG','FPT','HPG')
ORDER BY Date DESC, Ticker
LIMIT 100;
~~~

Verify:

- normalized scores are 0..100;
- ConfidenceScore is independent from SmartMoneyScore;
- missing LimitUpScore is NULL, not 0;
- SupplyLock can exist without LimitUp;
- Distribution reduces final SmartMoneyScore.

# Phase 6 — Incremental operational command

Full active universe:

~~~powershell
python scripts\run_smart_money.py --days 15
~~~

Ticker persistence subset:

~~~powershell
python scripts\run_smart_money.py --days 30 --tickers MWG FPT HPG
~~~

Ticker subset affects persistence only. Percentile normalization still uses the
full active universe on each date.

# Phase 7 — Historical / OOS evaluation

After functional validation and full historical persistence:

~~~powershell
python scripts\evaluate_smart_money_v1.py --horizons 5 10 20
~~~

The evaluation uses chronological:

~~~text
TRAIN       60%
VALIDATION  20%
TEST        20%
~~~

and evaluates:

- SmartMoneyScore buckets;
- MarketState;
- Confidence buckets;
- forward stock return;
- forward VNINDEX return;
- excess return;
- win rate / excess-win rate;
- score-bucket monotonicity;
- top-minus-bottom excess-return spread.

Forward H is measured on the exact VNINDEX trading-session date H bars after the
score date. If the ticker has no Close on that exact future session, the label is
unavailable rather than silently shifted to a later ticker observation.

Outputs are written under:

~~~text
data/evaluation/smart_money_v1/
  metrics.csv
  monotonicity.csv
  summary.json
~~~

This is research evidence only. The evaluator MUST NOT mutate SmartMoney weights,
score persistence or the auto-run flag.

No predictive-performance threshold is hard-coded in V1 because no approved
business calibration threshold exists yet. OOS evidence must be reviewed explicitly
before treating the initial weights as calibrated.

# Phase 8 — Production orchestration gate

Do not add SmartMoney to normal daily run.py until TestEngineer returns PASS for:

~~~text
unit tests
historical initload
SQL preflight
full/incremental convergence
public view contract
~~~

After TestEngineer functional PASS **and explicit OOS evaluation review**, production order is:

~~~text
EOD refresh
→ VNINDEX refresh
→ Trend / Indicator Engine
→ SmartMoney incremental refresh
→ data-quality checks
→ metadata export
~~~

This gate is intentional: runtime implementation exists, but automatic daily
activation is validation-dependent.

# Market-limit later cutover

When the following path passes its independent runbook:

~~~text
raw_stock_eod_astraded
→ cal_stock_market_limit_eod
→ vw_stock_market_limit_eod
~~~

SmartMoney can consume trusted LimitUp / LimitUpStreak without changing its public
schema.

# Rollback

SmartMoney V1 is additive. If validation fails:

1. stop SmartMoney refresh;
2. leave existing market/indicator data unchanged;
3. revert SmartMoney implementation commits if required;
4. optionally drop only SmartMoney objects;
5. do not mutate raw_stock_eod, Indicator Engine tables or VNINDEX source.

Do not restore legacy adjusted-Close LimitUp as authoritative fallback.

# Terminal verdict

~~~text
SmartMoneyScore V1
------------------
Unit tests: PASS | FAIL | BLOCKED
Schema/metadata: PASS | FAIL
Historical initload: PASS | FAIL | BLOCKED
Score range: PASS | FAIL
Factor keys: PASS | FAIL
Score keys: PASS | FAIL
NULL semantics: PASS | FAIL
State distribution: PASS | WARNING | FAIL
Public view: PASS | FAIL
Full/incremental convergence: PASS | FAIL
MarketLimit evidence: PASS | WARNING

Verdict: PASS | FAIL | BLOCKED | REGRESSION
Action: KEEP | FIX ONCE | REVERT | STOP
~~~

Only TestEngineer owns final PASS.
