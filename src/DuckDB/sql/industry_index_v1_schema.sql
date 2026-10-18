-- CherryStock industry indices. Additive schema; no mutation of source facts.
-- All prices are adjusted analytical prices in thousand VND / share.
-- Index close is a dimensionless level (base 1000), not a price in VND.

CREATE TABLE IF NOT EXISTS "CherryMon"."main"."cal_Industry_Index_D" (
    "Date" DATE NOT NULL,
    "IndustryCode" VARCHAR NOT NULL,
    "Industry" VARCHAR,
    "Index_Method" VARCHAR NOT NULL,
    "Close" DOUBLE NOT NULL,
    "Daily_Return" DOUBLE NOT NULL,
    "Pct_Change" DOUBLE NOT NULL,
    "Volume" BIGINT,
    "TradingValue" HUGEINT,
    "TradingValue_Known_Count" INTEGER NOT NULL,
    "TradingValue_Proxy_Count" INTEGER NOT NULL,
    "Ticker_Count" INTEGER NOT NULL,
    "Advancers" INTEGER NOT NULL,
    "Decliners" INTEGER NOT NULL,
    "Unchanged" INTEGER NOT NULL,
    "FloatMarketCap_ThousandVND" DOUBLE,
    "Max_Weight" DOUBLE NOT NULL,
    "Top3_Weight" DOUBLE NOT NULL,
    "Calculation_Mode" VARCHAR NOT NULL,
    "Snapshot_Date" DATE NOT NULL,
    "Calculated_At" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY ("Date", "IndustryCode", "Index_Method"),
    CHECK ("Index_Method" IN ('FFMC', 'EW')),
    CHECK ("Close" > 0)
);

CREATE TABLE IF NOT EXISTS "CherryMon"."main"."cal_Industry_Index_Weights" (
    "Date" DATE NOT NULL,
    "IndustryCode" VARCHAR NOT NULL,
    "Index_Method" VARCHAR NOT NULL,
    "Ticker" VARCHAR NOT NULL,
    "Close" DOUBLE NOT NULL,
    "Previous_Close" DOUBLE NOT NULL,
    "FloatShares" DOUBLE,
    "Weight" DOUBLE NOT NULL,
    "Return_Weight" DOUBLE NOT NULL,
    "Price_Return" DOUBLE NOT NULL,
    "Return_Contribution" DOUBLE NOT NULL,
    "Snapshot_Date" DATE NOT NULL,
    PRIMARY KEY ("Date", "IndustryCode", "Index_Method", "Ticker"),
    CHECK ("Index_Method" IN ('FFMC', 'EW')),
    CHECK ("Weight" >= 0 AND "Weight" <= 1.00000001),
    CHECK ("Return_Weight" >= 0 AND "Return_Weight" <= 1.00000001)
);

CREATE OR REPLACE VIEW "CherryMon"."main"."vw_Industry_Index_D" AS
SELECT
    "Date", "IndustryCode", "Industry", "Index_Method",
    "Close", "Daily_Return", "Pct_Change",
    "Volume", "TradingValue", "TradingValue_Known_Count",
    "TradingValue_Proxy_Count", "Ticker_Count",
    "Advancers", "Decliners", "Unchanged",
    "FloatMarketCap_ThousandVND", "Max_Weight", "Top3_Weight",
    "Calculation_Mode", "Snapshot_Date", "Calculated_At"
FROM "CherryMon"."main"."cal_Industry_Index_D";

-- Idempotent metadata comments; supported by DuckDB COMMENT ON.
COMMENT ON TABLE "CherryMon"."main"."cal_Industry_Index_D" IS 'Daily industry index series calculated from the latest active ticker universe and adjusted daily OHLC. Historical results are proxies, not point-in-time sector benchmarks. Grain: Date + IndustryCode + Index_Method.';
COMMENT ON COLUMN "CherryMon"."main"."cal_Industry_Index_D"."Date" IS 'Trading session date of the industry index.';
COMMENT ON COLUMN "CherryMon"."main"."cal_Industry_Index_D"."IndustryCode" IS 'Stable industry identifier from vw_Ticker_Active; grouping and primary-key component.';
COMMENT ON COLUMN "CherryMon"."main"."cal_Industry_Index_D"."Industry" IS 'Display name of the industry from the current active ticker universe.';
COMMENT ON COLUMN "CherryMon"."main"."cal_Industry_Index_D"."Index_Method" IS 'Weighting method: FFMC (free-float market capitalization) or EW (equal weight).';
COMMENT ON COLUMN "CherryMon"."main"."cal_Industry_Index_D"."Close" IS 'End-of-session industry index level in points, base 1000; not a stock price or currency amount.';
COMMENT ON COLUMN "CherryMon"."main"."cal_Industry_Index_D"."Daily_Return" IS 'Daily industry index return as a decimal fraction; 0.0125 means +1.25 percent.';
COMMENT ON COLUMN "CherryMon"."main"."cal_Industry_Index_D"."Pct_Change" IS 'Daily industry index percentage change; Daily_Return multiplied by 100.';
COMMENT ON COLUMN "CherryMon"."main"."cal_Industry_Index_D"."Volume" IS 'Sum of EOD traded share volume for eligible index constituents on this date, in shares.';
COMMENT ON COLUMN "CherryMon"."main"."cal_Industry_Index_D"."TradingValue" IS 'Sum of available constituent trading values in VND; may include EOD-derived proxy values. NULL if no value is available.';
COMMENT ON COLUMN "CherryMon"."main"."cal_Industry_Index_D"."TradingValue_Known_Count" IS 'Number of eligible constituents with non-NULL TradingValue.';
COMMENT ON COLUMN "CherryMon"."main"."cal_Industry_Index_D"."TradingValue_Proxy_Count" IS 'Number of eligible constituents whose TradingValue was estimated using the EOD typical-price proxy.';
COMMENT ON COLUMN "CherryMon"."main"."cal_Industry_Index_D"."Ticker_Count" IS 'Number of valid constituents participating in this industry and weighting method on this date.';
COMMENT ON COLUMN "CherryMon"."main"."cal_Industry_Index_D"."Advancers" IS 'Number of eligible constituents with positive daily adjusted-close price return.';
COMMENT ON COLUMN "CherryMon"."main"."cal_Industry_Index_D"."Decliners" IS 'Number of eligible constituents with negative daily adjusted-close price return.';
COMMENT ON COLUMN "CherryMon"."main"."cal_Industry_Index_D"."Unchanged" IS 'Number of eligible constituents with zero daily adjusted-close price return.';
COMMENT ON COLUMN "CherryMon"."main"."cal_Industry_Index_D"."FloatMarketCap_ThousandVND" IS 'Sum of adjusted Close times latest FreeFloat shares, in thousand VND; populated only for FFMC.';
COMMENT ON COLUMN "CherryMon"."main"."cal_Industry_Index_D"."Max_Weight" IS 'Largest end-of-day constituent weight in this industry/method, as a fraction from 0 to 1.';
COMMENT ON COLUMN "CherryMon"."main"."cal_Industry_Index_D"."Top3_Weight" IS 'Sum of the three largest end-of-day constituent weights in this industry/method, as a fraction from 0 to 1.';
COMMENT ON COLUMN "CherryMon"."main"."cal_Industry_Index_D"."Calculation_Mode" IS 'Calculation provenance. HISTORICAL_PROXY_LATEST_FLOAT means latest float shares and active membership were applied historically.';
COMMENT ON COLUMN "CherryMon"."main"."cal_Industry_Index_D"."Snapshot_Date" IS 'Date of the latest-free-float snapshot used to calculate or refresh this row.';
COMMENT ON COLUMN "CherryMon"."main"."cal_Industry_Index_D"."Calculated_At" IS 'Timestamp at which the calculated index row was persisted in DuckDB.';
