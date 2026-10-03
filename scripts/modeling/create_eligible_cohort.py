import pandas as pd
import os

# Load original cleaned dataset
df = pd.read_csv(
    "data/processed/clean_base.csv",
    low_memory=False
)

print("Original encounters:", len(df))

# Count expired encounters
expired = df[
    df["discharge_disposition_id"] == 11
]

print("Expired encounters:", len(expired))

# Remove ONLY patients whose encounter ended in death
eligible = df[
    df["discharge_disposition_id"] != 11
].copy()

print("Eligible encounters:", len(eligible))

# Safety check
print(
    "Expired remaining:",
    (
        eligible["discharge_disposition_id"]
        == 11
    ).sum()
)

print(
    "30-day readmission rate:",
    eligible["target_30d"].mean()
)

# Save as NEW dataset
os.makedirs(
    "data/processed",
    exist_ok=True
)

eligible.to_csv(
    "data/processed/eligible_base.csv",
    index=False
)

print(
    "Saved:",
    os.path.exists(
        "data/processed/eligible_base.csv"
    )
)
