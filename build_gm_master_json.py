import json

# =========================
# LOAD FILES
# =========================

def load_json(file):
    with open(file, "r", encoding="utf-8-sig") as f:
        return json.load(f)

chevy = load_json("chevy_dealers_master.json")
gmc = load_json("gmc_dealers.json")
buick = load_json("buick_dealers.json")
cadillac = load_json("cadillac_dealers_master.json")


# =========================
# HELPER
# =========================

def clean(val):
    if not val:
        return ""
    return str(val).strip()


# =========================
# MASTER BUILD
# =========================

master = {}

def add_dealers(data, brand_name):
    for d in data:

        bac = clean(d.get("bac"))
        url = clean(d.get("dealerUrl")).lower()

        # 🔥 Primary key logic
        key = bac if bac else url

        if not key:
            continue

        if key not in master:
            master[key] = {
                "dealerName": clean(d.get("dealerName")),
                "dealerUrl": url,
                "bac": bac,
                "dealerCode": clean(d.get("dealerCode")),
                "city": clean(d.get("city")),
                "state": clean(d.get("state")),
                "postalCode": clean(d.get("postalCode")),
                "brands": set()
            }

        # add brand
        master[key]["brands"].add(brand_name)

        # fill missing fields if needed
        if not master[key]["city"]:
            master[key]["city"] = clean(d.get("city"))

        if not master[key]["state"]:
            master[key]["state"] = clean(d.get("state"))

        if not master[key]["postalCode"]:
            master[key]["postalCode"] = clean(d.get("postalCode"))

        if not master[key]["dealerName"]:
            master[key]["dealerName"] = clean(d.get("dealerName"))


# =========================
# PROCESS ALL BRANDS
# =========================

add_dealers(chevy, "Chevy")
add_dealers(gmc, "GMC")
add_dealers(buick, "Buick")
add_dealers(cadillac, "Cadillac")


# =========================
# FINALIZE OUTPUT
# =========================

output = []

for dealer in master.values():
    dealer["brands"] = sorted(list(dealer["brands"]))
    output.append(dealer)


# =========================
# SAVE
# =========================

with open("gm_dealers_master.json", "w") as f:
    json.dump(output, f, indent=2)


# =========================
# DEBUG
# =========================

print("\n✅ GM MASTER JSON BUILT")
print(f"Total unique dealers: {len(output)}")