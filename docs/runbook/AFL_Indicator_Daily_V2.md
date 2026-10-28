# CherryStock — AFL Indicator Daily V2 (Local Agent Runbook)

> Effective after code merge on `main`. This runbook supersedes
> `AFL_Indicator_Full_Refresh.md` for production ingestion.
> **No test scenarios are required** by the owner. Execute the migration and
> daily operation; report actual execution status and blockers truthfully.

## Decision and data contract

Canonical source: `C:\Github\CherryStock\src\Amibroker\Formulas\CherryMon\Export_Indicator.apx`.

- **Do not modify** the saved APX or change its `ApplyTo=2` filter.
- Do not calculate indicators in Python. AmiBroker AFL remains the only producer.
- The export stays wide: one `Ticker+Date` CSV row containing 108 indicator
  columns for D/W/M. W/M may appear only on the last observed bar of their period.
- Importer uses a **temporary local copy** of AFL+APX and forces
  `Timeframes=ALL`, `Export mode=INCREMENTAL`, and the exact `--days` value.
  Original .apx and .afl are never overwritten.
- The fact storage does **not** contain `ConfigId` or `ComponentCode`.

### Production tables

`"CherryMon"."main"."cal_indicator_values"` (closed historical observations):
`Ticker, Date, IndicatorName, Timeframe, Value, UpdatedAt`.
Logical PK = `(Ticker,Date,IndicatorName,Timeframe)`.

`"CherryMon"."main"."cal_indicator_current"` (developing W/M):
`Ticker, Date, IndicatorName, Timeframe, Value, UpdatedAt`.
Logical PK = `(Ticker,IndicatorName,Timeframe)`.

Names are taken from the source column without its trailing timeframe suffix:
`MA20_D -> (MA20,D)`, `BB20_2_UPPER_W -> (BB20_2_UPPER,W)`,
`MACD12_26_9_SIGNAL_M -> (MACD12_26_9_SIGNAL,M)`.
This preserves component uniqueness inside `IndicatorName`, not a separate
component key.

- **D**: history immediately on each exported daily date.
- **W/M older than current calendar week/month**: closed history on the actual
  last daily bar emitted by AFL. No forward fill.
- **W/M in current calendar week/month**: developing snapshot; rewrite the
  `Date` + `Value` for each ticker/indicator/timeframe each run.
  Example on 28 Oct 2026: the current `W` and `M` are valid indicators
  calculated from current price, but not yet confirmed period-close values.
- On the next calendar period, delete the obsolete developing snapshot and
  obtain the closed W/M observation from the newly exported completed bar.
  The daily window includes a monthly overlap to cover the rollover.
- `NULL`/blank CSV cells are **absent observations**, never deletion signals.
- The transitional `vw_Ticker_indicators` view projects legacy
  `ConfigId/ComponentCode` from dim tables for downstream R/S/SmartMoney.
  Neither field is persisted in the two new tables.

## One-time local agent steps (do before daily run)

1. Stop all Python runs, DuckDB writers and AmiBroker batch processes.
2. Ensure the existing DuckDB path resolves to `C:\Datafile\CherryMon.duckdb`.
3. Create a **filesystem backup** of the database after writers are stopped
   and the WAL has been checkpointed/cleanly closed. Store it outside the DB
   directory and note the backup filename. Do not delete or overwrite it.
4. Update repository:

   ```powershell
   cd C:\Github\CherryStock
   git switch main
   git pull --ff-only origin main
   ```

5. Execute the transactional one-time schema/data migration:

   ```powershell
   python -m scripts.migrate_indicator_storage_v2
   ```

   The script copies all old rows into
   `CherryMon.main.cal_indicator_values_legacy_backup` and verifies its row
   count before atomically replacing the original physical table (no
   destructive loss of the legacy data), then creates history/current
   tables and translates legacy
   config/component keys into the new `IndicatorName/Timeframe` keys and
   replaces `vw_Ticker_indicators` with a compatibility projection.
   Everything is committed in one transaction; failure rolls back.

   The migration needs enough free space for the complete legacy backup **and**
   the new indicator fact/index because there can be tens of millions of rows. Do not run two DuckDB
   writers simultaneously. If a dependent custom DuckDB VIEW blocks the
   atomic rename/replacement, stop; preserve backup; inspect its SQL and
   update its dependency to the new contract before retrying. Never force
   DROP CASCADE or delete the legacy table.

6. Execute the **production daily update** as configured:

   ```powershell
   python run.py
   ```

   `run.py` runs the APX incremental stage **after Ingest commits and before**
   Industry/MarketCap aggregate. Window:
   `indicator_days = max(35, days_diff + 3)` trading bars. This allows daily
   overlap plus the most recent month-end correction. The APX runtime copy
   receives exactly `indicator_days`, unlike the old fixed 10-bar UI value.

## Resume just the indicator stage (no EOD re-ingest)

When Ingest has committed but a later aggregate failed, rerun just the AFL
loader using the same --days window or a larger window for the missed period:

```powershell
python -m scripts.sync_amibroker_indicator_full --mode incremental --days 35
```

If indicators were down for a long period, increase `--days` to cover the
missing period and the preceding closing week/month. Unlike `days_diff`,
which follows the EOD pipeline, this is explicit indicator recovery.
For a full-source re-import that *does not delete old v2 values*:

```powershell
python -m scripts.sync_amibroker_indicator_full --mode full
```

To replay a previously exported CSV without opening AmiBroker:

```powershell
python -m scripts.sync_amibroker_indicator_full --mode incremental --days 10 --csv "C:\path\to\export.csv"
```

Avoid a 10-day CSV replay for monthly catch-up: it may not contain the last
trading day of the prior month.

## Operational results to report

Report the actual output lines `[AFL INDICATORS] STAGED` and
`[AFL INDICATORS] COMMITTED`, including CSV rows, ticker coverage,
date range, counts per D/W/M and counts upserted into history/current.
The migration reports `legacy_backup_rows`, `history_rows`, and
`current_rows`. Do not claim local execution occurred based only on a
GitHub code commit.

The loader ensures primary-key UPSERT, numeric parsing, D/W/M column presence,
duplicate prevention and stale-export protection as part of the real load.
These are production data guards, not a separate test scenario.

## Compatibility and boundaries

- Existing `dim_indicator*` tables are left in place for the compatibility
  view. `vw_Indicator_config` is not dropped.
- The former Python `refresh_technical_indicators` write path is retired;
  `IndicatorRepository.replace_indicator_checkpoint` rejects legacy writes.
  Archived scripts that expect the old physical `ConfigId` columns must be
  ported before reuse.
- `cal_indicator_values_legacy_backup` remains for rollback/reference. Never
  remove without the owner's explicit approval.
- Do **not** invoke the former full-history replacement (delete/reinsert) code.
  The active `scripts.sync_amibroker_indicator_full` CLI now delegates to the
  v2 importer; `--mode full` also UPSERTs without deleting v2 history.
- Weekly/monthly values may move daily in `cal_indicator_current`.
  Dashboard consumers should use the union compatibility view or read
  `cal_indicator_current` specifically to distinguish developing values.
- The daily EOD `days_diff` is not an independent AFL checkpoint. If EOD was
  already committed but AFL lagged for more than the 35-day minimum, use the
  explicit resume command above with a wider range.
