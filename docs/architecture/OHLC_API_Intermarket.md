# OHLC API layer — Intermarket Analysis (2026-10-25)

## Scope
Keep all eight comparison indicators/assets and Daily, Weekly and Monthly toggles unchanged. Intermarket alone fetches the latest one year of Yahoo Finance OHLC daily candles. Other Market Overview panels preserve their existing mock/R2 snapshot driver.

## Architecture
```text
GitHub Pages React (static, no Yahoo credentials)
     │ loadOhlc(provider, symbol, 1y, 1d)
     ▼
Cloudflare Worker: cherrystock-ohlc
     ├─ /health
     └─ /api/v1/ohlc?provider=yahoo&symbol=...&range=1y&interval=1d
           ├─ Yahoo Finance chart v8 (current adapter)
           ├─ FireAnt adapter [not configured]
           ├─ DuckDB adapter [not configured; needs secure private backend]
           └─ R2 adapter [not configured; recommended snapshot fallback]
```

Endpoint: `https://cherrystock-ohlc.cherrystock-haithanh8x.workers.dev`.
Override in Vite using `VITE_OHLC_API_BASE_URL` (optional); do not put secrets in VITE env vars.

Normalized contract:
```json
{"schemaVersion":1,"provider":"yahoo","symbol":"^GSPC","range":"1y","interval":"1d","timezone":"America/New_York","currency":"USD","asOf":"YYYY-MM-DD","candles":[{"date":"YYYY-MM-DD","open":0,"high":0,"low":0,"close":0,"volume":0}]}
```

The example zero values are schema placeholders, NOT real candles. Runtime rejects OHLC <=0 and reports API errors explicitly. Cache successful responses for 30 minutes at Worker edge; do not cache errors. CORS restricted to GitHub Pages origin and local Vite development origins. Yahoo chart endpoint is an unofficial, unguaranteed public interface; upstream may rate-limit or change. Never silently fall back to synthetic prices.

## Symbol mapping
- VN-Index: `^VNINDEX.VN`
- S&P 500: `^GSPC`
- Nasdaq-100: `^NDX`
- Bitcoin: `BTC-USD`
- Gold futures: `GC=F`
- WTI oil futures: `CL=F`
- DXY: `DX-Y.NYB`
- USD/VND: `VND=X`

## Data integrity
- Yahoo 1y/1d is fetched separately for each asset in parallel.
- All OHLC dates converted in the exchange timezone and deduplicated.
- Missing sessions remain missing: **no zero-filling, forward-filling, or synthetic fallback**.
- Daily chart shows the complete one-year period; weekly/monthly select each period's last available close.
- Relative returns normalized independently to the first valid close for each selected asset in the visible window.
- Some futures symbols may not have values on all trading days; UI reports missing assets.
- `^NDX` is Nasdaq-100, not Nasdaq Composite. Keep label as Nasdaq to preserve UI.

## Extend later
Implement provider-specific handlers behind the exact same `OhlcHistory` response: FireAnt licensed backend; DuckDB via authenticated service running alongside local DB or MotherDuck; R2 via public snapshot or private bucket binding. Do not expose DuckDB paths, FireAnt credentials, Cloudflare S3 secrets, or MotherDuck tokens to GitHub Pages.

## Deployment
- Worker source `cloudflare/workers/ohlc-api/worker.js`. Deploy to Cloudflare service `cherrystock-ohlc`.
- React client `frontend/src/data/ohlc.ts`; Intermarket component in `frontend/src/App.tsx`.
- Frontend deploy workflow automatically runs on a merge to main touching `frontend/**`.
- Check Yahoo responses and actual browser cross-origin requests after deploy. The Workers script upload/enable operations themselves are not proof that Yahoo returns valid candles.

## Live availability incident (2026-10-25)

- Confirmed by GitHub Actions probe: the Worker `/health` returned HTTP 200;
  its Yahoo `^GSPC` request returned HTTP 503 because Yahoo upstream returned **429**.
  The direct Yahoo Chart API probe from GitHub runner also returned 429.
- However `yfinance` successfully downloaded one-year EOD for seven assets on the
  same GitHub runner: ^GSPC (251), ^NDX (251), BTC-USD (365), GC=F (250),
  CL=F (250), DX-Y.NYB (250), VND=X (260).
- Yahoo `^VNINDEX.VN` returned only **one** EOD candle (2026-10-23).
  Other tested Yahoo aliases `^VNINDEX`, `VNINDEX.VN`, `VN30.VN`,
  `^VN30.VN` returned zero bars. No replacement proxy/index is used.
- GitHub Pages deployment now uses `scripts/export_intermarket_yahoo.py`
  to materialize `public/data/intermarket-1y.json` before the Vite build.
  This is actual Yahoo 1Y OHLC, not mock data. The frontend first calls
  the live Worker; if some calls fail, it falls back to the dated Yahoo
  snapshot asset-by-asset. UI identifies the source and missing assets.
- Daily schedule 02:00 UTC; page deployment fails closed if less than five
  of eight Yahoo assets have valid history; it does not publish synthetic
  OHLC. A failed daily refresh retains the previously deployed site.
- Follow-up: publish VNINDEX OHLC to R2 from local DuckDB's `raw_index_eod`
  or integrate an approved Vietnam-index data feed; do not fabricate
  VNINDEX history from a synthetic index or unrelated ETF.
