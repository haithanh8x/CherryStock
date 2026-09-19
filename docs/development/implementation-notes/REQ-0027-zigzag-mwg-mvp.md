# REQ-0027 — ZigZag MWG MVP Implementation Note

## Outcome

    IMPLEMENTED_PENDING_VALIDATION

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
