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

## Enriched stock EOD market-limit view

`main.vw_raw_stock_eod` is the consumer-oriented stock EOD contract for standard-session
reference prices, price bands and daily limit-up/down state.

Logical grain:

```text
Ticker + Date
```

Primary lineage:

```text
raw_stock_eod
  └─ OHLCV / OpenInt
  └─ previous Close for listed-market standard ReferencePrice

raw_stock_fa
  └─ current Market snapshot (HOSE / HNX / UPCOM)

raw_stock_intraday
  └─ UPCOM previous eligible-session VWAP proxy
        ↓
vw_raw_stock_eod
```

Public enrichment fields:

```text
Market
Market_Source
Market_IsPointInTime
ReferencePrice
ReferencePrice_Source
ReferencePrice_IsProxy
PriceBandRate
PriceBandRuleQuality
CeilingPrice
FloorPrice
LimitUp
LimitUpStreak
LimitDown
LimitDownStreak
```

Price units remain the same as `raw_stock_eod`: **thousand VND/share**.

Standard-session rules implemented from the current 2026 VNX/HOSE trading rules:

| Market | ReferencePrice | Normal band | Quote unit |
| --- | --- | ---: | --- |
| HOSE | nearest previous closing price | +/-7% | 10 / 50 / 100 VND by price level |
| HNX | nearest previous closing price | +/-10% | 100 VND |
| UPCOM | nearest previous weighted-average eligible matched price | +/-15% | 100 VND |

Price-band calculation:

```text
CeilingRaw = ReferencePrice * (1 + band)
FloorRaw   = ReferencePrice * (1 - band)

CeilingPrice = round DOWN to quote unit
FloorPrice   = round UP to quote unit
```

When rounding collapses a limit to ReferencePrice, the exchange one-quote-unit
adjustment is applied. If ReferencePrice equals the minimum quote unit, FloorPrice
stays at ReferencePrice.

UPCOM ReferencePrice follows the exchange rule conceptually: weighted-average price
of regular-lot continuous-matching trades from the nearest previous eligible trading
session. The current raw Intraday contract does not expose an explicit
regular-lot/negotiated flag, so CherryStock uses matched ticks with
`OpenInt IN (1,2,3)`, `Volume >= 100`, and `Volume % 100 = 0` as a best-effort
regular-lot-compatible subset. This source is explicitly marked
`UPCOM_INTRADAY_LOT100_VWAP_PROXY`.

`LimitUp` / `LimitDown` mean the **daily Close** equals the derived CeilingPrice
or FloorPrice. Streak fields count consecutive available EOD observations with the
same TRUE state.

Quality boundary:

- `raw_stock_fa.Market` is a current snapshot, not point-in-time exchange history;
- historical `raw_stock_eod` can be corporate-action adjusted;
- first-trading-day, >=25-session trading-resumption and ex-right/corporate-action
  special bands are not inferred without event data;
- therefore `PriceBandRuleQuality='STANDARD_RULE_DERIVED'` is not an authoritative
  exchange-published daily limit contract.

Current rule references:
- VNX Decision 22/QD-HDTV dated 16/03/2026 — listed securities;
- VNX Decision 23/QD-HDTV dated 18/03/2026 — UPCOM;
- HOSE 2026 trading guide — ordinary +/-7% band and HOSE quote units.

Definition:
`src/DuckDB/sql/vw_raw_stock_eod.sql`

Validation:
`src/DuckDB/sql/vw_raw_stock_eod_preflight.sql`

Runbook:
`docs/runbook/vw_raw_stock_eod.md`

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
  └─ TradingValue fallback proxy when Intraday is unavailable

raw_stock_intraday
  └─ TradingValue primary source
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
- AmiBroker stock prices are stored in thousand VND/share. Every `*_Val` field is
  normalized to **VND** and cast to `BIGINT`, so consumer output has no decimal places.
- `TradingValue` uses the following precedence:
  1. If Intraday exists for `Ticker + Date`, use
     `ROUND(SUM(tick Close * tick Volume * 1000))`.
  2. If Intraday is unavailable and EOD `Volume > 0`, use the proxy
     `ROUND(((High + Low + Close) / 3) * Volume * 1000)`.
  3. If EOD `Volume = 0`, return `0`.
  4. If EOD `Volume > 0` but `High/Low/Close` is incomplete, return NULL.
- `TradingValue_Source` identifies provenance:
  - `INTRADAY_TICK`;
  - `EOD_TYPICAL_PRICE_PROXY`;
  - `NO_TRADE`;
  - `MISSING_INPUT`.
- `TradingValue_IsProxy` is `TRUE` only for `EOD_TYPICAL_PRICE_PROXY`, `FALSE`
  for `INTRADAY_TICK`/`NO_TRADE`, and NULL for `MISSING_INPUT`.
- BuyUp/SellDown/ATO/ATC require Intraday evidence. On positive-volume EOD dates
  without Intraday coverage these flow fields remain NULL; the system must not
  manufacture directional flow from OHLCV.
- `OpenInt=1` contributes to `SellDown_*`.
- `OpenInt=2` contributes to `BuyUp_*`.
- `OpenInt=3` is only assigned to an auction bucket when the decoded local
  `DateTime` is inside the current validated source windows:
  - ATO: 09:00:00 through 09:20:00;
  - ATC: 14:30:00 through 14:50:00.
- `OpenInt=3` outside those windows remains part of tick-based `TradingValue` but
  is not force-classified as ATO or ATC.
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