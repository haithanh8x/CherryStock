from __future__ import annotations
from pathlib import Path
from datetime import date, datetime, timedelta
import asyncio
from contextlib import redirect_stderr, redirect_stdout
import importlib
import inspect
import io
import logging
from queue import Empty, Queue
import sys
import traceback
from random import Random
from time import perf_counter, time_ns
from duckdb import df
import pandas as pd
from typing import Any
from nicegui import ui

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from webapp import NiceGUI_grid_market_tb
importlib.reload(NiceGUI_grid_market_tb)
from webapp.NiceGUI_grid import create_market_grid
from DuckDB.Data import view_to_dataframe
from Ults.DuckLib import DuckDBManager
import Chart.plot as chart_plot
importlib.reload(chart_plot)
from calcEngine.levelLadder import build_level_ladder
import Chart.levelLadderChart as level_ladder_chart
importlib.reload(level_ladder_chart)
from Ults.lstPara import CHART_START_DATE, IFRAME_HEIGHT, THEME, TIMEFRAME_OPTIONS


CASHFLOW_UI_BUILD = "cashflow-tooltip-v3-20260801"
print(f"[CherryStock] Loaded {CASHFLOW_UI_BUILD} from {Path(__file__).resolve()}")
# =============================================================================
# Datagrid
# =============================================================================

def create_aggrid(df: pd.DataFrame) -> dict:
    row_data = (
        df.astype(object)
        .where(pd.notnull(df), None)
        .to_dict("records")
    )

    column_defs = []

    for col in df.columns:
        col_def = {
            "headerName": col.replace("_", " ").title(),
            "field": col,
            "sortable": True,
            "filter": True,
            "resizable": True,
            "floatingFilter": True,
        }
        # col_def.update(COLUMN_CONFIG.get(col, {}))
        # column_defs.append(col_def)

        # Numeric column
        if pd.api.types.is_numeric_dtype(df[col]):
            col_def["filter"] = "agNumberColumnFilter"
            col_def["width"] = 100

        # String column
        else:
            col_def["minWidth"] = 120
            col_def["flex"] = 1

        column_defs.append(col_def)

    options = {
        "columnDefs": column_defs,
        "rowData": row_data,
        "pagination": True,
        "paginationPageSize": 20,
    }

    return options

# =============================================================================
# Theme
# =============================================================================


rng = Random(2026)

# =============================================================================
# Mock data
# Replace these functions with DuckDB/Pandas queries in a real application.
# =============================================================================

def generate_ohlcv(days: int = 120, start_price: float = 100.0) -> list[dict[str, Any]]:
    """Generate deterministic OHLCV data for the demo."""
    start_date = date.today() - timedelta(days=days)
    price = start_price
    records: list[dict[str, Any]] = []

    for day_index in range(days):
        session_date = start_date + timedelta(days=day_index)
        open_price = price
        close_price = max(10.0, open_price + rng.uniform(-2.2, 2.6))
        high_price = max(open_price, close_price) + rng.uniform(0.2, 1.8)
        low_price = min(open_price, close_price) - rng.uniform(0.2, 1.8)

        records.append(
            {
                "date": session_date.isoformat(),
                "open": round(open_price, 2),
                "high": round(high_price, 2),
                "low": round(low_price, 2),
                "close": round(close_price, 2),
                "volume": rng.randint(1_800_000, 9_000_000),
            }
        )
        price = close_price

    return records


OHLCV = generate_ohlcv()

WATCHLIST_ROWS = [
    {"ticker": "FPT", "company": "FPT Corp", "price": 128.40, "change": 1.82, "volume": 5_482_100, "sector": "Công nghệ", "pe": 24.6, "rsi": 61.2},
    {"ticker": "VCB", "company": "Vietcombank", "price": 63.80, "change": -0.47, "volume": 2_103_400, "sector": "Ngân hàng", "pe": 15.1, "rsi": 48.5},
    {"ticker": "HPG", "company": "Hòa Phát", "price": 28.75, "change": 2.31, "volume": 32_452_700, "sector": "Thép", "pe": 13.8, "rsi": 66.4},
    {"ticker": "MWG", "company": "Thế Giới Di Động", "price": 67.20, "change": 0.75, "volume": 8_214_800, "sector": "Bán lẻ", "pe": 20.4, "rsi": 57.8},
    {"ticker": "VNM", "company": "Vinamilk", "price": 63.10, "change": -1.10, "volume": 4_621_300, "sector": "Tiêu dùng", "pe": 14.9, "rsi": 42.7},
    {"ticker": "SSI", "company": "SSI Securities", "price": 34.65, "change": 3.12, "volume": 41_654_900, "sector": "Chứng khoán", "pe": 17.2, "rsi": 70.1},
    {"ticker": "GAS", "company": "PV GAS", "price": 73.40, "change": -0.27, "volume": 1_240_500, "sector": "Năng lượng", "pe": 16.8, "rsi": 46.9},
    {"ticker": "VIC", "company": "Vingroup", "price": 47.90, "change": 1.05, "volume": 7_830_200, "sector": "Bất động sản", "pe": 31.5, "rsi": 54.2},
]

SCREENER_ROWS = [
    {**row, "ma20": round(row["price"] * rng.uniform(0.95, 1.04), 2), "ma50": round(row["price"] * rng.uniform(0.92, 1.07), 2)}
    for row in WATCHLIST_ROWS
]

PORTFOLIO_ROWS = [
    {"ticker": "FPT", "quantity": 2500, "avg_price": 112.30, "market_price": 128.40, "market_value": 321_000_000, "pnl": 40_250_000, "weight": 29.8},
    {"ticker": "VCB", "quantity": 3200, "avg_price": 58.20, "market_price": 63.80, "market_value": 204_160_000, "pnl": 17_920_000, "weight": 18.9},
    {"ticker": "HPG", "quantity": 7500, "avg_price": 25.10, "market_price": 28.75, "market_value": 215_625_000, "pnl": 27_375_000, "weight": 20.0},
    {"ticker": "MWG", "quantity": 2100, "avg_price": 61.70, "market_price": 67.20, "market_value": 141_120_000, "pnl": 11_550_000, "weight": 13.1},
    {"ticker": "VNM", "quantity": 3100, "avg_price": 66.40, "market_price": 63.10, "market_value": 195_610_000, "pnl": -10_230_000, "weight": 18.2},
]


# =============================================================================
# Formatting helpers
# =============================================================================

def format_compact(value: float) -> str:
    if abs(value) >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f}B"
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if abs(value) >= 1_000:
        return f"{value / 1_000:.1f}K"
    return f"{value:,.0f}"


# =============================================================================
# Apache ECharts option builders
# =============================================================================

def performance_chart_options() -> dict[str, Any]:
    dates = [row["date"] for row in OHLCV]
    closes = [row["close"] for row in OHLCV]

    ma20: list[float] = []
    for index in range(len(closes)):
        window = closes[max(0, index - 19): index + 1]
        ma20.append(round(sum(window) / len(window), 2))

    return {
        "backgroundColor": "transparent",
        "animation": False,
        "tooltip": {"trigger": "axis"},
        "legend": {
            "top": 4,
            "right": 8,
            "data": ["VN-Index", "MA20"],
            "textStyle": {"color": THEME["muted"]},
        },
        "grid": {"left": 54, "right": 24, "top": 48, "bottom": 55},
        "xAxis": {
            "type": "category",
            "boundaryGap": False,
            "data": dates,
            "axisLine": {"lineStyle": {"color": THEME["border"]}},
            "axisLabel": {"color": THEME["muted"], "hideOverlap": True},
        },
        "yAxis": {
            "type": "value",
            "scale": True,
            "axisLabel": {"color": THEME["muted"]},
            "splitLine": {"lineStyle": {"color": THEME["border"], "opacity": 0.45}},
        },
        "dataZoom": [
            {"type": "inside", "start": 45, "end": 100},
            {
                "type": "slider",
                "height": 18,
                "bottom": 10,
                "start": 45,
                "end": 100,
                "borderColor": THEME["border"],
                "backgroundColor": THEME["surface_alt"],
            },
        ],
        "series": [
            {
                "name": "VN-Index",
                "type": "line",
                "data": closes,
                "showSymbol": False,
                "smooth": True,
                "lineStyle": {"width": 2, "color": THEME["primary"]},
                "areaStyle": {"opacity": 0.08, "color": THEME["primary"]},
            },
            {
                "name": "MA20",
                "type": "line",
                "data": ma20,
                "showSymbol": False,
                "lineStyle": {"width": 1.5, "color": THEME["warning"]},
            },
        ],
    }


def candlestick_chart_options() -> dict[str, Any]:
    dates = [row["date"] for row in OHLCV]
    candle_data = [
        [row["open"], row["close"], row["low"], row["high"]]
        for row in OHLCV
    ]

    return {
        "backgroundColor": "transparent",
        "animation": False,
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "cross"}},
        "grid": {"left": 54, "right": 24, "top": 26, "bottom": 58},
        "xAxis": {
            "type": "category",
            "data": dates,
            "boundaryGap": True,
            "axisLine": {"lineStyle": {"color": THEME["border"]}},
            "axisLabel": {"color": THEME["muted"], "hideOverlap": True},
        },
        "yAxis": {
            "type": "value",
            "scale": True,
            "axisLabel": {"color": THEME["muted"]},
            "splitLine": {"lineStyle": {"color": THEME["border"], "opacity": 0.45}},
        },
        "dataZoom": [
            {"type": "inside", "start": 55, "end": 100},
            {
                "type": "slider",
                "height": 18,
                "bottom": 10,
                "start": 55,
                "end": 100,
                "borderColor": THEME["border"],
                "backgroundColor": THEME["surface_alt"],
            },
        ],
        "series": [
            {
                "name": "VN-Index",
                "type": "candlestick",
                "data": candle_data,
                "itemStyle": {
                    "color": THEME["positive"],
                    "color0": THEME["negative"],
                    "borderColor": THEME["positive"],
                    "borderColor0": THEME["negative"],
                },
            }
        ],
    }


def sector_chart_options() -> dict[str, Any]:
    sectors = ["Công nghệ", "Chứng khoán", "Thép", "Ngân hàng", "Bán lẻ", "Năng lượng"]
    performance = [3.4, 2.8, 1.9, 0.7, -0.4, -1.1]

    return {
        "backgroundColor": "transparent",
        "grid": {"left": 96, "right": 32, "top": 20, "bottom": 28},
        "xAxis": {
            "type": "value",
            "axisLabel": {"color": THEME["muted"], "formatter": "{value}%"},
            "splitLine": {"lineStyle": {"color": THEME["border"], "opacity": 0.45}},
        },
        "yAxis": {
            "type": "category",
            "data": sectors,
            "axisLabel": {"color": THEME["muted"]},
            "axisLine": {"show": False},
            "axisTick": {"show": False},
        },
        "series": [
            {
                "type": "bar",
                "barWidth": 18,
                "data": [
                    {
                        "value": value,
                        "itemStyle": {
                            "color": THEME["positive"] if value >= 0 else THEME["negative"],
                            "borderRadius": 5,
                        },
                    }
                    for value in performance
                ],
                "label": {
                    "show": True,
                    "position": "right",
                    "formatter": "{c}%",
                    "color": THEME["text"],
                },
            }
        ],
    }


def breadth_chart_options() -> dict[str, Any]:
    labels = ["Trên MA20", "Trên MA50", "Trên MA100", "Trên MA200"]
    values = [68, 61, 54, 47]

    return {
        "backgroundColor": "transparent",
        "grid": {"left": 48, "right": 20, "top": 25, "bottom": 44},
        "xAxis": {
            "type": "category",
            "data": labels,
            "axisLabel": {"color": THEME["muted"], "interval": 0},
            "axisLine": {"lineStyle": {"color": THEME["border"]}},
        },
        "yAxis": {
            "type": "value",
            "max": 100,
            "axisLabel": {"color": THEME["muted"], "formatter": "{value}%"},
            "splitLine": {"lineStyle": {"color": THEME["border"], "opacity": 0.45}},
        },
        "series": [
            {
                "type": "bar",
                "barWidth": "42%",
                "data": values,
                "itemStyle": {
                    "color": THEME["primary"],
                    "borderRadius": [6, 6, 0, 0],
                },
                "label": {
                    "show": True,
                    "position": "top",
                    "formatter": "{c}%",
                    "color": THEME["text"],
                },
            }
        ],
    }


def allocation_chart_options() -> dict[str, Any]:
    return {
        "backgroundColor": "transparent",
        "tooltip": {"trigger": "item", "formatter": "{b}: {c}%"},
        "legend": {
            "bottom": 0,
            "textStyle": {"color": THEME["muted"]},
        },
        "series": [
            {
                "type": "pie",
                "radius": ["52%", "76%"],
                "center": ["50%", "43%"],
                "label": {"show": False},
                "data": [
                    {"name": "Công nghệ", "value": 29.8},
                    {"name": "Ngân hàng", "value": 18.9},
                    {"name": "Thép", "value": 20.0},
                    {"name": "Bán lẻ", "value": 13.1},
                    {"name": "Tiêu dùng", "value": 18.2},
                ],
            }
        ],
    }


# =============================================================================
# Reusable UI components
# =============================================================================




def card_classes(extra: str = "") -> str:
    return (
        "dashboard-card rounded-2xl border shadow-sm min-w-0 "
        f"bg-[{THEME['surface']}] border-[{THEME['border']}] {extra}"
    )


def metric_card(
    title: str,
    value: str,
    change: str,
    *,
    positive: bool,
    icon: str,
) -> None:
    change_color = THEME["positive"] if positive else THEME["negative"]
    trend_icon = "north_east" if positive else "south_east"

    with ui.card().classes(card_classes("metric-card p-4 hover:-translate-y-0.5 transition-transform")):
        with ui.row().classes("w-full items-start justify-between no-wrap gap-3"):
            with ui.column().classes("gap-1 min-w-0"):
                ui.label(title).classes(f"text-xs uppercase tracking-wider text-[{THEME['muted']}]")
                ui.label(value).classes(f"text-xl xl:text-2xl font-bold text-[{THEME['text']}] truncate")
                with ui.row().classes("items-center gap-1 no-wrap"):
                    ui.icon(trend_icon).classes(f"text-sm text-[{change_color}]")
                    ui.label(change).classes(f"text-xs font-medium text-[{change_color}] truncate")
            ui.icon(icon).classes(
                f"text-xl text-[{THEME['primary']}] bg-[{THEME['surface_alt']}] "
                "rounded-xl p-2.5 shrink-0"
            )


def section_title(title: str, subtitle: str | None = None) -> None:
    with ui.column().classes("gap-0 min-w-0"):
        ui.label(title).classes("text-base md:text-lg font-semibold truncate")
        if subtitle:
            ui.label(subtitle).classes(f"text-xs md:text-sm text-[{THEME['muted']}] truncate")


def card_header(
    title: str,
    subtitle: str | None = None,
    *,
    icon: str | None = None,
) -> None:
    with ui.row().classes("w-full items-center justify-between gap-3 no-wrap"):
        with ui.row().classes("items-center gap-3 min-w-0 no-wrap"):
            if icon:
                ui.icon(icon).classes(
                    f"text-lg text-[{THEME['primary']}] bg-[{THEME['surface_alt']}] rounded-lg p-2"
                )
            section_title(title, subtitle)


def create_watchlist_grid() -> ui.aggrid:
    options = {
        "defaultColDef": {"sortable": True, "resizable": True},
        "columnDefs": [
            {"headerName": "Mã", "field": "ticker", "pinned": "left", "width": 82},
            {"headerName": "Giá", "field": "price", "width": 92,
             ":valueFormatter": "params => params.value.toLocaleString('vi-VN', {minimumFractionDigits: 2})"},
            {"headerName": "%", "field": "change", "width": 88,
             ":valueFormatter": "params => `${params.value > 0 ? '+' : ''}${params.value.toFixed(2)}%`",
             ":cellStyle": (
                 f"params => params.value >= 0 ? {{color: '{THEME['positive']}', fontWeight: 700}} "
                 f": {{color: '{THEME['negative']}', fontWeight: 700}}"
             )},
        ],
        "rowData": WATCHLIST_ROWS,
        "rowSelection": {"mode": "singleRow"},
        "animateRows": True,
        "headerHeight": 36,
        "rowHeight": 38,
    }
    return ui.aggrid(options, theme="quartz", auto_size_columns=False).classes("w-full h-[350px]")


def create_portfolio_grid() -> ui.aggrid:
    options = {
        "defaultColDef": {"sortable": True, "filter": True, "resizable": True},
        "columnDefs": [
            {"headerName": "Mã", "field": "ticker", "pinned": "left", "width": 90},
            {"headerName": "Khối lượng", "field": "quantity", "width": 120,
             ":valueFormatter": "params => params.value.toLocaleString('vi-VN')"},
            {"headerName": "Giá vốn", "field": "avg_price", "width": 110},
            {"headerName": "Giá thị trường", "field": "market_price", "width": 135},
            {"headerName": "Giá trị", "field": "market_value", "minWidth": 145,
             ":valueFormatter": "params => params.value.toLocaleString('vi-VN')"},
            {"headerName": "Lãi/Lỗ", "field": "pnl", "minWidth": 135,
             ":valueFormatter": "params => params.value.toLocaleString('vi-VN')",
             ":cellStyle": (
                 f"params => params.value >= 0 ? {{color: '{THEME['positive']}', fontWeight: 700}} "
                 f": {{color: '{THEME['negative']}', fontWeight: 700}}"
             )},
            {"headerName": "Tỷ trọng", "field": "weight", "width": 110,
             ":valueFormatter": "params => `${params.value.toFixed(1)}%`"},
        ],
        "rowData": PORTFOLIO_ROWS,
        "animateRows": True,
    }
    return ui.aggrid(options, theme="quartz", auto_size_columns=False).classes(
        "w-full h-[390px] dashboard-data-grid"
    )



def get_investor_cashflow(
    start_date: str | None = None,
    timeframe: str = "daily",
) -> pd.DataFrame:
    """Lấy chuỗi thời gian mua/bán ròng theo nhóm nhà đầu tư."""
    normalized = str(timeframe).strip().lower()
    aliases = {
        "daily": "daily", "day": "daily", "1d": "daily",
        "weekly": "weekly", "week": "weekly", "1w": "weekly",
        "monthly": "monthly", "month": "monthly", "1m": "monthly",
    }
    if normalized not in aliases:
        raise ValueError("timeframe phải là daily, weekly hoặc monthly")
    normalized = aliases[normalized]

    conditions: list[str] = []
    parameters: list[object] = []
    if start_date:
        conditions.append('"Date" >= CAST(? AS DATE)')
        parameters.append(start_date)

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    sql = f"""
        SELECT
            "Date" AS time,
            SUM(COALESCE("AC_NetVal", 0)) / 1000000000.0 AS institutional,
            SUM(COALESCE("CC_NetVal", 0)) / 1000000000.0 AS individual,
            SUM(COALESCE("NN_NetVal", 0)) / 1000000000.0 AS foreign_flow,
            SUM(COALESCE("TD_NetVal", 0)) / 1000000000.0 AS proprietary
        FROM "CherryMon"."main"."vw_ACCCNNTD_Price"
        {where_clause}
        GROUP BY "Date"
        ORDER BY "Date"
    """

    with DuckDBManager(read_only=True) as connection:
        df = connection.execute(sql, parameters).df()
    columns = ["time", "institutional", "individual", "foreign_flow", "proprietary"]
    if df.empty:
        return pd.DataFrame(columns=columns)

    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    numeric_columns = columns[1:]
    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0.0)

    df = (
        df.dropna(subset=["time"])
        .sort_values("time")
        .drop_duplicates(subset=["time"], keep="last")
        .reset_index(drop=True)
    )

    if normalized != "daily":
        frequency = "W-FRI" if normalized == "weekly" else "ME"
        df = (
            df.set_index("time")[numeric_columns]
            .resample(frequency)
            .sum(min_count=1)
            .fillna(0.0)
            .reset_index()
        )

    return df[columns]


def get_cashflow_cumulative_summary(
    timeframe: str = "daily",
    start_date: str | None = None,
) -> dict[str, float]:
    """Tính dòng tiền lũy kế trên toàn bộ dữ liệu đang được lọc."""
    df = get_investor_cashflow(start_date=start_date, timeframe=timeframe)
    columns = {
        "institutional": "Tổ chức",
        "individual": "Cá nhân",
        "foreign_flow": "Nước ngoài",
        "proprietary": "Tự doanh",
    }
    if df.empty:
        return {label: 0.0 for label in columns.values()}
    return {
        label: float(df[column].sum())
        for column, label in columns.items()
    }


def build_investor_cashflow_chart(
    timeframe: str = "daily",
    start_date: str | None = None,
):
    """Tạo lightweight chart cho dòng tiền theo nhóm nhà đầu tư."""
    df = get_investor_cashflow(
        start_date=start_date,
        timeframe=timeframe,
    )
    if df.empty:
        return None, df

    chart_df = df.copy()
    chart_df["time"] = (
        pd.to_datetime(chart_df["time"], errors="coerce")
        .dt.strftime("%Y-%m-%d")
    )
    chart_df = chart_df.dropna(subset=["time"]).reset_index(drop=True)
    if chart_df.empty:
        return None, chart_df

    chart = chart_plot.init_chart(
        height=500,
        inner_width=1,
        inner_height=1,
        background_color=THEME["surface"],
        text_color=THEME["text"],
        legend_visible=True,
    )

    series_config = (
        ("Tổ chức", "institutional", "#38bdf8"),
        ("Cá nhân", "individual", "#f59e0b"),
        ("Nước ngoài", "foreign_flow", "#22c55e"),
        ("Tự doanh", "proprietary", "#ef4444"),
    )

    created_lines = []
    for label, column, color in series_config:
        line = chart_plot.add_line(
            chart=chart,
            data=chart_df[["time", column]],
            name=column,
            label_name=label,
            color=color,
            width=2,
            price_line=False,
            price_label=False,
        )
        created_lines.append(line)

    # Đường mức 0 dùng price line thay vì một series riêng để không xuất hiện
    # trong legend. lineStyle=2 tương ứng nét đứt của Lightweight Charts.
    if created_lines:
        zero_anchor = created_lines[0]
        chart.run_script(
            f"""
            if ({zero_anchor.id} && {zero_anchor.id}.series) {{
                {zero_anchor.id}.series.createPriceLine({{
                    price: 0,
                    color: 'rgba(143, 163, 189, 0.24)',
                    lineWidth: 1,
                    lineStyle: 2,
                    axisLabelVisible: false,
                    title: ''
                }});
            }}
            """
        )

    normalized = str(timeframe).strip().lower()
    bar_spacing = {
        "daily": 6,
        "weekly": 10,
        "monthly": 16,
    }.get(normalized, 6)

    chart.run_script(
        f"""
        {chart.id}.chart.applyOptions({{
            layout: {{
                background: {{type: 'solid', color: '{THEME["surface"]}'}},
                textColor: '{THEME["muted"]}'
            }},
            grid: {{
                vertLines: {{color: 'rgba(38, 55, 80, 0.35)'}},
                horzLines: {{color: 'rgba(38, 55, 80, 0.50)'}}
            }},
            crosshair: {{
                vertLine: {{color: 'rgba(143, 163, 189, 0.55)', width: 1, style: 2}},
                horzLine: {{color: 'rgba(143, 163, 189, 0.35)', width: 1, style: 2}}
            }},
            rightPriceScale: {{
                borderColor: '{THEME["border"]}',
                scaleMargins: {{top: 0.12, bottom: 0.12}}
            }},
            timeScale: {{
                borderColor: '{THEME["border"]}',
                timeVisible: false,
                secondsVisible: false,
                barSpacing: {bar_spacing},
                rightOffset: 2,
                fixLeftEdge: true,
                fixRightEdge: true
            }}
        }});
        """
    )

    # Cài tooltip sau khi Lightweight Charts đã khởi tạo xong. Dùng cơ chế retry
    # vì script có thể được thực thi trước khi handler/series sẵn sàng trong iframe.
    series_meta_js = ",\n".join(
        f"{{series: {line.id}.series, label: {label!r}, color: {color!r}}}"
        for line, (label, _, color) in zip(created_lines, series_config)
    )

    chart.run_script(
        f"""
        (function installCashflowPointTooltip(attempt) {{
            attempt = attempt || 0;

            const handler = (typeof {chart.id} !== 'undefined') ? {chart.id} : null;
            const seriesReady = [
                {series_meta_js}
            ].every(function(item) {{
                return item.series && typeof item.series.applyOptions === 'function';
            }});

            if (!handler || !handler.chart || !handler.wrapper || !seriesReady) {{
                if (attempt < 80) {{
                    setTimeout(function() {{
                        installCashflowPointTooltip(attempt + 1);
                    }}, 50);
                }}
                return;
            }}

            if (handler.__cashflowPointTooltipInstalled) return;
            handler.__cashflowPointTooltipInstalled = true;

            console.info('[CherryStock] cashflow tooltip installed', {{
                chartId: {chart.id!r},
                attempt: attempt
            }});

            const seriesMeta = [
                {series_meta_js}
            ];

            seriesMeta.forEach(function(item) {{
                item.series.applyOptions({{
                    crosshairMarkerVisible: true,
                    crosshairMarkerRadius: 5,
                    crosshairMarkerBorderWidth: 2,
                    crosshairMarkerBorderColor: item.color,
                    crosshairMarkerBackgroundColor: '#FFFFFF'
                }});
            }});

            handler.wrapper.style.position = 'relative';

            let tooltip = handler.wrapper.querySelector('.cashflow-point-tooltip');
            if (!tooltip) {{
                tooltip = document.createElement('div');
                tooltip.className = 'cashflow-point-tooltip';
                Object.assign(tooltip.style, {{
                    position: 'absolute',
                    top: '48px',
                    right: '14px',
                    zIndex: '99999',
                    display: 'none',
                    minWidth: '210px',
                    padding: '10px 12px',
                    border: '1px solid rgba(143, 163, 189, 0.42)',
                    borderRadius: '8px',
                    background: 'rgba(7, 17, 31, 0.97)',
                    boxShadow: '0 8px 28px rgba(0, 0, 0, 0.38)',
                    color: '#E5EDF7',
                    fontFamily: 'Segoe UI, Arial, sans-serif',
                    fontSize: '12px',
                    lineHeight: '1.4',
                    pointerEvents: 'none'
                }});
                handler.wrapper.appendChild(tooltip);
            }}

            function formatDateOnly(time) {{
                if (!time) return '';
                if (typeof time === 'string') {{
                    const parts = time.split('-');
                    return parts.length === 3
                        ? parts[2] + '/' + parts[1] + '/' + parts[0]
                        : time;
                }}
                if (typeof time === 'object' && time.year && time.month && time.day) {{
                    return String(time.day).padStart(2, '0') + '/'
                        + String(time.month).padStart(2, '0') + '/'
                        + String(time.year);
                }}
                if (typeof time === 'number') {{
                    const date = new Date(time * 1000);
                    return String(date.getUTCDate()).padStart(2, '0') + '/'
                        + String(date.getUTCMonth() + 1).padStart(2, '0') + '/'
                        + String(date.getUTCFullYear());
                }}
                return String(time);
            }}

            function readValue(param, series) {{
                let data = null;
                if (param.seriesData && typeof param.seriesData.get === 'function') {{
                    data = param.seriesData.get(series);
                }}
                if ((data === null || data === undefined)
                    && param.seriesPrices
                    && typeof param.seriesPrices.get === 'function') {{
                    data = param.seriesPrices.get(series);
                }}
                if (typeof data === 'number') return data;
                if (data && Number.isFinite(data.value)) return data.value;
                if (data && Number.isFinite(data.close)) return data.close;
                return null;
            }}

            function formatValue(value) {{
                if (!Number.isFinite(value)) return '—';
                const sign = value > 0 ? '+' : '';
                return sign + value.toLocaleString('vi-VN', {{
                    minimumFractionDigits: 1,
                    maximumFractionDigits: 1
                }}) + ' tỷ';
            }}

            handler.chart.subscribeCrosshairMove(function(param) {{
                if (!param || !param.time || !param.point) {{
                    tooltip.style.display = 'none';
                    return;
                }}

                const chartWidth = handler.wrapper.clientWidth;
                const chartHeight = handler.wrapper.clientHeight;
                if (param.point.x < 0 || param.point.y < 0
                    || param.point.x > chartWidth || param.point.y > chartHeight) {{
                    tooltip.style.display = 'none';
                    return;
                }}

                let hasAnyValue = false;
                const rows = seriesMeta.map(function(item) {{
                    const value = readValue(param, item.series);
                    if (Number.isFinite(value)) hasAnyValue = true;
                    const valueColor = !Number.isFinite(value)
                        ? '#8FA3BD'
                        : (value > 0 ? '#22C55E' : (value < 0 ? '#EF4444' : '#E5EDF7'));

                    return '<div style="display:flex;align-items:center;justify-content:space-between;'
                        + 'gap:18px;margin-top:5px;">'
                        + '<span style="display:inline-flex;align-items:center;gap:7px;color:#B7C4D6;">'
                        + '<span style="width:8px;height:8px;border-radius:50%;background:'
                        + item.color + ';display:inline-block;"></span>'
                        + item.label + '</span>'
                        + '<strong style="color:' + valueColor + ';font-weight:700;">'
                        + formatValue(value) + '</strong></div>';
                }}).join('');

                if (!hasAnyValue) {{
                    tooltip.style.display = 'none';
                    return;
                }}

                tooltip.innerHTML = '<div style="font-weight:700;color:#FFFFFF;'
                    + 'padding-bottom:5px;border-bottom:1px solid rgba(143,163,189,0.20);">'
                    + formatDateOnly(param.time) + '</div>' + rows;
                tooltip.style.display = 'block';
            }});
        }})(0);
        """
    )

    first_date = str(chart_df["time"].iloc[0])
    last_date = str(chart_df["time"].iloc[-1])
    chart_plot.load_chart(
        chart=chart,
        precision=1,
        visible_range=(first_date, last_date),
    )
    return chart, df

# =============================================================================
# Operations / write pipeline
# =============================================================================

PIPELINE_WRITE_LOCK = asyncio.Lock()

PIPELINE_STEPS: tuple[dict[str, str], ...] = (
    {
        "key": "amibroker_eod",
        "title": "Đồng bộ AmiBroker EOD",
        "method": "_sync_amibroker_eod",
        "detail": "self._sync_amibroker_eod(from_last_day=days_diff, connection=connection)",
        "icon": "storage",
    },
    {
        "key": "yahoo_eod",
        "title": "Đồng bộ Yahoo Finance EOD",
        "method": "_sync_yahoo_eod",
        "detail": "self._sync_yahoo_eod(from_last_day=days_diff, connection=connection)",
        "icon": "cloud_download",
    },
    {
        "key": "fundamental",
        "title": "Cập nhật Fundamental Analysis",
        "method": "_upsert_fa",
        "detail": "self._upsert_fa(amibroker=amibroker, connection=connection)",
        "icon": "analytics",
    },
    {
        "key": "tickers",
        "title": "Cập nhật danh sách Ticker",
        "method": "_upsert_tickers",
        "detail": "self._upsert_tickers(connection=connection, repository=ticker_repository)",
        "icon": "format_list_bulleted",
    },
    {
        "key": "holiday",
        "title": "Cập nhật ngày nghỉ",
        "method": "_execute_sql",
        "detail": "self._execute_sql(.../updateHoliday.sql, sql_description='Update Holiday Table')",
        "icon": "event_busy",
    },
    {
        "key": "index",
        "title": "Tính VNINDEX_NOT_VIN",
        "method": "_calc_index",
        "detail": "self._calc_index(connection=connection, repository=index_repository)",
        "icon": "functions",
    },
    {
        "key": "trend",
        "title": "Tính Moving Average / Trend",
        "method": "_calc_trend",
        "detail": "self._calc_trend(from_last_day=days_diff, connection=connection, repository=trend_repository)",
        "icon": "trending_up",
    },
)


class _QueueTextWriter(io.TextIOBase):
    """Đẩy stdout/stderr từ worker thread sang ui.log."""

    def __init__(self, event_queue: Queue, stream_name: str) -> None:
        super().__init__()
        self._queue = event_queue
        self._stream_name = stream_name
        self._buffer = ""

    def writable(self) -> bool:
        return True

    def write(self, text: str) -> int:
        if not text:
            return 0
        self._buffer += str(text)
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            if line.strip():
                _queue_log(self._queue, line.rstrip(), source=self._stream_name)
        return len(text)

    def flush(self) -> None:
        if self._buffer.strip():
            _queue_log(self._queue, self._buffer.rstrip(), source=self._stream_name)
        self._buffer = ""


class _QueueLogHandler(logging.Handler):
    """Forward Python logging records to the operations log."""

    def __init__(self, event_queue: Queue) -> None:
        super().__init__()
        self._queue = event_queue
        self.setFormatter(logging.Formatter("%(levelname)s | %(name)s | %(message)s"))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            _queue_log(self._queue, self.format(record), source="logging")
        except Exception:
            self.handleError(record)


def _queue_log(event_queue: Queue, message: str, *, source: str = "pipeline") -> None:
    timestamp = datetime.now().strftime("%H:%M:%S")
    event_queue.put(("log", f"[{timestamp}] [{source}] {message}"))


def _queue_status(event_queue: Queue, step_key: str, status: str) -> None:
    event_queue.put(("status", step_key, status))


def _import_pipeline_symbol(symbol_name: str, module_candidates: tuple[str, ...]) -> Any:
    """
    Import symbol theo architecture hiện tại của CherryStock.

    Candidate paths được thử trước để code rõ ràng. Nếu source đã được di chuyển
    trong quá trình refactor, fallback sẽ tìm module chứa class/function trong src/.
    Việc này chỉ chạy khi người dùng click tab Vận Hành, không ảnh hưởng startup UI.
    """
    import_errors: list[str] = []
    for module_name in module_candidates:
        try:
            module = importlib.import_module(module_name)
            if hasattr(module, symbol_name):
                return getattr(module, symbol_name)
        except Exception as exc:
            import_errors.append(f"{module_name}: {exc}")

    definition_tokens = (f"class {symbol_name}", f"def {symbol_name}")
    for source_file in PROJECT_ROOT.rglob("*.py"):
        if source_file == Path(__file__).resolve():
            continue
        try:
            source_text = source_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if not any(token in source_text for token in definition_tokens):
            continue

        relative = source_file.relative_to(PROJECT_ROOT)
        module_parts = list(relative.with_suffix("").parts)
        if module_parts[-1] == "__init__":
            module_parts.pop()
        if not module_parts:
            continue
        module_name = ".".join(module_parts)
        try:
            module = importlib.import_module(module_name)
            if hasattr(module, symbol_name):
                return getattr(module, symbol_name)
        except Exception as exc:
            import_errors.append(f"{module_name}: {exc}")

    details = "\n".join(import_errors[-8:])
    raise ImportError(
        f"Không tìm thấy {symbol_name} trong CherryStock source."
        + (f"\nCác import gần nhất:\n{details}" if details else "")
    )


def _settings_values(settings: Any) -> dict[str, Any]:
    context: dict[str, Any] = {"settings": settings}
    for attr_name in dir(settings):
        if attr_name.startswith("_"):
            continue
        try:
            value = getattr(settings, attr_name)
        except Exception:
            continue
        if callable(value):
            continue
        context[attr_name] = value
    return context


def _lookup_constructor_value(name: str, context: dict[str, Any]) -> tuple[bool, Any]:
    aliases = {
        "factory": ("connection_factory", "duckdb_connection_factory"),
        "connection_factory": ("factory", "duckdb_connection_factory"),
        "amibroker": ("amibroker_adapter", "adapter"),
        "amibroker_adapter": ("amibroker", "adapter"),
        "conn": ("connection", "con"),
        "con": ("connection", "conn"),
        "db_path": ("local_db_path", "database_path", "duckdb_path"),
        "database_path": ("local_db_path", "db_path", "duckdb_path"),
        "sql_dir": ("duckdb_sql_path", "sql_path"),
    }
    if name in context:
        return True, context[name]
    for alias in aliases.get(name, ()):
        if alias in context:
            return True, context[alias]

    normalized = name.replace("_", "").lower()
    for key, value in context.items():
        if key.replace("_", "").lower() == normalized:
            return True, value
    return False, None


def _construct_from_context(cls: type, context: dict[str, Any]) -> Any:
    signature = inspect.signature(cls)
    kwargs: dict[str, Any] = {}
    missing: list[str] = []
    for parameter in signature.parameters.values():
        if parameter.name == "self" or parameter.kind in {
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        }:
            continue
        found, value = _lookup_constructor_value(parameter.name, context)
        if found:
            kwargs[parameter.name] = value
        elif parameter.default is inspect.Parameter.empty:
            missing.append(parameter.name)

    if missing:
        raise TypeError(
            f"Không thể khởi tạo {cls.__name__}; thiếu constructor args: {', '.join(missing)}"
        )
    return cls(**kwargs)


def _build_pipeline_runtime() -> dict[str, Any]:
    load_settings = _import_pipeline_symbol(
        "load_settings",
        (
            "cherrystock.config.settings",
            "config.settings",
        ),
    )
    settings = load_settings()
    context = _settings_values(settings)

    connection_factory_cls = _import_pipeline_symbol(
        "DuckDBConnectionFactory",
        (
            "cherrystock.infrastructure.duckdb.connection_factory",
            "cherrystock.infrastructure.persistence.duckdb.connection_factory",
        ),
    )
    connection_factory = _construct_from_context(connection_factory_cls, context)
    context.update(
        {
            "connection_factory": connection_factory,
            "duckdb_connection_factory": connection_factory,
            "factory": connection_factory,
        }
    )

    amibroker_cls = _import_pipeline_symbol(
        "WindowsAmiBrokerAdapter",
        (
            "cherrystock.infrastructure.amibroker.windows_adapter",
            "cherrystock.infrastructure.amibroker.adapter",
        ),
    )
    amibroker = _construct_from_context(amibroker_cls, context)
    context.update(
        {
            "amibroker": amibroker,
            "amibroker_adapter": amibroker,
            "adapter": amibroker,
        }
    )

    pipeline_cls = _import_pipeline_symbol(
        "SyncWritePipelineService",
        (
            "cherrystock.application.sync_write_pipeline",
            "cherrystock.application.services.sync_write_pipeline",
        ),
    )

    # Một số phiên bản service nhận uow_factory trong constructor.
    try:
        uow_cls = _import_pipeline_symbol(
            "DuckDBUnitOfWork",
            (
                "cherrystock.infrastructure.duckdb.unit_of_work",
                "cherrystock.infrastructure.persistence.duckdb.unit_of_work",
            ),
        )
    except ImportError:
        uow_cls = None

    if uow_cls is not None:
        def uow_factory() -> Any:
            return _construct_from_context(uow_cls, context)
        context["uow_factory"] = uow_factory
        context["unit_of_work_factory"] = uow_factory

    pipeline = _construct_from_context(pipeline_cls, context)
    return {
        "settings": settings,
        "context": context,
        "connection_factory": connection_factory,
        "amibroker": amibroker,
        "pipeline": pipeline,
        "uow_cls": uow_cls,
    }


def _repository_from_uow(uow: Any, *names: str) -> Any | None:
    for name in names:
        value = getattr(uow, name, None)
        if value is not None:
            return value
    return None


def _build_repository(symbol_name: str, connection: Any, context: dict[str, Any]) -> Any | None:
    try:
        repository_cls = _import_pipeline_symbol(
            symbol_name,
            (
                "cherrystock.infrastructure.duckdb.repositories",
                "cherrystock.infrastructure.persistence.duckdb.repositories",
                f"cherrystock.infrastructure.duckdb.{symbol_name.removesuffix('Repository').lower()}_repository",
            ),
        )
    except ImportError:
        return None

    repository_context = dict(context)
    repository_context.update({"connection": connection, "conn": connection, "con": connection})
    try:
        return _construct_from_context(repository_cls, repository_context)
    except TypeError:
        return None


def _resolve_sql_file(pipeline: Any, settings: Any) -> str:
    sql_dir = getattr(pipeline, "_sql_dir", None)
    if sql_dir is None:
        for attr_name in ("duckdb_sql_path", "sql_dir", "sql_path"):
            sql_dir = getattr(settings, attr_name, None)
            if sql_dir is not None:
                break
    if sql_dir is None:
        try:
            lst_para = importlib.import_module("Ults.lstPara")
            sql_dir = getattr(lst_para, "DUCKDB_SQL_PATH", None)
        except Exception:
            sql_dir = None
    if sql_dir is None:
        raise RuntimeError("Không xác định được thư mục SQL để chạy updateHoliday.sql")
    return str(Path(sql_dir) / "updateHoliday.sql")


def _execute_pipeline_step(
    *,
    step_key: str,
    pipeline: Any,
    amibroker: Any,
    connection: Any,
    days_diff: int,
    ticker_repository: Any | None,
    index_repository: Any | None,
    trend_repository: Any | None,
    settings: Any,
) -> None:
    if step_key == "amibroker_eod":
        pipeline._sync_amibroker_eod(from_last_day=days_diff, connection=connection)
    elif step_key == "yahoo_eod":
        pipeline._sync_yahoo_eod(from_last_day=days_diff, connection=connection)
    elif step_key == "fundamental":
        pipeline._upsert_fa(amibroker=amibroker, connection=connection)
    elif step_key == "tickers":
        pipeline._upsert_tickers(connection=connection, repository=ticker_repository)
    elif step_key == "holiday":
        pipeline._execute_sql(
            con=connection,
            sql_file_path=_resolve_sql_file(pipeline, settings),
            sql_description="Update Holiday Table",
        )
    elif step_key == "index":
        pipeline._calc_index(connection=connection, repository=index_repository)
    elif step_key == "trend":
        pipeline._calc_trend(
            from_last_day=days_diff,
            connection=connection,
            repository=trend_repository,
        )
    else:
        raise KeyError(f"Pipeline step không hợp lệ: {step_key}")


def _run_pipeline_steps_sync(
    step_keys: list[str],
    days_diff: int,
    event_queue: Queue,
) -> None:
    """Chạy pipeline trong worker thread; Run All dùng một transaction/UoW chung."""
    stdout_writer = _QueueTextWriter(event_queue, "stdout")
    stderr_writer = _QueueTextWriter(event_queue, "stderr")
    log_handler = _QueueLogHandler(event_queue)
    root_logger = logging.getLogger()
    root_logger.addHandler(log_handler)

    step_map = {step["key"]: step for step in PIPELINE_STEPS}
    current_step: str | None = None
    completed: set[str] = set()

    try:
        with redirect_stdout(stdout_writer), redirect_stderr(stderr_writer):
            _queue_log(event_queue, f"Bắt đầu pipeline | from_last_day={days_diff}")
            runtime = _build_pipeline_runtime()
            pipeline = runtime["pipeline"]
            amibroker = runtime["amibroker"]
            settings = runtime["settings"]
            context = runtime["context"]
            uow_cls = runtime["uow_cls"]

            uow = None
            if uow_cls is not None:
                try:
                    uow = _construct_from_context(uow_cls, context)
                except TypeError as exc:
                    _queue_log(
                        event_queue,
                        f"Không khởi tạo được DuckDBUnitOfWork ({exc}); dùng DuckDBManager fallback.",
                        source="warning",
                    )

            if uow is not None:
                with uow as active_uow:
                    active_uow = active_uow or uow
                    connection = _repository_from_uow(
                        active_uow, "connection", "conn", "con", "_connection", "_conn"
                    )
                    if connection is None and hasattr(active_uow, "execute"):
                        connection = active_uow
                    if connection is None:
                        connection = _repository_from_uow(
                            uow, "connection", "conn", "con", "_connection", "_conn"
                        )
                    if connection is None:
                        raise RuntimeError("DuckDBUnitOfWork không expose writer connection")

                    ticker_repository = _repository_from_uow(
                        active_uow,
                        "ticker_repository", "tickers", "ticker_repo", "_ticker_repository", "_ticker_repo",
                    ) or _repository_from_uow(
                        uow,
                        "ticker_repository", "tickers", "ticker_repo", "_ticker_repository", "_ticker_repo",
                    )
                    index_repository = _repository_from_uow(
                        active_uow,
                        "index_repository", "indexes", "index_repo", "_index_repository", "_index_repo",
                    ) or _repository_from_uow(
                        uow,
                        "index_repository", "indexes", "index_repo", "_index_repository", "_index_repo",
                    )
                    trend_repository = _repository_from_uow(
                        active_uow,
                        "trend_repository", "trends", "trend_repo", "_trend_repository", "_trend_repo",
                    ) or _repository_from_uow(
                        uow,
                        "trend_repository", "trends", "trend_repo", "_trend_repository", "_trend_repo",
                    )

                    # Một số UoW chỉ expose connection; tạo repository từ chính writer
                    # để vẫn giữ đúng một transaction cho toàn bộ Run All.
                    ticker_repository = ticker_repository or _build_repository(
                        "TickerRepository", connection, context
                    )
                    index_repository = index_repository or _build_repository(
                        "IndexRepository", connection, context
                    )
                    trend_repository = trend_repository or _build_repository(
                        "TrendRepository", connection, context
                    )

                    for step_key in step_keys:
                        current_step = step_key
                        step = step_map[step_key]
                        _queue_status(event_queue, step_key, "running")
                        started = perf_counter()
                        _queue_log(event_queue, f"▶ {step['title']} ({step['method']})")
                        _execute_pipeline_step(
                            step_key=step_key,
                            pipeline=pipeline,
                            amibroker=amibroker,
                            connection=connection,
                            days_diff=days_diff,
                            ticker_repository=ticker_repository,
                            index_repository=index_repository,
                            trend_repository=trend_repository,
                            settings=settings,
                        )
                        elapsed = perf_counter() - started
                        completed.add(step_key)
                        _queue_status(event_queue, step_key, "success")
                        _queue_log(event_queue, f"✓ {step['title']} hoàn tất sau {elapsed:.1f}s")
            else:
                # Compatibility fallback cho source cũ chưa có DuckDBUnitOfWork.
                with DuckDBManager(read_only=False) as connection:
                    transaction_started = False
                    try:
                        connection.execute("BEGIN TRANSACTION")
                        transaction_started = True
                    except Exception as exc:
                        if "transaction" not in str(exc).lower():
                            raise

                    ticker_repository = _build_repository("TickerRepository", connection, context)
                    index_repository = _build_repository("IndexRepository", connection, context)
                    trend_repository = _build_repository("TrendRepository", connection, context)
                    try:
                        for step_key in step_keys:
                            current_step = step_key
                            step = step_map[step_key]
                            _queue_status(event_queue, step_key, "running")
                            started = perf_counter()
                            _queue_log(event_queue, f"▶ {step['title']} ({step['method']})")
                            _execute_pipeline_step(
                                step_key=step_key,
                                pipeline=pipeline,
                                amibroker=amibroker,
                                connection=connection,
                                days_diff=days_diff,
                                ticker_repository=ticker_repository,
                                index_repository=index_repository,
                                trend_repository=trend_repository,
                                settings=settings,
                            )
                            elapsed = perf_counter() - started
                            completed.add(step_key)
                            _queue_status(event_queue, step_key, "success")
                            _queue_log(event_queue, f"✓ {step['title']} hoàn tất sau {elapsed:.1f}s")
                        if transaction_started:
                            connection.execute("COMMIT")
                    except Exception:
                        if transaction_started:
                            try:
                                connection.execute("ROLLBACK")
                            except Exception:
                                pass
                        raise

            _queue_log(event_queue, "Pipeline hoàn tất. Transaction đã commit.")
            event_queue.put(("job", "success"))
    except Exception as exc:
        if current_step:
            _queue_status(event_queue, current_step, "error")
        for step_key in completed:
            if step_key != current_step:
                _queue_status(event_queue, step_key, "rolled_back")
        for step_key in step_keys:
            if step_key not in completed and step_key != current_step:
                _queue_status(event_queue, step_key, "skipped")
        _queue_log(
            event_queue,
            f"✗ Pipeline thất bại: {type(exc).__name__}: {exc}. "
            "Database transaction (nếu đã mở) đã rollback.",
            source="error",
        )
        for line in traceback.format_exc().rstrip().splitlines():
            _queue_log(event_queue, line, source="traceback")
        event_queue.put(("job", "error"))
        raise
    finally:
        stdout_writer.flush()
        stderr_writer.flush()
        root_logger.removeHandler(log_handler)

def operations_tab_content() -> None:
    event_queue: Queue = Queue()
    status_labels: dict[str, ui.label] = {}
    step_buttons: dict[str, ui.button] = {}

    with ui.card().classes(card_classes("p-4 w-full")):
        with ui.row().classes("w-full items-center justify-between gap-3"):
            card_header(
                "Write Pipeline",
                "Chạy từng bước hoặc chạy toàn bộ tuần tự theo sync_write_pipeline.py",
                icon="settings_suggest",
            )
            job_status = ui.label("Sẵn sàng").classes(
                f"text-xs font-semibold px-3 py-1.5 rounded-full bg-[{THEME['surface_alt']}] "
                f"text-[{THEME['muted']}]"
            )

        with ui.row().classes("w-full items-end gap-3 mt-4"):
            days_input = ui.number(
                label="Số ngày cập nhật",
                value=15,
                min=1,
                max=3650,
                step=1,
                format="%.0f",
            ).props("outlined dense").classes("w-44")
            ui.label(
                "from_last_day dùng cho AmiBroker, Yahoo và Trend"
            ).classes(f"text-xs text-[{THEME['muted']}] pb-2")

    with ui.element("div").classes("grid grid-cols-1 xl:grid-cols-2 gap-3 w-full"):
        for index, step in enumerate(PIPELINE_STEPS, start=1):
            with ui.card().classes(card_classes("p-4")):
                with ui.row().classes("w-full items-center gap-3 no-wrap"):
                    ui.label(str(index)).classes(
                        f"w-8 h-8 rounded-full flex items-center justify-center shrink-0 "
                        f"bg-[{THEME['surface_alt']}] text-[{THEME['primary']}] font-bold"
                    )
                    ui.icon(step["icon"]).classes(f"text-xl text-[{THEME['primary']}] shrink-0")
                    with ui.column().classes("gap-0 flex-1 min-w-0"):
                        ui.label(step["title"]).classes("font-semibold")
                        ui.label(step["detail"]).classes(
                            f"text-[11px] font-mono text-[{THEME['muted']}] break-all"
                        )
                    status_labels[step["key"]] = ui.label("Chờ").classes(
                        f"text-xs font-semibold text-[{THEME['muted']}] shrink-0"
                    )

                    async def run_single_step(
                        _event: Any = None,
                        step_key: str = step["key"],
                    ) -> None:
                        await run_job([step_key])

                    step_buttons[step["key"]] = ui.button(
                        "Chạy",
                        icon="play_arrow",
                        on_click=run_single_step,
                    ).props("outline dense no-caps").classes("shrink-0")

    with ui.card().classes(card_classes("p-4 w-full")):
        with ui.row().classes("w-full items-center justify-between gap-3 mb-3"):
            card_header("Execution Log", "Log realtime trong lúc pipeline đang chạy", icon="terminal")
            with ui.row().classes("items-center gap-2"):
                clear_log_button = ui.button("Xóa log", icon="delete_sweep").props(
                    "flat dense no-caps"
                )
                run_all_button = ui.button("Run All", icon="playlist_play").props(
                    "unelevated dense no-caps"
                )
        log_view = ui.log(max_lines=3000).classes(
            f"w-full h-[460px] rounded-xl border border-[{THEME['border']}] "
            f"bg-[{THEME['background']}] p-3 font-mono text-xs"
        )

    status_classes = {
        "waiting": f"text-[{THEME['muted']}]",
        "running": f"text-[{THEME['warning']}]",
        "success": f"text-[{THEME['positive']}]",
        "error": f"text-[{THEME['negative']}]",
        "rolled_back": f"text-[{THEME['warning']}]",
        "skipped": f"text-[{THEME['muted']}]",
    }
    status_text = {
        "waiting": "Chờ",
        "running": "Đang chạy",
        "success": "Thành công",
        "error": "Lỗi",
        "rolled_back": "Rollback DB",
        "skipped": "Bỏ qua",
    }
    all_status_class_names = " ".join(status_classes.values())

    def set_step_status(step_key: str, status: str) -> None:
        label = status_labels.get(step_key)
        if label is None:
            return
        label.set_text(status_text.get(status, status))
        label.classes(remove=all_status_class_names)
        label.classes(status_classes.get(status, status_classes["waiting"]))

    def set_controls_enabled(enabled: bool) -> None:
        for button in step_buttons.values():
            button.enable() if enabled else button.disable()
        run_all_button.enable() if enabled else run_all_button.disable()
        days_input.enable() if enabled else days_input.disable()

    def drain_pipeline_events() -> None:
        while True:
            try:
                event = event_queue.get_nowait()
            except Empty:
                break
            kind = event[0]
            if kind == "log":
                log_view.push(event[1])
            elif kind == "status":
                _, step_key, status = event
                set_step_status(step_key, status)
            elif kind == "job":
                _, status = event
                if status == "success":
                    job_status.set_text("Hoàn tất")
                    ui.notify("Pipeline hoàn tất", type="positive")
                else:
                    job_status.set_text("Thất bại")
                    ui.notify("Pipeline thất bại — xem Execution Log", type="negative")

    ui.timer(0.15, drain_pipeline_events)

    async def run_job(step_keys: list[str]) -> None:
        if PIPELINE_WRITE_LOCK.locked():
            ui.notify("Một write pipeline khác đang chạy", type="warning")
            return

        try:
            days_diff = max(1, int(days_input.value or 15))
        except (TypeError, ValueError):
            days_diff = 15
            days_input.value = days_diff

        for key in step_keys:
            set_step_status(key, "waiting")
        set_controls_enabled(False)
        job_status.set_text("Đang chạy")
        _queue_log(
            event_queue,
            "Run All" if len(step_keys) > 1 else f"Run step: {step_keys[0]}",
            source="ui",
        )

        async with PIPELINE_WRITE_LOCK:
            try:
                await asyncio.to_thread(
                    _run_pipeline_steps_sync,
                    step_keys,
                    days_diff,
                    event_queue,
                )
            except Exception:
                # Chi tiết exception đã được worker đẩy vào log.
                pass
            finally:
                set_controls_enabled(True)
                drain_pipeline_events()

    async def run_all(_event: Any = None) -> None:
        await run_job([step["key"] for step in PIPELINE_STEPS])

    def clear_log() -> None:
        log_view.clear()
        for step in PIPELINE_STEPS:
            set_step_status(step["key"], "waiting")
        job_status.set_text("Sẵn sàng")

    run_all_button.on("click", run_all)
    clear_log_button.on("click", clear_log)

# =============================================================================
# Tab contents
# =============================================================================

def overview_tab_content() -> None:
    symbol_sources = {
        "remaining_vnindex": {"symbol": "VNINDEX_NOT_VIN", "source": "custom", "color": "#A0AEC0", "label_name": "Remaining VNINDEX", "target": "main"},
        "vnindex": {"symbol": "VNINDEX", "source": "index", "color": "#03FD10", "label_name": "VNINDEX", "target": "main"},
        "btc": {"symbol": "BTC-USD", "source": "other", "color": "#F7931A", "label_name": "BTC-USD", "target": "main"},
        "spx": {"symbol": "^SPX", "source": "other", "color": "#3182CE", "label_name": "SPX", "target": "main"},
        "ndx": {"symbol": "^NDX", "source": "other", "color": "#00B5D8", "label_name": "NDX", "target": "main"},
        "gcz": {"symbol": "GC=F", "source": "other", "color": "#ECC94B", "label_name": "Gold", "target": "main"},
        "lcoz": {"symbol": "^LCOZ", "source": "other", "color": "#E53E3E", "label_name": "Oil", "target": "main"},
        "dxy": {"symbol": "DX-Y.NYB", "source": "other", "color": "#A0AEC0", "label_name": "DXY", "target": "sub"},
        "VND=X": {"symbol": "VND=X", "source": "other", "color": "#FFAA00", "label_name": "USD/VND", "target": "sub"},
    }

    with ui.element("div").classes("grid grid-cols-2 lg:grid-cols-5 gap-3 w-full"):
        metric_card("VN-Index", "1,286.42", "+1.18% hôm nay", positive=True, icon="show_chart")
        metric_card("GTGD HOSE", "18.6 nghìn tỷ", "+12.4% so với TB20", positive=True, icon="payments")
        metric_card("Độ rộng", "268 / 151", "Nghiêng về bên mua", positive=True, icon="compare_arrows")
        metric_card("Khối ngoại", "-642 tỷ", "Bán ròng", positive=False, icon="public")
        metric_card("Tự doanh", "-1 tỷ", "Bán ròng", positive=False, icon="account_balance")

    with ui.element("div").classes("grid grid-cols-1 xl:grid-cols-12 gap-4 w-full"):
        with ui.card().classes(card_classes("p-4 xl:col-span-9")):
            with ui.row().classes("w-full items-center justify-between gap-3"):
                card_header("Intermarket", "VN-Index so với tài sản toàn cầu", icon="language")
                intermarket_timeframe = ui.toggle(TIMEFRAME_OPTIONS, value="daily").props(
                    "dense unelevated no-caps toggle-color=primary"
                ).classes("timeframe-toggle")
            intermarket_container = ui.html("", sanitize=False).classes("w-full min-w-0 mt-2")

            def refresh_intermarket() -> None:
                chart = chart_plot.draw_comparision_main_sub(
                    start_date=CHART_START_DATE,
                    symbol_sources=symbol_sources,
                    timeframe=str(intermarket_timeframe.value or "daily"),
                )
                intermarket_container.set_content(
                    chart_plot.build_chart_iframe_html(chart, height=IFRAME_HEIGHT)
                )

            intermarket_timeframe.on_value_change(lambda _: refresh_intermarket())
            refresh_intermarket()

        with ui.card().classes(card_classes("p-4 xl:col-span-3")):
            card_header("Watchlist", "Danh sách theo dõi", icon="star")
            with ui.row().classes("w-full gap-2 mt-3"):
                ui.input(placeholder="Tìm mã...").props("dense outlined clearable").classes("flex-1")
                ui.button(icon="add").props("round dense unelevated").tooltip("Thêm mã")
            create_watchlist_grid()

        with ui.card().classes(card_classes("p-4 xl:col-span-8")):
            with ui.row().classes("w-full items-center justify-between gap-3"):
                card_header("Độ rộng thị trường", "Tỷ lệ cổ phiếu trên MA20/50/100/200", icon="insights")
                breadth_timeframe = ui.toggle(TIMEFRAME_OPTIONS, value="daily").props(
                    "dense unelevated no-caps toggle-color=primary"
                ).classes("timeframe-toggle")
            breadth_container = ui.html("", sanitize=False).classes("w-full min-w-0 mt-2")

            def refresh_market_breadth() -> None:
                chart = chart_plot.draw_ticker_above_MA(
                    start_date=CHART_START_DATE,
                    timeframe=str(breadth_timeframe.value or "daily"),
                )
                breadth_container.set_content(
                    chart_plot.build_chart_iframe_html(chart, height=IFRAME_HEIGHT)
                )

            breadth_timeframe.on_value_change(lambda _: refresh_market_breadth())
            refresh_market_breadth()

        with ui.card().classes(card_classes("p-4 xl:col-span-4")):
            card_header("Hiệu suất ngành", "Biến động trong phiên", icon="donut_large")
            ui.echart(sector_chart_options()).classes("w-full h-[430px]")

        with ui.card().classes(card_classes("p-4 xl:col-span-12")):
            with ui.row().classes("w-full items-center justify-between gap-3"):
                card_header(
                    "Dòng tiền nhà đầu tư",
                    "Chuỗi thời gian mua/bán ròng theo Ngày, Tuần và Tháng — đơn vị tỷ đồng",
                    icon="account_balance",
                )
                cashflow_timeframe = ui.toggle(
                    TIMEFRAME_OPTIONS,
                    value="daily",
                ).props(
                    "dense unelevated no-caps toggle-color=primary"
                ).classes("timeframe-toggle")

            cumulative_labels: dict[str, ui.label] = {}
            with ui.element("div").classes(
                "grid grid-cols-2 lg:grid-cols-4 gap-3 w-full mt-4"
            ):
                for investor_name, icon_name in (
                    ("Tổ chức", "corporate_fare"),
                    ("Cá nhân", "person"),
                    ("Nước ngoài", "public"),
                    ("Tự doanh", "account_balance"),
                ):
                    with ui.element("div").classes(
                        "rounded-xl border px-4 py-3 "
                        f"bg-[{THEME['surface_alt']}] border-[{THEME['border']}]"
                    ):
                        with ui.row().classes("items-center gap-2"):
                            ui.icon(icon_name).classes(f"text-[{THEME['primary']}]")
                            ui.label(investor_name).classes(
                                f"text-xs font-medium text-[{THEME['muted']}]"
                            )
                        cumulative_labels[investor_name] = ui.label("0 tỷ").classes(
                            "text-xl font-bold mt-2"
                        )
                        ui.label("Lũy kế theo khung đang chọn").classes(
                            f"text-[11px] text-[{THEME['muted']}]"
                        )

            cashflow_container = ui.html(
                "",
                sanitize=False,
            ).classes("w-full min-w-0 mt-2")

            def set_cumulative_labels(summary: dict[str, float]) -> None:
                for investor_name, value in summary.items():
                    label = cumulative_labels[investor_name]
                    sign = "+" if value > 0 else ""
                    label.set_text(f"{sign}{value:,.1f} tỷ")
                    label.classes(
                        remove=(
                            f"text-[{THEME['positive']}] "
                            f"text-[{THEME['negative']}] "
                            f"text-[{THEME['muted']}]"
                        )
                    )
                    if value > 0:
                        label.classes(f"text-[{THEME['positive']}]")
                    elif value < 0:
                        label.classes(f"text-[{THEME['negative']}]")
                    else:
                        label.classes(f"text-[{THEME['muted']}]")

            def summarize_cashflow(df: pd.DataFrame) -> dict[str, float]:
                mapping = {
                    "institutional": "Tổ chức",
                    "individual": "Cá nhân",
                    "foreign_flow": "Nước ngoài",
                    "proprietary": "Tự doanh",
                }
                if df.empty:
                    return {label: 0.0 for label in mapping.values()}
                return {
                    label: float(
                        pd.to_numeric(df[column], errors="coerce")
                        .fillna(0.0)
                        .sum()
                    )
                    for column, label in mapping.items()
                }

            def refresh_cashflow() -> None:
                selected_timeframe = str(
                    cashflow_timeframe.value or "daily"
                ).strip().lower()

                chart, filtered_df = build_investor_cashflow_chart(
                    timeframe=selected_timeframe,
                    start_date=CHART_START_DATE,
                )

                if chart is None:
                    cashflow_container.set_content(
                        '<div style="height:500px;display:flex;align-items:center;'
                        'justify-content:center;color:#8fa3bd;">'
                        'Không có dữ liệu dòng tiền</div>'
                    )
                else:
                    iframe_html = chart_plot.build_chart_iframe_html(
                        chart,
                        height=500,
                    )
                    # Nonce làm nội dung srcdoc khác nhau sau mỗi lần render,
                    # buộc NiceGUI thay iframe thay vì tái sử dụng DOM cũ.
                    render_nonce = time_ns()
                    cashflow_container.set_content(
                        f"<!-- cashflow-build:{render_nonce} -->{iframe_html}"
                    )

                set_cumulative_labels(summarize_cashflow(filtered_df))

            cashflow_timeframe.on_value_change(lambda _: refresh_cashflow())
            refresh_cashflow()


def market_tab_content() -> None:
    df = view_to_dataframe("vw_Ticker", condition="Status = 'Y'")
    with ui.card().classes(card_classes("p-4 w-full")):
        with ui.row().classes("w-full items-center justify-between gap-3 mb-3"):
            card_header("Stock Screener", "Lọc và so sánh cổ phiếu Việt Nam", icon="filter_alt")
            with ui.row().classes("items-center gap-2"):
                ui.button("Xuất Excel", icon="download").props("outline dense no-caps")
                ui.button("Lưu bộ lọc", icon="bookmark_add").props("unelevated dense no-caps")
        market_grid = create_market_grid(
            df=df,
            filter_configs=NiceGUI_grid_market_tb.filter_configs,
            field_configs=NiceGUI_grid_market_tb.field_configs,
        )
        market_grid.classes("dashboard-data-grid")


def portfolio_tab_content() -> None:
    with ui.element("div").classes("grid grid-cols-2 lg:grid-cols-4 gap-3 w-full"):
        metric_card("Giá trị danh mục", "1.078 tỷ", "+86.9 triệu", positive=True, icon="account_balance_wallet")
        metric_card("Lãi/Lỗ hôm nay", "+14.2 triệu", "+1.34%", positive=True, icon="trending_up")
        metric_card("Tiền mặt", "146.5 triệu", "12.0% tài sản", positive=True, icon="savings")
        metric_card("Max Drawdown", "-8.42%", "Trong 12 tháng", positive=False, icon="waterfall_chart")

    with ui.element("div").classes("grid grid-cols-1 xl:grid-cols-12 gap-4 w-full"):
        with ui.card().classes(card_classes("p-4 xl:col-span-4")):
            card_header("Phân bổ danh mục", "Theo nhóm ngành", icon="pie_chart")
            ui.echart(allocation_chart_options()).classes("w-full h-[390px]")
        with ui.card().classes(card_classes("p-4 xl:col-span-8")):
            card_header("Vị thế đang nắm giữ", "Cập nhật theo giá thị trường", icon="table_chart")
            create_portfolio_grid()



def rs_tab_content() -> None:
    """Render the Support / Resistance Ladder V1 page.

    Data acquisition and business calculation belong to calcEngine.levelLadder;
    this function only composes controls, metrics, chart and table.
    """
    metric_values: dict[str, Any] = {}

    with ui.element("div").classes("grid grid-cols-1 xl:grid-cols-12 gap-4 w-full"):
        with ui.card().classes(card_classes("p-4 xl:col-span-8")):
            card_header(
                "Support / Resistance Ladder",
                "V1: MA20 / MA50 / MA100 / MA200 trên D / W / M",
                icon="vertical_align_center",
            )
            ui.label(
                "R1/S1 = level gần giá hiện tại nhất; Strength là độ mạnh độc lập."
            ).classes(f"text-xs text-[{THEME['muted']}] mt-1")

            with ui.row().classes("w-full items-end gap-3 flex-wrap mt-4"):
                ticker_input = ui.input(
                    label="Ticker",
                    value="MWG",
                    placeholder="MWG",
                ).props("outlined dense clearable").classes("w-32 uppercase")

                as_of_input = ui.input(
                    label="As of date",
                    placeholder="YYYY-MM-DD",
                ).props("outlined dense clearable type=date").classes("w-44")

                cluster_input = ui.number(
                    label="Cluster %",
                    value=1.0,
                    min=0.1,
                    max=5.0,
                    step=0.1,
                    format="%.1f",
                ).props("outlined dense").classes("w-32")

                refresh_button = ui.button(
                    "Refresh",
                    icon="refresh",
                ).props("unelevated no-caps").classes("h-10 px-4")

        with ui.card().classes(card_classes("p-4 xl:col-span-4")):
            card_header(
                "Reward / Risk",
                "Structural R/R theo R1 và S1",
                icon="balance",
            )
            with ui.row().classes("w-full items-center gap-4 mt-4 no-wrap"):
                metric_values["rr"] = ui.label("—").classes(
                    f"text-3xl font-bold text-[{THEME['text']}] shrink-0"
                )
                ui.separator().props("vertical").classes(
                    f"h-12 bg-[{THEME['border']}]"
                )
                ui.label(
                    "Upside tới R1 / downside tới S1. >1 nghĩa là upside lớn hơn downside."
                ).classes(
                    f"text-xs text-[{THEME['muted']}] leading-snug"
                )

    with ui.element("div").classes("grid grid-cols-1 xl:grid-cols-12 gap-4 w-full"):
        with ui.card().classes(card_classes("p-4 xl:col-span-4")):
            card_header(
                "R/S Price Ladder",
                "Khoảng cách dọc phản ánh đúng khoảng cách giá thực tế",
                icon="stacked_line_chart",
            )
            ladder_chart = ui.echart(
                level_ladder_chart.empty_level_ladder_chart_options()
            ).classes("w-full h-[620px]")

        with ui.card().classes(card_classes("p-4 xl:col-span-8")):
            card_header(
                "Level Details",
                "Source, timeframe, distance và strength",
                icon="table_chart",
            )
            level_grid = ui.aggrid(
                {
                    "defaultColDef": {
                        "sortable": True,
                        "resizable": True,
                    },
                    "columnDefs": [
                        {"headerName": "Rank", "field": "rank", "width": 72},
                        {
                            "headerName": "Price",
                            "field": "price",
                            "width": 105,
                            ":valueFormatter": "params => Number(params.value).toLocaleString('vi-VN', {minimumFractionDigits: 1, maximumFractionDigits: 1})",
                        },
                        {
                            "headerName": "Dist %",
                            "field": "distance_pct",
                            "width": 92,
                            ":valueFormatter": "params => (params.value > 0 ? '+' : '') + Number(params.value).toFixed(2) + '%'",
                        },
                        {
                            "headerName": "Strength",
                            "field": "strength",
                            "width": 96,
                        },
                        {"headerName": "TF", "field": "timeframes", "width": 78},
                        {
                            "headerName": "Sources",
                            "field": "sources",
                            "minWidth": 170,
                            "flex": 1,
                        },
                    ],
                    "rowData": [],
                    "animateRows": True,
                    "headerHeight": 36,
                    "rowHeight": 38,
                },
                theme="quartz",
                auto_size_columns=False,
            ).classes("w-full h-[620px] dashboard-data-grid")

    def clear_output(message: str) -> None:
        metric_values["rr"].set_text("—")
        ladder_chart.options.clear()
        ladder_chart.options.update(level_ladder_chart.empty_level_ladder_chart_options(message))
        ladder_chart.update()
        level_grid.options["rowData"] = []
        level_grid.update()

    def refresh_rs_ladder() -> None:
        ticker = str(ticker_input.value or "").strip().upper()
        if not ticker:
            clear_output("Ticker là bắt buộc")
            ui.notify("Ticker là bắt buộc", type="warning")
            return

        selected_date = None
        raw_date = str(as_of_input.value or "").strip()
        if raw_date:
            try:
                selected_date = date.fromisoformat(raw_date)
            except ValueError:
                clear_output("As of date không hợp lệ")
                ui.notify("As of date phải theo YYYY-MM-DD", type="negative")
                return

        try:
            cluster_pct = float(cluster_input.value or 1.0)
            result = build_level_ladder(
                ticker,
                as_of_date=selected_date,
                cluster_threshold_pct=cluster_pct / 100.0,
            )
        except Exception as exc:
            logging.getLogger(__name__).exception(
                "R/S tab refresh failed | ticker=%s", ticker
            )
            clear_output("Không thể build R/S Ladder")
            ui.notify(f"R/S error: {exc}", type="negative", timeout=8000)
            return

        metric_values["rr"].set_text(
            f"{result.risk_reward_ratio:.2f}"
            if result.risk_reward_ratio is not None
            else "—"
        )

        ladder_chart.options.clear()
        ladder_chart.options.update(
            level_ladder_chart.build_level_ladder_chart_options(
                result,
                support_color=THEME["positive"],
                resistance_color=THEME["negative"],
                current_color=THEME["warning"],
                text_color=THEME["text"],
                muted_color=THEME["muted"],
                grid_color=THEME["border"],
            )
        )
        ladder_chart.update()

        level_grid.options["rowData"] = level_ladder_chart.ladder_rows(result)
        level_grid.update()

        ui.notify(
            f"{result.ticker} R/S @ {result.as_of_date.isoformat()} | "
            f"S={len(result.support_levels)} R={len(result.resistance_levels)}",
            type="positive",
        )

    refresh_button.on("click", refresh_rs_ladder)

# =============================================================================
# Page layout
# =============================================================================

def build_page() -> None:
    ui.colors(primary=THEME["primary"])
    ui.add_head_html('<meta name="viewport" content="width=device-width, initial-scale=1">')
    ui.add_css(f"""
        :root {{ --q-primary: {THEME['primary']}; }}
        body {{ background: {THEME['background']}; color: {THEME['text']}; }}
        .q-page, .q-layout, .nicegui-content {{ background: {THEME['background']}; }}
        .nicegui-content {{ padding: 0 !important; }}
        .dashboard-card {{ overflow: hidden; backdrop-filter: blur(12px); }}
        .dashboard-card:hover {{ border-color: #36506f; }}
        .metric-card {{ min-height: 112px; }}
        .q-tab {{ min-height: 46px; padding: 0 16px; }}
        .q-tab--active {{ background: {THEME['surface_alt']}; border-radius: 10px; }}
        .q-field--outlined .q-field__control:before {{ border-color: {THEME['border']}; }}
        .q-field--outlined:hover .q-field__control:before {{ border-color: #3c5878; }}
        .ag-root-wrapper {{ border-color: {THEME['border']} !important; border-radius: 12px !important; }}
        .dashboard-data-grid {{
            --ag-background-color: {THEME['surface']};
            --ag-foreground-color: {THEME['text']};
            --ag-header-background-color: {THEME['surface_alt']};
            --ag-header-foreground-color: {THEME['text']};
            --ag-odd-row-background-color: {THEME['surface_alt']};
            --ag-row-hover-color: #1b2a3f;
            --ag-border-color: {THEME['border']};
            --ag-secondary-border-color: {THEME['border']};
        }}
        .timeframe-toggle .q-btn {{ min-width: 58px; }}
        .app-shell {{ max-width: 2200px; margin: 0 auto; }}
        @media (max-width: 700px) {{
            .metric-card {{ min-height: 104px; }}
            .timeframe-toggle .q-btn {{ min-width: 48px; padding-left: 8px; padding-right: 8px; }}
        }}
    """)

    with ui.left_drawer(value=False).props("width=260 breakpoint=1024").classes(
        f"bg-[{THEME['surface']}] border-r border-[{THEME['border']}] p-3"
    ) as drawer:
        with ui.row().classes("items-center gap-3 px-2 py-3"):
            ui.icon("candlestick_chart").classes(f"text-3xl text-[{THEME['primary']}]")
            with ui.column().classes("gap-0"):
                ui.label("CherryStock").classes("text-lg font-bold")
                ui.label("Financial Terminal").classes(f"text-xs text-[{THEME['muted']}]")
        ui.separator().classes(f"my-2 bg-[{THEME['border']}]")
        for label, icon in [
            ("Tổng quan", "dashboard"), ("Thị trường", "show_chart"),
            ("Screener", "filter_alt"), ("Danh mục", "account_balance_wallet"),
            ("Watchlist", "star"), ("Cảnh báo", "notifications_active")
        ]:
            ui.button(label, icon=icon).props("flat align=left no-caps").classes(
                "w-full justify-start rounded-xl py-2"
            )
        ui.space()
        ui.separator().classes(f"my-2 bg-[{THEME['border']}]")
        ui.button("Cài đặt", icon="settings").props("flat align=left no-caps").classes(
            "w-full justify-start rounded-xl"
        )

    with ui.header().classes(
        f"h-16 px-3 md:px-5 items-center justify-between bg-[{THEME['surface']}] "
        f"border-b border-[{THEME['border']}]"
    ):
        with ui.row().classes("items-center gap-2 md:gap-3 no-wrap"):
            ui.button(icon="menu", on_click=drawer.toggle).props("flat round dense")
            ui.label("CherryStock").classes("font-bold text-lg md:text-xl")
            ui.badge("LIVE", color="positive").props("outline").classes("hidden sm:flex")
        with ui.row().classes("items-center gap-2 no-wrap"):
            ui.input(placeholder="Tìm mã, công ty...").props(
                "dense outlined rounded debounce=300 clearable"
            ).classes("hidden md:flex w-64 xl:w-80")
            ui.button(icon="refresh", on_click=lambda: ui.notify("Đã làm mới dữ liệu")).props("flat round")
            ui.button(icon="notifications").props("flat round")
            ui.avatar("CS").classes(f"bg-[{THEME['primary']}] text-black font-bold")

    with ui.column().classes("app-shell w-full px-3 md:px-5 py-4 gap-4"):
        with ui.row().classes("w-full items-end justify-between gap-3"):
            with ui.column().classes("gap-0"):
                ui.label("Trung tâm thị trường").classes("text-xl md:text-2xl font-bold")
                ui.label("Theo dõi xu hướng, độ rộng và danh mục trong một màn hình").classes(
                    f"text-xs md:text-sm text-[{THEME['muted']}]"
                )
            ui.select(
                ["Phiên hiện tại", "1 tuần", "1 tháng", "3 tháng"],
                value="Phiên hiện tại",
            ).props("dense outlined options-dense").classes("hidden sm:flex w-40")

        with ui.tabs().classes(
            f"w-full rounded-xl p-1 bg-[{THEME['surface']}] border border-[{THEME['border']}]"
        ).props("align=left inline-label mobile-arrows outside-arrows") as tabs:
            ui.tab("overview", label="Tổng quan", icon="dashboard")
            ui.tab("market", label="Screener", icon="filter_alt")
            ui.tab("portfolio", label="Danh mục", icon="account_balance_wallet")
            ui.tab("rs", label="R/S", icon="vertical_align_center")
            ui.tab("operations", label="Vận Hành", icon="settings_suggest")

        with ui.tab_panels(tabs, value="overview").classes(
            "w-full bg-transparent p-0"
        ).props("animated keep-alive swipeable"):
            with ui.tab_panel("overview").classes("p-0 gap-4"):
                overview_tab_content()
            with ui.tab_panel("market").classes("p-0"):
                market_tab_content()
            with ui.tab_panel("portfolio").classes("p-0 gap-4"):
                portfolio_tab_content()
            with ui.tab_panel("rs").classes("p-0 gap-4"):
                rs_tab_content()
            with ui.tab_panel("operations").classes("p-0 gap-4"):
                operations_tab_content()


build_page()

ui.run(
    host="0.0.0.0",
    port=8081,
    title="CherryStock Financial Terminal",
    dark=True,
    reload=True,
)