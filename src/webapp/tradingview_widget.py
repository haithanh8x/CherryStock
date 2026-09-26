"""Official TradingView loader mounted into a live DOM node after dialog rendering."""
from __future__ import annotations

import json
import math
from nicegui import ui
from Presentation.theme import THEME, is_dark_theme
from webapp.ticker_detail_contract import normalize_ticker
from webapp.tradingview_links import tradingview_chart_url, VIETNAM_EXCHANGES


def widget_config(ticker: str, market: str) -> dict:
    ticker = normalize_ticker(ticker)
    if tradingview_chart_url(ticker, market) is None:
        raise ValueError("Sàn TradingView không được hỗ trợ.")
    return {
        "autosize": True, "symbol": f"{VIETNAM_EXCHANGES[market.strip().upper()]}:{ticker}",
        "interval": "D", "timezone": "Asia/Ho_Chi_Minh",
        "theme": "dark" if is_dark_theme() else "light", "style": "1",
        "locale": "vi_VN", "allow_symbol_change": False,
        "calendar": False, "support_host": "https://www.tradingview.com",
    }


# No srcdoc/opaque-origin sandbox around the vendor's own cross-origin iframe.
# Insert a real script node: scripts inside innerHTML do not execute reliably.
MOUNT_JS = r"""
(hostId, config) => {
    const host = document.getElementById(hostId);
    if (!host || !host.isConnected) return false;
    if (host._tvCleanup) host._tvCleanup();
    host.replaceChildren();
    const start = performance.now();
    const report = (stage, status = "ok") => {
        if (host.isConnected) host.dispatchEvent(new CustomEvent("tv-status", {
            detail: {stage, status, duration_ms: performance.now() - start}
        }));
    };
    const container = document.createElement("div");
    container.className = "tradingview-widget-container";
    container.style.cssText = "height:100%;width:100%";
    const target = document.createElement("div");
    target.className = "tradingview-widget-container__widget";
    target.style.cssText = "height:calc(100% - 32px);width:100%";
    const copyright = document.createElement("div");
    copyright.className = "tradingview-widget-copyright";
    const link = document.createElement("a");
    link.href = "https://www.tradingview.com/chart/?symbol=" + encodeURIComponent(config.symbol);
    link.target = "_blank"; link.rel = "noopener noreferrer";
    link.textContent = config.symbol + " chart by TradingView";
    copyright.append(link);
    container.append(target, copyright);
    host.append(container);
    let finished = false;
    let frameTimer;
    const finish = (stage, status = "ok") => {
        if (finished) return;
        finished = true;
        clearTimeout(frameTimer);
        observer.disconnect();
        report(stage, status);
    };
    const observer = new MutationObserver(() => {
        const frame = container.querySelector("iframe");
        if (!frame || frame.dataset.csObserved) return;
        frame.dataset.csObserved = "true";
        report("iframe_created");
        frame.addEventListener("load", () => finish("iframe_load"), {once: true});
    });
    observer.observe(container, {childList: true, subtree: true});
    const removal = new MutationObserver(() => {
        if (!host.isConnected) host._tvCleanup();
    });
    removal.observe(document.body, {childList: true, subtree: true});
    host._tvCleanup = () => {
        clearTimeout(frameTimer); observer.disconnect(); removal.disconnect();
        finished = true;
    };
    frameTimer = setTimeout(() => finish("timeout", "unknown"), 20000);
    const script = document.createElement("script");
    script.src = "https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";
    script.type = "text/javascript"; script.async = true;
    script.textContent = JSON.stringify(config);
    script.addEventListener("error", () => finish("script_error", "error"), {once: true});
    script.addEventListener("load", () => report("script_load"), {once: true});
    report("mount");
    container.append(script);
    return true;
}
"""


def render_tradingview(ticker: str, market: str, trace, hint) -> None:
    config = widget_config(ticker, market)
    hint(ui.link("Mở trên TradingView ↗", tradingview_chart_url(ticker, market), new_tab=True).props(
        'rel="noopener noreferrer"'
    ), f"Mở biểu đồ đầy đủ trên website TradingView. Ví dụ: {config['symbol']}.")
    status_label = ui.label("Đang tải TradingView…").classes("text-xs").style(f"color:{THEME['muted']}")
    host = ui.element("div").classes("w-full").style("height:620px;min-height:620px")
    host._props["data-tv-symbol"] = config["symbol"]

    def status(event):
        payload = event.args
        if not isinstance(payload, dict) or host.is_deleted:
            return
        stage = payload.get("stage")
        if stage not in {"mount", "script_load", "iframe_created", "iframe_load", "timeout", "script_error"}:
            return
        try:
            duration = float(payload.get("duration_ms", 0))
        except (TypeError, ValueError):
            return
        if not math.isfinite(duration) or duration < 0:
            return
        event_status = {"timeout": "unknown", "script_error": "error"}.get(stage, "ok")
        trace.record("tv." + stage, duration, event_status, clock="browser_since_mount")
        if stage == "iframe_load":
            status_label.set_text("Đã tải khung TradingView. Nếu chưa có nến, kiểm tra thông báo trong biểu đồ.")
        elif stage in {"timeout", "script_error"}:
            status_label.set_text("Chưa tải được TradingView. Kiểm tra mạng/extension hoặc mở liên kết phía trên.")

    host.on("tv-status", status, js_handler="event => emit(event.detail)")

    async def mount():
        if host.is_deleted:
            return
        try:
            mounted = await ui.run_javascript(
                f"({MOUNT_JS})({json.dumps('c' + str(host.id))}, {json.dumps(config)})",
                timeout=5.0,
            )
            if not mounted and not host.is_deleted:
                status_label.set_text("Không khởi tạo được khung TradingView. Đóng rồi mở lại popup.")
                trace.record("tv.mount_missing", 0, "error")
        except Exception:
            trace.record("tv.mount_error", 0, "error")
            if not host.is_deleted:
                status_label.set_text("Không khởi tạo được TradingView. Dùng liên kết phía trên.")

    ui.timer(0.1, mount, once=True)
