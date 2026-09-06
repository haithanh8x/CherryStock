# Init Load Scripts

Entry points for one-time/full initialization workflows.

## AmiBroker Intraday

Resets and fully reloads all configured Intraday sources:

- futures
- index
- stock
- warrant

Run from repository root:

```powershell
python scripts\initload\init_reload_amibroker_intraday.py
```

## Technical Indicators

Runs a full historical refresh for all active stock tickers and all enabled
indicator configurations.

Run from repository root:

```powershell
.\.venv\Scripts\python.exe scripts\initload\init_refresh_technical_indicators.py
```

## Scope rule

Keep only scripts whose primary purpose is full/init loading in this directory.
Incremental refresh, seed/onboarding, diagnostics, migrations and operational
evaluation scripts remain under their existing locations.
