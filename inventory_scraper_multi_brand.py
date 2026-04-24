# ==========================================
# SNAPSHOT INVENTORY ENGINE — NORTHEAST LIVE + UI READY
# WITH BACKUP + TESTING PIPELINE (NO DRIFT)
# ==========================================

import csv
import logging
import json
import shutil
from datetime import datetime
from pathlib import Path
from collections import defaultdict

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

BASE_DIR = Path(__file__).resolve().parent
JSON_FILE = BASE_DIR / "gm_dealers_master.json"
TESTING_DIR = BASE_DIR / "Testing"

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger()

TEST_TARGET_NAMES = []

NORTHEAST_STATES = {
    "NY", "NJ", "PA", "CT", "MA", "RI", "VT", "NH", "ME"
}

# ---------------- VIN YEAR ----------------

VIN_YEAR_MAP = {
    '1': 2001, '2': 2002, '3': 2003, '4': 2004,
    '5': 2005, '6': 2006, '7': 2007, '8': 2008, '9': 2009,
    'A': 2010, 'B': 2011, 'C': 2012, 'D': 2013,
    'E': 2014, 'F': 2015, 'G': 2016, 'H': 2017,
    'J': 2018, 'K': 2019, 'L': 2020, 'M': 2021,
    'N': 2022, 'P': 2023, 'R': 2024, 'S': 2025,
    'T': 2026, 'V': 2027, 'W': 2028, 'X': 2029,
    'Y': 2030
}

def get_year_from_vin(vin):
    if len(vin) != 17:
        return None
    return VIN_YEAR_MAP.get(vin[9])

# ---------------- HELPERS ----------------

def safe_int(val):
    try:
        return int(float(val))
    except:
        return 0

def calc_age_days(date_str):
    try:
        dt = datetime.strptime(date_str, "%Y/%m/%d")
        return (datetime.now() - dt).days
    except:
        return 0

# ---------------- LOAD ----------------

def load_dealers():
    with open(JSON_FILE, "r", encoding="utf-8-sig") as f:
        return json.load(f)

# ---------------- EXTRACTION ----------------

def extract(html, dealer_name, bac, state, city):

    soup = BeautifulSoup(html, "html.parser")
    rows = []

    cards = soup.select("[data-vehicle-information]")

    if not cards:
        cards = soup.find_all(attrs={"data-vin": True})

    if not cards:
        log.warning(f"{dealer_name} → NO VEHICLE CARDS FOUND")
        return []

    for c in cards:

        vin = (c.get("data-vin") or "").strip().upper()
        if len(vin) != 17:
            continue

        model = (c.get("data-model") or "").strip()

        inventory_date = c.get("data-dotagging-item-inventory-date")
        age_days = calc_age_days(inventory_date)

        rows.append({
            "dealer": dealer_name,
            "city": city,
            "state": state,
            "bac": bac,
            "model": model,
            "vin": vin,
            "year": get_year_from_vin(vin),
            "true_age_days": age_days,
            "inventory_type": "new"
        })

    return rows

# ---------------- SCRAPE ----------------

def scrape(dealers, raw_file):

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context()

        for d in dealers:

            dealer_name = d.get("dealerName", "")
            url = d.get("dealerUrl")
            state = (d.get("state") or "").upper()
            city = d.get("city")
            bac = str(d.get("bac", "")).strip()

            page = ctx.new_page()
            page.set_default_timeout(15000)

            dealer_rows = []

            for page_num in range(1, 4):

                try:
                    log.info(f"{dealer_name} → page {page_num}")

                    page.goto(f"{url}/searchnew.aspx?pt={page_num}", timeout=20000)

                    html = page.content()

                    dealer_rows.extend(
                        extract(html, dealer_name, bac, state, city)
                    )

                except Exception as e:
                    log.warning(f"{dealer_name} failed → {e}")
                    break

            page.close()

            if dealer_rows:
                append_csv(raw_file, dealer_rows)

        browser.close()

# ---------------- SAVE ----------------

def append_csv(path, rows):
    if not rows:
        return

    file_exists = path.exists()
    keys = rows[0].keys()

    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)

def overwrite_csv(path, rows):
    if not rows:
        return

    keys = rows[0].keys()

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)

# ---------------- METRICS ----------------

def add_metrics(rows):

    grouped = defaultdict(list)

    for r in rows:
        grouped[(r["dealer"], r["model"])].append(r)

    for units in grouped.values():

        total = len(units)
        aged_60 = sum(1 for u in units if safe_int(u["true_age_days"]) >= 60)
        stuck_ratio = round(aged_60 / total, 3) if total else 0

        for u in units:
            age = safe_int(u["true_age_days"])

            age_factor = min(age / 30, 5)
            base_pressure = (aged_60 * 3) + (stuck_ratio * 15)

            u["pressure_score"] = round(base_pressure + age_factor, 2)

            u["model_total"] = total
            u["model_aged_60_plus"] = aged_60
            u["model_stuck_ratio"] = stuck_ratio

    return rows

# ---------------- MAIN ----------------

def main():

    dealers = load_dealers()

    dealers = [
        d for d in dealers
        if (d.get("state") or "").upper() in NORTHEAST_STATES
    ]

    if TEST_TARGET_NAMES:
        dealers = [
            d for d in dealers
            if any(name in d.get("dealerName", "").upper() for name in TEST_TARGET_NAMES)
        ]

    log.info(f"DEALERS RUNNING: {len(dealers)}")

    # LIVE FILES
    raw_file = BASE_DIR / "inventory_raw.csv"
    call_file = BASE_DIR / "call_sheet.csv"

    # BACKUPS
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_backup = BASE_DIR / f"inventory_raw_{ts}.csv"
    call_backup = BASE_DIR / f"call_sheet_{ts}.csv"

    if raw_file.exists():
        raw_file.unlink()

    scrape(dealers, raw_file)

    if not raw_file.exists():
        log.warning("NO DATA WRITTEN")
        return

    rows = list(csv.DictReader(open(raw_file)))
    rows = add_metrics(rows)

    overwrite_csv(call_file, rows)

    # 🔥 SAVE BACKUPS
    shutil.copy(raw_file, raw_backup)
    shutil.copy(call_file, call_backup)

    # 🔥 COPY TO TESTING FOLDER
    TESTING_DIR.mkdir(exist_ok=True)
    shutil.copy(call_file, TESTING_DIR / call_backup.name)

    log.info(f"CALL SHEET GENERATED → {call_file}")

if __name__ == "__main__":
    main()