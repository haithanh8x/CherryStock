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
  let response:Response;
  try { response=await fetch(`${API_BASE}/api/v1/ohlc?${query}`,{signal}); }
  catch(err) {
    if(signal?.aborted) throw err;
    throw new Error(`${symbol}: không kết nối Cloudflare Worker (network/CORS)`);
  }
  if(!response.ok) {
    let details="";
    try {
      const e=await response.json() as {error?:string;upstreamStatus?:number;detail?:string};
      details=[e.error,e.upstreamStatus && `Yahoo HTTP ${e.upstreamStatus}`,e.detail].filter(Boolean).join(" · ");
    }catch{/* HTML or empty response */}
    throw new Error(`${symbol}: API HTTP ${response.status}${details?" — "+details:""}`);
  }
  const payload:unknown=await response.json();
  if(!payload || typeof payload!=="object") throw new Error(`${symbol}: JSON lỗi`);
  const history=payload as OhlcHistory;
  if(history.schemaVersion!==1 || history.symbol!==symbol ||
     !Array.isArray(history.candles) || history.candles.length<2 ||
     history.candles.some(c=>!/^\d{4}-\d{2}-\d{2}$/.test(c.date) || !Number.isFinite(c.close) || c.close<=0))
    throw new Error(`${symbol}: dữ liệu OHLC không hợp lệ`);
  return history;
}
interface YahooSnapshot {
  schemaVersion:1;
  provider:"yahoo";
  generatedAt:string;
  assets: Partial<Record<AssetKey,{symbol:string;asOf:string;candles:OhlcCandle[]}>>;
}
export interface IntermarketResult {
  rows:IntermarketRow[];
  failed:string[];
  asOf:string;
  source:string;
  diagnostics:string[];
}
async function loadBackup(signal?:AbortSignal):Promise<YahooSnapshot> {
  const response=await fetch(`${import.meta.env.BASE_URL}data/intermarket-1y.json`,{signal,cache:"no-store"});
  if(!response.ok) throw new Error(`Yahoo snapshot chưa xuất bản (HTTP ${response.status})`);
  const data=await response.json() as YahooSnapshot;
  if(data.schemaVersion!==1 || data.provider!=="yahoo" || !data.assets) throw new Error("Yahoo snapshot sai schema");
  return data;
}

export async function loadIntermarket(signal?:AbortSignal):Promise<IntermarketResult> {
  const keys=Object.keys(ASSET_SYMBOLS) as AssetKey[];
  const results=await Promise.allSettled(keys.map(key=>loadOhlc("yahoo",ASSET_SYMBOLS[key],signal)));
  if(signal?.aborted) throw new DOMException("Aborted","AbortError");
  const histories=new Map<AssetKey,OhlcCandle[]>();
  const diagnostics:string[]=[];
  results.forEach((r,i)=>{
    if(r.status==="fulfilled") histories.set(keys[i],r.value.candles);
    else diagnostics.push(r.reason instanceof Error?r.reason.message:String(r.reason));
  });
  let backupCount=0;
  if(histories.size<keys.length) {
    try {
      const backup=await loadBackup(signal);
      for(const key of keys) {
        if(histories.has(key)) continue;
        const asset=backup.assets[key];
        if(!asset || asset.symbol!==ASSET_SYMBOLS[key] || !Array.isArray(asset.candles) || asset.candles.length<2) continue;
        if(asset.candles.some(c=>!/^\d{4}-\d{2}-\d{2}$/.test(c.date)||!Number.isFinite(c.close)||c.close<=0)) continue;
        histories.set(key,asset.candles);
        backupCount++;
      }
      if(backupCount) diagnostics.push(`Dự phòng Yahoo snapshot: ${backupCount} mã (xuất bản ${backup.generatedAt})`);
    } catch(e) {
      diagnostics.push("Snapshot: "+(e instanceof Error?e.message:String(e)));
    }
  }
  const dates=new Map<string,IntermarketRow>();
  for(const [key,candles] of histories) {
    for(const candle of candles) {
      const row=dates.get(candle.date)||{date:candle.date};
      row[key]=candle.close;
      dates.set(candle.date,row);
    }
  }
  const rows=[...dates.values()].sort((a,b)=>a.date.localeCompare(b.date));
  if(!rows.length) throw new Error(`Không tải được Yahoo Finance OHLC: ${diagnostics.join(" | ")}`);
  return {rows,diagnostics,failed:keys.filter(k=>!histories.has(k)).map(k=>ASSET_SYMBOLS[k]),
    asOf:rows[rows.length-1].date,source:backupCount?(backupCount===histories.size?"Yahoo snapshot":"Yahoo live + snapshot"):"Yahoo live"};
}
