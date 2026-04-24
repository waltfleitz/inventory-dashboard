import pandas as pd
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
HISTORY_FILE = BASE_DIR / "inventory_history.csv"

def main():

    df = pd.read_csv(HISTORY_FILE)

    df["first_seen"] = pd.to_datetime(df["first_seen"])
    df["days"] = (pd.Timestamp.today() - df["first_seen"]).dt.days

    df["model"] = df["model"].fillna("UNKNOWN")
    df["trim"] = df["trim"].fillna("")
    df["condition"] = df["condition"].fillna("unknown")

    grouped = (
        df.groupby(["dealer","condition","model","trim"])
        .agg(
            qty=("vin","count"),
            avg_days=("days","mean"),
            aged_units=("days", lambda x: (x >= 21).sum()),
            oldest_days=("days","max")
        )
        .reset_index()
    )

    grouped["avg_days"] = grouped["avg_days"].round(1)

    grouped = grouped.sort_values(
        by=["oldest_days","aged_units","qty"],
        ascending=False
    )

    grouped.to_csv(BASE_DIR / "model_trim_breakdown.csv", index=False)

    hot = grouped[
        (grouped["condition"] == "new") &
        (grouped["aged_units"] >= 3) &
        (grouped["avg_days"] >= 25)
    ]

    hot.to_csv(BASE_DIR / "HOT_OPPORTUNITIES.csv", index=False)

    print("\nAnalysis complete:")
    print(" - model_trim_breakdown.csv")
    print(" - HOT_OPPORTUNITIES.csv\n")

if __name__ == "__main__":
    main()