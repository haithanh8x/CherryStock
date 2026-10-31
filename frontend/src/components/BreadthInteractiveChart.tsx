import type { BreadthPoint } from "../data/types";
import { MultiSeriesLineChartTemplate, type ChartLineDefinition } from "./charts/MultiSeriesLineChartTemplate";

// CherryStock's market-breadth preset for the reusable line-chart template.
export function BreadthInteractiveChart({
  data, series,
}: {
  data: BreadthPoint[];
  series: ChartLineDefinition[];
}) {
  return <MultiSeriesLineChartTemplate
    data={data}
    series={series}
    valueSuffix="%"
    allRangeLabel="2N"
    accessibleName="Biểu đồ độ rộng thị trường; kéo trục thời gian để co giãn X, kéo trục phần trăm để co giãn Y."
  />;
}
