"""RescueNet V3 Upgrade D: frozen outer patient-grouped folds."""

from pathlib import Path
import json

import numpy as np
import pandas as pd

from sklearn.model_selection import StratifiedGroupKFold

SOURCE = Path("data/processed/eligible/train.csv")
OUT = Path("results/eligible/v3/upgrade_d")

MANIFEST = OUT / "outer_fold_assignments.csv"
SUMMARY = OUT / "outer_fold_summary.json"

SEED = 42
N_FOLDS = 5

assert not MANIFEST.exists(), "Outer fold manifest already exists"
assert not SUMMARY.exists(), "Outer fold summary already exists"

df = pd.read_csv(SOURCE, low_memory=False)

assert df.encounter_id.is_unique
assert df.patient_nbr.notna().all()
assert df.target_30d.notna().all()
assert set(df.target_30d.unique()) == {0, 1}

y = df.target_30d.astype(int)
groups = df.patient_nbr

splitter = StratifiedGroupKFold(
    n_splits=N_FOLDS,
    shuffle=True,
    random_state=SEED,
)

assignments = np.full(len(df), -1, dtype=int)
fold_summary = []

print("=== UPGRADE D OUTER FOLD CREATION ===")

for fold, (train_idx, test_idx) in enumerate(
    splitter.split(df, y, groups)
):
    train_patients = set(groups.iloc[train_idx])
    test_patients = set(groups.iloc[test_idx])

    assert train_patients.isdisjoint(test_patients)
    assert np.all(assignments[test_idx] == -1)

    assignments[test_idx] = fold

    record = {
        "fold": fold,
        "train_encounters": len(train_idx),
        "test_encounters": len(test_idx),
        "train_patients": len(train_patients),
        "test_patients": len(test_patients),
        "test_positives": int(y.iloc[test_idx].sum()),
        "test_negatives": int((y.iloc[test_idx] == 0).sum()),
        "patient_overlap": 0,
    }

    fold_summary.append(record)

    print(
        f"Fold {fold}: "
        f"train={len(train_idx)}, "
        f"test={len(test_idx)}, "
        f"positives={record['test_positives']}, "
        f"patient_overlap=0"
    )

assert np.all(assignments >= 0)

manifest = df[["encounter_id", "patient_nbr", "target_30d"]].copy()
manifest["outer_fold"] = assignments

assert manifest.encounter_id.is_unique

# Every patient must belong to exactly one outer evaluation fold.
patient_fold_counts = (
    manifest.groupby("patient_nbr")["outer_fold"].nunique()
)

assert patient_fold_counts.max() == 1

OUT.mkdir(parents=True, exist_ok=True)

manifest.to_csv(MANIFEST, index=False)

SUMMARY.write_text(json.dumps({
    "status": "FROZEN_OUTER_SPLIT",
    "seed": SEED,
    "n_folds": N_FOLDS,
    "source": str(SOURCE),
    "encounters": len(df),
    "unique_patients": int(groups.nunique()),
    "folds": fold_summary,
}, indent=2))

print("\nSaved:", MANIFEST)
print("Saved:", SUMMARY)
print("All patients assigned to exactly one fold: PASS")
print("OUTER PATIENT-GROUPED SPLIT: PASS")
