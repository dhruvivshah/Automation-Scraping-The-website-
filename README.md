# Automation-Scraping-The-website-
Scraping the data from the existing website. 

# DoorDash Store Scraper 

## Overview

This script integrates **Tkinter** for interactive address input dialogs and **Playwright** for browser automation to scrape store URLs from DoorDash using a single login session.

It opens a Chromium browser, allows the user to manually authenticate and set an address, and then automates scraping actions. The user can update addresses repeatedly using a popup window.

---

## Features

✅ Login manually once — session persists for scraping

✅ Tkinter popup for changing store addresses easily

✅ Automated double‑click navigation on store cards

✅ Repeated scraping without re‑authentication

✅ Works with visible browser (`headless=False`) for easier debugging

---

## Requirements

Install required dependencies:

```bash
pip install playwright
pip install tkinter  # usually comes preinstalled on Windows/Linux
playwright install
```

---

## How It Works

1. Launches a Chromium browser
2. Opens DoorDash homepage in a visible window
3. User logs in manually
4. Script automates scraping of store URLs
5. Tkinter dialogs allow repeated address updates
6. Script navigates to new address locator pages and repeats scraping

---

## Script Structure

* `AddressDialog`: Tkinter popup for entering addresses
* `ask_for_new_address()`: Handles dialog lifecycle
* `scrape_store_with_playwright()`: Initializes scraping task
* `scrape_store_urls()`: Collects store URLs by opening each tile
* `Main Script`: Controls session flow and address loop

---

## Example Workflow

1. Run script
2. Log into DoorDash when prompted
3. Press **Enter** in console to continue
4. Scraping begins
5. Address dialog appears
6. Enter a new address and press OK
7. Scraping continues for next location
8. Choose whether to continue or exit

---

## Important Notes

> ⚠️ This script **requires user interaction**.
>
> * You must complete login manually
> * Some pages or regions may require CAPTCHA or extra checks

---

## Customization Options

You may want to modify:

* `card_selector` CSS selector if DoorDash UI changes
* URL format for new address navigation

---

## Disclaimer

This script is intended for **educational and personal automation only**. Respect DoorDash’s **Terms of Service**, robots.txt rules, and rate limits.

---

## License

Free for personal use and modification.
