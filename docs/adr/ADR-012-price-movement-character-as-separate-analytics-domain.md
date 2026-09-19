# ADR-012 — Price Movement Character as a Separate Analytics Domain

- **Status:** Accepted
- **Date:** 2026-09-15
- **Requirement:** REQ-0027
- **Decision scope:** Analytics component boundary, persistence ownership and dependency direction
- **Segmentation decision:** ADR-013

## Context

REQ-0027 requires CherryStock to reason about directional price swings and, later, derive
movement magnitude, velocity, persistence and historical context.

This behavior is stateful and event-oriented. A pivot can occur on one date but only become
knowable on a later reversal-confirmation date. That lifecycle does not fit the ordinary
long-format technical-indicator value grain.

The first implementation mixed segmentation and daily path analytics and was later rolled
back after MWG pivot-quality and performance issues were found.

## Decision

Price/swing analytics remain a separate analytical domain from the Technical Indicator Engine.

The domain is now decomposed into two layers:

    Layer 1: ZigZag Swing Engine
             owns pivot segmentation and current provisional leg

    Layer 2: Price Movement Character
             future consumer of confirmed ZigZag swings
             owns movement features/profiles/classification

The ZigZag layer is reusable by Chart, pattern research and future analytical models.

It does not write into cal_indicator_values and is not registered as an ordinary indicator
component in the MVP.

## Source of Truth

Price source:

    vw_Ticker_OHLC_D

ZigZag confirmed-event source:

    cal_zigzag_pivot
      -> vw_Ticker_ZigZag_Pivots
      -> vw_Ticker_ZigZag_Swings

Current state:

    cal_zigzag_current_leg
      -> vw_Ticker_ZigZag_Current

## Point-in-Time Rule

Every confirmed pivot exposes both:

    PivotDate
    ConfirmedAtDate

A historical consumer may only use a pivot when:

    ConfirmedAtDate <= as_of_date

The system must never infer historical knowledge from PivotDate alone.

## Dependency Direction

MVP:

    vw_Ticker_OHLC_D
            |
            v
    ZigZag Swing Engine
            |
            v
    ZigZag public contracts
            |
            v
    validation / analyst review

Future:

    ZigZag public contracts
            |
            v
    Price Movement Character
            |
            v
    optional downstream analytics

No SmartMoney dependency is introduced by REQ-0027 MVP.

## Persistence Principle

The swing foundation is event-first.

The MVP does not persist a daily historical movement row for every ticker/date.

This reduces storage and prevents the segmentation layer from becoming coupled to expensive
per-bar movement-feature recomputation.

## Consequences

### Benefits

- clean state/event ownership;
- reusable pivot contract;
- point-in-time semantics are explicit;
- event-first persistence;
- ZigZag can be validated independently before movement scoring.

### Costs

- current/provisional state must be modeled separately;
- downstream historical research must respect ConfirmedAtDate;
- percentage-reversal configuration requires empirical validation before broad rollout.

## Relationship to ADR-013

ADR-012 owns the component boundary.

ADR-013 owns the concrete segmentation decision: percentage-reversal ZigZag, first validated
only on MWG.
