from playwright.sync_api import sync_playwright
import pandas as pd
from datetime import datetime
from lstPara import var_user_agent, lstTicker, var_Datafile_Folder
from functools import reduce

# =========================================================
# LIB Function
# =========================================================
def fnc_quarter_to_date(qstr: str) -> str:
    qstr = qstr.strip()
    # Tách quý và năm
    quarter_part, year = qstr.replace("Quý", "").strip().split("/")
    quarter = int(quarter_part)
    # Map quý -> tháng bắt đầu
    quarter_month_map = {
        1: 1,
        2: 4,
        3: 7,
        4: 10
    }
    if quarter not in quarter_month_map:
        raise ValueError("Quarter must be 1-4")
    month = quarter_month_map[quarter]
    date_obj = datetime(int(year), month, 1)
    return date_obj.strftime("%Y%m%d").upper()

# =========================================================
# EXTRACT HEADER
# =========================================================
def extract_header(page,
                   plocator_tbl,
                   plocator_header="thead tr th",
                   plocator_tag="b"):

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

    data_table_0 = []
    headers_0 = None

    data_table_1 = []
    headers_1 = None
    
    data_table_2 = []
    headers_2 = None
    
    with sync_playwright() as p:

        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state="state.json")
        page = context.new_page() # pyright: ignore[reportCallIssue]

        cookies = context.cookies()
        print("cookies runtime:", len(cookies))
        print([ (c["name"], c["domain"]) for c in cookies[:15] ]) # type: ignore

        page.goto(URL, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)

        page_count = 1

        while True:

            #print(f"Processing page {page_count}")
            page.wait_for_selector("#table-0")

            # ==============================
            # HEADER
            # ==============================
            headers_0 = extract_header(page, "#table-0")
            headers_0 = make_unique_columns(headers_0)

            headers_1 = extract_header(page, "#table-1")
            headers_1 = make_unique_columns(headers_1)

            headers_2 = extract_header(page, "#table-2")
            headers_2 = make_unique_columns(headers_2)
            # ==============================
            # TABLE 0
            # ==============================
            df0 = extract_table(page, "#table-0", "tbody tr.Normal", headers_0)
            if df0 is not None:
                data_table_0.append(df0)

            # ==============================
            # TABLE 1
            # ==============================
            df1 = extract_table(page, "#table-1", "tbody tr.Normal", headers_1)
            if df1 is not None:
                data_table_1.append(df1)

            # ==============================
            # TABLE 2
            # ==============================
            df2 = extract_table(page, "#table-2", "tbody tr", headers_2)
            if df2 is not None:
                data_table_2.append(df2)

            # ==============================
            # PAGINATION
            # ==============================
            next_btn = page.locator("div.btn.btn-default.m-l").first

            if next_btn.count() == 0:
                print("Next button not found")
                break

            try:
                next_btn.scroll_into_view_if_needed()

                # Lấy nội dung toàn bộ tbody trước khi click
                table_before = page.locator("#table-0 tbody").inner_text()

                next_btn.click(force=True)

                # Chờ 1 chút cho AJAX chạy
                page.wait_for_timeout(1000)

                # Lấy lại nội dung sau khi click
                table_after = page.locator("#table-0 tbody").inner_text()

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
    # CONCAT SAFE
    # ==============================
    df_table_0 = pd.concat(data_table_0, ignore_index=True) if data_table_0 else None
    df_table_1 = pd.concat(data_table_1, ignore_index=True) if data_table_1 else None
    df_table_2 = pd.concat(data_table_2, ignore_index=True) if data_table_2 else None

    return df_table_0, df_table_1, df_table_2


# =========================================================
# MAIN
# =========================================================
if __name__ == "__main__":

    for _ticker in lstTicker:

        print("Processing:", _ticker[0])

        df0, df1, df2  = crawl_all_pages(_ticker[1])

        # TRANSFORM and clean data

        # =============================
        # EXPORT TABLE 0
        # =============================
        if df0 is not None:
            df0 = df0.replace(',', '', regex=True)
            df0 = df0.groupby(df0.columns[0], as_index=False).first()
            df0 = df0.set_index(df0.columns[0]).T.reset_index()
            df0[df0.columns[0]] = df0[df0.columns[0]].apply(fnc_quarter_to_date)
            df0["Ticker"] = _ticker[0]
            df0["Ticker"] = _ticker[0]       
            df0.to_csv(
                var_Datafile_Folder + f"BCTQ_table0_{_ticker[0]}.csv",
                index=False,
                encoding="utf-8-sig")

        # =============================
        # EXPORT TABLE 1
        # =============================
        if df1 is not None:
            df1 = df1.replace(',', '', regex=True)
            df1 = df1.groupby(df1.columns[0], as_index=False).first()
            df1 = df1.set_index(df1.columns[0]).T.reset_index()
            df1[df1.columns[0]] = df1[df1.columns[0]].apply(fnc_quarter_to_date)
            df1["Ticker"] = _ticker[0]
            df1.to_csv(
                var_Datafile_Folder + f"BCTQ_table1_{_ticker[0]}.csv",
                index=False,
                encoding="utf-8-sig")
            
        # =============================
        # EXPORT TABLE 2
        # =============================
        if df2 is not None:
            df2 = df2.replace(',', '', regex=True)
            df2 = df2.groupby(df2.columns[0], as_index=False).first()
            df2 = df2.set_index(df2.columns[0]).T.reset_index()
            df2[df2.columns[0]] = df2[df2.columns[0]].apply(fnc_quarter_to_date)
            df2["Ticker"] = _ticker[0]
            df2.to_csv(
                var_Datafile_Folder + f"BCTQ_table2_{_ticker[0]}.csv",
                index=False,
            encoding="utf-8-sig")

