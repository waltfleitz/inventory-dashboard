# ==========================================================
# [01] IMPORTS
# ==========================================================

import pandas as pd
import re
from datetime import datetime
import csv
import requests
import json
import os
from concurrent.futures import ThreadPoolExecutor


# ==========================================================
# [02] CONFIG
# ==========================================================

INPUT_FILE = "2025 Chevy Units Jake Pulled From GM Global.xlsx"

CALL_OUTPUT_FILE = f"call_sheet_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

CACHE_FILE = "vin_cache.json"

MAX_WORKERS = 12


# ==========================================================
# [03] HELPERS
# ==========================================================

def clean(val):
    try:
        if pd.isna(val):
            return ""
        return str(val).strip()
    except:
        return ""


def find_vin(row):
    for cell in row:
        cell = str(cell).strip()
        if re.match(r'^[A-HJ-NPR-Z0-9]{17}$', cell):
            return cell
    return None


def extract_msrp_age(row):

    msrp = ""
    age = ""

    for idx, cell in enumerate(row):

        s = str(cell)

        if "$" in s:
            val = re.sub(r"[^\d]", "", s)
            if len(val) >= 5:
                msrp = val

        if re.match(r'^\d{1,4}$', s):
            num = int(s)
            if 0 < num < 1500:
                age = num

    return msrp, age


# ==========================================================
# [04] BRAND LOGIC
# ==========================================================

def get_brand(vin, model, dealer_name):

    d = dealer_name.lower()
    m = model.lower()

    if "gmc" in d:
        return "GMC"
    if "cadillac" in d:
        return "Cadillac"
    if "buick" in d:
        return "Buick"
    if "chevrolet" in d:
        return "Chevrolet"

    if "sierra" in m or "yukon" in m:
        return "GMC"
    if "silverado" in m:
        return "Chevrolet"

    if vin.startswith(("1G","3G")):
        return "Chevrolet"
    if vin.startswith("KL"):
        return "Buick"
    if vin.startswith("1GY"):
        return "Cadillac"
    if vin.startswith("1GT"):
        return "GMC"

    return ""


# ==========================================================
# [05] VIN CACHE
# ==========================================================

vin_cache = {}

if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r") as f:
        vin_cache = json.load(f)


def decode_vin(vin):

    if vin in vin_cache:
        return vin_cache[vin]

    data = {"model": ""}

    try:
        url = f"https://vpic.nhtsa.dot.gov/api/vehicles/decodevin/{vin}?format=json"
        r = requests.get(url, timeout=3)

        if r.status_code == 200:
            for item in r.json().get("Results", []):
                if item.get("Variable") == "Model":
                    data["model"] = item.get("Value")

    except:
        pass

    vin_cache[vin] = data
    return data


def batch_decode_vins(vins):
    unique = list(set(vins))

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        list(ex.map(decode_vin, unique))

    with open(CACHE_FILE, "w") as f:
        json.dump(vin_cache, f)


# ==========================================================
# [06] LOAD FILE
# ==========================================================

xls = pd.ExcelFile(INPUT_FILE)
rows = []

for sheet_name in xls.sheet_names:
    df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
    for r in df.values.tolist():
        rows.append((sheet_name, r))


# ==========================================================
# [07] FIRST PASS
# ==========================================================

all_vins = []

for _, row in rows:
    vin = find_vin(row)
    if vin:
        all_vins.append(vin)

batch_decode_vins(all_vins)


# ==========================================================
# [08] MAIN PARSE
# ==========================================================

call_rows = []
seen_vin = set()

current_bac = ""
dealer_name = ""


for i in range(len(rows)):

    sheet, raw = rows[i]
    row = [clean(x) for x in raw]
    row_str = " ".join(row).upper()


    # ===============================
    # BAC CONTEXT
    # ===============================
    if "BAC:" in row_str:

        match = re.search(r'BAC:\s*(\d{6})', row_str)
        if match:
            current_bac = match.group(1)

        target_index = i + 1 if "OWNING DEALER CODE" in row_str else i + 2

        if target_index < len(rows):
            _, next_raw = rows[target_index]
            next_row = [clean(x) for x in next_raw]
            dealer_name = next_row[0].title() if next_row[0] else ""

        continue


    vin = find_vin(row)
    if not vin:
        continue

    if not current_bac or not dealer_name:
        continue

    key = (current_bac, vin)
    if key in seen_vin:
        continue
    seen_vin.add(key)


    # ===============================
    # MSRP FIX (GLOBAL)
    # ===============================
    msrp, age = extract_msrp_age(row)

    if not msrp:
        for k in range(1,6):
            if i+k < len(rows):
                _, nxt = rows[i+k]
                for cell in nxt:
                    if "$" in str(cell):
                        val = re.sub(r"[^\d]", "", str(cell))
                        if len(val) >= 5:
                            msrp = val
                            break
            if msrp:
                break


    vin_data = vin_cache.get(vin, {})
    model = vin_data.get("model", "")

    peg = ""
    trim = ""
    engine = ""
    drivetrain = ""
    color = ""
    body_style = ""

    for j in range(i, min(i + 15, len(rows))):

        _, look_raw = rows[j]
        look_row = [clean(x) for x in look_raw]
        look_str = " ".join(look_row).upper()

        if "BODY STYLE:" in look_str and not body_style:
            body_style = look_str.replace("BODY STYLE:", "").strip()

        elif "PEG:" in look_str and not peg:
            peg = look_str.replace("PEG:", "").strip()

        elif "TRIM:" in look_str and not trim:
            trim = look_str.replace("TRIM:", "").strip()

        elif "ENGINE:" in look_str and not engine:
            engine = look_str.replace("ENGINE:", "").strip()

        elif "TRANSMISSION:" in look_str and not drivetrain:
            drivetrain = look_str.replace("TRANSMISSION:", "").strip()

        elif "PRIMARY COLOR:" in look_str and not color:
            color = look_str.replace("PRIMARY COLOR:", "").strip()

        if "OPTIONS" in look_str:
            break

        if j > i and find_vin(look_row):
            break


    if not model:
        combined = f"{peg} {body_style}".upper()
        if "SILVERADO" in combined:
            model = "Silverado"
        elif "TRAX" in combined:
            model = "Trax"


    brand = get_brand(vin, model, dealer_name)


    call_rows.append([
        current_bac,
        dealer_name,
        vin,
        brand,
        model,
        body_style,
        peg,
        trim,
        engine,
        drivetrain,
        color,
        msrp,
        age,
        sheet
    ])


# ==========================================================
# [09] OUTPUT
# ==========================================================

with open(CALL_OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow([
        "bac","dealer_name","vin","brand","model",
        "body_style","peg","trim","engine","drivetrain","color",
        "msrp","age_days","source_sheet"
    ])
    writer.writerows(call_rows)

print(f"\n🚀 CALL SHEET: {CALL_OUTPUT_FILE}")