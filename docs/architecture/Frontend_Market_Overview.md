# Market Overview — React + Cloudflare R2 snapshot architecture

## Scope

This increment replaces the **Tổng quan** panel group under
`src/webapp/NiceGUI_chart.py:overview_tab_content()` on a static React/Vite
GitHub Pages frontend. It does not migrate the adjacent Screener, Portfolio,
R/S, SmartMoney or Operations tabs.

## Read-only architecture

```text
AmiBroker -> local DuckDB -> (future snapshot publisher)
                                |
                 Cloudflare R2: cherrystock bucket
                  manifest + versioned snapshot
                                |
                  public GET / browser CORS
                                |
              GitHub Pages React Market Overview
               data driver -> chart-ready contract
               view/components -> CSS design tokens
```

The frontend cannot connect securely to authenticated S3 endpoints directly.
The future local snapshot publisher should use private credentials on the
local machine, upload immutable objects, validate them and update
`market-overview/v1/manifest.json` **last**.

The browser reads public HTTPS objects from the R2 public-domain/custom-domain
endpoint only; alternatively a server-side proxy is required for a private
bucket. Public bucket objects must contain **non-sensitive market data only**.
No access key, secret key, DuckDB connection string or MotherDuck token may be
placed in Vite environment variables.

## Data adapter contract

- `frontend/src/data/driver.ts`: source selection and R2 manifest loader.
- `frontend/src/data/types.ts`: typed `MarketOverviewSnapshot` v1.
- `frontend/src/data/mock.ts`: deterministic synthetic snapshot.
- `frontend/src/App.tsx`: read-only visualization composition.
- `frontend/src/theme/theme.ts`: frontend-wide presentation tokens.

`VITE_MARKET_DATA_SOURCE=mock` is the safe default; `r2` is explicit and
requires `VITE_R2_PUBLIC_BASE_URL`. Snapshot failures are displayed rather
than silently replaced with synthetic data. Browser requests use
`cache: no-store` for the manifest so users can see published updates
without a redeployment.

The mock source never queries Cloudflare. It is not a statement about
current Vietnamese market price, investor flow, index sector performance or
market health.

## Chart semantics

- The intermarket panel normalizes each selected series to 0% at start of
  the **selected visible period**, permitting assets with different units
  to be compared.
- Breadth percentages are the percentage of covered tickers above each MA;
  the future publisher must specify its eligible ticker universe.
- Sector performance is an input from a future upstream industry index;
  the React frontend does not approximate it from member stock prices.
- Investor flow input is daily VND billions; weekly/monthly views sum those
  daily amounts. These flows must be published from licensed, validated
  source data, not derived from volume-only inference.
- Timeseries dates must be ascending and expressed as YYYY-MM-DD.

## Design system boundary

`frontend/src/theme/theme.ts` owns all app-wide semantic CSS color tokens
for the **new React frontend**, supporting per-browser dark/light selection.
The prior NiceGUI runtime keeps `src/Presentation/theme.py` during gradual
migration; only the React theme registry is consumed by React pages.
If the requirement later becomes one **cross-runtime** theme source, migrate
both registries to a shared JSON design-tokens contract in a separate change,
rather than importing Python in a browser or duplicating per-page values.

## Deploy

Push to `main` touching `frontend/**` triggers
`.github/workflows/deploy-frontend-pages.yml`. Pull request build check runs
`.github/workflows/verify-frontend.yml`. Confirm the deploy job and
GitHub Pages site rather than assuming push == successful publish.
