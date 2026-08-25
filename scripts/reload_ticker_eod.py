"""Reload toàn bộ lịch sử EOD của một Ticker (mặc định MWG) từ Amibroker vào raw_stock_eod.

Cách chạy:
    python scripts\reload_ticker_eod.py            # reload MWG
    python scripts\reload_ticker_eod.py FPT        # reload ticker khác

Lưu ý: đóng webapp/NiceGUI trước khi chạy để tránh lock file DuckDB.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from CrawlStock.readAmi import read_amibroker_dat  # noqa: E402
from Ults.DuckLib import DuckDBManager  # noqa: E402
from Ults.lstPara import AMIBROKER_EOD_STOCK_PATH  # noqa: E402

TABLE_TARGET = '"CherryMon"."main"."raw_stock_eod"'


def main() -> int:
    ticker = (sys.argv[1] if len(sys.argv) > 1 else "MWG").strip().upper()
    dat_path = AMIBROKER_EOD_STOCK_PATH / f"{ticker}.dat"

    if not dat_path.exists():
        print(f"[ERROR] Không tìm thấy file Amibroker: {dat_path}")
        return 1

    print(f"[*] Đọc toàn bộ lịch sử từ: {dat_path}")
    df_ticker = read_amibroker_dat(str(dat_path), from_date=None)
    if df_ticker is None or df_ticker.empty:
        print(f"[ERROR] File {dat_path} không đọc được dữ liệu hợp lệ.")
        return 1
    df_ticker.insert(0, "Ticker", ticker)
    df_ticker["Date"] = df_ticker["Date"].dt.date
    before_rows = len(df_ticker)
    df_ticker.drop_duplicates(subset=["Ticker", "Date"], keep="last", inplace=True)
    print(f"[*] Số dòng đọc được: {before_rows} | sau khi dedupe: {len(df_ticker)}")
    print(f"[*] Khoảng dữ liệu: {df_ticker['Date'].min()} -> {df_ticker['Date'].max()}")

    # Xóa toàn bộ dòng cũ của ticker này để nạp lại sạch (delete-then-insert cho 1 ticker),
    # không đụng tới dữ liệu các ticker khác.
    with DuckDBManager(read_only=False) as con:
        deleted = con.execute(
            f"DELETE FROM {TABLE_TARGET} WHERE Ticker = ?", [ticker]
        ).fetchone()
        print(f"[*] Đã xóa {deleted[0] if deleted else 0} dòng cũ của {ticker}.")

        # Upsert lại bằng pattern chuẩn của project (ON CONFLICT bảo vệ dữ liệu).
        # KHÔNG dùng upsert_stock_eod(folder, from_last_day=None) vì hàm đó sẽ
        # DROP toàn bảng raw_stock_eod — chỉ nạp đúng ticker đang reload.
        con.register("df_reload_ticker", df_ticker)
        con.execute(f"""
            INSERT INTO {TABLE_TARGET} (Ticker, Date, Open, High, Low, Close, Volume, OpenInt)
            SELECT Ticker, Date, Open, High, Low, Close, Volume, OpenInt
            FROM df_reload_ticker
            ON CONFLICT (Ticker, Date) DO UPDATE SET
                Open = EXCLUDED.Open,
                High = EXCLUDED.High,
                Low = EXCLUDED.Low,
                Close = EXCLUDED.Close,
                Volume = EXCLUDED.Volume,
                OpenInt = EXCLUDED.OpenInt;
        """)
        con.unregister("df_reload_ticker")

    with DuckDBManager(read_only=True) as con:
        summary = con.execute(
            f"""
            SELECT COUNT(*) AS total_rows,
                   MIN(Date) AS min_date,
                   MAX(Date) AS max_date
            FROM {TABLE_TARGET}
            WHERE Ticker = ?
            """,
            [ticker],
        ).df()
    print(f"[OK] Reload hoàn tất cho {ticker}:")
    print(summary)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
