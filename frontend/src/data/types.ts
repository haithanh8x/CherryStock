/** Public, chart-ready snapshot contract. Monetary values are in VND billions. */
export interface IndexQuote {
  symbol: string;
  label: string;
  value: number;
  change: number;
  changePct: number;
  history: number[];
}
export interface MarketSummary {
  turnoverBn: number;
  turnoverVs20Pct: number;
  advancers: number;
  decliners: number;
  unchanged: number;
  foreignNetBn: number;
  proprietaryNetBn: number;
}
export interface IntermarketPoint {
  date: string;
  vnindex: number;
  spx: number;
  ndx: number;
  btc: number;
  gold: number;
  oil: number;
  dxy: number;
  usdvnd: number;
}
export interface BreadthPoint {
  date: string;
  ma20: number;
  ma50: number;
  ma100: number;
  ma200: number;
}
export interface IndustryPerformance {
  name: string;
  changePct: number;
  turnoverBn: number;
  advancing: number;
  declining: number;
}
export interface InvestorFlowPoint {
  date: string;
  institutional: number;
  individual: number;
  foreign: number;
  proprietary: number;
}
export interface WatchlistQuote {
  symbol: string;
  price: number;
  changePct: number;
  volume: string;
}
export interface MarketOverviewSnapshot {
  schemaVersion: 1;
  asOf: string;
  indices: IndexQuote[];
  summary: MarketSummary;
  intermarket: IntermarketPoint[];
  breadth: BreadthPoint[];
  industries: IndustryPerformance[];
  flows: InvestorFlowPoint[];
  watchlist: WatchlistQuote[];
}
export type MarketSource = "mock" | "r2";
export type Timeframe = "daily" | "weekly" | "monthly";
