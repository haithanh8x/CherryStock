from __future__ import annotations

import logging
from typing import Any

import pandas as pd
from nicegui import ui

from Presentation.theme import THEME, with_alpha
from Ults.DuckLib import DuckDBManager
from webapp.smart_money_state_flow import (
    SMART_MONEY_STATE_FLOW,
    TRADE_ACTION_ORDER,
    build_smart_money_state_blocks,
)


SMART_MONEY_VIEW = '"CherryMon"."main"."vw_Ticker_SmartMoney"'
SMART_MONEY_MODEL_CODE = "SMART_MONEY_V1"


def load_latest_smart_money_snapshot() -> pd.DataFrame:
    """Load the latest available SmartMoney V1 cross-sectional snapshot."""
    sql = f"""
        WITH latest AS (
            SELECT MAX(Date) AS Date
            FROM {SMART_MONEY_VIEW}
            WHERE ModelCode = ?
        )
        SELECT
            v.Ticker,
            v.Date,
            v.ModelCode,
            v.ModelVersion,
            v.SmartMoneyScore,
            v.ConfidenceScore,
            v.MarketState,
            v.DataQualityStatus,
            v.TradeAction,
            v.TradeActionConfidenceScore
        FROM {SMART_MONEY_VIEW} AS v
        INNER JOIN latest AS d
            ON d.Date = v.Date
        WHERE v.ModelCode = ?
        ORDER BY v.MarketState, v.TradeActionConfidenceScore DESC, v.Ticker
    """
    with DuckDBManager(read_only=True) as connection:
        return connection.execute(
            sql,
            [SMART_MONEY_MODEL_CODE, SMART_MONEY_MODEL_CODE],
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


def _render_ticker_row(row: dict[str, Any]) -> None:
    action = str(row.get("TradeAction") or "HOLD").upper()
    action_confidence = float(row.get("TradeActionConfidenceScore") or 0.0)
    smart_money_score = row.get("SmartMoneyScore")
    upstream_confidence = row.get("ConfidenceScore")

    with ui.row().classes(
        "w-full items-center gap-2 no-wrap rounded-lg px-2 py-2"
    ).style(
        f"background:{with_alpha(THEME['surface_alt'], 0.55)};"
        f"border:1px solid {with_alpha(THEME['border'], 0.75)};"
    ):
        ui.label(str(row.get("Ticker") or "—")).classes(
            f"w-16 shrink-0 font-bold text-[{THEME['text']}]"
        )
        ui.label(action).classes(
            "w-14 shrink-0 text-center text-[10px] font-bold rounded-full px-2 py-1"
        ).style(_action_style(action))
        with ui.column().classes("gap-0 flex-1 min-w-0"):
            ui.label(f"Action confidence {action_confidence:.2f}").classes(
                f"text-xs font-semibold text-[{THEME['text']}]"
            )
            detail_parts: list[str] = []
            if smart_money_score is not None:
                detail_parts.append(f"SM {float(smart_money_score):.2f}")
            if upstream_confidence is not None:
                detail_parts.append(f"Upstream {float(upstream_confidence):.2f}")
            if detail_parts:
                ui.label(" · ".join(detail_parts)).classes(
                    f"text-[10px] text-[{THEME['muted']}]"
                )


def _render_action_group(action: str, rows: list[dict[str, Any]]) -> None:
    """Render one BUY/HOLD/SELL subgroup preserving confidence-desc row order."""
    color = _action_color(action)
    with ui.column().classes("w-full gap-1.5"):
        with ui.row().classes("w-full items-center justify-between gap-2"):
            with ui.row().classes("items-center gap-2"):
                ui.element("span").classes("w-2 h-2 rounded-full").style(
                    f"background:{color};"
                )
                ui.label(action).classes(
                    f"text-xs font-bold text-[{color}]"
                )
            ui.label(str(len(rows))).classes(
                "text-[10px] font-bold rounded-full px-2 py-0.5"
            ).style(_action_style(action))

        if not rows:
            ui.label("Không có ticker").classes(
                f"text-[10px] italic text-[{THEME['muted']}] pl-4 py-1"
            )
            return

        for row in rows:
            _render_ticker_row(row)


def _render_state_block(block: dict[str, Any]) -> None:
    state = str(block["market_state"])
    total = int(block["total_tickers"])
    action_counts = block["action_counts"]
    rows: list[dict[str, Any]] = list(block["rows"])
    action_rows: dict[str, list[dict[str, Any]]] = block["action_rows"]

    with ui.card().classes(_card_classes("p-4 h-full")):
        with ui.row().classes("w-full items-start justify-between gap-3 no-wrap"):
            with ui.row().classes("items-start gap-3 min-w-0 no-wrap"):
                ui.label(str(block["stage"])).classes(
                    f"w-8 h-8 rounded-full flex items-center justify-center shrink-0 "
                    f"font-bold text-[{THEME['primary']}] bg-[{THEME['surface_alt']}]"
                )
                with ui.column().classes("gap-0 min-w-0"):
                    ui.label(_state_title(state)).classes(
                        f"font-bold text-base text-[{THEME['text']}]"
                    )
                    ui.label(str(block["description"])).classes(
                        f"text-[11px] leading-snug text-[{THEME['muted']}]"
                    )
            with ui.column().classes("gap-0 items-end shrink-0"):
                ui.label(str(total)).classes(
                    f"text-2xl font-bold text-[{THEME['primary']}]"
                )
                ui.label("tickers").classes(
                    f"text-[10px] uppercase tracking-wide text-[{THEME['muted']}]"
                )

        with ui.row().classes("w-full items-center gap-2 flex-wrap mt-3"):
            for action in TRADE_ACTION_ORDER:
                count = int(action_counts.get(action, 0))
                ui.label(f"{action} {count}").classes(
                    "text-[10px] font-bold rounded-full px-2.5 py-1"
                ).style(_action_style(action))

        ui.separator().classes(f"my-3 bg-[{THEME['border']}]")

        if not rows:
            ui.label("Không có ticker ở phiên mới nhất").classes(
                f"text-xs italic text-[{THEME['muted']}] py-3"
            )
            return

        with ui.column().classes(
            "w-full gap-3 max-h-[430px] overflow-y-auto pr-1"
        ):
            for action in TRADE_ACTION_ORDER:
                _render_action_group(action, list(action_rows.get(action, [])))


def smart_money_tab_content() -> None:
    """Render SmartMoney MarketState blocks from the latest public-view snapshot."""
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
                        "Latest snapshot · MarketState → TradeAction → Action Confidence"
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

        with ui.row().classes("w-full items-center gap-1.5 flex-wrap mt-3"):
            for index, (state, _) in enumerate(SMART_MONEY_STATE_FLOW):
                if index:
                    ui.icon("arrow_forward").classes(
                        f"text-xs text-[{THEME['muted']}]"
                    )
                ui.label(_state_title(state)).classes(
                    f"text-[10px] font-semibold px-2 py-1 rounded-lg "
                    f"bg-[{THEME['surface_alt']}] text-[{THEME['muted']}]"
                )

    state_container = ui.element("div").classes(
        "grid grid-cols-1 lg:grid-cols-2 2xl:grid-cols-3 gap-4 w-full"
    )

    def refresh_snapshot() -> None:
        state_container.clear()
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

        with state_container:
            for block in blocks:
                _render_state_block(block)

    refresh_button.on("click", refresh_snapshot)
    refresh_snapshot()
