# CherryStock Data Architecture

## Purpose
High-level map of CherryStock data layers and data-contract ownership.

## Layer model

```text
External Sources
      ↓
Crawler / Import
      ↓
raw_*                source/raw datasets
      ↓
Validation
      ↓
cal_* / dim_*        calculated + master/config data
      ↓
vw_*                 consumer-oriented read contracts
      ↓
Chart / Screener / API / Analytics / ML

sys_*                operational audit / monitoring
```

## Core principles
- `raw_*` preserves normalized source facts as close to source semantics as practical.
- `dim_*` owns dimensions, metadata and executable configuration.
- `cal_*` is calculated/internal persistence and is not automatically the preferred public contract.
- `vw_*` should expose stable consumer-oriented contracts when a public read layer is needed.
- `sys_*` stores operational/audit history and must not replace validation of source data.
- Write workflows requiring atomicity should share one writer transaction.
- Data pipelines should be idempotent and explicit about logical keys.

## AmiBroker Intraday raw contract

FireAnt/AmiBroker Intraday data for the configured Vietnamese market sources is
ingested at **tick grain**, not EOD grain. The four configured source/target pairs are:

| Source folder | Target table |
| --- | --- |
| `Intraday/futures` | `main.raw_futures_intraday` |
| `Intraday/index` | `main.raw_index_intraday` |
| `Intraday/stock` | `main.raw_stock_intraday` |
| `Intraday/warrant` | `main.raw_warrant_intraday` |

Canonical normalized columns:

```text
Ticker
Date
DateTime
RawTime
TickSeq
Open
High
Low
Close
Volume
OpenInt
```

Logical uniqueness is `Ticker + Date + RawTime + TickSeq`.

- `RawTime` preserves the source's 32-bit time value unchanged.
- `TickSeq` preserves multiple ticks that share the same source timestamp.
- `DateTime` is the decoded local/exchange timestamp and MUST NOT be converted
  from UTC merely because the pandas value is timezone-naive.
- `OpenInt` remains a raw source field. FireAnt documents intraday OI for
  Vietnamese stocks/futures as transaction classification (1 active sell,
  2 active buy, 3 both); consumers must not assume futures open-interest semantics
  for every intraday dataset.
- Full/init reload resets all four intraday targets before loading source files.
- Incremental reload upserts recent ticks and must not collapse records to
  `Ticker + Date`.
- Intraday file discovery is recursive to support source installations that group
  symbols into nested folders.

The generated `docs/reference/DB_Metadata.md` must be refreshed after the local
database has been init-loaded with this schema; it is not hand-edited ahead of the
actual database state.


## Daily ticker OHLC + transaction-flow view

`main.vw_Ticker_OHLC_D` is the consumer-oriented daily contract that combines
canonical EOD OHLCV with transaction-flow metrics reconstructed from validated
AmiBroker Intraday ticks.

Logical grain:

```text
Ticker + Date
```

Ownership and lineage:

```text
raw_stock_eod
  └─ Open / High / Low / Close / Volume

raw_stock_intraday
  └─ TradingValue
  └─ BuyUp_Val / BuyUp_Vol
  └─ SellDown_Val / SellDown_Vol
  └─ ATO_Val / ATO_Vol
  └─ ATC_Val / ATC_Vol
        ↓
vw_Ticker_OHLC_D
```

Rules:

- EOD OHLCV remains owned by `raw_stock_eod`; the view does not reconstruct
  canonical daily prices from Intraday because historical corporate-action
  adjustment can make EOD and Intraday OHLC differ legitimately.
- `TradingValue = SUM(tick Close * tick Volume)` over all available Intraday
  transactions for the ticker/date.
- `OpenInt=1` contributes to `SellDown_*`.
- `OpenInt=2` contributes to `BuyUp_*`.
- `OpenInt=3` is only assigned to an auction bucket when the decoded local
  `DateTime` is inside the corresponding auction window:
  - ATO: 09:00:00 through 09:15:00;
  - ATC: 14:30:00 through 14:45:00.
- `OpenInt=3` outside those windows remains part of `TradingValue` but is not
  force-classified as ATO or ATC.
- `*_Val` uses source price units multiplied by source volume units. No
  undocumented price-scale multiplier is applied in the view.
- EOD dates with `Volume=0` and no Intraday rows expose zero flow/value because
  no transaction occurred. EOD dates with `Volume>0` but no Intraday coverage
  retain NULL flow/value fields so missing historical coverage is not disguised
  as zero.
- Full EOD/Intraday reload entry points drop and recreate the view around raw
  table rebuilds so dependency state remains deterministic.

Definition:
`src/DuckDB/sql/vw_Ticker_OHLC_D.sql`

Validation:
`src/DuckDB/sql/vw_Ticker_OHLC_D_preflight.sql`

## Database access policy
See [[../../.github/instructions/database.instructions|Database Instructions]].

## Metadata reference
See [[../../.github/agents/DB_Metadata|DB Metadata]].

## Related architecture
- [[Indicator_Engine|Indicator Engine]]
- [[../adr/ADR-001-duckdb-connection|ADR-001 DuckDB Connection]]
- [[../00_HOME|Knowledge Home]]