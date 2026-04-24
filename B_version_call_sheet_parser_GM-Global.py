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
OUTPUT_FILE = f"call_sheet_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

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


def extract_msrp_age_block(rows, start_idx):

    msrp = ""
    age = ""

    for i in range(start_idx, min(start_idx + 6, len(rows))):

        _, r = rows[i]

        for cell in r:
            s = str(cell)

            if "$" in s:
                val = re.sub(r"[^\d]", "", s)
                if len(val) >= 5:
                    msrp = val

            if re.match(r'^\d{1,4}$', s):
                num = int(s)
                if 0 < num < 1500:
                    age = num

        if msrp:
            break

    return msrp, age


def extract_details_block(rows, start_idx):

    peg = ""
    trim = ""
    engine = ""
    drivetrain = ""
    color = ""
    body_style = ""

    for i in range(start_idx, min(start_idx + 15, len(rows))):

        _, raw = rows[i]
        row = [clean(x) for x in raw]
        text = " ".join(row).upper()

        if "BODY STYLE:" in text and not body_style:
            body_style = text.split("BODY STYLE:")[-1].strip()

        elif "PEG:" in text and not peg:
            peg = text.split("PEG:")[-1].strip()

        elif "TRIM:" in text and not trim:
            trim = text.split("TRIM:")[-1].strip()

        elif "ENGINE:" in text and not engine:
            engine = text.split("ENGINE:")[-1].strip()

        elif "TRANSMISSION:" in text and not drivetrain:
            drivetrain = text.split("TRANSMISSION:")[-1].strip()

        elif "PRIMARY COLOR:" in text and not color:
            color = text.split("PRIMARY COLOR:")[-1].strip()

        if "OPTIONS" in text:
            break

        if i > start_idx and find_vin(row):
            break

    return peg, trim, engine, drivetrain, color, body_style


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
# [04] VIN CACHE
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
# [05] LOAD FILE
# ==========================================================

xls = pd.ExcelFile(INPUT_FILE)

rows = []
for sheet in xls.sheet_names:
    df = pd.read_excel(xls, sheet_name=sheet, header=None)
    for r in df.values.tolist():
        rows.append((sheet, r))


# ==========================================================
# [06] FIRST PASS VIN DECODE
# ==========================================================

all_vins = []

for _, r in rows:
    vin = find_vin(r)
    if vin:
        all_vins.append(vin)

batch_decode_vins(all_vins)


# ==========================================================
# [07] BLOCK PARSER
# ==========================================================

call_rows = []
seen = set()

current_bac = ""
dealer_name = ""

i = 0

while i < len(rows):

    sheet, raw = rows[i]
    row = [clean(x) for x in raw]
    text = " ".join(row).upper()

    # ===============================
    # DEALER BLOCK START
    # ===============================
    if "BAC:" in text:

        match = re.search(r'BAC:\s*(\d{6})', text)
        if match:
            current_bac = match.group(1)

        # dealer name extraction
        for j in range(i+1, min(i+4, len(rows))):
            _, next_raw = rows[j]
            next_row = [clean(x) for x in next_raw]
            next_text = " ".join(next_row)

            if next_text and not find_vin(next_row):
                dealer_name = re.split(r'\d{3,}', next_text)[0]
                dealer_name = re.split(r'DISTANCE', dealer_name, flags=re.IGNORECASE)[0]
                dealer_name = dealer_name.strip().title()
                break

        i += 1
        continue

    # ===============================
    # VIN DETECT
    # ===============================
    vin = find_vin(row)

    if vin and current_bac and dealer_name:

        key = (current_bac, vin)
        if key in seen:
            i += 1
            continue

        seen.add(key)

        # MSRP + AGE
        msrp, age = extract_msrp_age_block(rows, i)

        # DETAILS
        peg, trim, engine, drivetrain, color, body_style = extract_details_block(rows, i)

        # VIN decode
        vin_data = vin_cache.get(vin, {})
        model = vin_data.get("model", "")

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

    i += 1


# ==========================================================
# [08] OUTPUT
# ==========================================================

with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow([
        "bac","dealer_name","vin","brand","model",
        "body_style","peg","trim","engine","drivetrain","color",
        "msrp","age_days","source_sheet"
    ])
    writer.writerows(call_rows)


print(f"\n🚀 DONE: {OUTPUT_FILE}")