# Init / Full Reload Scripts

This directory owns explicit **full-load / full-reload / historical-backfill**
entry points.

Use it for workflows that intentionally rebuild an entire managed dataset or the
full history of a selected entity. Incremental/checkpoint jobs remain outside
this directory.

## Reload all AmiBroker market data

Runs a full EOD reload followed by a full Intraday reload.

```powershell
python scripts\initload\init_reload_raw_eod_raw_intraday.py
```

This is the broadest raw market-data reload entry point.

## Reload all AmiBroker EOD data

Reloads every source configured in `settings.amibroker_eod_targets`, including
stock, futures, index, warrant and the other configured EOD datasets.

```powershell
python scripts\initload\init_reload_raw_eod_tables.py
```

`from_last_day=None` is used, so the existing EOD loader rebuilds each managed
target from full source history.

## Reload all AmiBroker Intraday data

Resets and fully reloads the four configured Intraday sources:

- futures
- index
- stock
- warrant

```powershell
python scripts\initload\init_reload_raw_intraday_tables.py
```


## Rebuild `vw_raw_stock_eod`

Creates or replaces the enriched stock EOD market-limit view.

```powershell
python scripts\initload\init_reload_vw_raw_stock_eod.py
```

The view adds Market, ReferencePrice, CeilingPrice, FloorPrice, LimitUp/Down and
their streaks with provenance/quality fields. Full EOD, full Intraday and combined
raw reload entry points automatically drop/recreate this dependent view around
destructive source-table rebuilds.

Read-only validation:
`src/DuckDB/sql/vw_raw_stock_eod_preflight.sql`

Runbook:
`docs/runbook/vw_raw_stock_eod.md`

## Rebuild `vw_Ticker_OHLC_D`

Creates or replaces the daily OHLC + Intraday transaction-flow view.

```powershell
python scripts\initload\init_reload_vw_Ticker_OHLC_D.py
```

The full EOD, full Intraday and combined raw reload entry points automatically
drop/recreate this dependent view around their raw-table rebuild.

## Reload full EOD history for one stock ticker

Use this when a corporate action/back-adjustment requires full historical reload
for one stock without rebuilding the whole `raw_stock_eod` table.

```powershell
python scripts\initload\reload_raw_stock_eod_ticker.py FPT
```

Without an argument the existing script defaults to MWG.

## Full historical Technical Indicator refresh

Runs a full historical refresh for all active stock tickers and all enabled
indicator configurations.

```powershell
.\.venv\Scripts\python.exe scripts\initload\init_reload_cal_indicator_values.py
```

## Targeted OBV + AD Line historical initload

After OBV/AD metadata has been activated with
`src/DuckDB/sql/indicator_obv_ad_activate.sql`, backfill only the six affected
D/W/M configs:

```powershell
.\\.venv\\Scripts\\python.exe scripts\\initload\\init_reload_cal_indicator_values_obv_ad.py
```

The wrapper resolves ConfigIds dynamically, runs an MWG smoke refresh, then
performs a full historical backfill for `OBV_D/W/M` and `AD_D/W/M` only.
Unrelated indicator configs are not recalculated.

Read-only validation:
`src/DuckDB/sql/indicator_obv_ad_preflight.sql`


## SmartMoneyScore V1 full historical initload

Bootstraps SmartMoney V1 metadata/storage and performs a full historical backfill:

```powershell
python scripts\initload\init_reload_smart_money_score.py
```

The workflow runs inside one DuckDB UnitOfWork and exports generated DB metadata
only after a successful commit.

Read-only validation:

```text
src/DuckDB/sql/smart_money_v1_preflight.sql
```

Runbook:

```text
docs/runbook/SmartMoneyScore_V1.md
```

Incremental refresh belongs outside `scripts/initload/`:

```powershell
python scripts\run_smart_money.py --days 15
```

## Scope rule

Belongs in `scripts/initload/`:

- full raw-data reload;
- full historical reload for a selected entity;
- initial/full historical backfill;
- rebuild entry points that intentionally use full-history semantics.

Does not belong here:

- incremental/checkpoint refresh;
- diagnostics;
- seed/onboarding metadata;
- migration;
- evaluation/promotion;
- normal daily/monthly operational execution.
