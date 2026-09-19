# Price Movement Character Engine

- **Status:** SUPERSEDED_BY_PRICE_MOVEMENT_CHARACTER_V2
- **Owner:** .github/agents/SolutionArchitect.agent.md
- **Requirement:** docs/backlog/requirements/REQ-0027-price-movement-characterization.md
- **Foundation:** docs/architecture/ZigZag_Engine.md
- **ADR:** docs/adr/ADR-012-price-movement-character-as-separate-analytics-domain.md
- **Segmentation ADR:** docs/adr/ADR-013-zigzag-as-price-movement-segmentation-foundation.md

## Supersession

The deferred design in this document has now resumed as REQ-0031.

Canonical active design:

    docs/architecture/Price_Movement_Character_V2.md

Canonical decision:

    docs/adr/ADR-016-zigzag-price-movement-characterization-v2.md

This file is retained only as the historical deferred design bridge after rollback of Price
Movement V1. Do not implement new behavior from this document.

## Purpose

Price Movement Character remains the future analytical layer that will describe how a ticker
moves using magnitude, velocity, persistence and historical context.

The previous ATR-based implementation has been rolled back.

The engine is **not** implemented in the current MVP. Its segmentation dependency is now the
independent ZigZag Swing Engine.

## Target Dependency

    vw_Ticker_OHLC_D
            |
            v
    ZigZag Swing Engine
            |
            v
    confirmed pivots / derived swings
            |
            v
    future Swing Feature Engine
            |
            +-> magnitude
            +-> duration
            +-> velocity
            +-> efficiency / persistence
            +-> ticker-relative profiles
            |
            v
    future Movement Character classification

ATR is no longer responsible for locating pivots.

ATR may be reintroduced later only as an optional descriptive/normalization feature after
ZigZag segmentation has already established swing boundaries.

## Current Delivery Scope

Current scope is only:

    MWG
    daily OHLC
    ZigZag 5% evaluation config
    confirmed pivots
    derived swings
    provisional current leg

Not currently implemented:

- movement daily history;
- MagnitudeScore;
- VelocityScore;
- PersistenceScore;
- historical percentiles;
- MovementCharacter labels;
- run.py integration;
- SmartMoney integration;
- all-ticker processing.

## Future Contract

When this layer resumes, it must consume stable ZigZag public contracts rather than
re-implementing pivot detection.

Candidate future input:

    vw_Ticker_ZigZag_Swings

Any future Price Movement implementation must preserve:

- point-in-time eligibility via ConfirmedAtDate;
- separation of confirmed swing facts from provisional current state;
- O(n) or otherwise bounded incremental behavior;
- explainable independent dimensions;
- no direct claim of Smart Money intent from price path alone.

## Rollout Gate

Price Movement work remains blocked until the ZigZag MWG MVP passes structural and visual
validation.

See:

- docs/architecture/ZigZag_Engine.md
- docs/runbook/ZigZag_MWG_MVP.md
