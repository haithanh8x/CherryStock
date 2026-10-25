import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { createMarketDataDriver } from "./data/driver";
import { loadIntermarket } from "./data/ohlc";
import type { IntermarketRow } from "./data/ohlc";
import type {
  MarketOverviewSnapshot, MarketSource, Timeframe, IntermarketPoint,
  InvestorFlowPoint,
} from "./data/types";
import { applyTheme, DEFAULT_THEME, resolveTheme } from "./theme/theme";
import type { ThemeName } from "./theme/theme";
import "./App.css";

const number = (n: number, digits = 2) =>
  n.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });
const signed = (n: number, digits = 2) => `${n > 0 ? "+" : ""}${number(n, digits)}`;
const pct = (n: number) => `${signed(n)}%`;
const signClass = (n: number) => n > 0 ? "positive" : n < 0 ? "negative" : "neutral";
const formatDate = (iso: string) =>
  new Intl.DateTimeFormat("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric", timeZone: "UTC" }).format(new Date(iso + "T00:00:00Z"));

function Icon({ name, size = 18 }: { name: string; size?: number }) {
  const paths: Record<string, ReactNode> = {
    overview: <><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></>,
    grid: <><path d="M3 4h18M3 10h18M3 16h18M3 22h18M8 4v18M16 4v18"/></>,
    chart: <><path d="M3 19l6-7 4 3 8-10"/><path d="M16 5h5v5"/></>,
    layers: <><path d="m12 3 9 5-9 5-9-5 9-5ZM3 12l9 5 9-5M3 16l9 5 9-5"/></>,
    wallet: <><rect x="3" y="5" width="18" height="15" rx="3"/><path d="M3 9h18M16 15h2"/></>,
    shield: <><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/><path d="m9 12 2 2 4-4"/></>,
    refresh: <><path d="M20 7v5h-5M4 17v-5h5"/><path d="M5 9a8 8 0 0 1 14-2l1 5M4 12a8 8 0 0 0 15 3"/></>,
    search: <><circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/></>,
    sun: <><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M19.1 4.9l-1.4 1.4M6.3 17.7l-1.4 1.4"/></>,
    moon: <path d="M20 15.5A8 8 0 0 1 8.5 4 8.5 8.5 0 1 0 20 15.5Z"/>,
    arrow: <><path d="m5 12 7-7 7 7M12 5v14"/></>,
    arrowdown: <><path d="m5 12 7 7 7-7M12 5v14"/></>,
    globe: <><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a15 15 0 0 1 0 18M12 3a15 15 0 0 0 0 18"/></>,
    activity: <path d="M2 13h5l3-7 4 12 3-6h5"/>,
    users: <><circle cx="9" cy="8" r="3"/><path d="M3 20v-2a6 6 0 0 1 12 0v2M17 5a3 3 0 0 1 0 6m1 4a4 4 0 0 1 3 4"/></>,
    flows: <><path d="M3 17l6-6 4 4 8-9M17 6h4v4"/></>,
    bolt: <path d="m13 2-9 12h7l-1 8 10-13h-7l0-7Z"/>,
    filter: <><path d="M3 5h18M7 12h10M10 19h4"/></>,
    info: <><circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7h.01"/></>,
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name] ?? paths.chart}</svg>;
}

function Panel({ title, subtitle, icon, action, children, className = "" }:
  { title: string; subtitle?: string; icon: string; action?: ReactNode; children: ReactNode; className?: string }) {
  return <section className={`panel ${className}`}>
    <div className="panel-head">
      <div className="panel-heading"><span className="panel-icon"><Icon name={icon} size={17}/></span>
        <div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div></div>
      {action}
    </div>
    <div className="panel-body">{children}</div>
  </section>;
}

function FrameToggle({ value, onChange }: { value: Timeframe; onChange: (t: Timeframe) => void }) {
  return <div className="segment" role="group" aria-label="Khung thời gian">
    {([["daily", "Ngày"], ["weekly", "Tuần"], ["monthly", "Tháng"]] as const).map(([key, text]) =>
      <button key={key} className={value === key ? "selected" : ""} type="button" onClick={() => onChange(key)} aria-pressed={value === key}>{text}</button>)}
  </div>;
}

type DatePoint = { date: string };
function sampleByTimeframe<T extends DatePoint>(data: T[], timeframe: Timeframe, limit = 48): T[] {
  if (timeframe === "daily") return data.slice(-limit);
  const map = new Map<string, T>();
  for (const row of data) {
    const d = new Date(row.date + "T00:00:00Z");
    if (Number.isNaN(d.getTime())) continue;
    if (timeframe === "weekly") d.setUTCDate(d.getUTCDate() - ((d.getUTCDay() + 6) % 7));
    const key = timeframe === "weekly" ? d.toISOString().slice(0, 10) : row.date.slice(0, 7);
    map.set(key, row); // end of each reporting period
  }
  return [...map.values()].slice(-limit);
}
type SeriesDef = { key: string; label: string; color: string };
function LineChart<T extends DatePoint>({ data, series, percent = false, height = 278 }:
  { data: T[]; series: SeriesDef[]; percent?: boolean; height?: number }) {
  if (!data.length || !series.length) return <div className="empty-plot">Chưa có chuỗi dữ liệu</div>;
  const w = 840, h = height, l = 48, r = 24, top = 18, bottom = 33;
  const plotW = w - l - r, plotH = h - top - bottom;
  const val = (row: T, key: string) => Number((row as unknown as Record<string, unknown>)[key]);
  const values = data.flatMap(row => series.map(s => val(row, s.key))).filter(Number.isFinite);
  if (!values.length) return <div className="empty-plot">Không có dữ liệu hợp lệ</div>;
  const minRaw = Math.min(...values), maxRaw = Math.max(...values);
  const pad = Math.max((maxRaw - minRaw) * .14, percent ? 1.8 : 1);
  const min = minRaw - pad, max = maxRaw + pad;
  const x = (i: number) => l + (data.length === 1 ? plotW / 2 : (i / (data.length - 1)) * plotW);
  const y = (v: number) => top + (max - v) / (max - min) * plotH;
  const path = (key: string) => data.map((row, i) => {
    const v = val(row, key);
    if (!Number.isFinite(v)) return "";
    const prior = i > 0 ? val(data[i-1], key) : NaN;
    return `${Number.isFinite(prior) ? "L" : "M"} ${x(i).toFixed(1)} ${y(v).toFixed(1)}`;
  }).join(" ");
  return <div className="plot">
    <svg viewBox={`0 0 ${w} ${h}`} role="img" aria-label={`Biểu đồ chuỗi thời gian: ${series.map(s=>s.label).join(", ")}`}>
      {Array.from({length:5},(_,i) => {
        const yy = top + i*plotH/4, v = max - i*(max-min)/4;
        return <g key={i}><line x1={l} x2={w-r} y1={yy} y2={yy} stroke="var(--border)" strokeDasharray="3 5" opacity=".8"/>
          <text x={l-10} y={yy+4} textAnchor="end" className="chart-label">{percent ? number(v,0)+"%" : number(v, v > 1000 ? 0 : 1)}</text></g>;
      })}
      {series.map(s => <g key={s.key}>
        <path d={path(s.key)} fill="none" stroke={s.color} strokeWidth={s.key === "vnindex" || s.key === "ma20" ? 2.7 : 1.9} strokeLinejoin="round" strokeLinecap="round"/>
        {Number.isFinite(val(data[data.length-1],s.key)) && <circle cx={x(data.length-1)} cy={y(val(data[data.length-1],s.key))} r="3" fill={s.color} stroke="var(--surface)" strokeWidth="1.5"/>}
      </g>)}
      <text x={l} y={h-8} className="chart-label">{data[0].date.slice(5)}</text>
      <text x={w-r} y={h-8} textAnchor="end" className="chart-label">{data[data.length-1].date.slice(5)}</text>
    </svg>
  </div>;
}

const intermarketSeries: SeriesDef[] = [
  {key:"vnindex",label:"VN-Index",color:"var(--chart-vni)"},
  {key:"spx",label:"S&P 500",color:"var(--chart-spx)"},
  {key:"ndx",label:"Nasdaq",color:"var(--chart-ndx)"},
  {key:"btc",label:"Bitcoin",color:"var(--chart-btc)"},
  {key:"gold",label:"Gold",color:"var(--chart-gold)"},
  {key:"oil",label:"Oil",color:"var(--chart-oil)"},
  {key:"dxy",label:"DXY",color:"var(--chart-dxy)"},
  {key:"usdvnd",label:"USD/VND",color:"var(--chart-usdvnd)"},
];
const breadthSeries: SeriesDef[] = [
  {key:"ma20",label:"> MA20",color:"var(--chart-ma20)"},
  {key:"ma50",label:"> MA50",color:"var(--chart-ma50)"},
  {key:"ma100",label:"> MA100",color:"var(--chart-ma100)"},
  {key:"ma200",label:"> MA200",color:"var(--chart-ma200)"},
];
function Legend({ series }: {series: SeriesDef[]}) {
  return <div className="chart-legend">{series.map(s => <span key={s.key}><i style={{background:s.color}}/>{s.label}</span>)}</div>;
}
function Sparkline({ values, positive }: { values: number[]; positive: boolean }) {
  if (values.length < 2) return null;
  const min = Math.min(...values), max = Math.max(...values), span = max-min||1;
  const pts = values.map((v,i) => `${(i/(values.length-1)*110).toFixed(1)},${(33-(v-min)/span*27).toFixed(1)}`).join(" ");
  return <svg className={positive?"spark pos":"spark neg"} viewBox="0 0 110 38" preserveAspectRatio="none" aria-hidden="true"><polyline points={pts} fill="none" stroke="currentColor" strokeWidth="2.3" strokeLinejoin="round" strokeLinecap="round"/></svg>;
}
function IndexCard({ label, value, change, changePct, history }: {
  label: string; value: number; change: number; changePct: number; history: number[];
}) {
  const isPositive=changePct>=0;
  return <div className="index-card">
    <div className="index-top"><span>{label}</span><span className="index-dot"/></div>
    <div className="index-main"><strong>{number(value)}</strong><Sparkline values={history} positive={isPositive}/></div>
    <div className={`index-change ${signClass(changePct)}`}><Icon name={isPositive?"arrow":"arrowdown"} size={13}/> {signed(change)} <span>({pct(changePct)})</span></div>
  </div>;
}
// Combine last known close per asset in each week/month; assets have different calendars.
function resampleIntermarket(rows:IntermarketRow[],timeframe:Timeframe):IntermarketRow[] {
  if(timeframe==="daily") return rows;
  const map=new Map<string,IntermarketRow>();
  for(const row of rows) {
    const d=new Date(row.date+"T00:00:00Z");
    if(timeframe==="weekly") d.setUTCDate(d.getUTCDate()-((d.getUTCDay()+6)%7));
    const key=timeframe==="weekly"?d.toISOString().slice(0,10):row.date.slice(0,7);
    const prior=map.get(key)??{date:row.date};
    prior.date=row.date;
    for(const asset of intermarketSeries) {
      const value=row[asset.key as keyof IntermarketRow];
      if(typeof value==="number"&&Number.isFinite(value)) (prior as Record<string,number|string>)[asset.key]=value;
    }
    map.set(key,prior);
  }
  return [...map.values()];
}
function Intermarket({ rows: _snapshotRows }: {rows: IntermarketPoint[]}) {
  const [timeframe,setTimeframe]=useState<Timeframe>("daily");
  const [selected,setSelected]=useState<string[]>(["vnindex","spx","ndx","gold"]);
  const [rows,setRows]=useState<IntermarketRow[]>([]);
  const [failed,setFailed]=useState<string[]>([]);
  const [error,setError]=useState<string|null>(null);
  const [asOf,setAsOf]=useState("");
  const [liveSource,setLiveSource]=useState("");
  const [diagnostics,setDiagnostics]=useState<string[]>([]);
  const [reload,setReload]=useState(0);
  useEffect(()=>{
    const controller=new AbortController();
    setError(null);
    loadIntermarket(controller.signal).then(result=>{
      if(!controller.signal.aborted){
        setRows(result.rows);setFailed(result.failed);setAsOf(result.asOf);
        setLiveSource(result.source);setDiagnostics(result.diagnostics);
      }
    }).catch(err=>{
      if(!controller.signal.aborted) setError(err instanceof Error?err.message:String(err));
    });
    return ()=>controller.abort();
  },[reload]);
  // Keep the full year for daily, and every period within that year for weekly/monthly.
  const sample=useMemo(()=>resampleIntermarket(rows,timeframe),[rows,timeframe]);
  const normalized=useMemo(()=>{
    const baseline:Record<string,number>={};
    return sample.map(row=>{
      const n:Record<string,number|string>={date:row.date};
      for(const s of intermarketSeries) {
        const close=row[s.key as keyof IntermarketRow];
        if(typeof close==="number" && Number.isFinite(close) && close>0) {
          if(!baseline[s.key]) baseline[s.key]=close;
          n[s.key]=(close/baseline[s.key]-1)*100;
        }
      }
      return n as {date:string;[key:string]:number|string};
    });
  },[sample]);
  const visible=intermarketSeries.filter(s=>selected.includes(s.key));
  const toggle=(key:string)=>setSelected(old=>old.includes(key)?(old.length>1?old.filter(k=>k!==key):old):[...old,key]);
  return <Panel title="Intermarket Analysis" subtitle="So sánh hiệu suất tương đối · chuẩn hóa 0% tại đầu kỳ" icon="globe" className="intermarket-panel"
    action={<FrameToggle value={timeframe} onChange={setTimeframe}/>}>
    <div className="series-controls" aria-label="Chọn tài sản để so sánh">
      {intermarketSeries.map(s=><button key={s.key} type="button" className={selected.includes(s.key)?"series-chip active":"series-chip"}
        onClick={()=>toggle(s.key)} aria-pressed={selected.includes(s.key)}>
        <i style={{background:s.color}}/>{s.label}</button>)}
    </div>
    {error && <div className="error-state" role="alert">{error} <button type="button" onClick={()=>setReload(x=>x+1)}>Thử lại</button></div>}
    {!rows.length && !error && <div className="loading-state">Đang tải OHLC 1 năm từ Yahoo Finance…</div>}
    {rows.length>0 && <LineChart data={normalized} series={visible} percent height={304}/>}
    {diagnostics.length>0 && <details className="chart-foot"><summary>Chi tiết kết nối Yahoo ({diagnostics.length})</summary><p>{diagnostics.join(" | ")}</p></details>}
    <div className="chart-foot">
      <span><span className="foot-dot"/> Source: {liveSource||"Yahoo Finance"} (OHLC 1D, 1Y) · EOD: {asOf || "—"} · Không điền dữ liệu giả</span>
      <span>{failed.length ? "Thiếu: "+failed.join(", ") : "8/8 tài sản"} · Khung {timeframe==="daily"?"ngày":timeframe==="weekly"?"tuần":"tháng"}</span>
    </div>
  </Panel>;
}
function Breadth({ rows }: {rows: MarketOverviewSnapshot["breadth"]}) {
  const [timeframe,setTimeframe]=useState<Timeframe>("daily");
  const sample=sampleByTimeframe(rows,timeframe,48);
  const latest=sample[sample.length-1];
  return <Panel title="Độ rộng thị trường" subtitle="Tỷ lệ cổ phiếu đang giao dịch trên đường MA" icon="activity" className="breadth-panel"
    action={<FrameToggle value={timeframe} onChange={setTimeframe}/>}>
    <div className="breadth-stats">{breadthSeries.map(s=><div className="breadth-stat" key={s.key}><span>{s.label}</span><strong>{latest?number(Number((latest as unknown as Record<string,number>)[s.key]),1):"—"}%</strong></div>)}</div>
    <LineChart data={sample} series={breadthSeries} percent height={260}/>
    <Legend series={breadthSeries}/>
  </Panel>;
}
function Sectors({ rows }: {rows: MarketOverviewSnapshot["industries"]}) {
  const sorted=[...rows].sort((a,b)=>b.changePct-a.changePct);
  const max=Math.max(...sorted.map(s=>Math.abs(s.changePct)),1);
  return <Panel title="Hiệu suất ngành" subtitle="Biến động ngành trong phiên" icon="layers" className="sectors-panel"
    action={<span className="tiny-label">1 phiên</span>}>
    <div className="sector-head"><span>Ngành</span><span>Thay đổi</span></div>
    <div className="sector-list">{sorted.map(s=><div className="sector-row" key={s.name}>
      <div className="sector-name">{s.name}</div>
      <div className="sector-meter"><span className="sector-zero"/><span className={`sector-bar ${s.changePct>=0?"up":"down"}`}
        style={{width:`${Math.abs(s.changePct)/max*48}%`}}/></div>
      <strong className={signClass(s.changePct)}>{pct(s.changePct)}</strong>
    </div>)}</div>
    <div className="sector-note">Hiệu suất ngành sẽ lấy từ <code>cal_Industry_Index_D</code> sau khi pipeline R2 hoạt động.</div>
  </Panel>;
}
const investorSeries=[
  {key:"institutional" as const,label:"Tổ chức",color:"var(--chart-vni)"},
  {key:"individual" as const,label:"Cá nhân",color:"var(--chart-spx)"},
  {key:"foreign" as const,label:"Nước ngoài",color:"var(--chart-gold)"},
  {key:"proprietary" as const,label:"Tự doanh",color:"var(--chart-ndx)"},
];
function aggregateFlows(data: InvestorFlowPoint[], timeframe:Timeframe): InvestorFlowPoint[] {
  if (timeframe==="daily") return data.slice(-22);
  const map=new Map<string,InvestorFlowPoint>();
  for (const r of data) {
    const d=new Date(r.date+"T00:00:00Z");
    if (timeframe==="weekly") d.setUTCDate(d.getUTCDate()-((d.getUTCDay()+6)%7));
    const key=timeframe==="weekly"?d.toISOString().slice(0,10):r.date.slice(0,7);
    const prior=map.get(key)??{date:key,institutional:0,individual:0,foreign:0,proprietary:0};
    for(const s of investorSeries) prior[s.key]+=r[s.key];
    map.set(key,prior);
  }
  return [...map.values()].slice(-22);
}
function CashFlow({ rows }: { rows:InvestorFlowPoint[] }) {
  const [timeframe,setTimeframe]=useState<Timeframe>("daily");
  const [investor,setInvestor]=useState<typeof investorSeries[number]["key"]>("foreign");
  const data=useMemo(()=>aggregateFlows(rows,timeframe),[rows,timeframe]);
  const summary=investorSeries.map(s=>({...s,total:data.reduce((sum,row)=>sum+row[s.key],0)}));
  const selected=investorSeries.find(s=>s.key===investor)!;
  const v=data.map(x=>x[investor]), range=Math.max(...v.map(Math.abs),1);
  const h=215,w=780,l=46,r=18,mid=100,scale=80/range,barW=Math.min(23,(w-l-r)/Math.max(data.length,1)*.65);
  return <Panel title="Dòng tiền nhà đầu tư" subtitle="Mua / bán ròng ước tính · đơn vị tỷ đồng" icon="flows" className="flow-panel"
    action={<FrameToggle value={timeframe} onChange={setTimeframe}/>}>
    <div className="flow-totals">{summary.map(s=><button type="button" key={s.key} className={investor===s.key?"flow-total selected":"flow-total"} onClick={()=>setInvestor(s.key)} aria-pressed={investor===s.key}>
      <span className="flow-name"><i style={{background:s.color}}/>{s.label}</span>
      <strong className={signClass(s.total)}>{signed(s.total,0)} <small>tỷ</small></strong>
      <span className="flow-meta">Lũy kế khung đang xem</span>
    </button>)}</div>
    <div className="plot flow-plot"><svg viewBox={`0 0 ${w} ${h}`} role="img" aria-label={`Dòng tiền ${selected.label} theo ${timeframe}`}>
      {[-1,-.5,0,.5,1].map((frac,i)=>{
        const yy=mid-frac*80;return <g key={i}><line x1={l} x2={w-r} y1={yy} y2={yy} stroke="var(--border)" strokeDasharray={frac===0?"none":"3 5"}/>
        <text className="chart-label" x={l-8} y={yy+4} textAnchor="end">{number(range*frac,0)}</text></g>})}
      {v.map((val,i)=>{
        const x=l+((i+.5)/Math.max(v.length,1))*(w-l-r)-barW/2;
        const yy=mid-val*scale;
        return <rect key={i} x={x} y={Math.min(mid,yy)} width={barW} height={Math.max(1,Math.abs(mid-yy))}
          fill={val>=0?"var(--positive)":"var(--negative)"} opacity=".85" rx="2"><title>{data[i].date}: {signed(val,0)} tỷ</title></rect>;
      })}
      {data.length>0 && <><text x={l} y={h-10} className="chart-label">{data[0].date.slice(5)}</text>
        <text x={w-r} y={h-10} textAnchor="end" className="chart-label">{data[data.length-1].date.slice(5)}</text></>}
    </svg></div>
    <div className="flow-foot"><span className="positive">■ Mua ròng</span><span className="negative">■ Bán ròng</span><span>Chọn nhóm NĐT ở trên để xem diễn biến</span></div>
  </Panel>;
}
function Watchlist({ rows, query, onQuery }: {rows:MarketOverviewSnapshot["watchlist"]; query:string;onQuery:(s:string)=>void}) {
  const filtered=rows.filter(x=>x.symbol.toLowerCase().includes(query.toLowerCase()));
  return <Panel title="Watchlist" subtitle="Theo dõi mã cổ phiếu" icon="shield" className="watch-panel">
    <label className="watch-search"><Icon name="search" size={16}/><input aria-label="Tìm mã trong Watchlist" placeholder="Tìm mã cổ phiếu..." value={query} onChange={e=>onQuery(e.target.value)}/></label>
    <div className="watch-thead"><span>Mã CK</span><span>Giá</span><span>% thay đổi</span></div>
    <div className="watch-rows">{filtered.length?filtered.map(q=><div className="watch-row" key={q.symbol}>
      <div><strong>{q.symbol}</strong><small>KL {q.volume}</small></div>
      <strong>{number(q.price,2)}</strong><span className={`pill-change ${signClass(q.changePct)}`}>{pct(q.changePct)}</span>
    </div>):<div className="watch-empty">Không tìm thấy mã phù hợp.</div>}</div>
    <div className="watch-bottom"><span><span className="foot-dot"/> Dữ liệu từ snapshot</span><span>{filtered.length} mã</span></div>
  </Panel>;
}
function Dashboard({ data }: {data:MarketOverviewSnapshot}) {
  const [query,setQuery]=useState("");
  const summary=data.summary;
  const breadthTotal=summary.advancers+summary.decliners+summary.unchanged;
  return <>
    <div className="indices-grid">{data.indices.map(i=><IndexCard key={i.symbol} {...i}/>)}</div>
    <div className="market-strip">
      <div className="strip-item"><span className="strip-icon"><Icon name="wallet"/></span><div><small>GTGD toàn thị trường</small><strong>{number(summary.turnoverBn/1000,2)} <em>nghìn tỷ</em></strong><span className={signClass(summary.turnoverVs20Pct)}>{pct(summary.turnoverVs20Pct)} so với TB20</span></div></div>
      <div className="strip-item"><span className="strip-icon"><Icon name="users"/></span><div><small>Độ rộng thị trường</small><strong><span className="positive">{summary.advancers}</span> / <span className="negative">{summary.decliners}</span></strong><div className="breadth-bar" aria-label={`Tăng ${summary.advancers}, giảm ${summary.decliners}, đứng giá ${summary.unchanged}`}><i style={{width:`${summary.advancers/breadthTotal*100}%`}}/><i style={{width:`${summary.unchanged/breadthTotal*100}%`}}/><i style={{width:`${summary.decliners/breadthTotal*100}%`}}/></div></div></div>
      <div className="strip-item"><span className="strip-icon"><Icon name="globe"/></span><div><small>Khối ngoại</small><strong className={signClass(summary.foreignNetBn)}>{signed(summary.foreignNetBn,0)} <em>tỷ</em></strong><span className="strip-muted">Giá trị mua / bán ròng</span></div></div>
      <div className="strip-item"><span className="strip-icon"><Icon name="bolt"/></span><div><small>Tự doanh</small><strong className={signClass(summary.proprietaryNetBn)}>{signed(summary.proprietaryNetBn,0)} <em>tỷ</em></strong><span className="strip-muted">Giá trị mua / bán ròng</span></div></div>
    </div>
    <div className="dashboard-grid"><Intermarket rows={data.intermarket}/><Watchlist rows={data.watchlist} query={query} onQuery={setQuery}/><Breadth rows={data.breadth}/><Sectors rows={data.industries}/><CashFlow rows={data.flows}/></div>
  </>;
}
export default function App() {
  const [theme,setTheme]=useState<ThemeName>(() => {
    try {return resolveTheme(localStorage.getItem("cherrystock-theme"));} catch {return DEFAULT_THEME;}
  });
  const [data,setData]=useState<MarketOverviewSnapshot|null>(null);
  const [error,setError]=useState<string|null>(null);
  const [source,setSource]=useState<MarketSource>("mock");
  const [loading,setLoading]=useState(true);
  const [revision,setRevision]=useState(0);
  useEffect(()=>{
    applyTheme(theme);
    try {localStorage.setItem("cherrystock-theme",theme);}catch{/* private mode */}
  },[theme]);
  useEffect(()=>{
    const controller=new AbortController();
    setLoading(true);setError(null);
    try {
      const driver=createMarketDataDriver();
      setSource(driver.source);
      driver.load(controller.signal).then(snapshot=>{
        if(!controller.signal.aborted){setData(snapshot);setLoading(false);}
      }).catch(err=>{
        if(!controller.signal.aborted){setError(err instanceof Error?err.message:String(err));setLoading(false);}
      });
    }catch(err){setError(err instanceof Error?err.message:String(err));setLoading(false);}
    return ()=>controller.abort();
  },[revision]);
  return <div className="app-shell">
    <aside className="sidebar">
      <a className="brand" href={import.meta.env.BASE_URL} aria-label="CherryStock Home">
        <span className="brand-logo"><svg viewBox="0 0 32 32" width="27" height="27" fill="none"><path d="M5 22 12 15 17 19 27 7" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"/><path d="M21 7h6v6" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"/></svg></span>
        <div><strong>CherryStock</strong><small>QUANT TERMINAL</small></div>
      </a>
      <div className="sidebar-group-label">WORKSPACE</div>
      <nav className="sidebar-nav" aria-label="Điều hướng chính">
        <a href="#market-overview" className="active"><Icon name="overview"/>Market Overview <span className="nav-current"/></a>
        {([["chart","Screener"],["wallet","Portfolio"],["layers","R/S Levels"],["flows","SmartMoney"],["shield","Operations"]] as const).map(([icon,name])=>
          <span key={name} className="nav-coming" title="Chưa chuyển đổi sang React"><Icon name={icon}/>{name}<small>Sớm</small></span>)}
      </nav>
      <div className="sidebar-foot"><div className="sidebar-system"><span className="signal-dot"/><div><strong>CherryStock Data</strong><small>{source==="mock"?"DEMO MODE":"R2 SNAPSHOT"}</small></div></div><span>Financial intelligence platform</span></div>
    </aside>
    <main className="main-content" id="market-overview">
      <header className="topbar">
        <div className="topbar-left"><span className="topbar-breadcrumb">CherryStock</span><span className="slash">/</span><span>Market Overview</span></div>
        <div className="topbar-actions"><span className="market-session"><span className="signal-dot"/> EOD SNAPSHOT</span>
          <button className="icon-button" type="button" aria-label="Đổi giao diện sáng tối" title="Đổi theme" onClick={()=>setTheme(t=>t==="cherry_dark"?"cherry_light":"cherry_dark")}><Icon name={theme==="cherry_dark"?"sun":"moon"}/></button>
          <button className="icon-button" type="button" aria-label="Tải lại dữ liệu" title="Tải lại dữ liệu" onClick={()=>setRevision(x=>x+1)}><Icon name="refresh"/></button>
          <div className="avatar">CS</div>
        </div>
      </header>
      <div className="content-area">
        <div className="heading-row">
          <div><div className="eyebrow"><span className="eyebrow-line"/> FINANCIAL MARKET INTELLIGENCE</div><h1>Market Overview</h1>
          <p>Theo dõi xu hướng, độ rộng, dòng tiền và hiệu suất ngành trong một màn hình.</p></div>
          <div className="heading-right"><span className="asof-label">NGÀY DỮ LIỆU</span><strong>{data?formatDate(data.asOf):"—"}</strong><span className="snapshot-caption">Thị trường chứng khoán Việt Nam</span></div>
        </div>
        <div className={source==="mock"?"mode-banner demo":"mode-banner"}><Icon name="info" size={17}/>
          {source==="mock"?
            <span><strong>DEMO / MOCK DATA</strong> — Các panel khác dùng dữ liệu giả lập; riêng Intermarket lấy dữ liệu từ Yahoo Finance qua Cloudflare API. Chưa kết nối snapshot Cloudflare R2.</span>:
            <span><strong>R2 SNAPSHOT</strong> — Các panel khác lấy snapshot từ Cloudflare R2; Intermarket lấy Yahoo Finance qua Cloudflare API. Không phải luồng realtime.</span>}
        </div>
        {loading && !data && <div className="loading-state">Đang tải dữ liệu Market Overview...</div>}
        {error && <div className="error-state" role="alert"><strong>Không tải được dữ liệu thị trường</strong><p>{error}</p><button type="button" onClick={()=>setRevision(x=>x+1)}>Thử lại</button></div>}
        {data && <><Dashboard data={data}/>{loading&&<div className="inline-loading">Đang làm mới snapshot…</div>}</>}
        <footer className="page-footer"><span>© 2026 CherryStock · Market Overview</span><span>Source: Intermarket Yahoo Finance API · Other panels: {source==="mock"?"Synthetic demo data":"Cloudflare R2 snapshot"} · {data?.asOf ?? "n/a"}</span></footer>
      </div>
    </main>
  </div>;
}
