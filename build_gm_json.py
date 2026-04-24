import pandas as pd
import json

# =========================
# LOAD CLEAN DATA
# =========================

df = pd.read_csv("gm_scrape_data_clean.csv")


# =========================
# DEBUG: UNDERSTAND YOUR DATA
# =========================

print("\n=== DATA DIAGNOSTICS ===")
print("Total rows:", len(df))
print("Unique BACs:", df['bac'].nunique())
print("Unique URLs:", df['dealerUrl'].nunique())
print("========================\n")


# =========================
# CLEAN KEY FIELDS
# =========================

# Normalize BAC
df['bac'] = df['bac'].astype(str).str.strip()

# Normalize URLs
df['dealerUrl'] = df['dealerUrl'].astype(str).str.strip().str.lower()

# Normalize ZIP (extra safety)
df['postalCode'] = df['postalCode'].astype(str).str.zfill(5).str[:5]


# =========================
# REMOVE BAD ROWS
# =========================

# Remove missing BAC OR URL (must have at least one valid identity)
df = df[(df['bac'] != "") | (df['dealerUrl'] != "")]

# Remove obvious junk URLs
df = df[~df['dealerUrl'].str.contains("search", na=False)]


# =========================
# PRIMARY DEDUPE LOGIC
# =========================

# Step 1: Deduplicate by BAC (true rooftop identity)
df_bac = df[df['bac'] != ""].drop_duplicates(subset=['bac'])

# Step 2: Handle rows with missing BAC → dedupe by URL
df_no_bac = df[df['bac'] == ""].drop_duplicates(subset=['dealerUrl'])

# Combine back
gm_df = pd.concat([df_bac, df_no_bac], ignore_index=True)


# =========================
# FINAL FIELD SELECTION
# =========================

gm_df = gm_df[[
    'dealerName',
    'dealerUrl',
    'city',
    'state',
    'postalCode',
    'bac',
    'dealerCode'
]]


# =========================
# FINAL CLEANUP
# =========================

for col in ['dealerName', 'dealerUrl', 'city', 'state', 'postalCode']:
    gm_df[col] = gm_df[col].astype(str).str.strip()

# Final dedupe safety (BAC + URL combo)
gm_df = gm_df.drop_duplicates(subset=['bac', 'dealerUrl'])


# =========================
# OUTPUT JSON
# =========================

records = gm_df.to_dict(orient='records')

with open("gm_master.json", "w") as f:
    json.dump(records, f, indent=2)


# =========================
# FINAL DEBUG OUTPUT
# =========================

print("✅ GM JSON created successfully")
print(f"Final dealer count: {len(records)}")
print(f"Final unique BACs: {gm_df['bac'].nunique()}")
print(f"Final unique URLs: {gm_df['dealerUrl'].nunique()}")