---
applyTo: "src/Chart/**/*.py,**/*chart*.py,**/*Chart*.py"
---

# Chart Instructions

This file defines mandatory chart and visualization implementation rules.

Canonical knowledge:
- `docs/architecture/Chart_Architecture.md`
- `docs/architecture/theme.md`
- `.github/skills/chart-authoring/SKILL.md`
- relevant chart/domain architecture and ADR materials routed from `docs/00_HOME.md`

## Agent routing
- Chart-type recommendation, analytical visualization mapping, Flint `ChartAssemblyInput` authoring, Flint validation/rendering/compilation → `.github/agents/Chart.agent.md` + `.github/skills/chart-authoring/SKILL.md`.
- Materially unclear analytical/business objective, user behavior, scope or acceptance criteria → `.github/agents/BusinessAnalyst.agent.md`.
- New chart architecture, reusable contract, renderer abstraction or cross-page design → `.github/agents/SolutionArchitect.agent.md`.
- Clear production chart/UI implementation following an approved chart decision/contract → `.github/agents/GeneralCoding.agent.md`.
- Test design/execution or independent UI validation → `.github/agents/TestEngineer.agent.md`.

The Chart Agent owns visualization selection and Flint authoring, not production application integration. General Coding MUST update the affected canonical chart/theme document when an approved input, output or interaction contract changes, then hand off with `IMPLEMENTED_PENDING_VALIDATION`.

## Flint authoring policy
- MCP server `flint` is the mandatory generation path for Flint-authored charts.
- Treat ECharts, Vega-Lite and Chart.js example galleries as visualization catalogs; do not copy their backend-native specs as the primary authoring contract.
- Author Flint semantic input first: `semantic_types` + `chart_spec`, referencing real columns by exact name.
- Transform aggregation/join/pivot/derived/reshape needs before Flint.
- Validate generated specs with `flint/validate_chart`.
- Prefer `flint/create_chart_view` for interactive output; use `flint/render_chart` for static output and `flint/compile_chart` only when backend-native JSON is required.
- Detailed decision rules and MCP sequence live only in `.github/skills/chart-authoring/SKILL.md`; do not duplicate them here.

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