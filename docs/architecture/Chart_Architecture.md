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

## SmartMoney ticker detail popup (2026-09-26)

This is presentation integration of existing contracts, not a new strategy engine.
The SmartMoney tab owns one reusable client-local NiceGUI dialog. A normal ticker
click (or Enter) opens it; modifier-click retains the native external TradingView link.

- `ticker_detail_contract.py`: explicit allowlist of 21 SmartMoney, 24 Movement
  Profile and 44 Movement Context columns, deterministic latest-per-config queries,
  field explanations/examples and unit formatting.
- `ticker_detail_data.py`: bounded ticker reads with `DuckDBManager(read_only=True)`;
  reuses `build_level_ladder` without changing source selection or calculations.
- `ticker_detail_dialog.py`: official TradingView Advanced Chart widget beside
  the existing `levelLadderChart` renderer; full view fields below.
- `Presentation.theme.build_nicegui_css()`: theme-derived ticker hover/active/focus
  rules, 150ms transitions and reduced-motion support.

Each public view returns the latest row per declared configuration grain for the
selected ticker. Each row displays its own date and config identity. This is a
latest-state inspection screen, not a historical point-in-time join or synthesized
buy/sell recommendation. Missing fields stay unavailable rather than becoming zero.
A panel error is logged and displayed without suppressing unrelated panels.

R/S values retain the existing engine's price units (thousand VND/share) and
distance percent units. Movement fractions are formatted as percent (0.1 → 10%);
scores stay 0–100; DirectionalBias remains a signed ratio, not a return.
Provisional current-leg data are clearly distinguished from confirmed profile data.

The widget uses the official external-embedding script mounted as a real script
node into a live, explicitly sized (620px) DOM container after dialog render.
The vendor creates its own cross-origin iframe; there is no extra srcdoc sandbox
with an opaque origin around it. Symbol changes are disabled and TradingView
attribution is retained. Script failure/20s timeout has a visible fallback link. It receives only the exchange-qualified symbol and chart
settings; CherryStock analytics are not sent to TradingView. A direct external
link remains visible when the widget is unavailable. TradingView owns its internal
controls/tooltips; CherryStock owns hints on its surrounding UI and every rendered
analytics field. Widget coverage/data freshness may differ from the local database.

Loading runs off the UI event loop only on ticker activation. A generation guard
prevents results for a closed/replaced request from updating the current dialog;
closing unloads the widget. No new calculation/persistence/SSOT or migration is
introduced; existing analytics topology remains unchanged.

Deployment and independent validation:
`docs/runbook/SmartMoney_Ticker_Detail_Popup.md`.

### Ticker diagnostics and UI follow-up

The state block now renders its complete confidence-ranked rows in a single wrapping
list; no MA200 headings/separators are shown. Each ticker is bold and colored by
its own TradeAction. Snapshot/builder calculations and coverage are unchanged.

Optional CHERRYSTOCK_TICKER_TRACE=1 emits request-correlated JSONL under
docs/reference/data/smart_money/ticker_detail_popup/timing.jsonl. Spans distinguish
each view's connection, execute, fetch/map and close, market lookup, R/S total,
worker wait, server render build, and TradingView script/iframe lifecycle.
Browser durations use performance.now since widget mount; server elapsed_ms
uses its own perf_counter. Never add nested/inclusive spans or mix these clocks.
iframe_load means the document loaded, not that candles or market data are ready.

scripts/profile_ticker_detail.py calls the production read-only loader with
bounded tickers/repetitions and exports baseline stage/summary CSV. --profile
adds separate Python cumulative/self-time hotspot evidence for R/S subcalls;
it incurs measurement overhead and is not a latency baseline.
No cache, query tuning, provider selection or engine calculation changes are
included before real measurements establish the bottleneck.
