from playwright.sync_api import sync_playwright
from lxml import html
import pandas as pd
import time
URL = "https://finance.vietstock.vn/MWG-ctcp-dau-tu-the-gioi-di-dong.htm?tab=BCTQ"
# URL = "https://f319.com/"

def extract_table(page, page_index=None):
    table = page.locator("#table-0")

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

        row_data = []
        cell_count = cells.count()

        for j in range(cell_count):
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

def crawl_all_pages():
    all_data = []

    with sync_playwright() as p:
        
        browser = p.chromium.launch(headless=True, # test trước
                                    args=["--disable-blink-features=AutomationControlled"])

        context = browser.new_context(
            user_agent= "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36",
                        viewport={"width": 1366, "height": 768})

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
            print(f" Crawling page {page_count}")
            
            page.wait_for_selector('xpath=//*[@id="table-0"]')

            df = extract_table(page)
            if df is not None:
                df["page_index"] = page_count
                all_data.append(df)

            # Tìm nút chevron-left
            next_btn = page.locator('.fa-chevron-left.pull-left')

            if next_btn.count() == 0:
                print("not found the button")
                break

            # Kiểm tra nếu bị disabled
            parent = next_btn.locator('xpath=..').nth(1)
            class_attr = parent.get_attribute("class")

            if class_attr and "disabled" in class_attr:
                print("Button disabled")
                break

            try:
                parent.click()
                time.sleep(2)
                page_count += 1
            except:
                print("cannot click")
                break

        browser.close()

    if all_data:
        final_df = pd.concat(all_data, ignore_index=True)
        return final_df
    else:
        return None

# def crawl_f319():
#     results = []

#     with sync_playwright() as p:
#         browser = p.chromium.launch(
#             headless=False,
#             args=["--disable-blink-features=AutomationControlled"]
#         )

#         context = browser.new_context(
#             user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
#                        "AppleWebKit/537.36 (KHTML, like Gecko) "
#                        "Chrome/120.0.0.0 Safari/537.36"
#         )

#         page = context.new_page()
#         page.set_default_navigation_timeout(60000)

#         page.goto(URL, wait_until="domcontentloaded")
#         page.wait_for_selector(".discussionListItems")

#         # Lấy HTML phần discussionListItems
#         container = page.query_selector(".discussionListItems")
#         html_content = container.inner_html()

#         browser.close()

#     # Parse HTML bằng lxml
#     tree = html.fromstring(html_content)

#     # Mỗi topic thường là <li> trong list
#     topics = tree.xpath('//li[contains(@class,"discussionListItem")]')

#     for topic in topics:
#         try:
#             title = topic.xpath('.//a[@class="PreviewTooltip"]/text()')
#             link = topic.xpath('.//a[@class="PreviewTooltip"]/@href')
#             replies = topic.xpath('.//dd[@class="replies"]/text()')
#             views = topic.xpath('.//dd[@class="views"]/text()')

#             results.append({
#                 "title": title[0].strip() if title else "",
#                 "link": "https://f319.com" + link[0] if link else "",
#                 "replies": replies[0].strip() if replies else "",
#                 "views": views[0].strip() if views else ""
#             })
#         except:
#             continue

#     return pd.DataFrame(results)

if __name__ == "__main__":
    df = crawl_all_pages()

    # df.to_csv("f319_topics.csv", index=False, encoding="utf-8-sig")
    # print("Saved to f319_topics.csv")

    if df is not None:
        df = df.set_index(df.columns[0])  # lấy cột chỉ tiêu làm index
        df = df.T
        df.reset_index(inplace=True)
        df.rename(columns={"index": "period"}, inplace=True)

        df.to_csv("MWG_BCTQ_full.csv", index=False, encoding="utf-8-sig")
        print("saved file MWG_BCTQ_full.csv")
    else:
        print("no data")