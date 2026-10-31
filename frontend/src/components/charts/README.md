# CherryStock reusable multi-series chart template

Reusable implementation: `MultiSeriesLineChartTemplate.tsx`
Styles: `MultiSeriesLineChartTemplate.css`
Production usage: `../BreadthInteractiveChart.tsx` (Market Overview).

## What this template includes

- TradingView Lightweight Charts v5 (React + TypeScript), responsive light/dark themes.
- Native X-axis zoom, Y-axis scaling, chart dragging/pan, crosshair, mobile touch/pinch, keyboard date inspection.
- A fixed date/value inspector ABOVE the plotting canvas (no floating popup covering line series).
- Multi-select series chips: show one or multiple lines; never hide the final remaining series.
- Date window shortcuts: last 3 months, 6 months, 1 year, or all available data.
- **No Time Range Navigator** / mini-chart / range brush; no mouse-wheel zoom.
- Visible TradingView attribution and link remain mandatory.

## Use in another feature

```tsx
import { MultiSeriesLineChartTemplate } from './components/charts/MultiSeriesLineChartTemplate';

const lines = [
  { key: 'sales', label: 'Doanh thu', color: 'var(--chart-ma20)', width: 3 as const },
  { key: 'profit', label: 'Lợi nhuận', color: 'var(--chart-ma50)', width: 2 as const },
];

const points = [
  { date: '2026-10-29', sales: 104, profit: 36 },
  { date: '2026-10-30', sales: 108, profit: 38 },
];

<MultiSeriesLineChartTemplate
  data={points}
  series={lines}
  valueSuffix=""
  allRangeLabel="Tất cả"
  accessibleName="Biểu đồ doanh thu và lợi nhuận"
/>
```

## Data contract

`data` must be sorted by `date` ascending, with unique ISO dates (`YYYY-MM-DD`) and finite numeric values for each `series[].key`. All series share the same date axis; values should use comparable units because they share the right Y scale.

| Prop | Type | Meaning |
| --- | --- | --- |
| `data` | `{ date: string; ... }[]` | Time series data |
| `series` | `{ key: string; label: string; color: string; width?: 1\|2\|3\|4 }[]` | Lines and toggles |
| `valueSuffix` | `string`, default `%` | Suffix for Y-axis and selected values |
| `allRangeLabel` | `string`, default `Tất cả` | Shortcut label for the full period |
| `accessibleName` | `string` | Screen-reader chart description |

Use the wrappers in each feature to set domain-specific fields and labels. Do not duplicate the chart implementation. The breadth wrapper uses a percent suffix and a `2N` shortcut for its two-year dataset.

Note: TradingView's Lightweight Charts is MIT-licensed, but its attribution notice must remain visible. Source: https://tradingview.github.io/lightweight-charts/.
