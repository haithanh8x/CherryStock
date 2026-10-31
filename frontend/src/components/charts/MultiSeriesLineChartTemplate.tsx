import { useEffect, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import {
  ColorType, CrosshairMode, LineSeries, createChart,
  type IChartApi, type ISeriesApi, type LogicalRange,
  type MouseEventParams, type Time,
} from "lightweight-charts";
import "./MultiSeriesLineChartTemplate.css";

export type ChartLineDefinition = { key: string; label: string; color: string; width?: 1 | 2 | 3 | 4 };
export type ChartDataPoint = { date: string };
type WindowRange = [number, number];
type HoverPoint = { date: string; row: ChartDataPoint };

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
function seriesValue(row: ChartDataPoint, key: string): number {
  return Number((row as unknown as Record<string, number | string>)[key]);
}

export function MultiSeriesLineChartTemplate({
  data, series, valueSuffix = "%", allRangeLabel = "Tất cả",
  accessibleName = "Biểu đồ nhiều chuỗi dữ liệu",
}: {
  data: ChartDataPoint[];
  series: ChartLineDefinition[];
  valueSuffix?: string;
  allRangeLabel?: string;
  accessibleName?: string;
}) {
  const chartContainer = useRef<HTMLDivElement>(null);
  const chartApi = useRef<IChartApi | null>(null);
  const lineApiByKey = useRef<Map<string, ISeriesApi<"Line", Time>>>(new Map());
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

  // Native Lightweight Charts owns X/Y zoom and pan; range state mirrors the chart.
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
        lineWidth: line.width ?? 2,
        priceLineVisible: false,
        lastValueVisible: true,
        crosshairMarkerVisible: true,
        visible: visibleKeys.includes(line.key),
        priceFormat: {
          type: "custom",
          formatter: (v: number) => `${v.toFixed(1)}${valueSuffix}`,
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
  if (!data.length) return <div className="empty-plot">Chưa có dữ liệu để vẽ biểu đồ</div>;

  return <div className="breadth-interactive">
    <div className="breadth-range-tools">
      <div className="breadth-presets" role="group" aria-label="Khoảng thời gian">
        {([{ label: "3T", days: 90 }, { label: "6T", days: 182 },
          { label: "1N", days: 365 }, { label: allRangeLabel, days: "all" }] as const).map(preset =>
          <button type="button" key={preset.label} onClick={() => zoomPreset(preset.days)}
            className={preset.days === "all" && from === 0 && to === last ? "active" : ""}
            aria-label={preset.days === "all" ? "Xem toàn bộ dữ liệu" : `Xem ${preset.label} gần nhất`}>
            {preset.label}
          </button>)}
      </div>
      <span className="breadth-visible-dates">
        {displayDate(data[from].date)} – {displayDate(data[to].date)}
        <small> ({to - from + 1} điểm)</small>
      </span>
    </div>

    <div className="breadth-series-filters" role="group" aria-label="Chọn các đường dữ liệu hiển thị">
      {series.map(line => {
        const enabled = visibleKeys.includes(line.key);
        return <button type="button" key={line.key}
          className={enabled ? "breadth-series-toggle active" : "breadth-series-toggle"}
          aria-pressed={enabled} aria-label={line.label}
          onClick={() => toggleLine(line.key)}
          title={enabled && visibleKeys.length === 1 ? "Giữ ít nhất một đường" : undefined}>
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
          <b>{seriesValue(hover?.row ?? data[to], line.key).toFixed(1)}{valueSuffix}</b>
        </span>)}
      </div>
    </div>
    <div className="breadth-chart-stage">
      <div className="breadth-lightweight-chart" ref={chartContainer} role="img"
        tabIndex={0} onKeyDown={chartKey}
        aria-label={accessibleName}/>
    </div>
    <div className="breadth-tradingview-attribution">
      Biểu đồ sử dụng Lightweight Charts™ của <a href="https://www.tradingview.com/"
        target="_blank" rel="noopener noreferrer">TradingView</a>
    </div>
  </div>;
}
