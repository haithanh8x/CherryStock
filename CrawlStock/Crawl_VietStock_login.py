import html
from multiprocessing import context # type: ignore
from playwright.sync_api import sync_playwright

LOGIN_URL = "https://finance.vietstock.vn/"
EMAIL = "haithanh8x@outlook.com"
PASSWORD = "12091984Thanh"


with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    pw_context = browser.new_context()
    page = pw_context.new_page()

    page.goto(LOGIN_URL, wait_until="domcontentloaded")
    
    # If the modal is already open, just use it.
    # If not open, open it (safe code).
    if page.locator("#login-form:visible").count() == 0:
        # there are 2 elements; click the visible one
        page.locator("a.btnlogin-link:visible").first.click()

    # Wait modal visible
    page.wait_for_selector("#login-form", state="visible")

    # Fill fields (use your ids)
    page.fill("#txtEmailLogin", EMAIL)
    page.fill("#passwordLogin", PASSWORD)

    # Click submit
    page.click("#btnLoginAccount")

    # Wait for modal to disappear OR for something that indicates login success
    page.wait_for_selector("#login-form", state="hidden")

    # In cookies trước khi lưu
    cookies = pw_context.cookies()
    print("cookies runtime before save:", len(cookies))
    pw_context.storage_state(path="state.json")
    
    print("Logged in (modal closed).")

    # Now crawl protected pages
    page.goto("https://finance.vietstock.vn/", wait_until="networkidle")
    html = page.content()
    print(html[:500])

    browser.close()