"""
batch_address_automation_excel.py
Batch GUI automation for many addresses read from an Excel file.

Requirements:
  pip install pyautogui opencv-python pillow numpy pyperclip pandas openpyxl

Usage:
  1. Place templates in ./templates:
       - input_field.png
       - submit_button.png
       - success_indicator.png   (optional)
  2. Put addresses.xlsx in same folder (must have a column 'address').
  3. Open the browser tab manually (active session, cookies preserved).
  4. Run: python batch_address_automation_excel.py
"""

import os, time, random, sys, csv
import pyautogui as pag
import pyperclip
import pandas as pd

# ---------- CONFIGURATION ----------
TEMPLATES = {
    "field": "templates/input_field.png",
    "submit": "templates/submit_button.png",
    "success": "templates/success_indicator.png"  # optional
}
INPUT_EXCEL = "addresses.xlsx"  # Excel file
OUT_LOG = "automation_log.csv"
FAILED_DIR = "failed_screens"
CONFIDENCE = 0.80
MAX_RETRIES = 5
PER_RUN_LIMIT = None  # Set integer to limit per run

# Timing & realism settings
MIN_DELAY = 0.6
MAX_DELAY = 1.2
INTER_ITEM_DELAY = (3.0, 7.0)
SLOW_TYPING = True  # if True, type char by char, else paste

pag.FAILSAFE = True  # move mouse to top-left to abort
os.makedirs(FAILED_DIR, exist_ok=True)

# ---------- HELPER FUNCTIONS ----------

def human_sleep(a=MIN_DELAY, b=MAX_DELAY):
    time.sleep(random.uniform(a, b))

def human_move_and_click(x, y, dur=0.4):
    dur = dur * random.uniform(0.9, 1.4)
    pag.moveTo(x + random.randint(-3,3), y + random.randint(-3,3),
               duration=dur, tween=pag.easeOutQuad)
    human_sleep(0.05, 0.18)
    pag.click()
    human_sleep(0.08, 0.25)

def find_template(name, timeout=10):
    path = TEMPLATES[name]
    start = time.time()
    while time.time() - start < timeout:
        try:
            loc = pag.locateCenterOnScreen(path, confidence=CONFIDENCE)
        except Exception:
            loc = None
        if loc:
            return loc
        time.sleep(0.5)
    return None

def save_failure_screenshot(index, address):
    fname = f"{FAILED_DIR}/failure_{index}.png"
    pag.screenshot(fname)
    return fname

def type_or_paste(text):
    """Type slowly or paste (clipboard restored after)."""
    try:
        old_clip = pyperclip.paste()
    except Exception:
        old_clip = None
    try:
        if SLOW_TYPING and len(text) < 180:
            for ch in text:
                pag.typewrite(ch, interval=random.uniform(0.02, 0.09))
        else:
            pyperclip.copy(text)
            time.sleep(0.12)
            if os.name == "nt":
                pag.hotkey("ctrl", "v")
            else:
                pag.hotkey("command", "v")
        time.sleep(0.15)
    finally:
        try:
            if old_clip is not None:
                pyperclip.copy(old_clip)
        except Exception:
            pass

def process_row(index, address):
    """Process one address. Returns (success, note)."""
    try:
        # 1️⃣ Find and click input field
        loc = find_template("field", timeout=10)
        if not loc:
            return False, "input_field_not_found"
        human_move_and_click(loc.x, loc.y, dur=0.45)

        # Clear existing text
        if os.name == "nt":
            pag.hotkey("ctrl", "a")
        else:
            pag.hotkey("command", "a")
        human_sleep(0.08, 0.18)
        pag.press("backspace")

        # Type or paste address
        type_or_paste(address)
        human_sleep(0.4, 0.9)

        # 2️⃣ Submit
        loc2 = find_template("submit", timeout=6)
        if loc2:
            human_move_and_click(loc2.x, loc2.y, dur=0.38)
        else:
            pag.press("enter")

        # 3️⃣ Optional success check
        if os.path.exists(TEMPLATES["success"]):
            ok = find_template("success", timeout=12)
            if ok:
                return True, "ok"
            else:
                fname = save_failure_screenshot(index, address)
                return False, f"no_success_indicator (screenshot:{fname})"
        else:
            human_sleep(1.0, 2.0)
            return True, "ok_no_success_check"

    except Exception as e:
        fname = save_failure_screenshot(index, address)
        return False, f"exception:{str(e)} (screenshot:{fname})"

def load_addresses():
    if not os.path.exists(INPUT_EXCEL):
        print(f"❌ Excel file not found: {INPUT_EXCEL}")
        sys.exit(1)
    df = pd.read_excel(INPUT_EXCEL)
    cols = [c.lower().strip() for c in df.columns]
    if "address" not in cols:
        print("❌ Excel must have a column named 'address'")
        sys.exit(1)
    df.columns = cols
    addresses = df["address"].dropna().astype(str).tolist()
    return addresses

def write_log_line(row_idx, address, status, note):
    header_needed = not os.path.exists(OUT_LOG)
    with open(OUT_LOG, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if header_needed:
            w.writerow(["index","address","timestamp","status","note"])
        w.writerow([row_idx, address, time.strftime("%Y-%m-%d %H:%M:%S"), status, note])

# ---------- MAIN ----------
def main():
    addresses = load_addresses()
    total = len(addresses)
    print(f"📋 Loaded {total} addresses from {INPUT_EXCEL}")

    start_index = 0
    if os.path.exists(OUT_LOG):
        try:
            prev = pd.read_csv(OUT_LOG)
            if not prev.empty:
                start_index = int(prev["index"].iloc[-1]) + 1
        except Exception:
            start_index = 0

    print(f"▶️ Starting from index {start_index}")
    print("Please ensure your browser tab with session is active (do NOT minimize it).")
    time.sleep(3)

    processed = 0
    for idx in range(start_index, total):
        if PER_RUN_LIMIT and processed >= PER_RUN_LIMIT:
            print("Per-run limit reached. Stopping.")
            break
        address = addresses[idx].strip()
        if not address:
            write_log_line(idx, address, "skipped", "empty_address")
            continue
        print(f"[{idx}/{total-1}] → Processing: {address[:60]}...")
        human_sleep(1.0, 2.0)
        success, note = process_row(idx, address)
        write_log_line(idx, address, "success" if success else "failed", note)
        print("  ✅ success" if success else f"  ❌ failed: {note}")
        time.sleep(random.uniform(*INTER_ITEM_DELAY))
        processed += 1

    print(f"\n🏁 Finished. Results logged in: {OUT_LOG}")

if __name__ == "__main__":
    main()
