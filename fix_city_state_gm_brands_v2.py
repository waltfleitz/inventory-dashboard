import pandas as pd

# =========================
# LOAD ZIP DATABASE
# =========================

zips = pd.read_excel("uszips.xlsx", dtype={"zip": str})

zips['zip'] = zips['zip'].astype(str).str.zfill(5)
zips = zips[['zip', 'city', 'state_id']]
zips.columns = ['zip_clean', 'zip_city', 'zip_state']


# =========================
# ZIP CLEAN FUNCTION
# =========================

def clean_zip(z):
    if pd.isna(z):
        return ""

    z = str(z).strip()

    # CASE 1: encoded pattern (00007-0663)
    if "-" in z:
        left, right = z.split("-", 1)
        left = left.lstrip('0')

        if left and len(right) >= 4:
            return (left[0] + right[:4]).zfill(5)

    # CASE 2: normal ZIP
    digits = ''.join(filter(str.isdigit, z))

    if len(digits) >= 5:
        return digits[:5]

    return ""


# =========================
# PROCESS FILE
# =========================

def fix_file(input_file):
    df = pd.read_csv(input_file)

    # normalize headers
    df.columns = df.columns.str.strip().str.lower()

    # detect ZIP column
    if 'postalcode' in df.columns:
        zip_col = 'postalcode'
    elif 'zip' in df.columns:
        zip_col = 'zip'
    else:
        print(f"\n❌ No ZIP column in {input_file}")
        print(df.columns)
        return

    # ensure columns exist
    if 'city' not in df.columns:
        df['city'] = None
    if 'state' not in df.columns:
        df['state'] = None

    # 🔥 FIX: force zip_clean to be string BEFORE assignment
    if 'zip_clean' not in df.columns:
        df['zip_clean'] = ""
    df['zip_clean'] = df['zip_clean'].astype(str)

    # only rows still missing
    mask = df['city'].isna() | df['state'].isna()

    # apply cleaning only to missing rows
    df.loc[mask, 'zip_clean'] = df.loc[mask, zip_col].apply(clean_zip)

    # merge ZIP lookup
    df = df.merge(zips, on='zip_clean', how='left')

    # fill missing only
    df.loc[mask, 'city'] = df.loc[mask, 'city'].fillna(df.loc[mask, 'zip_city'])
    df.loc[mask, 'state'] = df.loc[mask, 'state'].fillna(df.loc[mask, 'zip_state'])

    # cleanup
    df = df.drop(columns=['zip_city', 'zip_state'])

    # overwrite same file
    df.to_csv(input_file, index=False)

    # debug
    print(f"\n✅ UPDATED: {input_file}")
    print(f"Total rows: {len(df)}")
    print(f"Missing city: {df['city'].isna().sum()}")
    print(f"Missing state: {df['state'].isna().sum()}")


# =========================
# RUN ON CLEAN FILES
# =========================

fix_file("gmc_dealers_clean.csv")
fix_file("buick_dealers_clean.csv")