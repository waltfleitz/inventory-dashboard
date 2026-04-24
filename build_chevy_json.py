import pandas as pd
import json

# =========================
# LOAD CLEAN DATA
# =========================

df = pd.read_csv("gm_scrape_data_clean.csv")


# =========================
# FILTER CHEVY DEALERS
# =========================

chevy_df = df[df['dealerName'].str.contains("chev", case=False, na=False)]


# =========================
# SELECT + STANDARDIZE FIELDS
# =========================

chevy_df = chevy_df[[
    'dealerName',
    'dealerUrl',
    'city',
    'state',
    'postalCode',
    'bac',
    'dealerCode'
]]


# =========================
# CLEAN TEXT (IMPORTANT)
# =========================

for col in ['dealerName', 'dealerUrl', 'city', 'state', 'postalCode']:
    chevy_df[col] = chevy_df[col].astype(str).str.strip()


# =========================
# REMOVE BAD ROWS
# =========================

chevy_df = chevy_df[chevy_df['dealerUrl'].notna()]
chevy_df = chevy_df.drop_duplicates(subset=['dealerUrl'])


# =========================
# CONVERT TO JSON
# =========================

records = chevy_df.to_dict(orient='records')

with open("chevy_new.json", "w") as f:
    json.dump(records, f, indent=2)


print(f"✅ Chevy JSON created: {len(records)} dealers")