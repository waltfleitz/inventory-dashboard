import pandas as pd
import json

# =========================
# CLEAN VALUE HELPER
# =========================

def clean(val):
    if pd.isna(val):
        return ""
    return str(val).strip()


# =========================
# BUILD JSON FUNCTION
# =========================

def build_json(input_file, output_file):
    df = pd.read_csv(input_file)

    df.columns = df.columns.str.strip().str.lower()

    dealers = []
    seen = set()

    for _, row in df.iterrows():

        name = clean(row.get("dealername"))
        url = clean(row.get("dealerurl"))
        bac = clean(row.get("bac"))
        code = clean(row.get("dealercode"))
        city = clean(row.get("city"))
        state = clean(row.get("state"))
        zip_code = clean(row.get("postalcode"))

        # 🔥 dedupe key (priority: BAC → URL)
        key = bac if bac else url

        if not key or key in seen:
            continue

        seen.add(key)

        dealer = {
            "dealerName": name,
            "dealerUrl": url,
            "bac": bac,
            "dealerCode": code,
            "city": city,
            "state": state,
            "postalCode": zip_code
        }

        dealers.append(dealer)

    # =========================
    # SAVE JSON
    # =========================

    with open(output_file, "w") as f:
        json.dump(dealers, f, indent=2)

    print(f"\n✅ JSON built: {output_file}")
    print(f"Total dealers: {len(dealers)}")


# =========================
# RUN BOTH
# =========================

build_json("gmc_dealers_clean.csv", "gmc_dealers.json")
build_json("buick_dealers_clean.csv", "buick_dealers.json")