"""
Automate Rundeck job execution for CherryMon.

Steps performed:
1. Open http://localhost:4440/user/login in Chrome/Chromium.
2. Log in with username/password: admin/admin.
3. Open project CherryMon.
4. Open job "Ingest Intraday Price".
5. Click "Run Job Now".

Requirements:
    pip install playwright
    python -m playwright install chromium

Run:
    python Orchestrator/run_rundeck_ingest_intraday.py
"""

from __future__ import annotations

import os
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, sync_playwright


RUNDECK_BASE_URL = os.getenv("RUNDECK_BASE_URL", "http://localhost:4440")
RUNDECK_USERNAME = os.getenv("RUNDECK_USERNAME", "admin")
RUNDECK_PASSWORD = os.getenv("RUNDECK_PASSWORD", "admin")
RUNDECK_PROJECT = os.getenv("RUNDECK_PROJECT", "CherryMon")
RUNDECK_JOB_NAME = os.getenv("RUNDECK_JOB_NAME", "Ingest Intraday Price")
HEADLESS = os.getenv("RUNDECK_HEADLESS", "false").strip().lower() in {"1", "true", "yes"}


def click_first_visible(page: Page, selectors: list[str], timeout: int = 10_000) -> None:
    """Click the first visible locator from a list of CSS/text selectors."""
    last_error: Exception | None = None

    for selector in selectors:
        try:
            locator = page.locator(selector).first
            locator.wait_for(state="visible", timeout=timeout)
            locator.click()
            return
        except Exception as exc:  # Playwright can raise multiple locator/action exceptions.
            last_error = exc

    raise RuntimeError(f"Could not click any selector: {selectors}") from last_error


def fill_first_visible(page: Page, selectors: list[str], value: str, timeout: int = 10_000) -> None:
    """Fill the first visible input from a list of selectors."""
    last_error: Exception | None = None

    for selector in selectors:
        try:
            locator = page.locator(selector).first
            locator.wait_for(state="visible", timeout=timeout)
            locator.fill(value)
            return
        except Exception as exc:
            last_error = exc

    raise RuntimeError(f"Could not fill any selector: {selectors}") from last_error


def login(page: Page) -> None:
    login_url = f"{RUNDECK_BASE_URL}/user/login"
    print(f"Opening login page: {login_url}")
    page.goto(login_url, wait_until="domcontentloaded")

    fill_first_visible(
        page,
        [
            "input[name='j_username']",
            "input[name='username']",
            "input#login",
            "input#username",
            "input[type='text']",
        ],
        RUNDECK_USERNAME,
    )
    fill_first_visible(
        page,
        [
            "input[name='j_password']",
            "input[name='password']",
            "input#password",
            "input[type='password']",
        ],
        RUNDECK_PASSWORD,
    )
    click_first_visible(
        page,
        [
            "button[type='submit']",
            "input[type='submit']",
            "text=Log In",
            "text=Login",
            "text=Sign in",
        ],
    )
    page.wait_for_load_state("networkidle")
    print("Logged in.")


def open_project(page: Page) -> None:
    print(f"Selecting project by click: {RUNDECK_PROJECT}")
    page.goto(RUNDECK_BASE_URL, wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")

    click_first_visible(
        page,
        [
            f"a:has-text('{RUNDECK_PROJECT}')",
            f"button:has-text('{RUNDECK_PROJECT}')",
            f".project-name:has-text('{RUNDECK_PROJECT}')",
            f".project_list_item:has-text('{RUNDECK_PROJECT}')",
            f"text={RUNDECK_PROJECT}",
        ],
        timeout=15_000,
    )
    page.wait_for_load_state("networkidle")


def open_job(page: Page) -> None:
    print(f"Opening job: {RUNDECK_JOB_NAME}")

    # Prefer direct UI search/click because job UUID is unknown.
    click_first_visible(
        page,
        [
            f"text={RUNDECK_JOB_NAME}",
            f"a:has-text('{RUNDECK_JOB_NAME}')",
            f".jobname:has-text('{RUNDECK_JOB_NAME}')",
        ],
        timeout=15_000,
    )
    page.wait_for_load_state("networkidle")


def run_job_now(page: Page) -> None:
    print("Clicking Run Job Now...")
    click_first_visible(
        page,
        [
            "text=Run Job Now",
            "button:has-text('Run Job Now')",
            "a:has-text('Run Job Now')",
            "button:has-text('Run')",
            "a:has-text('Run')",
        ],
        timeout=15_000,
    )

    # Some Rundeck versions show a confirmation/final run button after opening the run form.
    try:
        click_first_visible(
            page,
            [
                "button:has-text('Run Job Now')",
                "button:has-text('Run')",
                "input[type='submit'][value*='Run']",
            ],
            timeout=3_000,
        )
    except RuntimeError:
        pass

    try:
        page.wait_for_url("**/execution/**", timeout=10_000)
    except PlaywrightTimeoutError:
        # Job may still have been started; keep going and print current URL for troubleshooting.
        pass

    print(f"Done. Current URL: {page.url}")


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=HEADLESS,
            channel="chrome",
            args=["--start-maximized"],
        )
        context = browser.new_context(no_viewport=True)
        page = context.new_page()
        page.set_default_timeout(15_000)

        try:
            login(page)
            open_project(page)
            open_job(page)
            run_job_now(page)
        finally:
            if HEADLESS:
                browser.close()
            else:
                print("Browser is left open for review. Close it manually when finished.")


if __name__ == "__main__":
    main()