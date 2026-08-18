from __future__ import annotations

import os
import threading
import time

import pandas as pd

from CrawlStock.readAmi import _build_default_amibroker_adapter
from Ults.DuckLib import DuckDBManager
from Ults.Timing import timeit, toggle_print
from Ults.lstPara import AMIBROKER_AFL_PATH, AMIBROKER_LOG_PATH, DATAFILE_PATH
from cherrystock.application.ports.amibroker import AmiBrokerPort
from cherrystock.application.services.sync_amibroker_fa import SyncAmiBrokerFAService


@timeit
@toggle_print(allow_print=False)
def upsert_stock_fa(amibroker: "AmiBrokerPort | None" = None, connection=None):
    """Export FA from AmiBroker and upsert it into ``raw_stock_fa``.

    The CSV is normalized before DuckDB sees it:
    - legacy ``Date/Time`` is renamed to ``Date``;
    - ``Date`` is converted to Python ``date`` so DuckDB maps it to DATE;
    - INSERT/SELECT columns are explicit instead of relying on column order.
    """
    exported_csv_path = DATAFILE_PATH / "tmp_Export_Shares.csv"
    amibroker_afl_shares = AMIBROKER_AFL_PATH / "Export Shares.afl"
    con = connection or DuckDBManager.get_connection()
    owns_connection = connection is None
    table_name = "raw_stock_fa"

    try:
        if amibroker is None:
            amibroker = _build_default_amibroker_adapter()

        service = SyncAmiBrokerFAService(amibroker)
        print("[*] Bắt đầu tiến trình cập nhật Fundamental Analysis (FA)...")

        if os.path.exists(AMIBROKER_LOG_PATH):
            open(AMIBROKER_LOG_PATH, "w", encoding="utf-8").close()

        export_error: list[Exception] = []

        def run_amibroker_explore() -> None:
            try:
                service.run_latest_export(
                    formula_path=amibroker_afl_shares,
                    export_path=exported_csv_path,
                    apply_to=0,
                    range_mode=2,
                    range_n=1,
                )
            except Exception as exc:
                export_error.append(exc)
                print(f"❌ LỖI trong luồng AmiBroker COM: {exc}")

        explore_thread = threading.Thread(target=run_amibroker_explore)
        explore_thread.start()

        last_pos = 0
        while explore_thread.is_alive():
            if os.path.exists(AMIBROKER_LOG_PATH):
                with open(AMIBROKER_LOG_PATH, "r", encoding="utf-8", errors="ignore") as log_file:
                    log_file.seek(last_pos)
                    for line in log_file.readlines():
                        print(f"[AmiBroker _TRACE]: {line.strip()}")
                    last_pos = log_file.tell()
            time.sleep(0.5)

        explore_thread.join()

        if export_error:
            raise RuntimeError("AmiBroker FA export failed") from export_error[0]

        if os.path.exists(AMIBROKER_LOG_PATH):
            with open(AMIBROKER_LOG_PATH, "r", encoding="utf-8", errors="ignore") as log_file:
                log_file.seek(last_pos)
                for line in log_file.readlines():
                    print(f"[AmiBroker _TRACE]: {line.strip()}")

        print("[*] AmiBroker Script Execution Hoàn tất!")

        if not os.path.exists(exported_csv_path.as_posix()):
            raise FileNotFoundError(f"Không tìm thấy file dữ liệu tại {exported_csv_path.as_posix()}")

        df = pd.read_csv(exported_csv_path.as_posix())
        if df.empty:
            raise ValueError("Dữ liệu FA export từ AmiBroker trống.")

        # Normalize headers first because AmiBroker exports may contain surrounding spaces.
        df.columns = [str(column).strip() for column in df.columns]

        if "Ticker" not in df.columns:
            df.rename(columns={df.columns[0]: "Ticker"}, inplace=True)

        # Backward compatibility with the old AFL/CSV header.
        if "Date/Time" in df.columns:
            if "Date" in df.columns:
                df.drop(columns=["Date/Time"], inplace=True)
            else:
                df.rename(columns={"Date/Time": "Date"}, inplace=True)

        df["Ticker"] = df["Ticker"].astype(str).str.strip().str.upper()
        df = df[df["Ticker"].ne("") & df["Ticker"].ne("NAN")].copy()

        if "Date" not in df.columns:
            raise ValueError("FA CSV không có cột 'Date'.")

        parsed_date = pd.to_datetime(df["Date"], errors="coerce")
        invalid_date_count = int(parsed_date.isna().sum())
        if invalid_date_count:
            print(f"[!] Bỏ {invalid_date_count} dòng FA có Date không hợp lệ.")
        df["Date"] = parsed_date.dt.date
        df = df[df["Date"].notna()].copy()

        if df.empty:
            raise ValueError("Không còn dữ liệu FA hợp lệ sau khi chuẩn hóa Date.")

        df.drop_duplicates(subset=["Ticker"], keep="last", inplace=True)

        con.register("df_fa_tmp", df)
        try:
            con.execute("DROP TABLE IF EXISTS _tmp_fa_schema;")
            con.execute("CREATE TEMPORARY TABLE _tmp_fa_schema AS SELECT * FROM df_fa_tmp LIMIT 0;")
            schema_info = con.execute("DESCRIBE _tmp_fa_schema;").fetchall()

            cols_def: list[str] = []
            update_cols: list[str] = []
            for row in schema_info:
                col_name, col_type = row[0], row[1]
                if col_name == "Ticker":
                    cols_def.append(f'"{col_name}" {col_type} PRIMARY KEY')
                else:
                    # Keep Date deterministic even if a pandas/duckdb version infers differently.
                    if col_name == "Date":
                        col_type = "DATE"
                    cols_def.append(f'"{col_name}" {col_type}')
                    update_cols.append(col_name)

            con.execute(
                f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(cols_def)});"
            )

            table_schema = con.execute(f"DESCRIBE {table_name};").fetchall()
            table_columns = {row[0]: row[1] for row in table_schema}

            missing_columns = [column for column in df.columns if column not in table_columns]
            if missing_columns:
                raise ValueError(
                    f"raw_stock_fa thiếu column so với FA CSV: {missing_columns}. "
                    "Cần đồng bộ schema trước khi upsert."
                )

            if str(table_columns.get("Date", "")).upper() != "DATE":
                raise TypeError(
                    f"raw_stock_fa.Date phải là DATE, hiện tại là {table_columns.get('Date')}."
                )

            columns = list(df.columns)
            insert_columns = ", ".join(f'"{column}"' for column in columns)
            select_columns = ", ".join(f'"{column}"' for column in columns)
            update_columns = [column for column in columns if column != "Ticker"]
            update_clause = ", ".join(
                f'"{column}" = EXCLUDED."{column}"' for column in update_columns
            )

            print(f"[*] Đang ghi đè (Upsert) {len(df)} bản ghi FA vào bảng '{table_name}'...")
            con.execute(
                f"""
                INSERT INTO {table_name} ({insert_columns})
                SELECT {select_columns}
                FROM df_fa_tmp
                ON CONFLICT (Ticker) DO UPDATE SET {update_clause};
                """
            )

            row_count = con.execute(f"SELECT COUNT(*) FROM {table_name};").fetchone()[0]
            print(f"[✔] Upsert Stock FA hoàn tất. raw_stock_fa hiện có {row_count} bản ghi.")
        finally:
            con.execute("DROP TABLE IF EXISTS _tmp_fa_schema;")
            try:
                con.unregister("df_fa_tmp")
            except Exception:
                pass
    finally:
        if owns_connection:
            DuckDBManager.close_connection(con)
