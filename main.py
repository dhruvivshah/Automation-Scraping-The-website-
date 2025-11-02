import os
import re
import time
import subprocess
import pyautogui
import pyperclip
import pandas as pd
from playwright.sync_api import sync_playwright

# SETTINGS
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.6
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
DOORDASH_URL = "https://www.doordash.com/"
CHROME_PROFILE = r"C:\Users\Dhruvi\AppData\Local\Google\Chrome\User Data"
CHROME_PROFILE_NAME = "Default"  # change if you use Profile 1, etc.
OUTPUT_FILE = "flowers_div_links.xlsx"

# HELPERS

def wait(sec): time.sleep(sec)

def type_text_clipboard(text):
    pyperclip.copy(text)
    pyautogui.hotkey("ctrl", "v")

def click_image(image_name, confidence=0.8, timeout=10):
    print(f" Searching {image_name} (timeout={timeout}s)...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            region = pyautogui.locateOnScreen(image_name, confidence=confidence)
        except Exception:
            region = None
        if region:
            x, y = pyautogui.center(region)
            pyautogui.moveTo(x, y, duration=0.4)
            pyautogui.click()
            print(f" Clicked {image_name}")
            return True
        wait(0.5)
    print(f" {image_name} not found.")
    return False

def wait_for_image(image_name, confidence=0.8, timeout=15):
    start = time.time()
    while time.time() - start < timeout:
        try:
            if pyautogui.locateOnScreen(image_name, confidence=confidence):
                return True
        except Exception:
            pass
        wait(0.5)
    return False

def wait_until_gone(image_name, confidence=0.8, timeout=15):
    start = time.time()
    while time.time() - start < timeout:
        try:
            region = pyautogui.locateOnScreen(image_name, confidence=confidence)
        except Exception:
            region = None
        if not region:
            return True
        wait(0.5)
    return False

# ---------------------------
# READ ADDRESSES
# ---------------------------
def read_addresses():
    print("📂 Enter Excel file path (.xlsx) or Google Sheet link:")
    src = input("👉 ").strip()
    if not src:
        raise ValueError("No file or link provided.")
    if "docs.google.com" in src:
        m = re.search(r"/d/([A-Za-z0-9\-_]+)", src)
        if not m:
            raise ValueError("Invalid Google Sheet link.")
        sheet_id = m.group(1)
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
        df = pd.read_excel(url)
    else:
        if not os.path.exists(src):
            raise FileNotFoundError("Excel file not found.")
        df = pd.read_excel(src)
    if "Store Address" not in df.columns:
        raise ValueError("Missing 'Store Address' column.")
    addresses = [str(v).strip() for v in df["Store Address"].dropna()]
    print(f"✅ Loaded {len(addresses)} addresses.")
    return addresses

# ---------------------------
# OPEN DOORDASH
# ---------------------------
def open_doordash():
    print("🧭 Opening DoorDash with your saved Chrome session...")
    subprocess.Popen([
        CHROME_PATH,
        "--remote-debugging-port=9222",
        f"--user-data-dir={CHROME_PROFILE}",
        f"--profile-directory={CHROME_PROFILE_NAME}",
        "--new-window",
        DOORDASH_URL
    ])
    wait(8)
    try:
        pyautogui.hotkey("alt", "tab")
        wait(0.6)
        pyautogui.hotkey("win", "up")
    except Exception:
        pass
    print("✅ DoorDash window ready (session preserved).")

# ADDRESS FLOW
def select_first_suggestion():
    wait(1.2)
    pyautogui.press("down")
    wait(0.25)
    pyautogui.press("enter")

def handle_next_and_save():
    if click_image("next_button.png", confidence=0.85, timeout=5):
        wait(1.5)
    if click_image("save_button.png", confidence=0.85, timeout=6):
        wait_until_gone("dialog_search.png", confidence=0.8, timeout=15)
    else:
        wait_until_gone("dialog_search.png", confidence=0.8, timeout=8)

def change_location(address):
    print(f" Changing location to: {address}")
    for attempt in range(3):
        if click_image("address_box.png", confidence=0.7, timeout=10):
            wait(1)
            pyautogui.click()
            if wait_for_image("dialog_search.png", confidence=0.75, timeout=10):
                click_image("dialog_search.png", confidence=0.7, timeout=3)
                type_text_clipboard(address)
                wait(1)
                select_first_suggestion()
                wait(1.5)
                handle_next_and_save()
                print("✅ Address changed successfully.")
                return True
        wait(2)
    print(" Could not change address.")
    return False

# FLOWERS PAGE LOGIC
# ---------------------------
def click_browse_all_and_flowers():
    print(" Navigating to Flowers category...")
    if click_image("browse_all.png", confidence=0.8, timeout=10):
        wait(2)
        if click_image("flowers_btn.png", confidence=0.8, timeout=10):
            print(" Clicked Flowers successfully!")
            wait(5)
            scroll_and_click_arrows("arrow.png", confidence=0.8)
        else:
            print(" flowers_btn.png not found.")
    else:
        print("browse_all.png not found.")
    wait(2)
-
# SCROLL + CLICK ARROWS
# ---------------------------
def scroll_and_click_arrows(arrow_image="arrow.png", confidence=0.8, scroll_pause=1.2):
    print("\n Scrolling Flowers page and clicking arrows...")
    arrows_clicked = 0
    not_found = 0

    while True:
        try:
            region = pyautogui.locateOnScreen(arrow_image, confidence=confidence)
        except Exception:
            region = None

        if region:
            x, y = pyautogui.center(region)
            pyautogui.moveTo(x, y, duration=0.4)
            pyautogui.click()
            arrows_clicked += 1
            print(f" Clicked arrow #{arrows_clicked}")
            not_found = 0
            wait(1.0)
        else:
            not_found += 1
            pyautogui.scroll(-700)
            wait(scroll_pause)
            if not_found > 5:
                print(" No more arrows visible. Doing final deep scrolls...")
                for _ in range(4):
                    pyautogui.scroll(-900)
                    wait(1.0)
                print(f" Finished all arrows ({arrows_clicked} clicked).")
                break
    print(" Finished clicking and scrolling.\n")


# SCRAPE LINKS (Playwright)
# --------------------------
def scrape_raw_links():
    print(" Connecting to existing Chrome to scrape links...")
    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
        except Exception as e:
            print(f" Playwright connection failed: {e}")
            return
        context = browser.contexts[0]
        page = context.pages[0]
        print(f" Connected | URL: {page.url}")
        time.sleep(3)
        selector = 'div.sc-eqUAAy.hZncWr a'
        elements = page.query_selector_all(selector)
        print(f"🔍 Found {len(elements)} links in div.sc-eqUAAy.hZncWr")
        links = []
        for i, el in enumerate(elements, start=1):
            href = el.get_attribute("href")
            if href:
                links.append({"Link": href})
                print(f" [{i}] {href}")
        if links:
            df = pd.DataFrame(links)
            df.to_excel(OUTPUT_FILE, index=False)
            print(f"\n Saved {len(df)} links to {OUTPUT_FILE}")
        else:
            print(" No links found.")
        browser.close()
        print(" Scraping done.")

# ---------------------------
# MAIN
# ---------------------------
def main():
    try:
        addresses = read_addresses()
    except Exception as e:
        print(f" Address file error: {e}")
        return

    open_doordash()
    print("\n Starting automation...\n")

    for i, addr in enumerate(addresses, start=1):
        print(f" [{i}/{len(addresses)}] {addr}")
        if change_location(addr):
            click_browse_all_and_flowers()
        else:
            print(f" Skipped address {addr}")

    scrape_raw_links()
    print("\n Completed all tasks successfully!")

# ---------------------------
# RUN
# ---------------------------
if __name__ == "__main__":
    try:
        main()
    except pyautogui.FailSafeException:
        print(" Manually stopped.")
    except Exception as ex:
        print(f"Unexpected error: {ex}")

