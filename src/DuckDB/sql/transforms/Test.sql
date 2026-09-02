select Industry, sum(Capital)/sum("Shares Outstanding"*EPS) from "CherryMon"."main"."vw_Ticker" 
where EPS>=0
group by Industry;

select sum(Capital)/sum("Shares Outstanding"*EPS) from "CherryMon"."main"."vw_Ticker" 
where EPS>=0;

select sum(Capital)/sum("Shares Outstanding"*EPS) from "CherryMon"."main"."vw_Ticker" 
where EPS>=0 and Industry<>'Vingroup' and status='Y';

select * from "CherryMon"."main"."raw_stock_eod" where ticker='MWG' order by date desc;

select * from "CherryMon"."main"."vw_Ticker" where industry='Bán lẻ' and status='Y';


select IndustryCode, Industry, sum(Capital) Capital from "CherryMon"."main"."vw_Ticker" 
where Status='Y'
group by IndustryCode, Industry;

SELECT max("Date/Time") FROM "CherryMon"."main"."raw_stock_fa";

select Ticker, min("Date"), max("Date") from "CherryMon"."main"."raw_commodity_eod" where Ticker='^GCZ' group by Ticker;

select * from "CherryMon"."main"."raw_other_eod" where Ticker='^GCZ';


select * from "CherryMon"."main"."cal_Trends" where Ticker='MWG' order by Date desc;

select * from "CherryMon"."main"."dim_indicator";
select * from "CherryMon"."main"."dim_indicator_component";
select * from "CherryMon"."main"."dim_indicator_config";
select * from "CherryMon"."main"."vw_Ticker_indicators" where Ticker='MWG' and date='2026-08-28';
