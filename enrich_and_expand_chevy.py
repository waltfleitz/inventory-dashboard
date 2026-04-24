import pandas as pd
import json

# =========================
# URL NORMALIZATION
# =========================

def normalize_url(url):
    if not url or str(url) == "nan":
        return ""

    url = str(url).strip().lower()
    url = url.replace("https://", "").replace("http://", "").replace("www.", "")

    if url.endswith("/"):
        url = url[:-1]

    return url


# =========================
# LOAD FILES
# =========================

with open("chevy_dealers_master.json", "r", encoding="utf-8-sig") as f:
    master = json.load(f)

df = pd.read_csv("gm_scrape_data_clean.csv")

df['dealerUrl'] = df['dealerUrl'].apply(normalize_url)
df['bac'] = df['bac'].astype(str).str.strip()

df = df[(df['dealerUrl'] != "") | (df['bac'] != "")]


# =========================
# BUILD LOOKUPS
# =========================

lookup_url = {}
lookup_bac = {}

for _, row in df.iterrows():
    if row['dealerUrl']:
        lookup_url[row['dealerUrl']] = row.to_dict()
    if row['bac']:
        lookup_bac[row['bac']] = row.to_dict()


# =========================
# INDEX MASTER
# =========================

master_url_set = set()
master_bac_set = set()

for d in master:
    url = normalize_url(d.get("dealerUrl", ""))
    bac = str(d.get("bac", "")).strip()

    if url:
        master_url_set.add(url)
    if bac:
        master_bac_set.add(bac)


# =========================
# ENRICH EXISTING
# =========================

matched = 0

for d in master:
    url = normalize_url(d.get("dealerUrl", ""))
    bac = str(d.get("bac", "")).strip()

    row = None

    if bac and bac in lookup_bac:
        row = lookup_bac[bac]
    elif url and url in lookup_url:
        row = lookup_url[url]

    if row:
        d["bac"] = d.get("bac") or row.get("bac")
        d["dealerCode"] = d.get("dealerCode") or row.get("dealerCode")
        d["city"] = d.get("city") or row.get("city")
        d["state"] = d.get("state") or row.get("state")
        d["postalCode"] = d.get("postalCode") or row.get("postalCode")
        matched += 1


# =========================
# ADD NEW DEALERS
# =========================

added = 0

for _, row in df.iterrows():
    url = row['dealerUrl']
    bac = row['bac']

    if (url and url not in master_url_set) and (bac and bac not in master_bac_set):

        new_dealer = {
            "bac": row.get("bac"),
            "dealerCode": row.get("dealerCode"),
            "dealerName": row.get("dealerName"),
            "dealerUrl": row.get("dealerUrl"),
            "city": row.get("city"),
            "state": row.get("state"),
            "postalCode": row.get("postalCode")
        }

        master.append(new_dealer)

        if url:
            master_url_set.add(url)
        if bac:
            master_bac_set.add(bac)

        added += 1


# =========================
# SAVE OUTPUT
# =========================

with open("chevy_dealers_master_updated.json", "w") as f:
    json.dump(master, f, indent=2)


# =========================
# OUTPUT
# =========================

print("\n✅ ENRICH + EXPAND COMPLETE")
print(f"Original dealers: {len(master) - added}")
print(f"Enriched: {matched}")
print(f"Added new dealers: {added}")
print(f"Final total: {len(master)}")