from __future__ import annotations

from typing import Optional

import pandas as pd
import yfinance as yf

from Ults.DuckLib import DuckDBManager
from Ults.Timing import timeit, toggle_print


YAHOO_OTHER_TICKERS = ["DX-Y.NYB", "BTC-USD", "VND=X", "GC=F"]


def _days_to_period(from_last_day: Optional[int]) -> str:
    """Convert day offset to a valid yfinance period string."""
    if from_last_day is None:
        return "1y"

    days = max(1, int(from_last_day))
    return f"{days}d"


def _normalize_date_arg(value: str, name: str) -> str:
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        raise ValueError(f"Invalid {name}: {value!r}. Expected YYYY-MM-DD.")
    return parsed.date().isoformat()


def _build_download_kwargs(
    from_last_day: Optional[int] = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> tuple[dict[str, object], str]:
    """Build a mutually exclusive yfinance period or explicit date-window request."""
    if start_date is None:
        if end_date is not None:
            raise ValueError("end_date requires start_date")
        period = _days_to_period(from_last_day)
        return {"period": period}, f"period={period}"

    start = _normalize_date_arg(start_date, "start_date")
    kwargs: dict[str, object] = {"start": start}
    label = f"start={start}"

    if end_date is not None:
        end = _normalize_date_arg(end_date, "end_date")
        if end <= start:
            raise ValueError("end_date must be later than start_date")
        kwargs["end"] = end
        label += f" | end(exclusive)={end}"

    return kwargs, label


def _normalize_yf_eod(df_raw: Optional[pd.DataFrame], ticker: str) -> pd.DataFrame:
    """Normalize yfinance EOD dataframe to target schema."""
    if df_raw is None or df_raw.empty:
        return pd.DataFrame(
            columns=["Ticker", "Date", "Open", "High", "Low", "Close", "Volume"]
        )

    df = df_raw.copy()

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]

    df = df.reset_index()

    if "Date" not in df.columns:
        first_col = str(df.columns[0])
        df = df.rename(columns={first_col: "Date"})

    df = df[["Date", "Open", "High", "Low", "Close", "Volume"]].copy()
    df.insert(0, "Ticker", ticker)

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.date
    df["Open"] = pd.to_numeric(df["Open"], errors="coerce")
    df["High"] = pd.to_numeric(df["High"], errors="coerce")
    df["Low"] = pd.to_numeric(df["Low"], errors="coerce")
    df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
    df["Volume"] = pd.to_numeric(df["Volume"], errors="coerce").fillna(0).astype("int64")
    df = df.dropna(subset=["Date", "Open", "High", "Low", "Close"])
    df = df.drop_duplicates(subset=["Ticker", "Date"], keep="last")
    return df


def _upsert_yahoo_eod(connection, df_all: pd.DataFrame) -> None:
    table_name = '"CherryMon"."main"."raw_other_eod"'
    connection.register("df_yf_other_eod", df_all)
    try:
        connection.execute(
            f"""
            INSERT INTO {table_name} (Ticker, Date, Open, High, Low, Close, Volume)
            SELECT Ticker, Date, Open, High, Low, Close, Volume
            FROM df_yf_other_eod
            ON CONFLICT (Ticker, Date) DO UPDATE SET
                Open = EXCLUDED.Open,
                High = EXCLUDED.High,
                Low = EXCLUDED.Low,
                Close = EXCLUDED.Close,
                Volume = EXCLUDED.Volume;
            """
        )
    finally:
        connection.unregister("df_yf_other_eod")


@timeit
@toggle_print(allow_print=False)
def syncYahooFinance_EOD(
    from_last_day: Optional[int] = None,
    connection=None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> None:
    """Sync Yahoo Finance EOD into CherryMon.main.raw_other_eod using idempotent upsert.

    Normal daily mode uses ``from_last_day`` and yfinance ``period``.
    Historical/backfill mode uses ``start_date`` and optional ``end_date``.
    yfinance treats ``end`` as exclusive.
    """
    ticker_list = [t.strip() for t in YAHOO_OTHER_TICKERS if str(t).strip()]
    if not ticker_list:
        print("Không có ticker hợp lệ để đồng bộ Yahoo Finance.")
        return

    download_window, window_label = _build_download_kwargs(
        from_last_day=from_last_day,
        start_date=start_date,
        end_date=end_date,
    )
    frames: list[pd.DataFrame] = []

    for ticker in ticker_list:
        print(f"[*] Download Yahoo EOD: {ticker} | {window_label}")
        df_raw = yf.download(
            ticker,
            interval="1d",
            auto_adjust=True,
            progress=False,
            **download_window,
        )

        df_norm = _normalize_yf_eod(df_raw=df_raw, ticker=ticker)
        if df_norm.empty:
            print(f"[WARN] Yahoo EOD empty after normalization: {ticker}")
            continue

        print(
            f"[+] Yahoo EOD normalized: {ticker} | rows={len(df_norm)} | "
            f"range={df_norm['Date'].min()}..{df_norm['Date'].max()}"
        )
        frames.append(df_norm)

    if not frames:
        print("Không có dữ liệu EOD hợp lệ từ Yahoo Finance.")
        return

    df_all = pd.concat(frames, ignore_index=True)
    df_all = df_all[["Ticker", "Date", "Open", "High", "Low", "Close", "Volume"]]
    print(f"[*] Yahoo EOD upsert rows prepared: {len(df_all)} | {window_label}")

    if connection is not None:
        _upsert_yahoo_eod(connection, df_all)
        return

    with DuckDBManager() as con:
        _upsert_yahoo_eod(con, df_all)
