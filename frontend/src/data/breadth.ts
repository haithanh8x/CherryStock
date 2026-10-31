/** Real market-breadth series, independently loaded from Cloudflare R2 via Worker. */
import type { BreadthPoint } from "./types";

export interface BreadthSnapshot {
  schemaVersion: 1;
  source: string;
  asOf: string;
  summary: { advancers: number; decliners: number; unchanged: number };
  breadth: (BreadthPoint & { coverage?: number })[];
  timeframes: Record<"D" | "W" | "M", BreadthPoint[]>;
}

const API_BASE = (
  import.meta.env.VITE_BREADTH_API_BASE_URL ||
  "https://cherrystock-breadth.cherrystock-haithanh8x.workers.dev"
).replace(/\/$/, "");

export async function loadBreadth(signal?: AbortSignal): Promise<BreadthSnapshot> {
  const response = await fetch(`${API_BASE}/api/v1/breadth`, {
    signal, cache: "no-store",
  });
  if (!response.ok) throw new Error(`Cloudflare R2 breadth: HTTP ${response.status}`);
  const raw: unknown = await response.json();
  if (!raw || typeof raw !== "object") throw new Error("Invalid market breadth JSON");
  const value = raw as Record<string, unknown>;
  if (value.schemaVersion !== 1 || !Array.isArray(value.breadth) ||
      !value.breadth.length || typeof value.asOf !== "string") {
    throw new Error("Invalid market breadth snapshot contract");
  }
  if (!value.summary || typeof value.summary !== "object") {
    throw new Error("Market breadth summary is missing");
  }
  const summary = value.summary as Record<string, unknown>;
  for (const key of ["advancers", "decliners", "unchanged"]) {
    if (typeof summary[key] !== "number" || !Number.isInteger(summary[key]) ||
        summary[key] < 0) throw new Error("Invalid breadth summary");
  }
  function parsePoints(input: unknown): BreadthPoint[] {
    if (!Array.isArray(input)) throw new Error("Invalid timeframe series");
    return input.map((r: unknown) => {
    if (!r || typeof r !== "object") throw new Error("Invalid breadth record");
    const row = r as Record<string, unknown>;
    if (typeof row.date !== "string") throw new Error("Invalid breadth date");
    for (const key of ["ma20", "ma50", "ma100", "ma200"]) {
      if (typeof row[key] !== "number" || !Number.isFinite(row[key]) ||
          row[key] < 0 || row[key] > 100) {
        throw new Error(`Invalid breadth value: ${key}`);
      }
    }
    return row as unknown as BreadthPoint;
    });
  }
  const validated = parsePoints(value.breadth);
  if (!value.timeframes || typeof value.timeframes !== "object")
    throw new Error("Native D/W/M breadth series missing");
  const frames = value.timeframes as Record<string, unknown>;
  const timeframes = { D: parsePoints(frames.D), W: parsePoints(frames.W), M: parsePoints(frames.M) };
  return {
    schemaVersion: 1,
    source: typeof value.source === "string" ? value.source : "cal_indicator_history",
    asOf: value.asOf,
    summary: summary as unknown as BreadthSnapshot["summary"],
    breadth: validated,
    timeframes,
  };
}
