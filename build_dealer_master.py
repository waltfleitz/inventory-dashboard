# ==========================================
# DEALER MASTER BUILDER (AUTO CLEAN + PRIORITY)
# ==========================================

import csv
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parent

INPUT_FILE = BASE_DIR / "dealer_master.csv"      # your GHL export (renamed headers)
OUTPUT_FILE = BASE_DIR / "dealer_master_clean.csv"


# ---------------- CONTACT PRIORITY ----------------

def get_priority(contact_type):
    if not contact_type:
        return 2  # treat blank as GSM

    ct = contact_type.lower()

    if "general manager" in ct:
        return 1
    if "gsm" in ct:
        return 2
    if "sales_manager" in ct:
        return 3
    if "inventory_manager" in ct:
        return 4

    return 5


# ---------------- LOAD DATA ----------------

def load_contacts():
    with open(INPUT_FILE, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ---------------- BUILD MASTER ----------------

def build_master(rows):

    grouped = defaultdict(list)

    for r in rows:
        bac = r.get("bac")
        if not bac:
            continue
        grouped[bac].append(r)

    final = []

    for bac, contacts in grouped.items():

        # sort by priority
        contacts_sorted = sorted(
            contacts,
            key=lambda x: get_priority(x.get("contact_type"))
        )

        best = contacts_sorted[0]

        contact_name = f"{best.get('first_name','').strip()} {best.get('last_name','').strip()}".strip()

        final.append({
            "bac": bac,
            "dealer_name": best.get("dealer_name"),
            "contact_name": contact_name,
            "email": best.get("email"),
            "phone": best.get("phone"),
            "assigned_rep": best.get("assigned_rep"),
            "customer_status": best.get("customer_status"),
            "dealer_type": best.get("dealer_type"),
            "region": best.get("region")
        })

    return final


# ---------------- WRITE FILE ----------------

def write_output(rows):
    if not rows:
        print("No rows to write")
        return

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"Dealer master built → {len(rows)} dealers")


# ---------------- MAIN ----------------

def main():
    rows = load_contacts()
    cleaned = build_master(rows)
    write_output(cleaned)


if __name__ == "__main__":
    main()