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

**All default numbers are synthetic mock values.** The UI clearly marks DEMO
mode and does not claim real market data.

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
Pages build needs matching values configured in its GitHub Actions job.

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
