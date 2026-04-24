import pandas as pd

# =========================
# LOAD ZIP DATABASE
# =========================

zips = pd.read_excel("uszips.xlsx", dtype={"zip": str})

zips['zip'] = zips['zip'].astype(str).str.zfill(5)
zips = zips[['zip', 'city', 'state_id']]
zips.columns = ['zip_clean', 'zip_city', 'zip_state']


# =========================
# ZIP CLEAN FUNCTION (FINAL)
# =========================

def clean_zip(z):
    if pd.isna(z):
        return ""

    z = str(z).strip()

    # CASE 1: has dash
    if "-" in z:
        left, right = z.split("-", 1)

        # 🔥 ENCODED FORMAT (00007-0663)
        if left.startswith("0000"):
            left = left.lstrip('0')

            if left and len(right) >= 4:
                return (left[0] + right[:4]).zfill(5)

        # 🔥 NORMAL ZIP+4
        digits = ''.join(filter(str.isdigit, z))
        if len(digits) >= 5:
            return digits[:5]

        return ""

    # CASE 2: no dash → normal ZIP
    digits = ''.join(filter(str.isdigit, z))

    if len(digits) >= 5:
        return digits[:5]

    return ""


# =========================
# PROCESS FILE FUNCTION
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
        print(f"\n❌ No ZIP column found in {input_file}")
        print(df.columns)
        return

    # ensure city/state exist
    if 'city' not in df.columns:
        df['city'] = None
    if 'state' not in df.columns:
        df['state'] = None

    # 🔥 ensure zip_clean exists and is STRING (fix crash)
    if 'zip_clean' not in df.columns:
        df['zip_clean'] = ""
    df['zip_clean'] = df['zip_clean'].astype(str)

    # only rows still missing
    mask = df['city'].isna() | df['state'].isna()

    # apply ZIP cleaning ONLY to missing rows
    df.loc[mask, 'zip_clean'] = df.loc[mask, zip_col].apply(clean_zip)

    # remove blanks before merge
    df_valid = df[df['zip_clean'] != ""].copy()

    # merge ZIP lookup
    df_valid = df_valid.merge(zips, on='zip_clean', how='left')

    # bring results back
    df.loc[df_valid.index, 'city'] = df_valid['city'].fillna(df_valid['zip_city'])
    df.loc[df_valid.index, 'state'] = df_valid['state'].fillna(df_valid['zip_state'])

    # save (overwrite same clean file)
    df.to_csv(input_file, index=False)

    # debug output
    print(f"\n✅ UPDATED: {input_file}")
    print(f"Total rows: {len(df)}")
    print(f"Missing city: {df['city'].isna().sum()}")
    print(f"Missing state: {df['state'].isna().sum()}")


# =========================
# RUN BOTH FILES
# =========================

fix_file("gmc_dealers_clean.csv")
fix_file("buick_dealers_clean.csv")