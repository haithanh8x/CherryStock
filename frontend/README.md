# CherryStock Frontend — Market Overview

React 19 + TypeScript + Vite, deployed to GitHub Pages at:
https://haithanh8x.github.io/CherryStock/

## UI migration

The **Market Overview** page ports the NiceGUI `Trung tâm thị trường > Tổng quan`
dashboard (`src/webapp/NiceGUI_chart.py:overview_tab_content`) with the following
panels: four market indices; turnover, breadth, foreign/proprietary net flows;
intermarket comparison (VN-Index, S&P 500, Nasdaq, BTC, gold, oil, DXY, USD/VND);
watchlist search; MA20/50/100/200 breadth; industry performance; and
institutional/individual/foreign/proprietary flow charts.
Other NiceGUI tabs are displayed as disabled placeholders and **are not yet migrated**.

The dashboard defaults to demo values for panels without a live data feed.
Market breadth is an exception: it loads real MA statistics from the
Cloudflare R2 breadth API independently of the dashboard mock setting.

## Setup

```bash
cd frontend
npm install
npm run dev
npm run build
```

Vite's `base` is `/CherryStock/` so the site works on GitHub Pages.

## Data drivers

Data driver: `src/data/driver.ts`; contract: `src/data/types.ts`;
deterministic fixture: `src/data/mock.ts`.

Default: `VITE_MARKET_DATA_SOURCE=mock` (no external request).

When snapshot files are published from local DuckDB to the **cherrystock** R2
bucket, configure build-time environment variables:

```env
VITE_MARKET_DATA_SOURCE=r2
VITE_R2_PUBLIC_BASE_URL=https://<your-public-r2-domain>/
```

The frontend uses **public read-only HTTPS** (R2 public bucket/custom domain
with CORS allowing the GitHub Pages origin). It must **never** access the
authenticated S3 API from a browser or include access keys in Vite variables.
For private buckets, implement a server-side proxy / signed delivery instead.
`VITE_*` values are public and compiled into the site; the published GitHub
Pages build reads these **GitHub Actions repository variables**:\n\n- \`CHERRYSTOCK_MARKET_DATA_SOURCE\`: \`mock\` (default) or \`r2\`.\n- \`CHERRYSTOCK_R2_PUBLIC_BASE_URL\`: public HTTPS origin for the R2 bucket.\n\nSet them under **Settings → Secrets and variables → Actions → Variables**.\nAfter changing variables, manually rerun **Deploy CherryStock Frontend**\nusing **Actions → Run workflow**, because variable changes alone do not\ntrigger a new build.

Required objects under the configured public base URL:

```text
market-overview/v1/manifest.json
market-overview/v1/snapshots/<yyyymmdd>.json
```

Example `market-overview/v1/manifest.json`:

```json
{
  "schemaVersion": 1,
  "snapshot": "market-overview/v1/snapshots/20261016.json"
}
```

The snapshot JSON must follow `MarketOverviewSnapshot` in
`src/data/types.ts` with `schemaVersion: 1`, `asOf` (`YYYY-MM-DD`),
`indices`, `summary`, `intermarket`, `breadth`,
`industries`, `flows` and `watchlist`.
- Timeseries sorted in ascending `date` order (`YYYY-MM-DD`).
- Quote and breadth units use **percent points** (e.g. 1.25 = +1.25%).
- `turnoverBn`, `foreignNetBn`, `proprietaryNetBn`,
  `turnoverBn` (industries), and investor flow figures use **VND billions**.
- Indices/intermarket assets include symbol-native close values.
- Chart prices have no client-side adjusted-price calculation.
- Flow values are daily sums (weekly/monthly period totals are computed client-side).
- Sector performance represents real calculated industry indices only after an
  upstream industry-index pipeline is implemented; mock figures are synthetic.

**Safe publishing order:** write immutable dated snapshot first; validate;
publish the manifest last, atomically flipping readers to the new version.
Never publish the manifest pointing at missing/incomplete objects.
The driver explicitly reports failed/invalid R2 data; it will **not silently
fall back to demo numbers**.

## Centralized theme

Change visual tokens in **`src/theme/theme.ts`** (one frontend SSOT).
All styles, charts and other future pages reference semantic CSS variables.
Dark/light theme is selected from the header and remembered in local storage.
The legacy Python NiceGUI theme is separately defined at
`src/Presentation/theme.py`; this migration does not change its runtime.

## Deployment

`.github/workflows/deploy-frontend-pages.yml` builds `frontend/` and deploys
to GitHub Pages on pushes to `main` affecting `frontend/**`.
A working Pages URL requires repository Pages to use the **GitHub Actions**
source, and successful deployment permissions/environment. Check the latest
`Deploy CherryStock Frontend` run before claiming live deployment.

## Interactive market-breadth chart

The breadth chart is backed by the real `cal_indicator_history` series, served
via the read-only Cloudflare Worker `cherrystock-breadth`. It uses each
timeframe's native D/W/M indicator values over the most recent two years.

- Hover or tap the plot to snap to a reporting date. A crosshair and tooltip
  show that date and all four percentages (>MA20/50/100/200).
- Use the **3T / 6T / 1N / 2N** controls for a recent-window shortcut.
- Drag the left/right grips in the mini overview to resize the selected
  interval; drag its center to pan through history; click outside the window
  to reposition it.
- Keyboard: focus the plot and press arrow keys to inspect neighboring dates.
  Focus a brush grip and use arrow or PageUp/PageDown to resize the interval.
- On touch devices, tap the chart for the point details and drag the overview
  grips to adjust time.

Interactive component: `src/components/BreadthInteractiveChart.tsx`.
CSS: `src/components/BreadthInteractiveChart.css`.
R2 daily publication and historical backfill notes:
`scripts/cloudflare_sync/INDICATORS_RUNBOOK.md`.
