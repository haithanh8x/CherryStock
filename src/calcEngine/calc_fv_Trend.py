from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
from Ults.DuckLib import DuckDBManager
from Ults.Timing import timeit, toggle_print


@timeit
@toggle_print(allow_print=False)
def cal_Moving_Average(from_last_day: Optional[int] = None, connection=None, repository=None) -> None:
    """
    Tính toán các đường trung bình động MA(20), MA(50), MA(100), MA(200) theo từng Ticker.

    - Dữ liệu nguồn: "CherryMon"."main"."raw_stock_eod" join với
      "CherryMon"."main"."raw_lstTicker" theo Ticker để lấy điều kiện status = 'Y'
      (cột status nằm ở raw_lstTicker).
    - Toàn bộ lịch sử giá của mỗi Ticker được lấy để đảm bảo MA(200) được tính đúng
      ngay tại checkpoint, sau đó chỉ giữ lại các bản ghi từ checkpoint để upsert.
    - Kết quả được upsert (INSERT ... ON CONFLICT DO UPDATE) vào bảng cal_Trends.

    Parameters:
    - from_last_day: số ngày gần nhất để tính checkpoint upsert (tương tự syncAmibroker_EOD/
      syncYahooFinance_EOD). None -> lấy toàn bộ lịch sử để upsert.
    """
    table_lstTicker = '"CherryMon"."main"."raw_lstTicker"'
    table_stock_eod = '"CherryMon"."main"."raw_stock_eod"'
    table_target = '"CherryMon"."main"."cal_Trends"'

    con = connection or DuckDBManager.get_connection()
    owns_connection = connection is None
    try:
        relation = (
            con.table(table_lstTicker).set_alias("lt")
                .join(con.table(table_stock_eod).set_alias("eod"), "lt.Ticker = eod.Ticker")
                .filter("lt.status = 'Y'")
                .project("lt.Ticker, eod.Date, eod.Close")
                .order("Ticker, Date")
        )
        df = relation.df()
    finally:
        if owns_connection:
            DuckDBManager.close_connection(con)

    if df.empty:
        print("Không có dữ liệu raw_stock_eod với status = 'Y' để tính Moving Average.")
        return

    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values(["Ticker", "Date"]).reset_index(drop=True)

    windows = {"MA20": 20, "MA50": 50, "MA100": 100, "MA200": 200}
    for col_name, window in windows.items():
        df[col_name] = (
            df.groupby("Ticker")["Close"]
              .transform(lambda s: s.rolling(window=window, min_periods=window).mean())
        )

    # Weekly/Monthly MA: tính trên chuỗi Close resample theo tuần (W-FRI) và tháng (ME),
    # sau đó map giá trị MA kỳ lớn về từng ngày giao dịch trong kỳ đó.
    weekly_ma_columns = ("MA20_W", "MA50_W")
    monthly_ma_columns = ("MA20_M", "MA50_M")
    for col_name in (*weekly_ma_columns, *monthly_ma_columns):
        df[col_name] = pd.NA

    for ticker, ticker_df in df.groupby("Ticker", sort=False):
        ticker_index = ticker_df.index
        for frequency, ma_columns in (("W-FRI", weekly_ma_columns), ("ME", monthly_ma_columns)):
            period_close = (
                ticker_df.set_index("Date")["Close"].resample(frequency).last().dropna()
            )
            period_frame = pd.DataFrame(index=period_close.index)
            period_frame["MA20_W" if frequency == "W-FRI" else "MA20_M"] = (
                period_close.rolling(window=20, min_periods=20).mean()
            )
            period_frame["MA50_W" if frequency == "W-FRI" else "MA50_M"] = (
                period_close.rolling(window=50, min_periods=50).mean()
            )
            mapped = pd.merge_asof(
                ticker_df[["Date"]].sort_values("Date"),
                period_frame.reset_index()
                    .rename(columns={period_frame.index.name or "index": "PeriodEnd"})
                    .rename(columns={"PeriodEnd": "Date"}),
                on="Date",
                direction="backward",
            )
            for col_name in ma_columns:
                df.loc[ticker_index, col_name] = mapped[col_name].to_numpy()

    ma_columns = [*windows.keys(), *weekly_ma_columns, *monthly_ma_columns]
    if from_last_day is not None:
        from_date = datetime.now() - timedelta(days=from_last_day)
        df_result = df.loc[df["Date"] >= from_date, ["Ticker", "Date", "Close", *ma_columns]].copy()
    else:
        df_result = df[["Ticker", "Date", "Close", *ma_columns]].copy()
    df_result = df_result.dropna(subset=ma_columns, how="all")

    if df_result.empty:
        print(f"Không có dữ liệu Moving Average từ from_last_day={from_last_day} để upsert vào cal_Trends.")
        return

    df_result["Date"] = df_result["Date"].dt.date

    if repository is not None:
        repository.upsert_moving_average(dataframe=df_result, table_name=table_target)
        return

    con = connection or DuckDBManager.get_connection()
    owns_connection = connection is None
    try:
        con.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_target} (
                Ticker VARCHAR,
                Date DATE,
                Close DOUBLE,
                MA20 DOUBLE,
                MA50 DOUBLE,
                MA100 DOUBLE,
                MA200 DOUBLE,
                MA20_W DOUBLE,
                MA50_W DOUBLE,
                MA20_M DOUBLE,
                MA50_M DOUBLE,
                PRIMARY KEY (Ticker, Date)
            );
        """)
        for added_column in ("MA20_W", "MA50_W", "MA20_M", "MA50_M"):
            con.execute(f"ALTER TABLE {table_target} ADD COLUMN IF NOT EXISTS {added_column} DOUBLE;")

        con.register("df_moving_average", df_result)
        con.execute(f"""
            INSERT INTO {table_target} (Ticker, Date, Close, MA20, MA50, MA100, MA200, MA20_W, MA50_W, MA20_M, MA50_M)
            SELECT Ticker, Date, Close, MA20, MA50, MA100, MA200, MA20_W, MA50_W, MA20_M, MA50_M
            FROM df_moving_average
            ON CONFLICT (Ticker, Date) DO UPDATE SET
                Close = EXCLUDED.Close,
                MA20 = EXCLUDED.MA20,
                MA50 = EXCLUDED.MA50,
                MA100 = EXCLUDED.MA100,
                MA200 = EXCLUDED.MA200,
                MA20_W = EXCLUDED.MA20_W,
                MA50_W = EXCLUDED.MA50_W,
                MA20_M = EXCLUDED.MA20_M,
                MA50_M = EXCLUDED.MA50_M;
        """)
        con.unregister("df_moving_average")
    finally:
        if owns_connection:
            DuckDBManager.close_connection(con)