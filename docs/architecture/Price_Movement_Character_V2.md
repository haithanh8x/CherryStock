# Price Movement Character V2 — ZigZag-based Characterization

- Requirement: docs/backlog/requirements/REQ-0031-zigzag-price-movement-character-v2.md
- Status: DESIGN_COMPLETE_PENDING_LOCAL_ARCHIFY_VALIDATION
- Owner: .github/agents/SolutionArchitect.agent.md
- Foundation: docs/architecture/ZigZag_Engine.md
- ADR: docs/adr/ADR-016-zigzag-price-movement-characterization-v2.md
- Operational boundary: manual/initload + validation only; not in run.py

## 1. Architecture Decision Summary

Price Movement V2 is a downstream analytical domain.

It consumes confirmed ZigZag public swing facts and daily OHLC path data, enriches each
confirmed swing with movement descriptors, and summarizes recent confirmed swings into a
ticker profile.

It does not locate pivots and does not choose ZigZag deviation.

    vw_Ticker_ZigZag_Swings
                |
                | confirmed boundaries / identity
                v
        Price Movement Swing Engine
                ^
                |
        vw_Ticker_OHLC_D
        descriptive path only
                |
                v
    cal_price_movement_swing
                |
                v
       Profile Classifier
                |
                v
   cal_price_movement_profile
                |
         +------+------+
         |             |
         v             v
 vw_Ticker_Price_  vw_Ticker_
 Movement_Swings   Movement_Profile

## 2. Current Source of Truth

Segmentation Source of Truth:

    vw_Ticker_ZigZag_Swings

Path-data Source of Truth:

    vw_Ticker_OHLC_D

REQ-0031 MUST NOT read dim_zigzag_ticker_config and silently apply an unpromoted
BaseDeviationPct. The upstream active ZigZag contract determines the actual swing set.

This matters because V1.2 currently reports KEEP_5_BASELINE for the pilot universe; V1.1
recommendations remain research evidence unless separately promoted.

## 3. Component Responsibilities

### 3.1 Price Movement domain models

Path:

    src/cherrystock/domain/analytics/price_movement/models.py

Owns immutable domain records:

- PriceMovementConfig
- PriceMovementSwing
- PriceMovementProfile

It does not know DuckDB.

### 3.2 Swing feature engine

Path:

    src/cherrystock/domain/analytics/price_movement/engine.py

Inputs:

- confirmed ZigZag swing DataFrame
- daily OHLC DataFrame
- PriceMovementConfig

Responsibilities:

- preserve upstream swing identity
- calculate TradingBars
- calculate SwingPct and VelocityPctPerBar
- build TrueRange / ATR20Pct path context
- calculate AvgATRPct and ATRNormalizedMove
- calculate PathEfficiency
- calculate DirectionalPersistenceRate
- enforce numeric and structural invariants
- build recent-swing profile

The engine does not query a database and does not detect pivots.

### 3.3 Character classifier

Path:

    src/cherrystock/domain/analytics/price_movement/classifier.py

Input:

- recent confirmed enriched swings
- versioned classification thresholds

Output:

    INSUFFICIENT_HISTORY
    TRENDING_UP
    TRENDING_DOWN
    RANGE_BOUND
    MIXED

This is descriptive classification only.

### 3.4 Repository

Path:

    src/cherrystock/infrastructure/database/repositories/price_movement_repository.py

Responsibilities:

- load Price Movement config
- load active ZigZag public swings
- load ticker OHLC path
- replace one config/ticker's confirmed swing/profile rows idempotently

Transaction ownership remains with the caller.

### 3.5 Operational wrapper

Path:

    src/calcEngine/priceMovement.py

Responsibilities:

- coordinate one ticker refresh using a caller-owned connection
- return deterministic diagnostics
- no commit ownership

MWG initload uses this wrapper.

## 4. Data Model

### 4.1 dim_price_movement_config

Business meaning:
versioned characterization/classification policy.

Grain:

    ConfigId

Important fields:

    ConfigCode
    ModelVersion
    Timeframe
    ProfileLookbackSwings
    MinimumProfileSwings
    TrendBiasThreshold
    RangeBiasThreshold
    EfficiencyThreshold
    ATRPeriod
    IsEnabled

Initial config:

    PM_ZZ_D_V2
    ProfileLookbackSwings = 20
    MinimumProfileSwings = 6
    TrendBiasThreshold = 0.20
    RangeBiasThreshold = 0.15
    EfficiencyThreshold = 0.30
    ATRPeriod = 20

### 4.2 cal_price_movement_swing

Business meaning:
one enriched, confirmed ZigZag swing.

Grain:

    PriceMovementConfigId + ZigZagConfigId + Ticker + SwingSeq

Identity/lineage:

    ZigZagConfigId
    ZigZagConfigCode
    Ticker
    SwingSeq
    StartPivotSeq
    EndPivotSeq
    StartDate
    EndDate
    ConfirmedAtDate

Calculated fields:

    Direction
    StartPrice
    EndPrice
    SwingPct
    TradingBars
    CalendarDays
    VelocityPctPerBar
    AvgATRPct
    ATRNormalizedMove
    PathEfficiency
    DirectionalPersistenceRate

ConfirmedAtDate is the point-in-time eligibility timestamp.

### 4.3 cal_price_movement_profile

Business meaning:
latest confirmed-history movement summary for one ticker/config.

Grain:

    PriceMovementConfigId + ZigZagConfigId + Ticker

Fields:

    AsOfConfirmedAtDate
    ProfileLookbackSwings
    ConfirmedSwingCount
    LastSwingSeq
    LastSwingDirection
    LastSwingPct
    MedianUpSwingPct
    MedianDownSwingAbsPct
    MedianAbsSwingPct
    MedianTradingBars
    MedianAbsVelocityPctPerBar
    MedianATRNormalizedMove
    MedianPathEfficiency
    MedianDirectionalPersistenceRate
    DirectionalBias
    MovementCharacter

## 5. Public Contracts

### vw_Ticker_Price_Movement_Swings

Stable consumer view for enriched confirmed swings.

No provisional/current leg is included.

### vw_Ticker_Movement_Profile

Stable consumer view for the latest confirmed-history profile.

Consumers must use this view rather than internal profile persistence when possible.

## 6. Calculation Semantics

### 6.1 TradingBars

For OHLC rows ordered by Date and bounded inclusively by StartDate/EndDate:

    TradingBars = row_count - 1

A valid confirmed swing requires TradingBars >= 1.

### 6.2 SwingPct

    EndPrice / StartPrice - 1

This is independently recomputed instead of blindly trusting an upstream derived percentage,
then reconciled against the ZigZag public swing contract.

### 6.3 Velocity

    SwingPct / TradingBars

### 6.4 True Range / ATR20Pct

ATR is calculated only as descriptive path context:

    TrueRange = max(
        High-Low,
        abs(High-PreviousClose),
        abs(Low-PreviousClose)
    )

    ATR20 = rolling mean(TrueRange, 20)
    ATR20Pct = ATR20 / Close

No ATR value affects start/end pivots.

### 6.5 ATRNormalizedMove

    abs(SwingPct) / mean(ATR20Pct within swing)

NULL when no valid ATR20Pct is available.

### 6.6 PathEfficiency

    abs(EndPrice - StartPrice)
    /
    sum(TrueRange within swing)

Then clip to [0,1].

### 6.7 DirectionalPersistenceRate

For close-to-close intervals inside the swing:

    UP   -> count(Return > 0) / interval_count
    DOWN -> count(Return < 0) / interval_count

The measure is clipped to [0,1].

## 7. Profile Semantics

Use the latest N confirmed enriched swings, ordered by SwingSeq.

Default:

    N = 20

DirectionalBias:

    sum(SwingPct) / sum(abs(SwingPct))

Classifier:

    n < 6
        -> INSUFFICIENT_HISTORY

    DirectionalBias >= 0.20
    AND MedianPathEfficiency >= 0.30
        -> TRENDING_UP

    DirectionalBias <= -0.20
    AND MedianPathEfficiency >= 0.30
        -> TRENDING_DOWN

    abs(DirectionalBias) < 0.15
    AND MedianPathEfficiency < 0.30
        -> RANGE_BOUND

    else
        -> MIXED

Thresholds live in config and are not hard-coded business strategy.

## 8. Point-in-Time Contract

For each Price Movement swing:

    EligibleAtDate = ZigZag EndPivot ConfirmedAtDate

Allowed descriptive source:

    OHLC Date <= EndDate

The calculation does not need or use any bar after EndDate for path features, and therefore
cannot use bars after ConfirmedAtDate because EndDate < ConfirmedAtDate under ADR-013.

Profile AsOfConfirmedAtDate is the maximum ConfirmedAtDate among included recent swings.

## 9. Migration Contract

Forward change:

- create dim_price_movement_config
- create cal_price_movement_swing
- create cal_price_movement_profile
- create/replace two public views
- seed PM_ZZ_D_V2 config idempotently

Compatibility:

- additive only
- no existing ZigZag table/view is changed
- no existing Price Movement V1 persistence is reintroduced
- run.py unchanged

Backfill:

- initial MWG-only full deterministic rebuild
- multi-ticker expansion requires TestEngineer gate

Rerun:

- delete/replace only the target PriceMovementConfigId + ZigZagConfigId + Ticker rows
- caller-owned UnitOfWork provides transaction boundary

Rollback/repair:

- because migration is additive, rollback is disabling/removing consumers and dropping only
  the REQ-0031-owned objects after evidence export if explicitly required
- normal repair path is forward-fix + deterministic rebuild

## 10. Reconciliation Contract

The local export script writes:

    docs/reference/data/price_movement/<ticker-lower>/

Files:

    <TICKER>_OHLC_<from>_<to>.csv
    <TICKER>_ZigZag_Pivots.csv
    <TICKER>_ZigZag_Swings.csv
    <TICKER>_Price_Movement_Swings.csv
    <TICKER>_Movement_Profile.csv
    <TICKER>_Price_Movement_Reconciliation_Summary.csv

Summary checks include:

- swing row count parity
- identity mismatch count
- direction mismatch count
- endpoint date/price mismatch count
- SwingPct formula mismatch count
- TradingBars mismatch count
- velocity mismatch count
- bounds violations for efficiency/persistence
- ConfirmedAtDate/eligibility mismatch count

## 11. Validation Strategy

Developer-focused tests:

- pure domain formula tests
- classifier boundary tests
- point-in-time/source-bound tests
- one-to-one swing identity test
- idempotent repository replacement behavior where practical

Local TestEngineer runbook:

- focused pytest
- apply additive schema
- MWG initload
- structural validator
- rerun/idempotency
- reconciliation export
- ChatGPT review from committed evidence
- run.py regression check

## 12. Operational Boundary

REQ-0031 is manual/initload first.

No production scheduling, no daily pipeline integration and no SmartMoney integration are
authorized by this design.

## 13. Architecture Artifact Synchronization

Typed source:

    docs/architecture/diagrams/cherrystock-analytics-calculation-engines.architecture.json

Generated artifact:

    docs/architecture/generated/CherryStock_Analytics_Calculation_Engines.html

The typed source is updated by this change. The connected GitHub environment cannot execute
the local Archify renderer, so the generated artifact must be synchronized locally with:

    .\scripts\render_archify_analytics.ps1 -NoOpen

Until that command returns Archify showcase ok=true and the generated HTML is committed,
architecture visualization status remains:

    PENDING_LOCAL_ARCHIFY_VALIDATION/RENDER

## 14. SA Handoff

    DESIGN HANDOFF
    Requirement: REQ-0031
    Outcome: ZigZag-based Price Movement Characterization V2
    Canonical design: docs/architecture/Price_Movement_Character_V2.md
    ADR: ADR-016
    Architecture semantics: DESIGN COMPLETE
    Archify artifact: PENDING_LOCAL_ARCHIFY_VALIDATION/RENDER
    Implementation boundary: MWG-first manual/initload, run.py unchanged
    Next owner: GeneralCoding
