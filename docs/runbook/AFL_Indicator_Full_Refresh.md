> **DEPRECATED (2026-10-28):** The physical indicator fact contract has moved to
> `Ticker, Date, IndicatorName, Timeframe, Value, UpdatedAt`, with developing
> W/M values in `cal_indicator_current`. Follow the current local agent runbook:
> [AFL_Indicator_Daily_V2.md](AFL_Indicator_Daily_V2.md).
> The old ConfigId/ComponentCode full-history replacement instructions below
> are retained for historical reference only. Do not execute them on v2.

# Full-history AFL Indicator Refresh (CherryStock)

## Operational contract

The daily producer is **AmiBroker**, executing the saved New Analysis project:

- \`src/Amibroker/Formulas/CherryMon/Export_Indicator.afl\`
- \`src/Amibroker/Formulas/CherryMon/Export_Indicator.apx\` (saved **locally** from AmiBroker New Analysis)

The Python loader does not calculate any technical indicators and requires **no manual dim_indicator* onboarding**. It imports all 108 D/W/M columns for 17 requested indicator families into the existing long-format \`cal_indicator_values\`. Legacy metadata rows are automatically maintained **only** to preserve \`ConfigId\` and the existing \`vw_Ticker_indicators\` / \`vw_Indicator_config\` interfaces used by R/S and SmartMoney. Do not delete the old dim tables until consumers are redesigned.

### One-time AmiBroker setup

1. Open the latest \`Export_Indicator.afl\` in AmiBroker **New Analysis**, save the project as **\`Export_Indicator.apx\` next to that AFL**.
2. Set **Apply to = Filter** (`ApplyTo=2`) to use your saved AmiBroker ticker universe (or **All symbols**, `ApplyTo=0`), **Range = All quotations**, **Periodicity = Daily**.
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
- At least 100 tickers and 200 distinct dates must have values; if using ApplyTo=2, the filter must cover the full intended production ticker universe. \`--min-tickers\` and \`--min-dates\` are explicit troubleshooting overrides for small controlled environments.
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

## Incremental UPSERT (latest 10 trading dates)

Save the AmiBroker APX with **ApplyTo=2 (Filter)**, **Periodicity=Daily**,
**Timeframes=ALL**, and **Range = 10 recent bars** (or All quotations; the
importer keeps only the latest 10 trading dates). Unlike the full mode, the
incremental mode accepts a recent-bars APX and does not require 200 dates.

```powershell
python scripts\sync_amibroker_indicator_full.py --mode incremental --days 10 --dry-run
python scripts\sync_amibroker_indicator_full.py --mode incremental --days 10
```

Incremental mode **never truncates or deletes historical rows**. It MERGEs by
`Ticker + Date + ConfigId + ComponentCode`, updating existing values and
inserting missing keys in one transaction. Only the latest 10 **distinct
trading dates present in the export** are used. Re-running the same CSV does
not create duplicates. Existing `run.py` remains on **full** mode until
explicitly switched; this new incremental CLI is standalone.

**Caveats:** AmiBroker must have the *full OHLCV history available to calculate*
EMA/OBV/AD and other long-lookback values; the APX limits only output rows.
Weekly/monthly expandPoint cells can be sparse in a ten-day export; their
values are upserted only where present. A later full reconciliation is
recommended if historical adjustments or W/M period revisions occur.

## Limit AmiBroker CSV output to 10 trading bars

The AFL has **Export mode = FULL|INCREMENTAL** and **Incremental trading bars = 10**.
In New Analysis, open the updated `Export_Indicator.afl`, choose
`Export mode = INCREMENTAL`, `Incremental trading bars = 10`, keep
`Apply to = Filter` (`ApplyTo=2`) and `Periodicity = Daily`.
**Range can remain All quotations**: the AFL's `Filter` limits exported
Exploration rows to the last ten bars for each ticker while indicator
calculations retain the full available OHLCV history.

**Save the APX** after changing Parameters, as AmiBroker saves an embedded
formula copy. The Python incremental mode refuses APX files with an older
embedded formula. For a full-history export, change `Export mode = FULL`
and re-save the APX before running full mode.

```powershell
python scripts\sync_amibroker_indicator_full.py --mode incremental --days 10 --dry-run
python scripts\sync_amibroker_indicator_full.py --mode incremental --days 10
```

`--days` selects the number of trading dates to UPSERT; set the matching
AFL parameter to 10 to avoid exporting more than needed. On tickers missing
the latest market sessions, the AFL exports their last ten available bars,
and the importer retains the latest ten distinct dates globally.
