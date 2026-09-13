from __future__ import annotations


SMART_MONEY_VIEW = '"CherryMon"."main"."vw_Ticker_SmartMoney"'
MARKET_DATA_VIEW = '"CherryMon"."main"."vw_Ticker_OHLC_D"'
INDICATOR_VALUE_VIEW = '"CherryMon"."main"."vw_Ticker_indicators"'
INDICATOR_CONFIG_VIEW = '"CherryMon"."main"."vw_Indicator_config"'
MODEL_CODE = "SMART_MONEY_V1"
MA200_CONFIG_CODE = "MA200_D"


def latest_smart_money_snapshot_sql() -> str:
    """Return the canonical latest SmartMoney UI snapshot query.

    Close comes from the public daily OHLC contract. MA200 comes from the
    long-format Indicator Engine public views, resolved by ConfigCode rather
    than by a hard-coded ConfigId.
    """
    return f"""
        WITH latest AS (
            SELECT MAX(Date) AS Date
            FROM {SMART_MONEY_VIEW}
            WHERE ModelCode = ?
        ),
        ma200 AS (
            SELECT
                iv.Ticker,
                iv.Date,
                iv.Value AS MA200
            FROM {INDICATOR_VALUE_VIEW} AS iv
            INNER JOIN {INDICATOR_CONFIG_VIEW} AS cfg
                ON cfg.ConfigId = iv.ConfigId
               AND cfg.ComponentCode = iv.ComponentCode
            INNER JOIN latest AS d
                ON d.Date = iv.Date
            WHERE cfg.ConfigCode = '{MA200_CONFIG_CODE}'
              AND cfg.ConfigIsEnabled = TRUE
              AND cfg.IndicatorIsActive = TRUE
              AND cfg.ComponentIsActive = TRUE
              AND iv.ComponentCode = 'VALUE'
        )
        SELECT
            v.Ticker,
            v.Date,
            v.ModelCode,
            v.ModelVersion,
            v.SmartMoneyScore,
            v.ConfidenceScore,
            v.MarketState,
            v.DataQualityStatus,
            v.TradeAction,
            v.TradeActionConfidenceScore,
            o.Close,
            m.MA200
        FROM {SMART_MONEY_VIEW} AS v
        INNER JOIN latest AS d
            ON d.Date = v.Date
        LEFT JOIN {MARKET_DATA_VIEW} AS o
            ON o.Ticker = v.Ticker
           AND o.Date = v.Date
        LEFT JOIN ma200 AS m
            ON m.Ticker = v.Ticker
           AND m.Date = v.Date
        WHERE v.ModelCode = ?
        ORDER BY v.MarketState, v.TradeActionConfidenceScore DESC, v.Ticker
    """
