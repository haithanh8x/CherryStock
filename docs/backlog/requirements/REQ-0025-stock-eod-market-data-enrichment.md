---
id: REQ-0025
title: Stock EOD Market Data Enrichment
status: READY_FOR_DESIGN
priority: P1
owner: BusinessAnalyst
primary_next_owner: SolutionArchitect
related:
  architecture:
    - docs/architecture/Data_Architecture.md
  adr:
  implementation:
  test:
  change_request:
---

# REQ-0025 — Stock EOD Market Data Enrichment

## Business Objective

Provide a complete, traceable and point-in-time-safe market-data contract for stock EOD consumers that need more than OHLCV, especially Custom Index calculation, weighting, liquidity filtering, valuation, screening and analytics.

The enriched contract must make the following information available with explicit semantics:

- TradingValue
- ReferencePrice
- CeilingPrice
- FloorPrice
- MarketCap
- FreeFloat

The requirement defines the data capability and semantics. It does not prescribe that all fields must be physically stored in `raw_stock_eod`.

## Background / Problem

Current generated database metadata shows that `main.raw_stock_eod` contains only:

```text
Ticker
Date
Open
High
Low
Close
Volume
OpenInt
```

Therefore the current stock EOD source does not provide a canonical daily contract for:

- actual daily traded value;
- exchange reference price;
- exchange ceiling price;
- exchange floor price;
- point-in-time market capitalization;
- point-in-time free-float information.

This limits downstream use cases that require liquidity, market-cap weighting, free-float-adjusted weighting, official daily price-band context or historical constituent calculations.

The repository already contains `main.raw_stock_fa` with fields including `Capital`, `Shares Float` and `Shares Outstanding`. These are potential existing inputs, but their business semantics, temporal grain, history coverage and suitability for point-in-time EOD use must be verified before reuse. They must not be assumed to be equivalent to daily MarketCap or FreeFloat without evidence.

The current Amibroker EOD reload path also persists only `Ticker/Date/OHLC/Volume/OpenInt`, so the missing data cannot be solved by merely reading additional columns from the existing contract unless the upstream source itself is changed or complemented.

## Stakeholders / Consumers

- Custom Index Engine
- Stock analytics and screening
- Data Platform / DuckDB ingestion
- Charting and market-context consumers
- Future portfolio/index weighting workflows
- Research, backtest and historical evaluation workflows

## Functional Requirements

1. CherryStock MUST expose a canonical stock market-data contract that can provide, for each ticker and relevant effective date, the following fields:
   - `TradingValue`
   - `ReferencePrice`
   - `CeilingPrice`
   - `FloorPrice`
   - `MarketCap`
   - `FreeFloat`

2. `TradingValue` MUST represent actual/source-reported daily traded value when such data is available. A derived estimate such as `Close * Volume` MUST NOT be silently presented as source-reported TradingValue.

3. `ReferencePrice`, `CeilingPrice` and `FloorPrice` MUST represent the official daily exchange price-band context for the ticker/date when available.

4. `MarketCap` MUST have explicit point-in-time semantics. Historical consumers MUST be able to determine the value applicable to a requested trading date without using future information.

5. `FreeFloat` MUST have explicit point-in-time semantics suitable for historical index weighting. The public contract MUST document whether the canonical representation is a factor/ratio, percentage, free-float shares, or a combination of these.

6. For every enriched field, the solution MUST define:
   - business meaning;
   - source/provenance;
   - logical grain;
   - effective/as-of date semantics;
   - key and uniqueness rules;
   - nullability and unavailable-data behavior;
   - whether the value is source-reported or derived.

7. The architecture MUST evaluate existing `raw_stock_fa.Capital`, `raw_stock_fa."Shares Float"` and `raw_stock_fa."Shares Outstanding"` before introducing duplicate data ownership.

8. The solution MUST NOT assume that all six fields belong physically in `raw_stock_eod`. Data with different temporal grains or ownership MAY use separate raw/dimension/calculated persistence with a stable consumer-oriented `vw_*` contract.

9. Historical backfill MUST be supported for the maximum trustworthy history available from the selected source(s), with explicit coverage reporting when full history is unavailable.

10. Incremental refresh MUST support normal daily execution and MUST be idempotent for the same logical key/effective date.

11. Downstream consumers MUST have a stable way to retrieve OHLCV plus the enriched market fields without implementing their own inconsistent joins or point-in-time logic.

12. Existing consumers of the current `raw_stock_eod` OHLCV contract MUST remain backward compatible unless a separately approved migration explicitly changes that contract.

## Business Rules

1. `raw_*` data must preserve normalized source facts as close to source semantics as practical.

2. A derived value MUST be distinguishable from a source-reported value. Derivation formula and required inputs MUST be documented.

3. Do not derive `TradingValue` as `Close * Volume` and label it as actual traded value.

4. Official Reference/Ceiling/Floor values should be sourced from exchange/vendor facts when available. If reconstruction is ever required, the calculation rule, exchange, effective period and rounding/tick-size behavior must be explicit and versioned.

5. MarketCap and FreeFloat are time-varying attributes. Historical calculations MUST use point-in-time/as-of semantics and MUST NOT use the latest known value for past dates when that would introduce look-ahead bias.

6. If `raw_stock_fa.Capital` or `Shares Float` is reused, its semantics and effective-date behavior MUST first be demonstrated to match the required contract.

7. Missing source data MUST remain explicitly missing or carry a documented quality/status flag. It MUST NOT be silently filled with zero.

8. The EOD price-fact logical key remains ticker + trading date unless an approved architecture introduces a different grain for a separate dataset.

9. Custom Index logic is a consumer of this capability and MUST NOT become the owner/Source of Truth for stock market-data facts.

## Scope

### In Scope

- Current-state assessment of the missing stock market fields.
- Source/provenance assessment for all six required fields.
- Evaluation of existing `raw_stock_fa` fields for possible reuse.
- Logical and physical data-model design.
- Point-in-time/as-of semantics for MarketCap and FreeFloat.
- Daily ingestion/refresh design.
- Historical backfill design.
- Data-quality and observability requirements.
- Stable downstream read contract.
- Backward compatibility with current `raw_stock_eod` consumers.
- Documentation and metadata updates required by the approved design.

### Out of Scope

- Custom Index calculation algorithms themselves.
- Definition of index weighting methodology beyond providing the required source data.
- Intraday/tick-level market-data redesign.
- General corporate-action architecture redesign, except where effective-date handling is necessary for correct MarketCap/FreeFloat history.
- UI/chart redesign unrelated to consuming the enriched data.
- Vendor procurement or commercial licensing decisions.

## Acceptance Criteria

### AC-01 — Current gap is explicitly verified

Given the current CherryStock database metadata  
When the requirement is taken into design  
Then the current `raw_stock_eod` schema is documented as containing `Ticker/Date/OHLC/Volume/OpenInt` and the six required enriched fields are identified as absent from that contract.

### AC-02 — Canonical semantics are defined

Given the six required fields  
When the architecture is completed  
Then each field has documented business meaning, source, grain, key, effective-date semantics, null behavior, provenance and source-reported/derived classification.

### AC-03 — Existing data is evaluated before duplication

Given `raw_stock_fa` already contains `Capital`, `Shares Float` and `Shares Outstanding`  
When MarketCap and FreeFloat are designed  
Then the architecture records whether those fields are reused, transformed or rejected, including the reason and point-in-time implications.

### AC-04 — Historical point-in-time correctness

Given a historical ticker/date request  
When MarketCap or FreeFloat is resolved  
Then the returned value is the value effective for that date/as-of period and no future observation is used.

### AC-05 — TradingValue provenance is unambiguous

Given a daily TradingValue consumed by analytics or Custom Index logic  
When its provenance is inspected  
Then the system can distinguish an actual source-reported TradingValue from any derived approximation, and a derived approximation is never silently labeled as reported TradingValue.

### AC-06 — Stable consumer contract exists

Given a downstream consumer needs OHLCV plus the enriched fields  
When it reads through the approved consumer contract  
Then it can obtain the required fields using documented ticker/date/as-of semantics without implementing custom point-in-time joins.

### AC-07 — Backfill and rerun are safe

Given the same historical period is ingested more than once  
When the enrichment/backfill workflow is rerun  
Then duplicate logical records are not created and existing values follow the approved conflict/update rules.

### AC-08 — Data quality is observable

Given a daily or historical enrichment run  
When required values are missing, inconsistent or stale  
Then the condition is observable through the project-standard validation/audit mechanism and is not silently converted to valid zero/default market data.

### AC-09 — Backward compatibility is preserved

Given an existing consumer reads `raw_stock_eod` using the current OHLCV contract  
When the enrichment capability is introduced  
Then that consumer continues to work without mandatory changes unless an explicitly approved migration says otherwise.

## Non-functional Requirements

- Performance: Daily refresh and historical backfill should use set-based/batch operations and avoid query-per-ticker patterns when batching is available.
- Reliability: Ingestion/backfill must be idempotent and define deterministic conflict handling for each logical key.
- Security: No special security requirement beyond existing CherryStock data-source credential and repository policies.
- Observability: Coverage, freshness, missing values, duplicate keys and source failures must be measurable and auditable.
- Compatibility: Existing `raw_stock_eod` consumers must remain backward compatible by default.

## Dependencies

- Availability and trustworthiness of upstream data source(s) for TradingValue, Reference/Ceiling/Floor, MarketCap and FreeFloat.
- `docs/architecture/Data_Architecture.md`.
- `docs/reference/DB_Metadata.md`.
- `.github/instructions/database.instructions.md`.
- Existing stock EOD ingestion/reload workflow.
- Existing `raw_stock_fa` data and its source semantics.
- CherryStock trading calendar for effective-date and coverage validation.

## Constraints

- CherryStock uses DuckDB and existing `raw_*/cal_*/dim_*/vw_*/sys_*` ownership conventions.
- Physical schema changes must not be chosen before the logical grain, key, ownership and point-in-time semantics are defined.
- The solution must avoid introducing a second Source of Truth for data already owned reliably elsewhere.
- Database writes and backfill must follow current transaction/idempotency rules.
- Public-facing query contracts should use explicit columns.

## Assumptions

- At least one trustworthy upstream source can provide some or all of the required market fields.
- Different required fields may come from different upstream sources and may have different update frequencies.
- MarketCap and FreeFloat may require effective-dated/as-of handling rather than a simple same-day raw EOD column.
- Existing `raw_stock_fa` values are candidates for reuse only; their equivalence to the target semantics has not yet been established.

## Open Questions

No business clarification is currently required to begin architecture design.

The following are design decisions owned by Solution Architect and must be resolved in the architecture material:

- Which upstream source is authoritative for each field?
- Should the physical model extend `raw_stock_eod`, introduce one or more separate datasets, or expose a composed `vw_*` contract?
- What is the exact mapping, if any, from `raw_stock_fa.Capital` to MarketCap?
- What is the exact mapping, if any, from `raw_stock_fa."Shares Float"` to the canonical FreeFloat contract?
- How should source effective dates be aligned to trading dates without look-ahead?
- What historical coverage can each source support?
- Which enriched fields should be persisted versus derived at read/calculation time?

## Risks

- Vendor/source history may be shorter than OHLCV history.
- Mixing latest fundamental/share data into historical dates can introduce look-ahead bias.
- `Capital` or `Shares Float` may have semantics different from the target MarketCap/FreeFloat definitions.
- A denormalized extension of `raw_stock_eod` may duplicate facts with different temporal grains.
- Reconstructed Reference/Ceiling/Floor values can be wrong across exchange-rule or tick-size changes if rules are not versioned.
- Using `Close * Volume` as TradingValue can materially misstate actual traded value.
- Source licensing, limits or availability may constrain backfill.

## Suggested Routing

- Architecture required: Yes
- Primary next owner: SolutionArchitect
- Domain instructions: `.github/instructions/database.instructions.md`; crawler instructions if a new external source is introduced
- Validation owner: TestEngineer

The Solution Architect must produce an explicit Data Model section as required by `.github/agents/SolutionArchitect.agent.md`, including logical/physical model, grain, keys, relationships, ownership, lineage, point-in-time semantics and downstream contract.

## Handoff

```text
Status: READY_FOR_DESIGN
Primary next owner: SolutionArchitect
Acceptance criteria count: 9
Blocking questions: None; remaining questions are architecture/data-source design decisions.
```
