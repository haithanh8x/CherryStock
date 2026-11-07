#!/usr/bin/env python3
"""
AWS SSO Login with auto-approve in browser.

Automates the SSO login flow by:
1. Starting `aws sso login --profile <profile>`
2. Capturing the authorization URL from output
3. Opening the URL in a headless browser (Playwright)
4. Automatically clicking "Allow" to approve the device authorization

Requirements:
    pip3 install playwright
    playwright install chromium

Usage:
    # Default: log into BOTH data-app-sit and data-app-prd
    python3 scripts/aws-login.py

    # Single profile
    python3 scripts/aws-login.py --profile data-app-prd

    # Multiple profiles (repeat --profile)
    python3 scripts/aws-login.py --profile data-app-sit --profile data-app-prd

    # Debug (show the browser)
    python3 scripts/aws-login.py --profile data-app-sit --headless false

    # Reuse a signed-in Chrome profile (skips SSO login when the session is live)
    python3 scripts/aws-login.py --chrome-profile "Profile 1"

    # Point at a non-default Chrome user-data dir
    python3 scripts/aws-login.py \\
        --chrome-user-data-dir "~/Library/Application Support/Google/Chrome" \\
        --chrome-profile "Default"

Notes on --chrome-profile:
    * Uses Playwright's persistent context so your existing Chrome login/cookies
      are reused — the corporate SSO step is skipped when the session is still
      valid, leaving only the device-authorization "Allow" pages to click.
    * Chrome LOCKS its user-data dir: close all running Chrome windows that use
      the same profile before running, otherwise Playwright cannot attach.
    * A persistent context is always a real (non-headless-friendly) Chrome; when
      --chrome-profile is set the browser is shown so you can see / intervene.
"""

import argparse
import os
import re
import subprocess
import sys
import threading
import time


def run_sso_login(profile: str) -> subprocess.Popen:
    """Start aws sso login process and return the Popen object."""
    proc = subprocess.Popen(
        ["aws", "sso", "login", "--profile", profile],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return proc


def capture_url_from_process(proc: subprocess.Popen, timeout: int = 15) -> str | None:
    """Read process output and extract the authorization URL."""
    url_pattern = re.compile(r"(https://[^\s]+)")
    start = time.time()
    lines = []

    while time.time() - start < timeout:
        line = proc.stdout.readline()
        if not line:
            if proc.poll() is not None:
                break
            time.sleep(0.1)
            continue
        lines.append(line.strip())
        print(f"  [aws] {line.strip()}", file=sys.stderr)

        match = url_pattern.search(line)
        if match:
            url = match.group(1)
            # AWS SSO outputs a verification URL like:
            # https://device.sso.ap-southeast-1.amazonaws.com/?user_code=XXXX-XXXX
            if "device.sso" in url or "awsapps.com" in url or "user_code" in url:
                return url

    return None


# Accessible NAMES of the buttons that advance the AWS SSO device-authorization
# flow, in the order the pages appear: "Confirm and continue" (code match) ->
# "Allow" (grant access). Matched case-insensitively via get_by_role, which —
# unlike CSS :has-text — pierces the Shadow DOM these pages are built with.
APPROVE_NAMES = [
    "Confirm and continue",
    "Allow",
    "Approve",
    "Confirm",
]

# JS fragment: find a clickable approve control anywhere on the page, INCLUDING
# inside open shadow roots (AWS renders these pages as web components, so plain
# CSS/:has-text often can't see the button). Returns true if it clicked one.
_JS_CLICK_APPROVE = """
(names) => {
  const wanted = names.map(s => s.toLowerCase());
  const out = [];
  const collect = (root) => {
    const els = root.querySelectorAll('button, input[type="submit"], a[role="button"], [role="button"]');
    for (const el of els) out.push(el);
    // descend into open shadow roots
    const all = root.querySelectorAll('*');
    for (const el of all) if (el.shadowRoot) collect(el.shadowRoot);
  };
  collect(document);
  for (const el of out) {
    const txt = ((el.innerText || el.textContent || el.value || '') + '').trim().toLowerCase();
    if (!txt) continue;
    if (wanted.some(w => txt === w || txt.includes(w))) {
      const r = el.getBoundingClientRect();
      if (r.width > 0 && r.height > 0) { el.click(); return txt; }
    }
  }
  return null;
}
"""

# JS fragment: list every visible button-like control (incl. shadow DOM) so we
# can log what the page actually exposes when auto-click fails.
_JS_LIST_BUTTONS = """
() => {
  const out = [];
  const collect = (root) => {
    const els = root.querySelectorAll('button, input[type="submit"], a[role="button"], [role="button"]');
    for (const el of els) {
      const txt = ((el.innerText || el.textContent || el.value || '') + '').trim();
      const r = el.getBoundingClientRect();
      if (txt && r.width > 0 && r.height > 0) out.push(txt);
    }
    const all = root.querySelectorAll('*');
    for (const el of all) if (el.shadowRoot) collect(el.shadowRoot);
  };
  collect(document);
  return out;
}
"""

# Text that signals the flow is finished — no more buttons to click.
DONE_MARKERS = ["Request approved", "You can close this window", "approved the request"]


def _list_visible_buttons(page) -> list[str]:
    """Return the text of every visible button-like control, incl. shadow DOM."""
    try:
        return page.evaluate(_JS_LIST_BUTTONS) or []
    except Exception:
        return []


def _click_one_approve(page) -> str | None:
    """Click the first visible approve control on the current page.

    Tries three strategies, in order of reliability on these AWS pages:
      1. get_by_role("button", name=...) — accessible name, pierces shadow DOM.
      2. A JS walk that clicks a matching control inside any open shadow root.
      3. Plain CSS :has-text (last resort, light DOM only).

    Returns a short description of what matched, or None if nothing clickable.
    """
    # 1) Accessible-role lookup (handles shadow DOM + locale-stable).
    for name in APPROVE_NAMES:
        try:
            btn = page.get_by_role("button", name=re.compile(re.escape(name), re.I)).first
            if btn.is_visible(timeout=800):
                btn.click()
                return f"role:{name}"
        except Exception:
            continue

    # 2) Shadow-DOM-aware JS click.
    try:
        clicked = page.evaluate(_JS_CLICK_APPROVE, APPROVE_NAMES)
        if clicked:
            return f"js:{clicked}"
    except Exception:
        pass

    # 3) Light-DOM CSS fallback.
    for name in APPROVE_NAMES:
        try:
            btn = page.locator(f'button:has-text("{name}")').first
            if btn.is_visible(timeout=400):
                btn.click()
                return f"css:{name}"
        except Exception:
            continue

    return None


def _flow_is_done(page) -> bool:
    """True once the 'Request approved' confirmation is on screen."""
    for marker in DONE_MARKERS:
        try:
            if page.get_by_text(marker, exact=False).first.is_visible(timeout=500):
                return True
        except Exception:
            continue
    # Fallback: scan full rendered text (covers shadow-DOM confirmation panels).
    try:
        body = (page.evaluate("() => document.body ? document.body.innerText : ''") or "").lower()
        if any(m.lower() in body for m in DONE_MARKERS):
            return True
    except Exception:
        pass
    return False


def _drive_approval_pages(page, headless: bool, max_steps: int = 6):
    """Walk the multi-page device-authorization flow, clicking each button.

    AWS SSO presents the approval across several pages in sequence. We click the
    visible approve button, let the next page render, and loop until the
    "Request approved" page shows or no more buttons appear.
    """
    for step in range(max_steps):
        if _flow_is_done(page):
            print("  [browser] Request approved. Flow complete.", file=sys.stderr)
            return True

        # Each page may still be rendering (incl. shadow-DOM web components).
        # Retry the click a few times before giving up on this page.
        matched = None
        for attempt in range(5):
            matched = _click_one_approve(page)
            if matched:
                break
            time.sleep(1.0)

        if matched:
            print(f"  [browser] Step {step + 1}: clicked [{matched}]", file=sys.stderr)
            # Let the click navigate / render the next page before re-checking.
            try:
                page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass
            time.sleep(1.5)
            continue

        # Nothing clickable found this page. Log what IS visible for diagnosis.
        buttons = _list_visible_buttons(page)
        print(
            f"  [browser] Step {step + 1}: no approve button matched. "
            f"Visible buttons: {buttons!r} | title: '{page.title()}'",
            file=sys.stderr,
        )
        time.sleep(1.5)
        if _flow_is_done(page):
            print("  [browser] Request approved. Flow complete.", file=sys.stderr)
            return True
        break

    if _flow_is_done(page):
        return True

    title = page.title()
    print(f"  [browser] Could not complete approval automatically. Page title: '{title}'", file=sys.stderr)
    print(f"  [browser] Visible buttons now: {_list_visible_buttons(page)!r}", file=sys.stderr)
    print("  [browser] You may need to approve manually in the browser.", file=sys.stderr)
    if not headless:
        print("  [browser] Waiting 30s for manual interaction...", file=sys.stderr)
        time.sleep(30)
    return False


def _launch_ephemeral(p, headless: bool):
    """
    Launch a throwaway Chromium-based browser (no profile reuse).

    Order of preference:
      1. Playwright's bundled Chromium (if `playwright install chromium` was run).
      2. The system Google Chrome via channel="chrome" (no download needed).

    Returns a Browser. Raises with a clear fix message if neither works.
    """
    # 1) bundled Chromium
    try:
        return p.chromium.launch(headless=headless)
    except Exception as exc_bundled:
        print(f"  [browser] Bundled Chromium unavailable: {exc_bundled}", file=sys.stderr)

    # 2) system Google Chrome
    try:
        print("  [browser] Falling back to system Google Chrome (channel=chrome)...", file=sys.stderr)
        return p.chromium.launch(headless=headless, channel="chrome")
    except Exception as exc_chrome:
        print("[ERROR] Could not launch a browser for Playwright.", file=sys.stderr)
        print(f"        bundled: see above | chrome: {exc_chrome}", file=sys.stderr)
        print(
            "[FIX] Install Playwright's Chromium once (with the TCB CA bundle for SSL inspection):",
            file=sys.stderr,
        )
        print(
            "        SSL_CERT_FILE=~/.aws/cacert.pem NODE_EXTRA_CA_CERTS=~/.aws/cacert.pem "
            "python3 -m playwright install chromium",
            file=sys.stderr,
        )
        print(
            "[NOTE] Meanwhile, approve the device authorization manually in a browser at the URL above.",
            file=sys.stderr,
        )
        raise


def _launch_persistent_chrome(p, headless: bool, user_data_dir: str, profile_dir: str):
    """
    Launch system Google Chrome reusing an existing profile (persistent context).

    This reuses the cookies / signed-in session of the given Chrome profile, so
    the corporate SSO step is skipped when the session is still valid.

    Returns the BrowserContext (persistent contexts have no separate Browser).
    Raises with guidance if Chrome's profile dir is locked or Chrome is missing.
    """
    user_data_dir = os.path.expanduser(user_data_dir)
    args = [f"--profile-directory={profile_dir}"]
    try:
        return p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            channel="chrome",
            headless=headless,
            args=args,
        )
    except Exception as exc:
        print("[ERROR] Could not open Chrome with the requested profile.", file=sys.stderr)
        print(f"        user_data_dir={user_data_dir!r} profile={profile_dir!r}: {exc}", file=sys.stderr)
        print(
            "[FIX] Close ALL running Chrome windows using this profile first — Chrome "
            "locks its user-data dir and Playwright cannot attach while it is open.",
            file=sys.stderr,
        )
        raise


def auto_approve_browser(
    url: str,
    headless: bool = True,
    timeout: int = 30,
    chrome_user_data_dir: str | None = None,
    chrome_profile: str | None = None,
):
    """Open the URL in Playwright and walk the Allow/Confirm pages in order.

    When chrome_profile is given, reuse that signed-in Chrome profile via a
    persistent context (SSO login is skipped if the session is still valid).
    Otherwise launch a throwaway browser.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[ERROR] playwright not installed. Run:", file=sys.stderr)
        print("  pip3 install playwright && playwright install chromium", file=sys.stderr)
        sys.exit(1)

    use_profile = bool(chrome_profile)
    # A persistent (profile) context must be visible; headless profile reuse is
    # unreliable on macOS Chrome. Force headful whenever a profile is requested.
    effective_headless = headless and not use_profile

    print(f"  [browser] Opening URL: {url}", file=sys.stderr)
    if use_profile:
        print(
            f"  [browser] Reusing Chrome profile: {chrome_profile!r} "
            f"(user-data-dir: {chrome_user_data_dir!r}, headless forced off)",
            file=sys.stderr,
        )
    else:
        print(f"  [browser] Headless: {effective_headless}", file=sys.stderr)

    with sync_playwright() as p:
        browser = None  # ephemeral Browser (closed explicitly); None for persistent
        if use_profile:
            context = _launch_persistent_chrome(
                p, effective_headless, chrome_user_data_dir, chrome_profile
            )
            # Persistent context opens with one page already; reuse it.
            page = context.pages[0] if context.pages else context.new_page()
        else:
            browser = _launch_ephemeral(p, effective_headless)
            context = browser.new_context()
            page = context.new_page()

        try:
            # domcontentloaded is more reliable than networkidle here: the AWS
            # SSO pages keep background connections open, so networkidle can time
            # out and skip the approval entirely. A goto failure must NOT abort
            # the approval walk — the page often renders anyway.
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
            except Exception as nav_exc:
                print(f"  [browser] goto warning (continuing): {nav_exc}", file=sys.stderr)
            time.sleep(2)
            _drive_approval_pages(page, effective_headless)
        except Exception as e:
            print(f"  [browser] Error: {e}", file=sys.stderr)
            if not effective_headless:
                print("  [browser] Waiting 30s for manual interaction...", file=sys.stderr)
                time.sleep(30)
        finally:
            if browser is not None:
                browser.close()
            else:
                context.close()


# Default profiles to log in when none is given on the command line.
DEFAULT_PROFILES = ["data-app-sit", "data-app-prd"]

# Default Chrome user-data dir on macOS (holds the per-profile subfolders like
# "Default", "Profile 1"). Used only when --chrome-profile is set.
DEFAULT_CHROME_USER_DATA_DIR = os.path.expanduser(
    "~/Library/Application Support/Google/Chrome"
)


def login_profile(
    profile: str,
    headless: bool,
    timeout: int,
    chrome_user_data_dir: str | None = None,
    chrome_profile: str | None = None,
) -> bool:
    """
    Run the full SSO login flow for a single profile.

    Returns True on success (aws sso login exit 0 or browser approval likely
    succeeded), False if the authorization URL could not be captured.
    """
    print(f"\n[INFO] Starting AWS SSO login for profile: {profile}", file=sys.stderr)

    # Start the SSO login process
    proc = run_sso_login(profile)

    # Capture the authorization URL from its output
    url = capture_url_from_process(proc, timeout=15)

    if not url:
        print("[ERROR] Could not capture authorization URL from aws sso login output.", file=sys.stderr)
        print(f"[ERROR] Make sure profile '{profile}' is configured in ~/.aws/config", file=sys.stderr)
        proc.terminate()
        return False

    # Auto-approve in browser. If the browser can't start (e.g. Chromium not
    # installed), don't abort the whole run — the SSO CLI is still waiting, so
    # the user can approve manually, and other profiles can still proceed.
    auto_ok = True
    try:
        auto_approve_browser(
            url,
            headless=headless,
            timeout=timeout,
            chrome_user_data_dir=chrome_user_data_dir,
            chrome_profile=chrome_profile,
        )
    except Exception as exc:  # noqa: BLE001 — degrade gracefully per profile
        auto_ok = False
        print(
            f"[WARN] Auto-approve failed for '{profile}': {exc}. "
            "Approve manually in a browser at the URL above.",
            file=sys.stderr,
        )

    # Wait for the aws sso login process to complete
    if auto_ok:
        print("  [aws] Waiting for SSO login to complete...", file=sys.stderr)
    else:
        print("  [aws] Waiting up to 90s for MANUAL approval...", file=sys.stderr)

    # Read remaining output
    def drain_output():
        for line in proc.stdout:
            print(f"  [aws] {line.strip()}", file=sys.stderr)

    drain_thread = threading.Thread(target=drain_output, daemon=True)
    drain_thread.start()

    wait_secs = 5
    try:
        proc.wait(timeout=wait_secs)
    except subprocess.TimeoutExpired:
        print("[WARN] aws sso login process timed out. It may still be waiting.", file=sys.stderr)
        proc.terminate()

    if proc.returncode == 0:
        print(f"[OK] SSO login successful for profile: {profile}", file=sys.stderr)
        return True

    print(f"[WARN] aws sso login exited with code {proc.returncode} for profile: {profile}", file=sys.stderr)
    print("[WARN] Login may have succeeded if browser approval worked. Verify with an AWS command.", file=sys.stderr)
    # Treat as success: the device approval often completes even when the CLI
    # reports a non-zero exit in this corporate SSO flow.
    return True


def main():
    parser = argparse.ArgumentParser(
        description="AWS SSO login with auto-approve in browser. "
        "Logs into one or more profiles (default: data-app-sit + data-app-prd)."
    )
    parser.add_argument(
        "--profile",
        action="append",
        metavar="NAME",
        help="AWS profile name. Repeat for multiple profiles "
        "(e.g. --profile data-app-sit --profile data-app-prd). "
        "If omitted, logs into both default profiles.",
    )
    parser.add_argument(
        "--headless",
        default="true",
        choices=["true", "false"],
        help="Run browser in headless mode (default: true). Use 'false' for debugging.",
    )
    parser.add_argument("--timeout", type=int, default=30, help="Timeout in seconds for browser operations")
    parser.add_argument(
        "--chrome-profile",
        metavar="DIR",
        default=None,
        help="Reuse an existing Chrome profile DIRECTORY NAME (e.g. 'Default', "
        "'Profile 1') via a persistent context, so a live SSO session skips the "
        "login step. Forces the browser to be visible. Close running Chrome on "
        "that profile first (Chrome locks its data dir).",
    )
    parser.add_argument(
        "--chrome-user-data-dir",
        metavar="PATH",
        default=DEFAULT_CHROME_USER_DATA_DIR,
        help="Chrome user-data dir holding the profile (default: the macOS Chrome "
        f"location: {DEFAULT_CHROME_USER_DATA_DIR}). Only used with --chrome-profile.",
    )
    args = parser.parse_args()

    headless = args.headless == "true"
    profiles = args.profile if args.profile else list(DEFAULT_PROFILES)

    print(f"[INFO] Profiles to log in: {', '.join(profiles)}", file=sys.stderr)
    if args.chrome_profile and len(profiles) > 1:
        print(
            "[NOTE] Reusing a single Chrome profile for multiple AWS profiles in "
            "sequence. Each run closes the browser before the next starts.",
            file=sys.stderr,
        )

    results: dict[str, bool] = {}
    for profile in profiles:
        results[profile] = login_profile(
            profile,
            headless,
            args.timeout,
            chrome_user_data_dir=args.chrome_user_data_dir,
            chrome_profile=args.chrome_profile,
        )

    # Summary
    print("\n[SUMMARY] AWS SSO login results:", file=sys.stderr)
    for profile in profiles:
        status = "OK" if results[profile] else "FAILED"
        print(f"  - {profile}: {status}", file=sys.stderr)

    # Non-zero exit if any profile could not even start the flow.
    if not all(results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
