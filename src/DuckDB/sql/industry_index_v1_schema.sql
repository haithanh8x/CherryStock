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
