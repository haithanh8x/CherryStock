# Chart Architecture

## Purpose
Define a stable separation between market-data preparation and visualization components.

## Preferred flow

```text
CherryMon public view / domain service
        ↓
query / data preparation
        ↓
chart-ready data contract
        ↓
reusable chart component
        ↓
page / dashboard composition
```

## Component contract
Every reusable chart should make input and output explicit.

Input should define:
- required/optional fields;
- ticker/timeframe/date range assumptions;
- units/scales;
- ordering;
- missing-value behavior.

Output should define:
- render/component type;
- interactions/events;
- selected/current values if applicable;
- empty-state behavior.

## Design rules
- Avoid mixing complex SQL, business calculation and rendering in one function.
- Domain calculations should be reused rather than recreated for a chart.
- Prefer stable views/services as chart data sources.
- Keep reusable components ticker-agnostic unless a domain requirement explicitly prevents it.

Implementation policy: [[../../.github/instructions/chart.instructions|Chart Instructions]].

Back to [[../00_HOME|Knowledge Home]].