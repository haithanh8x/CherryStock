# RS Ladder V1 — Local Agent Cross-check & MCP Test Guide

> Requested logical name: test_R/S.md. Because "/" is a path separator on Windows/Git, the repository-safe filename is tests/test_R_S.md.

## 1. Objective

This guide is the acceptance-test handoff for RS Ladder V1.

The local agent must cross-check three layers:

1. Domain logic in src/calcEngine/levelLadder.py.
2. Public CherryMon data contracts through MCP cherrymon-duckdb.
3. NiceGUI rendering in the R/S tab of src/webapp/NiceGUI_chart.py.

V1 source scope is intentionally limited to:

- MA20_D, MA50_D, MA100_D, MA200_D
- MA20_W, MA50_W, MA100_W, MA200_W
- MA20_M, MA50_M, MA100_M, MA200_M

The runtime MUST identify MA length from vw_Indicator_config.Parameters. Do not infer parameters by parsing ConfigCode.

## 2. Mandatory MCP

Use the local CherryMon DuckDB MCP server registered as:

cherrymon-duckdb

Do not replace the MCP data checks below with ad-hoc Python DuckDB queries.

Server command, if it is not running:

    C:/Program1/Python/Python313/python.exe src/mcp_server/duckdb_mcp.py

Relevant tools:

- list_tables()
- describe_table(table_name)
- query(sql, max_rows=100)
- table_stats(table_name)

All checks in this guide are read-only. Do not call execute().

## 3. Pre-check public contracts

### 3.1 List objects

Call list_tables().

Required objects:

- main.raw_stock_eod
- main.vw_Indicator_config
- main.vw_Ticker_indicators

If either public view is missing, mark:

DATA PRECONDITION: FAIL

Do not silently fall back to cal_indicator_values or cal_Trends.

### 3.2 Describe source objects

Call:

- describe_table("raw_stock_eod")
- describe_table("vw_Indicator_config")
- describe_table("vw_Ticker_indicators")

Required fields:

raw_stock_eod:
- Ticker
- Date
- High
- Low
- Close

vw_Ticker_indicators:
- Ticker
- Date
- ConfigId
- ComponentCode
- Value

vw_Indicator_config:
- ConfigId
- ConfigCode
- IndicatorCode
- Timeframe
- Parameters
- ConfigIsEnabled
- IndicatorIsActive
- ComponentCode
- ComponentIsActive

The production implementation validates the same contract at runtime.

## 4. Resolve the test snapshot

Use MWG as the first smoke-test ticker.

Run with MCP query():

    SELECT
        "Ticker",
        "Date",
        "Close"
    FROM "CherryMon"."main"."raw_stock_eod"
    WHERE "Ticker" = 'MWG'
      AND "Close" IS NOT NULL
    ORDER BY "Date" DESC
    LIMIT 1;

Record:

- Ticker
- AS_OF_DATE
- Current Close

This row is the expected CurrentPrice used for the default UI request when as_of_date is empty.

## 5. Validate V1 MA configuration

Run:

    SELECT
        "ConfigId",
        "ConfigCode",
        "IndicatorCode",
        "Timeframe",
        "Parameters",
        "ComponentCode",
        "ConfigIsEnabled",
        "IndicatorIsActive",
        "ComponentIsActive"
    FROM "CherryMon"."main"."vw_Indicator_config"
    WHERE "IndicatorCode" = 'MA'
      AND "Timeframe" IN ('D', 'W', 'M')
      AND "ComponentCode" = 'VALUE'
      AND "ConfigIsEnabled" = TRUE
      AND "IndicatorIsActive" = TRUE
      AND COALESCE("ComponentIsActive", TRUE) = TRUE
    ORDER BY "Timeframe", "ConfigId";

For every row, parse Parameters as JSON and inspect Parameters.length.

Expected V1 family:

| length | D | W | M |
| ---: | :---: | :---: | :---: |
| 20 | PASS | PASS | PASS |
| 50 | PASS | PASS | PASS |
| 100 | PASS | PASS | PASS |
| 200 | PASS | PASS | PASS |

Expected target count: 12 active configs/components.

If the database intentionally has additional MA lengths, that is acceptable. RS Ladder V1 must ignore them based on Parameters.length.

If one of the required 12 is missing, report DATA PRECONDITION: FAIL rather than modifying the database during this test.

## 6. Cross-check latest MA values

Replace <AS_OF_DATE> with the date from section 4.

Run:

    WITH ranked AS (
        SELECT
            val."Ticker",
            val."Date",
            val."ConfigId",
            val."ComponentCode",
            val."Value",
            cfg."ConfigCode",
            cfg."IndicatorCode",
            cfg."Timeframe",
            cfg."Parameters",
            ROW_NUMBER() OVER (
                PARTITION BY val."ConfigId", val."ComponentCode"
                ORDER BY val."Date" DESC
            ) AS rn
        FROM "CherryMon"."main"."vw_Ticker_indicators" val
        INNER JOIN "CherryMon"."main"."vw_Indicator_config" cfg
            ON cfg."ConfigId" = val."ConfigId"
           AND cfg."ComponentCode" = val."ComponentCode"
        WHERE val."Ticker" = 'MWG'
          AND val."Date" <= DATE '<AS_OF_DATE>'
          AND cfg."IndicatorCode" = 'MA'
          AND cfg."Timeframe" IN ('D', 'W', 'M')
          AND cfg."ConfigIsEnabled" = TRUE
          AND cfg."IndicatorIsActive" = TRUE
          AND COALESCE(cfg."ComponentIsActive", TRUE) = TRUE
          AND val."ComponentCode" = 'VALUE'
          AND val."Value" IS NOT NULL
    )
    SELECT
        "Ticker",
        "Date",
        "ConfigId",
        "ComponentCode",
        "Value",
        "ConfigCode",
        "Timeframe",
        "Parameters"
    FROM ranked
    WHERE rn = 1
    ORDER BY "Timeframe", "ConfigId";

Agent checks:

- every returned Value is numeric and > 0;
- Date <= AS_OF_DATE;
- Parameters.length is one of 20, 50, 100, 200 for V1 rows;
- latest row is used independently per ConfigId + ComponentCode;
- no ConfigCode parsing is needed to determine length.

## 7. Run automated domain tests

From repository root:

    python -m pytest tests/test_rs_ladder.py -v

Expected:

- proximity rank is independent from strength;
- nearby source levels cluster;
- empty candidates return an empty ladder safely;
- current/neutral zone is excluded from S/R rank;
- invalid clustering threshold raises;
- repeated identical input is deterministic.

All tests must PASS before continuing to UI smoke test.

## 8. Run production smoke calculation

From repository root:

    python -c "from src.calcEngine.levelLadder import build_level_ladder; r=build_level_ladder('MWG'); print(r)"

Record:

- ticker
- as_of_date
- current_price
- R1/R2/R3 if available
- S1/S2/S3 if available
- upside_to_r1_pct
- downside_to_s1_pct
- risk_reward_ratio

Cross-check these against the MCP rows from sections 4 and 6.

## 9. Ranking invariants

For result R/S rows:

Support:
- every S level must be below current price;
- S1 is the highest support price below current price;
- S2 follows below S1;
- distance_pct < 0.

Resistance:
- every R level must be above current price;
- R1 is the lowest resistance price above current price;
- R2 follows above R1;
- distance_pct > 0.

Important:

S1/R1 means NEAREST, not STRONGEST.

A farther S2/R2 is allowed to have a higher strength_score.

## 10. Cluster validation

V1 default:

cluster_threshold_pct = 0.01

If two normalized MA levels are within the deterministic cluster threshold, they may form one LevelZone.

For each RankedLevel validate:

- price_low <= price <= price_high;
- source_count equals number of source entries;
- each source retains source_code/timeframe/config metadata;
- representative price remains inside the zone.

Re-run with another threshold, for example:

    python -c "from src.calcEngine.levelLadder import build_level_ladder; print(build_level_ladder('MWG', cluster_threshold_pct=0.005))"

Smaller threshold should never merge more zones than a larger threshold for the same prepared inputs.

## 11. Strength V1 cross-check

Default model:

StrengthScore =
    35% Source Confluence
  + 25% Timeframe Confluence
  + 25% Historical Touches
  + 15% Recency

Timeframe importance:

- D = 1.0
- W = 1.5
- M = 2.0

MA source weighting used for zone representative weighting:

- MA20 = 0.80
- MA50 = 1.00
- MA100 = 1.15
- MA200 = 1.30

Touch model:

- price history: latest 252 observations at/before as_of_date;
- tolerance: 0.3%;
- target saturation: 4 touches.

Recency horizon:

- 180 days.

For every ranked level:

0 <= strength_score <= 100

Do not reorder S/R rank by strength.

## 12. NiceGUI R/S tab smoke test

Start the app:

    python src/webapp/NiceGUI_chart.py

Open:

    http://localhost:8081

Select tab:

R/S

Default smoke:

- Ticker = MWG
- As of date = blank
- Cluster = 1.0%
- click Refresh

Expected UI:

- Current Price card matches MCP latest Close.
- R1 card matches nearest resistance from production result.
- S1 card matches nearest support from production result.
- R:R matches upside_to_r1_pct / downside_to_s1_pct when both exist.
- Ladder chart preserves actual numeric price distance on Y axis.
- Current price is visually distinct from S/R.
- table lists rank, type, price/zone, distance, strength, timeframe and sources.

Historical test:

- enter a valid prior trading date;
- Refresh;
- current price must resolve to latest raw_stock_eod row at or before that date;
- no indicator value after that date may be used.

Invalid ticker test:

- enter a ticker with no source data;
- UI must show an explicit error notification;
- previous chart/table must be cleared;
- app must not crash.

## 13. Empty / partial data behavior

If price exists but no eligible MA candidates:

- domain returns empty support_levels/resistance_levels;
- nearest_support/resistance are None;
- R:R is None;
- UI shows a clear empty-state chart;
- no fabricated MA or cal_Trends fallback is allowed.

If required public-view columns are missing:

- production must raise RuntimeError with missing columns;
- classify as PUBLIC CONTRACT FAILURE.

## 14. Cross-check report template

Use this exact report structure:

    RS LADDER V1 CROSS-CHECK

    Ticker: MWG
    As-of date: <date>

    MCP PRECHECK
    raw_stock_eod: PASS/FAIL
    vw_Indicator_config: PASS/FAIL
    vw_Ticker_indicators: PASS/FAIL

    V1 CONFIG FAMILY
    MA20 D/W/M: PASS/FAIL
    MA50 D/W/M: PASS/FAIL
    MA100 D/W/M: PASS/FAIL
    MA200 D/W/M: PASS/FAIL

    DOMAIN TESTS
    pytest: PASS/FAIL
    deterministic: PASS/FAIL

    DATA CROSS-CHECK
    current price: PASS/FAIL
    candidate values: PASS/FAIL
    S1 nearest: PASS/FAIL
    R1 nearest: PASS/FAIL
    distance signs: PASS/FAIL
    strength range: PASS/FAIL

    UI
    R/S tab loads: PASS/FAIL
    refresh: PASS/FAIL
    historical as-of: PASS/FAIL
    invalid ticker: PASS/FAIL
    empty state: PASS/FAIL

    RESULT: PASS / FAIL
    Notes: <details>
