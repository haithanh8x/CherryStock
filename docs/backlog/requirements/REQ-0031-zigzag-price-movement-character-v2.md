---
id: REQ-0031
title: ZigZag-based Price Movement Characterization V2
status: IMPLEMENTED_PENDING_VALIDATION
priority: P1
owner: BusinessAnalyst
primary_next_owner: TestEngineer
related:
  prerequisite:
    - docs/backlog/requirements/REQ-0027-price-movement-characterization.md
    - docs/backlog/requirements/REQ-0028-zigzag-deviation-calibration-v1-1.md
    - docs/backlog/requirements/REQ-0029-zigzag-multi-ticker-pilot-v1-2.md
    - docs/backlog/requirements/REQ-0030-zigzag-regime-aware-v2.md
  architecture:
    - docs/architecture/Price_Movement_Character_V2.md
  adr:
    - docs/adr/ADR-016-zigzag-price-movement-characterization-v2.md
---

# REQ-0031 — ZigZag-based Price Movement Characterization V2

## Business Objective

Describe how a ticker moves after swing boundaries have already been established by ZigZag.

The Price Movement domain transforms confirmed ZigZag swings into explainable movement
features such as magnitude, duration, velocity, volatility-normalized magnitude and path
persistence, then summarizes recent confirmed swing history into a ticker-level movement
profile.

The engine must not infer Smart Money intent and must not detect pivots itself.

## Background / Problem

The retired Price Movement V1 mixed two responsibilities:

1. locating price-movement boundaries; and
2. describing the resulting movement.

ATR-adaptive segmentation made the first responsibility difficult to reconcile and produced
incorrect swing starts for cases such as MWG.

REQ-0027/ADR-013 moved swing segmentation to the independent ZigZag domain. REQ-0031 resumes
the downstream characterization layer only.

## Source-of-Truth Rule

Confirmed swing boundaries come from the active ZigZag public contracts:

    vw_Ticker_ZigZag_Pivots
    vw_Ticker_ZigZag_Swings

Price Movement MUST NOT re-run pivot detection from OHLC.

The V1.1 BaseDeviationPct recommendation is calibration evidence, not automatically a runtime
segmentation setting. REQ-0031 consumes whichever ZigZag configuration has actually been
promoted/activated. Under the current V1.2 result, the fixed 5% baseline remains the active
reference.

## Stakeholders / Consumers

- CherryStock analytical layer;
- chart/screener/API consumers that need movement descriptors;
- future SmartMoney/strategy research, only through a separate approved integration;
- TestEngineer and ChatGPT reconciliation workflows.

## In Scope

Initial delivery:

- daily confirmed ZigZag swings;
- MWG-first initload/validation path;
- reusable multi-ticker domain calculation;
- magnitude, trading duration and velocity;
- ATR20 percentage as descriptive normalization only;
- path efficiency and directional persistence;
- recent-swing ticker profile;
- deterministic movement classification;
- DuckDB persistence + public read views;
- local validation script;
- post-golive reconciliation export under docs/reference/data/**;
- runbooks for validation and reconciliation.

## Out of Scope

- pivot detection;
- modifying ZigZag deviation or config promotion;
- provisional/current ZigZag leg characterization;
- SmartMoney scoring/action changes;
- BUY/SELL strategy or profit optimization;
- daily run.py integration;
- all-universe production scheduling;
- inference of operator/institutional intent from price path alone.

## Functional Requirements

### FR-01 — Confirmed swing enrichment

For every confirmed ZigZag swing, produce one Price Movement swing with the same:

- ZigZag config;
- ticker;
- swing sequence;
- start/end pivot sequence;
- start/end date;
- start/end price;
- direction;
- ZigZag ConfirmedAtDate.

### FR-02 — Magnitude

    SwingPct = EndPrice / StartPrice - 1

UP swings must be positive and DOWN swings must be negative.

### FR-03 — Trading duration

TradingBars is the number of daily OHLC intervals between StartDate and EndDate.

For N source bars inclusive of both boundaries:

    TradingBars = N - 1

### FR-04 — Velocity

    VelocityPctPerBar = SwingPct / TradingBars

when TradingBars > 0.

### FR-05 — ATR normalization

ATR MUST NOT establish swing boundaries.

For descriptive normalization:

    TrueRange = max(
        High - Low,
        abs(High - PreviousClose),
        abs(Low - PreviousClose)
    )

    ATR20 = rolling mean(TrueRange, 20)
    ATR20Pct = ATR20 / Close

For each swing:

    AvgATRPct = mean(ATR20Pct from StartDate through EndDate)
    ATRNormalizedMove = abs(SwingPct) / AvgATRPct

when sufficient ATR history exists.

### FR-06 — Path efficiency

For each confirmed swing:

    PathEfficiency =
        abs(EndPrice - StartPrice)
        /
        sum(TrueRange from StartDate through EndDate)

The value is capped to [0, 1] for numeric safety.

### FR-07 — Directional persistence

For intervals inside the swing:

- UP: percentage of close-to-close returns > 0;
- DOWN: percentage of close-to-close returns < 0.

Flat return intervals do not count as directionally persistent.

### FR-08 — Point-in-time eligibility

A movement swing becomes eligible only on the ZigZag end pivot ConfirmedAtDate.

Price Movement may describe bars inside the already completed swing, but MUST NOT use bars
after ConfirmedAtDate for that swing.

### FR-09 — Recent movement profile

Build a ticker-level profile from the most recent confirmed swings using a versioned lookback.
The MVP default is 20 swings.

Profile outputs must include:

- confirmed swing count used;
- last swing direction and magnitude;
- median UP magnitude;
- median absolute DOWN magnitude;
- median absolute swing magnitude;
- median trading bars;
- median absolute velocity;
- median ATR-normalized move;
- median path efficiency;
- median directional persistence;
- directional bias;
- deterministic MovementCharacter.

### FR-10 — Movement character

The MVP classifier is descriptive and configurable:

- INSUFFICIENT_HISTORY when fewer than 6 swings are available;
- TRENDING_UP when DirectionalBias >= 0.20 and MedianPathEfficiency >= 0.30;
- TRENDING_DOWN when DirectionalBias <= -0.20 and MedianPathEfficiency >= 0.30;
- RANGE_BOUND when abs(DirectionalBias) < 0.15 and MedianPathEfficiency < 0.30;
- otherwise MIXED.

Where:

    DirectionalBias =
        sum(SwingPct)
        /
        sum(abs(SwingPct))

over the configured recent lookback.

These thresholds are classification parameters, not trading rules.

### FR-11 — Persistence

Persist confirmed movement swings and one current confirmed-history profile per
Price Movement config/ticker.

### FR-12 — Reconciliation export

After initload/golive, a local script MUST export bounded ChatGPT-readable evidence under:

    docs/reference/data/price_movement/<ticker-lower>/

The package must contain OHLC, ZigZag pivots, ZigZag swings, Price Movement swings,
profile and a machine-readable reconciliation summary.

## Business Rules

1. ZigZag owns segmentation; Price Movement owns characterization.
2. A Price Movement swing must map 1:1 to a confirmed ZigZag swing.
3. A swing may not be persisted before the ZigZag end pivot confirmation date.
4. Price Movement does not retroactively move a pivot.
5. ATR is descriptive only.
6. Profile labels are descriptive, not investment recommendations.
7. Changing classification thresholds requires a new/versioned Price Movement config.
8. Calibration recommendations that were not promoted do not silently change segmentation.

## Non-functional Requirements

- deterministic/idempotent full rebuild for the same config/ticker/input;
- bounded computation with one OHLC load and one ZigZag swing load per ticker;
- no query-per-bar implementation;
- additive DuckDB migration;
- explicit columns in persistence and public views;
- repository/UoW caller owns transactions;
- no run.py modification in this delivery;
- reconciliation evidence follows the global docs/reference/data/** rule.

## Acceptance Criteria

- AC-01: Price Movement creates exactly one enriched row for every eligible confirmed ZigZag swing in scope.
- AC-02: Start/end pivot identifiers, dates, prices and direction exactly reconcile to ZigZag public swing data.
- AC-03: stored SwingPct equals EndPrice / StartPrice - 1 within floating-point tolerance.
- AC-04: UP movements have positive SwingPct and DOWN movements have negative SwingPct.
- AC-05: TradingBars equals the OHLC interval count between pivot dates.
- AC-06: VelocityPctPerBar equals SwingPct/TradingBars when TradingBars > 0.
- AC-07: ATR normalization does not affect swing boundaries or pivot selection.
- AC-08: no source bar after a swing's ConfirmedAtDate is used to characterize that swing.
- AC-09: PathEfficiency remains in [0,1].
- AC-10: DirectionalPersistenceRate remains in [0,1].
- AC-11: profile uses at most the configured most-recent swing lookback and is deterministic.
- AC-12: classifier returns only INSUFFICIENT_HISTORY, TRENDING_UP, TRENDING_DOWN, RANGE_BOUND or MIXED.
- AC-13: rerunning the same initload produces the same business rows without duplicates.
- AC-14: reconciliation script exports all required CSV evidence under docs/reference/data/price_movement/<ticker>/.
- AC-15: reconciliation summary reports zero core identity/formula mismatches for a PASS candidate.
- AC-16: run.py remains unchanged and contains no Price Movement orchestration.
- AC-17: MWG-focused tests and structural validation are provided before multi-ticker expansion.
- AC-18: implementation owner reports IMPLEMENTED_PENDING_VALIDATION; final PASS belongs to TestEngineer.

## Dependencies

- active confirmed ZigZag public contracts;
- adjusted daily OHLC public contract vw_Ticker_OHLC_D;
- existing DuckDB UnitOfWork/connection conventions.

## Assumptions

- ZigZag public swings are already structurally validated.
- Each confirmed ZigZag swing contains both endpoint pivots.
- Daily OHLC is the correct descriptive path source for V2.

## Risks

- classification thresholds may require later empirical refinement;
- ATR20 is unavailable for very early history, so normalized fields may be NULL;
- future activation of ticker-specific/regime-aware ZigZag changes upstream swing facts and therefore requires Price Movement rebuild/reconciliation.

## Open Questions

None blocking for the MWG-first implementation.

## Suggested Routing

    BusinessAnalyst
      -> SolutionArchitect
      -> GeneralCoding
      -> TestEngineer

## BA Handoff

    REQUIREMENT HANDOFF
    Requirement ID: REQ-0031
    Outcome: ZigZag-based Price Movement Characterization V2
    Status: READY_FOR_DESIGN
    Primary next owner: SolutionArchitect.agent.md
    Material: docs/backlog/requirements/REQ-0031-zigzag-price-movement-character-v2.md
    Open questions: none blocking
    Acceptance criteria count: 18


## Current Delivery State

Implementation, migration SQL, tests, validation script, post-golive reconciliation exporter
and runbooks are present on main.

    IMPLEMENTED_PENDING_VALIDATION

Local validation still required:

    .\scripts\render_archify_analytics.ps1 -NoOpen
    python -m pytest tests\test_zigzag_engine.py tests\test_price_movement_zigzag.py -v
    python -m pytest tests\test_sync_write_pipeline_service.py -v
    python scripts\initload\init_reload_price_movement_mwg.py
    python scripts\validate_price_movement_mwg.py
    python scripts\export_price_movement_reconciliation.py --ticker MWG

Final PASS/FAIL belongs to TestEngineer. No run.py integration is authorized.


## Delivery Gate History

    BA
    Requirement quality: COMPLETE
    Gate: READY_FOR_DESIGN
    Material: this REQ-0031 document

    SA
    Architecture semantics: APPROVED_FOR_IMPLEMENTATION
    Design: docs/architecture/Price_Movement_Character_V2.md
    ADR: docs/adr/ADR-016-zigzag-price-movement-characterization-v2.md
    Archify generated artifact: pending local render/validation only

    DEV
    Implementation: COMPLETE
    State: IMPLEMENTED_PENDING_VALIDATION
    Validation owner: TestEngineer

The implementation currently consumes active ZigZag config ZZ_D_5_MVP. This is intentional:
V1.1 calibration recommendations remain research evidence because V1.2 concluded
KEEP_5_BASELINE for the pilot. REQ-0031 must never silently substitute an unpromoted
BaseDeviationPct.
