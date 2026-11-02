"""RescueNet V3 Upgrade D: outer-fold-0 LR router pilot."""

from pathlib import Path
import argparse
import json

import numpy as np
import pandas as pd

from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

parser = argparse.ArgumentParser()
parser.add_argument("--fold", type=int, required=True, choices=[1, 2, 3, 4])
args = parser.parse_args()
FOLD = args.fold

BASE = Path(f"results/eligible/v3/upgrade_d/pilot_fold{FOLD}")

DEV_PATH = BASE / "router_development_predictions.csv"
TEST_PATH = BASE / "outer_test_predictions_LOCKED.csv"

DEV_OUTPUT = BASE / "lr_router_development_scores.csv"
TEST_OUTPUT = BASE / "lr_router_outer_test_scores_LOCKED.csv"
META_OUTPUT = BASE / "lr_router_pilot_metadata.json"

for path in [DEV_OUTPUT, TEST_OUTPUT, META_OUTPUT]:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite: {path}")

THRESHOLD = 0.115

FEATURES = [
    "calibrated_probability",
    "model_disagreement_std",
    "number_diagnoses",
    "number_outpatient",
    "number_emergency",
]

dev = pd.read_csv(DEV_PATH)
test = pd.read_csv(TEST_PATH)

assert "actual_30d" in dev.columns
assert "actual_30d" not in test.columns
assert "target_30d" not in test.columns

assert set(dev.patient_nbr).isdisjoint(set(test.patient_nbr))
assert dev.encounter_id.is_unique
assert test.encounter_id.is_unique

dev_neg = dev.loc[
    dev.calibrated_probability < THRESHOLD
].copy()

dev_neg["is_false_negative"] = (
    dev_neg.actual_30d.astype(int)
)

assert len(dev_neg) > 0
assert 0 < int(dev_neg.is_false_negative.sum()) < len(dev_neg)
assert dev_neg.is_false_negative.nunique() == 2

router = Pipeline([
    ("imputer", SimpleImputer(strategy="median")),
    ("scaler", StandardScaler()),
    ("classifier", LogisticRegression(
        class_weight="balanced",
        max_iter=2000,
        random_state=42,
    )),
])

print("=== UPGRADE D LR ROUTER PILOT ===")
print("Training encounters:", len(dev_neg))
print("Training false negatives:", int(dev_neg.is_false_negative.sum()))
print("Features:", FEATURES)

router.fit(
    dev_neg[FEATURES],
    dev_neg["is_false_negative"],
)

dev_neg["lr_router_score"] = router.predict_proba(
    dev_neg[FEATURES]
)[:, 1]

# No outer-test outcomes are read or used.
test_neg = test.loc[
    test.calibrated_probability < THRESHOLD
].copy()

test_neg["lr_router_score"] = router.predict_proba(
    test_neg[FEATURES]
)[:, 1]

for frame in [dev_neg, test_neg]:
    assert np.isfinite(frame.lr_router_score).all()
    assert frame.lr_router_score.between(0, 1).all()

# Preserve development labels only in the development artifact.
dev_cols = [
    "encounter_id", "patient_nbr",
    "actual_30d", "is_false_negative",
    "calibrated_probability", "lr_router_score",
]

test_cols = [
    "encounter_id", "patient_nbr",
    "calibrated_probability", "lr_router_score",
]

metadata = {
    "outer_fold": FOLD,
    "primary_threshold": THRESHOLD,
    "features": FEATURES,
    "model": "LogisticRegression",
    "class_weight": "balanced",
    "random_state": 42,
    "development_primary_negatives": len(dev_neg),
    "development_false_negatives": int(
        dev_neg.is_false_negative.sum()
    ),
    "outer_test_primary_negatives": len(test_neg),
    "outer_test_labels_used": False,
    "status": "PILOT_NOT_FINAL_EVALUATION",
}

BASE.mkdir(parents=True, exist_ok=True)

dev_neg[dev_cols].to_csv(DEV_OUTPUT, index=False)
test_neg[test_cols].to_csv(TEST_OUTPUT, index=False)

META_OUTPUT.write_text(
    json.dumps(metadata, indent=2) + "\n"
)

print("\nDevelopment scores:", len(dev_neg))
print("Outer-test scores:", len(test_neg))
print("Outer-test labels used: NO")
print("Saved:", DEV_OUTPUT)
print("Saved:", TEST_OUTPUT)
print("Saved:", META_OUTPUT)
print("\nUPGRADE D LR ROUTER PILOT: COMPLETE")
