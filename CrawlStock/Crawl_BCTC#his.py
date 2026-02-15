from playwright.sync_api import sync_playwright
from lxml import html
import pandas as pd
import time
from lstPara import var_user_agent, lstTicker

def extract_header(page, 
                   plocator_tbl,      # locator của table (vd: "#table-0")
                   plocator_header,   # locator header cell (vd: "thead tr th")
                   plocator_tag=None  # locator tag con nếu muốn lấy riêng (vd: "b")
                   ):
    
    table = page.locator(plocator_tbl)
    headers = []
    header_cells = table.locator(plocator_header)
    header_count = header_cells.count()
    for i in range(header_count):
        cell = header_cells.nth(i)
        # Nếu có tag con (ví dụ <b>)
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

def extract_table(page, plocator_tbl, page_index=None):
    # =========================
    # HEADER
    # =========================
    headers = extract_header(page=page,plocator_tbl=plocator_tbl,plocator_header="thead tr th",plocator_tag="b")    
    
    table = page.locator(plocator_tbl)

    # =========================
    # HEADER
    # =========================
    headers = []
    header_cells = table.locator("thead tr th")
    header_count = header_cells.count()

    for i in range(header_count):
        # nếu muốn chỉ lấy tiêu đề quý
        b_tag = header_cells.nth(i).locator("b")
        if b_tag.count() > 0:
            text = b_tag.inner_text().strip()
        else:
            text = header_cells.nth(i).inner_text().strip()

        headers.append(text)

    # =========================
    # BODY
    # =========================
    rows = table.locator("tbody tr.Normal")
    row_count = rows.count()

    table_data = []

    for i in range(row_count):
        row = rows.nth(i)
        cells = row.locator("td")

        row_data = [] # reset row avoid duplication
        cell_count = cells.count()

        for j in range(cell_count):
            cell_text = "" # reset data cell avoid duplication
            cell_text = cells.nth(j).inner_text().strip()
            row_data.append(cell_text)

        table_data.append(row_data)
        

    # =========================
    # CONVERT to DATAFRAME
    # =========================
    df = pd.DataFrame(table_data, columns=headers)

    # thêm page_index nếu có
    if page_index is not None:
        df["page_index"] = page_index

    return df

def crawl_all_pages(URL):
    _data_KQKD = []
    _data_CDKT = []
    _data_CSTC = []

    with sync_playwright() as p:
        
        browser = p.chromium.launch(headless=True,args=["--disable-blink-features=AutomationControlled"])
        context = browser.new_context(user_agent = var_user_agent, viewport={"width": 1366, "height": 768})
        page = context.new_page()
        page.set_default_navigation_timeout(10000)
        page.goto(URL
            ,wait_until="domcontentloaded" # không chờ full load
            ,timeout=10000 # tăng lên 60s 
            )
        page.wait_for_timeout(5000)
        print("Current URL:", page.url)
        page_count = 1

        while True:

            # Extract table Kết quả kinh doanh -----------------------------
            page.wait_for_selector('xpath=//*[@id="table-0"]')
            df = extract_table(page,"#table-0")
            if df is not None:
                df["page_index"] = page_count
                _data_KQKD.append(df)
 
            # Extract Cân đối kế toán --------------------------------------
            # Extract Chỉ số tài chính -------------------------------------

            # Tìm nút chevron-left
            next_btn = page.locator('.fa-chevron-left.pull-left')
            if next_btn.count() == 0:
                print("not found the button")
                break

            # Kiểm tra nếu bị disabled
            parent = next_btn.locator('xpath=..').nth(1)
            class_attr = parent.get_attribute("class")

            if class_attr and "disabled" in class_attr:
                break

            try:
                parent.click()
                time.sleep(2)
                page_count += 1
            except:
                print("cannot click")
                break

        browser.close()

    if _data_KQKD:
        return pd.concat(_data_KQKD, ignore_index=True) # final DataFrame
    else:
        return None

# Main file
if __name__ == "__main__":
    
    for _ticker in lstTicker:
        print(_ticker[0],_ticker[1])
        df = crawl_all_pages(_ticker[1])
        if df is not None:
            # Cleansing data
            df = df.replace(',', '', regex=True) 
            
            # Sum up data
            df = df.groupby(df.columns[0], as_index=False).first() 
            
            # Transpose Column to Row
            df = df.set_index(df.columns[0]).T.reset_index()
            df["Ticker"] = _ticker[0]
        else:
            print("no data")

    # export file data
    df.to_csv("BCTQ.csv", index=False, encoding="utf-8-sig")