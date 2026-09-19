# REQ-0027 — ZigZag MWG MVP Implementation Note

## Outcome

    IMPLEMENTED_PENDING_VISUAL_ACCEPTANCE

The rolled-back ATR-based Price Movement implementation has been replaced by an isolated
event-first ZigZag MVP.

## Implemented Scope

- MWG only;
- adjusted daily OHLC;
- 5% percentage-reversal configuration;
- High/Low candidate extrema;
- Close confirmation;
- confirmed pivots;
- derived swing public view;
- one provisional current-leg record;
- full deterministic manual initload;
- structural validator;
- focused synthetic tests.

## Explicitly Not Implemented

- all-ticker run;
- daily run.py integration;
- incremental checkpoint;
- ATR segmentation;
- daily movement persistence;
- magnitude / velocity / persistence score;
- Movement Character labels;
- SmartMoney integration.

## Files

    docs/backlog/requirements/REQ-0027-price-movement-characterization.md
    docs/architecture/ZigZag_Engine.md
    docs/architecture/Price_Movement_Character.md
    docs/adr/ADR-013-zigzag-as-price-movement-segmentation-foundation.md
    src/DuckDB/sql/zigzag_mvp_schema.sql
    src/cherrystock/domain/analytics/zigzag/models.py
    src/cherrystock/domain/analytics/zigzag/engine.py
    src/cherrystock/infrastructure/database/repositories/zigzag_repository.py
    src/calcEngine/zigzag.py
    scripts/initload/init_reload_zigzag_mwg.py
    scripts/validate_zigzag_mwg.py
    tests/test_zigzag_engine.py
    docs/runbook/ZigZag_MWG_MVP.md

## GeneralCoding Handoff

    IMPLEMENTATION HANDOFF
    Requirement / Request: REQ-0027 ZigZag MWG MVP
    Outcome: IMPLEMENTED_PENDING_VALIDATION
    Changed files: ZigZag domain/repository/SQL/scripts/tests/docs
    Updated materials: requirement, ADR, architecture, Archify typed source, runbook
    Skills used: architecture-design contract; DuckDB migration conventions
    Developer verification: focused tests authored; local CherryMon execution required
    Acceptance criteria handed off: AC-01 through AC-12
    Known risks: 5% calibration; daily OHLC intraday ordering ambiguity
    Next owner: TestEngineer + user MWG visual gate

## Remaining Architecture Artifact Step

The Archify typed source has been updated. Generated HTML must be regenerated locally:

    .\scripts\render_archify_analytics.ps1 -NoOpen

Do not hand-edit the generated HTML.


## 2026-09-19 — Whipsaw / same-day pivot repair

TestEngineer evidence after the initial stall fix found three remaining structural failures:
one alternation error and two local-extreme mismatches caused by same-day High/Low ambiguity
plus post-hoc pivot deduplication.

Solution Architect refinement:

- daily OHLC uses one confirmed pivot per trading date;
- consecutive PivotDates must be strictly increasing;
- a next-leg candidate may only come from a bar strictly after the previous PivotDate;
- a candidate updated on the current bar cannot be confirmed on that same bar;
- post-hoc pivot deduplication is removed;
- interior local-extreme validation excludes neighboring pivot bars;
- confirmed pivots require PivotDate < ConfirmedAtDate.

Implementation changes:

- src/cherrystock/domain/analytics/zigzag/engine.py
- tests/test_zigzag_engine.py
- scripts/validate_zigzag_mwg.py
- src/DuckDB/sql/zigzag_mvp_schema.sql
- docs/architecture/ZigZag_Engine.md
- docs/adr/ADR-013-zigzag-as-price-movement-segmentation-foundation.md
- docs/runbook/ZigZag_MWG_MVP.md

Validation state remains IMPLEMENTED_PENDING_VALIDATION. Local CherryMon must rerun Phase 1-5.


## 2026-09-19 — TestEngineer technical PASS

Runbook Phase 1–8 completed successfully after correcting the validator to honor the
point-in-time contract.

Evidence:

- 7 focused ZigZag tests PASS;
- 3,041 MWG daily source rows;
- 279 confirmed pivots;
- structural_errors = 0;
- deterministic/idempotent rerun = 279 pivots;
- current leg = PROVISIONAL / UP from LOW 2026-09-14 @ 68.60;
- Jul–Sep review includes UP from LOW 2026-07-28 @ 61.54;
- calculation ~0.02–0.06s;
- 3 daily-pipeline regression tests PASS.

The remaining rollout gate is user visual acceptance of MWG and acceptance of the 5% config.
No multi-ticker implementation is authorized yet.
