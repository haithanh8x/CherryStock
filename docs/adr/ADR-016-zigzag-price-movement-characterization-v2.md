# ADR-016 — ZigZag-based Price Movement Characterization V2

- Status: Accepted
- Date: 2026-09-19
- Requirement: REQ-0031
- Related: ADR-012, ADR-013, ADR-014, ADR-015

## Context

CherryStock previously attempted to locate and characterize price movements in one ATR-adaptive
engine. That mixed segmentation with description and produced swing-boundary behavior that was
hard to reconcile.

ADR-013 established the percentage-reversal ZigZag engine as the segmentation foundation.
REQ-0028 through REQ-0030 then evaluated static calibration, multi-ticker promotion and
regime-aware research.

Price Movement can now resume as a separate downstream analytical domain.

## Decision

Price Movement V2 will consume confirmed ZigZag public swing facts and will never detect or
move pivots itself.

The dependency direction is:

    adjusted OHLC ---------------------+
                                       |
    active ZigZag public swings -------+--> Price Movement V2
                                               |
                                               +--> enriched confirmed swings
                                               +--> recent movement profile

ZigZag owns segmentation.
Price Movement owns characterization.

## Deviation / Calibration Decision

Price Movement does not read a V1.1 BaseDeviationPct recommendation and silently rebuild
swings.

It consumes the active ZigZag public contract. A calibrated or regime-aware deviation only
affects Price Movement after that upstream behavior has been separately promoted and has
materialized as active ZigZag swing facts.

This preserves the current V1.2 decision that the 5% baseline remains sufficient for the pilot.

## ATR Decision

ATR is permitted only as a descriptive normalization feature after swing boundaries exist.

ATR may not:

- establish a pivot
- move a pivot
- determine swing direction
- alter confirmed ZigZag identity

## Persistence Decision

REQ-0031 owns additive Price Movement persistence:

- dim_price_movement_config
- cal_price_movement_swing
- cal_price_movement_profile
- vw_Ticker_Price_Movement_Swings
- vw_Ticker_Movement_Profile

ZigZag persistence remains the segmentation Source of Truth.

## Point-in-Time Decision

A Price Movement swing becomes eligible on the end pivot ConfirmedAtDate inherited from
ZigZag.

Descriptive path features may use only OHLC through EndDate. They do not use future bars after
confirmation.

## Classification Decision

Initial MovementCharacter labels are deterministic descriptive summaries:

    INSUFFICIENT_HISTORY
    TRENDING_UP
    TRENDING_DOWN
    RANGE_BOUND
    MIXED

Thresholds are versioned Price Movement configuration, not investment rules.

## Production Boundary

REQ-0031 does not modify run.py.

The first delivery is a deterministic MWG initload + validation + reconciliation path.
Multi-ticker scheduling requires a later explicit promotion decision.

## Consequences

Positive:

- segmentation correctness remains isolated in ZigZag
- movement features become independently testable
- no ATR-driven boundary drift
- reconciliation is pivot/swing identity based
- future ZigZag promotion can flow downstream through stable public contracts

Trade-offs:

- changing the active ZigZag config requires Price Movement rebuild
- early history can have NULL ATR-normalized features
- classifier thresholds require later empirical review
- the first release is not automatically daily/incremental production

## Architecture Artifact Status

Canonical Markdown and typed Archify source are updated in Git.

Generated Archify HTML must be regenerated locally. Until showcase validation returns ok=true,
do not claim Archify artifact synchronization complete.


## Architecture visualization synchronization

The ADR decision is accepted. The Archify typed source is already synchronized with the
canonical design. Local generation/validation of
`docs/architecture/generated/CherryStock_Analytics_Calculation_Engines.html` remains an
operational validation step and does not change the accepted ADR semantics.
