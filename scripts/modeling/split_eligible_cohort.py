import pandas as pd
import os

from sklearn.model_selection import GroupShuffleSplit


# ==========================================
# LOAD ELIGIBLE COHORT
# ==========================================

df = pd.read_csv(
    "data/processed/eligible_base.csv",
    low_memory=False
)

print("Total eligible encounters:", len(df))
print("Unique patients:", df["patient_nbr"].nunique())


# ==========================================
# FIRST SPLIT: 70% TRAIN / 30% TEMP
# ==========================================

groups = df["patient_nbr"]

gss1 = GroupShuffleSplit(
    n_splits=1,
    train_size=0.70,
    random_state=42
)

train_idx, temp_idx = next(
    gss1.split(
        df,
        df["target_30d"],
        groups
    )
)

train = df.iloc[train_idx].copy()
temp = df.iloc[temp_idx].copy()


# ==========================================
# SECOND SPLIT: TEMP -> 15% VAL / 15% TEST
# ==========================================

gss2 = GroupShuffleSplit(
    n_splits=1,
    train_size=0.50,
    random_state=42
)

val_idx, test_idx = next(
    gss2.split(
        temp,
        temp["target_30d"],
        temp["patient_nbr"]
    )
)

val = temp.iloc[val_idx].copy()
test = temp.iloc[test_idx].copy()


# ==========================================
# LEAKAGE CHECK
# ==========================================

assert set(
    train["patient_nbr"]
).isdisjoint(
    val["patient_nbr"]
)

assert set(
    train["patient_nbr"]
).isdisjoint(
    test["patient_nbr"]
)

assert set(
    val["patient_nbr"]
).isdisjoint(
    test["patient_nbr"]
)

print()
print("PATIENT LEAKAGE CHECK: PASSED")


# ==========================================
# BASIC RESULTS
# ==========================================

print()
print("SPLIT SIZES")
print("--------------------")

print("Train:", len(train))
print("Validation:", len(val))
print("Test:", len(test))

print()
print("READMISSION RATES")
print("--------------------")

print(
    "Train:",
    train["target_30d"].mean()
)

print(
    "Validation:",
    val["target_30d"].mean()
)

print(
    "Test:",
    test["target_30d"].mean()
)


# ==========================================
# EXTRA SAFETY CHECK
# ==========================================

print()
print("EXPIRED ENCOUNTERS")
print("--------------------")

print(
    "Train:",
    (train["discharge_disposition_id"] == 11).sum()
)

print(
    "Validation:",
    (val["discharge_disposition_id"] == 11).sum()
)

print(
    "Test:",
    (test["discharge_disposition_id"] == 11).sum()
)


# ==========================================
# SAVE NEW SPLITS
# ==========================================

output_dir = "data/processed/eligible"

os.makedirs(
    output_dir,
    exist_ok=True
)

train.to_csv(
    f"{output_dir}/train.csv",
    index=False
)

val.to_csv(
    f"{output_dir}/validation.csv",
    index=False
)

test.to_csv(
    f"{output_dir}/test.csv",
    index=False
)

print()
print("FILES SAVED")
print("--------------------")

print(
    os.path.exists(
        f"{output_dir}/train.csv"
    )
)

print(
    os.path.exists(
        f"{output_dir}/validation.csv"
    )
)

print(
    os.path.exists(
        f"{output_dir}/test.csv"
    )
)
