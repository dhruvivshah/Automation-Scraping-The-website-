import os
import json
import time
import random
import itertools
from typing import Optional, List, Dict

import tkinter as tk
from tkinter import simpledialog

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# CONFIG
TARGET_URL = "https://www.doordash.com/home"

# PROXIES = ["http://user:pass@1.2.3.4:8000", "http://5.6.7.8:8080"]
# Leave empty to run without proxy rotation.
PROXIES: List[Optional[str]] = [
    # "http://username:password@proxy1.example.com:8000",
    # "http://proxy2.example.com:8080",
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
]

COOKIES_FILE = "cookies.json"
HTML_DUMP = "scraped_page.html"
NAV_TIMEOUT_MS = 45000

# Utilities: cookies
def save_cookies(cookies: List[Dict], filename: str = COOKIES_FILE):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(cookies, f, indent=2)
        print(f" Saved {len(cookies)} cookies to {filename}")
    except Exception as e:
        print(f" Could not save cookies: {e}")

def load_cookies(filename: str = COOKIES_FILE) -> Optional[List[Dict]]:
    if not os.path.exists(filename):
        return None
    try:
        with open(filename, "r", encoding="utf-8") as f:
            cookies = json.load(f)
        print(f" Loaded {len(cookies)} cookies from {filename}")
        return cookies
    except Exception as e:
        print(f" Could not load cookies: {e}")
        return None

# -----------------------------
# Small GUI to accept address (optional)
# -----------------------------
def ask_user_for_address(prompt: str = "Please update the address for search (optional):") -> Optional[str]:
    root = tk.Tk()
    root.withdraw()
    val = simpledialog.askstring(title="Address (optional)", prompt=prompt)
    root.destroy()
    return val

# Human verification detection heuristics
def detect_human_verification(page) -> bool:
    """
    Return True if common captcha/verification elements are detected.
    Heuristics: scan for iframes with recaptcha/hcaptcha, elements/classes containing 'captcha' or 'turnstile',
    or clear textual prompts like 'verify you are human'.
    """
    try:
        # Check for iframes that often host captchas
        iframe_selectors = [
            'iframe[src*="recaptcha"]',
            'iframe[src*="hcaptcha"]',
            'iframe[src*="turnstile"]',
            'iframe[src*="captcha"]',
        ]
        for sel in iframe_selectors:
            el = page.query_selector(sel)
            if el:
                print(f" Detected captcha iframe by selector {sel}")
                return True

        # Generic checks for elements that include 'captcha' or 'turnstile' in class or id
        generic_selectors = [
            '[class*="captcha"]',
            '[id*="captcha"]',
            '[class*="turnstile"]',
            '[id*="turnstile"]',
            '[class*="h-captcha"]',
            '[id*="h-captcha"]',
        ]
        for sel in generic_selectors:
            el = page.query_selector(sel)
            if el:
                print(f" Detected captcha element by selector {sel}")
                return True

        # Look for textual prompts
        body_text = page.inner_text("body", timeout=2000).lower() if page.query_selector("body") else ""
        heuristics = ["verify you are human", "please verify", "are you human", "complete the security check", "please complete the security check"]
        for phrase in heuristics:
            if phrase in body_text:
                print(f" Detected verification text: '{phrase}'")
                return True

        # No obvious verification found
        return False
    except Exception as e:
        print(f" Error during verification detection: {e}")
        # Be conservative: if detection throws, assume possible verification
        return True

# Simple parse and save

def parse_and_save_html(html: str, filename: str = HTML_DUMP):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html)
        print(f" Saved HTML to {filename}")
    except Exception as e:
        print(f" Failed to save HTML: {e}")

    # Example parse (title + snippet)
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else "No title"
    snippet = soup.get_text(separator=" ", strip=True)[:800]
    print(f" Page title: {title}")
    print(f" Snippet (first 300 chars):\n{snippet[:300]}")


# Core: launch visible browser with proxy + optional cookies

def run_one_session(url: str,
                    proxy: Optional[str],
                    user_agent: str,
                    cookies_to_restore: Optional[List[Dict]],
                    allow_manual_solve: bool = True) -> Optional[str]:
    """
    Launch visible Chromium with provided proxy and cookies, navigate, detect verification.
    If verification found and allow_manual_solve True, pause and let user solve in browser.
    Returns page HTML if successful (no verification after optional manual solve), else None.
    """
    with sync_playwright() as p:
        launch_args = {"headless": False}
        if proxy:
            launch_args["proxy"] = {"server": proxy}
            print(f" Launching Chromium with proxy: {proxy}")

        browser = p.chromium.launch(**launch_args)
        try:
            context = browser.new_context(user_agent=user_agent, viewport={"width": 1280, "height": 800})

            # Attempt to add cookies if provided
            if cookies_to_restore:
                try:
                    # If cookies were saved from a previous Playwright session they should be compatible
                    print(" Injecting saved cookies into the browser context...")
                    context.add_cookies(cookies_to_restore)
                except Exception as e:
                    print(f" Could not add cookies: {e}")

            page = context.new_page()
            page.set_default_navigation_timeout(NAV_TIMEOUT_MS)

            try:
                page.goto(url, wait_until="networkidle")
            except PlaywrightTimeoutError:
                print(" Navigation timeout; falling back to domcontentloaded.")
                page.goto(url, wait_until="domcontentloaded")

            # Short pause
            time.sleep(random.uniform(1.0, 2.5))

            # Detect verification
            is_verif = detect_human_verification(page)
            if is_verif:
                print(" Human verification detected on the page.")

                if allow_manual_solve:
                    print(" Please solve the verification in the opened browser window.")
                    print("When done, come back to this console and press ENTER to continue (or type 'skip' to skip this proxy).")
                    resp = input("Press ENTER when verification is solved (or type 'skip' then ENTER to skip): ").strip().lower()
                    if resp == "skip":
                        print("⏭ Skipping this proxy attempt.")
                        # close browser and try next proxy
                        try:
                            context.close()
                            browser.close()
                        except Exception:
                            pass
                        return None
                    # user pressed enter to continue — re-check
                    time.sleep(1.0)
                    # re-evaluate verification
                    is_verif = detect_human_verification(page)
                    if is_verif:
                        print(" Verification still detected after manual solve attempt.")
                        try:
                            context.close()
                            browser.close()
                        except Exception:
                            pass
                        return None
                    else:
                        print(" Verification cleared after manual solve.")
                else:
                    print("Skipping proxy because manual solving is not allowed.")
                    try:
                        context.close()
                        browser.close()
                    except Exception:
                        pass
                    return None

            # At this point, no verification is present
            html = page.content()

            # Save cookies from this verified session
            try:
                saved_cookies = context.cookies()
                if saved_cookies:
                    save_cookies(saved_cookies, COOKIES_FILE)
                else:
                    print(" No cookies were returned from the session.")
            except Exception as e:
                print(f" Could not extract cookies: {e}")

            # Clean up
            context.close()
            browser.close()

            return html

        finally:
            # ensure browser closed on exception
            try:
                browser.close()
            except Exception:
                pass


# High-level flow: rotate proxies until success

def main():
    print("▶ Starting proxy-rotation + cookie-restore flow.")

    # Optional: ask for address (used only by you; you can manually type it into the opened browser)
    addr = ask_user_for_address()
    if addr:
        print(f" Address provided (you can paste/type it into the page): {addr}")
    else:
        print(" No address provided.")

    # Load saved cookies if present and ask user if they want to reuse
    saved_cookies = load_cookies(COOKIES_FILE)
    cookies_to_restore = None
    if saved_cookies:
        ans = input("Found saved cookies. Reuse them? (y/N): ").strip().lower()
        if ans == "y":
            cookies_to_restore = saved_cookies
            print(" Will try reusing saved cookies for each proxy session.")
        else:
            print(" Not reusing saved cookies (will attempt fresh session).")

    # Build proxy sequence; ensure at least one attempt without proxy if PROXIES empty
    proxies_list = PROXIES if PROXIES else [None]
    proxy_cycle = itertools.cycle(proxies_list)
    attempts = 0
    max_attempts = len(proxies_list)

    last_error = None
    for _ in range(max_attempts):
        proxy = next(proxy_cycle)
        attempts += 1
        print(f"\n--- Attempt {attempts}/{max_attempts}  (proxy={proxy}) ---")
        ua = random.choice(USER_AGENTS)
        try:
            html = run_one_session(TARGET_URL, proxy, ua, cookies_to_restore, allow_manual_solve=True)
            if html:
                print(" Successfully loaded page without verification blocking.")
                parse_and_save_html(html, HTML_DUMP)
                return
            else:
                print(" Session did not produce usable HTML (verification unsolved or skipped). Trying next proxy.")
        except Exception as e:
            last_error = e
            print(f" Exception during attempt with proxy {proxy}: {e}")

    print(" All attempts exhausted.")
    if last_error:
        print("Last exception:", last_error)

if __name__ == "__main__":
    main()
