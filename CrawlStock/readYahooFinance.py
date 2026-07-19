from __future__ import annotations
from typing import Optional
import pandas as pd
import yfinance as yf
from Ults.DuckLib import DuckDBManager
from Ults.Timing import timeit, toggle_print


YAHOO_OTHER_TICKERS = ["DX-Y.NYB","BTC-USD","VND=X"]


def _days_to_period(from_last_day: Optional[int]) -> str:
	"""Convert day offset to a valid yfinance period string."""
	if from_last_day is None:
		return "1y"

	days = max(1, int(from_last_day))
	return f"{days}d"


def _normalize_yf_eod(df_raw: Optional[pd.DataFrame], ticker: str) -> pd.DataFrame:
	"""Normalize yfinance EOD dataframe to target schema."""
	if df_raw is None or df_raw.empty:
		return pd.DataFrame(columns=["Ticker", "Date", "Open", "High", "Low", "Close", "Volume"])

	df = df_raw.copy()

	# If yfinance returns a MultiIndex (some setups), flatten to first level.
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

@timeit
@toggle_print(allow_print=False)
def syncYahooFinance_EOD(
	from_last_day: Optional[int] = None,
) -> None:
	"""
	Sync Yahoo Finance EOD into "CherryMon"."main"."raw_other_eod".

	- from_last_day: số ngày gần nhất để convert sang period của yf.download (vd: 15 -> "15d").
	- ticker list cố định: DX-Y.NYB, BTC-USD.
	"""
	ticker_list = [t.strip() for t in YAHOO_OTHER_TICKERS if str(t).strip()]
	if not ticker_list:
		print("Không có ticker hợp lệ để đồng bộ Yahoo Finance.")
		return

	period = _days_to_period(from_last_day)
	frames: list[pd.DataFrame] = []

	for ticker in ticker_list:
		print(f"[*] Download Yahoo EOD: {ticker} | period={period}")
		df_raw = yf.download(
			ticker,
			period=period,
			interval="1d",
			auto_adjust=True,
			progress=False,
		)

		df_norm = _normalize_yf_eod(df_raw=df_raw, ticker=ticker)
		if not df_norm.empty:
			frames.append(df_norm)

	if not frames:
		print("Không có dữ liệu EOD hợp lệ từ Yahoo Finance.")
		return

	df_all = pd.concat(frames, ignore_index=True)
	df_all = df_all[["Ticker", "Date", "Open", "High", "Low", "Close", "Volume"]]

	table_name = '"CherryMon"."main"."raw_other_eod"'
	with DuckDBManager() as con:
		con.register("df_yf_other_eod", df_all)
		con.execute(
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
		con.unregister("df_yf_other_eod")
