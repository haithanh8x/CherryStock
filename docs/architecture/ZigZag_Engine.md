# ZigZag Swing Engine — MWG MVP

- **Status:** APPROVED_FOR_IMPLEMENTATION
- **Owner:** .github/agents/SolutionArchitect.agent.md
- **Requirement:** docs/backlog/requirements/REQ-0027-price-movement-characterization.md
- **ADR:** docs/adr/ADR-013-zigzag-as-price-movement-segmentation-foundation.md
- **Parent:** docs/architecture/Analytics_Calculation_Engines.md
- **Archify source:** docs/architecture/diagrams/cherrystock-analytics-calculation-engines.architecture.json

## 1. Purpose

The ZigZag Swing Engine owns only price-pivot segmentation.

It converts ordered daily OHLC into:

- confirmed LOW/HIGH pivots;
- derived UP/DOWN swings from adjacent pivots;
- one provisional current-leg state.

It does not calculate ATR, movement scores, persistence, Smart Money intent or trade actions.

## 2. MVP Boundary

The first implementation is deliberately limited to:

    Ticker             = MWG
    Timeframe          = D
    ConfigCode         = ZZ_D_5_MVP
    DeviationPct       = 0.05
    PivotPriceSource   = HIGH_LOW
    ConfirmationSource = CLOSE
    MinimumSwingBars   = 1
    Execution          = manual initload only

The MVP is not part of run.py.

## 3. Component Flow

    vw_Ticker_OHLC_D
            |
            v
    ZigZagSourceLoader
            |
            v
    PercentageReversalZigZagEngine
            |
            +--------------------------+
            |                          |
            v                          v
    confirmed pivots             current leg
            |                          |
            v                          v
    cal_zigzag_pivot       cal_zigzag_current_leg
            |
            v
    vw_Ticker_ZigZag_Pivots
            |
            v
    vw_Ticker_ZigZag_Swings

Consumers during MVP are validation scripts and analyst review only.

## 4. Input Contract

Source:

    "CherryMon"."main"."vw_Ticker_OHLC_D"

Required columns:

    Ticker
    Date
    High
    Low
    Close

Rows with non-positive or non-finite High/Low/Close are excluded from ZigZag calculation
and reported in the initload summary. Open/Volume are not required.

Input must be sorted by Date ascending before entering the state machine.

## 5. State Model

States:

    TRANSITION
    UP
    DOWN

### TRANSITION

The engine has not yet confirmed the first pivot.

It tracks both:

- lowest Low and highest High reached after that low;
- highest High and lowest Low reached after that high.

The first LOW is confirmed when Close rises at least DeviationPct above the tracked low.
The first HIGH is confirmed when Close falls at least DeviationPct below the tracked high.

When both conditions become true on the same daily bar, deterministic tie-break is:

1. larger excess excursion beyond DeviationPct;
2. earlier candidate PivotDate;
3. LOW if still tied.

### UP

The last confirmed pivot is LOW.

Runtime state:

    last LOW pivot
    candidate HIGH
    lowest Low seen since candidate HIGH

Candidate HIGH updates only when current High is strictly greater than the stored candidate.

Confirmation rule:

    (CandidateHighPrice - Close) / CandidateHighPrice >= DeviationPct

and candidate HIGH must occur at least MinimumSwingBars after the last confirmed LOW.

On confirmation:

- emit HIGH with PivotDate = candidate-high date;
- ConfirmedAtDate = current bar date;
- switch to DOWN;
- seed next candidate LOW from the lowest Low observed since candidate HIGH.

### DOWN

Symmetric to UP.

Runtime state:

    last HIGH pivot
    candidate LOW
    highest High seen since candidate LOW

Confirmation rule:

    Close / CandidateLowPrice - 1 >= DeviationPct

On confirmation:

- emit LOW;
- switch to UP;
- seed next candidate HIGH from the highest High observed since candidate LOW.

## 6. Point-in-Time Contract

A pivot is not a confirmed fact on PivotDate.

Example:

    PivotDate       = 2026-08-27
    ConfirmedAtDate = 2026-09-07

Historical consumers may use this pivot only when:

    as_of >= ConfirmedAtDate

The public pivot view therefore exposes both dates.

No daily historical state table is required for the MVP.

## 7. Data Model

### 7.1 dim_zigzag_config

Grain:

    ConfigId

Fields:

    ConfigId
    ConfigCode
    ModelVersion
    Timeframe
    DeviationPct
    PivotPriceSource
    ConfirmationPriceSource
    MinimumSwingBars
    EffectiveFrom
    EffectiveTo
    IsEnabled
    CreatedAt
    UpdatedAt

MVP seed:

    ConfigId = 1
    ConfigCode = ZZ_D_5_MVP

### 7.2 cal_zigzag_pivot

Grain:

    ConfigId + Ticker + PivotSeq

Fields:

    ConfigId
    Ticker
    PivotSeq
    PivotType              HIGH | LOW
    PivotDate
    PivotPrice
    ConfirmedAtDate
    ConfirmationPrice
    DeviationPct
    CalculatedAt

Constraints:

    PivotDate <= ConfirmedAtDate
    PivotPrice > 0
    ConfirmationPrice > 0

### 7.3 cal_zigzag_current_leg

Grain:

    ConfigId + Ticker

Fields:

    ConfigId
    Ticker
    AsOfDate
    Direction              UP | DOWN | NULL
    StartPivotSeq
    StartPivotDate
    StartPivotPrice
    CandidatePivotType
    CandidatePivotDate
    CandidatePivotPrice
    LastClose
    CurrentMovePct
    ReversalFromCandidatePct
    Status                 PROVISIONAL | TRANSITION
    CalculatedAt

This table contains exactly one row per config/ticker after a successful rebuild.

## 8. Public Contracts

### vw_Ticker_ZigZag_Pivots

Stable read contract for confirmed pivots with config metadata.

### vw_Ticker_ZigZag_Swings

Derived from adjacent confirmed pivots using LAG.

Output includes:

    Ticker
    SwingSeq
    Direction
    StartPivotType
    StartDate
    StartPrice
    EndPivotType
    EndDate
    EndPrice
    ConfirmedAtDate
    SwingPct
    CalendarDays

Direction mapping:

    LOW -> HIGH = UP
    HIGH -> LOW = DOWN

### vw_Ticker_ZigZag_Current

Current provisional leg plus config metadata.

## 9. Persistence and Transaction

The MVP runner owns one DuckDBUnitOfWork.

Sequence:

    ensure zigzag schema/config/views
    -> load MWG OHLC
    -> calculate O(n)
    -> delete prior rows for MWG + ConfigId
    -> insert new confirmed pivots
    -> replace one current-leg row
    -> commit
    -> export DB metadata

Repository code must not call COMMIT/ROLLBACK.

If any step fails inside the UoW, the rebuild is rolled back.

## 10. Idempotency

Full MWG rebuild is the only supported write mode in MVP.

For unchanged source + config, rerun must produce the same:

- pivot count;
- PivotSeq;
- PivotType;
- PivotDate;
- PivotPrice;
- ConfirmedAtDate.

The implementation intentionally avoids incremental complexity until pivot semantics are approved.

## 11. Performance Contract

State-machine complexity:

    O(number_of_MWG_bars)

The implementation must keep scalar runtime state and must not perform an expanding DataFrame
slice/copy in the per-bar loop.

No regression, percentile or persistence computation is allowed in the ZigZag segmentation loop.

## 12. Validation Contract

Structural validator checks:

- no duplicate ConfigId/Ticker/PivotSeq;
- alternating pivot types;
- increasing PivotSeq;
- PivotDate <= ConfirmedAtDate;
- confirmation dates non-decreasing;
- each interior LOW equals the minimum Low between adjacent pivot dates;
- each interior HIGH equals the maximum High between adjacent pivot dates;
- one current-leg row exists;
- current direction is opposite the next expected pivot type.

The validator also prints MWG pivots/swings for 2026-07-01 through 2026-09-30 for visual review.

## 13. Rollout Gate

Do not add other tickers until all are true:

    structural_errors = 0
    duplicate_pivots = 0
    repeated_initload = identical
    Jul-Sep 2026 visual review = accepted by user

If 5% is rejected, create a new config/version and rerun MWG. Do not silently overwrite the
meaning of ZZ_D_5_MVP.

## 14. Future Phase

After MWG approval, a separate design increment may add:

- multi-ticker config scope;
- incremental checkpoints;
- 3% / 8% ZigZag levels;
- swing feature calculations;
- Price Movement Character;
- downstream SmartMoney consumption.

## SA Handoff

    DESIGN HANDOFF
    Requirement / objective: REQ-0027 ZigZag-based swing segmentation
    Outcome: APPROVED_FOR_IMPLEMENTATION
    Design path: docs/architecture/ZigZag_Engine.md
    ADR: docs/adr/ADR-013-zigzag-as-price-movement-segmentation-foundation.md
    Archify source: docs/architecture/diagrams/cherrystock-analytics-calculation-engines.architecture.json
    Affected modules/files: ZigZag domain, repository, SQL, MWG initload, validator, tests
    Contracts/invariants: event-first, PivotDate vs ConfirmedAtDate, O(n), MWG only
    Migration/backfill: additive ZigZag schema; full MWG rebuild only
    Validation focus: MWG local extremes + Jul-Sep 2026 visual gate
    Known risks: 5% calibration, daily-bar intraday ambiguity
    Next owner: GeneralCoding
