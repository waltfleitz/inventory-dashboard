# ==========================================
# CLEAN FORD DEALER JSON
# NORMALIZE KEYS + REMOVE BAD RECORDS
# ==========================================

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

INPUT_FILE = BASE_DIR / "ford_dealers_master.json"
OUTPUT_FILE = BASE_DIR / "ford_dealers_master_clean.json"


def normalize_dealer(d):

    dealer_name = (
        d.get("dealerName")
        or d.get("name")
        or d.get("dealer")
        or d.get("DealerName")
        or ""
    )

    dealer_url = (
        d.get("dealerUrl")
        or d.get("url")
        or d.get("website")
        or ""
    )

    bac = str(d.get("bac") or "").strip()

    # basic validation
    if not dealer_name or not dealer_url:
        return None

    return {
        "dealerName": dealer_name.strip(),
        "dealerUrl": dealer_url.strip(),
        "bac": bac
    }


def main():

    with open(INPUT_FILE, "r", encoding="utf-8-sig") as f:
        data = json.load(f)

    cleaned = []
    seen_urls = set()

    for d in data:

        norm = normalize_dealer(d)

        if not norm:
            continue

        # remove duplicates by URL
        url = norm["dealerUrl"].lower()

        if url in seen_urls:
            continue

        seen_urls.add(url)
        cleaned.append(norm)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, indent=2)

    print(f"✅ CLEANED DEALERS: {len(cleaned)}")
    print(f"📁 OUTPUT: {OUTPUT_FILE.name}")


if __name__ == "__main__":
    main()