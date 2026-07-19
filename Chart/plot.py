from typing import Literal, Optional, Sequence, Tuple, Union
import pandas as pd
from lightweight_charts import JupyterChart
from Ults.DuckLib import DuckDBManager


def _prepare_line_df(data: pd.DataFrame, name: str, line_name: str) -> pd.DataFrame:
    """
    Validate dữ liệu line và trả về DataFrame chuẩn để set vào line.
    """
    if data is None or data.empty:
        raise ValueError(f"Dữ liệu của line '{name}' đang rỗng.")

    required_columns = {"time", name}
    missing_columns = required_columns - set(data.columns)

    if missing_columns:
        raise ValueError(
            f"Line '{name}' thiếu cột: {sorted(missing_columns)}. "
            f"Các cột hiện có: {list(data.columns)}"
        )

    line_df = data[["time", name]].copy()
    if line_name != name:
        line_df = line_df.rename(columns={name: line_name})

    return line_df

def plotTicker(ticker: str, timeframe: str = "Daily"):
    """
    Vẽ chart nến cho mã cổ phiếu từ bảng raw_stock_eod.
    timeframe: "Daily", "weekly", "monthly"
    """
    timeframe = timeframe.strip().lower()
    con = DuckDBManager.get_connection(read_only=False)

    sql = f"""
    SELECT
        Date,
        Open,
        High,
        Low,
        Close,
        Volume
    FROM "CherryMon"."main"."raw_stock_eod"
    WHERE Ticker = '{ticker}'
    ORDER BY Date
    """
    df = con.execute(sql).df()

    if df.empty:
        raise ValueError(f"No data for ticker={ticker}")

    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date")

    if timeframe == "daily":
        df_resampled = df
    elif timeframe == "weekly":
        df_resampled = df.resample("W-FRI").agg({
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
            "Volume": "sum",
        })
    elif timeframe == "monthly":
        df_resampled = df.resample("ME").agg({
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
            "Volume": "sum",
        })
    else:
        raise ValueError("timeframe phải là Daily, weekly hoặc monthly")

    df_resampled = df_resampled.dropna(subset=["Open", "High", "Low", "Close"]).reset_index()
    df_resampled = df_resampled.rename(columns={
        "Date": "date",
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume",
    })

    chart = JupyterChart(width=900, height=550)
    chart.set(df_resampled)
    chart.load()
    return chart

def init_chart(
    width: int = 1200,
    height: int = 550,
    inner_width: float = 1,
    inner_height: float = 1,
    background_color: str = "#121314",
    text_color: str = "#FFFFFF",
    legend_visible=True
) -> JupyterChart:
    """
    Khởi tạo và cấu hình giao diện chung cho JupyterChart.
    Chưa gọi chart.load().
    """
    chart = JupyterChart(
        width=width,
        height=height,
        inner_width=inner_width,  # pyright: ignore[reportArgumentType]
        inner_height=inner_height,  # pyright: ignore[reportArgumentType]
    )

    chart.layout(
        background_color=background_color,
        text_color=text_color,
    )

    chart.legend(
        visible=legend_visible,
        ohlc=False,
        percent=False,
        lines=True,
        color="#FFFFFF",
        font_size=13,
        font_family="Arial",
    )

    return chart

def add_line(
    chart: JupyterChart,
    data: pd.DataFrame,
    name: str = "Y",
    color: str = "#FFFFFF",
    width: int = 1,
    price_line: bool = False,
    price_label: bool = False,
    price_scale_id: Optional[str] = None,
    label_name: Optional[str] = None,
):
    """
    Tạo line và gán dữ liệu vào chart.

    DataFrame cần có:
    - time
    - cột dữ liệu có tên trùng với `name`
    """
    line_name = label_name if label_name else name

    line_df = _prepare_line_df(data=data, name=name, line_name=line_name)

    line = chart.create_line(
        name=line_name,
        color=color,
        width=width,
        price_line=price_line,
        price_label=price_label,
        price_scale_id=price_scale_id,
    )

    line.set(line_df)

    return line


def create_subchart(
    chart: JupyterChart,
    position: Literal["left", "right", "top", "bottom"] = "bottom",
    width: float = 1,
    height: float = 0.3,
    sync: Optional[Union[str, bool]] = None,
    scale_candles_only: bool = False,
    sync_crosshairs_only: bool = False,
    toolbox: bool = False,
):
    """
    Tạo subchart từ chart chính.
    """
    # lightweight_charts hiện render position bằng CSS float.
    # Với top/bottom, ép layout cột để tránh pane phụ bị ẩn trong Interactive/Jupyter.
    effective_position = "left" if position in ("top", "bottom") else position
    effective_width = 1 if position in ("top", "bottom") else width

    subchart = chart.create_subchart(
        position=effective_position,
        width=effective_width,
        height=height,
        sync=sync,
        scale_candles_only=scale_candles_only,
        sync_crosshairs_only=sync_crosshairs_only,
        toolbox=toolbox,
    )

    if position in ("top", "bottom"):
        sub_ratio = max(0.1, min(0.9, float(height)))
        main_ratio = max(0.1, min(0.9, 1.0 - sub_ratio))

        chart.run_script(
            f"""
            window.containerDiv.style.display = 'block';

            {chart.id}.wrapper.style.float = 'none';
            {subchart.id}.wrapper.style.float = 'none';
            {chart.id}.wrapper.style.display = 'block';
            {subchart.id}.wrapper.style.display = 'block';

            {chart.id}.wrapper.style.width = '100%';
            {subchart.id}.wrapper.style.width = '100%';

            const __totalH = window.innerHeight || 700;
            const __mainH = Math.max(220, Math.floor(__totalH * {main_ratio:.6f}));
            const __subH = Math.max(140, Math.floor(__totalH * {sub_ratio:.6f}));

            {chart.id}.wrapper.style.height = __mainH + 'px';
            {subchart.id}.wrapper.style.height = __subH + 'px';

            {chart.id}.chart.resize(window.innerWidth, __mainH);
            {subchart.id}.chart.resize(window.innerWidth, __subH);

            {subchart.id}.wrapper.style.marginTop = '6px';
            """
        )

    return subchart


def init_subchart(
    chart: JupyterChart,
    position: Literal["left", "right", "top", "bottom"] = "bottom",
    width: float = 1,
    height: float = 0.3,
    sync: Optional[Union[str, bool]] = None,
    scale_candles_only: bool = False,
    sync_crosshairs_only: bool = False,
    toolbox: bool = False,
    background_color: str = "#0F1820",
    text_color: str = "#FFAA00",
    legend_visible: bool = True,
    legend_color: str = "#FFFFFF",
    legend_font_size: int = 13,
    legend_font_family: str = "Arial",
    border_color: Optional[str] = "#FFAA00",
    border_width: int = 0,
):
    """
    Khởi tạo subchart theo một cấu hình tiêu chuẩn:
    - create_subchart
    - layout
    - border wrapper (tuỳ chọn)
    """
    subchart = create_subchart(
        chart=chart,
        position=position,
        width=width,
        height=height,
        sync=sync,
        scale_candles_only=scale_candles_only,
        sync_crosshairs_only=sync_crosshairs_only,
        toolbox=toolbox,
    )

    subchart.layout(
        background_color=background_color,
        text_color=text_color,
    )

    subchart.legend(
        visible=legend_visible,
        ohlc=False,
        percent=False,
        lines=True,
        color=legend_color,
        font_size=legend_font_size,
        font_family=legend_font_family,
    )

    if border_color and border_width > 0:
        subchart.run_script(
            f"{subchart.id}.wrapper.style.border = '{border_width}px solid {border_color}';"
        )

    return subchart


def subchart_add_line(
    subchart,
    data: pd.DataFrame,
    name: str = "Y",
    color: str = "#FFFFFF",
    width: int = 1,
    price_line: bool = False,
    price_label: bool = False,
    price_scale_id: Optional[str] = None,
    label_name: Optional[str] = None,
):
    """
    Tạo line và gán dữ liệu vào subchart.

    DataFrame cần có:
    - time
    - cột dữ liệu có tên trùng với `name`
    """
    line_name = label_name if label_name else name
    line_df = _prepare_line_df(data=data, name=name, line_name=line_name)

    line = subchart.create_line(
        name=line_name,
        color=color,
        width=width,
        price_line=price_line,
        price_label=price_label,
        price_scale_id=price_scale_id,
    )

    line.set(line_df)

    return line

def load_chart(
    chart: JupyterChart,
    precision: int = 1,
    subcharts: Optional[Sequence] = None,
    visible_range: Optional[Tuple[str, str]] = None,
    price_scale_min_width: Optional[int] = None,
) -> None:
    """
    Áp dụng formatter số âm bằng dấu '-' ASCII và render chart.
    Phải gọi sau khi hoàn tất việc thêm các line.
    """
    if precision < 0:
        raise ValueError("precision phải lớn hơn hoặc bằng 0.")

    if price_scale_min_width is not None and price_scale_min_width < 0:
        raise ValueError("price_scale_min_width phải lớn hơn hoặc bằng 0.")

    script_parts = [
        f"""
        function __copilot_fadeColor(color, alpha) {{
            if (!color) return color;
            if (color.startsWith('rgba')) {{
                return color.replace(/rgba\\(([^,]+),([^,]+),([^,]+),[^\\)]+\\)/, 'rgba($1,$2,$3,' + alpha + ')');
            }}
            if (color.startsWith('rgb(')) {{
                return color.replace(/rgb\\(([^,]+),([^,]+),([^\\)]+)\\)/, 'rgba($1,$2,$3,' + alpha + ')');
            }}
            if (color.startsWith('#')) {{
                let hex = color.slice(1);
                if (hex.length === 3) {{
                    hex = hex.split('').map(function(ch) {{ return ch + ch; }}).join('');
                }}
                const r = parseInt(hex.slice(0, 2), 16);
                const g = parseInt(hex.slice(2, 4), 16);
                const b = parseInt(hex.slice(4, 6), 16);
                return 'rgba(' + r + ',' + g + ',' + b + ',' + alpha + ')';
            }}
            return color;
        }}

        function __copilot_attach_legend_highlight(handler) {{
            if (!handler || handler.__copilotLegendHighlightBound) return;
            handler.__copilotLegendHighlightBound = true;

            const getItems = function() {{
                return (handler.legend && handler.legend._lines) ? handler.legend._lines : [];
            }};

            const resetAll = function() {{
                getItems().forEach(function(item) {{
                    item.series.applyOptions({{ color: item.solid }});
                    if (item.originalLineWidth !== undefined) {{
                        item.series.applyOptions({{ lineWidth: item.originalLineWidth }});
                    }}
                    item.row.style.opacity = '1';
                }});
                handler.__copilotLegendSelected = null;
            }};

            const applyHighlight = function(selectedItem) {{
                const items = getItems();
                const wasSelected = handler.__copilotLegendSelected === selectedItem;

                if (wasSelected) {{
                    resetAll();
                    return;
                }}

                handler.__copilotLegendSelected = selectedItem;

                items.forEach(function(item) {{
                    if (item.originalLineWidth === undefined) {{
                        const opts = item.series.options ? item.series.options() : {{}};
                        item.originalLineWidth = opts.lineWidth || 2;
                    }}

                    if (item === selectedItem) {{
                        item.series.applyOptions({{ color: item.solid }});
                        item.series.applyOptions({{ lineWidth: Math.max(2, item.originalLineWidth + 1) }});
                        item.row.style.opacity = '1';
                    }} else {{
                        item.series.applyOptions({{ color: __copilot_fadeColor(item.solid, 0.18) }});
                        item.row.style.opacity = '0.55';
                    }}
                }});
            }};

            getItems().forEach(function(item) {{
                if (!item || !item.row) return;
                item.row.style.cursor = 'pointer';
                item.row.addEventListener('click', function(ev) {{
                    ev.preventDefault();
                    ev.stopPropagation();
                    applyHighlight(item);
                }});
            }});

            if (handler.div) {{
                handler.div.addEventListener('dblclick', function() {{
                    resetAll();
                }});
            }}
        }}

        {chart.id}.chart.applyOptions({{
            localization: {{
                priceFormatter: function(price) {{
                    return (price < 0 ? '-' : '')
                        + Math.abs(price).toFixed({precision});
                }}
            }}
        }});

        {chart.id}.legend.div.style.display = 'flex';
        {chart.id}.legend.ohlcEnabled = false;
        {chart.id}.legend.percentEnabled = false;
        {chart.id}.legend.linesEnabled = true;
        __copilot_attach_legend_highlight({chart.id});
        if ({chart.id}.legend && {chart.id}.legend._lines) {{
            {chart.id}.legend._lines.forEach(function(item) {{
                item.row.style.display = 'flex';
                if (!item.div.innerText || !item.div.innerText.trim()) {{
                    item.div.innerHTML = '<span style="color: ' + item.solid + ';"></span>    ' + item.name;
                }}
            }});
        }}
        """
    ]

    if price_scale_min_width is not None:
        script_parts.append(
            f"""
            {chart.id}.chart.applyOptions({{rightPriceScale: {{minimumWidth: {price_scale_min_width}}}}});
            """
        )

    if visible_range is not None:
        start_time, end_time = visible_range
        script_parts.append(
            f"""
            {chart.id}.chart.timeScale().setVisibleRange({{from: '{start_time}', to: '{end_time}'}});
            """
        )

    if subcharts:
        for subchart in subcharts:
            script_parts.append(
                f"""
                {subchart.id}.chart.applyOptions({{
                    localization: {{
                        priceFormatter: function(price) {{
                            return (price < 0 ? '-' : '')
                                + Math.abs(price).toFixed({precision});
                        }}
                    }}
                }});

                {subchart.id}.legend.div.style.display = 'flex';
                {subchart.id}.legend.ohlcEnabled = false;
                {subchart.id}.legend.percentEnabled = false;
                {subchart.id}.legend.linesEnabled = true;
                __copilot_attach_legend_highlight({subchart.id});
                if ({subchart.id}.legend && {subchart.id}.legend._lines) {{
                    {subchart.id}.legend._lines.forEach(function(item) {{
                        item.row.style.display = 'flex';
                        if (!item.div.innerText || !item.div.innerText.trim()) {{
                            item.div.innerHTML = '<span style="color: ' + item.solid + ';"></span>    ' + item.name;
                        }}
                    }});
                }}
                """
            )

            if price_scale_min_width is not None:
                script_parts.append(
                    f"""
                    {subchart.id}.chart.applyOptions({{rightPriceScale: {{minimumWidth: {price_scale_min_width}}}}});
                    """
                )

            if visible_range is not None:
                start_time, end_time = visible_range
                script_parts.append(
                    f"""
                    {subchart.id}.chart.timeScale().setVisibleRange({{from: '{start_time}', to: '{end_time}'}});
                    """
                )

    chart.run_script("\n".join(script_parts))

    chart.load()

def draw_comparision_main_sub(start_date: str = '2025-03-23', symbol_sources: Optional[dict] = None):
    from timeit import timeit
    import importlib
    import pandas as pd
    import Chart.plot as plot
    importlib.reload(plot)
    from DuckDB.Data import get_symbol, upd_symbol_percent, _align_to_base_time, _normalize_time
    from Chart.plot import init_chart, add_line, init_subchart, subchart_add_line, load_chart

    base_time_df = pd.DataFrame({
        'time': pd.date_range(
            start=pd.to_datetime(start_date),
            end=pd.Timestamp.today().normalize(),
            freq='D',
        ).strftime('%Y-%m-%d')
    })
    visible_range = None
    if not base_time_df.empty:
        start_time = base_time_df['time'].iloc[0]
        end_time = base_time_df['time'].iloc[-1]
        visible_range = (start_time, end_time)

    def _get_linebar_symbol(symbol: str, source: str) -> pd.DataFrame:
        raw_df = upd_symbol_percent(get_symbol(symbol, start_date, source=source))
        return _align_to_base_time(base_time_df, _normalize_time(raw_df))

    if symbol_sources is None:
        symbol_sources = {
            'vnindex': {
                'symbol': 'VNINDEX',
                'source': 'index',
                'color': '#03FD10',
                'label_name': 'VNINDEX',
                'target': 'main',
            },
        }

    df = {
        key: _get_linebar_symbol(cfg['symbol'], cfg['source'])
        for key, cfg in symbol_sources.items()
    }

    chart = init_chart(width=1000, height=600, inner_width=1, inner_height=0.7)
    subchart = init_subchart(chart=chart,sync=chart.id)
    for key, cfg in symbol_sources.items():
        target = cfg.get('target', 'main')
        color = cfg.get('color', '#FFFFFF')
        label_name = cfg.get('label_name') or cfg.get('symbol') or key

        if target == 'main':
            add_line(chart=chart, color=color, label_name=label_name, data=df[key])
        else:
            subchart_add_line(subchart=subchart, color=color, label_name=label_name, data=df[key])
    load_chart(chart=chart,subcharts=[subchart],visible_range=visible_range,price_scale_min_width=80)