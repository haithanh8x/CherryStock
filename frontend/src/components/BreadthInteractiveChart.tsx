import { useEffect, useRef, useState } from "react";
import type { KeyboardEvent, PointerEvent } from "react";
import type { BreadthPoint } from "../data/types";
import "./BreadthInteractiveChart.css";

type Line = { key: string; label: string; color: string };
type DragMode = "start" | "end" | "move";

const PLOT_WIDTH = 840;
const PLOT_HEIGHT = 282;
const LEFT = 45;
const RIGHT = 17;
const TOP = 17;
const BOTTOM = 39;
const PLOT_SPAN = PLOT_WIDTH - LEFT - RIGHT;
const OVERVIEW_HEIGHT = 64;

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function displayDate(iso: string): string {
  const [year, month, day] = iso.split("-");
  return day && month && year ? `${day}/${month}/${year}` : iso;
}

export function BreadthInteractiveChart({
  data, series,
}: {
  data: BreadthPoint[];
  series: Line[];
}) {
  const [range, setRange] = useState<[number, number]>([0, Math.max(0, data.length - 1)]);
  const [hover, setHover] = useState<number | null>(null);
  const overviewRef = useRef<HTMLDivElement>(null);
  const dragRef = useRef<{
    mode: DragMode;
    anchor: number;
    initial: [number, number];
  } | null>(null);

  const last = Math.max(0, data.length - 1);
  const start = clamp(range[0], 0, last);
  const end = clamp(range[1], start, last);
  const visible = data.slice(start, end + 1);
  const minSpan = Math.min(last, 5);

  useEffect(() => {
    setRange([0, Math.max(0, data.length - 1)]);
    setHover(null);
  }, [data]);

  function zoomToDays(days: number | "all") {
    if (!data.length) return;
    if (days === "all") {
      setRange([0, last]);
    } else {
      const endDate = new Date(data[last].date + "T00:00:00Z");
      endDate.setUTCDate(endDate.getUTCDate() - days);
      const cutoff = endDate.toISOString().slice(0, 10);
      const index = data.findIndex(row => row.date >= cutoff);
      setRange([clamp(index < 0 ? 0 : index, 0, Math.max(0, last - minSpan)), last]);
    }
    setHover(null);
  }

  function chartIndex(e: PointerEvent<SVGSVGElement>): number {
    const rect = e.currentTarget.getBoundingClientRect();
    const chartX = (e.clientX - rect.left) / rect.width * PLOT_WIDTH;
    const position = clamp((chartX - LEFT) / PLOT_SPAN, 0, 1);
    return Math.round(position * Math.max(0, visible.length - 1));
  }

  function onChartKey(e: KeyboardEvent<SVGSVGElement>) {
    if (!visible.length) return;
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(e.key)) return;
    e.preventDefault();
    setHover(previous => {
      if (e.key === "Home") return 0;
      if (e.key === "End") return visible.length - 1;
      return clamp((previous ?? visible.length - 1) + (e.key === "ArrowLeft" ? -1 : 1), 0, visible.length - 1);
    });
  }

  function overviewIndex(clientX: number): number {
    const rect = overviewRef.current?.getBoundingClientRect();
    if (!rect || rect.width <= 0) return 0;
    return Math.round(clamp((clientX - rect.left) / rect.width, 0, 1) * last);
  }

  function onOverviewDown(e: PointerEvent<HTMLDivElement>) {
    if (last === 0) return;
    const target = e.target as HTMLElement;
    const action = target.closest("[data-brush-action]")?.getAttribute("data-brush-action") as DragMode | null;
    const index = overviewIndex(e.clientX);
    if (!action) {
      // Clicking the overview jumps the currently selected range to that date.
      const span = end - start;
      const left = clamp(index - Math.floor(span / 2), 0, last - span);
      const next: [number, number] = [left, left + span];
      setRange(next);
      dragRef.current = { mode: "move", anchor: index, initial: next };
    } else {
      dragRef.current = { mode: action, anchor: index, initial: [start, end] };
    }
    e.currentTarget.setPointerCapture(e.pointerId);
    e.preventDefault();
    setHover(null);
  }

  function onOverviewMove(e: PointerEvent<HTMLDivElement>) {
    const drag = dragRef.current;
    if (!drag) return;
    const shift = overviewIndex(e.clientX) - drag.anchor;
    const [a, b] = drag.initial;
    if (drag.mode === "start") {
      setRange([clamp(a + shift, 0, b - minSpan), b]);
    } else if (drag.mode === "end") {
      setRange([a, clamp(b + shift, a + minSpan, last)]);
    } else {
      const span = b - a;
      const left = clamp(a + shift, 0, last - span);
      setRange([left, left + span]);
    }
  }

  function onOverviewEnd(e: PointerEvent<HTMLDivElement>) {
    dragRef.current = null;
    if (e.currentTarget.hasPointerCapture(e.pointerId)) {
      e.currentTarget.releasePointerCapture(e.pointerId);
    }
  }

  function onHandleKey(e: KeyboardEvent<HTMLButtonElement>, side: "start" | "end") {
    const amount = e.key === "ArrowLeft" ? -1 :
      e.key === "ArrowRight" ? 1 :
      e.key === "PageDown" ? -5 :
      e.key === "PageUp" ? 5 : null;
    if (amount === null) return;
    e.preventDefault();
    if (side === "start") setRange([clamp(start + amount, 0, end - minSpan), end]);
    else setRange([start, clamp(end + amount, start + minSpan, last)]);
    setHover(null);
  }

  if (!visible.length) {
    return <div className="empty-plot">Chưa có dữ liệu độ rộng thị trường</div>;
  }

  const px = (index: number) => LEFT +
    (visible.length <= 1 ? PLOT_SPAN / 2 : index * PLOT_SPAN / (visible.length - 1));
  const py = (value: number) => TOP + (100 - clamp(value, 0, 100)) *
    (PLOT_HEIGHT - TOP - BOTTOM) / 100;
  const ovx = (index: number) => last <= 0 ? 0 : index * PLOT_WIDTH / last;
  const ovy = (value: number) => 5 + (100 - clamp(value, 0, 100)) * (OVERVIEW_HEIGHT - 10) / 100;
  const value = (point: BreadthPoint, key: string) =>
    Number((point as unknown as Record<string, number | string>)[key]);

  const mainPath = (key: string) => visible.map((point, index) => {
    const n = value(point, key);
    return Number.isFinite(n) ? `${index ? "L" : "M"}${px(index).toFixed(2)},${py(n).toFixed(2)}` : "";
  }).join(" ");
  const overviewPath = (key: string) => data.map((point, index) => {
    const n = value(point, key);
    return Number.isFinite(n) ? `${index ? "L" : "M"}${ovx(index).toFixed(2)},${ovy(n).toFixed(2)}` : "";
  }).join(" ");

  const active = hover !== null && hover < visible.length ? visible[hover] : null;
  const tooltipLeft = active && hover !== null
    ? clamp(100 * px(hover) / PLOT_WIDTH, 17, 83) : 50;

  const ticks = Array.from({ length: 5 }, (_, index) =>
    Math.round(index * (visible.length - 1) / 4))
    .filter((idx, pos, list) => list.indexOf(idx) === pos);

  return <div className="breadth-interactive">
    <div className="breadth-range-tools">
      <div className="breadth-presets" role="group" aria-label="Khoảng thời gian">
        {([{ label: "3T", days: 90 }, { label: "6T", days: 182 },
          { label: "1N", days: 365 }, { label: "2N", days: "all" }] as const).map(preset =>
          <button type="button" key={preset.label} onClick={() => zoomToDays(preset.days)}
            className={preset.days === "all" && start === 0 && end === last ? "active" : ""}
            aria-label={preset.label === "2N" ? "Xem toàn bộ 2 năm" : `Xem ${preset.label} gần nhất`}>
            {preset.label}
          </button>)}
      </div>
      <span className="breadth-visible-dates">
        {displayDate(data[start].date)} – {displayDate(data[end].date)}
        <small> ({visible.length} điểm)</small>
      </span>
    </div>

    <div className="breadth-chart-stage">
      <svg className="breadth-chart-svg" viewBox={`0 0 ${PLOT_WIDTH} ${PLOT_HEIGHT}`}
        aria-label="Đồ thị độ rộng thị trường. Rê chuột hoặc chạm để xem ngày và tỷ lệ từng đường MA; dùng phím trái phải khi có tiêu điểm."
        role="img" tabIndex={0}
        onPointerMove={e => setHover(chartIndex(e))}
        onPointerDown={e => setHover(chartIndex(e))}
        onPointerLeave={e => { if (e.pointerType === "mouse") setHover(null); }}
        onKeyDown={onChartKey}>
        {[0, 25, 50, 75, 100].map(n => <g key={n}>
          <line x1={LEFT} y1={py(n)} x2={PLOT_WIDTH - RIGHT} y2={py(n)}
            stroke="var(--border)" strokeDasharray="4 4"/>
          <text className="chart-label" x={LEFT - 8} y={py(n) + 4} textAnchor="end">{n}%</text>
        </g>)}
        {ticks.map(index => <text key={index} className="chart-label"
          x={px(index)} y={PLOT_HEIGHT - 9}
          textAnchor={index === 0 ? "start" : index === visible.length - 1 ? "end" : "middle"}>
          {displayDate(visible[index].date)}
        </text>)}
        {series.map(line => <path key={line.key} d={mainPath(line.key)} fill="none"
          stroke={line.color} strokeWidth={line.key === "ma20" ? 2.4 : 1.8}
          strokeLinejoin="round" strokeLinecap="round"/>)}
        {active && hover !== null && <>
          <line x1={px(hover)} x2={px(hover)} y1={TOP} y2={PLOT_HEIGHT - BOTTOM}
            className="breadth-crosshair"/>
          {series.map(line => <circle key={line.key} cx={px(hover)}
            cy={py(value(active, line.key))} r={4.1} fill={line.color}
            stroke="var(--surface)" strokeWidth={1.8}/>)}
        </>}
      </svg>
      {active && <div className="breadth-tooltip" role="status" aria-live="off"
        style={{ left: `clamp(112px, ${tooltipLeft}%, calc(100% - 112px))` }}>
        <strong>{displayDate(active.date)}</strong>
        <div className="breadth-tooltip-values">
          {series.map(line => <span key={line.key}>
            <i style={{ background: line.color }}/>
            <span>{line.label}</span>
            <b>{value(active, line.key).toFixed(1)}%</b>
          </span>)}
        </div>
      </div>}
    </div>

    <div className="breadth-navigator-title">
      <span>Chọn khoảng thời gian</span>
      <span>Kéo hai mép để thu phóng · Kéo vùng giữa để dịch chuyển</span>
    </div>
    <div className="breadth-overview" ref={overviewRef}
      onPointerDown={onOverviewDown} onPointerMove={onOverviewMove}
      onPointerUp={onOverviewEnd} onPointerCancel={onOverviewEnd}
      onLostPointerCapture={() => { dragRef.current = null; }}>
      <svg viewBox={`0 0 ${PLOT_WIDTH} ${OVERVIEW_HEIGHT}`} aria-hidden="true"
        preserveAspectRatio="none">
        {series.map(line => <path key={line.key} d={overviewPath(line.key)}
          fill="none" stroke={line.color} strokeWidth={1.5} opacity={0.8}/>)}
      </svg>
      <div className="breadth-viewport"
        style={{ left: `${last ? 100 * start / last : 0}%`,
          width: `${last ? 100 * (end - start) / last : 100}%` }}
        data-brush-action="move" title="Kéo để dịch chuyển cửa sổ thời gian">
        <button type="button" data-brush-action="start" className="breadth-grip start"
          role="slider" tabIndex={0} aria-label="Thời điểm bắt đầu"
          aria-valuemin={0} aria-valuemax={Math.max(0, end - minSpan)}
          aria-valuenow={start} aria-valuetext={displayDate(data[start].date)}
          onKeyDown={e => onHandleKey(e, "start")}/>
        <button type="button" data-brush-action="end" className="breadth-grip end"
          role="slider" tabIndex={0} aria-label="Thời điểm kết thúc"
          aria-valuemin={Math.min(last, start + minSpan)} aria-valuemax={last}
          aria-valuenow={end} aria-valuetext={displayDate(data[end].date)}
          onKeyDown={e => onHandleKey(e, "end")}/>
      </div>
    </div>
    <div className="breadth-overview-dates">
      <span>{displayDate(data[0].date)}</span>
      <span>{displayDate(data[last].date)}</span>
    </div>
  </div>;
}
