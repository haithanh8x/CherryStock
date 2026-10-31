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
