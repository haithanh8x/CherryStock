"""SmartMoney ticker popup: TradingView widget, existing R/S renderer, public facts."""
from __future__ import annotations

import html
import logging
from time import perf_counter

from nicegui import run, ui
from Presentation.theme import THEME
from Chart.levelLadderChart import build_level_ladder_chart_options, ladder_rows
from webapp.ticker_detail_contract import (
    FIELDS, FIELD_HINTS, VIEW_LABELS, DATE_FIELDS, PARTITIONS,
    field_hint, format_field, normalize_ticker,
)
from webapp.ticker_detail_data import load_ticker_details
from webapp.tradingview_links import tradingview_chart_url
from webapp.tradingview_widget import render_tradingview
from webapp.ticker_detail_trace import TickerTrace

LOGGER = logging.getLogger(__name__)


def tooltip_html(title: str, text: str) -> str:
    """Shared compact R/S-style title, explanation and example layout."""
    marker = "Ví dụ minh họa:" if "Ví dụ minh họa:" in text else "Ví dụ:"
    meaning, separator, example = text.partition(marker)
    content = f'<div style="font-weight:700;margin-bottom:6px">{html.escape(title)}</div>'
    content += f'<div>{html.escape(meaning.strip())}</div>'
    if separator:
        content += '<div style="margin-top:6px"><b>Ví dụ:</b> ' + html.escape(example.strip()) + '</div>'
    return content


def hint(element, text: str):
    """Hover/focus hint; accessible description also remains on the trigger."""
    element.props('tabindex=0')
    element._props["aria-label"] = text
    with element:
        tooltip = ui.tooltip().props("delay=400").style(
            f"background:{THEME['tooltip_background']};color:{THEME['text']};"
            f"border:1px solid {THEME['border']};border-radius:4px;padding:10px;"
            "max-width:min(360px,calc(100vw - 24px));white-space:normal;"
            "font:14px/1.5 sans-serif;box-shadow:1px 2px 10px rgba(0,0,0,0.2)"
        )
        with tooltip:
            ui.html(tooltip_html(str(getattr(element, "text", "") or "Thông tin"), text))
    def toggle(visible: bool):
        tooltip._props["model-value"] = visible
        tooltip.update()
    element.on("focus", lambda: toggle(True))
    element.on("blur", lambda: toggle(False))
    element.on("keydown.escape", lambda: toggle(False))
    return element



def _field(field: str, value: object) -> None:
    with ui.column().classes("gap-1 min-w-0 rounded border p-2").style(
        f"border-color:{THEME['border']}"
    ):
        hint(ui.label(FIELD_HINTS[field][0]).classes("text-xs font-semibold"), field_hint(field))
        ui.label(field).classes("text-xs break-all").style(f"color:{THEME['muted']}")
        hint(ui.label(format_field(field, value)).classes("text-sm break-all"), field_hint(field))


def _section(view: str, rows: list[dict], error: str | None) -> None:
    with ui.expansion(VIEW_LABELS[view], value=True).classes("w-full border rounded-lg"):
        hint(ui.label(view).classes("text-xs"), (
            "Nguồn dữ liệu chỉ đọc. Mỗi cấu hình hiển thị bản ghi mới nhất và ngày riêng. "
            "Ví dụ: ngày SmartMoney 25/09 có thể khác ngày xác nhận profile 23/09."
        ))
        if error:
            ui.label(error).classes("text-sm").style(f"color:{THEME['negative']}")
            return
        if not rows:
            hint(ui.label("Chưa có dữ liệu cho ticker này."), "Không có bản ghi; không thay bằng 0. Ví dụ: mã mới chưa đủ sóng.")
        for row in rows:
            identity = " · ".join(str(row.get(key)) for key in PARTITIONS[view])
            hint(ui.label(f"{identity} · {format_field(DATE_FIELDS[view], row.get(DATE_FIELDS[view]))}").classes("font-bold"),
                 "Cấu hình và ngày của riêng bản ghi này. Ví dụ: hai cấu hình ZigZag có thể cho hai profile khác nhau.")
            with ui.element("div").classes("grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-2 w-full"):
                for field in FIELDS[view]:
                    _field(field, row.get(field))


LADDER_HINTS = {
    "rank": "S1/R1 là mức hỗ trợ/kháng cự gần giá nhất, không phải mạnh nhất. Ví dụ: S1 gần hơn S2.",
    "price": "Giá đại diện vùng, nghìn đồng/cp. Ví dụ: 100 = 100,000 đồng/cp.",
    "distance_pct": "Khoảng cách tới giá hiện tại, đã ở đơn vị %. Ví dụ: 2.5 = +2.5%; không nhân 100 lần nữa.",
    "strength": "Độ mạnh độc lập của vùng, thang 0–100. Ví dụ: Strength 80 không phải xác suất bật giá 80%.",
    "zone": "Biên dưới–trên vùng gom mức giá, nghìn đồng/cp. Ví dụ: 99–101.",
    "timeframes": "Các khung tạo vùng. Ví dụ: D/W = ngày/tuần.",
    "families": "Nhóm nguồn hợp lưu; khác số lượng nguồn riêng lẻ. Ví dụ: MA và pivot là hai nhóm.",
    "sources": "Nguồn cụ thể đóng góp vào vùng. Ví dụ: MA200_D.",
}


def _ladder_options(ladder):
    options = build_level_ladder_chart_options(ladder)
    for series in options.get("series", []):
        if series.get("name") not in {"Support", "Resistance", "Current Price"}:
            continue
        for point in series.get("data", []):
            if not isinstance(point, dict):
                continue
            explanation = (
                "Giá tham chiếu, nghìn đồng/cp. Ví dụ: 100 = 100,000 đồng."
                if series["name"] == "Current Price" else
                "S = hỗ trợ; R = kháng cự. S1/R1 gần giá nhất, không nhất thiết mạnh nhất. "
                "Giá: nghìn đồng/cp; Dist: %. Ví dụ: +2.5% là cao hơn giá hiện tại 2.5%. "
                "Strength 80 là điểm độ mạnh, không phải xác suất 80%."
            )
            point["tooltip"] = {"formatter": tooltip_html(str(point.get("name", "Giá hiện tại")), explanation)}
    options.setdefault("tooltip", {}).update({"padding": 10, "borderWidth": 1, "extraCssText": "max-width:360px;white-space:normal;line-height:1.5;border-radius:4px"})
    return options


class TickerDetailDialog:
    """One reusable dialog per client/tab; stale async completions cannot overwrite it."""
    def __init__(self):
        self.generation = 0
        with ui.dialog() as self.dialog:
            with ui.card().classes("w-[96vw] max-w-none h-[92vh] p-4 overflow-auto").style(
                f"background:{THEME['surface']};color:{THEME['text']}"
            ):
                with ui.row().classes("w-full justify-between items-center"):
                    self.title = ui.label("Chi tiết ticker").classes("text-xl font-bold")
                    hint(ui.button("Đóng", icon="close", on_click=self.dialog.close).props("flat"),
                         "Đóng popup và quay về SmartMoney. Ví dụ: nhấn Escape cũng đóng.")
                self.body = ui.column().classes("w-full gap-4")
        self.dialog.on("hide", self._closed)

    def _closed(self):
        self.generation += 1
        self.body.clear()  # unload TradingView iframe on close

    async def show(self, ticker: str):
        ticker = normalize_ticker(ticker)
        trace = TickerTrace(ticker)
        self.generation += 1
        generation = self.generation
        self.title.set_text(f"{ticker} · TradingView & phân tích")
        self.body.clear()
        with self.body:
            ui.spinner()
            ui.label("Đang tải dữ liệu theo ticker…")
        self.dialog.open()
        try:
            with trace.span("ui.data_wait"):
                data = await run.io_bound(load_ticker_details, ticker, trace)
        except Exception:
            LOGGER.exception("Ticker popup load failed | ticker=%s", ticker)
            if generation == self.generation:
                self.body.clear()
                with self.body:
                    ui.label("Không tải được dữ liệu. Đóng và mở lại; xem log nếu lỗi tiếp diễn.")
            return
        if generation != self.generation or self.dialog.is_deleted:
            trace.record("ui.discarded", 0, "cancelled")
            return
        render_started = perf_counter()
        self.body.clear()
        with self.body:
            hint(ui.label("Dữ liệu từng nguồn có thể khác ngày. Các ví dụ trong tooltip chỉ để minh họa.").classes("text-xs"),
                 "Đọc ngày ở từng khối. TradingView là nguồn ngoài; R/S và ba view dùng dữ liệu CherryStock.")
            with ui.element("div").classes("grid grid-cols-1 xl:grid-cols-3 gap-4 w-full"):
                with ui.column().classes("xl:col-span-2 w-full min-w-0"):
                    hint(ui.label("TradingView").classes("text-lg font-bold"),
                         "Biểu đồ bên ngoài cho cùng ticker và sàn. Ví dụ: HOSE:MWG. Nguồn/đơn vị có thể khác CherryStock.")
                    chart_box = ui.column().classes("w-full")
                    def render_chart(market: str):
                        chart_box.clear()
                        with chart_box:
                            url = tradingview_chart_url(ticker, market)
                            if not url:
                                ui.label("Chọn sàn Việt Nam để xem biểu đồ.")
                                return
                            render_tradingview(ticker, market, trace, hint)
                    market = data["market"]
                    if tradingview_chart_url(ticker, market):
                        render_chart(str(market))
                    else:
                        hint(ui.label(data["errors"].get("market", "Chưa có sàn hợp lệ.")),
                             "Không tự đoán sàn. Ví dụ: ACV Việt Nam phải chọn UPCOM, không phải NYSE.")
                        picker = hint(ui.select(["HOSE", "HNX", "UPCOM"], label="Sàn Việt Nam"),
                                      "Chọn đúng sàn niêm yết. Ví dụ: SHS → HNX. Chỉ ảnh hưởng biểu đồ, không ghi dữ liệu.")
                        picker.on_value_change(lambda event: render_chart(event.value))
                with ui.column().classes("w-full min-w-0"):
                    hint(ui.label("R/S Price Ladder").classes("text-lg font-bold"),
                         "Thang hỗ trợ/kháng cự từ engine hiện có. Ví dụ: S1 gần giá nhất; độ cao phản ánh mức giá.")
                    ladder = data["ladder"]
                    if ladder is None:
                        ui.label(data["errors"].get("ladder", "Chưa có R/S."))
                    else:
                        hint(ui.label(f"{ladder.ticker} · {ladder.as_of_date} · {ladder.model_version}"),
                             "Ngày nguồn R/S của ticker, không mặc định trùng TradingView. Ví dụ: R/S ngày phiên gần nhất.")
                        hint(ui.label(f"Giá: {ladder.current_price:,.2f} nghìn đồng"),
                             "Giá tham chiếu R/S, nghìn đồng/cp. Ví dụ: 100 = 100,000 đồng.")
                        rr = "—" if ladder.risk_reward_ratio is None else f"{ladder.risk_reward_ratio:.2f}"
                        hint(ui.label(f"Reward / Risk: {rr}"),
                             "Khoảng tăng tới R1 / khoảng giảm tới S1. Ví dụ: 6% / 3% = 2; không phải tỷ lệ thắng.")
                        ui.echart(_ladder_options(ladder)).classes("w-full h-[540px]")
            if data["ladder"] is not None:
                with ui.expansion("Chi tiết các mức R/S", value=False).classes("w-full"):
                    rows = ladder_rows(data["ladder"])
                    if not rows:
                        ui.label("Không có mức hỗ trợ/kháng cự hợp lệ.")
                    for row in rows:
                        with ui.row().classes("w-full gap-3 flex-wrap border-b py-2"):
                            for field, explanation in LADDER_HINTS.items():
                                hint(ui.label(f"{field}: {row[field]}").classes("text-sm"), explanation)
            for view in FIELDS:
                _section(view, data["sections"].get(view, []), data["errors"].get(view))

        trace.record("ui.render_build", (perf_counter() - render_started) * 1000)
        trace.record("ui.server_total", (perf_counter() - trace.started) * 1000)
