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
