---
name: chart-authoring
description: "Select the best visualization from the analytical question and input data, then author, validate, and render a Flint chart. Use for chart recommendation, chart-type comparison, visualization design, ChartAssemblyInput authoring, or Flint MCP chart generation."
---

# CherryStock Chart Authoring Skill

## Purpose

Turn a user's analytical intent plus a described or available dataset into the most suitable visualization, then generate it through the repository's `flint` MCP server.

This skill separates two decisions:

1. **Visualization decision** — determine what chart best answers the analytical question.
2. **Flint authoring/execution** — express that decision as a valid Flint `ChartAssemblyInput`, validate it, and render or compile it when requested.

Do not choose a chart merely because it is visually attractive or because one chart library has an example for it.

## Reference catalogs

Use these three catalogs as visualization references when chart selection is required:

- Apache ECharts examples: https://echarts.apache.org/examples/en/index.html#chart-type-dataset
- Vega-Lite examples: https://vega.github.io/vega-lite/examples/
- Chart.js examples collected by wpDataTables: https://wpdatatables.com/chart-js-examples/

These sources are **idea/catalog references**, not the final execution contract. A selected concept must still be checked against Flint support and expressed through Flint semantics.

Flint authoring rules are derived from the upstream skill:

- https://github.com/microsoft/flint-chart/blob/main/agent-skills/flint-chart-author/SKILL.md

When the upstream Flint skill and this repository skill differ on Flint syntax or supported behavior, prefer the upstream Flint contract and report the mismatch so this skill can be updated.

## Mandatory tool

For chart generation, validation, rendering, supported-type discovery, or backend compilation, use MCP server:

`flint`

The VS Code repository configuration is `.vscode/mcp.json`.

Do not manually author a final ECharts, Vega-Lite, or Chart.js backend spec when Flint can produce it.

## Workflow

### Step 1 — Restate the analytical question

Convert the request into one primary analytical question.

Classify the analytical task into one or more of:

- comparison / ranking;
- trend or change over time;
- composition / part-to-whole;
- distribution;
- relationship / correlation;
- deviation / variance;
- flow / transfer / network;
- hierarchy;
- financial OHLC;
- geospatial;
- KPI / target / status.

If several questions exist, identify the primary question first. One chart should have one dominant analytical purpose.

Examples:

- "Which sectors receive the strongest money flow?" → ranking/comparison.
- "How does sector leadership rotate through time?" → change-over-time/rank.
- "Where does money transfer from one sector to another?" → flow/network.
- "How are return and liquidity related?" → relationship/correlation.

### Step 2 — Profile the input data contract

Inspect or infer only from evidence:

- row grain;
- field names;
- temporal fields and frequency;
- quantitative measures and units;
- categorical dimensions and cardinality;
- ordered/ranked dimensions;
- hierarchy fields;
- source/target/value fields for real flows;
- OHLC fields for financial charts;
- geographic fields;
- missing values;
- sorting requirements;
- whether data is long or wide;
- approximate row count / density.

Never invent a field that is not present.

If the data is insufficient for the requested analytical question, state the missing fields before selecting a misleading chart.

### Step 3 — Decide whether a chart is appropriate

Prefer a table or KPI when visual encoding adds little value.

Use a chart only when it materially improves pattern detection, comparison, change detection, relationship discovery, or communication.

### Step 4 — Generate candidate chart families

Consult the three reference catalogs conceptually and generate a small candidate set.

Typical mapping:

| Analytical question | Strong candidates |
|---|---|
| Compare/rank categories | Bar, grouped bar, lollipop, dot plot |
| Trend over time | Line, area, sparkline |
| Composition | Stacked bar, normalized stacked bar, pie/donut for few categories |
| Distribution | Histogram, boxplot, density, strip plot |
| Relationship | Scatter, bubble, connected scatter |
| Deviation/change contribution | Waterfall, diverging bar |
| Flow/network | Sankey, graph/network |
| Hierarchy | Treemap, sunburst, tree |
| Rank changes over time | Bump chart |
| Dense category × time matrix | Heatmap |
| OHLC | Candlestick |
| KPI vs target | KPI card, bullet |
| Geography | Map, choropleth |

Do not force pie/donut for many categories or line charts for unordered categorical axes.

### Step 5 — Score and choose the best chart

Evaluate each serious candidate against:

- **Analytical fit — 40%**: directly answers the primary question.
- **Data fit — 25%**: matches grain, semantic types, cardinality, and shape.
- **Readability — 15%**: minimizes cognitive load and visual clutter.
- **Interaction/time behavior — 10%**: handles filtering, zoom, temporal navigation, or selection when important.
- **Flint/backend fit — 10%**: supported cleanly by Flint and the intended renderer.

Return one recommended chart. Provide at most two alternatives and explain the trade-off.

Do not choose based on novelty.

### Step 6 — Apply finance/flow-specific sanity checks

For sector or smart-money analysis, distinguish **measured transfer** from **relative strength**:

- If rows contain true `source → target → value` relationships, Sankey/network is a valid flow candidate.
- If data only contains per-sector scores/returns/volume over time, do **not** claim money literally flowed from A to B. Prefer heatmap, bump, stacked/stream area, line, or ranking views depending on the question.
- If a Sankey is used across time, prefer a selected period or small multiples. A single Sankey is poor for a long continuous time axis.
- For OHLC, use Candlestick only when open/high/low/close are all available.

### Step 7 — Check Flint support and choose backend

Before authoring, identify the Flint chart type and required channels.

Use `flint/list_chart_types` when:

- the exact registered Flint chart name is uncertain;
- backend coverage is uncertain;
- the candidate is advanced (for example Sankey, Graph, Tree, Sunburst, Parallel Coordinates).

Backend guidance:

- Prefer **Vega-Lite** for broad declarative/statistical visualization when no backend is mandated.
- Prefer **ECharts** when the selected chart requires advanced interactive types such as Sankey, Graph, Tree, Treemap, Sunburst, Funnel, Gauge, or Parallel Coordinates.
- Prefer **Chart.js** for supported conventional charts when project/runtime constraints favor it.

The recommendation is driven by the analytical question first, backend second.

### Step 8 — Prepare data before Flint

Flint is a chart assembler, not a general data-wrangling engine.

Before Flint, transform data when the chart requires:

- aggregation;
- filtering;
- joins;
- pivots;
- derived columns;
- non-trivial long/wide reshaping;
- source/target edge construction.

Use repository data services, SQL, Python, or another appropriate tool.

Flint's supported static multi-series fold on `x` or `y` arrays may be used when applicable. Do not invent a Flint `transforms` property.

Do not manually re-serialize a large dataset into the prompt/spec. Bind by URL/host variable where possible; embed only small data.

### Step 9 — Author Flint ChartAssemblyInput

Author the semantic input, not a backend-native output spec.

Required conceptual structure:

```json
{
  "data": { "values": [] },
  "semantic_types": {
    "field": "Category"
  },
  "chart_spec": {
    "chartType": "Exact Flint Chart Type",
    "encodings": {
      "x": { "field": "field" }
    }
  }
}
```

Rules:

- use exact existing field names;
- assign a semantic type to every encoded field;
- use the most specific Flint semantic type available;
- include every required channel for the chosen chart type;
- set `chartProperties` only when they express intentional chart behavior;
- prefer semantic types over manual scale/format overrides;
- do not hand-tune backend colors/fonts/ticks in the Flint input;
- do not mix total/subtotal rows with their component rows in stacked/grouped/color encodings.

Common semantic type defaults when uncertain:

- number → `Quantity`;
- category/string → `Category`;
- date → `Date` or `DateTime`.

Never invent semantic type names.

### Step 10 — Validate with Flint MCP

After authoring a spec, use Flint validation before claiming it is ready.

Preferred MCP sequence:

1. `flint/list_chart_types` — only when support/channels are uncertain.
2. `flint/validate_chart` — validate the authored input/spec.
3. If validation fails, fix the spec/data contract and validate again within the normal bounded retry policy.

Never skip validation when a chart is being generated.

### Step 11 — Render or compile

If the user asks to **see** the chart:

- default to `flint/create_chart_view` for an interactive chart when App UI support is available;
- use `flint/render_chart` for PNG/SVG or when interactive UI is unavailable.

Use `flint/compile_chart` only when backend-native JSON is explicitly needed for application integration or debugging.

Do not edit compiled Vega-Lite/ECharts/Chart.js JSON and feed it back into `render_chart`.

### Step 12 — Visual/data sanity validation

Before finishing, verify:

- chart title/purpose matches the analytical question;
- fields and units are correct;
- dates are sorted chronologically;
- ranking/sorting communicates the intended comparison;
- stacked/grouped semantics are not confused;
- legends do not overload the view;
- labels are readable at expected density;
- zero baseline is appropriate for the measure;
- no double counting from totals/subtotals;
- no unsupported visual claim is made from the data;
- empty or sparse data behavior is explicit.

## Required output

Use this concise contract:

```text
CHART DECISION
Analytical question:
Input data contract:
Recommended chart:
Why this chart:
Alternatives:
Target backend:
Flint chart type:
Field → channel mapping:
Required pre-transform:
Flint validation:
Render/compile result:
Caveats:
```

When only advice is requested, stop after recommendation and mapping.

When chart generation is requested, continue through Flint validation and render.

## Anti-patterns

- Choosing the library first and forcing the analysis into its examples.
- Using Sankey when no source/target transfer data exists.
- Using pie/donut for high-cardinality categories.
- Writing direct ECharts/Vega-Lite/Chart.js JSON instead of Flint semantic input.
- Inventing missing columns.
- Embedding a large dataset by hand.
- Performing hidden aggregation inside visualization code.
- Claiming a chart is valid without Flint validation when Flint is available.
- Treating a visually attractive chart as analytically superior without evidence.
