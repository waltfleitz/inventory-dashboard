# ==========================================
# SNAPSHOT INVENTORY ENGINE (SCRAPE + MATCH SWITCH)
# VERSION: v1.2.1 (FULL FILE - extraction fixed properly)
# ==========================================

import csv
import logging
import re
import json
import base64
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

BASE_DIR = Path(__file__).resolve().parent

JSON_FILE = BASE_DIR / "chevy_dealers_master.json"
DEALER_MASTER_FILE = BASE_DIR / "dealer_master.csv"
HISTORY_FILE = BASE_DIR / "inventory_history.csv"

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger()

TEST_MODE = True
TEST_DEALERS = 5

RUN_MATCHES_ONLY = False

# ---------------- LOADERS ----------------

def load_dealers():
    with open(JSON_FILE, "r", encoding="utf-8-sig") as f:
        return json.load(f)

def load_dealer_master():
    out = {}

    if not DEALER_MASTER_FILE.exists():
        return out

    with open(DEALER_MASTER_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for r in reader:
            key = r.get("bac") or r.get("GM Dealer ID (BAC)")
            if key:
                key = str(key).strip().split(".")[0]
                out[key] = r

    return out

def load_history():
    if not HISTORY_FILE.exists():
        return {}

    history = {}

    with open(HISTORY_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for r in reader:
            history[r["vin"]] = r

    return history

# ---------------- SAVE ----------------

def append_history(path, rows):
    exists = path.exists()
    keys = sorted({k for r in rows for k in r.keys()})

    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)

        if not exists:
            writer.writeheader()

        writer.writerows(rows)

def safe_write(path, rows):
    if not rows:
        return

    keys = sorted({k for r in rows for k in r.keys()})

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)

# ---------------- HELPERS ----------------

def is_valid_vin(v):
    return v and len(v) == 17 and not any(c in v for c in ["I","O","Q"])

def calc_age_days(date_str):
    try:
        dt = datetime.strptime(date_str, "%Y/%m/%d").replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - dt).days
    except:
        return None

def vin_year(v):
    m = {"L":2020,"M":2021,"N":2022,"P":2023,"R":2024,"S":2025,"T":2026}
    return m.get(v[9], None)

# ---------------- EXTRACTION ----------------

def extract(html, inventory_type):

    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("[data-vehicle-information]")

    out = []

    for c in cards:

        vin = (c.get("data-vin") or "").strip().upper()

        if not is_valid_vin(vin):
            continue

        raw_model = c.get("data-model") or ""
        trim = c.get("data-trim") or ""
        color = c.get("data-dotagging-item-color")

        # MODEL SPLIT
        model = raw_model
        sub_model = ""

        parts = raw_model.split()
        if len(parts) >= 2:
            if parts[1].isdigit():
                model = parts[0]
                sub_model = parts[1]
            else:
                model = parts[0]
                sub_model = " ".join(parts[1:])

        # BODY STYLE
        body_style = ""
        blob = (raw_model + " " + trim).lower()

        if "crew" in blob:
            body_style = "Crew Cab"
        elif "double" in blob:
            body_style = "Double Cab"
        elif "regular" in blob:
            body_style = "Regular Cab"

        # DRIVETRAIN
        drivetrain = ""

        if "4wd" in blob or "4x4" in blob:
            drivetrain = "4WD"
        elif "awd" in blob:
            drivetrain = "AWD"
        elif "fwd" in blob:
            drivetrain = "FWD"
        elif "rwd" in blob:
            drivetrain = "RWD"

        inventory_date = c.get("data-dotagging-item-inventory-date")
        age_days = calc_age_days(inventory_date)

        pricing = {}
        pricelib = c.get("data-pricelib")

        if pricelib:
            try:
                decoded = base64.b64decode(pricelib).decode("utf-8", "ignore")
                pricing = json.loads(decoded)
            except:
                pricing = {}

        selling_price = (
            pricing.get("price")
            or pricing.get("selling_price")
            or pricing.get("internet_price")
            or pricing.get("final_price")
        )

        msrp = pricing.get("msrp") or c.get("data-msrp")

        try:
            selling_price = float(selling_price) if selling_price else None
            msrp = float(msrp) if msrp else None
        except:
            selling_price = None
            msrp = None

        if msrp and selling_price and selling_price <= msrp:
            dealer_discount = round(msrp - selling_price, 2)
        else:
            dealer_discount = 0

        year = c.get("data-year") or vin_year(vin)

        out.append({
            "vin": vin,
            "year": year,
            "brand": "Chevy",
            "model": model,
            "sub_model": sub_model,
            "body_style": body_style,
            "trim": trim,
            "drivetrain": drivetrain,
            "color": color,
            "dealer_discount": dealer_discount,
            "selling_price": selling_price,
            "msrp": msrp,
            "inventory_date": inventory_date,
            "true_age_days": age_days,
            "inventory_type": inventory_type
        })

    return out

# ---------------- SCRAPE ----------------

def scrape(dealers, ctx):

    all_rows = []

    if TEST_MODE:
        log.info(f"TEST MODE ACTIVE → limiting to {TEST_DEALERS} dealers")
        dealers = list(dealers)[:TEST_DEALERS]

    for d in dealers:

        base_url = d.get("dealerUrl")
        dealer_name = d.get("dealerName")

        if not base_url:
            continue

        page = ctx.new_page()

        for inv_type, path in [("new", "searchnew.aspx"), ("used", "searchused.aspx")]:

            page_num = 1

            while True:

                url = f"{base_url.rstrip('/')}/{path}?pt={page_num}"

                try:
                    log.info(f"{dealer_name} → {inv_type} → page {page_num}")

                    page.goto(url, timeout=60000)
                    html = page.content()

                    rows = extract(html, inv_type)

                    if not rows:
                        break

                    for r in rows:
                        r["dealer"] = dealer_name
                        r["bac"] = d.get("bac")
                        r["inventory_type"] = inv_type

                    all_rows.extend(rows)

                    page_num += 1

                    if TEST_MODE and page_num > 2:
                        break

                except Exception as e:
                    log.warning(f"{dealer_name} error: {e}")
                    break

        page.close()

    return all_rows

# ---------------- MAIN ----------------

def main():

    dealers = load_dealers()
    dealer_master = load_dealer_master()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context()

        rows = scrape(dealers, ctx)

        browser.close()

    for r in rows:
        dm = dealer_master.get(str(r.get("bac", "")).split(".")[0], {})

        r["assigned_rep"] = dm.get("Assigned To")
        r["email"] = dm.get("Email")
        r["contact_name"] = dm.get("First Name")
        r["region"] = dm.get("Region")

    safe_write(BASE_DIR / "inventory_raw.csv", rows)
    safe_write(BASE_DIR / "call_sheet.csv", rows)

    append_history(HISTORY_FILE, rows)

    log.info(f"SCRAPE COMPLETE → {len(rows)} units")

if __name__ == "__main__":
    main()