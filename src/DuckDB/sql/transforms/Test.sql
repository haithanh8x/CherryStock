
select * from "CherryMon"."main"."vw_Ticker_indicators";
select * from "CherryMon"."main"."vw_Ticker_SmartMoney" where date='2026-09-11' and ticker='MWG' order by date desc ;





select * from "CherryMon"."main"."vw_Ticker_SmartMoney" where date='2026-09-11' 
and MarketState = 'ACCUMULATION'
and AccumulationScore >= 65
and AccumulationMemoryScore >= 60
and RelativeStrengthScore >= 50
and DistributionScore < 50
and ConfidenceScore >= 70;


select * from "CherryMon"."main"."vw_Ticker_SmartMoney" where date='2026-09-11' 
and SupplyLockScore >= 70
and AccumulationMemoryScore >= 60;

select * from "CherryMon"."main"."vw_Ticker_SmartMoney" where date='2026-09-11' 
and FreshFlowScore >= 70
and RelativeLiquidityScore >= 70;

select * from "CherryMon"."main"."vw_Ticker_SmartMoney" where date='2026-09-11' ;


select * from "CherryMon"."main"."dim_smart_money_config";