# ADR-002 — Indicator Configuration and Calculated Value Sources of Truth

## Status
Accepted

## Context
CherryStock Indicator Engine separates metadata/configuration, internal calculated persistence and downstream consumption. Without explicit contracts, consumers can couple directly to internal tables and indicator onboarding can become schema/hard-code driven.

## Decision
Use two explicit public contracts:

```text
vw_Indicator_config
    = Single Source of Truth for indicator metadata + executable config + component mapping

vw_Ticker_indicators
    = Single Source of Truth for downstream calculated indicator values
```

`cal_indicator_values` remains internal long-format persistence and is not the preferred downstream read contract when `vw_Ticker_indicators` satisfies the use case.

New indicator families are metadata/config-driven through:
- `dim_indicator`;
- `dim_indicator_component`;
- `dim_indicator_config`;
- default D/W/M configuration where applicable.

## Alternatives Considered
### Make `cal_indicator_values` the public contract
Rejected because it exposes persistence details and increases downstream coupling.

### Add columns to one wide fact table for every indicator
Rejected because onboarding would require repeated schema changes.

### Create one table per indicator
Rejected because it fragments metadata, orchestration and consumer access.

## Consequences
Positive:
- indicator onboarding is configuration-driven;
- downstream consumers depend on stable views;
- long-format persistence can evolve internally;
- D/W/M families can be managed consistently.

Trade-off:
- views must be maintained as stable contracts and validated whenever internal schemas evolve.

## Related Documents
- [[../architecture/Indicator_Engine|Indicator Engine Architecture]]
- [[../../.github/instructions/indicators.instructions|Indicator Instructions]]
- [[../00_HOME|Knowledge Home]]