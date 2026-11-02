"""RescueNet V3 Upgrade D: fixed MLP router, outer fold 0."""

from pathlib import Path
import json

import numpy as np
import pandas as pd

from sklearn.impute import SimpleImputer
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

BASE = Path("results/eligible/v3/upgrade_d/pilot_fold0")

DEV = BASE / "router_development_predictions.csv"
TEST = BASE / "outer_test_predictions_LOCKED.csv"

DEV_OUT = BASE / "mlp_router_development_scores.csv"
TEST_OUT = BASE / "mlp_router_outer_test_scores_LOCKED.csv"
META_OUT = BASE / "mlp_router_pilot_metadata.json"

for path in [DEV_OUT, TEST_OUT, META_OUT]:
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

dev = pd.read_csv(DEV)
test = pd.read_csv(TEST)

assert "actual_30d" in dev.columns
assert "actual_30d" not in test.columns
assert "target_30d" not in test.columns

dev_neg = dev.loc[
    dev.calibrated_probability < THRESHOLD
].copy()

test_neg = test.loc[
    test.calibrated_probability < THRESHOLD
].copy()

assert len(dev_neg) == 8241
assert int(dev_neg.actual_30d.sum()) == 673
assert len(test_neg) == 10391

assert set(dev_neg.patient_nbr).isdisjoint(
    set(test_neg.patient_nbr)
)

X_train = dev_neg[FEATURES]
y_train = dev_neg.actual_30d.astype(int)

router = Pipeline([
    ("imputer", SimpleImputer(strategy="median")),
    ("scaler", StandardScaler()),
    ("classifier", MLPClassifier(
        hidden_layer_sizes=(32, 16),
        activation="relu",
        alpha=0.001,
        learning_rate_init=0.001,
        max_iter=300,
        early_stopping=False,
        random_state=42,
    )),
])

print("=== UPGRADE D MLP ROUTER PILOT ===")
print("Training encounters:", len(dev_neg))
print("Training false negatives:", int(y_train.sum()))
print("Features:", FEATURES)

router.fit(X_train, y_train)

dev_neg["mlp_router_score"] = router.predict_proba(
    dev_neg[FEATURES]
)[:, 1]

test_neg["mlp_router_score"] = router.predict_proba(
    test_neg[FEATURES]
)[:, 1]

for frame in [dev_neg, test_neg]:
    assert np.isfinite(frame.mlp_router_score).all()
    assert frame.mlp_router_score.between(0, 1).all()

dev_neg[
    ["encounter_id", "patient_nbr", "actual_30d",
     "calibrated_probability", "mlp_router_score"]
].to_csv(DEV_OUT, index=False)

test_neg[
    ["encounter_id", "patient_nbr",
     "calibrated_probability", "mlp_router_score"]
].to_csv(TEST_OUT, index=False)

metadata = {
    "outer_fold": 0,
    "primary_threshold": THRESHOLD,
    "features": FEATURES,
    "model": "MLPClassifier",
    "hidden_layer_sizes": [32, 16],
    "alpha": 0.001,
    "max_iter": 300,
    "random_state": 42,
    "development_primary_negatives": len(dev_neg),
    "outer_test_primary_negatives": len(test_neg),
    "outer_test_labels_used": False,
    "status": "PILOT_NOT_FINAL_EVALUATION",
}

META_OUT.write_text(json.dumps(metadata, indent=2) + "\n")

print("\nDevelopment scores:", len(dev_neg))
print("Outer-test scores:", len(test_neg))
print("Outer-test labels used: NO")
print("Saved:", DEV_OUT)
print("Saved:", TEST_OUT)
print("Saved:", META_OUT)
print("\nUPGRADE D MLP ROUTER PILOT: COMPLETE")
