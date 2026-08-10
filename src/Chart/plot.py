from html import escape
from typing import Literal, Optional, Sequence, Tuple, Union

import pandas as pd
from IPython.display import HTML, display
from lightweight_charts import JupyterChart
from sympy import plot
from Ults.DuckLib import DuckDBManager
from DuckDB import Data
from Ults.lstPara import CHART_START_DATE, IFRAME_HEIGHT, IFRAME_WIDTH, PRICE_SCALE_MIN_WIDTH


def _patched_jupyter_chart_load(self):
    """Ensure generated chart HTML declares UTF-8 charset."""
    if HTML is None:
        raise ModuleNotFoundError('IPython.display.HTML was not found, and must be installed to use JupyterChart.')

    html_source = self._html
    if '<meta charset=' not in html_source.lower():
        if '<head>' in html_source.lower():
            html_source = html_source.replace('<head>', '<head>\n<meta charset="UTF-8">', 1)
        elif '<html>' in html_source.lower():
            html_source = html_source.replace('<html>', '<html>\n<head><meta charset="UTF-8"></head>', 1)
        else:
            html_source = f'<head><meta charset="UTF-8"></head>{html_source}'

    html_code = escape(f"{html_source}</script></body></html>")
    iframe = f'<iframe width="{self.width}" height="{self.height}" frameBorder="0" srcdoc="{html_code}"></iframe>'
    display(HTML(iframe))


JupyterChart._load = _patched_jupyter_chart_load


def build_chart_iframe_html(
    chart: JupyterChart,
    width: int | str | None = None,
    height: int | None = None,
) -> str:
    """Build responsive iframe HTML for embedding a lightweight chart."""
    html_source = getattr(chart, "_html", None)
    if not html_source:
        return '<div style="padding:12px;color:#888;">Chart is not ready yet.</div>'

    if '<meta charset=' not in html_source.lower():
        if '<head>' in html_source.lower():
            html_source = html_source.replace(
                '<head>',
                '<head>\n<meta charset="UTF-8">',
                1,
            )
        elif '<html>' in html_source.lower():
            html_source = html_source.replace(
                '<html>',
                '<html>\n<head><meta charset="UTF-8"></head>',
                1,
            )
        else:
            html_source = f'<head><meta charset="UTF-8"></head>{html_source}'

    html_code = escape(f"{html_source}</script></body></html>")
    iframe_height = height or getattr(chart, "height", IFRAME_HEIGHT)

    if width is None:
        width_css = "100%"
    elif isinstance(width, int):
        width_css = f"{width}px"
    else:
        width_css = width

    return (
        '<iframe '
        'width="100%" '
        f'height="{iframe_height}" '
        'frameborder="0" '
        f'style="width:{width_css};max-width:100%;min-width:0;height:{iframe_height}px;border:0;display:block;box-sizing:border-box;" '
        f'srcdoc="{html_code}"></iframe>'
    )


def _prepare_line_df(data: pd.DataFrame, name: str, line_name: str) -> pd.DataFrame:
    """
    Validate dữ liệu line và trả về DataFrame chuẩn để set vào line.
    """
    if data is None or data.empty:
        raise ValueError(f"Dữ liệu của line '{name}' đang rỗng.")

    if name in data.columns:
        source_column = name
    else:
        value_columns = [col for col in data.columns if col != "time"]
        if len(value_columns) == 1:
            source_column = value_columns[0]
        else:
            raise ValueError(
                f"Line '{name}' thiếu cột: {sorted({'time', name} - set(data.columns))}. "
                f"Các cột hiện có: {list(data.columns)}"
            )

    line_df = data[["time", source_column]].copy()
    if line_name != source_column:
        line_df = line_df.rename(columns={source_column: line_name})

    return line_df

def plotTicker(ticker: str, timeframe: str = "Daily"):
    """
    Vẽ chart nến cho mã cổ phiếu từ bảng raw_stock_eod.
    timeframe: "Daily", "weekly", "monthly"
    """
    timeframe = timeframe.strip().lower()

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
    with DuckDBManager(read_only=True) as con:
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

    chart = JupyterChart(width=IFRAME_WIDTH, height=IFRAME_HEIGHT)
    chart.set(df_resampled)
    chart.load()
    return chart

def init_chart(
    width: int = IFRAME_WIDTH,
    height: int = IFRAME_HEIGHT,
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

def _create_line_with_data(
    chart,
    data: pd.DataFrame,
    *,
    name: str,
    color: str,
    width: int,
    price_line: bool,
    price_label: bool,
    price_scale_id: Optional[str],
    label_name: Optional[str],
):
    line_name = label_name or name
    line = chart.create_line(
        name=line_name,
        color=color,
        width=width,
        price_line=price_line,
        price_label=price_label,
        price_scale_id=price_scale_id,
    )
    line.set(_prepare_line_df(data, name, line_name))
    return line

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
    hide_data: bool = False,
):
    """Tạo line, chuẩn hóa dữ liệu và gán vào chart."""
    line = _create_line_with_data(
        chart,
        data,
        name=name,
        color=color,
        width=width,
        price_line=price_line,
        price_label=price_label,
        price_scale_id=price_scale_id,
        label_name=label_name,
    )
    if hide_data:
        line.hide_data()
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
                if (window.containerDiv && window.containerDiv.style) {{
                    window.containerDiv.style.display = 'block';
                }}

            {chart.id}.wrapper.style.float = 'none';
            {subchart.id}.wrapper.style.float = 'none';
            {chart.id}.wrapper.style.display = 'block';
            {subchart.id}.wrapper.style.display = 'block';

            {chart.id}.wrapper.style.width = '100%';
            {subchart.id}.wrapper.style.width = '100%';

            const __totalH = {int(getattr(chart, 'height', IFRAME_HEIGHT))};
            const __mainH = Math.max(220, Math.floor(__totalH * {main_ratio:.6f}));
            const __subH = Math.max(140, __totalH - __mainH - 6);

            {chart.id}.wrapper.style.height = __mainH + 'px';
            {subchart.id}.wrapper.style.height = __subH + 'px';

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
    """Tạo line và gán dữ liệu vào subchart."""
    return _create_line_with_data(
        subchart,
        data,
        name=name,
        color=color,
        width=width,
        price_line=price_line,
        price_label=price_label,
        price_scale_id=price_scale_id,
        label_name=label_name,
    )

def _enable_responsive_resize(
    chart: JupyterChart,
    *,
    height: int,
    subcharts: Optional[Sequence] = None,
) -> None:
    """Make chart wrappers follow the iframe viewport width."""
    subcharts = list(subcharts or [])

    sub_resize = []
    sub_observe = []
    for subchart in subcharts:
        sub_resize.append(
            f"""
            if ({subchart.id} && {subchart.id}.wrapper) {{
                {subchart.id}.wrapper.style.width = '100%';
                const __subH = Math.max(1, {subchart.id}.wrapper.clientHeight);
                {subchart.id}.chart.resize(__viewportWidth, __subH);
            }}
            """
        )
        sub_observe.append(
            f"if ({subchart.id} && {subchart.id}.wrapper) __observer.observe({subchart.id}.wrapper);"
        )

    chart.run_script(
        f"""
        (() => {{
            document.documentElement.style.width = '100%';
            document.documentElement.style.margin = '0';
            document.documentElement.style.overflowX = 'hidden';
            document.body.style.width = '100%';
            document.body.style.margin = '0';
            document.body.style.overflowX = 'hidden';

            if (window.containerDiv) {{
                window.containerDiv.style.width = '100%';
                window.containerDiv.style.maxWidth = '100%';
                window.containerDiv.style.overflow = 'hidden';
            }}

            const __resizeAllCharts = () => {{
                try {{
                    const __viewportWidth = Math.max(
                        1,
                        document.documentElement.clientWidth || window.innerWidth || {getattr(chart, 'width', IFRAME_WIDTH)}
                    );

                    if ({chart.id} && {chart.id}.wrapper) {{
                        {chart.id}.wrapper.style.width = '100%';
                        {chart.id}.wrapper.style.maxWidth = '100%';
                        const __mainH = Math.max(1, {chart.id}.wrapper.clientHeight || {height});
                        {chart.id}.chart.resize(__viewportWidth, __mainH);
                    }}

                    {''.join(sub_resize)}
                }} catch (error) {{
                    console.debug('Chart resize skipped:', error);
                }}
            }};

            const __observer = new ResizeObserver(() => {{
                window.requestAnimationFrame(__resizeAllCharts);
            }});

            if ({chart.id} && {chart.id}.wrapper) __observer.observe({chart.id}.wrapper);
            if (window.containerDiv) __observer.observe(window.containerDiv);
            {''.join(sub_observe)}

            window.addEventListener('resize', __resizeAllCharts, {{passive: true}});
            window.requestAnimationFrame(__resizeAllCharts);
            setTimeout(__resizeAllCharts, 50);
            setTimeout(__resizeAllCharts, 250);
        }})();
        """
    )


def load_chart(
    chart: JupyterChart,
    precision: int = 1,
    subcharts: Optional[Sequence] = None,
    visible_range: Optional[Tuple[str, str]] = None,
    price_scale_min_width: Optional[int] = PRICE_SCALE_MIN_WIDTH,
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

        function __copilot_render_horizontal_legend(handler, legendId) {{
            if (!handler || !handler.wrapper) return;

            let legendDiv = handler.wrapper.querySelector('#' + legendId);
            if (!legendDiv) {{
                legendDiv = document.createElement('div');
                legendDiv.id = legendId;
                legendDiv.style.position = 'absolute';
                legendDiv.style.top = '8px';
                legendDiv.style.left = '8px';
                legendDiv.style.zIndex = '4500';
                legendDiv.style.display = 'flex';
                legendDiv.style.flexWrap = 'wrap';
                legendDiv.style.alignItems = 'center';
                legendDiv.style.gap = '8px 12px';
                legendDiv.style.fontSize = '12px';
                legendDiv.style.color = '#FFFFFF';
                legendDiv.style.pointerEvents = 'auto';
                handler.wrapper.appendChild(legendDiv);
            }}

            legendDiv.innerHTML = '';
            const items = (handler.legend && handler.legend._lines) ? handler.legend._lines : [];
            if (!handler.__copilotHiddenByKey) {{
                handler.__copilotHiddenByKey = {{}};
            }}

            const hiddenByKey = handler.__copilotHiddenByKey;

            const getItemKey = function(item, idx) {{
                const namePart = (item && item.name) ? String(item.name) : 'series';
                return String(idx) + '::' + namePart;
            }};

            function applyLegendState() {{
                const selectedKey = handler.__copilotLegendSelectedKey || null;
                const selectionOn = !!selectedKey;

                items.forEach(function(item, idx) {{
                    if (!item || !item.series) return;

                    const itemKey = getItemKey(item, idx);

                    if (item.__copilotOriginalLineWidth === undefined) {{
                        const opts = item.series.options ? item.series.options() : {{}};
                        item.__copilotOriginalLineWidth = opts.lineWidth || 2;
                    }}

                    const hidden = !!hiddenByKey[itemKey];
                    const isSelected = selectionOn && selectedKey === itemKey;
                    const isFaded = selectionOn && !isSelected && !hidden;

                    try {{
                        item.series.applyOptions({{ visible: !hidden }});
                    }} catch (err) {{
                        // Fallback for chart versions without visible option.
                        const fallbackColor = hidden
                            ? __copilot_fadeColor(item.solid || '#FFFFFF', 0.08)
                            : (isFaded ? __copilot_fadeColor(item.solid || '#FFFFFF', 0.2) : (item.solid || '#FFFFFF'));
                        item.series.applyOptions({{ color: fallbackColor }});
                    }}

                    if (!hidden) {{
                        item.series.applyOptions({{
                            color: isFaded ? __copilot_fadeColor(item.solid || '#FFFFFF', 0.2) : (item.solid || '#FFFFFF'),
                            lineWidth: isSelected
                                ? Math.max(2, (item.__copilotOriginalLineWidth || 2) + 1)
                                : (item.__copilotOriginalLineWidth || 2),
                        }});
                    }}

                    if (item.__copilotLegendEye) {{
                        item.__copilotLegendEye.textContent = hidden ? '🔓' : '🔒';
                        item.__copilotLegendEye.style.opacity = '1';
                        item.__copilotLegendEye.style.color = hidden ? '#9AA4B2' : '#FFFFFF';
                        item.__copilotLegendEye.style.background = hidden ? '#2A2F36' : 'transparent';
                        item.__copilotLegendEye.title = hidden ? 'Bật line' : 'Tắt line';
                    }}

                    if (item.__copilotLegendRow) {{
                        item.__copilotLegendRow.style.opacity = '1';
                        item.__copilotLegendRow.style.background = isSelected ? '#2A2F36' : 'transparent';
                        item.__copilotLegendRow.style.outline = isSelected ? '1px solid #9AA4B2' : 'none';
                        item.__copilotLegendRow.style.borderRadius = '6px';
                        item.__copilotLegendRow.style.padding = '2px 6px';
                        item.__copilotLegendRow.style.filter = 'none';
                        item.__copilotLegendRow.style.backdropFilter = 'none';
                    }}

                    if (item.__copilotLegendLabel) {{
                        item.__copilotLegendLabel.style.fontWeight = '600';
                        item.__copilotLegendLabel.style.color = hidden ? '#A7B0BD' : '#FFFFFF';
                        item.__copilotLegendLabel.style.textShadow = 'none';
                        item.__copilotLegendLabel.style.webkitTextStroke = '0';
                        item.__copilotLegendLabel.style.filter = 'none';
                        item.__copilotLegendLabel.style.letterSpacing = '0';
                    }}

                    if (item.__copilotLegendDot) {{
                        item.__copilotLegendDot.style.opacity = '1';
                        item.__copilotLegendDot.style.filter = hidden ? 'grayscale(35%)' : 'none';
                    }}
                }});
            }}

            items.forEach(function(item, idx) {{
                if (!item || !item.series) return;

                const row = document.createElement('span');
                row.style.display = 'inline-flex';
                row.style.alignItems = 'center';
                row.style.gap = '6px';
                row.style.whiteSpace = 'nowrap';
                row.style.cursor = 'pointer';
                row.style.userSelect = 'none';
                row.style.flex = '0 0 auto';
                row.style.flexShrink = '0';
                row.style.minWidth = 'max-content';
                row.style.marginRight = '8px';
                row.style.position = 'relative';
                row.style.zIndex = '1';

                const itemKey = getItemKey(item, idx);

                const eye = document.createElement('span');
                eye.textContent = hiddenByKey[itemKey] ? '🔓' : '🔒';
                eye.style.cursor = 'pointer';
                eye.style.opacity = '1';
                eye.style.display = 'inline-flex';
                eye.style.alignItems = 'center';
                eye.style.justifyContent = 'center';
                eye.style.width = '16px';
                eye.style.height = '16px';
                eye.style.borderRadius = '4px';
                eye.title = hiddenByKey[itemKey] ? 'Bật line' : 'Tắt line';

                const dot = document.createElement('span');
                dot.textContent = '◼';
                dot.style.color = item.solid || '#FFFFFF';
                dot.style.cursor = 'pointer';
                dot.style.display = 'inline-flex';
                dot.style.alignItems = 'center';
                dot.style.justifyContent = 'center';
                dot.style.width = '14px';
                dot.style.height = '14px';
                dot.style.borderRadius = '50%';
                dot.style.background = 'rgba(255,255,255,0.08)';
                dot.style.userSelect = 'none';

                const label = document.createElement('span');
                label.textContent = item.name || ('Series ' + (idx + 1));
                label.style.cursor = 'pointer';
                label.style.userSelect = 'none';
                label.style.textShadow = 'none';
                label.style.display = 'inline-block';
                label.style.whiteSpace = 'nowrap';
                label.style.fontFamily = 'Segoe UI, Arial, sans-serif';
                label.style.fontSize = '12px';
                label.style.lineHeight = '1.2';
                label.style.fontWeight = '600';
                label.style.webkitFontSmoothing = 'antialiased';
                label.style.mozOsxFontSmoothing = 'grayscale';

                const selectLegendItem = function(ev) {{
                    ev.preventDefault();
                    ev.stopPropagation();

                    if (hiddenByKey[itemKey]) {{
                        return;
                    }}

                    handler.__copilotLegendSelectedKey =
                        (handler.__copilotLegendSelectedKey === itemKey) ? null : itemKey;
                    applyLegendState();
                }};

                eye.addEventListener('click', function(ev) {{
                    ev.preventDefault();
                    ev.stopPropagation();
                    hiddenByKey[itemKey] = !hiddenByKey[itemKey];
                    handler.__copilotLegendSelectedKey = null;
                    applyLegendState();
                }});

                row.addEventListener('click', selectLegendItem);
                dot.addEventListener('click', selectLegendItem);
                dot.addEventListener('mousedown', selectLegendItem);
                dot.addEventListener('pointerdown', selectLegendItem);
                label.addEventListener('click', selectLegendItem);

                row.appendChild(eye);
                row.appendChild(dot);
                row.appendChild(label);
                legendDiv.appendChild(row);

                item.__copilotLegendRow = row;
                item.__copilotLegendEye = eye;
                item.__copilotLegendDot = dot;
                item.__copilotLegendLabel = label;
            }});

            const validKeys = new Set(items.map(function(item, idx) {{ return getItemKey(item, idx); }}));
            if (handler.__copilotLegendSelectedKey && !validKeys.has(handler.__copilotLegendSelectedKey)) {{
                handler.__copilotLegendSelectedKey = null;
            }}
            applyLegendState();
        }}

        {chart.id}.chart.applyOptions({{
            localization: {{
                priceFormatter: function(price) {{
                    return (price < 0 ? '-' : '')
                        + Math.abs(price).toFixed({precision});
                }}
            }}
        }});

        {chart.id}.legend.ohlcEnabled = false;
        {chart.id}.legend.percentEnabled = false;
        {chart.id}.legend.linesEnabled = false;
        if ({chart.id}.legend && {chart.id}.legend.div) {{
            {chart.id}.legend.div.style.setProperty('display', 'none', 'important');
            {chart.id}.legend.div.style.setProperty('visibility', 'hidden', 'important');
            {chart.id}.legend.div.style.setProperty('opacity', '0', 'important');
            {chart.id}.legend.div.style.setProperty('pointer-events', 'none', 'important');
        }}
        __copilot_render_horizontal_legend({chart.id}, '{chart.id}_copilot_horizontal_legend');
        setTimeout(function() {{ __copilot_render_horizontal_legend({chart.id}, '{chart.id}_copilot_horizontal_legend'); }}, 120);
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

                {subchart.id}.legend.ohlcEnabled = false;
                {subchart.id}.legend.percentEnabled = false;
                {subchart.id}.legend.linesEnabled = false;
                if ({subchart.id}.legend && {subchart.id}.legend.div) {{
                    {subchart.id}.legend.div.style.setProperty('display', 'none', 'important');
                    {subchart.id}.legend.div.style.setProperty('visibility', 'hidden', 'important');
                    {subchart.id}.legend.div.style.setProperty('opacity', '0', 'important');
                    {subchart.id}.legend.div.style.setProperty('pointer-events', 'none', 'important');
                }}
                __copilot_render_horizontal_legend({subchart.id}, '{subchart.id}_copilot_horizontal_legend');
                setTimeout(function() {{ __copilot_render_horizontal_legend({subchart.id}, '{subchart.id}_copilot_horizontal_legend'); }}, 120);
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
    _enable_responsive_resize(
        chart,
        height=getattr(chart, "height", IFRAME_HEIGHT),
        subcharts=subcharts,
    )

    chart.load()



def _normalize_timeframe(timeframe: str) -> str:
    """Chuẩn hóa khung thời gian về daily, weekly hoặc monthly."""
    normalized = timeframe.strip().lower()
    aliases = {
        "d": "daily",
        "day": "daily",
        "daily": "daily",
        "w": "weekly",
        "week": "weekly",
        "weekly": "weekly",
        "m": "monthly",
        "month": "monthly",
        "monthly": "monthly",
    }
    if normalized not in aliases:
        raise ValueError("timeframe phải là 'daily', 'weekly' hoặc 'monthly'.")
    return aliases[normalized]


def _resample_line_dataframe(
    data: pd.DataFrame,
    timeframe: str,
    *,
    time_column: str = "time",
) -> pd.DataFrame:
    """Lấy quan sát cuối kỳ cho dữ liệu line theo daily/weekly/monthly."""
    timeframe = _normalize_timeframe(timeframe)
    if data is None or data.empty or timeframe == "daily":
        return data.copy() if data is not None else pd.DataFrame()
    if time_column not in data.columns:
        raise ValueError(f"DataFrame thiếu cột thời gian '{time_column}'.")

    result = data.copy()
    result[time_column] = pd.to_datetime(result[time_column], errors="coerce")
    result = result.dropna(subset=[time_column]).sort_values(time_column)

    rule = "W-FRI" if timeframe == "weekly" else "ME"
    value_columns = [column for column in result.columns if column != time_column]
    result = (
        result.set_index(time_column)[value_columns]
        .resample(rule)
        .last()
        .dropna(how="all")
        .reset_index()
    )
    result[time_column] = result[time_column].dt.strftime("%Y-%m-%d")
    return result

def draw_comparision_main_sub(
    start_date: str = "2025-03-23",
    symbol_sources: Optional[dict] = None,
    timeframe: str = "daily",
    width: int = IFRAME_WIDTH,
    height: int = IFRAME_HEIGHT,
):
    """Vẽ biểu đồ liên thị trường theo daily, weekly hoặc monthly."""
    from DuckDB.Data import (
        _align_to_base_time,
        _normalize_time,
        get_symbol,
        upd_symbol_percent,
    )

    timeframe = _normalize_timeframe(timeframe)
    base_frequency = {
        "daily": "D",
        "weekly": "W-FRI",
        "monthly": "ME",
    }[timeframe]

    base_time_df = pd.DataFrame({
        "time": pd.date_range(
            start=pd.to_datetime(start_date),
            end=pd.Timestamp.today().normalize(),
            freq=base_frequency,
        ).strftime("%Y-%m-%d")
    })

    visible_range = None
    if not base_time_df.empty:
        visible_range = (
            base_time_df["time"].iloc[0],
            base_time_df["time"].iloc[-1],
        )

    def _get_linebar_symbol(symbol: str, source: str) -> pd.DataFrame:
        raw_df = get_symbol(symbol, start_date, source=source)
        normalized_df = _normalize_time(raw_df)
        period_df = _resample_line_dataframe(normalized_df, timeframe)
        percent_df = upd_symbol_percent(period_df)
        return _align_to_base_time(base_time_df, percent_df)

    if symbol_sources is None:
        symbol_sources = {
            "vnindex": {
                "symbol": "VNINDEX",
                "source": "index",
                "color": "#03FD10",
                "label_name": "VNINDEX",
                "target": "main",
            },
        }

    dataframes = {
        key: _get_linebar_symbol(config["symbol"], config["source"])
        for key, config in symbol_sources.items()
    }

    chart = init_chart(
        width=width,
        height=height,
        inner_width=1,
        inner_height=0.7,
    )
    subchart = init_subchart(chart=chart, sync=chart.id)

    for key, config in symbol_sources.items():
        target = config.get("target", "main")
        color = config.get("color", "#FFFFFF")
        label_name = config.get("label_name") or config.get("symbol") or key

        if target == "main":
            add_line(
                chart=chart,
                color=color,
                label_name=label_name,
                data=dataframes[key],
            )
        else:
            subchart_add_line(
                subchart=subchart,
                color=color,
                label_name=label_name,
                data=dataframes[key],
            )

    load_chart(
        chart=chart,
        subcharts=[subchart],
        visible_range=visible_range,
    )
    return chart


def draw_ticker_above_MA(
    start_date: Optional[str] = None,
    timeframe: str = "daily",
    width: int = IFRAME_WIDTH,
    height: int = IFRAME_HEIGHT,
):
    """
    Vẽ VNINDEX và tỷ lệ ticker trên MA theo daily, weekly hoặc monthly.

    Với weekly/monthly, hàm lấy giá trị cuối tuần hoặc cuối tháng.
    """
    timeframe = _normalize_timeframe(timeframe)

    breadth_df = Data.get_total_ticker_above_MA(start_date=start_date)
    vnindex_df = Data.get_symbol(
        index_name="VNINDEX",
        start_date=start_date,
        source="index",
    )

    breadth_df = _resample_line_dataframe(breadth_df, timeframe)
    vnindex_df = _resample_line_dataframe(vnindex_df, timeframe)

    chart = init_chart(
        width=width,
        height=height,
        inner_width=1,
        inner_height=1,
    )

    add_line(
        chart=chart,
        data=vnindex_df,
        name="Close",
        color="#0080FF",
        label_name="VNINDEX",
        price_scale_id="left",
        width=3,
    )
    add_line(
        chart=chart,
        data=breadth_df,
        name="TickerAboveMA20",
        color="#00FF0D",
        label_name="Ticker > MA20",
    )
    add_line(
        chart=chart,
        data=breadth_df,
        name="TickerAboveMA50",
        color="#A6FCB8",
        label_name="Ticker > MA50",
        hide_data=True,
    )
    add_line(
        chart=chart,
        data=breadth_df,
        name="TickerAboveMA100",
        color="#FC8B8B",
        label_name="Ticker > MA100",
        hide_data=True,
    )
    add_line(
        chart=chart,
        data=breadth_df,
        name="TickerAboveMA200",
        color="#FD0303",
        label_name="Ticker > MA200",
    )

    load_chart(chart=chart)
    return chart