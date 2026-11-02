"""Create a patient-disjoint V3 router development split."""

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit

SOURCE = Path("results/eligible/v3/primary_oof_calibrated.csv")
OUTPUT_DIR = Path("results/eligible/v3")
THRESHOLD = 0.115
SEED = 42

df = pd.read_csv(SOURCE, low_memory=False)

routing = df.loc[
    df["calibrated_probability"] < THRESHOLD
].copy()

features = [
    "calibrated_probability",
    "model_disagreement_std",
    "number_diagnoses",
    "number_outpatient",
    "number_emergency",
]

assert routing["encounter_id"].is_unique
assert routing[features].notna().all().all()

splitter = GroupShuffleSplit(
    n_splits=1,
    test_size=0.20,
    random_state=SEED,
)

train_idx, val_idx = next(
    splitter.split(
        routing[features],
        routing["actual_30d"],
        groups=routing["patient_nbr"],
    )
)

train = routing.iloc[train_idx].copy()
val = routing.iloc[val_idx].copy()

overlap = set(train["patient_nbr"]) & set(val["patient_nbr"])
assert not overlap, "Patient overlap detected"

assert len(train) + len(val) == len(routing)

print("=== V3 ROUTER DEVELOPMENT SPLIT ===")
for name, part in [("TRAIN", train), ("VALIDATION", val)]:
    print(
        name,
        "encounters=", len(part),
        "patients=", part["patient_nbr"].nunique(),
        "false_negatives=", int(part["actual_30d"].sum()),
        "FN_rate=", round(part["actual_30d"].mean(), 5),
    )

print("Patient overlap:", len(overlap))

outputs = [
    (train, OUTPUT_DIR / "router_dev_train.csv"),
    (val, OUTPUT_DIR / "router_dev_validation.csv"),
]

for _, path in outputs:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite: {path}")

for part, path in outputs:
    part.to_csv(path, index=False)
    print("Saved:", path)

print("ROUTER DEVELOPMENT SPLIT: PASS")
