CREATE OR REPLACE VIEW "CherryMon"."main"."vw_stock_fa_ticker" AS
SELECT
    fa.Ticker AS fa_Ticker,
    fa."Date/Time" AS fa_Date_Time,
    fa.Open AS fa_Open,
    fa.Close AS fa_Close,
    fa."Full Name" AS fa_Full_Name,
    fa.Market AS fa_Market,
    fa.Capital AS fa_Capital,
    fa.Sector AS fa_Sector,
    fa."ICB ID" AS fa_ICB_ID,
    fa.ICB AS fa_ICB,
    fa.Industry AS fa_Industry,
    fa."Shares Float" AS fa_Shares_Float,
    fa."Shares Outstanding" AS fa_Shares_Outstanding,
    fa.EPS AS fa_EPS,
    fa.PE AS fa_PE,
    fa."Book Value" AS fa_Book_Value,
    fa.ROA AS fa_ROA,
    fa.ROE AS fa_ROE,
    lt.Stock AS lt_Stock,
    lt.Ticker AS lt_Ticker,
    lt."Company Name" AS lt_Company_Name,
    lt.Industry AS lt_Industry,
    lt."Expected Price" AS lt_Expected_Price,
    lt.Watchlist AS lt_Watchlist,
    lt.EcoSystem AS lt_EcoSystem,
    eod.Date AS eod_Date,
    eod.Open AS eod_Open,
    eod.High AS eod_High,
    eod.Low AS eod_Low,
    eod.Close AS eod_Close,
    eod.Volume AS eod_Volume,
    eod.OpenInt AS eod_OpenInt
FROM "CherryMon"."main"."raw_stock_fa" AS fa
INNER JOIN "CherryMon"."main"."raw_lstTicker" AS lt
    ON fa.Ticker = lt.Ticker
INNER JOIN "CherryMon"."main"."raw_stock_eod" AS eod
    ON fa.Ticker = eod.Ticker;
