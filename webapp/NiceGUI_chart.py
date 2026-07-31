from __future__ import annotations
from datetime import date, timedelta
import importlib
from random import Random
from pathlib import Path
import sys
from duckdb import df
import pandas as pd
from typing import Any
from nicegui import ui
from collections.abc import Hashable



PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from webapp import NiceGUI_grid_market_tb
importlib.reload(NiceGUI_grid_market_tb)
from NiceGUI_grid import create_market_grid
from DuckDB.Data import view_to_dataframe
from Chart.plot import build_chart_iframe_html, draw_comparision_main_sub, draw_ticker_above_MA
from lstPara import CHART_START_DATE, IFRAME_HEIGHT

ROOT = Path(__file__).resolve().parent
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

THEME = {
    "background": "#07111f",
    "surface": "#0f1b2d",
    "surface_alt": "#14233a",
    "border": "#263750",
    "text": "#e5edf7",
    "muted": "#8fa3bd",
    "primary": "#38bdf8",
    "positive": "#22c55e",
    "negative": "#ef4444",
    "warning": "#f59e0b",
}
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

def card_classes(extra: str = "") -> str:
    return (
        "dashboard-card rounded-xl border shadow-sm "
        f"bg-[{THEME['surface']}] border-[{THEME['border']}] {extra}"
    )


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

def metric_card(
    title: str,
    value: str,
    change: str,
    *,
    positive: bool,
    icon: str,
) -> None:
    change_color = THEME["positive"] if positive else THEME["negative"]
    trend_icon = "trending_up" if positive else "trending_down"

    with ui.card().classes(card_classes("p-4 min-w-0")):
        with ui.row().classes("w-full items-start justify-between no-wrap"):
            with ui.column().classes("gap-1 min-w-0"):
                ui.label(title).classes(f"text-sm text-[{THEME['muted']}]")
                ui.label(value).classes(
                    f"text-2xl font-semibold text-[{THEME['text']}] truncate"
                )
                with ui.row().classes("items-center gap-1"):
                    ui.icon(trend_icon).classes(f"text-sm text-[{change_color}]")
                    ui.label(change).classes(f"text-sm font-medium text-[{change_color}]")
            ui.icon(icon).classes(
                f"text-2xl text-[{THEME['primary']}] "
                f"bg-[{THEME['surface_alt']}] rounded-lg p-2"
            )


def section_title(title: str, subtitle: str | None = None) -> None:
    with ui.column().classes("gap-0"):
        ui.label(title).classes("text-lg font-semibold")
        if subtitle:
            ui.label(subtitle).classes(f"text-sm text-[{THEME['muted']}]")


def create_watchlist_grid() -> ui.aggrid:
    options = {
        "defaultColDef": {
            "sortable": True,
            "filter": True,
            "resizable": True,
            "floatingFilter": True,
        },
        "columnDefs": [
            {"headerName": "Mã", "field": "ticker", "pinned": "left", "width": 95},
            {"headerName": "Doanh nghiệp", "field": "company", "minWidth": 180, "flex": 1},
            {
                "headerName": "Giá",
                "field": "price",
                "width": 110,
                ":valueFormatter": "params => params.value.toLocaleString('vi-VN', {minimumFractionDigits: 2})",
            },
            {
                "headerName": "% thay đổi",
                "field": "change",
                "width": 125,
                ":valueFormatter": "params => `${params.value > 0 ? '+' : ''}${params.value.toFixed(2)}%`",
                ":cellStyle": (
                    f"params => params.value >= 0 "
                    f"? {{color: '{THEME['positive']}', fontWeight: 600}} "
                    f": {{color: '{THEME['negative']}', fontWeight: 600}}"
                ),
            },
            {
                "headerName": "Khối lượng",
                "field": "volume",
                "width": 130,
                ":valueFormatter": "params => Intl.NumberFormat('en-US', {notation: 'compact'}).format(params.value)",
            },
            {"headerName": "Ngành", "field": "sector", "minWidth": 135},
            {"headerName": "P/E", "field": "pe", "width": 90},
            {"headerName": "RSI", "field": "rsi", "width": 90},
        ],
        "rowData": WATCHLIST_ROWS,
        "rowSelection": {"mode": "singleRow"},
        "animateRows": True,
        "pagination": True,
        "paginationPageSize": 6,
    }

    return ui.aggrid(
        options,
        theme="quartz",
        auto_size_columns=False,
    ).classes("w-full h-[420px]")

def create_portfolio_grid() -> ui.aggrid:
    options = {
        "defaultColDef": {
            "sortable": True,
            "filter": True,
            "resizable": True,
        },
        "columnDefs": [
            {"headerName": "Mã", "field": "ticker", "pinned": "left", "width": 90},
            {
                "headerName": "Khối lượng",
                "field": "quantity",
                "width": 120,
                ":valueFormatter": "params => params.value.toLocaleString('vi-VN')",
            },
            {"headerName": "Giá vốn", "field": "avg_price", "width": 110},
            {"headerName": "Giá thị trường", "field": "market_price", "width": 135},
            {
                "headerName": "Giá trị",
                "field": "market_value",
                "minWidth": 145,
                ":valueFormatter": "params => params.value.toLocaleString('vi-VN')",
            },
            {
                "headerName": "Lãi/Lỗ",
                "field": "pnl",
                "minWidth": 135,
                ":valueFormatter": "params => params.value.toLocaleString('vi-VN')",
                ":cellStyle": (
                    f"params => params.value >= 0 "
                    f"? {{color: '{THEME['positive']}', fontWeight: 600}} "
                    f": {{color: '{THEME['negative']}', fontWeight: 600}}"
                ),
            },
            {
                "headerName": "Tỷ trọng",
                "field": "weight",
                "width": 110,
                ":valueFormatter": "params => `${params.value.toFixed(1)}%`",
            },
        ],
        "rowData": PORTFOLIO_ROWS,
    }

    return ui.aggrid(
        options,
        theme="quartz",
        auto_size_columns=False,
    ).classes("w-full h-[380px]")


# =============================================================================
# Tab contents
# =============================================================================

def overview_tab_content() -> None:
    symbol_sources = {
        # main
            'remaining_vnindex': {'symbol': 'VNINDEX_NOT_VIN', 'source': 'custom', 'color': '#A0AEC0', 'label_name': 'Remaining VNINDEX', 'target': 'main', },
            'vnindex': {'symbol': 'VNINDEX', 'source': 'index', 'color': '#03FD10', 'label_name': 'VNINDEX', 'target': 'main', },
            'btc': {'symbol': 'BTC-USD', 'source': 'other', 'color': '#F7931A', 'label_name': 'BTC-USD', 'target': 'main', },
            'spx': {'symbol': '^SPX', 'source': 'other', 'color': '#3182CE', 'label_name': 'SPX', 'target': 'main', },
            'ndx': {'symbol': '^NDX', 'source': 'other', 'color': '#00B5D8', 'label_name': 'NDX', 'target': 'main', },
            'gcz': {'symbol': '^GCZ', 'source': 'other', 'color': '#ECC94B', 'label_name': 'Gold', 'target': 'main', },
            'lcoz': {'symbol': '^LCOZ', 'source': 'other', 'color': '#E53E3E', 'label_name': 'Oil', 'target': 'main', },    
        # sub main
            'dxy': {'symbol':'DX-Y.NYB','source':'other','color':'#A0AEC0','label_name':'DX-Y.NYB','target':'sub'},
            #'USBY10Y' : {'symbol':'USBY10Y','source':'other','color':'#FFAA00','label_name':'US Bond 10Y','target':'sub'},
            #'VIX' : {'symbol':'^VIX','source':'other','color':'#FFAA00','label_name':'VIX','target':'sub'},
            'VND=X' : {'symbol':'VND=X','source':'other','color':'#FFAA00','label_name':'USD to VND','target':'sub'},
        }
    
    with ui.element("div").classes(
        "grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-4 w-full"
    ):
        metric_card(
            "VN-Index",
            "1,286.42",
            "+1.18% hôm nay",
            positive=True,
            icon="trending_up",            
        )
        metric_card(
            "GTGD HOSE",
            "18.6 nghìn tỷ",
            "+12.4% so với TB20",
            positive=True,
            icon="payments",
        )
        metric_card(
            "Độ rộng",
            "268 / 151",
            "Nghiêng về bên mua",
            positive=True,
            icon="compare_arrows",
        )
        metric_card(
            "Khối ngoại",
            "-642 tỷ",
            "Bán ròng",
            positive=False,
            icon="public",
        )
        metric_card(
            "Tự Doanh",
            "-1 tỷ",
            "Bán ròng",
            positive=False,
            icon="account_balance",
            )

    with ui.element("div").classes(
        "grid grid-cols-1 xl:grid-cols-12 gap-4 w-full mt-4"
    ):
        with ui.card().classes(card_classes("p-4 xl:col-span-8 w-full min-w-0")):
            with ui.row().classes("w-full items-center justify-between"):
                section_title(
                    "Intermarket",
                    "Biến động của VN-Index so với BTC, SPX, NDX, Gold và Oil",
                )
                ui.badge("ECharts").classes(
                    f"bg-[{THEME['primary']}] text-black"
                )
            intermarket_chart = draw_comparision_main_sub(
                start_date=CHART_START_DATE,
                symbol_sources=symbol_sources,
            )
            ui.html(
                build_chart_iframe_html(
                    intermarket_chart,
                    height=IFRAME_HEIGHT,
                ),
                sanitize=False,
            ).classes("w-full min-w-0")

        with ui.card().classes(card_classes("p-4 xl:col-span-4")):
            section_title("Hiệu suất ngành", "Mức thay đổi trong phiên")
            ui.echart(sector_chart_options()).classes("w-full")

        with ui.card().classes(card_classes("p-4 xl:col-span-8 w-full min-w-0")):
            with ui.row().classes("w-full items-center justify-between"):
                section_title(
                    "Diễn biến thị trường",
                    "Tỷ lệ tổng số Ticker > MA20, MA50, MA100 và MA200",
                )
                ui.badge("ECharts").classes(
                    f"bg-[{THEME['primary']}] text-black"
                )            
            market_breadth_chart = draw_ticker_above_MA(CHART_START_DATE)
            ui.html(
                build_chart_iframe_html(
                    market_breadth_chart,
                    height=IFRAME_HEIGHT,
                ),
                sanitize=False,
            ).classes("w-full min-w-0")

def market_tab_content() -> None:
    df = view_to_dataframe("vw_Ticker", condition="Status = 'Y'",)    

    with ui.element("div").classes(
        "grid grid-cols-1 xl:grid-cols-12 gap-4 w-full"
    ):
        with ui.card().classes(
            card_classes("p-4 xl:col-span-12 h-full")
        ):
            section_title(
                "Stock Screener",
                "Lọc cổ phiếu theo giá, MA20, MA50, RSI, P/E và xu hướng",
            )

            create_market_grid(
                df=df,
                filter_configs=NiceGUI_grid_market_tb.filter_configs,
                field_configs=NiceGUI_grid_market_tb.field_configs,
            )


def portfolio_tab_content() -> None:
    with ui.element("div").classes(
        "grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 w-full"
    ):
        metric_card(
            "Giá trị danh mục",
            "1.078 tỷ",
            "+86.9 triệu",
            positive=True,
            icon="account_balance_wallet",
        )
        metric_card(
            "Lãi/Lỗ hôm nay",
            "+14.2 triệu",
            "+1.34%",
            positive=True,
            icon="trending_up",
        )
        metric_card(
            "Tiền mặt",
            "146.5 triệu",
            "12.0% tài sản",
            positive=True,
            icon="savings",
        )
        metric_card(
            "Max Drawdown",
            "-8.42%",
            "Trong 12 tháng",
            positive=False,
            icon="waterfall_chart",
        )

    with ui.element("div").classes(
        "grid grid-cols-1 xl:grid-cols-12 gap-4 w-full mt-4"
    ):
        with ui.card().classes(card_classes("p-4 xl:col-span-4")):
            section_title("Phân bổ danh mục", "Ví dụ ECharts donut")
            ui.echart(allocation_chart_options()).classes("w-full h-[390px]")

        with ui.card().classes(card_classes("p-4 xl:col-span-8 w-full min-w-0")):
            section_title("Vị thế đang nắm giữ", "Ví dụ AG Grid cho portfolio")
            create_portfolio_grid()


# =============================================================================
# Page layout: Header, Sidebar and Tabs
# =============================================================================

def build_page() -> None:
    ui.colors(primary=THEME["primary"])

    ui.add_css(
        f"""
        body {{
            background: {THEME['background']};
            color: {THEME['text']};
        }}

        .q-page,
        .q-layout,
        .nicegui-content {{
            background: {THEME['background']};
        }}

        .dashboard-card {{
            overflow: hidden;
        }}

        .q-tab {{
            min-height: 42px;
        }}

        .ag-root-wrapper {{
            border-color: {THEME['border']} !important;
        }}
        """
    )

    with ui.left_drawer(value=False).classes(
        f"bg-[{THEME['surface']}] border-r border-[{THEME['border']}]"
    ) as drawer:
        with ui.row().classes("items-center gap-3 px-3 pt-3 pb-5"):
            ui.icon("candlestick_chart").classes(
                f"text-3xl text-[{THEME['primary']}]"
            )
            with ui.column().classes("gap-0"):
                ui.label("CherryStock").classes("text-lg font-semibold")
                ui.label("Financial Terminal").classes(
                    f"text-xs text-[{THEME['muted']}]"
                )

        ui.label("MENU").classes(
            f"text-xs tracking-widest text-[{THEME['muted']}] px-3"
        )

        navigation = [
            ("Dashboard", "dashboard"),
            ("Thị trường", "show_chart"),
            ("Screener", "filter_alt"),
            ("Danh mục", "account_balance_wallet"),
            ("Watchlist", "star"),
            ("Báo cáo", "analytics"),
        ]

        for index, (label, icon) in enumerate(navigation):
            button = ui.button(label, icon=icon).props(
                "flat align=left no-caps"
            ).classes("w-full justify-start rounded-lg")
            if index == 0:
                button.classes(f"bg-[{THEME['surface_alt']}]")

        ui.separator().classes(f"my-4 bg-[{THEME['border']}]")
        ui.button("Cảnh báo", icon="notifications_active").props(
            "flat align=left no-caps"
        ).classes("w-full justify-start")
        ui.button("Cài đặt", icon="settings").props(
            "flat align=left no-caps"
        ).classes("w-full justify-start")

    with ui.header().classes(
        f"h-16 px-4 items-center justify-between "
        f"bg-[{THEME['surface']}] border-b border-[{THEME['border']}]"
    ):
        with ui.row().classes("items-center gap-3 no-wrap"):
            ui.button(
                icon="menu",
                on_click=drawer.toggle,
            ).props("flat round dense")
            with ui.column().classes("gap-0"):
                ui.label("Cherry Stock").classes("font-semibold text-2xl")

        with ui.row().classes("items-center gap-2 no-wrap"):
            ui.input(placeholder="Tìm mã cổ phiếu...").props(
                "dense outlined rounded debounce=300"
            ).classes("hidden sm:flex w-56 lg:w-72")
            ui.button(
                icon="refresh",
                on_click=lambda: ui.notify("Đã làm mới dữ liệu mô phỏng"),
            ).props("flat round")
            ui.button(icon="notifications").props("flat round")
            ui.avatar("B").classes(
                f"bg-[{THEME['primary']}] font-semibold"
            )

    with ui.column().classes("w-full max-w-[2600px] mx-auto p-4 md:p-6 gap-4"):
        with ui.row().classes("w-full items-end justify-between"):
            with ui.column().classes("gap-0"):
                ui.label("Overview").classes(
                    "text-2xl md:text-3xl font-semibold"
                )
            ui.select(
                ["Phiên hiện tại", "1 tuần", "1 tháng", "3 tháng"],
                value="Phiên hiện tại",
            ).props("dense outlined").classes("hidden md:flex w-40")

        with ui.tabs().classes(
            f"w-full rounded-lg bg-[{THEME['surface']}] "
            f"border border-[{THEME['border']}]"
        ).props("align=left inline-label") as tabs:
            ui.tab("overview", label="Tổng Quan", icon="dashboard")
            ui.tab("market", label="Lọc Cổ Phiếu", icon="show_chart")
            ui.tab("portfolio", label="Danh mục", icon="account_balance_wallet")

        with ui.tab_panels(
            tabs,
            value="overview",
        ).classes("w-full bg-transparent p-0").props("animated keep-alive"):
            with ui.tab_panel("overview").classes("p-0"):
                overview_tab_content()

            with ui.tab_panel("market").classes("p-0"):
                market_tab_content()

            with ui.tab_panel("portfolio").classes("p-0"):
                portfolio_tab_content()


build_page()

ui.run(
        host="0.0.0.0",
        port=8081,
        title="CherryStock Dashboard",
        dark=True,
        reload=False,
    )