"""
Unofficial TradingView Forecast client.

Derived from the WebSocket flow observed in Chrome DevTools/HAR:
    wss://data.tradingview.com/socket.io/websocket
    set_data_quality
    set_auth_token
    set_locale
    quote_create_session
    quote_add_symbols
    quote_fast_symbols
    qsd responses

Important:
- This is NOT an official TradingView public API.
- TradingView may change the protocol/fields at any time.
- Use only in ways permitted by TradingView's terms and your data-license rights.

Install:
    pip install websocket-client

Example:
    python tradingview_forecast.py HOSE:VJC
    python tradingview_forecast.py HOSE:VJC HOSE:MWG HOSE:FPT
    python tradingview_forecast.py HOSE:VJC --forecast-fields
    python tradingview_forecast.py HOSE:VJC --forecast-fields --all-qsd
"""

from __future__ import annotations

import argparse
import json
import random
import re
import string
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Iterable
from urllib.parse import quote

import websocket


TV_WS_BASE = "wss://data.tradingview.com/socket.io/websocket"

# Forecast / analyst-consensus fields observed in the VJC qsd payload captured
# from Chrome DevTools.  This catalog intentionally includes scalar FY forecasts,
# historical forecast arrays, and estimate-history objects.
#
# IMPORTANT:
# - Not every ticker has every field.
# - TradingView can add/remove/rename fields without notice.
# - The client below can also preserve *all* qsd fields dynamically, so this list
#   is not a hard limit.

PRICE_TARGET_FIELDS = {
    "forecast_availability",
    "price_target_average",
    "price_target_average_prev",
    "price_target_high",
    "price_target_low",
    "price_target_median",
    "price_target_estimates_num",
    "price_target_date",
    "price_target_up_num",
    "price_target_down_num",
}

RECOMMENDATION_FIELDS = {
    "recommendation_buy",
    "recommendation_hold",
    "recommendation_sell",
    "recommendation_over",
    "recommendation_under",
    "recommendation_total",
    "recommendation_mark",
    "recommendation_mark_prev",
    "recommendation_date",
}

# Current / next FY scalar forecast values.
FORECAST_SCALAR_FIELDS = {
    "book_value_per_share_estimate_fy",
    "capital_expenditures_estimate_fy",
    "cash_f_financing_activities_estimate_fy",
    "cash_f_investing_activities_estimate_fy",
    "cash_f_operating_activities_estimate_fy",
    "cash_n_short_term_invest_estimate_fy",
    "cost_of_goods_estimate_fy",
    "dps_estimate_fy",
    "earnings_per_share_forecast_fy",
    "earnings_per_share_forecast_next_fy",
    "ebit_estimate_fy",
    "ebitda_estimate_fy",
    "eps_estimate_fy",
    "free_cash_flow_estimate_fy",
    "gross_profit_estimate_fy",
    "net_income_estimate_fy",
    "revenue_estimate_fy",
    "revenue_forecast_fy",
    "revenue_forecast_next_fy",
    "sell_gen_admin_exp_total_estimate_fy",
    "total_assets_estimate_fy",
}

# Fiscal period labels that align with *_h arrays.
FORECAST_PERIOD_FIELDS = {
    "estimates_fiscal_period_fh_h",
    "estimates_fiscal_period_fq_h",
    "estimates_fiscal_period_fy_h",
}

# Historical forecast arrays / detailed estimate histories observed in the HAR.
FORECAST_HISTORY_FIELDS = {
    "book_value_per_share_estimates_fy_h",
    "capital_expenditures_estimates_fy_h",
    "cash_f_financing_activities_estimates_fy_h",
    "cash_f_investing_activities_estimates_fy_h",
    "cash_f_operating_activities_estimates_fy_h",
    "cash_n_short_term_invest_estimates_fy_h",
    "cost_of_goods_estimates_fy_h",
    "dps_estimates_fy_h",

    "earnings_per_share_forecast_fh_h",
    "earnings_per_share_forecast_fq_h",
    "earnings_per_share_forecast_fy_h",

    "ebit_estimates_fq_h",
    "ebit_estimates_fy_h",
    "ebitda_estimates_fy_h",
    "eps_estimates_fy_h",

    "free_cash_flow_estimates_fy_h",

    "gross_profit_estimates_fh_h",
    "gross_profit_estimates_fq_h",
    "gross_profit_estimates_fy_h",

    "net_income_estimates_fh_h",
    "net_income_estimates_fq_h",
    "net_income_estimates_fy_h",

    "revenue_estimates_fh_h",
    "revenue_estimates_fq_h",
    "revenue_estimates_fy_h",
    "revenue_forecast_fh_h",
    "revenue_forecast_fq_h",
    "revenue_forecast_fy_h",

    "sell_gen_admin_exp_total_estimates_fq_h",
    "sell_gen_admin_exp_total_estimates_fy_h",

    "total_assets_estimates_fy_h",
}

FORECAST_FIELDS = (
    PRICE_TARGET_FIELDS
    | RECOMMENDATION_FIELDS
    | FORECAST_SCALAR_FIELDS
    | FORECAST_PERIOD_FIELDS
    | FORECAST_HISTORY_FIELDS
)


def looks_like_forecast_field(name: str) -> bool:
    """Heuristic fallback for future TradingView fields not yet in the catalog."""
    n = name.lower()
    tokens = (
        "forecast",
        "estimate",
        "estimates",
        "recommendation",
        "price_target",
        "target_price",
        "consensus",
    )
    return any(token in n for token in tokens)

# Parse one or more TradingView "~m~<length>~m~<payload>" envelopes from a WS frame.
# Regex is intentionally used here because the incoming length is byte-oriented while
# Python strings are Unicode code points; slicing by the numeric length can break on
# Vietnamese text.
_ENVELOPE_RE = re.compile(r"~m~\d+~m~(.*?)(?=~m~\d+~m~|$)", re.DOTALL)


@dataclass(slots=True)
class Forecast:
    symbol: str

    forecast_availability: int | None = None

    target_average: float | None = None
    target_average_prev: float | None = None
    target_high: float | None = None
    target_low: float | None = None
    target_median: float | None = None
    target_estimates_num: int | None = None
    target_date: str | None = None
    target_up_num: int | None = None
    target_down_num: int | None = None

    recommendation_buy: int | None = None
    recommendation_hold: int | None = None
    recommendation_sell: int | None = None
    recommendation_over: int | None = None
    recommendation_under: int | None = None
    recommendation_total: int | None = None
    recommendation_mark: float | None = None
    recommendation_mark_prev: float | None = None
    recommendation_date: str | None = None

    close: float | None = None
    currency: str | None = None
    description: str | None = None

    fetched_at_utc: str | None = None

    @property
    def upside_to_average_pct(self) -> float | None:
        if self.close in (None, 0) or self.target_average is None:
            return None
        return (self.target_average / self.close - 1.0) * 100.0

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["upside_to_average_pct"] = self.upside_to_average_pct
        return d


class TradingViewForecastClient:
    """
    Small adapter around TradingView's internal quote WebSocket.

    Default auth token matches the anonymous flow captured from the browser:
        unauthorized_user_token

    For a logged-in workflow, do NOT hard-code cookies/tokens in source code.
    """

    def __init__(
        self,
        *,
        auth_token: str = "unauthorized_user_token",
        data_quality: str = "low",
        locale: str = "en",
        country: str = "US",
        timeout: float = 12.0,
        page_context: str = "symbols/HOSE-VJC/forecast-price-target/",
        user_agent: str | None = None,
    ) -> None:
        self.auth_token = auth_token
        self.data_quality = data_quality
        self.locale = locale
        self.country = country
        self.timeout = timeout
        self.page_context = page_context
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/151.0.0.0 Safari/537.36"
        )

        self._ws: websocket.WebSocket | None = None
        self._quote_session: str | None = None

    @staticmethod
    def _session(prefix: str, n: int = 12) -> str:
        alphabet = string.ascii_letters + string.digits
        return prefix + "".join(random.choice(alphabet) for _ in range(n))

    @staticmethod
    def _frame(payload: str) -> str:
        # Outgoing JSON below is ASCII (ensure_ascii=True), so char length == byte length.
        return f"~m~{len(payload)}~m~{payload}"

    @classmethod
    def _command(cls, method: str, params: list[Any]) -> str:
        payload = json.dumps(
            {"m": method, "p": params},
            separators=(",", ":"),
            ensure_ascii=True,
        )
        return cls._frame(payload)

    @staticmethod
    def _iter_payloads(frame: str) -> Iterable[str]:
        for match in _ENVELOPE_RE.finditer(frame):
            yield match.group(1)

    def _send_command(self, method: str, params: list[Any]) -> None:
        assert self._ws is not None
        self._ws.send(self._command(method, params))

    def connect(self) -> None:
        if self._ws is not None:
            return

        # Reproduce the browser page-context query parameter seen in the HAR.
        from_value = quote(self.page_context, safe="")
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        url = f"{TV_WS_BASE}?from={from_value}&date={quote(now)}&auth=sessionid"

        self._ws = websocket.create_connection(
            url,
            timeout=self.timeout,
            origin="https://www.tradingview.com",
            header=[f"User-Agent: {self.user_agent}"],
        )

        # Server sends an initial session frame first. We don't need its values,
        # but receiving it keeps the flow aligned with the browser.
        try:
            self._ws.recv()
        except websocket.WebSocketTimeoutException:
            pass

        self._quote_session = self._session("qs_")

        self._send_command("set_data_quality", [self.data_quality])
        self._send_command("set_auth_token", [self.auth_token])
        self._send_command("set_locale", [self.locale, self.country])
        self._send_command("quote_create_session", [self._quote_session])

    def close(self) -> None:
        if self._ws is not None:
            try:
                self._ws.close()
            finally:
                self._ws = None
                self._quote_session = None

    def __enter__(self) -> "TradingViewForecastClient":
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        symbol = symbol.strip().upper()
        if ":" not in symbol:
            raise ValueError(
                f"Symbol must include exchange, e.g. 'HOSE:VJC'; got {symbol!r}"
            )
        return symbol

    @staticmethod
    def _date_from_tv(value: Any) -> str | None:
        """
        TradingView dates may arrive as:
        - YYYY-MM-DD string
        - unix seconds
        - null
        """
        if value is None:
            return None
        if isinstance(value, str):
            return value
        if isinstance(value, (int, float)):
            try:
                return datetime.fromtimestamp(value, tz=timezone.utc).date().isoformat()
            except (ValueError, OSError, OverflowError):
                return str(value)
        return str(value)

    @staticmethod
    def _forecast_from_quote(symbol: str, q: dict[str, Any]) -> Forecast:
        return Forecast(
            symbol=symbol,
            forecast_availability=q.get("forecast_availability"),

            target_average=q.get("price_target_average"),
            target_average_prev=q.get("price_target_average_prev"),
            target_high=q.get("price_target_high"),
            target_low=q.get("price_target_low"),
            target_median=q.get("price_target_median"),
            target_estimates_num=q.get("price_target_estimates_num"),
            target_date=TradingViewForecastClient._date_from_tv(
                q.get("price_target_date")
            ),
            target_up_num=q.get("price_target_up_num"),
            target_down_num=q.get("price_target_down_num"),

            recommendation_buy=q.get("recommendation_buy"),
            recommendation_hold=q.get("recommendation_hold"),
            recommendation_sell=q.get("recommendation_sell"),
            recommendation_over=q.get("recommendation_over"),
            recommendation_under=q.get("recommendation_under"),
            recommendation_total=q.get("recommendation_total"),
            recommendation_mark=q.get("recommendation_mark"),
            recommendation_mark_prev=q.get("recommendation_mark_prev"),
            recommendation_date=TradingViewForecastClient._date_from_tv(
                q.get("recommendation_date")
            ),

            close=q.get("close"),
            currency=q.get("currency_code") or q.get("currency"),
            description=(
                q.get("short_description")
                or q.get("description")
                or q.get("local_description")
            ),

            fetched_at_utc=datetime.now(timezone.utc).isoformat(),
        )

    def get_forecasts(
        self,
        symbols: Iterable[str],
        *,
        include_forecast_fields: bool = True,
        include_all_qsd_fields: bool = False,
    ) -> tuple[
        dict[str, Forecast],
        dict[str, dict[str, Any]],
        dict[str, dict[str, Any]],
    ]:
        """
        Request multiple symbols on one quote session.

        Returns:
            forecasts:
                Typed core price-target/recommendation object per symbol.

            forecast_fields:
                Every known/heuristically detected forecast/estimate/recommendation
                field observed in qsd. Includes nested history arrays.

            all_qsd_fields:
                Complete merged qsd payload per symbol when include_all_qsd_fields=True.
                This is the safest way to retain new TradingView fields automatically.
        """
        self.connect()
        assert self._ws is not None
        assert self._quote_session is not None

        symbols = [self._normalize_symbol(s) for s in symbols]
        if not symbols:
            return {}, {}, {}

        # One quote session can subscribe to multiple tickers.
        for symbol in symbols:
            self._send_command(
                "quote_add_symbols",
                [self._quote_session, symbol],
            )

        # HAR shows quote_fast_symbols after subscription. Sending the whole set at once
        # is sufficient for the quote session and reduces round trips.
        self._send_command(
            "quote_fast_symbols",
            [self._quote_session, *symbols],
        )

        quotes: dict[str, dict[str, Any]] = {s: {} for s in symbols}
        forecast_fields: dict[str, dict[str, Any]] = {s: {} for s in symbols}

        deadline = time.monotonic() + self.timeout
        first_complete_at: float | None = None

        while time.monotonic() < deadline:
            remaining = max(0.2, deadline - time.monotonic())
            self._ws.settimeout(remaining)

            try:
                frame = self._ws.recv()
            except websocket.WebSocketTimeoutException:
                break

            if isinstance(frame, bytes):
                frame = frame.decode("utf-8", errors="replace")

            for payload in self._iter_payloads(frame):
                # TradingView heartbeat. Echo exactly the payload back in an envelope.
                if payload.startswith("~h~"):
                    self._ws.send(self._frame(payload))
                    continue

                try:
                    message = json.loads(payload)
                except json.JSONDecodeError:
                    continue

                if message.get("m") != "qsd":
                    continue

                params = message.get("p") or []
                if len(params) < 2 or not isinstance(params[1], dict):
                    continue

                quote_msg = params[1]
                name = quote_msg.get("n")
                if name not in quotes:
                    continue

                values = quote_msg.get("v")
                if not isinstance(values, dict):
                    continue

                # qsd is incremental: merge every update.
                quotes[name].update(values)

                if include_forecast_fields:
                    for key, value in values.items():
                        if key in FORECAST_FIELDS or looks_like_forecast_field(key):
                            forecast_fields[name][key] = value

            # Target fields are the key signal that the Forecast dataset has arrived.
            complete = all(
                (
                    quotes[s].get("price_target_average") is not None
                    or quotes[s].get("forecast_availability") == 0
                )
                for s in symbols
            )

            if complete:
                # Small grace window: qsd is incremental and recommendation fields
                # may arrive in a neighboring frame.
                if first_complete_at is None:
                    first_complete_at = time.monotonic()
                elif time.monotonic() - first_complete_at >= 0.35:
                    break

        forecasts = {
            symbol: self._forecast_from_quote(symbol, quotes[symbol])
            for symbol in symbols
        }

        if not include_forecast_fields:
            forecast_fields = {}

        all_qsd_fields = quotes if include_all_qsd_fields else {}

        return forecasts, forecast_fields, all_qsd_fields

    def get_forecast(self, symbol: str) -> Forecast:
        forecasts, _, _ = self.get_forecasts([symbol])
        return forecasts[self._normalize_symbol(symbol)]

    def get_forecast_fields(self, symbol: str) -> dict[str, Any]:
        """Return every forecast/estimate/recommendation field detected for one symbol."""
        _, fields, _ = self.get_forecasts([symbol], include_forecast_fields=True)
        return fields[self._normalize_symbol(symbol)]

    def get_all_qsd_fields(self, symbol: str) -> dict[str, Any]:
        """Return the complete merged TradingView qsd dictionary for one symbol."""
        _, _, raw = self.get_forecasts(
            [symbol],
            include_forecast_fields=True,
            include_all_qsd_fields=True,
        )
        return raw[self._normalize_symbol(symbol)]


def _main() -> None:
    parser = argparse.ArgumentParser(
        description="Read analyst price targets/recommendations from TradingView's internal quote WS."
    )
    parser.add_argument(
        "symbols",
        nargs="+",
        help="Symbols with exchange prefix, e.g. HOSE:VJC HOSE:MWG",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=12.0,
        help="Receive timeout in seconds (default: 12)",
    )
    parser.add_argument(
        "--forecast-fields",
        action="store_true",
        help="Print all detected forecast/estimate/recommendation fields, including histories.",
    )
    parser.add_argument(
        "--all-qsd",
        action="store_true",
        help="Print the complete merged qsd payload (all TradingView quote fields).",
    )
    args = parser.parse_args()

    with TradingViewForecastClient(timeout=args.timeout) as client:
        forecasts, forecast_fields, all_qsd = client.get_forecasts(
            args.symbols,
            include_forecast_fields=True,
            include_all_qsd_fields=args.all_qsd,
        )

    output: dict[str, Any] = {
        "core": {
            symbol: forecast.to_dict()
            for symbol, forecast in forecasts.items()
        }
    }

    if args.forecast_fields:
        output["forecast_fields"] = forecast_fields

    if args.all_qsd:
        output["all_qsd_fields"] = all_qsd

    print(json.dumps(output, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    _main()