# CherryStock Indicator / R2 Runbook

Daily sequence in run.py:
1. Ingest market data.
2. Export AmiBroker with incremental 1 bar, replace cal_indicator_current.
3. Export AmiBroker with incremental 10 bars, upsert cal_indicator_history.
4. Aggregate.
5. Publish vw_Ticker_Info, cal_indicator_current, cal_indicator_history and market breadth to R2.

R2 bucket: cherrystock
- cal_indicator_current.parquet: complete snapshot.
- cal_indicator_history/month=YYYY-MM.parquet: monthly partitions in the last 600 calendar days.
- cal_indicator_history/checkpoint.json: last successfully published date and active months.
- market-breadth/v1/latest.json: daily/weekly/monthly breadth with the corresponding native D/W/M indicator series.

The latest ten trading days and affected month partitions are recalculated each daily run. Checkpoint is saved only after data and breadth have been uploaded.

A read-only Cloudflare Worker named cherrystock-breadth serves /api/v1/breadth using the CHERRYSTOCK_R2 bucket binding. The frontend's breadth panel and advance/decline strip fetch this endpoint independently of the other mock/R2 dashboard data.

Test:
    python -m scripts.cloudflare_sync.sync_indicators --dry-run
Publish:
    python -m scripts.cloudflare_sync.sync_indicators
Normal daily:
    python run.py

Environment flags:
- CHERRYSTOCK_INDICATOR_SYNC_ENABLED=false: skip daily indicator work
- CHERRYSTOCK_R2_SYNC_ENABLED=false: skip R2 publication
- VITE_BREADTH_API_BASE_URL: optional frontend Worker endpoint override

Important: DuckDB must permit a read-only connection. Close any other application's conflicting DuckDB connection before publishing. Do not bypass active database locks.

## Two-year market breadth

The market-breadth chart covers the previous **two calendar years** relative to the last available indicator date (for the 2026-10-30 EOD this starts 2024-10-30). It displays every observed D, W or M point rather than truncating to 48 points. The chart's JSON includes `windowYears: 2` and `windowStart` for auditability.

The R2 indicator-history Parquet retention remains **600 calendar days** as previously configured; the breadth JSON is computed from the broader **local** history before publication, independently of the R2 Parquet window.

If an existing AmiBroker history begins after the required two-year start, backfill only the MA20/MA50/MA100/MA200 D/W/M inputs for the missing dates from the existing `cal_indicator_values` and `dim_indicator_config` tables. This is a historical legacy-data bridge, not a recomputation in AFL; the values may differ slightly from AmiBroker calculations. Rows already present in `cal_indicator_history` are never overwritten.

```powershell
python -m scripts.backfill_market_breadth_ma_history --dry-run
python -m scripts.backfill_market_breadth_ma_history
python -m scripts.cloudflare_sync.sync_indicators
```

Do not silently plot a partial two-year chart: the R2 publisher rejects an insufficiently populated history window.
