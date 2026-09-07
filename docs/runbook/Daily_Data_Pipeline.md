# CherryStock Daily Data Pipeline

- **Status:** ACTIVE
- **Entry point:** `run.py`
- **Canonical orchestrator:** `src/cherrystock/application/services/sync_write_pipeline.py`
- **Transaction owner:** `DuckDBUnitOfWork`
- **Last aligned with runtime:** 2026-09-07

## Purpose

This document is the canonical operational description of the CherryStock daily
data pipeline.

`run.py` owns the runtime boundary and shared DuckDB transaction. It does not
orchestrate private pipeline methods individually. The application service owns the
daily order:

```text
run.py
  ↓
DuckDBUnitOfWork
  ↓
SyncWritePipelineService.run()
  ↓
daily ingestion / calculation / Data Quality
  ↓
COMMIT
  ↓
exportDuckDB_metadata()
```

If any blocking Data Quality check raises before commit, the shared UnitOfWork
rolls back the whole daily write set.

---

# 1. Daily flow — full sequence

```text
01  AmiBroker EOD sync — 12 source domains
        ↓
02  Refresh Trading Calendar (updateHoliday.sql)
        ↓
03  AmiBroker EOD Data Quality — raw_stock_eod
        ↓
04  AmiBroker Intraday sync — 4 source domains
        ↓
05  Intraday Data Quality — futures / index / stock / warrant
        ↓
06  Yahoo Finance EOD
        ↓
07  Yahoo Finance Data Quality
        ↓
08  Fundamental Analysis snapshot
        ↓
09  FA Snapshot / Reference Data Quality
        ↓
10  Ticker Master
        ↓
11  Ticker Reference Data Quality
        ↓
12  VNINDEX_NOT_VIN calculation
        ↓
13  Index Data Quality
        ↓
14  Moving Average / Trend calculation
        ↓
15  Trend Data Quality
        ↓
16  Technical Indicator Engine
        ↓
17  Indicator Data Quality
        ↓
18  Ensure SmartMoney V1 schema
        ↓
19  SmartMoneyScore incremental refresh
        ↓
20  SmartMoney Data Quality
        ↓
21  COMMIT shared DuckDB transaction
        ↓
22  exportDuckDB_metadata()
```

The Trading Calendar refresh intentionally runs **immediately after AmiBroker EOD
sync and before any dated Data Quality check**. Dated validation resolves the
expected trading date from `dimCalendar`; running the calendar refresh later can
produce a false stale/ahead-of-calendar failure.

---

# 2. AmiBroker EOD ingestion

`syncAmibroker_EOD()` loads every target configured by
`settings.amibroker_eod_targets`.

| # | AmiBroker source | DuckDB target |
|---:|---|---|
| 1 | `EOD/active` | `raw_active_eod` |
| 2 | `EOD/commodity` | `raw_commodity_eod` |
| 3 | `EOD/foreign` | `raw_foreign_eod` |
| 4 | `EOD/futures` | `raw_futures_eod` |
| 5 | `EOD/index` | `raw_index_eod` |
| 6 | `EOD/industry` | `raw_industry_eod` |
| 7 | `EOD/market` | `raw_market_eod` |
| 8 | `EOD/other` | `raw_other_eod` |
| 9 | `EOD/prop` | `raw_prop_eod` |
| 10 | `EOD/stock` | `raw_stock_eod` |
| 11 | `EOD/supplydemand` | `raw_supplydemand_eod` |
| 12 | `EOD/warrant` | `raw_warrant_eod` |

## Current daily EOD DQ coverage

The current blocking EOD Data Quality gate validates:

```text
raw_stock_eod
grain = Ticker + Date
```

Required fields:

```text
Ticker
Date
Open
High
Low
Close
Volume
```

The other eleven EOD domains are still ingested every day, but they do **not**
currently have individual blocking per-table DQ gates in
`SyncWritePipelineService.run()`.

This is an explicit current-state boundary, not an indication that those sources
are skipped.

---

# 3. Trading Calendar refresh

Definition:

```text
src/DuckDB/sql/updateHoliday.sql
```

Order invariant:

```text
AmiBroker EOD
    ↓
raw_index_eod contains current VNINDEX date
    ↓
updateHoliday.sql
    ↓
dimCalendar current
    ↓
dated Data Quality
```

Do not move the calendar refresh after dated DQ.

A dated table can legitimately contain the new trading date before the previous
calendar snapshot knows that date. Refreshing `dimCalendar` first prevents false
errors such as:

```text
max_date      = 2026-09-07
expected_date = 2026-09-04
```

---

# 4. AmiBroker Intraday ingestion

`syncAmibroker_Intraday()` loads four configured domains.

| # | AmiBroker source | DuckDB target |
|---:|---|---|
| 1 | `Intraday/futures` | `raw_futures_intraday` |
| 2 | `Intraday/index` | `raw_index_intraday` |
| 3 | `Intraday/stock` | `raw_stock_intraday` |
| 4 | `Intraday/warrant` | `raw_warrant_intraday` |

Logical key:

```text
Ticker + Date + RawTime + TickSeq
```

Required daily DQ fields:

```text
Ticker
Date
DateTime
RawTime
TickSeq
Close
Volume
```

Intraday count thresholds are intentionally wider than EOD:

```text
max_row_change_pct    = 100%
max_symbol_change_pct = 25%
```

Intraday market activity is naturally more variable than one-row-per-symbol EOD
data.

All four Intraday tables have individual daily DQ gates.

---

# 5. Yahoo Finance EOD

Yahoo scope:

```text
DX-Y.NYB
BTC-USD
VND=X
GC=F
```

Target:

```text
raw_other_eod
```

Yahoo is a **mixed-calendar** source:

- `BTC-USD` trades seven days per week;
- USD index / FX / futures instruments do not share the same weekend calendar.

Therefore daily Yahoo DQ uses:

```text
check_count_anomalies = FALSE
```

This disables hard gating on:

- day-over-day row-count change;
- day-over-day symbol-count change;
- missing-symbol rate caused only by different calendars;
- row/symbol historical z-score severity.

It does **not** disable:

- freshness;
- duplicate `Ticker + Date`;
- required NULL checks;
- invalid date/numeric checks;
- OHLC integrity;
- negative price/volume checks where semantically applicable;
- audit persistence.

A normal transition from Sunday:

```text
BTC-USD only
```

to Monday:

```text
BTC-USD + DX-Y.NYB + VND=X + GC=F
```

must not fail merely because symbol count changes from 1 to 4.

---

# 6. Fundamental Analysis snapshot

Target:

```text
raw_stock_fa
grain / primary key = Ticker
```

FA is a **current snapshot**, not a daily append-only time series.

It uses reference/snapshot DQ, not dated row-count anomaly DQ.

Checks:

```text
table exists / non-empty
Ticker unique
required Ticker non-null
required Date non-null
MAX(Date) matches expected trading date
latest-date coverage recorded
audit persisted
```

Rows with older `Date` may coexist with newer rows because individual tickers are
updated in place.

Therefore this is valid in principle:

```text
AAA  2026-09-07
BBB  2026-09-07
CCC  2026-09-04
```

provided the snapshot itself is current and the key/required-field contract passes.

Do not compare the number of FA rows grouped by `Date` as if each date were a
complete historical snapshot.

---

# 7. Ticker Master

Target:

```text
raw_lstTicker
grain / key = Ticker
```

Ticker Master uses reference-data validation:

- non-empty;
- unique `Ticker`;
- required `Ticker`;
- required `status`;
- audit persistence.

It is not validated as a dated time series.

---

# 8. VNINDEX_NOT_VIN

Calculation:

```text
calculate_VNINDEX_NOT_VIN()
        ↓
cal_Indexes
```

Daily DQ is filtered to:

```text
INDEX_NAME = 'VNINDEX_NOT_VIN'
```

Logical key:

```text
INDEX_NAME + Date
```

Required fields:

```text
INDEX_NAME
Date
Close
```

---

# 9. Moving Average / Trend

Calculation:

```text
calc_fv_Trend.cal_Moving_Average()
        ↓
cal_Trends
```

Logical key:

```text
Ticker + Date
```

Required:

```text
Ticker
Date
Close
```

Optional rolling fields include:

```text
MA20
MA50
MA100
MA200
MA20_W
MA50_W
MA20_M
MA50_M
```

Optional MA columns can be NULL because long rolling windows legitimately require
warmup history. They are evaluated with the optional-null-rate contract rather
than the strict required-column NULL contract.

---

# 10. Technical Indicator Engine

Calculation:

```text
refresh_technical_indicators()
        ↓
cal_indicator_values
```

Logical key:

```text
Ticker + Date + ConfigId + ComponentCode
```

Required:

```text
Ticker
Date
ConfigId
ComponentCode
Value
```

## Indicator-specific DQ profile

`cal_indicator_values` mixes multiple indicators, configs, timeframes and
components. Total rows per date are therefore **not** a stable completeness
contract.

Daily Indicator DQ uses:

```text
check_count_anomalies = FALSE
```

It still checks:

- freshness;
- duplicate logical key;
- required NULLs;
- valid dates;
- audit persistence.

## Negative indicator values

A generic column named `Value` is **not** assumed to be non-negative.

Negative values are valid for many mathematical indicator outputs, including
examples such as:

```text
OBV
AD
MACD-family values
ROC / momentum values
divergence-like metrics
```

Core Data Validation only applies the non-negative rule to columns with explicit
non-negative semantics such as:

```text
Volume
TradingValue
trading_value
```

Do not reintroduce a generic `Value >= 0` rule.

---

# 11. SmartMoneyScore daily refresh

Before execution the daily pipeline ensures:

```text
src/DuckDB/sql/smart_money_v1_schema.sql
```

Then executes bounded incremental refresh:

```text
refresh_smart_money_score(
    from_last_day = days_diff
)
```

Persistence:

```text
cal_smart_money_factor_values
cal_smart_money_ticker_score
        ↓
vw_Ticker_SmartMoney
```

Daily score DQ key:

```text
ModelId + Ticker + Date
```

Required score fields:

```text
ModelId
Ticker
Date
SmartMoneyScore
ConfidenceScore
MarketState
FactorCoverage
DataQualityStatus
```

Database constraints and SmartMoney validation preserve the score-domain
contracts, including:

```text
SmartMoneyScore  0..100
ConfidenceScore  0..100
FactorCoverage   0..1
```

SmartMoney runs in the normal daily pipeline. The former
`SMART_MONEY_AUTO_RUN` gate is retired.

Detailed model runbook:

```text
docs/runbook/SmartMoneyScore_V1.md
```

---

# 12. Data Quality profiles by dataset

| Dataset / stage | Validation profile | Count anomaly gate | Important semantics |
|---|---|---:|---|
| `raw_stock_eod` | dated market data | ON | one EOD row per ticker/date |
| 4 Intraday tables | dated tick data | ON, wider thresholds | tick activity varies strongly |
| Yahoo `raw_other_eod` scope | mixed-calendar dated data | **OFF** | weekend calendars differ |
| `raw_stock_fa` | snapshot/reference + freshness | N/A | grain is Ticker, not Date |
| `raw_lstTicker` | reference | N/A | master data |
| `cal_Indexes` | dated calculation | ON | filtered to VNINDEX_NOT_VIN |
| `cal_Trends` | dated calculation | ON | MA fields can be optional NULL |
| `cal_indicator_values` | indicator/config-aware dated data | **OFF** | negative generic Value is valid |
| `cal_smart_money_ticker_score` | dated score persistence | ON | score constraints 0..100 |

A Data Quality profile must follow the table's **grain, lifecycle and field
semantics**. Do not apply one generic time-series rule to every dataset.

---

# 13. Transaction and rollback behavior

All stages before commit reuse the same DuckDB writer transaction.

```text
BEGIN
  ingestion
  DQ
  calculations
  DQ
  SmartMoney
  DQ
COMMIT
```

If a blocking validation fails:

```text
Data Quality = FAIL
        ↓
RuntimeError
        ↓
DuckDBUnitOfWork.__exit__
        ↓
ROLLBACK
```

This prevents partial daily states such as:

```text
EOD committed
but Indicator / SmartMoney failed
```

Warnings do not automatically block execution. A DQ profile explicitly decides
which conditions are warnings versus failures.

---

# 14. Runtime command

Normal daily execution:

```powershell
git pull
python run.py
```

`run.py` resolves `from_last_day` from the latest `raw_stock_eod` date and
passes the checkpoint to the canonical write service.

Do not manually duplicate the sequence in `run.py`. Change ordering and stage
ownership in:

```text
src/cherrystock/application/services/sync_write_pipeline.py
```

and update this runbook in the same change.

---

# 15. Current explicit gaps

The current daily pipeline intentionally documents the following gap:

```text
12 AmiBroker EOD tables are ingested
but only raw_stock_eod has an individual blocking daily EOD DQ gate.
```

If per-source EOD quality coverage becomes a requirement, add explicit DQ profiles
for the remaining eleven domains rather than assuming the stock EOD contract fits
all of them.

As-Traded market-limit ingestion is also not yet part of this daily flow. Until
that approved architecture is implemented and validated, SmartMoney keeps
point-in-time LimitUp evidence unavailable instead of deriving authoritative
history from adjusted prices.

---

# 16. Source of Truth

Runtime:

```text
run.py
src/cherrystock/application/services/sync_write_pipeline.py
src/cherrystock/config/settings.py
src/Ults/DataValidation.py
src/Ults/DataQualityOrchestration.py
```

Validation:

```text
tests/test_sync_write_pipeline_service.py
tests/test_data_quality_orchestration.py
```

Architecture:

```text
docs/architecture/Data_Architecture.md
```

This runbook is the canonical operational description of the daily sequence.
