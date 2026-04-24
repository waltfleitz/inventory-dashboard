import pandas as pd
import json

# =========================
# URL NORMALIZATION (CRITICAL FIX)
# =========================

def normalize_url(url):
    if not url or str(url) == "nan":
        return ""

    url = str(url).strip().lower()

    url = url.replace("https://", "")
    url = url.replace("http://", "")
    url = url.replace("www.", "")

    if url.endswith("/"):
        url = url[:-1]

    return url


# =========================
# LOAD FILES (FIXED FOR BOM)
# =========================

with open("chevy_dealers_master.json", "r", encoding="utf-8-sig") as f:
    chevy_data = json.load(f)

df = pd.read_csv("gm_scrape_data_clean.csv")


# =========================
# CLEAN CSV DATA
# =========================

df['dealerUrl'] = df['dealerUrl'].apply(normalize_url)
df['bac'] = df['bac'].astype(str).str.strip()

# Remove bad rows early (important safety)
df = df[df['dealerUrl'] != ""]

# Keep only needed fields
df_lookup = df[[
    'dealerUrl',
    'bac',
    'dealerCode',
    'city',
    'state',
    'postalCode'
]].drop_duplicates(subset=['dealerUrl'])


# Convert CSV to lookup dictionary
lookup = df_lookup.set_index('dealerUrl').to_dict(orient='index')


# =========================
# ENRICH JSON
# =========================

updated = []
matched = 0

for dealer in chevy_data:
    url_raw = dealer.get("dealerUrl", "")
    url = normalize_url(url_raw)

    if url in lookup:
        row = lookup[url]

        # Only fill missing fields
        if not dealer.get("bac"):
            dealer["bac"] = row.get("bac")

        if not dealer.get("dealerCode"):
            dealer["dealerCode"] = row.get("dealerCode")

        if not dealer.get("city"):
            dealer["city"] = row.get("city")

        if not dealer.get("state"):
            dealer["state"] = row.get("state")

        if not dealer.get("postalCode"):
            dealer["postalCode"] = row.get("postalCode")

        matched += 1

    updated.append(dealer)


# =========================
# SAVE OUTPUT
# =========================

with open("chevy_dealers_enriched.json", "w") as f:
    json.dump(updated, f, indent=2)


# =========================
# DEBUG OUTPUT
# =========================

print("\n✅ Chevy JSON enrichment complete")
print(f"Total dealers: {len(updated)}")
print(f"Matched with CSV: {matched}")
print(f"Match rate: {round((matched / len(updated)) * 100, 2)}%")