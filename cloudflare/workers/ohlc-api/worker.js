/* CherryStock public OHLC API. No upstream secrets; allowlisted Yahoo host/symbol syntax. */
const ORIGINS = new Set(["https://haithanh8x.github.io", "http://localhost:5173", "http://127.0.0.1:5173"]);
const TTL_SECONDS = 1800;
function cors(origin) {
  return origin && ORIGINS.has(origin) ? { "Access-Control-Allow-Origin": origin, "Vary": "Origin" } : {};
}
function json(body, status, origin, ttl = 0) {
  return new Response(JSON.stringify(body), { status, headers: {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": ttl ? "public, max-age=" + ttl : "no-store",
    "X-Content-Type-Options": "nosniff", ...cors(origin),
  } });
}
function marketDate(epoch, timezone) {
  // Use exchange-local calendar date; UTC dates can be wrong for Asian exchanges.
  const format = new Intl.DateTimeFormat("en-US", {
    timeZone: timezone, year: "numeric", month: "2-digit", day: "2-digit",
  });
  const p = Object.fromEntries(format.formatToParts(new Date(epoch * 1000)).map(x => [x.type, x.value]));
  return p.year + "-" + p.month + "-" + p.day;
}
function normalizeYahoo(data, symbol) {
  const result = data && data.chart && data.chart.result && data.chart.result[0];
  if (!result || !Array.isArray(result.timestamp)) throw new Error("Yahoo returned no history");
  const meta = result.meta || {};
  const timezone = meta.exchangeTimezoneName || "UTC";
  const quote = result.indicators && result.indicators.quote && result.indicators.quote[0];
  if (!quote) throw new Error("Yahoo returned no OHLC");
  const byDate = new Map();
  for (let i = 0; i < result.timestamp.length; i++) {
    const o = quote.open && quote.open[i], h = quote.high && quote.high[i];
    const l = quote.low && quote.low[i], c = quote.close && quote.close[i];
    if (![o, h, l, c].every(x => typeof x === "number" && Number.isFinite(x) && x > 0)) continue;
    const v = quote.volume && quote.volume[i];
    const date = marketDate(result.timestamp[i], timezone);
    byDate.set(date, { date, open:o, high:h, low:l, close:c,
      volume: Number.isFinite(v) && v >= 0 ? v : 0 });
  }
  const candles = [...byDate.values()].sort((a,b) => a.date.localeCompare(b.date));
  if (!candles.length) throw new Error("Yahoo history has no valid candles");
  return { schemaVersion: 1, provider:"yahoo", symbol, range:"1y", interval:"1d",
    timezone, currency:meta.currency || null, asOf:candles[candles.length-1].date, candles };
}
async function handle(event) {
  const request = event.request;
  const origin = request.headers.get("Origin");
  const url = new URL(request.url);
  if (request.method === "OPTIONS" && url.pathname === "/api/v1/ohlc") {
    if (!origin || !ORIGINS.has(origin)) return new Response(null, {status:403});
    return new Response(null, {status:204, headers:{
      ...cors(origin), "Access-Control-Allow-Methods":"GET, OPTIONS",
      "Access-Control-Allow-Headers":"Content-Type", "Access-Control-Max-Age":"86400" }});
  }
  if (request.method !== "GET") return json({error:"Method not allowed"},405,origin);
  if (url.pathname === "/health") return json({ok:true,service:"cherrystock-ohlc",version:1},200,origin);
  if (url.pathname !== "/api/v1/ohlc") return json({error:"Not found"},404,origin);
  const provider = url.searchParams.get("provider") || "yahoo";
  if (!["yahoo","fireant","duckdb","r2"].includes(provider))
    return json({error:"Unknown OHLC provider"},400,origin);
  if (provider !== "yahoo")
    return json({error:"Provider not configured", provider},501,origin);
  const symbol = (url.searchParams.get("symbol") || "").trim();
  if (!/^[A-Za-z0-9^._=\-]{1,30}$/.test(symbol))
    return json({error:"Invalid symbol"},400,origin);
  if ((url.searchParams.get("range") || "1y") !== "1y" ||
      (url.searchParams.get("interval") || "1d") !== "1d")
    return json({error:"Only range=1y and interval=1d are supported"},400,origin);
  const cacheKey = new Request(url.origin + url.pathname + "?provider=yahoo&symbol=" +
    encodeURIComponent(symbol) + "&range=1y&interval=1d");
  const cache = caches.default;
  const cached = await cache.match(cacheKey);
  if (cached) {
    const headers = new Headers(cached.headers);
    for (const [k,v] of Object.entries(cors(origin))) headers.set(k,v);
    return new Response(cached.body,{status:cached.status,headers});
  }
  const upstream = "https://query1.finance.yahoo.com/v8/finance/chart/" +
    encodeURIComponent(symbol) + "?range=1y&interval=1d";
  let response;
  try {
    const result = await fetch(upstream, {headers:{"Accept":"application/json"}});
    if (!result.ok) {
      return json({error:"Yahoo Finance temporarily unavailable",provider,symbol,
        upstreamStatus:result.status},result.status===429?503:502,origin);
    }
    const parsed = normalizeYahoo(await result.json(), symbol);
    response = json(parsed,200,origin,TTL_SECONDS);
    event.waitUntil(cache.put(cacheKey, response.clone()));
    return response;
  } catch (err) {
    return json({error:"Yahoo OHLC request failed",provider,symbol,
      detail:err instanceof Error ? err.message : "Unknown upstream error"},502,origin);
  }
}
addEventListener("fetch", event => event.respondWith(handle(event)));
