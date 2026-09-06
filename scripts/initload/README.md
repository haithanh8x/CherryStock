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
