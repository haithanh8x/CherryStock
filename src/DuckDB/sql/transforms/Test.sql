

select * from "CherryMon"."main"."vw_Ticker_OHLC_D" where ticker='MWG' order by date desc;

select * from "CherryMon"."main"."vw_raw_stock_eod" where ticker='PNJ'  order by date desc;

select * from "CherryMon"."main"."vw_raw_stock_eod" where date>='2026-06-01';

select * from "CherryMon"."main"."dim_indicator";

select * from "CherryMon"."main"."dim_indicator_component";
select * from "CherryMon"."main"."dim_indicator_config";