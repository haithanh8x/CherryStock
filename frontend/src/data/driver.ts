import { mockOverview } from "./mock";
import type { MarketOverviewSnapshot, MarketSource } from "./types";

export interface MarketDataDriver {
  readonly source: MarketSource;
  load(signal?: AbortSignal): Promise<MarketOverviewSnapshot>;
}
export class MarketDataError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "MarketDataError";
  }
}
function assertSnapshot(data: unknown): asserts data is MarketOverviewSnapshot {
  if (!data || typeof data !== "object") throw new MarketDataError("Snapshot JSON không hợp lệ.");
  const x = data as Record<string, unknown>;
  if (x.schemaVersion !== 1 || typeof x.asOf !== "string" ||
      !Array.isArray(x.indices) || !Array.isArray(x.intermarket) ||
      !Array.isArray(x.breadth) || !Array.isArray(x.industries) ||
      !Array.isArray(x.flows) || !Array.isArray(x.watchlist) ||
      !x.summary || typeof x.summary !== "object") {
    throw new MarketDataError("Snapshot không đúng contract MarketOverview v1.");
  }
  if (!x.indices.length || !x.intermarket.length || !x.breadth.length) {
    throw new MarketDataError("Snapshot không có chuỗi dữ liệu thị trường cần thiết.");
  }
}
async function fetchJson(url: string, signal?: AbortSignal): Promise<unknown> {
  let res: Response;
  try {
    res = await fetch(url, { signal, cache: "no-store" });
  } catch (err) {
    if (signal?.aborted) throw err;
    throw new MarketDataError("Không kết nối được R2 public endpoint. Kiểm tra URL và CORS.");
  }
  if (!res.ok) throw new MarketDataError(`Không tải được dữ liệu R2 (HTTP ${res.status}).`);
  try { return await res.json(); } catch { throw new MarketDataError("R2 trả về JSON không hợp lệ."); }
}
function assetUrl(base: string, path: string): string {
  if (!path || path.startsWith("/") || path.includes("\\") ||
      path.split("/").some(part => !part || part === "." || part === ".." || part.includes("?") || part.includes("#"))) {
    throw new MarketDataError("Đường dẫn asset trong manifest không hợp lệ.");
  }
  const prefix = base.endsWith("/") ? base : base + "/";
  const origin = new URL(prefix);
  if (!["https:", "http:"].includes(origin.protocol)) throw new MarketDataError("R2 public URL phải dùng HTTP(S).");
  return new URL(path.split("/").map(encodeURIComponent).join("/"), prefix).toString();
}
function createR2Driver(base: string): MarketDataDriver {
  if (!base.trim()) throw new MarketDataError("Thiếu VITE_R2_PUBLIC_BASE_URL cho chế độ R2.");
  return {
    source: "r2",
    async load(signal) {
      const manifest = await fetchJson(assetUrl(base, "market-overview/v1/manifest.json"), signal);
      if (!manifest || typeof manifest !== "object") throw new MarketDataError("R2 manifest không hợp lệ.");
      const m = manifest as Record<string, unknown>;
      if (m.schemaVersion !== 1 || typeof m.snapshot !== "string") {
        throw new MarketDataError("R2 manifest cần schemaVersion=1 và snapshot=<relative path>.");
      }
      const snapshot = await fetchJson(assetUrl(base, m.snapshot), signal);
      assertSnapshot(snapshot);
      return snapshot;
    },
  };
}
/** No silent fallback: explicit R2 errors must be visible, not disguised as live mock data. */
export function createMarketDataDriver(): MarketDataDriver {
  const source = (import.meta.env.VITE_MARKET_DATA_SOURCE || "mock").toLowerCase();
  if (source === "mock") return { source: "mock", async load() { return mockOverview; } };
  if (source === "r2") return createR2Driver(import.meta.env.VITE_R2_PUBLIC_BASE_URL || "");
  throw new MarketDataError(`Nguồn dữ liệu không được hỗ trợ: ${source}`);
}
