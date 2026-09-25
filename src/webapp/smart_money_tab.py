from __future__ import annotations

import logging

import pandas as pd
from nicegui import ui

from Presentation.theme import THEME, with_alpha
from Ults.DuckLib import DuckDBManager
from webapp.tradingview_links import tradingview_chart_url
from webapp.smart_money_snapshot_query import (
    MODEL_CODE,
    latest_smart_money_snapshot_sql,
)
from webapp.smart_money_state_flow import (
    TRADE_ACTION_ORDER,
    build_smart_money_state_blocks,
)


def load_latest_smart_money_snapshot() -> pd.DataFrame:
    """Load latest SmartMoney V1 snapshot plus Close/MA200 for UI segmentation."""
    with DuckDBManager(read_only=True) as connection:
        return connection.execute(
            latest_smart_money_snapshot_sql(),
            [MODEL_CODE, MODEL_CODE],
        ).df()


def _card_classes(extra: str = "") -> str:
    return (
        "dashboard-card rounded-2xl border shadow-sm min-w-0 "
        f"bg-[{THEME['surface']}] border-[{THEME['border']}] {extra}"
    )


def _action_color(action: str) -> str:
    return {
        "BUY": THEME["positive"],
        "SELL": THEME["negative"],
        "HOLD": THEME["warning"],
    }.get(action, THEME["muted"])


def _action_style(action: str) -> str:
    color = _action_color(action)
    return (
        f"color:{color};background:{with_alpha(color, 0.12)};"
        f"border:1px solid {with_alpha(color, 0.32)};"
    )


def _state_title(state: str) -> str:
    return state.replace("_", " ")


# Run synchronously in the click gesture, before any server round-trip.
# Keep the native _blank link when the browser refuses the popup.
_TRADINGVIEW_POPUP_JS = """(event) => {
    if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    const link = event.currentTarget.closest('a');
    if (!link) return;
    const popup = window.open('', '_blank', 'popup,width=1280,height=820,resizable=yes,scrollbars=yes');
    if (popup) {
        popup.opener = null;
        popup.location.href = link.href;
        event.preventDefault();
    }
}"""


def _tradingview_link(label: str, url: str):
    return ui.link(label, url, new_tab=True).props(
        'rel="noopener noreferrer"'
    ).on("click", js_handler=_TRADINGVIEW_POPUP_JS)


def _show_market_picker(ticker: str) -> None:
    """Never send an unqualified ticker to a possibly foreign listing."""
    with ui.dialog() as dialog, ui.card().classes(_card_classes("p-4")):
        ui.label(f"TradingView · {ticker}").classes("text-lg font-bold")
        ui.label("Chưa xác định được sàn. Chọn sàn Việt Nam của mã này.")
        with ui.row():
            for market in ("HOSE", "HNX", "UPCOM"):
                url = tradingview_chart_url(ticker, market)
                if url:
                    _tradingview_link(market, url)
        ui.button("Đóng", on_click=dialog.close).props("flat")
    dialog.on("hide", dialog.delete)
    dialog.open()


def _render_ticker_links(rows: list[dict], *, muted: bool = False) -> None:
    color = THEME["muted"] if muted else THEME["text"]
    with ui.row().classes("w-full items-baseline gap-x-1 gap-y-0 flex-wrap"):
        for index, row in enumerate(rows):
            ticker = str(row.get("Ticker") or "").strip().upper()
            url = tradingview_chart_url(ticker, row.get("Market"))
            if index:
                ui.label(",").classes(f"text-[{color}]")
            if url:
                element = _tradingview_link(ticker, url)
                element.tooltip(f"Mở TradingView · {ticker}")
            else:
                element = ui.button(
                    ticker, on_click=lambda _event, t=ticker: _show_market_picker(t)
                ).props("flat dense no-caps").classes("p-0 min-h-0")
                element.tooltip("Chọn sàn Việt Nam để mở TradingView")
            element.classes(
                f"text-sm leading-7 text-[{color}] no-underline hover:underline "
                + ("font-bold" if index < 2 else "font-normal")
            )


def _render_ticker_bucket(title: str, count: int, rows: list[dict]) -> None:
    with ui.column().classes(
        "w-full min-w-0 gap-1.5 rounded-xl border p-3 "
        f"bg-[{THEME['surface_alt']}] border-[{THEME['border']}]"
    ):
        with ui.row().classes("w-full items-center justify-between gap-2"):
            ui.label(title).classes(f"text-xs font-bold text-[{THEME['text']}]")
            ui.label(str(count)).classes(
                f"text-xs font-bold text-[{THEME['primary']}]"
            )

        if rows:
            _render_ticker_links(rows)
        else:
            ui.label("Không có ticker").classes(
                f"text-xs italic text-[{THEME['muted']}] py-1"
            )


def _render_state_block(block: dict) -> None:
    state = str(block["market_state"])
    total = int(block["total_tickers"])
    action_counts = dict(block["action_counts"])
    anchor_id = str(block["anchor_id"])

    with ui.element("section").props(f"id={anchor_id}").classes("w-full scroll-mt-4"):
        with ui.card().classes(_card_classes("p-4 w-full")):
            with ui.row().classes("w-full items-start gap-4 no-wrap"):
                ui.label(str(block["stage"])).classes(
                    f"w-8 h-8 rounded-full flex items-center justify-center shrink-0 "
                    f"font-bold text-[{THEME['primary']}] bg-[{THEME['surface_alt']}]"
                )
                with ui.column().classes("gap-1 min-w-0 flex-1"):
                    with ui.row().classes("items-center gap-2 flex-wrap"):
                        ui.label(_state_title(state)).classes(
                            f"font-bold text-base text-[{THEME['text']}]"
                        )
                        rendered_action = False
                        for action in TRADE_ACTION_ORDER:
                            count = int(action_counts.get(action, 0))
                            if count <= 0:
                                continue
                            rendered_action = True
                            ui.label(f"{action} {count}").classes(
                                "text-[10px] font-bold rounded-full px-2.5 py-1"
                            ).style(_action_style(action))
                        if not rendered_action:
                            ui.label("NO TICKER").classes(
                                f"text-[10px] font-semibold rounded-full px-2.5 py-1 "
                                f"text-[{THEME['muted']}] bg-[{THEME['surface_alt']}]"
                            )
                    ui.label(str(block["description"])).classes(
                        f"text-[11px] leading-snug text-[{THEME['muted']}]"
                    )

            ui.separator().classes(f"my-3 bg-[{THEME['border']}]")

            if total <= 0:
                ui.label("Không có ticker ở phiên mới nhất").classes(
                    f"text-xs italic text-[{THEME['muted']}] py-2"
                )
                return

            with ui.element("div").classes(
                "grid grid-cols-1 lg:grid-cols-2 gap-3 w-full"
            ):
                _render_ticker_bucket(
                    ">= MA200",
                    int(block["above_ma200_count"]),
                    block["above_ma200_rows"],
                )
                _render_ticker_bucket(
                    "< MA200",
                    int(block["below_ma200_count"]),
                    block["below_ma200_rows"],
                )

            unavailable_count = int(block.get("ma200_unavailable_count", 0))
            if unavailable_count > 0:
                with ui.row().classes("w-full items-start gap-2 mt-2 flex-wrap"):
                    ui.label(f"MA200 N/A · {unavailable_count}").classes(
                        f"text-[10px] font-semibold text-[{THEME['muted']}]"
                    )
                    _render_ticker_links(block["ma200_unavailable_rows"], muted=True)


def _render_state_flow_links(container, blocks: list[dict]) -> None:
    container.clear()
    with container:
        for index, block in enumerate(blocks):
            if index:
                ui.icon("arrow_forward").classes(
                    f"text-xs text-[{THEME['muted']}]"
                )
            state = str(block["market_state"])
            total = int(block["total_tickers"])
            ui.link(
                f"{_state_title(state)} · {total}",
                f"#{block['anchor_id']}",
            ).classes(
                f"text-[10px] font-semibold px-2 py-1 rounded-lg no-underline "
                f"bg-[{THEME['surface_alt']}] text-[{THEME['primary']}] "
                "hover:underline"
            )


def smart_money_tab_content() -> None:
    """Render SmartMoney MarketState flow with MA200 detail segmentation."""
    latest_date_label: ui.label
    total_tickers_label: ui.label

    with ui.card().classes(_card_classes("p-4 w-full")):
        with ui.row().classes("w-full items-center justify-between gap-3 flex-wrap"):
            with ui.row().classes("items-center gap-3 min-w-0"):
                ui.icon("account_tree").classes(
                    f"text-xl text-[{THEME['primary']}] bg-[{THEME['surface_alt']}] "
                    "rounded-lg p-2"
                )
                with ui.column().classes("gap-0"):
                    ui.label("SmartMoney State Flow").classes(
                        f"text-lg font-bold text-[{THEME['text']}]"
                    )
                    ui.label(
                        "Latest snapshot · MarketState / TradeAction · MA200 position"
                    ).classes(f"text-xs text-[{THEME['muted']}]")
            refresh_button = ui.button("Refresh", icon="refresh").props(
                "outline dense no-caps"
            )

        with ui.row().classes("w-full items-center gap-3 flex-wrap mt-3"):
            latest_date_label = ui.label("As of —").classes(
                f"text-xs font-semibold text-[{THEME['muted']}]"
            )
            total_tickers_label = ui.label("0 tickers").classes(
                f"text-xs font-semibold text-[{THEME['primary']}]"
            )

        state_flow_container = ui.row().classes(
            "w-full items-center gap-1.5 flex-wrap mt-3"
        )

    state_container = ui.column().classes("w-full gap-4")

    def refresh_snapshot() -> None:
        state_container.clear()
        state_flow_container.clear()
        try:
            snapshot = load_latest_smart_money_snapshot()
            blocks = build_smart_money_state_blocks(snapshot)
        except Exception as exc:
            logging.getLogger(__name__).exception("SmartMoney tab refresh failed")
            latest_date_label.set_text("As of —")
            total_tickers_label.set_text("0 tickers")
            with state_container:
                with ui.card().classes(_card_classes("p-5 w-full")):
                    ui.label("Không thể tải SmartMoney snapshot").classes(
                        f"font-semibold text-[{THEME['negative']}]"
                    )
                    ui.label(str(exc)).classes(
                        f"text-xs text-[{THEME['muted']}] mt-1 break-all"
                    )
            ui.notify(f"SmartMoney error: {exc}", type="negative", timeout=8000)
            return

        if snapshot.empty:
            latest_date_label.set_text("As of —")
            total_tickers_label.set_text("0 tickers")
            with state_container:
                with ui.card().classes(_card_classes("p-5 w-full")):
                    ui.label("SmartMoney chưa có dữ liệu").classes(
                        f"text-sm text-[{THEME['muted']}]"
                    )
            return

        latest_date = pd.to_datetime(snapshot["Date"], errors="coerce").max()
        latest_date_text = (
            latest_date.strftime("%Y-%m-%d") if pd.notna(latest_date) else "—"
        )
        total_tickers = int(snapshot["Ticker"].astype(str).nunique())
        latest_date_label.set_text(f"As of {latest_date_text}")
        total_tickers_label.set_text(f"{total_tickers:,} tickers")

        _render_state_flow_links(state_flow_container, blocks)

        with state_container:
            for block in blocks:
                _render_state_block(block)

    refresh_button.on("click", refresh_snapshot)
    refresh_snapshot()
