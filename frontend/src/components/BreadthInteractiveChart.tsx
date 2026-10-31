import { useEffect, useRef, useState } from "react";
import type { KeyboardEvent, PointerEvent } from "react";
import {
  ColorType, CrosshairMode, LineSeries, createChart,
  type IChartApi, type ISeriesApi, type LogicalRange,
  type MouseEventParams, type Time,
} from "lightweight-charts";
import type { BreadthPoint } from "../data/types";
import "./BreadthInteractiveChart.css";

type LineDef = { key: string; label: string; color: string };
type DragMode = "start" | "end" | "move";
type WindowRange = [number, number];
type HoverPoint = { date: string; row: BreadthPoint };
const OVERVIEW_HEIGHT = 64;
const OVERVIEW_WIDTH = 840;

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}
function displayDate(date: string): string {
  const [year, month, day] = date.split("-");
  return year && month && day ? `${day}/${month}/${year}` : date;
}
function toIso(time: Time | undefined): string | null {
  if (time === undefined) return null;
  if (typeof time === "string") return time;
  if (typeof time === "number") return new Date(time * 1000).toISOString().slice(0, 10);
  return `${time.year}-${String(time.month).padStart(2, "0")}-${String(time.day).padStart(2, "0")}`;
}
function cssValue(variable: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(variable).trim();
}
function seriesValue(row: BreadthPoint, key: string): number {
  return Number((row as unknown as Record<string, number | string>)[key]);
}

export function BreadthInteractiveChart({
  data, series,
}: {
  data: BreadthPoint[];
  series: LineDef[];
}) {
  const chartContainer = useRef<HTMLDivElement>(null);
  const chartApi = useRef<IChartApi | null>(null);
  const lineApiByKey = useRef<Map<string, ISeriesApi<"Line", Time>>>(new Map());
  const overview = useRef<HTMLDivElement>(null);
  const drag = useRef<{ mode: DragMode; anchor: number; initial: WindowRange } | null>(null);
  const [selected, setSelected] = useState<WindowRange>([0, Math.max(0, data.length - 1)]);
  const [hover, setHover] = useState<HoverPoint | null>(null);
  const [visibleKeys, setVisibleKeys] = useState<string[]>(() => series.map(line => line.key));

  const last = Math.max(0, data.length - 1);
  const from = clamp(selected[0], 0, last);
  const to = clamp(selected[1], from, last);
  const minimumSpan = Math.min(5, last);
  const visibleLines = series.filter(line => visibleKeys.includes(line.key));
  const toggleLine = (key: string) => {
    setVisibleKeys(previous => {
      if (previous.includes(key)) {
        return previous.length > 1 ? previous.filter(item => item !== key) : previous;
      }
      return [...previous, key];
    });
    setHover(null);
  };

  // The chart library owns zoom/pan/price-scale gestures. The overview is only
  // a second input to the same chart's visible logical range.
  useEffect(() => {
    const container = chartContainer.current;
    if (!container || data.length === 0) return;

    const colors = () => ({
      background: cssValue("--surface"),
      text: cssValue("--muted"),
      border: cssValue("--border"),
    });
    const theme = colors();
    const chart = createChart(container, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: theme.background },
        textColor: theme.text,
        fontFamily: "DM Sans, sans-serif",
        fontSize: 11,
        attributionLogo: false,
      },
      grid: {
        vertLines: { color: theme.border, visible: true },
        horzLines: { color: theme.border, visible: true },
      },
      rightPriceScale: {
        visible: true,
        autoScale: true,
        borderColor: theme.border,
        scaleMargins: { top: 0.12, bottom: 0.1 },
      },
      leftPriceScale: { visible: false },
      timeScale: {
        visible: true,
        borderColor: theme.border,
        rightOffset: 0,
        fixLeftEdge: true,
        timeVisible: false,
      },
      localization: { locale: "vi-VN", dateFormat: "dd/MM/yyyy" },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { labelVisible: true, color: theme.text, width: 1 },
        horzLine: { labelVisible: true, color: theme.text, width: 1 },
      },
      handleScale: {
        mouseWheel: false,
        pinch: true,
        axisPressedMouseMove: { time: true, price: true },
        axisDoubleClickReset: { time: true, price: true },
      },
      handleScroll: {
        pressedMouseMove: true,
        mouseWheel: false,
        horzTouchDrag: true,
        vertTouchDrag: true,
      },
    });

    const lineApis: ISeriesApi<"Line", Time>[] = [];
    const byKey = new Map<string, ISeriesApi<"Line", Time>>();
    for (const line of series) {
      const color = line.color.startsWith("var(")
        ? cssValue(line.color.slice(4, -1)) : line.color;
      const api = chart.addSeries(LineSeries, {
        color,
        lineWidth: line.key === "ma20" ? 3 : 2,
        priceLineVisible: false,
        lastValueVisible: true,
        crosshairMarkerVisible: true,
        visible: visibleKeys.includes(line.key),
        priceFormat: {
          type: "custom",
          formatter: (v: number) => `${v.toFixed(1)}%`,
          minMove: 0.01,
        },
      });
      api.setData(data.map(row => ({
        time: row.date as Time,
        value: seriesValue(row, line.key),
      })));
      lineApis.push(api);
      byKey.set(line.key, api);
    }
    chartApi.current = chart;
    lineApiByKey.current = byKey;

    const byDate = new Map(data.map(row => [row.date, row] as const));
    const updateHover = (param: MouseEventParams<Time>) => {
      const iso = toIso(param.time);
      const row = iso ? byDate.get(iso) : undefined;
      if (!row || !param.point) {
        setHover(null);
        return;
      }
      setHover({ date: iso!, row });
    };
    chart.subscribeCrosshairMove(updateHover);
    chart.subscribeClick(updateHover);
    const onLogicalRange = (range: LogicalRange | null) => {
      if (!range) return;
      const a = clamp(Math.ceil(range.from), 0, last);
      const b = clamp(Math.floor(range.to), a, last);
      setSelected(old => old[0] === a && old[1] === b ? old : [a, b]);
    };
    chart.timeScale().subscribeVisibleLogicalRangeChange(onLogicalRange);
    chart.timeScale().setVisibleLogicalRange({ from: 0, to: last });

    const observer = new MutationObserver(() => {
      const next = colors();
      chart.applyOptions({
        layout: {
          background: { type: ColorType.Solid, color: next.background },
          textColor: next.text,
        },
        grid: {
          vertLines: { color: next.border },
          horzLines: { color: next.border },
        },
        timeScale: { borderColor: next.border },
        rightPriceScale: { borderColor: next.border },
      });
      lineApis.forEach((api, i) => {
        const color = series[i].color;
        api.applyOptions({ color: color.startsWith("var(")
          ? cssValue(color.slice(4, -1)) : color });
      });
    });
    observer.observe(document.documentElement, {
      attributes: true, attributeFilter: ["data-theme"],
    });

    return () => {
      observer.disconnect();
      chart.unsubscribeCrosshairMove(updateHover);
      chart.unsubscribeClick(updateHover);
      chart.timeScale().unsubscribeVisibleLogicalRangeChange(onLogicalRange);
      chart.remove();
      chartApi.current = null;
      lineApiByKey.current.clear();
    };
  }, [data, series, last]);

  // Toggle actual Lightweight Charts series without losing X/Y zoom.
  useEffect(() => {
    for (const line of series) {
      lineApiByKey.current.get(line.key)?.applyOptions({
        visible: visibleKeys.includes(line.key),
      });
    }
  }, [series, visibleKeys]);

  function showWindow(start: number, end: number) {
    if (!data.length) return;
    const a = clamp(start, 0, last);
    const b = clamp(end, a, last);
    setSelected([a, b]);
    chartApi.current?.timeScale().setVisibleLogicalRange({ from: a, to: b });
    setHover(null);
  }

  function zoomPreset(days: number | "all") {
    if (!data.length) return;
    if (days === "all") return showWindow(0, last);
    const cutoff = new Date(data[last].date + "T00:00:00Z");
    cutoff.setUTCDate(cutoff.getUTCDate() - days);
    const iso = cutoff.toISOString().slice(0, 10);
    const index = data.findIndex(row => row.date >= iso);
    showWindow(clamp(index === -1 ? 0 : index, 0, last - minimumSpan), last);
  }

  function overviewIndex(clientX: number) {
    const rect = overview.current?.getBoundingClientRect();
    if (!rect || rect.width <= 0) return 0;
    return Math.round(clamp((clientX - rect.left) / rect.width, 0, 1) * last);
  }
  function brushDown(e: PointerEvent<HTMLDivElement>) {
    if (!last) return;
    const target = e.target as HTMLElement;
    const mode = target.closest("[data-brush-action]")
      ?.getAttribute("data-brush-action") as DragMode | null;
    const anchor = overviewIndex(e.clientX);
    if (!mode) {
      const width = to - from;
      const start = clamp(anchor - Math.floor(width / 2), 0, last - width);
      showWindow(start, start + width);
      drag.current = { mode: "move", anchor, initial: [start, start + width] };
    } else {
      drag.current = { mode, anchor, initial: [from, to] };
    }
    e.currentTarget.setPointerCapture(e.pointerId);
    e.preventDefault();
  }
  function brushMove(e: PointerEvent<HTMLDivElement>) {
    if (!drag.current) return;
    const { mode, anchor, initial: [a, b] } = drag.current;
    const delta = overviewIndex(e.clientX) - anchor;
    if (mode === "start") showWindow(clamp(a + delta, 0, b - minimumSpan), b);
    else if (mode === "end") showWindow(a, clamp(b + delta, a + minimumSpan, last));
    else {
      const width = b - a;
      const start = clamp(a + delta, 0, last - width);
      showWindow(start, start + width);
    }
  }
  function brushEnd(e: PointerEvent<HTMLDivElement>) {
    drag.current = null;
    if (e.currentTarget.hasPointerCapture(e.pointerId))
      e.currentTarget.releasePointerCapture(e.pointerId);
  }
  function gripKey(e: KeyboardEvent<HTMLButtonElement>, side: "start" | "end") {
    const delta = e.key === "ArrowLeft" ? -1 :
      e.key === "ArrowRight" ? 1 :
      e.key === "PageDown" ? -5 :
      e.key === "PageUp" ? 5 : null;
    if (delta === null) return;
    e.preventDefault();
    if (side === "start") showWindow(clamp(from + delta, 0, to - minimumSpan), to);
    else showWindow(from, clamp(to + delta, from + minimumSpan, last));
  }
  function chartKey(e: KeyboardEvent<HTMLDivElement>) {
    const primaryKey = visibleLines[0]?.key;
    const primarySeries = primaryKey ? lineApiByKey.current.get(primaryKey) : undefined;
    if (!data.length || !primarySeries) return;
    if (e.key === "Escape") {
      setHover(null);
      chartApi.current?.clearCrosshairPosition();
      return;
    }
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(e.key)) return;
    e.preventDefault();
    const old = hover ? data.findIndex(row => row.date === hover.date) : to;
    const index = e.key === "Home" ? from :
      e.key === "End" ? to :
      clamp(old + (e.key === "ArrowLeft" ? -1 : 1), from, to);
    const row = data[index];
    chartApi.current?.setCrosshairPosition(
      seriesValue(row, primaryKey), row.date as Time, primarySeries,
    );
  }
  const overviewX = (idx: number) => last === 0 ? 0 : idx * OVERVIEW_WIDTH / last;
  const overviewY = (n: number) =>
    5 + (100 - clamp(n, 0, 100)) * (OVERVIEW_HEIGHT - 10) / 100;
  const overviewPath = (key: string) =>
    data.map((row, idx) => {
      const value = seriesValue(row, key);
      return Number.isFinite(value)
        ? `${idx ? "L" : "M"}${overviewX(idx).toFixed(2)},${overviewY(value).toFixed(2)}`
        : "";
    }).join(" ");

  if (!data.length) return <div className="empty-plot">Chưa có dữ liệu độ rộng thị trường</div>;

  return <div className="breadth-interactive">
    <div className="breadth-range-tools">
      <div className="breadth-presets" role="group" aria-label="Khoảng thời gian">
        {([{ label: "3T", days: 90 }, { label: "6T", days: 182 },
          { label: "1N", days: 365 }, { label: "2N", days: "all" }] as const).map(preset =>
          <button type="button" key={preset.label} onClick={() => zoomPreset(preset.days)}
            className={preset.days === "all" && from === 0 && to === last ? "active" : ""}
            aria-label={preset.label === "2N" ? "Xem toàn bộ 2 năm" : `Xem ${preset.label} gần nhất`}>
            {preset.label}
          </button>)}
      </div>
      <span className="breadth-visible-dates">
        {displayDate(data[from].date)} – {displayDate(data[to].date)}
        <small> ({to - from + 1} điểm)</small>
      </span>
    </div>

    <div className="breadth-series-filters" role="group" aria-label="Chọn các đường MA hiển thị">
      {series.map(line => {
        const enabled = visibleKeys.includes(line.key);
        return <button type="button" key={line.key}
          className={enabled ? "breadth-series-toggle active" : "breadth-series-toggle"}
          aria-pressed={enabled} aria-label={line.label}
          onClick={() => toggleLine(line.key)}
          title={enabled && visibleKeys.length === 1 ? "Giữ ít nhất một đường" : undefined}>
          <span className="breadth-series-check" aria-hidden="true">{enabled ? "✓" : ""}</span>
          <i style={{ background: line.color }} aria-hidden="true"/>
          {line.label}
        </button>;
      })}
    </div>
    <div className="breadth-inspector" role="status" aria-live="off">
      <div className="breadth-inspector-date">
        <small>{hover ? "Ngày đang trỏ" : "Ngày cuối khoảng chọn"}</small>
        <strong>{displayDate((hover?.row ?? data[to]).date)}</strong>
      </div>
      <div className="breadth-inspector-values">
        {visibleLines.map(line => <span key={line.key} className="breadth-inspector-value">
          <i style={{ background: line.color }} aria-hidden="true"/>
          <span>{line.label}</span>
          <b>{seriesValue(hover?.row ?? data[to], line.key).toFixed(1)}%</b>
        </span>)}
      </div>
    </div>
    <div className="breadth-chart-stage">
      <div className="breadth-lightweight-chart" ref={chartContainer} role="img"
        tabIndex={0} onKeyDown={chartKey}
        aria-label="Biểu đồ tỷ lệ MA. Kéo trục thời gian ở dưới để co giãn X, kéo thang phần trăm bên phải để co giãn Y. Kéo biểu đồ để dịch chuyển; "/>
    </div>
    <div className="breadth-navigator-title"><span>Chọn khoảng thời gian</span></div>
    <div className="breadth-overview" ref={overview}
      onPointerDown={brushDown} onPointerMove={brushMove}
      onPointerUp={brushEnd} onPointerCancel={brushEnd}
      onLostPointerCapture={() => { drag.current = null; }}>
      <svg viewBox={`0 0 ${OVERVIEW_WIDTH} ${OVERVIEW_HEIGHT}`} aria-hidden="true"
        preserveAspectRatio="none">
        {visibleLines.map(line => <path key={line.key} d={overviewPath(line.key)}
          fill="none" stroke={line.color} strokeWidth={1.5} opacity={0.8}/>)}
      </svg>
      <div className="breadth-viewport" data-brush-action="move"
        style={{ left: `${last ? 100 * from / last : 0}%`,
          width: `${last ? 100 * (to - from) / last : 100}%` }}
        title="Kéo để dịch chuyển khoảng thời gian">
        <button type="button" data-brush-action="start" className="breadth-grip start"
          role="slider" aria-label="Thời điểm bắt đầu" onKeyDown={e => gripKey(e, "start")}
          aria-valuemin={0} aria-valuemax={Math.max(0, to - minimumSpan)}
          aria-valuenow={from} aria-valuetext={displayDate(data[from].date)}/>
        <button type="button" data-brush-action="end" className="breadth-grip end"
          role="slider" aria-label="Thời điểm kết thúc" onKeyDown={e => gripKey(e, "end")}
          aria-valuemin={Math.min(last, from + minimumSpan)} aria-valuemax={last}
          aria-valuenow={to} aria-valuetext={displayDate(data[to].date)}/>
      </div>
    </div>
    <div className="breadth-overview-dates">
      <span>{displayDate(data[0].date)}</span>
      <span>{displayDate(data[last].date)}</span>
    </div>
    <div className="breadth-tradingview-attribution">
      Biểu đồ sử dụng Lightweight Charts™ của <a href="https://www.tradingview.com/"
        target="_blank" rel="noopener noreferrer">TradingView</a>
    </div>
  </div>;
}
