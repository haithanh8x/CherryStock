from playwright.sync_api import sync_playwright
import pandas as pd
from Ults.lstPara import lstTicker, db_path_CherryMon
from lstDuckDB import prc_upsert_by_ticker
import duckdb
import numpy as np
import sys, os, traceback
from concurrent.futures import ProcessPoolExecutor, as_completed


# =========================================================
# EXTRACT HEADER
# =========================================================
def extract_header(page,
                   plocator_tbl,
                   plocator_header="",
                   plocator_tag=""):

    table = page.locator(plocator_tbl)
    headers = []

    header_cells = table.locator(plocator_header)
    header_count = header_cells.count()

    for i in range(header_count):
        cell = header_cells.nth(i)

        if plocator_tag:
            child = cell.locator(plocator_tag)
            if child.count() > 0:
                text = child.inner_text().strip()
            else:
                text = cell.inner_text().strip()
        else:
            text = cell.inner_text().strip()

        headers.append(text)

    return headers

# =========================================================
# EXTRACT TABLE (BODY ONLY)
# =========================================================
def extract_table(page, plocator_tbl, plocator_row, headers, page_index=None):

    table = page.locator(plocator_tbl)
    rows = table.locator(plocator_row)
    row_count = rows.count()

    table_data = []

    for i in range(row_count):
        row = rows.nth(i)
        cells = row.locator("td")

        row_data = []
        cell_count = cells.count()

        for j in range(cell_count):
            cell_text = cells.nth(j).inner_text().strip()
            row_data.append(cell_text)

        table_data.append(row_data)

    if not table_data:
        return None

    if len(headers) != len(table_data[0]):
        print(f"Header mismatch in {plocator_tbl}")
        print("Header:", len(headers))
        print("Data:", len(table_data[0]))

    df = pd.DataFrame(table_data, columns=headers)

    if page_index is not None:
        df["page_index"] = page_index

    return df

def make_unique_columns(columns):
    seen = {}
    new_cols = []

    for col in columns:
        if col not in seen:
            seen[col] = 0
            new_cols.append(col)
        else:
            seen[col] += 1
            new_cols.append(f"{col}_{seen[col]}")

    return new_cols

# =========================================================
# CRAWL ALL PAGES
# =========================================================
def crawl_all_pages(URL):
    # TODO: change xpath
    # ==============================
    # TABLE 0
    # ==============================
    data_table_0 = []
    headers_0 = None
    vtableId_Tag_0 = "#tbl-data-BCTT-KQ"
    vHeader_Tag_0 = "thead tr th"
    vHeader_Tag_01 = ""
    vBody_Tag_0 = "tbody tr"
    vBody_all_Tag_0 = "#tbl-data-BCTT-KQ tbody"

    # ==============================
    # TABLE 1
    # ==============================
    data_table_1 = []
    headers_1 = None
    vtableId_Tag_1 = "#tbl-data-BCTT-CD"
    vHeader_Tag_1 = "thead tr th"
    vHeader_Tag_11 = ""
    vBody_Tag_1 = "tbody tr"
    
    # ==============================
    # TABLE 2
    # ==============================
    data_table_2 = []
    headers_2 = None
    vtableId_Tag_2 = "#tbl-data-BCTT-CSTC"
    vHeader_Tag_2 = "thead tr th"
    vHeader_Tag_21 = ""
    vBody_Tag_2 = "tbody tr"

    vButton_Prev = "//div[@name='btn-page-2']"

    with sync_playwright() as p:

        browser = p.chromium.launch(headless=True)
        # reuse login
        context = browser.new_context(storage_state="state.json")
        page = context.new_page() # pyright: ignore[reportCallIssue]

        page.goto(URL, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)

        page_count = 1

        while True:

            page.wait_for_selector(vtableId_Tag_0)

            # ==============================
            # TABLE 0
            # ==============================
            headers_0 = extract_header(page, plocator_tbl=vtableId_Tag_0, plocator_header=vHeader_Tag_0, plocator_tag=vHeader_Tag_01)
            headers_0 = make_unique_columns(headers_0)
            df0 = extract_table(page, vtableId_Tag_0, vBody_Tag_0, headers_0)
            if df0 is not None:
                data_table_0.append(df0)

            # ==============================
            # TABLE 1
            # ==============================
            headers_1 = extract_header(page, plocator_tbl=vtableId_Tag_1, plocator_header=vHeader_Tag_1, plocator_tag=vHeader_Tag_11)
            headers_1 = make_unique_columns(headers_1)
            df1 = extract_table(page, vtableId_Tag_1, vBody_Tag_1, headers_1)
            if df1 is not None:
                data_table_1.append(df1)

            # ==============================
            # TABLE 2
            # ==============================
            headers_2 = extract_header(page, plocator_tbl=vtableId_Tag_2, plocator_header=vHeader_Tag_2, plocator_tag=vHeader_Tag_21)
            headers_2 = make_unique_columns(headers_2)
            df2 = extract_table(page, vtableId_Tag_2, vBody_Tag_2, headers_2)
            if df2 is not None:
                data_table_2.append(df2)

            # ==============================
            # PAGINATION
            # ==============================
            next_btn = page.locator(vButton_Prev).first

            if next_btn.count() == 0:
                print("Next button not found")
                break

            try:
                next_btn.scroll_into_view_if_needed()
                # Lấy nội dung toàn bộ tbody trước khi click
                table_before = page.locator(vBody_all_Tag_0).inner_text()
                next_btn.click(force=True)
                # Chờ 1 chút cho AJAX chạy
                page.wait_for_timeout(1000)
                # Lấy lại nội dung sau khi click
                table_after = page.locator(vBody_all_Tag_0).inner_text()
                # Nếu không thay đổi => đã tới trang cuối
                if table_before == table_after:
                    #print("Last page reached")
                    break
                page_count += 1
            except Exception as e:
                print("Pagination error:", e)
                break
        browser.close()

    # ==============================
    # CONCAT SAFE # TODO: Concat Data Frame
    # ==============================
    df_table_0 = pd.concat(data_table_0, ignore_index=True) if data_table_0 else None
    df_table_1 = pd.concat(data_table_1, ignore_index=True) if data_table_1 else None
    df_table_2 = pd.concat(data_table_2, ignore_index=True) if data_table_2 else None

    return df_table_0, df_table_1, df_table_2

def upsert_DuckDB(con, _ticker, df0, df1, df2):
    # =============================
    # EXPORT TABLE 0
    # =============================
    if df0 is not None:
        df0 = df0.replace(',', '', regex=True)
        df0 = df0.groupby(df0.columns[0], as_index=False).first()
        df0 = df0.set_index(df0.columns[0]).T.reset_index()
        df0["Ticker"] = _ticker
        df0 = df0.replace(r'^\s*$', np.nan, regex=True)
        #print("df0 cols:", len(df0.columns), df0.columns.tolist())
        #print("table cols:", con.execute("SELECT COUNT(*) FROM pragma_table_info('bctc_kqkd')").fetchone()[0])
        prc_upsert_by_ticker(con, "bctc_kqkd", df0, _ticker, "Ticker")

    # =============================
    # EXPORT TABLE 1
    # =============================
    if df1 is not None:
        df1 = df1.replace(',', '', regex=True)
        df1 = df1.groupby(df1.columns[0], as_index=False).first()
        df1 = df1.set_index(df1.columns[0]).T.reset_index()
        df1["Ticker"] = _ticker
        df1 = df1.replace(r'^\s*$', np.nan, regex=True)
        prc_upsert_by_ticker(con, "bctc_cdkt", df1, _ticker, "Ticker")
        
    # =============================
    # EXPORT TABLE 2
    # =============================
    if df2 is not None:
        df2 = df2.replace(',', '', regex=True)
        df2 = df2.groupby(df2.columns[0], as_index=False).first()
        df2 = df2.set_index(df2.columns[0]).T.reset_index()
        df2["Ticker"] = _ticker
        df2 = df2.replace(r'^\s*$', np.nan, regex=True)
        prc_upsert_by_ticker(con, "bctc_cstc", df2, _ticker, "Ticker")

def crawl(_ticker):
    print(f"[Worker {os.getpid()}] START {_ticker}", flush=True)
    vURL = "https://finance.vietstock.vn/"+_ticker+"/tai-chinh.htm?tab=BCTT"
    # TODO: return df
    df0, df1, df2  = crawl_all_pages(vURL) # type: ignore
    return _ticker, df0, df1, df2


# =========================================================
# MAIN
# =========================================================
if __name__ == "__main__":
    # fix unicode cho printf
    os.environ["PYTHONIOENCODING"] = "utf-8"
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace") # type: ignore
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace") # type: ignore

    con = duckdb.connect(db_path_CherryMon)
    max_workers = 3
    futures = {}

    with ProcessPoolExecutor(max_workers=max_workers) as ex:
        for _ticker in lstTicker:
            ticker = _ticker[0]
            futures[ex.submit(crawl, ticker)] = ticker
        
        for fut in as_completed(futures):
            ticker = futures[fut]
            try:
                ticker, df0, df1, df2 = fut.result()
                if df0 is None and df1 is None and df2 is None:
                    print(f"Crawl failed / no data for {ticker}")
                    continue
                upsert_DuckDB(con, ticker, df0, df1, df2)             
            except Exception as e:
                print(f"ERROR at ticker {ticker} Reason:", e)
                traceback.print_exc()
                continue
    
    con.close();
