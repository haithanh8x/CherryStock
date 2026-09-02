# CR_RS_V2_4_Monthly_Full_Evaluation

## 1. Change Summary

- **Change ID:** CR-RS-V2.4-MONTHLY-20260902
- **Release / Change:** R/S V2.4 Monthly Full Source Effectiveness Evaluation
- **Date:** 2026-09-02
- **Type:** Operational / Orchestration / Research Governance
- **Status:** PRODUCTION DEPLOYED / VALIDATED
- **Final Verdict:** PASS
- **Action:** KEEP
- **Parent release:** R/S Ladder V2.4
- **Architecture:** docs/architecture/RS_Source_Effectiveness.md
- **Operational runbook:** docs/runbook/RS_V2_4_Monthly_Full_Evaluation.md
- **Validation runbook:** tests/test_R_S_V2_4_Full_Evaluation.md
- **Pull Request:** PR #9
- **Merge commit:** `eed1990c7bccc0475eb9ac83c2c187e3bebf2b65`
- **Production date:** 2026-09-02

## 2. Objective

Operationalize R/S V2.4 Source Effectiveness as a repeatable monthly full-universe workflow without changing production R/S scoring, source weights, provider registration or model deployment behavior.

Canonical user entry point:

```text
scripts/run_rs_v2_4_full_evaluation.py
```

Canonical orchestration implementation:

```text
src/Orchestrator/rs_v2_4_full_evaluation.py
```

## 3. Monthly Workflow

```text
Resolve eligible universe
        ↓
Reserve mature future outcome bars
        ↓
Baseline H5 / H10 / H20 / H40
        ↓
Source auto-discovery
        ↓
SOURCE_CONFIG ablation
        ↓
Source Effectiveness
        ↓
SOURCE_FAMILY ablation
        ↓
Family Effectiveness
        ↓
Source Promotion Gate dry-run
        ↓
vw_RS_Source_Effectiveness
```

## 4. Delivered Contracts

The monthly orchestrator provides:

- automatic active ticker-universe resolution from `raw_lstTicker.status='Y'` joined to `raw_stock_eod`;
- default 3-year evaluation lookback;
- canonical horizons 5 / 10 / 20 / 40;
- point-in-time-safe evaluation end that reserves future trading bars for mature outcomes;
- one reusable baseline per horizon;
- runtime-aligned source auto-discovery;
- SOURCE_CONFIG and complete SOURCE_FAMILY ablation;
- deterministic run IDs;
- resumable COMPLETED child runs;
- metadata compatibility guard before REUSE;
- Source Promotion Gate dry-run by default;
- public output through `vw_RS_Source_Effectiveness`.

## 5. Runtime Boundary

The monthly full evaluation remains a research/governance workflow.

It MUST NOT automatically mutate:

```text
Indicator Engine metadata
R/S provider registry
runtime source weights
ticker-specific runtime weights
production model deployment
```

A Source Promotion Gate outcome remains evidence only.

## 6. Source Discovery

Current runtime-aligned source mapping includes:

```text
MA runtime lengths 20/50/100/200
    → TREND_AVERAGE / LEVEL

BB active price-level components
    → VOLATILITY_BAND / LEVEL

ATR active daily configs
    → VOLATILITY_CONTEXT / CONTEXT

RSI active D/W/M configs
    → MOMENTUM_CONFIRMATION / CONFIRMATION

SWING / PREVIOUS H-L / 52W H-L
    → MARKET_STRUCTURE / LEVEL

VP_POC / VP_HVN / VP_LVN
    → VOLUME_STRUCTURE / LEVEL
```

LEVEL config evaluation requires observable baseline lineage.

SOURCE_FAMILY ablation always removes the complete discovered family membership.

## 7. Resume / Idempotency

Default:

```text
--resume = true
```

A child evaluation run is reusable only when compatible on:

```text
DatasetStart
DatasetEnd
HorizonBars
TickerCount
SnapshotCount
Ticker universe
IncludeSourceKeys
ExcludeSourceKeys
```

Effectiveness runs also require matching source/scope/baseline/ablation metadata.

A deterministic run ID collision with incompatible metadata fails explicitly instead of silently reusing evidence.

## 8. Validation Evidence

User executed:

```text
tests/test_R_S_V2_4_Full_Evaluation.md
```

Final result:

```text
Final Verdict: PASS
Action: KEEP
```

Validation confirmed:

- deterministic run IDs;
- source auto-discovery from current runtime contract and baseline lineage;
- resume / REUSE behavior;
- Source Promotion Gate dry-run;
- public Source Effectiveness persistence/read path;
- no production runtime/scoring changes.

## 9. Validation Notes

No production-code repair was required during local validation.

Observed failures during execution were environment-related DuckDB writer locks caused by the local MCP server and did not indicate an orchestrator defect.

Local diagnostic scripts created during lock troubleshooting are outside this Change Request and are not part of the production release.

## 10. Golden Regression Runner Path

Validation exposed that the canonical V2.3 golden runner had been archived while runbooks still referenced its original path.

Post-validation cleanup restored:

```text
scripts/run_rs_v2_3_golden.py
```

Commits:

```text
8dc1cc769e74066285c3e25988c46432ef1038a7
e348991c90ee0a8efeded13fe1367a6ac06ad8e5
```

The archived duplicate was removed.

This is a path/operational correction only; golden benchmark logic is unchanged.

## 11. Database Impact

No new DuckDB schema migration.

The workflow reuses V2.3/V2.4 persistence:

```text
cal_rs_evaluation_run
cal_rs_evaluation_event
cal_rs_evaluation_metric
cal_rs_source_effectiveness_run
cal_rs_source_effectiveness
sys_rs_source_promotion_audit
vw_RS_Source_Effectiveness
```

## 12. Rollback

```text
NOT REQUIRED
```

The monthly runner is additive orchestration and does not alter production R/S runtime behavior.

## 13. Final Release State

```text
IMPLEMENTATION       DONE
TEST                 PASS
FINAL VERDICT        PASS
ACTION               KEEP
PR                   #9 MERGED
MERGE COMMIT         eed1990c7bccc0475eb9ac83c2c187e3bebf2b65
PRODUCTION CODE FIX  NONE
ENVIRONMENT ISSUE    DuckDB lock from MCP server only
GOLDEN PATH          RESTORED
RUNTIME REGRESSION   NONE
ROLLBACK             NOT REQUIRED
PRODUCTION READY     YES
PRODUCTION           DEPLOYED
```


## 14. Post-release Fix — Active Ticker Universe

The initial monthly orchestrator resolved eligible tickers from `raw_stock_eod` only. Local plan validation exposed a universe of 1,491 tickers, which was broader than the CherryStock production-active universe.

The default universe contract is now:

```text
raw_lstTicker.status = 'Y'
        ∩
raw_stock_eod available
        ∩
minimum historical bars satisfied
        ∩
freshness gate satisfied
```

Implementation:

```text
src/Orchestrator/rs_v2_4_full_evaluation.py::_resolve_tickers()
```

Validation result:

```text
pytest tests/test_rs_v2_4_full_evaluation.py
11 passed
```

Plan validation after the fix:

```text
universe_filter         raw_lstTicker.status='Y'
ticker_count            340
expected_snapshot_count 50784
evaluation_end          2026-07-03
latest_data_date        2026-08-28
```

Release evidence:

```text
PR             #10
Merge commit   cfd27e92056ac1ce21d7f887cfc8e5f9c120ef16
Final Verdict  PASS
Action         KEEP
```

This fix changes only monthly evaluation universe selection. It does not alter R/S runtime scoring, Source Effectiveness formulas, Promotion Gate thresholds, source weights, provider registration or production deployment behavior.
