

select * from "CherryMon"."main"."vw_Ticker_OHLC_D" where ticker='MWG' order by date desc;

select * from "CherryMon"."main"."vw_raw_stock_eod" where ticker='PNJ'  order by date desc;

select * from "CherryMon"."main"."vw_raw_stock_eod" where date>='2026-06-01';