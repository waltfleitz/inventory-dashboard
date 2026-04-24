# ==========================================
# SNAPSHOT INVENTORY ENGINE — FORD (RESUMABLE + SAFE)
# ==========================================

import csv
import logging
import re
import json
import base64
from datetime import datetime
from pathlib import Path
from collections import defaultdict

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

BASE_DIR = Path(__file__).resolve().parent
JSON_FILE = BASE_DIR / "ford_dealers_master.json"

PROGRESS_FILE = BASE_DIR / "progress_ford.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger()

TEST_MODE = False
TEST_DEALERS = None
TEST_MAX_PAGES = 999


# ---------------- LOAD ----------------

def load_dealers():
    with open(JSON_FILE, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def load_progress():
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, "r") as f:
            return json.load(f)
    return {"last_index": 0}


def save_progress(index):
    with open(PROGRESS_FILE, "w") as f:
        json.dump({"last_index": index}, f)


# ---------------- SAVE ----------------

def append_csv(path, rows):
    if not rows:
        return

    file_exists = path.exists()
    keys = sorted({k for r in rows for k in r.keys()})

    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)

        if not file_exists:
            writer.writeheader()

        writer.writerows(rows)


# ---------------- HELPERS ----------------

def is_valid_vin(v):
    return v and len(v) == 17


def calc_age_days(date_str):
    try:
        dt = datetime.strptime(date_str, "%Y/%m/%d")
        return (datetime.now() - dt).days
    except:
        return 0


# ---------------- EXTRACTION ----------------

def extract(html, brand, selector, dealer_name, bac):

    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select(selector)

    out = []

    for c in cards:

        vin = (c.get("data-vin") or "").strip().upper()
        if not is_valid_vin(vin):
            continue

        model = (c.get("data-model") or "").strip()
        trim = (c.get("data-trim") or "").strip().upper()
        text = " ".join(c.stripped_strings).upper()

        inventory_date = c.get("data-dotagging-item-inventory-date")
        age_days = calc_age_days(inventory_date)

        selling_price = None
        msrp = None

        pricelib = c.get("data-pricelib")

        if pricelib:
            try:
                decoded = base64.b64decode(pricelib).decode()
                pricing = json.loads(decoded)
                selling_price = pricing.get("price") or pricing.get("internet_price")
                msrp = pricing.get("msrp")
            except:
                pass

        m = re.search(r"MSRP[^$]*\$([\d,]+)", text)
        p = re.search(r"(PRICE|NOW)[^$]*\$([\d,]+)", text)

        if not msrp and m:
            msrp = float(m.group(1).replace(",", ""))
        if not selling_price and p:
            selling_price = float(p.group(2).replace(",", ""))

        try:
            selling_price = float(selling_price) if selling_price else None
            msrp = float(msrp) if msrp else None
        except:
            selling_price = None
            msrp = None

        dealer_discount = (msrp - selling_price) if msrp and selling_price else 0

        drivetrain = None
        if "4WD" in text or "4X4" in text:
            drivetrain = "4WD"
        elif "AWD" in text:
            drivetrain = "AWD"
        elif "FWD" in text:
            drivetrain = "FWD"
        elif "RWD" in text:
            drivetrain = "RWD"

        out.append({
            "vin": vin,
            "dealer": dealer_name,
            "bac": bac,
            "brand": brand,
            "model": model,
            "trim": trim,
            "msrp": msrp,
            "selling_price": selling_price,
            "dealer_discount": dealer_discount,
            "drivetrain": drivetrain,
            "inventory_date": inventory_date,
            "true_age_days": age_days,
            "inventory_type": "new"
        })

    return out


# ---------------- SCRAPE ----------------

def scrape(dealers, raw_file):

    progress = load_progress()
    start_index = progress.get("last_index", 0)

    log.info(f"RESUMING FROM DEALER INDEX: {start_index}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context()

        for idx, d in enumerate(dealers):

            if idx < start_index:
                continue

            url = d.get("dealerUrl")
            dealer_name = d.get("dealerName", "")
            bac = str(d.get("bac", "")).strip()

            # 🔥 FIXED BRAND
            brand = "Ford"

            page = ctx.new_page()
            page.set_default_timeout(15000)

            page_num = 1
            dealer_rows = []

            while page_num <= TEST_MAX_PAGES:

                try:
                    log.info(f"{dealer_name} → page {page_num}")

                    page.goto(
                        f"{url}/searchnew.aspx?pt={page_num}",
                        timeout=20000,
                        wait_until="domcontentloaded"
                    )

                    try:
                        page.wait_for_selector("[data-vehicle-information]", timeout=8000)
                        selector = "[data-vehicle-information]"
                    except:
                        try:
                            page.wait_for_selector(".vehicle-card", timeout=6000)
                            selector = ".vehicle-card"
                        except:
                            log.warning(f"{dealer_name} → NO VALID SELECTOR")
                            break

                    html = page.content()

                    new_rows = extract(html, brand, selector, dealer_name, bac)

                    if not new_rows:
                        break

                    dealer_rows.extend(new_rows)
                    page_num += 1

                except Exception as e:
                    log.warning(f"{dealer_name} page {page_num} failed → {e}")

                    try:
                        page.goto(
                            f"{url}/searchnew.aspx?pt={page_num}",
                            timeout=15000,
                            wait_until="domcontentloaded"
                        )

                        html = page.content()
                        new_rows = extract(html, brand, "[data-vehicle-information]", dealer_name, bac)

                        if new_rows:
                            dealer_rows.extend(new_rows)
                            page_num += 1
                            continue

                    except:
                        pass

                    break

            page.close()

            append_csv(raw_file, dealer_rows)
            save_progress(idx + 1)

        browser.close()


# ---------------- MAIN ----------------

def main():

    dealers = load_dealers()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_file = BASE_DIR / f"inventory_raw_ford_{timestamp}.csv"

    scrape(dealers, raw_file)

    log.info("SCRAPE COMPLETE — FORD SAFE MODE")


if __name__ == "__main__":
    main()