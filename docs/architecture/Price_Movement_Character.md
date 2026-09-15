# Price Movement Character Engine

- **Status:** DRAFT_PENDING_ARCHIFY_RENDER
- **Owner:** `.github/agents/SolutionArchitect.agent.md`
- **Requirement:** `docs/backlog/requirements/REQ-0027-price-movement-characterization.md`
- **ADR:** `docs/adr/ADR-012-price-movement-character-as-separate-analytics-domain.md`
- **Architecture parent:** `docs/architecture/Analytics_Calculation_Engines.md`
- **Archify source:** `docs/architecture/diagrams/cherrystock-analytics-calculation-engines.architecture.json`

## 1. Purpose

The Price Movement Character Engine characterizes **how a ticker moves** rather than reducing behavior to endpoint return.

It separates three dimensions:

```text
Magnitude   = how far price has moved
Velocity    = how fast price has moved
Persistence = how steadily price has moved in one direction
```

It also maintains a ticker-specific historical swing profile so the current movement can be compared with the ticker's own prior up/down behavior.

The engine is a price-path analytics domain. It does not infer Smart Money intent and does not emit BUY/HOLD/SELL actions.

## 2. Scope and Boundary

### In scope

- daily adjusted OHLC;
- volatility-adaptive ZigZag-like swing segmentation;
- confirmed versus provisional swing state;
- magnitude, duration and velocity;
- ATR-normalized magnitude;
- same-direction historical percentiles;
- Efficiency Ratio;
- log-price linear-regression slope and R²;
- maximum adverse excursion / pullback;
- directional-day ratio;
- separate Magnitude / Velocity / Persistence scores;
- explainable movement-character labels;
- historical backfill and daily incremental refresh;
- public views for swing history, daily state and latest profile.

### Out of scope for V1

- intraday swing detection;
- weekly/monthly swing models;
- BUY/HOLD/SELL actions;
- volume/order-flow interpretation;
- SmartMoneyScore weight changes;
- machine-learned threshold optimization.

## 3. Architecture Decision Summary

Per ADR-012, Price Movement Character is a separate analytics domain because its state/event semantics do not fit the ordinary Indicator Engine fact grain.

The dependency direction is:

```text
vw_Ticker_OHLC_D
      │
      ├──────────────────────────────────┐
      │                                  │
      ▼                                  ▼
Technical Indicator Engine       Price Movement Character Engine
      │                                  ▲
      │ vw_Ticker_indicators / ATR       │
      └──────────────────────────────────┘
                                         │
                                         ▼
                         cal_price_movement_swing
                         cal_price_movement_daily
                                         │
                         ┌───────────────┼────────────────┐
                         ▼               ▼                ▼
              vw_Ticker_Movement_   vw_Ticker_      vw_Ticker_
                    Swings          Movement_D      Movement_Profile
                         │               │                │
                         └───────────────┼────────────────┘
                                         ▼
                               Chart / Screener /
                            future analytical models
```

The engine MUST consume ATR through the public Indicator contract when available; it MUST NOT read `cal_indicator_values` directly.

## 4. Daily Pipeline Placement

Target daily analytics order:

```text
1. Composite Index
2. Trend / Moving Average
3. Technical Indicators
4. Price Movement Character
5. SmartMoneyScore
```

The Price Movement stage executes inside the same caller-owned `DuckDBUnitOfWork` as the other daily analytics writes.

Rationale for placement:

- adjusted EOD price is already loaded and validated;
- ATR is available from the Indicator Engine public contract;
- a future SmartMoney requirement may consume the stable movement public contract without reordering upstream dependencies;
- Data Quality failure can block the shared transaction before commit.

V1 does **not** change SmartMoneyScore inputs or scoring.

## 5. Logical Components

### 5.1 `MovementConfigResolver`

Responsibility:

- resolve enabled model/config version;
- resolve ATR indicator identity through stable metadata rather than numeric ConfigId assumptions;
- expose classification thresholds and minimum-history rules.

Inputs:

- `dim_price_movement_model`;
- `dim_price_movement_config`;
- `vw_Indicator_config` for ATR identity/config resolution.

Output:

- immutable runtime config object for one calculation run.

### 5.2 `SwingSegmentationEngine`

Responsibility:

- sequentially track candidate highs/lows;
- confirm reversals;
- emit confirmed swing events;
- expose current provisional leg state;
- preserve the date when a pivot occurred separately from the date when that pivot became knowable.

The engine is an online state machine. Historical backfill MUST simulate dates in order; it must not locate all future pivots first and then back-project them into earlier as-of rows.

### 5.3 `SwingFeatureEngine`

Responsibility:

For a confirmed or current leg, calculate:

- raw swing return;
- trading-bar duration;
- calendar duration;
- velocity;
- ATR-normalized magnitude;
- Efficiency Ratio;
- log-price regression slope;
- regression R²;
- maximum adverse excursion;
- directional-day ratio.

### 5.4 `HistoricalSwingProfileEngine`

Responsibility:

- maintain same-direction historical reference sets;
- calculate distribution statistics from **prior confirmed** swings;
- calculate current magnitude/velocity percentiles;
- enforce minimum sample size and point-in-time cutoff by `ConfirmedAtDate`.

### 5.5 `MovementScoringEngine`

Responsibility:

- calculate `MagnitudeScore`;
- calculate `VelocityScore`;
- calculate `PersistenceScore`;
- preserve component values instead of exposing only an aggregate.

### 5.6 `MovementClassificationEngine`

Responsibility:

- combine direction plus score bands into an explainable `MovementCharacter`;
- emit `INSUFFICIENT_HISTORY` / `TRANSITION` states when prerequisites are not met;
- avoid business-language claims such as accumulation/distribution/capitulation from price-path evidence alone.

### 5.7 `PriceMovementRepository`

Responsibility:

- checkpoint-replace/upsert the requested ticker/date scope;
- keep confirmed event persistence and daily as-of state separate;
- expose stable read views;
- preserve idempotency for unchanged source + config.

## 6. Input Contracts

### 6.1 Adjusted OHLC

Primary price input:

```text
main.vw_Ticker_OHLC_D
```

Required columns:

```text
Ticker
Date
Open
High
Low
Close
```

Although `vw_Ticker_OHLC_D` also contains volume/flow fields, V1 Price Movement Character uses price-path fields only.

Adjusted analytical price is intentional because the objective is continuous historical price-path analysis across corporate actions.

### 6.2 ATR

Primary volatility input:

```text
main.vw_Ticker_indicators
IndicatorCode = ATR
Timeframe = D
ComponentCode = VALUE
```

ATR configuration is resolved through `vw_Indicator_config`; implementation MUST NOT assume a portable numeric `ConfigId`.

If ATR is unavailable for a valid price observation, the engine may fall back to the configured minimum percentage reversal rule but MUST mark:

```text
ThresholdSource = PCT_FALLBACK
QualityStatus   = PARTIAL
```

and `ATRNormMagnitude` remains NULL when it cannot be calculated honestly.

## 7. ZigZag / Swing Confirmation Contract

### 7.1 Pivot source

- candidate peak price uses daily `High`;
- candidate trough price uses daily `Low`;
- reversal confirmation uses `Close` to reduce wick-only false confirmations.

These are versioned configuration choices, not hard-coded business constants.

### 7.2 Adaptive reversal threshold

V1 threshold form:

```text
AtrPct = ATR / ReferencePrice

ReversalThresholdPct = max(
    MinReversalPct,
    ATRMultiplier * AtrPct
)
```

Optional `MaxReversalPct` may be configured as a safety cap after evaluation; absence of a cap is represented explicitly, not by an undocumented magic value.

Recommended initial evaluation defaults:

```text
Timeframe              = D
ATR indicator          = ATR(14)
ATRMultiplier          = 2.0
MinReversalPct         = 0.03
MinimumSwingBars       = 2
MinHistoricalSameDir   = 8
ProfileMaxSwings       = 50
```

These defaults are **tunable configuration**, not immutable business rules. Test/evaluation may change them by creating a new config version.

### 7.3 Confirmation semantics

For an up leg:

1. track the highest candidate `High` since the last confirmed trough;
2. update the candidate peak while price makes new highs;
3. confirm that peak only when a later `Close` falls by at least the configured reversal threshold from the candidate peak;
4. emit the completed up swing whose `PivotEndDate` is the peak date and whose `ConfirmedAtDate` is the later reversal-confirmation date.

For a down leg, apply the symmetric rule around the lowest candidate `Low` and a later upward `Close` reversal.

### 7.4 No-look-ahead invariant

```text
PivotEndDate != knowledge date
ConfirmedAtDate = first date the pivot is knowable
```

A historical consumer querying `as_of = D` MUST NOT observe a confirmed event with:

```text
ConfirmedAtDate > D
```

Daily rows before confirmation are never retroactively rewritten to imply the future pivot was already known.

### 7.5 Provisional current leg

The active leg is emitted to the daily-state contract as:

```text
SwingStatus = PROVISIONAL
```

Its candidate endpoint, magnitude, duration, velocity and persistence metrics may change on later dates. Consumers must not treat it as confirmed event history.

## 8. Feature Definitions

Let `P0` be leg start price and `P1` the current/confirmed endpoint price.

### 8.1 Swing magnitude

```text
SwingPct = (P1 / P0) - 1
```

Direction is stored explicitly as `UP` or `DOWN`.

### 8.2 Duration

```text
DurationBars = count of ordered trading-bar transitions from start to endpoint
DurationCalendarDays = PivotEndDate - PivotStartDate
```

`DurationBars` is the primary analytical duration because it is exchange-session aware.

### 8.3 Velocity

Use log-return-per-trading-bar for scale consistency:

```text
VelocityLogPerBar = ln(P1 / P0) / max(DurationBars, 1)
```

Consumer-friendly percentage-per-bar may also be exposed:

```text
VelocityPctPerBar = (exp(VelocityLogPerBar) - 1) * 100
```

### 8.4 ATR-normalized magnitude

For a completed leg:

```text
MeanATR = mean(valid ATR observations over the leg)
ATRNormMagnitude = abs(P1 - P0) / MeanATR
```

If valid ATR coverage is insufficient, `ATRNormMagnitude = NULL` and quality/provenance identifies the degraded basis.

### 8.5 Efficiency Ratio

Using closes along the known leg path:

```text
ER = abs(Close_end - Close_start)
     / sum(abs(Close_t - Close_t-1))
```

Range:

```text
0 <= ER <= 1
```

Near `1` means the path is directionally efficient; low values imply substantial back-and-forth movement.

### 8.6 Regression slope and R²

Fit:

```text
ln(Close_t) = alpha + beta * bar_index + error
```

Store:

```text
RegressionSlopePerBar = beta
RegressionR2          = coefficient of determination
```

R² measures how consistently the path follows a log-linear trend. Slope is retained as explanatory evidence but is not used to duplicate the VelocityScore role in V1.

### 8.7 Maximum adverse excursion

For `UP`:

```text
AdversePct_t = (Close_t / running_max_close_before_or_at_t) - 1
MaxAdverseExcursionPct = abs(min(AdversePct_t))
```

For `DOWN`, use the symmetric rally from running minimum close.

Normalize for persistence scoring:

```text
AdverseRatio = min(
    1,
    MaxAdverseExcursionPct / max(abs(SwingPct), epsilon)
)
SmoothnessComponent = 1 - AdverseRatio
```

### 8.8 Directional-day ratio

```text
DirectionalDayRatio =
    same-direction close-to-close changes
    / valid close-to-close changes in the leg
```

For `UP`, same-direction means positive daily change; for `DOWN`, negative daily change.

## 9. Historical Swing Profile

Historical distributions are calculated separately by direction.

For each ticker/config/direction, expose at least:

```text
SwingCount
MagnitudeMedian
MagnitudeP75
MagnitudeP90
DurationBarsMedian
DurationBarsP75
VelocityMedian
VelocityP75
ATRNormMagnitudeMedian
PersistenceMedian
```

Latest profile read contract uses confirmed events only.

For historical daily scoring at date `D`, the eligible reference sample is:

```text
same ticker
same config/model
same direction
ConfirmedAtDate < D
most recent ProfileMaxSwings events
```

Using `< D` rather than future events prevents the current date from grading itself against knowledge that did not yet exist.

## 10. Score Definitions

All scores use range `0..100`; unavailable scores are NULL, not zero.

### 10.1 MagnitudeScore

When sufficient same-direction history exists:

```text
RawMagnitudePercentile = percentile_rank(abs(CurrentSwingPct))
                         among prior same-direction abs(SwingPct)

ATRNormPercentile = percentile_rank(CurrentATRNormMagnitude)
                    among prior same-direction ATRNormMagnitude
```

If both are available:

```text
MagnitudeScore = 100 * (
    0.60 * RawMagnitudePercentile
  + 0.40 * ATRNormPercentile
)
ScoreBasis = RAW_PLUS_ATR
```

If ATR-normalized evidence is unavailable but raw-history sample is sufficient:

```text
MagnitudeScore = 100 * RawMagnitudePercentile
ScoreBasis = RAW_ONLY
QualityStatus = PARTIAL
```

Weights are versioned config values so calibration can change without silently changing historical semantics.

### 10.2 VelocityScore

```text
VelocityScore = 100 * percentile_rank(
    abs(CurrentVelocityLogPerBar)
)
```

Reference set: prior confirmed same-direction swings for the same ticker/config.

### 10.3 PersistenceScore

V1 persistence is a transparent path-quality composite:

```text
PersistenceScore = 100 * (
    0.35 * ER
  + 0.35 * RegressionR2
  + 0.20 * SmoothnessComponent
  + 0.10 * DirectionalDayRatio
)
```

Each component remains separately exposed. The weights are versioned configuration.

PersistenceScore is not a historical percentile. A separate `PersistencePercentile` may be exposed when sufficient confirmed history exists, but it does not replace the direct path-quality score.

## 11. Movement Character Classification

V1 classification uses direction plus score bands.

Recommended initial config bands:

```text
HIGH_MAGNITUDE    >= 75
HIGH_VELOCITY     >= 75
HIGH_PERSISTENCE  >= 70
LOW_PERSISTENCE   <  55
MID_MAGNITUDE     >= 40 and < 75
```

Classification logic:

| Direction | Conditions | MovementCharacter |
|---|---|---|
| UP | Magnitude high + Persistence high | `STRONG_PERSISTENT_UP` |
| DOWN | Magnitude high + Persistence high | `STRONG_PERSISTENT_DOWN` |
| UP | Magnitude high + Velocity high + Persistence low | `EXPLOSIVE_VOLATILE_UP` |
| DOWN | Magnitude high + Velocity high + Persistence low | `EXPLOSIVE_VOLATILE_DOWN` |
| UP | Persistence high + Magnitude mid | `STEADY_UP` |
| DOWN | Persistence high + Magnitude mid | `STEADY_DOWN` |
| UP | Persistence high + Magnitude below mid | `SLOW_GRIND_UP` |
| DOWN | Persistence high + Magnitude below mid | `SLOW_GRIND_DOWN` |
| UP | otherwise | `NORMAL_UP` |
| DOWN | otherwise | `NORMAL_DOWN` |
| N/A | insufficient historical sample | `INSUFFICIENT_HISTORY` |
| N/A | no stable directional leg yet | `TRANSITION` |

Names intentionally describe price-path behavior rather than investor intent.

## 12. Physical Data Model

### 12.1 `dim_price_movement_model`

Purpose: model/version identity.

Grain / PK:

```text
ModelId
```

Target columns:

```text
ModelId BIGINT
ModelCode VARCHAR              -- PRICE_MOVEMENT_CHARACTER
ModelVersion VARCHAR           -- V1
Description VARCHAR
IsEnabled BOOLEAN
EffectiveFrom DATE
EffectiveTo DATE NULL
CreatedAt TIMESTAMP
UpdatedAt TIMESTAMP
```

Uniqueness:

```text
ModelCode + ModelVersion
```

### 12.2 `dim_price_movement_config`

Purpose: executable versioned configuration.

Grain / PK:

```text
ConfigId
```

Target columns:

```text
ConfigId BIGINT
ModelId BIGINT
Timeframe VARCHAR              -- D in V1
PivotPriceSource VARCHAR       -- HIGH_LOW
ConfirmationPriceSource VARCHAR-- CLOSE
ATRIndicatorCode VARCHAR       -- ATR
ATRLength INTEGER              -- expected family identity / validation
ATRMultiplier DOUBLE
MinReversalPct DOUBLE
MaxReversalPct DOUBLE NULL
MinimumSwingBars INTEGER
MinHistoricalSameDir INTEGER
ProfileMaxSwings INTEGER
MagnitudeRawWeight DOUBLE
MagnitudeATRWeight DOUBLE
PersistenceERWeight DOUBLE
PersistenceR2Weight DOUBLE
PersistenceSmoothnessWeight DOUBLE
PersistenceDirectionalDayWeight DOUBLE
HighMagnitudeThreshold DOUBLE
HighVelocityThreshold DOUBLE
HighPersistenceThreshold DOUBLE
LowPersistenceThreshold DOUBLE
MidMagnitudeThreshold DOUBLE
EffectiveFrom DATE
EffectiveTo DATE NULL
IsEnabled BOOLEAN
CreatedAt TIMESTAMP
```

Integrity:

- score-component weights for each composite sum to `1.0` within numeric tolerance;
- percent thresholds are stored as decimals where applicable;
- one enabled production config per `ModelId + Timeframe + as-of date`.

### 12.3 `cal_price_movement_swing`

Business fact: confirmed swing event.

Grain:

```text
ConfigId + Ticker + PivotStartDate + Direction
```

Target columns:

```text
ConfigId BIGINT
Ticker VARCHAR
Direction VARCHAR             -- UP / DOWN
SwingSeq BIGINT
PivotStartDate DATE
PivotEndDate DATE
ConfirmedAtDate DATE
StartPrice DOUBLE
EndPrice DOUBLE
SwingPct DOUBLE
DurationBars INTEGER
DurationCalendarDays INTEGER
VelocityLogPerBar DOUBLE
VelocityPctPerBar DOUBLE
MeanATR DOUBLE NULL
ATRNormMagnitude DOUBLE NULL
EfficiencyRatio DOUBLE NULL
RegressionSlopePerBar DOUBLE NULL
RegressionR2 DOUBLE NULL
MaxAdverseExcursionPct DOUBLE NULL
DirectionalDayRatio DOUBLE NULL
PersistenceScore DOUBLE NULL
ThresholdPct DOUBLE
ThresholdSource VARCHAR        -- ATR_PLUS_FLOOR / PCT_FALLBACK
QualityStatus VARCHAR          -- OK / PARTIAL
CalculatedAt TIMESTAMP
```

Constraints:

```text
PivotStartDate <= PivotEndDate <= ConfirmedAtDate
Direction IN ('UP','DOWN')
DurationBars >= 1
ConfirmedAtDate is never NULL
```

`SwingSeq` is a deterministic convenience sequence, not the sole logical key.

### 12.4 `cal_price_movement_daily`

Business fact: point-in-time movement state as known on each date.

Grain / logical key:

```text
ConfigId + Ticker + Date
```

Target columns:

```text
ConfigId BIGINT
Ticker VARCHAR
Date DATE
Direction VARCHAR             -- UP / DOWN / NULL
SwingStatus VARCHAR           -- PROVISIONAL / TRANSITION
CurrentSwingStartDate DATE NULL
CandidateEndDate DATE NULL
StartPrice DOUBLE NULL
CandidateEndPrice DOUBLE NULL
CurrentSwingPct DOUBLE NULL
DurationBars INTEGER NULL
VelocityLogPerBar DOUBLE NULL
VelocityPctPerBar DOUBLE NULL
ATRNormMagnitude DOUBLE NULL
EfficiencyRatio DOUBLE NULL
RegressionSlopePerBar DOUBLE NULL
RegressionR2 DOUBLE NULL
MaxAdverseExcursionPct DOUBLE NULL
DirectionalDayRatio DOUBLE NULL
HistoricalSameDirSwingCount INTEGER
MagnitudePercentile DOUBLE NULL
ATRNormMagnitudePercentile DOUBLE NULL
VelocityPercentile DOUBLE NULL
PersistencePercentile DOUBLE NULL
MagnitudeScore DOUBLE NULL
VelocityScore DOUBLE NULL
PersistenceScore DOUBLE NULL
MovementCharacter VARCHAR
ScoreBasis VARCHAR             -- RAW_PLUS_ATR / RAW_ONLY / INSUFFICIENT
ThresholdPct DOUBLE NULL
ThresholdSource VARCHAR NULL
QualityStatus VARCHAR          -- OK / PARTIAL / INSUFFICIENT_HISTORY / INVALID_INPUT
CalculatedAt TIMESTAMP
```

No daily row may include a historical percentile based on a swing whose `ConfirmedAtDate` is after that row's `Date`.

## 13. Public Read Contracts

### 13.1 `vw_Ticker_Movement_Swings`

Grain:

```text
Ticker + enabled ModelCode/ModelVersion/ConfigId + confirmed swing
```

Purpose:

- chart swing overlays;
- research on typical up/down legs;
- event-history analysis.

It exposes only confirmed events from `cal_price_movement_swing`.

### 13.2 `vw_Ticker_Movement_D`

Grain:

```text
Ticker + Date + enabled ModelCode/ModelVersion
```

Purpose:

- screener/current-state consumption;
- historical point-in-time feature analysis;
- future downstream models.

### 13.3 `vw_Ticker_Movement_Profile`

Grain:

```text
Ticker + enabled ModelCode/ModelVersion + Direction
```

Purpose:

- answer “mỗi sóng tăng/giảm thường bao nhiêu % và kéo dài bao lâu?”;
- expose latest confirmed-history summary.

Target fields include:

```text
Ticker
Direction
SwingCount
MagnitudeMedian
MagnitudeP75
MagnitudeP90
DurationBarsMedian
DurationBarsP75
VelocityMedian
VelocityP75
ATRNormMagnitudeMedian
PersistenceMedian
LatestConfirmedAtDate
ModelCode
ModelVersion
ConfigId
```

The view may aggregate `cal_price_movement_swing` at read time because event volume is small relative to daily EOD facts; a duplicate persisted profile table is not introduced in V1.

## 14. Historical Backfill

Full backfill algorithm per ticker/config:

```text
load ordered OHLC + ATR history
        ↓
initialize segmentation state
        ↓
for each trading date in ascending order
        ↓
update candidate pivot / detect reversal
        ↓
if reversal confirmed:
    finalize confirmed swing
    make it eligible for profile only from ConfirmedAtDate onward
        ↓
calculate as-of current-leg metrics using knowledge available today
        ↓
calculate prior same-direction historical percentiles
        ↓
score + classify
        ↓
persist daily as-of row
        ↓
continue
```

This sequential simulation is mandatory for no-look-ahead correctness.

## 15. Daily Incremental Refresh

The engine needs enough warmup/state to recreate the current unconfirmed leg and historical comparison set.

Preferred V1 implementation strategy:

1. load the latest persisted finalized state for each ticker/config;
2. load confirmed prior swing events needed for the historical profile (`ProfileMaxSwings` per direction);
3. reload OHLC + ATR from the start of the still-open/provisional leg, with a safety warmup around the last confirmed pivot;
4. recompute the mutable checkpoint from that boundary through the requested latest date;
5. delete/replace only mutable daily rows and any confirmed swing events created inside that checkpoint;
6. leave older confirmed events untouched when upstream source/config has not changed.

If the implementation cannot prove a safe incremental boundary for a changed source/config, it MUST choose a bounded ticker rebuild/full backfill rather than silently accepting divergence.

## 16. Idempotency and Transaction Semantics

- schema migration is additive and rerunnable where practical;
- refresh runs inside the caller-owned DuckDB transaction;
- one calculation run uses one resolved config version;
- logical-key upsert/checkpoint replacement prevents duplicates;
- confirmed events outside the mutable checkpoint are immutable for unchanged source/config;
- Data Quality failure before commit rolls back Price Movement writes together with the daily UnitOfWork.

## 17. Data Quality Contract

Post-refresh validation should use the shared `validate_data_quality()` contract where applicable plus domain-specific assertions.

Required checks:

- no duplicate `ConfigId + Ticker + Date` in daily state;
- no duplicate confirmed swing logical key;
- `PivotStartDate <= PivotEndDate <= ConfirmedAtDate`;
- valid direction/status enums;
- scores within `0..100` when non-NULL;
- ER/R²/day-ratio within `0..1` when non-NULL;
- no historical percentile using future-confirmed events;
- latest active tickers have reasonable daily-state coverage after valid warmup;
- confirmed up/down swings alternate under one config/ticker unless an explicitly documented reset/rebuild boundary exists.

Persist DQ audit using existing `sys_data_quality_audit` conventions.

## 18. Failure and Missing-Data Semantics

### Missing/invalid OHLC

```text
QualityStatus = INVALID_INPUT
```

Do not manufacture movement scores.

### Missing ATR

- segmentation may use `MinReversalPct` fallback;
- raw magnitude/velocity/path metrics remain valid where price history is valid;
- ATR-normalized metrics are NULL;
- `ScoreBasis = RAW_ONLY` where a raw historical comparison is valid;
- `QualityStatus = PARTIAL`.

### Insufficient confirmed swing history

```text
MagnitudeScore = NULL where historical percentile is required
VelocityScore  = NULL where historical percentile is required
MovementCharacter = INSUFFICIENT_HISTORY
QualityStatus = INSUFFICIENT_HISTORY
```

Persistence component metrics may still be shown as descriptive evidence if calculable.

## 19. Migration Contract

Target durable SQL file:

```text
src/DuckDB/sql/price_movement_character_v1_schema.sql
```

Forward migration:

1. create model/config dimensions if absent;
2. seed V1 model/config idempotently using stable business identity;
3. create `cal_price_movement_swing`;
4. create `cal_price_movement_daily`;
5. create/replace the three public views;
6. backfill historical data;
7. validate keys, coverage, point-in-time invariants and public views;
8. refresh generated DB metadata after physical implementation.

Compatibility:

- fully additive;
- no existing public view is replaced;
- no existing Indicator or SmartMoney table is altered.

Rollback/repair:

- before consumer activation, disable the V1 model/config and remove/recreate only the new public views/tables as needed;
- after consumer activation, prefer forward repair/new config/model version rather than destructive history rewrite;
- upstream historical price restatement may trigger a controlled ticker/full rebuild.

## 20. Target Implementation Layout

Recommended ownership:

```text
src/calcEngine/priceMovementCharacter.py
    public orchestration entry: refresh_price_movement_character(...)

src/cherrystock/domain/analytics/price_movement/
    models.py
    segmentation.py
    features.py
    scoring.py
    classification.py

src/cherrystock/infrastructure/duckdb/
    price_movement_repository.py

src/DuckDB/sql/price_movement_character_v1_schema.sql
```

If the current runtime-package migration makes a narrower existing location more appropriate at implementation time, GeneralCoding may preserve the approved responsibility boundaries while adapting paths. A path change must not collapse domain calculation into UI or database code.

## 21. Public Python Contract

Recommended calculation entry:

```python
refresh_price_movement_character(
    *,
    connection,
    start_date=None,
    end_date=None,
    tickers=None,
    mode="incremental",
) -> PriceMovementRefreshSummary
```

Summary should include at least:

```text
model/config identity
requested date range
ticker count
daily rows written
confirmed swings written/replaced
partial-ATR ticker/date count
insufficient-history count
DQ status
```

No database connection is opened/closed inside domain calculation code; transaction ownership remains with the caller/UoW.

## 22. Test / Validation Design

### Unit tests

1. monotonic rise then reversal confirms one up swing at the correct confirmation date;
2. monotonic fall then reversal confirms one down swing;
3. candidate extreme updates without prematurely confirming a pivot;
4. future reversal does not leak pivot knowledge into earlier daily rows;
5. equal return but shorter duration yields higher absolute velocity;
6. smooth path has higher ER/R²/PersistenceScore than noisy equal-endpoint path;
7. deep pullback lowers smoothness/persistence;
8. ATR fallback marks degraded provenance;
9. insufficient sample produces NULL historical scores, not zero;
10. same-direction percentile excludes opposite-direction swings.

### Integration tests

- schema idempotent rerun;
- historical backfill writes unique keys;
- incremental run matches full backfill on overlapping finalized dates;
- daily pipeline rollback on blocking DQ failure;
- public views expose only enabled model/config semantics;
- downstream reads do not require internal `cal_*` access.

### Research/evaluation checks

Before production threshold promotion, inspect:

- swings per ticker/year;
- median/P75/P90 magnitude and duration by ticker;
- distribution of reversal thresholds;
- proportion of ATR fallback;
- score distributions;
- classification frequency;
- sensitivity of swing counts to ATRMultiplier/MinReversalPct;
- stability across representative low-, medium- and high-volatility tickers.

## 23. Example Interpretation

Two tickers can both show `+40%`:

```text
Ticker A
MagnitudeScore   88
VelocityScore    61
PersistenceScore 91
Max adverse      shallow
Character        STRONG_PERSISTENT_UP

Ticker B
MagnitudeScore   90
VelocityScore    94
PersistenceScore 42
Max adverse      deep
Character        EXPLOSIVE_VOLATILE_UP
```

The component therefore preserves the distinction between **large**, **fast** and **durable** movement.

## 24. Future Extensions

Not part of REQ-0027 V1:

- weekly/monthly movement models;
- intraday swing profiles;
- market-relative movement percentile;
- sector-relative movement character;
- volume/flow-conditioned swing quality;
- SmartMoneyScore factor integration;
- strategy/position-sizing use;
- model calibration through walk-forward/OOS research.

Each extension should preserve model/config version identity so historical semantics do not silently change.

## 25. Design Handoff

```text
DESIGN HANDOFF
Requirement / objective: REQ-0027 Price Movement Characterization and Swing Profile
Outcome: DRAFT_PENDING_ARCHIFY_RENDER
Design path: docs/architecture/Price_Movement_Character.md
ADR: docs/adr/ADR-012-price-movement-character-as-separate-analytics-domain.md
Archify source/artifact: update required in cherrystock-analytics-calculation-engines.architecture.json; render required before APPROVED_FOR_IMPLEMENTATION
Affected modules/files: daily analytics orchestration, new price-movement calc/domain/repository modules, additive DuckDB schema/views, DQ/tests
Contracts/invariants: confirmed vs provisional, PivotEndDate vs ConfirmedAtDate, no look-ahead, separate Magnitude/Velocity/Persistence, public-view-only downstream access
Migration/backfill: additive schema + full sequential backfill + incremental checkpoint strategy
Validation focus: no look-ahead, swing confirmation, score bounds, historical/incremental equivalence, DQ/idempotency
Known risks: threshold sensitivity, small swing samples, upstream adjusted-price restatements, ZigZag confirmation lag
Next owner after Archify synchronization: GeneralCoding.agent.md
```

The design MUST NOT be promoted to `APPROVED_FOR_IMPLEMENTATION` until the corresponding Archify typed source is synchronized and the generated architecture artifact is successfully rendered/validated according to repository governance.
