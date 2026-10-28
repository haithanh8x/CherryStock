-- Four market-cap group indices; latest membership snapshot, not point-in-time history.
CREATE TABLE IF NOT EXISTS "CherryMon"."main"."cal_MarketCap_Index_D" (
 "Date" DATE NOT NULL, "MarketCap_Group" VARCHAR NOT NULL,
 "Index_Method" VARCHAR NOT NULL, "Close" DOUBLE NOT NULL,
 "Daily_Return" DOUBLE NOT NULL, "Pct_Change" DOUBLE NOT NULL,
 "Ticker_Count" INTEGER NOT NULL, "Volume" BIGINT,
 "Calculation_Mode" VARCHAR NOT NULL, "Snapshot_Date" DATE NOT NULL,
 "Calculated_At" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
 PRIMARY KEY ("Date","MarketCap_Group","Index_Method"),
 CHECK ("Index_Method" IN ('EW','FFMC')), CHECK ("Close" > 0)
);
CREATE OR REPLACE VIEW "CherryMon"."main"."vw_MarketCap_Index_D" AS
SELECT * FROM "CherryMon"."main"."cal_MarketCap_Index_D";
COMMENT ON TABLE "CherryMon"."main"."cal_MarketCap_Index_D" IS 'Chỉ số vốn hóa theo nhóm hiện tại; lịch sử là proxy, không dùng cho backtest point-in-time.';
COMMENT ON COLUMN "CherryMon"."main"."cal_MarketCap_Index_D"."MarketCap_Group" IS 'Large Cap, Mid Cap, Small Cap hoặc Micro Cap từ vw_Ticker_Info.';
COMMENT ON COLUMN "CherryMon"."main"."cal_MarketCap_Index_D"."Close" IS 'Điểm chỉ số cơ sở 1000.';
