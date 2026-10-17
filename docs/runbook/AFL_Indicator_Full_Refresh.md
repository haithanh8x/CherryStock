# Full-history AFL Indicator Refresh (CherryStock)

## Operational contract

The daily producer is **AmiBroker**, executing the saved New Analysis project:

- \`src/Amibroker/Formulas/CherryMon/Export_Indicator.afl\`
- \`src/Amibroker/Formulas/CherryMon/Export_Indicator.apx\` (saved **locally** from AmiBroker New Analysis)

The Python loader does not calculate any technical indicators and requires **no manual dim_indicator* onboarding**. It imports all 108 D/W/M columns for 17 requested indicator families into the existing long-format \`cal_indicator_values\`. Legacy metadata rows are automatically maintained **only** to preserve \`ConfigId\` and the existing \`vw_Ticker_indicators\` / \`vw_Indicator_config\` interfaces used by R/S and SmartMoney. Do not delete the old dim tables until consumers are redesigned.

### One-time AmiBroker setup

1. Open the latest \`Export_Indicator.afl\` in AmiBroker **New Analysis**, save the project as **\`Export_Indicator.apx\` next to that AFL**.
2. Set **Apply to = All symbols**, **Range = All quotations**, **Periodicity = Daily**.
3. In Analysis **Parameters**, set **Timeframes = ALL** and **Symbol filter = All symbols**.
4. **Save the APX** after setting the options. The APX is currently a machine-local configuration file, not committed in this change.
5. Run **Explore** manually once and confirm the full CSV has Ticker, Date, MA20_D, MA20_W, MA20_M, etc. If the APX's embedded FormulaContent is stale, reopen/re-save the latest AFL.

### One-time dry run

From the CherryStock repository root on Windows:

\`\`\`powershell
git switch main
git pull --ff-only origin main

python scripts\sync_amibroker_indicator_full.py --dry-run
\`\`\`

Expected: \`STAGED\` with >100 tickers and >200 distinct dates, then \`DRY RUN\`. No fact or metadata tables are modified.

### Full-history replacement on demand

\`\`\`powershell
python scripts\sync_amibroker_indicator_full.py
\`\`\`

The script runs the APX through existing AmiBroker New Analysis COM, exports to \`settings.data_dir/tmp_Export_Indicator_full.csv\`, validates all columns/data, and **atomically deletes and re-inserts** \`CherryMon.main.cal_indicator_values\`. A failed exploration, malformed CSV, incomplete historical coverage, DB error or invalid public-view projection leaves the previous fact intact. Normal reruns yield the same logical keys; \`CalculatedAt\` is refreshed.

Existing CSV replay (no AmiBroker run; use only a known complete CSV):

\`\`\`powershell
python scripts\sync_amibroker_indicator_full.py --csv "C:\path\to\full.csv" --dry-run
\`\`\`

This \`--csv\` option is intended for diagnostics/recovery only. The normal daily job always creates a fresh CSV.

### Daily integration

\`run.py\` enables \`ENABLE_AFL_INDICATOR_FULL_REFRESH = True\` and runs the APX replacement **after EOD/source sync commits**, before optional Movement and metadata export. To temporarily disable the stage during AmiBroker troubleshooting, set the flag to \`False\`.

### Failure protection and scope

- The CSV must have **all 108 indicator-value columns**, even if warmup results are NULL.
- At least 100 tickers and 200 distinct dates must have values. \`--min-tickers\` and \`--min-dates\` are explicit troubleshooting overrides for small controlled environments.
- No invalid numbers/dates, duplicate \`Ticker+Date+ConfigCode+ComponentCode\`, or missing D/W/M values.
- Historical minimum date, latest date, number of tickers and total rows cannot regress dangerously versus the existing fact.
- Automatic minimal \`dim_indicator\`, \`dim_indicator_component\`, and \`dim_indicator_config\` inserts happen inside the same transaction as the fact replacement, only where absent; existing ConfigIds remain stable.
- The full-history CSV will often be large; allow enough free local disk space and DuckDB temporary space. The COM wait limit is 1 hour for this job.
- The periodic output stored for W/M is only populated on their matching observed daily bars. The current W/M bars can still be provisional.
- The \`VWAP20\` AFL output is a **rolling HLC3×Volume/Volume approximation**, not true intraday/session VWAP.

## Tests

\`\`\`powershell
python -m pytest tests\test_sync_amibroker_indicator_full.py -v
\`\`\`

AmiBroker syntax/runtime compilation, end-to-end COM performance and parity with the older Python indicator values must be validated on the Windows machine. Those tests cannot run in GitHub's Linux environment.
