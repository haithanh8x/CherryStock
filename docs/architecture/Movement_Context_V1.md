# MovementContext V1 — Price Behavior Semantic Contract

- **Requirement:** REQ-0032
- **Status:** DONE — TESTENGINEER_PASS_KEEP
- **Owner:** .github/agents/SolutionArchitect.agent.md
- **Decision:** docs/adr/ADR-017-movement-context-as-price-behavior-contract.md
- **Upstream:** Price Movement V2 + ZigZag Current + daily OHLC
- **Public contract:** `"CherryMon"."main"."vw_Ticker_Movement_Context"`

## 1. Purpose

MovementContext is a semantic read layer between raw movement analytics and future strategy
composition.

It converts already-owned movement facts into a stable vocabulary without becoming a second
Source of Truth for ZigZag segmentation or Price Movement history.

```text
vw_Ticker_Movement_Profile -----------+
                                      |
vw_Ticker_ZigZag_Current -------------+--> vw_Ticker_Movement_Context
                                      |
vw_Ticker_OHLC_D ---------------------+
        current-leg trading-bar count only
```

MovementContext does **not** read R/S or SmartMoney.

A later TickerStrategyContext may combine:

```text
MovementContext
RSContext
SmartMoneyContext
        ↓
TickerStrategyContext
        ↓
Setup / Strategy
```

## 2. Responsibility Boundary

### MovementContext owns

- semantic interpretation of the most recent confirmed movement profile;
- same-direction last-swing extent relative to ticker history;
- trend-quality label from confirmed efficiency/persistence;
- provisional current-leg speed relative to historical typical move speed;
- explicit completeness/status of confirmed-only versus confirmed+current context.

### MovementContext does not own

- ZigZag pivot detection or current-leg calculation;
- Price Movement swing/profile calculation;
- Support/Resistance;
- SmartMoney state/score;
- BUY/HOLD/SELL;
- entry/exit, stop, position sizing or portfolio policy.

## 3. Source of Truth

Confirmed historical behavior:

```text
vw_Ticker_Movement_Profile
```

Provisional current leg:

```text
vw_Ticker_ZigZag_Current
```

Current-leg trading-session count:

```text
vw_Ticker_OHLC_D
```

MovementContext does not copy or persist those facts.

## 4. Physical Design

### 4.1 dim_movement_context_config

Business meaning: versioned interpretation thresholds and upstream contract mapping.

Grain:

```text
MovementContextConfigId
```

V1 config:

```text
ConfigCode              MC_PM_ZZ_D_V1
ModelVersion            V1.0
Timeframe               D
PriceMovementConfigCode PM_ZZ_D_V2
ZigZagConfigCode        ZZ_D_5_MVP
```

Threshold groups:

- last-swing extent ratio;
- trend-quality efficiency/persistence;
- current move-speed ratio.

The thresholds are interpretation policy, not trading rules.

### 4.2 vw_Ticker_Movement_Context

Business meaning: latest movement context for one ticker under one enabled context config.

Grain:

```text
MovementContextConfigId + Ticker
```

The view is dynamic and has no `cal_movement_context` table.

This is intentional: the provisional ZigZag current leg may change before confirmation, so
persisting a second current-state copy would introduce synchronization/staleness risk.

## 5. Public Output Contract

### Identity / lineage

- MovementContextConfigId
- MovementContextConfigCode
- MovementContextModelVersion
- Timeframe
- PriceMovementConfigCode
- PriceMovementModelVersion
- ZigZagConfigCode
- Ticker
- ContextAsOfDate
- ProfileAsOfConfirmedAtDate
- CurrentLegAsOfDate
- ContextStatus

### Historical regime / baseline

- TrendRegime
- TrendQuality
- TypicalSwingPct
- TypicalSwingBars
- TypicalMoveSpeedPctPerBar
- MedianPathEfficiency
- MedianDirectionalPersistenceRate
- DirectionalBias

### Last confirmed swing

- LastSwingDirection
- LastSwingPct
- LastSwingTypicalPct
- LastSwingExtentRatio
- LastSwingState

### Current provisional leg

- CurrentLegDirection
- CurrentMovePct
- CurrentTradingBars
- CurrentMoveSpeedPctPerBar
- CurrentMoveSpeedRatio
- CurrentMoveSpeedState
- CurrentLegStatus

## 6. Last Swing Semantics

Same-direction baseline:

```text
UP   -> MedianUpSwingPct
DOWN -> MedianDownSwingAbsPct
```

Extent:

```text
LastSwingExtentRatio =
abs(LastSwingPct) / LastSwingTypicalPct
```

V1 classification:

```text
ratio < 0.50   -> SHALLOW
ratio < 0.80   -> BELOW_TYPICAL
ratio <= 1.25  -> TYPICAL
ratio <= 1.75  -> EXTENDED
else           -> EXTREME
```

Final label preserves direction:

```text
TYPICAL_DOWN_SWING
EXTENDED_UP_SWING
...
```

If the same-direction historical median is unavailable/non-positive:

```text
LastSwingExtentRatio = NULL
LastSwingState       = UNKNOWN
```

## 7. Trend Regime and Trend Quality

### TrendRegime

```text
TrendRegime = MovementCharacter
```

No second regime classifier is introduced.

### TrendQuality

TrendQuality describes **how clean/persistent confirmed swings tend to be**, not whether the
ticker is bullish or bearish.

V1 classification:

```text
MovementCharacter = INSUFFICIENT_HISTORY
    -> INSUFFICIENT_HISTORY

MedianPathEfficiency >= 0.60
AND MedianDirectionalPersistenceRate >= 0.75
    -> HIGH

MedianPathEfficiency >= 0.40
AND MedianDirectionalPersistenceRate >= 0.60
    -> MODERATE_HIGH

MedianPathEfficiency >= 0.25
AND MedianDirectionalPersistenceRate >= 0.50
    -> MODERATE

else
    -> LOW
```

A ticker may therefore be:

```text
TrendRegime  = MIXED
TrendQuality = MODERATE_HIGH
```

meaning direction is not dominant, while individual swings are still relatively clean.

## 8. Historical Typical Movement

The public context carries through:

```text
TypicalSwingPct            = MedianAbsSwingPct
TypicalSwingBars           = MedianTradingBars
TypicalMoveSpeedPctPerBar  = MedianAbsVelocityPctPerBar
```

These are baselines for interpretation, not targets/stops.

## 9. Current Provisional Leg

MovementContext joins the matching active ZigZag current-leg row by:

```text
Ticker + ZigZagConfigCode
```

Current trading intervals:

```text
CurrentTradingBars =
count(vw_Ticker_OHLC_D rows from StartPivotDate through AsOfDate) - 1
```

Current speed:

```text
CurrentMoveSpeedPctPerBar =
CurrentMovePct / CurrentTradingBars
```

Relative speed:

```text
CurrentMoveSpeedRatio =
abs(CurrentMoveSpeedPctPerBar)
/
TypicalMoveSpeedPctPerBar
```

V1 classification:

```text
ratio < 0.50   -> VERY_SLOW
ratio < 0.80   -> SLOW
ratio <= 1.25  -> NORMAL
ratio <= 1.75  -> FAST
else           -> EXTREME
```

Missing/invalid provisional data produces `UNKNOWN` rather than fabricating a movement state.

## 10. ContextStatus

```text
MovementCharacter = INSUFFICIENT_HISTORY
    -> INSUFFICIENT_HISTORY

usable current leg + CurrentTradingBars >= 1
    -> PROFILE_PLUS_CURRENT

otherwise
    -> PROFILE_ONLY
```

Confirmed historical context is not discarded merely because current provisional data is absent.

## 11. Point-in-Time Semantics

Confirmed profile knowledge date:

```text
ProfileAsOfConfirmedAtDate
```

Current provisional snapshot date:

```text
CurrentLegAsOfDate
```

Public:

```text
ContextAsOfDate =
coalesce(CurrentLegAsOfDate, ProfileAsOfConfirmedAtDate)
```

Consumers must not confuse provisional current-leg values with confirmed historical facts.

## 12. Migration / Compatibility

Forward change:

- create `dim_movement_context_config`;
- seed `MC_PM_ZZ_D_V1` idempotently;
- create/replace `vw_Ticker_Movement_Context`.

No existing table/view is altered.

No historical backfill is required because the public view derives from existing data.

Rollback:

- disable/remove the MovementContext config/view only;
- ZigZag and Price Movement remain unchanged.

After applying the schema locally, regenerate DB metadata using the existing repository metadata exporter.

## 13. Operational Boundary

REQ-0032 is manual/research first.

It does not modify:

- `run.py`;
- Price Movement persistence;
- ZigZag persistence;
- SmartMoney;
- R/S.

## 14. Validation Strategy

Minimum independent evidence:

- focused SQL/view tests;
- MWG local schema application;
- exact formula reconciliation for last-swing extent;
- exact trading-bar/current-speed/current-speed-ratio reconciliation;
- allowed-state validation;
- PROFILE_ONLY behavior when current-leg inputs are unavailable;
- no R/S/SmartMoney dependency;
- daily pipeline regression;
- generated DB metadata refresh after local migration.

Runbook:

```text
docs/runbook/Movement_Context_V1.md
```

## 15. Architecture Visualization

This design extends the existing **Movement Public Contracts** node rather than introducing a
new calculation engine. The Archify typed source should describe:

```text
pivots · swings · profile · context
```

Generated HTML must be regenerated/validated by the repository Archify workflow or local
renderer before architecture visualization synchronization is considered complete.

## 16. Validation Closure

Independent local validation completed on 2026-09-21:

- 13/13 focused tests PASS;
- additive migration PASS;
- MWG validator structural_errors=0;
- idempotency PASS;
- daily pipeline regression 3/3 PASS;
- Archify showcase `ok=true` with 9/9 checks;
- DB metadata refreshed from the actual local DuckDB.

Observed MWG context at validation time:

```text
TrendRegime          MIXED
TrendQuality         MODERATE_HIGH
LastSwingState       TYPICAL_DOWN_SWING
LastSwingExtentRatio ~0.98
CurrentLegDirection  UP
CurrentMoveSpeedState NORMAL
CurrentMoveSpeedRatio ~1.13
```

Validation evidence commit: `d95a6f0d717fe71d5e3447fb4a2f416c89b26558`.

## 17. Handoff

```text
DESIGN HANDOFF
Requirement: REQ-0032
Outcome: DONE — TESTENGINEER_PASS_KEEP
Design path: docs/architecture/Movement_Context_V1.md
ADR: docs/adr/ADR-017-movement-context-as-price-behavior-contract.md
Implementation: src/DuckDB/sql/movement_context_v1_schema.sql
Migration: additive config + derived public view; no backfill
Validation: focused tests + MWG local runbook
Known risk: heuristic thresholds require empirical strategy validation later
Next owner: None
```
