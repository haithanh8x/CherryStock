---
applyTo: "src/Chart/**/*.py,**/*chart*.py,**/*Chart*.py"
---

# Chart Instructions

This file owns chart and visualization implementation rules.

## Responsibilities
- Separate data acquisition/preparation from rendering.
- Define explicit input/output contracts for reusable chart components.
- Reuse project-wide data services/views instead of embedding duplicated SQL in chart code.
- Keep chart modules focused on visualization behavior.

## Input contract
A chart component should document:
- required fields;
- optional fields;
- ticker/timeframe/date-range assumptions;
- units/scales;
- missing-data handling;
- sorting requirements.

Validate required inputs before rendering and fail clearly when the contract is violated.

## Output contract
Document:
- returned component/object type;
- interactions/events exposed to parent UI;
- selected/current value outputs where applicable;
- empty-state behavior.

## Architecture
Preferred flow:

```text
DuckDB public view / domain service
        ↓
data preparation
        ↓
chart-ready contract
        ↓
reusable chart component
        ↓
page/dashboard composition
```

Avoid:
- complex SQL + business transformation + rendering in one function;
- hard-coded ticker-specific behavior;
- chart-specific copies of domain calculations;
- hidden assumptions about order or units;
- hard-coded application theme colors when a semantic token exists in `src/Presentation/theme.py`.

Presentation theme defaults MUST resolve from the centralized Theme System documented in `docs/architecture/theme.md`. Explicit caller-provided series colors remain allowed when color is part of the chart input contract.

## Validation
Test at least:
- normal dataset;
- empty dataset;
- one-point dataset;
- missing optional values;
- unsorted input where ordering matters;
- duplicate levels/points where relevant;
- current value outside/inside expected range.

Architecture entry point: `docs/architecture/Chart_Architecture.md`.