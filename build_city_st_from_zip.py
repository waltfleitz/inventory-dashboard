import pandas as pd

# =========================
# LOAD FILES
# =========================

# Your scraped dealer file
df = pd.read_csv("gm_scrape_data.csv")

# Your ZIP database (Excel)
zips = pd.read_excel("uszips.xlsx", dtype={"zip": str})


# =========================
# NORMALIZE ZIP CODES (CRITICAL FIX)
# =========================

# Scrape file ZIPs → force 5 digits
df['postalCode'] = df['postalCode'].astype(str).str.zfill(5).str[:5]

# ZIP database → force 5 digits
zips['zip'] = zips['zip'].astype(str).str.zfill(5)


# =========================
# PREP ZIP LOOKUP TABLE
# =========================

zips = zips[['zip', 'city', 'state_id']]
zips.columns = ['postalCode', 'zip_city', 'zip_state']


# =========================
# MERGE ZIP DATA INTO SCRAPE FILE
# =========================

df = df.merge(zips, on='postalCode', how='left')


# =========================
# FILL ONLY MISSING VALUES
# =========================

df['city'] = df['city'].fillna(df['zip_city'])
df['state'] = df['state'].fillna(df['zip_state'])


# =========================
# CLEANUP
# =========================

df = df.drop(columns=['zip_city', 'zip_state'])


# =========================
# SAVE OUTPUT
# =========================

df.to_csv("gm_scrape_data_clean.csv", index=False)


# =========================
# DEBUG SUMMARY
# =========================

total_rows = len(df)
missing_city = df['city'].isna().sum()
missing_state = df['state'].isna().sum()

print("✅ Done. Clean file created: gm_scrape_data_clean.csv")
print(f"Total rows: {total_rows}")
print(f"Missing city after fill: {missing_city}")
print(f"Missing state after fill: {missing_state}")