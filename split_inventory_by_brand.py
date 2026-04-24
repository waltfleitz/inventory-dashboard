# ==========================================
# SPLIT INVENTORY BY BRAND (FINAL STABLE VERSION)
# ==========================================

import pandas as pd
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent

INPUT_FILE = BASE_DIR / "inventory_raw_20260412_185932.csv"


# ---------------- BRAND MAP (EXPANDED GM) ----------------

MODEL_BRAND_MAP = {

    "CHEVROLET": [
        "SILVERADO", "TAHOE", "SUBURBAN", "TRAX", "EQUINOX",
        "TRAVERSE", "COLORADO", "CORVETTE", "CAMARO", "MALIBU",
        "BLAZER", "TRAILBLAZER", "EXPRESS", "SPARK",
        "BRIGHTDROP", "LOW CAB FORWARD", "LCF", "CUTAWAY"
    ],

    "GMC": [
        "SIERRA", "YUKON", "ACADIA", "TERRAIN", "CANYON",
        "HUMMER"
    ],

    "CADILLAC": [
        "ESCALADE", "CT4", "CT5", "XT4", "XT5", "XT6", "LYRIQ"
    ],

    "BUICK": [
        "ENCLAVE", "ENCORE", "ENCORE GX", "ENVISION", "ENVISTA"
    ],

    "FORD": [
        "F-150", "F150", "SUPER DUTY", "F-250", "F-350",
        "RANGER", "MAVERICK", "EXPEDITION", "EXPLORER",
        "ESCAPE", "EDGE", "BRONCO", "MUSTANG"
    ]
}


# ---------------- BRAND DETECTION ----------------

def detect_brand(row):

    text = ""

    if "model" in row and pd.notna(row["model"]):
        text += str(row["model"]).upper() + " "

    if "trim" in row and pd.notna(row["trim"]):
        text += str(row["trim"]).upper() + " "

    vin = str(row.get("vin", "")).upper()

    # 🔥 FIX: HANDLE COMMERCIAL / SPECIAL CASES FIRST
    if any(x in text for x in ["CAB FORWARD", "CUTAWAY", "LCF"]):
        return "CHEVROLET"

    # 🔥 PRIMARY MATCH
    for brand, models in MODEL_BRAND_MAP.items():
        for m in sorted(models, key=len, reverse=True):
            if m in text:
                return brand

    # 🔥 VIN FALLBACK
    if vin.startswith(("1F", "1FT")):
        return "FORD"

    if vin.startswith(("1G", "2G", "3G")):
        return "CHEVROLET"  # fallback GM bucket

    return "OTHER"


# ---------------- MAIN ----------------

def main():

    if not INPUT_FILE.exists():
        print(f"❌ FILE NOT FOUND: {INPUT_FILE}")
        return

    df = pd.read_csv(INPUT_FILE)

    if "model" not in df.columns:
        print("❌ 'model' column missing")
        return

    print("🔍 Detecting brands...")
    df["brand_clean"] = df.apply(detect_brand, axis=1)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    output_counts = {}

    for brand in df["brand_clean"].unique():

        brand_df = df[df["brand_clean"] == brand]

        output_file = BASE_DIR / f"inventory_raw_{brand.lower()}_{timestamp}.csv"

        brand_df.to_csv(output_file, index=False)

        output_counts[brand] = len(brand_df)

    print("\n✅ SPLIT COMPLETE:")
    for b, c in output_counts.items():
        print(f"{b}: {c} units")


if __name__ == "__main__":
    main()