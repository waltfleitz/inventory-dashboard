# ==========================================================
# [01] IMPORTS
# ==========================================================

import pandas as pd
import json
import re
from collections import defaultdict
from datetime import datetime


# ==========================================================
# [02] CONFIG
# ==========================================================

INPUT_FILE = "2025 Chevy Units Jake Pulled From GM Global.xlsx"   # <-- CHANGE THIS
OUTPUT_FILE = f"dealer_master_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"


# ==========================================================
# [03] HELPER FUNCTIONS
# ==========================================================

def clean_string(val):
    if pd.isna(val):
        return ""
    return str(val).strip()

def extract_email_domain(email):
    if not email or "@" not in email:
        return ""
    return email.split("@")[-1].lower()

def build_website(domain):
    if not domain:
        return ""
    return f"https://www.{domain}"

def normalize_name(name):
    return " ".join([w.capitalize() for w in name.split()])

def normalize_title(title):
    return title.upper()

def is_valid_email(email):
    return "@" in email and "." in email

def is_valid_row(row):
    return any([str(x).strip() != "" for x in row])

def dedupe_contacts(contacts):
    seen = set()
    result = []

    for c in contacts:
        key = (c["email"].lower(), c["phone"])
        if key not in seen:
            seen.add(key)
            result.append(c)

    return result


# ==========================================================
# [04] LOAD FILE
# ==========================================================

df = pd.read_excel(INPUT_FILE, header=None)
rows = df.values.tolist()


# ==========================================================
# [05] DETECT DEALER BLOCKS
# ==========================================================

dealer_blocks = []
current_block = []

for row in rows:
    if "BAC:" in str(row[0]):
        if current_block:
            dealer_blocks.append(current_block)
        current_block = [row]
    else:
        current_block.append(row)

if current_block:
    dealer_blocks.append(current_block)


# ==========================================================
# [06] PARSE DEALER BLOCK (FIXED)
# ==========================================================

def parse_block(block):

    bac = ""
    dealer_name = ""

    street = ""
    city = ""
    state = ""
    zip_code = ""

    brands = []
    contacts = []

    stop_parsing = False

    for i, row in enumerate(block):

        if stop_parsing:
            break

        row_str = " ".join([clean_string(x) for x in row])

        # -------------------------
        # BAC
        # -------------------------
        if "BAC:" in row_str:
            match = re.search(r'BAC:\s*(\d{6})', row_str)
            if match:
                bac = match.group(1)
            continue

        # -------------------------
        # DEALER NAME (FIXED LOGIC)
        # -------------------------
        if dealer_name == "" and i > 0:
            prev = " ".join([clean_string(x) for x in block[i-1]])

            if (
                "BAC:" in prev and
                "Owning Dealer Code" not in row_str and
                "Trade Contact" not in row_str
            ):
                dealer_name = normalize_name(row_str)
                continue

        # -------------------------
        # ADDRESS
        # -------------------------
        if "," in row_str and any(char.isdigit() for char in row_str):
            parts = row_str.split(",")

            if len(parts) >= 3:
                street = parts[0].strip()
                city = parts[1].strip()

                state_zip = parts[2].strip().split()
                if len(state_zip) >= 2:
                    state = state_zip[0]
                    zip_code = state_zip[1]

        # -------------------------
        # BRAND + DEALER CODE
        # -------------------------
        if ":" in row_str and any(b in row_str for b in ["Chevrolet", "GMC", "Cadillac", "Buick"]):
            try:
                brand, code = row_str.split(":")
                brands.append({
                    "brand": brand.strip(),
                    "dealer_code": code.strip()
                })
            except:
                pass

        # -------------------------
        # CONTACT PARSING
        # -------------------------
        if row_str.startswith("Primary") or row_str.startswith("Secondary"):

            name = clean_string(row[1])
            title = clean_string(row[2])
            phone = clean_string(row[3])
            ext = clean_string(row[4])
            fax = clean_string(row[5])
            email = clean_string(row[6])
            preferred = clean_string(row[7])
            text = clean_string(row[8])
            notes = clean_string(row[9])

            if name or email:
                contact = {
                    "type": "Primary" if row_str.startswith("Primary") else "Secondary",
                    "name": normalize_name(name),
                    "title": normalize_title(title),
                    "phone": phone,
                    "ext": ext,
                    "fax": fax,
                    "text": text,
                    "email": email,
                    "preferred_contact": preferred,
                    "notes": notes
                }

                contacts.append(contact)

            # -------------------------
            # HARD STOP AT SECONDARY
            # -------------------------
            if row_str.startswith("Secondary"):
                stop_parsing = True


    # -------------------------
    # DEDUPE CONTACTS
    # -------------------------
    contacts = dedupe_contacts(contacts)

    # -------------------------
    # EMAIL DOMAIN
    # -------------------------
    email_domain = ""
    for c in contacts:
        if is_valid_email(c["email"]):
            email_domain = extract_email_domain(c["email"])
            break

    # -------------------------
    # BUILD DEALERS (PER BRAND)
    # -------------------------
    dealer_objs = []

    for b in brands:
        dealer_objs.append({
            "brand": b["brand"],
            "dealer_code": b["dealer_code"],
            "dealer_name": dealer_name,
            "website": "",
            "inventory_url": "",
            "email_domain": email_domain,
            "website_guess": build_website(email_domain),
            "website_guess_source": "email_domain",
            "website_guess_status": "untried",
            "address": {
                "street": street,
                "city": city,
                "state": state,
                "zip": zip_code
            },
            "contact": {
                "phone": "",
                "fax": ""
            },
            "trade_contacts": contacts
        })

    return {
        "bac": bac,
        "dealers": dealer_objs
    }


# ==========================================================
# [07] PROCESS ALL BLOCKS
# ==========================================================

output = []

for block in dealer_blocks:
    parsed = parse_block(block)
    if parsed["bac"]:
        output.append(parsed)


# ==========================================================
# [08] WRITE OUTPUT (SAFE)
# ==========================================================

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2)

print(f"\n✅ DONE: {OUTPUT_FILE}")