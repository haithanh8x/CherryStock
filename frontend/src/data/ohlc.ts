/** Client OHLC provider contract. GitHub Pages calls the public Worker, never Yahoo directly. */
export type OhlcProvider = "yahoo" | "fireant" | "duckdb" | "r2";
export type AssetKey = "vnindex" | "spx" | "ndx" | "btc" | "gold" | "oil" | "dxy" | "usdvnd";
export interface OhlcCandle { date:string; open:number; high:number; low:number; close:number; volume:number }
export interface OhlcHistory { schemaVersion:1; provider:OhlcProvider; symbol:string; asOf:string; candles:OhlcCandle[] }
export type IntermarketRow = {date:string} & Partial<Record<AssetKey, number>>;
export const ASSET_SYMBOLS: Record<AssetKey, string> = {
  vnindex:"^VNINDEX.VN", spx:"^GSPC", ndx:"^NDX", btc:"BTC-USD",
  gold:"GC=F", oil:"CL=F", dxy:"DX-Y.NYB", usdvnd:"VND=X",
};
const API_BASE = (import.meta.env.VITE_OHLC_API_BASE_URL || "https://cherrystock-ohlc.cherrystock-haithanh8x.workers.dev").replace(/\/$/,"");
export async function loadOhlc(provider:OhlcProvider,symbol:string,signal?:AbortSignal):Promise<OhlcHistory> {
  const query=new URLSearchParams({provider,symbol,range:"1y",interval:"1d"});
  const response=await fetch(`${API_BASE}/api/v1/ohlc?${query}`,{signal});
  if(!response.ok) throw new Error(`${symbol}: HTTP ${response.status}`);
  const payload:unknown=await response.json();
  if(!payload || typeof payload!=="object") throw new Error(`${symbol}: JSON lỗi`);
  const history=payload as OhlcHistory;
  if(history.schemaVersion!==1 || !Array.isArray(history.candles) || !history.candles.length ||
     history.candles.some(c=>!/^\d{4}-\d{2}-\d{2}$/.test(c.date) || !Number.isFinite(c.close) || c.close<=0))
    throw new Error(`${symbol}: dữ liệu OHLC không hợp lệ`);
  return history;
}
export async function loadIntermarket(signal?:AbortSignal):Promise<{rows:IntermarketRow[];failed:string[];asOf:string}> {
  const keys=Object.keys(ASSET_SYMBOLS) as AssetKey[];
  const results=await Promise.allSettled(keys.map(key=>loadOhlc("yahoo",ASSET_SYMBOLS[key],signal)));
  if(signal?.aborted) throw new DOMException("Aborted","AbortError");
  const dates=new Map<string,IntermarketRow>();
  const failed:string[]=[];
  results.forEach((result,i)=>{
    const key=keys[i];
    if(result.status==="rejected"){failed.push(ASSET_SYMBOLS[key]);return;}
    for(const candle of result.value.candles) {
      const row=dates.get(candle.date)||{date:candle.date};
      row[key]=candle.close;
      dates.set(candle.date,row);
    }
  });
  const rows=[...dates.values()].sort((a,b)=>a.date.localeCompare(b.date));
  if(!rows.length) throw new Error("Yahoo Finance không trả dữ liệu hợp lệ cho 8 tài sản.");
  return {rows,failed,asOf:rows[rows.length-1].date};
}
