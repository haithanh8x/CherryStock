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

## Visualization Decision and Authoring Boundary

Chart selection and one-off Flint authoring are owned by `.github/agents/Chart.agent.md` using `.github/skills/chart-authoring/SKILL.md`.

The boundary is:

```text
analytical question + data contract
        ↓
chart recommendation
        ↓
chart-ready transformation (when needed)
        ↓
Flint semantic ChartAssemblyInput
        ↓
Flint validation/render/compile
        ↓
production integration (General Coding, when requested)
```

ECharts, Vega-Lite and Chart.js example catalogs are used to broaden visualization choices. They do not replace the Flint semantic input contract for generated charts.

A visualization recommendation is not itself a production architecture change. Reusable component contracts, cross-page interaction patterns, renderer abstractions and application integration remain governed by Solution Architect / General Coding according to the Agent Harness.

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
- Presentation colors must use the centralized theme Source of Truth instead of chart-local app color constants.

## Presentation Theme Boundary

`src/Presentation/theme.py` owns the app-wide visual tokens consumed by ECharts, lightweight_charts, NiceGUI and AG Grid.

Chart modules may own geometry, labels, interactions and explicit caller-provided color overrides, but their default application colors must resolve from the centralized theme.

See [[theme|Theme Architecture]] and [[../adr/ADR-003-centralized-theme-system|ADR-003]].

Implementation policy: [[../../.github/instructions/chart.instructions|Chart Instructions]].

Back to [[../00_HOME|Knowledge Home]].