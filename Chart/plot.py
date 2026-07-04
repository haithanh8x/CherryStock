import pandas as pd
from lightweight_charts import JupyterChart
from Ults.DuckLib import DuckDBManager

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