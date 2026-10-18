import type { MarketOverviewSnapshot } from "./types";

/** Deterministic DEMO fixture. These are synthetic numbers, never live trading data. */
function tradingDays(count: number): string[] {
  const dates: string[] = [];
  const day = new Date("2026-10-16T00:00:00Z");
  while (dates.length < count) {
    if (day.getUTCDay() !== 0 && day.getUTCDay() !== 6) dates.unshift(day.toISOString().slice(0, 10));
    day.setUTCDate(day.getUTCDate() - 1);
  }
  return dates;
}
const days = tradingDays(90);
const round = (v: number, d = 2) => Number(v.toFixed(d));
const wave = (i: number, pace: number, phase = 0) => Math.sin(i / pace + phase);
const points = (start: number, slope: number, amp: number, phase = 0) =>
  days.map((_, i) => round(start + i * slope + wave(i, 5.3, phase) * amp + wave(i, 12.7, phase) * amp * 0.6));
const indexPrices = points(1292, 3.32, 29);
const vn30 = points(1374, 3.77, 34, 0.6);
const hnx = points(228, 0.22, 4, 1.1);
const upcom = points(91, 0.055, 2, 1.8);
const series = {
  vnindex: indexPrices,
  spx: points(5400, 5.5, 100, 0.8),
  ndx: points(19000, 35, 460, 0.4),
  btc: points(62000, 150, 3800, 1.2),
  gold: points(2600, 9, 85, 2.2),
  oil: points(78, -0.05, 5.2, 1.7),
  dxy: points(105, -0.045, 1.2, 0.5),
  usdvnd: points(25060, 2.2, 58, 0.9),
};
const q = (symbol: string, label: string, history: number[], changePct: number) => {
  const value = history[history.length - 1];
  const change = round(value - value / (1 + changePct / 100));
  return { symbol, label, value, change, changePct, history: history.slice(-30) };
};
export const mockOverview: MarketOverviewSnapshot = {
  schemaVersion: 1,
  asOf: "2026-10-16",
  indices: [
    q("VNINDEX", "VN-INDEX", indexPrices, 1.18),
    q("VN30", "VN30", vn30, 1.42),
    q("HNXINDEX", "HNX-INDEX", hnx, -0.36),
    q("UPCOMINDEX", "UPCOM", upcom, 0.24),
  ],
  summary: {
    turnoverBn: 18640,
    turnoverVs20Pct: 12.4,
    advancers: 268,
    decliners: 151,
    unchanged: 71,
    foreignNetBn: -642,
    proprietaryNetBn: -108,
  },
  intermarket: days.map((date, i) => ({
    date,
    vnindex: series.vnindex[i], spx: series.spx[i], ndx: series.ndx[i],
    btc: series.btc[i], gold: series.gold[i], oil: series.oil[i],
    dxy: series.dxy[i], usdvnd: series.usdvnd[i],
  })),
  breadth: days.map((date, i) => ({
    date,
    ma20: round(Math.min(95, Math.max(19, 60 + wave(i, 5.6) * 16 + wave(i, 16, 0.5) * 12)), 1),
    ma50: round(Math.min(95, Math.max(19, 52 + i * .10 + wave(i, 8.3, 1) * 13)), 1),
    ma100: round(Math.min(90, Math.max(15, 44 + i * .12 + wave(i, 12, .7) * 9)), 1),
    ma200: round(Math.min(85, Math.max(10, 39 + i * .10 + wave(i, 18, 1.5) * 8)), 1),
  })),
  industries: [
    {name:"Công nghệ",changePct:3.42,turnoverBn:1190,advancing:19,declining:4},
    {name:"Chứng khoán",changePct:2.81,turnoverBn:2430,advancing:25,declining:7},
    {name:"Thép",changePct:1.93,turnoverBn:1020,advancing:14,declining:5},
    {name:"Ngân hàng",changePct:1.24,turnoverBn:5730,advancing:18,declining:9},
    {name:"Bán lẻ",changePct:0.86,turnoverBn:930,advancing:10,declining:7},
    {name:"Bất động sản",changePct:-0.43,turnoverBn:3320,advancing:26,declining:36},
    {name:"Dầu khí",changePct:-0.88,turnoverBn:780,advancing:6,declining:15},
    {name:"Hóa chất",changePct:-1.34,turnoverBn:540,advancing:5,declining:17},
  ],
  flows: days.map((date, i) => ({
    date,
    institutional: Math.round(230 * wave(i, 4.5, 1) + 75),
    individual: Math.round(250 * wave(i, 3.8, 2) + 130),
    foreign: Math.round(320 * wave(i, 6.5, .4) - 105),
    proprietary: Math.round(145 * wave(i, 5, 2.6) - 25),
  })),
  watchlist: [
    {symbol:"FPT",price:129.5,changePct:2.45,volume:"8.3M"},
    {symbol:"MWG",price:82.1,changePct:1.83,volume:"13.7M"},
    {symbol:"HPG",price:28.65,changePct:-0.52,volume:"26.1M"},
    {symbol:"VCB",price:67.2,changePct:0.75,volume:"4.9M"},
    {symbol:"SSI",price:35.8,changePct:3.16,volume:"19.4M"},
  ],
};
